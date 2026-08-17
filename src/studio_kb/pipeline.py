"""KB ingestion pipeline (spec DE) — chunker → embed_invoke → index, cộng `consent_purge`/`re_index`
cho vòng đời dữ liệu tenant. Điền cho **corpus 2.0** (`docs/callisto-2.0-schema.md`): role/doc_id đến
từ tên file (metadata NGOÀI nội dung), nên các bước nhận chúng qua tham số/`Chunk`, không suy từ text.

**Uỷ quyền, KHÔNG viết lại.** Phần cắt dùng `doc_factory_v2` (luật 2.0), phần ghi tái dùng `_UPSERT` +
`_bind_tenant` của `postgres.py` (một nguồn SQL, cùng fence RLS/`WITH CHECK` như `KbIngest`). Khác
`KbIngest` ở chỗ pipeline TÁCH `embed_invoke` khỏi `index` (nhận vector đã tính sẵn), đúng hình dạng
5-method của seam; `re_index` thì soạn lại chính hai bước đó.

Chữ ký seam khác bản stub gốc (trả `Chunk`, mang `doc_id`/`section_role`): `KbPipeline` là spec DE và
KHÔNG có consumer nào ngoài `packages/kb`, nên đây là quyết định trong lane — không đụng hợp đồng
chung. Thứ DÙNG CHUNG là cột `vector(EMBEDDING_DIM)` (schema.py) + `EmbeddingService` (AIE-1); đổi
số chiều mới cần mini-RFC, không phải các chữ ký dưới đây.
"""

from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from studio_contracts.protocols import EmbeddingService

from studio_kb.doc_factory import Chunk
from studio_kb.doc_factory_v2 import _cut_document
from studio_kb.postgres import _UPSERT, Pool, _bind_tenant, _vector_literal
from studio_kb.schema import EMBEDDING_DIM

_SELECT_TENANT = "SELECT chunk_id, section_role, text FROM kb.chunks WHERE tenant_id = %s"
_DELETE_TENANT = "DELETE FROM kb.chunks WHERE tenant_id = %s"


class KbPipeline:
    """Doc-factory pipeline (2.0). Ghi qua pool **non-owner** để vế `WITH CHECK` của RLS cắn — một
    chunk mang `tenant_id` khác biến phiên `app.tenant_id` bị DB từ chối ngay (xem `postgres.py`)."""

    def __init__(self, pool: Pool, embedding: EmbeddingService) -> None:
        self._pool = pool
        self._embedding = embedding

    async def chunker(self, document: str, *, doc_id: str, tenant_id: UUID, section_role: str) -> list[Chunk]:
        """Cắt `document` (markdown 2.0, KHÔNG front-matter) → `Chunk`, mọi chunk mang `section_role`.

        Uỷ quyền `doc_factory_v2._cut_document`: giữ luật 2.0 (heading `{section:…}` → raise I5, thân
        rỗng → raise I7) và `chunk_id = "{doc_id}#c{n}"` — một nguồn cắt, không nhân bản. `doc_id`/
        `section_role` đến từ tên file (`{tenant}/{role}-{name}.md`) nên bên gọi truyền xuống, không
        suy từ nội dung. Ranh giới chunk không bao giờ vắt hai `section_role` (R-SPEC A3 / I6)."""
        return _cut_document(document, doc_id, tenant_id, section_role)

    async def embed_invoke(self, chunks: list[Chunk]) -> list[list[float]]:
        """Nhúng `chunks` qua `EmbeddingService` (AIE-1). Mọi vector rộng đúng `EMBEDDING_DIM`.

        Fail-fast tại đây: cột là `vector(EMBEDDING_DIM)` nên Postgres cũng từ chối ở `index`, nhưng
        báo sớm chỉ thẳng thủ phạm là `EmbeddingService`, không phải câu INSERT."""
        vectors = await self._embedding.embed([c.text for c in chunks])
        if len(vectors) != len(chunks):
            raise ValueError(f"embed() trả {len(vectors)} vector cho {len(chunks)} chunk")
        for vector in vectors:
            if len(vector) != EMBEDDING_DIM:
                raise ValueError(f"embedding sai chiều: {len(vector)} != {EMBEDDING_DIM}")
        return vectors

    async def index(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        """Ghi `chunks` + `embeddings` (đã tính) vào `kb.chunks`, idempotent theo `chunk_id`.

        Gom theo `tenant_id` rồi mỗi tenant một giao dịch: `app.tenant_id` là MỘT giá trị cho cả giao
        dịch, trộn hai tenant sẽ bị `WITH CHECK` chặn vế thứ hai. `ON CONFLICT DO UPDATE` (trong
        `_UPSERT`) là điều kiện `re_index` giữ nguyên `chunk_id` (§6)."""
        if len(embeddings) != len(chunks):
            raise ValueError(f"index nhận {len(chunks)} chunk nhưng {len(embeddings)} vector")

        by_tenant: dict[UUID, list[tuple[Chunk, list[float]]]] = defaultdict(list)
        for chunk, vector in zip(chunks, embeddings, strict=True):
            by_tenant[chunk.tenant_id].append((chunk, vector))

        for tenant_id, batch in by_tenant.items():
            async with self._pool.connection() as conn, conn.transaction():
                await _bind_tenant(conn, tenant_id)
                for chunk, vector in batch:
                    await conn.execute(
                        _UPSERT,
                        (chunk.chunk_id, chunk.tenant_id, chunk.section_role, chunk.text, _vector_literal(vector)),
                    )

    async def consent_purge(self, tenant_id: UUID) -> int:
        """Xoá mọi `kb.chunks` của `tenant_id` (consent / right-to-erasure). Trả số dòng đã xoá.

        Fail-closed: RLS `USING` chỉ cho thấy — do đó chỉ cho xoá — dòng của `tenant_id` hiện tại;
        `WHERE tenant_id = %s` là tầng phòng thủ thứ hai (phòng khi refactor quên `set_config`)."""
        async with self._pool.connection() as conn, conn.transaction():
            await _bind_tenant(conn, tenant_id)
            cursor = await conn.execute(_DELETE_TENANT, (tenant_id,))
            return cursor.rowcount

    async def re_index(self, tenant_id: UUID) -> int:
        """Nhúng lại + ghi lại mọi `kb.chunks` của `tenant_id` (vd sau khi nâng embedding). Trả số
        dòng đã xử lý; **giữ nguyên `chunk_id`/`section_role`** (đọc lại rồi upsert theo `chunk_id`)."""
        async with self._pool.connection() as conn, conn.transaction():
            await _bind_tenant(conn, tenant_id)
            cursor = await conn.execute(_SELECT_TENANT, (tenant_id,))
            rows = await cursor.fetchall()

        chunks = [Chunk(chunk_id=r[0], text=r[2], tenant_id=tenant_id, section_role=r[1]) for r in rows]
        if not chunks:
            return 0
        await self.index(chunks, await self.embed_invoke(chunks))
        return len(chunks)
