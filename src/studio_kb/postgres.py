"""Tầng lưu trữ Postgres thật cho `kb.chunks` — ingest (ghi) + truy xuất vector (đọc).

**HAI TẦNG — seam chính thức ĐÃ lật ở D17 (#110).**
- **Impl cụ thể `PgKbSearch` ĐÃ nằm trên spine thật kể từ D13:** composition-root `apps/studio` tiêm
  thẳng `PgKbSearch(pool, embedding)` vào `KbRetrieveExecutor` của AIE-1 trên đường ghép thật
  (`apps/studio/tests/test_spine_scored_from_postgres.py`, `apps/studio/scripts/e2e_smoke_eval.py`).
  Trong unit-test thuần engine, executor nhận `EmptyKbSearch` (luôn `[]`); `StaticKbSearch` (v0 S1,
  D4) **vẫn được lane workbench tiêm vào `run(...)`** ở `packages/workbench/tests/test_wiring_d6.py`
  (đường ghép **không-Postgres**) + dùng nội bộ kb (annotate golden / `test_static_search`) — nó
  **KHÔNG nằm trên spine Postgres** (đường đó dùng `PgKbSearch`).
- **Seam CHÍNH THỨC `KbSearchService` (`search.py`) nay uỷ quyền một dòng sang `PgKbSearch.search`**
  (D17): đường vào chính thức chạy đúng cơ chế fence dưới đây. `test_leak.py::test_t1_idor` là gate
  cứng (đã gỡ `xfail`); `test_search_contract.py` đã xoá (nó khẳng định seam kia raise). `KbPipeline`
  (`pipeline.py`) vẫn `NotImplementedError` (spec DE cho sau).

`KbSearchService` cấp thêm embedding stub mặc định khi không được tiêm (để `KbSearchService(pool)` ở
T3 chạy được, QĐ-U1) — xem docstring `search.py`. Đường đọc thật, fence, sống ở `PgKbSearch` dưới đây.

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
from uuid import UUID

from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool
from studio_contracts.kb import KbSearchResultItem
from studio_contracts.protocols import EmbeddingService

from studio_kb.doc_factory import Chunk
from studio_kb.schema import EMBEDDING_DIM

Pool = AsyncConnectionPool[AsyncConnection[Any]]

_UPSERT = """
INSERT INTO kb.chunks (chunk_id, tenant_id, section_role, text, embed_text, embedding)
VALUES (%s, %s, %s, %s, %s, %s::vector)
ON CONFLICT (chunk_id) DO UPDATE SET
    tenant_id    = EXCLUDED.tenant_id,
    section_role = EXCLUDED.section_role,
    text         = EXCLUDED.text,
    embed_text   = EXCLUDED.embed_text,
    embedding    = EXCLUDED.embedding
"""
"""`embed_text` lưu ĐÚNG chuỗi đã đem embed (`Chunk.embedding_input`), không phải một biến thể.

Bất biến: **cột `embed_text` luôn là đầu vào đã sinh ra cột `embedding` cạnh nó.** Nhờ vậy
`KbPipeline.re_index` — vốn dựng lại `Chunk` TỪ DB — tái lập được đúng vector: tiêu đề tài liệu và
việc đã cắt boilerplate không suy lại được từ `text` của một dòng đơn lẻ. Không lưu cột này thì mỗi
vòng re-index âm thầm đổi vector của mọi chunk mà không `chunk_id` nào chết."""

_SEARCH = """
SELECT chunk_id, text, 1 - (embedding <=> %s::vector) AS score, tenant_id, section_role
FROM kb.chunks
WHERE tenant_id = %s
  AND section_role = ANY(%s)
  AND embedding IS NOT NULL
ORDER BY embedding <=> %s::vector
LIMIT %s
"""
"""Toán tử PHẢI là `<=>` (cosine distance), **không được** đổi sang `<#>` (inner product) cho nhanh.

