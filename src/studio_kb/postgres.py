"""Tầng lưu trữ Postgres thật cho `kb.chunks` — ingest (ghi) + truy xuất vector (đọc).

⚠️ **CHƯA NỐI VÀO ĐÂU.** Module này dựng sẵn cho task sắp tới, không nằm trên đường chạy nào hôm
nay. `KbSearchService` (`search.py`) và `KbPipeline` (`pipeline.py`) vẫn giữ nguyên
`NotImplementedError`, `tests/test_search_contract.py` vẫn xanh, và `StaticKbSearch` vẫn là thứ
AIE-1 tiêm vào ở D4.

**Bước "nối vào" khi tới lúc** — đây là quyết định của DE, không phải hệ quả phụ của commit này:
1. `KbSearchService.search` uỷ quyền một dòng sang `PgKbSearch.search` (chữ ký giống hệt).
2. **Xoá `tests/test_search_contract.py`** — nó là test XANH khẳng định seam kia raise; giữ lại thì
   nối vào là đỏ ngay.
3. **Gỡ `xfail` ở `tests/test_leak.py`** (un-ratchet, P5/P9) — hai test T1/T6 ở đó đang
   `xfail(strict=False)` chờ đúng ngày này.

**Đối chiếu với `static_search.py`:** bản tĩnh cắt markdown trong bộ nhớ, lọc bằng vòng `for`,
xếp hạng bằng trùng token. Bản này lọc **trong câu SQL** (RLS + `WHERE`) và xếp hạng bằng khoảng
cách cosine trên pgvector. Cùng chữ ký `studio_contracts.KbSearch`, khác hoàn toàn cơ chế.

**Hàng rào có hai trục, và chỉ một trục được RLS đỡ:**

| trục | ai chặn | ghi chú |
|---|---|---|
| `tenant` | **RLS** + `WHERE tenant_id` | policy `FORCE`, khoá theo `current_setting('app.tenant_id')` |
| `section_role` | **chỉ `WHERE section_role = ANY(...)`** | `schema.py` **không** có policy cho cột này |

Trục thứ hai không có lưới nào đỡ: mất mệnh đề `WHERE` là hở T6, im lặng.

Vì vậy `WHERE tenant_id` vẫn được viết ra dù RLS đã lo: RLS chỉ có tác dụng khi biến phiên
`app.tenant_id` đã được đặt. Một lần refactor quên `set_config` là fence bốc hơi im lặng; mệnh đề
tường minh giữ lại tầng thứ hai. Phòng thủ chiều sâu, không phải thừa.

**Còn thiếu so với contract đầy đủ (`search.py` docstring) — để S3:** `section_roles` ở đây dùng
**đúng giá trị bên gọi đưa xuống**, chưa phân giải server-side. Contract nói rõ giá trị client khai
là *yêu cầu*, không phải *sự cho phép* — nhưng chữ ký `search(query, tenant, section_roles, top_k)`
**không mang danh tính người gọi**, nên không có gì để phân giải từ đó. Đây là khoảng trống thật của
thiết kế v0, phải giải ở tầng phiên (S3), không vá được trong module này. Ghi ra để không ai đọc
nhầm là đã chặn T6 hoàn toàn.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence
from typing import TYPE_CHECKING, Any

from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool
from studio_contracts.kb import KbSearchResultItem
from studio_contracts.protocols import EmbeddingService

from studio_kb.doc_factory import Chunk
from studio_kb.schema import EMBEDDING_DIM

Pool = AsyncConnectionPool[AsyncConnection[Any]]

_UPSERT = """
INSERT INTO kb.chunks (chunk_id, tenant_id, section_role, text, embedding)
VALUES (%s, %s, %s, %s, %s::vector)
ON CONFLICT (chunk_id) DO UPDATE SET
    tenant_id    = EXCLUDED.tenant_id,
    section_role = EXCLUDED.section_role,
    text         = EXCLUDED.text,
    embedding    = EXCLUDED.embedding
"""

_SEARCH = """
SELECT chunk_id, text, 1 - (embedding <=> %s::vector) AS score, tenant_id, section_role
FROM kb.chunks
WHERE tenant_id = %s
  AND section_role = ANY(%s)
  AND embedding IS NOT NULL
