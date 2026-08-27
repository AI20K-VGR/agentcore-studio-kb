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

_SELECT_TENANT = "SELECT chunk_id, section_role, text, embed_text, doc_id, doc_name FROM kb.chunks WHERE tenant_id = %s"
_DELETE_TENANT = "DELETE FROM kb.chunks WHERE tenant_id = %s"
_DELETE_DOC = "DELETE FROM kb.chunks WHERE tenant_id = %s AND doc_id = %s"
_DELETE_DOC_TEXT = "DELETE FROM kb.document_texts WHERE tenant_id = %s AND doc_id = %s"
_UPSERT_DOC_TEXT = (
    "INSERT INTO kb.document_texts (tenant_id, doc_id, section_role, text) VALUES (%s, %s, %s, %s) "
    "ON CONFLICT (tenant_id, doc_id) DO UPDATE SET section_role = EXCLUDED.section_role, "
    "text = EXCLUDED.text, created_at = now()"
)
_SELECT_DOC_TEXTS = "SELECT doc_id, section_role, text FROM kb.document_texts WHERE tenant_id = %s ORDER BY doc_id"
_SELECT_TENANT_ORDERED = (
    "SELECT chunk_id, section_role, text, embed_text, doc_id, doc_name "
    "FROM kb.chunks WHERE tenant_id = %s ORDER BY chunk_id"
)


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
        vectors = await self._embedding.embed([c.embedding_input for c in chunks])
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
                        (
                            chunk.chunk_id,
                            chunk.tenant_id,
                            chunk.section_role,
                            chunk.text,
                            chunk.embedding_input,
                            _vector_literal(vector),
                            chunk.doc_id,
                            chunk.doc_name,
                        ),
                    )

    async def delete_by_doc_id(self, tenant_id: UUID, doc_id: str) -> int:
        """Xoá mọi `kb.chunks` của MỘT tài liệu (`doc_id`) trong `tenant_id`. Trả số dòng đã xoá.

        Tenant-scoped y hệt `consent_purge` (RLS `USING`/`WITH CHECK` + `WHERE tenant_id` tường
        minh, cùng lý do phòng thủ chiều sâu — xem đầu `postgres.py`). `doc_id` là khoá theo TÀI
        LIỆU, khác `chunk_id` (PK bền qua re-index) — nhiều chunk của cùng 1 doc chia sẻ đúng 1
        `doc_id`, nên một lệnh gọi xoá hết cả doc, không chỉ 1 chunk."""
        async with self._pool.connection() as conn, conn.transaction():
            await _bind_tenant(conn, tenant_id)
            cursor = await conn.execute(_DELETE_DOC, (tenant_id, doc_id))
            # Toàn văn đi cùng chunk, trong CÙNG transaction. Để lại nó là một tài liệu đã xoá vẫn
            # sinh ra case golden trỏ vào những `chunk_id` không còn tồn tại — mỗi case như vậy chấm
            # ra `citation_accuracy = 0` vĩnh viễn mà không ai truy được về đâu.
            await conn.execute(_DELETE_DOC_TEXT, (tenant_id, doc_id))
            return cursor.rowcount

    async def save_document_text(self, tenant_id: UUID, doc_id: str, section_role: str, text: str) -> None:
        """Giữ lại TOÀN VĂN tài liệu — thứ `extract_text` đã trích ra và `cut_window` đang vứt đi.

        Ghi ở đường upload, đọc ở đường sinh golden. Hai tầng khác nhau cho hai việc khác nhau:
        `kb.chunks` là tầng TRUY XUẤT (cửa sổ 850 từ, cắt ngang câu), còn soạn câu hỏi cần tầng TÀI
        LIỆU (tiêu đề và thân bài còn nguyên).

        `ON CONFLICT ... DO UPDATE` chứ không `DO NOTHING`: nạp lại cùng một tài liệu là cách người
        dùng SỬA nó, và giữ bản cũ sẽ làm bộ golden sinh từ một nội dung không còn tồn tại."""
        async with self._pool.connection() as conn, conn.transaction():
            await _bind_tenant(conn, tenant_id)
            await conn.execute(_UPSERT_DOC_TEXT, (tenant_id, doc_id, section_role, text))

    async def document_texts_for_tenant(self, tenant_id: UUID) -> list[tuple[str, str, str]]:
        """`(doc_id, section_role, text)` của mọi tài liệu ĐÃ lưu toàn văn, xếp theo `doc_id`.

        Tài liệu nạp trước khi hệ thống bắt đầu lưu toàn văn sẽ **không** có mặt ở đây, và đó là
        trạng thái hợp lệ: `build_cases` rơi về soạn ở tầng chunk cho đúng những tài liệu đó. Trả
        rỗng cũng hợp lệ — một tenant chưa nạp gì.

        `ORDER BY doc_id` cùng lý do `chunks_for_tenant`: `build_cases` khai tất định, và nó chỉ tất
        định khi đầu vào tất định."""
        async with self._pool.connection() as conn, conn.transaction():
            await _bind_tenant(conn, tenant_id)
            cursor = await conn.execute(_SELECT_DOC_TEXTS, (tenant_id,))
            return [(str(r[0]), str(r[1]), str(r[2])) for r in await cursor.fetchall()]

    async def chunks_for_tenant(self, tenant_id: UUID) -> list[Chunk]:
        """Mọi `kb.chunks` của `tenant_id`, **mọi phòng ban**, xếp theo `chunk_id`.

        Đường đọc cho bên sinh golden case từ KB đã upload (`studio_kb.golden_from_kb`). Trả về
        **cả tenant** chứ không một phòng ban, và đó là điểm chính chứ không phải tiện tay:
        `build_cases` dựng case **bẫy** bằng cách ghép chéo vai (`_pick_trap_source`) — hỏi dưới vai
        A trong khi đáp án nằm ở vai B. Đưa nó chunk của đúng một vai thì không còn gì để ghép
        chéo, và bộ sinh ra có **0 case hàng rào**: đo được, 400 chunk một vai ⇒ 58 case, 0 bẫy,
        0 `is_critical`, 0 `tier="core"`. Tức cổng sẽ chấm chất lượng trả lời mà **không bao giờ**
        chấm hàng rào — đúng trục duy nhất bắt được lỗi bịa-xuyên-chủ-thể (`engine#43`).

        Caller lọc case theo phòng ban SAU khi sinh (mỗi case mang `section_roles=(vai_hỏi,)`),
        chứ không lọc chunk TRƯỚC khi sinh.

        Trục T1 (chéo-tenant) vẫn không sinh được từ đây và **không nên**: nó đòi chunk của tenant
        khác, thứ RLS chặn và cũng không phải thứ nên đọc. Case T1 phải do người viết.

        `ORDER BY chunk_id` không phải trang trí — `build_cases` khai tất định, và nó chỉ tất định
        khi đầu vào tất định. Postgres không hứa thứ tự khi thiếu `ORDER BY`, nên bỏ nó đi thì bộ
        case đổi giữa hai lần chạy trên cùng dữ liệu, và cái đổi đó đi thẳng vào `eval.golden_sets`.

        Trả `Chunk` chứ không phải dòng thô: caller (composition root) không nên biết thứ tự cột.
        `embed_text`/`doc_id`/`doc_name` `NULL` → `""` cùng khuôn `re_index` ngay dưới.
        """
        async with self._pool.connection() as conn, conn.transaction():
            await _bind_tenant(conn, tenant_id)
            cursor = await conn.execute(_SELECT_TENANT_ORDERED, (tenant_id,))
            rows = await cursor.fetchall()
        return [
            Chunk(
                chunk_id=r[0],
                text=r[2],
                tenant_id=tenant_id,
                section_role=r[1],
                embed_text=r[3] or "",
                doc_id=r[4] or "",
                doc_name=r[5] or "",
            )
            for r in rows
        ]

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
        dòng đã xử lý; **giữ nguyên `chunk_id`/`section_role`/`doc_id`/`doc_name`** (đọc lại rồi
        upsert theo `chunk_id`)."""
        async with self._pool.connection() as conn, conn.transaction():
            await _bind_tenant(conn, tenant_id)
            cursor = await conn.execute(_SELECT_TENANT, (tenant_id,))
            rows = await cursor.fetchall()

        # `embed_text` ĐỌC LẠI TỪ DB (r[3]) chứ không suy lại: tiêu đề tài liệu không nằm trong
        # `text` của bất kỳ dòng nào, và việc đã-cắt-boilerplate cần thống kê cả scope — một dòng
        # đơn lẻ không tái tạo được. Dòng cũ (trước khi có cột) trả NULL → `""` → `embedding_input`
        # rơi về `text`, đúng hành vi trước đây. `doc_id` (r[4])/`doc_name` (r[5]) cùng khuôn: NULL
        # (dòng ghi trước khi có cột) → `""`, không raise — `doc_id` mất khả năng
        # `delete_by_doc_id` cho tới vòng re_index NÀY, sau đó tự phục hồi vì được ghi lại ở dưới;
        # `doc_name` chỉ mất nhãn hiển thị, không ai đọc nó để so khớp/xoá gì.
        chunks = [
            Chunk(
                chunk_id=r[0],
                text=r[2],
                tenant_id=tenant_id,
                section_role=r[1],
                embed_text=r[3] or "",
                doc_id=r[4] or "",
                doc_name=r[5] or "",
            )
            for r in rows
        ]
        if not chunks:
            return 0
        await self.index(chunks, await self.embed_invoke(chunks))
        return len(chunks)