`<=>` tự chia cho tích hai norm nên thứ hạng đúng kể cả khi vector CHƯA chuẩn hoá; `<#>` thì không.
Đây không phải lo xa: provider mặc định `gemini-embedding-001` (DL-22.1) chạy ở 2048 chiều, mà docs
Google nói rõ chỉ có bản 3072 gốc mới được chuẩn hoá sẵn — cắt Matryoshka xuống 2048 trả về vector
chưa chuẩn hoá. `GeminiEmbedding.embed()` đã L2-normalize trước khi ghi cache như lớp phòng thủ thứ
nhất, nhưng một provider tương lai quên bước đó cộng với `<#>` ở đây sẽ cho thứ hạng sai **hoàn toàn
im lặng** — không exception, không test đỏ, chỉ là kết quả tệ đi."""


def _vector_literal(values: Sequence[float]) -> str:
    """Mã hoá vector thành literal pgvector `'[1.0,2.0,...]'`.

    Đi qua text + `::vector` thay vì dùng adapter của gói `pgvector`: thêm một dependency vào
    `packages/kb` sẽ làm hỏng `uv.lock` của repo cha, mà file đó DE chỉ có quyền đọc — phải mentor
    re-lock (GITFLOWS §2/§5). `repr` giữ đủ chữ số float, không làm tròn mất mát.
    """
    return "[" + ",".join(repr(float(v)) for v in values) + "]"


async def _bind_tenant(conn: AsyncConnection[Any], tenant_id: UUID) -> None:
    """Đặt `app.tenant_id` cho **giao dịch hiện tại** — đây là thứ kích hoạt RLS.

    Dùng `set_config(..., is_local => true)` thay vì `SET LOCAL`: `SET LOCAL` không nhận tham số
    nên phải nội suy chuỗi vào câu lệnh, còn `set_config` nhận binding bình thường. Tham số thứ ba
    `true` giới hạn phạm vi trong giao dịch, nên kết nối trả về pool không mang theo tenant cũ —
    nếu rò sang request sau thì fence hỏng theo kiểu khó lần ra nhất.

    **Truyền `str(tenant_id)`, không phải object `UUID`.** `set_config(name, value, is_local)` nhận
    `value` kiểu **text**; psycopg sẽ adapt một `UUID` thành tham số kiểu `uuid`, và Postgres không
    tìm thấy `set_config(text, uuid, bool)` → lỗi phân giải hàm. Phía policy mới cast ngược lại
    `::uuid` (xem `schema.py`), nên biến phiên là text còn cột so sánh là uuid — khớp sau cast.
    """
    await conn.execute("SELECT set_config('app.tenant_id', %s, true)", (str(tenant_id),))


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
        by_tenant: dict[UUID, list[Chunk]] = defaultdict(list)
        for chunk in chunks:
            by_tenant[chunk.tenant_id].append(chunk)

        written = 0
        for tenant_id, batch in by_tenant.items():
            vectors = await self._embedding.embed([c.embedding_input for c in batch])
            if len(vectors) != len(batch):
                raise ValueError(f"embed() trả {len(vectors)} vector cho {len(batch)} chunk")
            for vector in vectors:
                if len(vector) != EMBEDDING_DIM:
                    # Fail-fast: cột là `vector(8)`, sai chiều thì Postgres cũng từ chối — nhưng báo
                    # ở đây chỉ ra ngay thủ phạm là EmbeddingService, không phải câu INSERT.
                    raise ValueError(f"embedding sai chiều: {len(vector)} != {EMBEDDING_DIM}")

            async with self._pool.connection() as conn, conn.transaction():
                await _bind_tenant(conn, tenant_id)
                for chunk, vector in zip(batch, vectors, strict=True):
                    await conn.execute(
                        _UPSERT,
                        (
                            chunk.chunk_id,
                            chunk.tenant_id,
                            chunk.section_role,
                            chunk.text,
                            chunk.embedding_input,
                            _vector_literal(vector),
                        ),
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
        tenant_id: UUID,
        section_roles: list[str],
        top_k: int,
    ) -> list[KbSearchResultItem]:
        """Trả `top_k` chunk gần `query` nhất theo cosine, **trong phạm vi `{tenant_id, section_roles}`**.

        `tenant_id` là **UUID** (D-13). RLS khoá theo `app.tenant_id` (biến phiên đặt bằng
        `_bind_tenant`), còn `WHERE tenant_id = %s` vẫn viết ra tường minh — xem đầu module vì sao
        cả hai cùng tồn tại.

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
            await _bind_tenant(conn, tenant_id)
            cursor = await conn.execute(_SEARCH, (literal, tenant_id, list(section_roles), literal, top_k))
            rows = await cursor.fetchall()

        # `row[3]` là `tenant_id` từ cột UUID → psycopg trả về object `UUID`, khớp thẳng contract.
        return [
            KbSearchResultItem(chunk_id=row[0], text=row[1], score=float(row[2]), tenant_id=row[3], section_role=row[4])
            for row in rows
        ]


if TYPE_CHECKING:  # pragma: no cover
    from studio_contracts.kb import KbSearch

    # Cùng lý do như `static_search.py`: bắt drift chữ ký ngay tại kb thay vì để bên tiêu thụ vỡ.
    _protocol_conformance: KbSearch = PgKbSearch(pool=None, embedding=None)  # type: ignore[arg-type]