ORDER BY embedding <=> %s::vector
LIMIT %s
"""


def _vector_literal(values: Sequence[float]) -> str:
    """Mã hoá vector thành literal pgvector `'[1.0,2.0,...]'`.

    Đi qua text + `::vector` thay vì dùng adapter của gói `pgvector`: thêm một dependency vào
    `packages/kb` sẽ làm hỏng `uv.lock` của repo cha, mà file đó DE chỉ có quyền đọc — phải mentor
    re-lock (GITFLOWS §2/§5). `repr` giữ đủ chữ số float, không làm tròn mất mát.
    """
    return "[" + ",".join(repr(float(v)) for v in values) + "]"


async def _bind_tenant(conn: AsyncConnection[Any], tenant: str) -> None:
    """Đặt `app.tenant_id` cho **giao dịch hiện tại** — đây là thứ kích hoạt RLS.

    Dùng `set_config(..., is_local => true)` thay vì `SET LOCAL`: `SET LOCAL` không nhận tham số
    nên phải nội suy chuỗi vào câu lệnh, còn `set_config` nhận binding bình thường. Tham số thứ ba
    `true` giới hạn phạm vi trong giao dịch, nên kết nối trả về pool không mang theo tenant cũ —
    nếu rò sang request sau thì fence hỏng theo kiểu khó lần ra nhất.
    """
    await conn.execute("SELECT set_config('app.tenant_id', %s, true)", (tenant,))


class KbIngest:
    """Đường ghi: `Chunk` (từ `doc_factory`) → embed → `kb.chunks`.

    Chạy qua pool **non-owner** (`studio_app`) có chủ đích: policy RLS có cả `WITH CHECK`, nên ghi
    một chunk mang `tenant_id` khác biến phiên sẽ bị chặn ngay tại DB. Ingest qua owner-pool sẽ mất
    lớp kiểm đó (FORCE RLS vẫn áp cho owner, nhưng owner là nơi người ta hay tắt fence "cho tiện").
    """

    def __init__(self, pool: Pool, embedding: EmbeddingService) -> None:
        self._pool = pool
        self._embedding = embedding

    async def ingest(self, chunks: Iterable[Chunk]) -> int:
        """Nạp/cập nhật chunk, trả về số dòng đã ghi.

        **Idempotent theo `chunk_id`** (`ON CONFLICT DO UPDATE`) — đây là điều kiện `re_index` bắt
        buộc ở `callisto-doc-schema.md` §6: chạy lại phải **giữ nguyên `chunk_id`**, nếu không mọi
        `expected_citation` trong golden-set trỏ vào hư không.

        Gom theo tenant rồi mỗi tenant một giao dịch: biến `app.tenant_id` là **một giá trị cho cả
        giao dịch**, nên không thể trộn hai tenant trong cùng một transaction — WITH CHECK sẽ chặn
        vế thứ hai. Đây là ràng buộc của fence, không phải chi tiết tối ưu.
        """
        by_tenant: dict[str, list[Chunk]] = defaultdict(list)
        for chunk in chunks:
            by_tenant[chunk.tenant].append(chunk)

        written = 0
        for tenant, batch in by_tenant.items():
            vectors = await self._embedding.embed([c.text for c in batch])
            if len(vectors) != len(batch):
                raise ValueError(f"embed() trả {len(vectors)} vector cho {len(batch)} chunk")
            for vector in vectors:
                if len(vector) != EMBEDDING_DIM:
                    # Fail-fast: cột là `vector(8)`, sai chiều thì Postgres cũng từ chối — nhưng báo
                    # ở đây chỉ ra ngay thủ phạm là EmbeddingService, không phải câu INSERT.
                    raise ValueError(f"embedding sai chiều: {len(vector)} != {EMBEDDING_DIM}")

            async with self._pool.connection() as conn, conn.transaction():
                await _bind_tenant(conn, tenant)
                for chunk, vector in zip(batch, vectors, strict=True):
                    await conn.execute(
                        _UPSERT,
                        (chunk.chunk_id, chunk.tenant, chunk.section_role, chunk.text, _vector_literal(vector)),
                    )
                    written += 1
        return written


class PgKbSearch:
    """Đường đọc: truy xuất vector trên `kb.chunks`, lọc fail-closed. Thoả `studio_contracts.KbSearch`."""

    def __init__(self, pool: Pool, embedding: EmbeddingService) -> None:
        self._pool = pool
        self._embedding = embedding

    async def search(
        self,
        query: str,
        tenant: str,
        section_roles: list[str],
        top_k: int,
    ) -> list[KbSearchResultItem]:
        """Trả `top_k` chunk gần `query` nhất theo cosine, **trong phạm vi `{tenant, section_roles}`**.

        Lọc nằm **trong câu SQL**, không phải lọc sau khi lấy về. `search.py` gọi thẳng tên cách làm
        sai: lấy hết rồi để LLM tự quyết là anti-pattern bị cấm — chunk ngoài phạm vi không được
        phép rời khỏi hàm này, kể cả để rồi bị bỏ đi ở tầng trên.

        `score` trả về là **độ tương đồng** cosine (`1 - khoảng cách`, càng lớn càng gần), khớp quy
        ước của `StaticKbSearch` — pgvector `<=>` cho **khoảng cách**, đảo dấu ở đây một lần để hai
        bản không mâu thuẫn nhau khi thay lẫn nhau.

        Rỗng là kết quả hợp lệ, không raise (`kb-search.v0.md` §6.1). `section_roles` rỗng nghĩa là
        **không có quyền nào** → trả `[]`, tuyệt đối không hiểu là "bỏ lọc".
        """
        if top_k <= 0 or not section_roles:
            return []

        vectors = await self._embedding.embed([query])
        if not vectors:
            return []
        literal = _vector_literal(vectors[0])

        async with self._pool.connection() as conn, conn.transaction():
            await _bind_tenant(conn, tenant)
            cursor = await conn.execute(_SEARCH, (literal, tenant, list(section_roles), literal, top_k))
            rows = await cursor.fetchall()

        return [
            KbSearchResultItem(chunk_id=row[0], text=row[1], score=float(row[2]), tenant=row[3], section_role=row[4])
            for row in rows
        ]


if TYPE_CHECKING:  # pragma: no cover
    from studio_contracts.kb import KbSearch

    # Cùng lý do như `static_search.py`: bắt drift chữ ký ngay tại kb thay vì để bên tiêu thụ vỡ.
    _protocol_conformance: KbSearch = PgKbSearch(pool=None, embedding=None)  # type: ignore[arg-type]
