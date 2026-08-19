"""Nạp corpus Callisto **2.0** vào `kb.chunks` per-tenant qua `KbPipeline`, bằng vector **THẬT**
(`gemini-embedding-001` @2048, DL-22.1) — cutover Phase C + PR-3 của `plans/real_embedding_plan.md`.

    # Cùng đường hạ tầng như ingest_callisto.py (1.0): pg sống + backend đã boot 1 lần (grant DML).
    docker compose up -d                                        # dev-stack, port 5432
    uv run python apps/studio/scripts/seed_demo_tenants.py      # tenants (owner-pool)
    # → khởi động backend apps/studio 1 lần (ensure_all_schemas + grant_app_privileges), rồi:
    export STUDIO_DATABASE_URL=postgresql://studio_app:changeme@localhost:5432/studio
    uv run python packages/kb/scripts/ingest_callisto_v2.py     # → ankor 400 · borea 400 · 800 chunk / 2 tenant
    # (Test/CI: docker-compose.test.yml port 5433/studio_test — harness tự apply grant.)

**KHÔNG cần API key.** Vector đọc từ cache đã commit (`tests/embedding-tests/cache/`, 800/800 chunk
2.0 có mặt), nên lệnh trên chạy được offline từ `main` — đúng INV-4 ("CI chạy 100% recorded
fixtures") và gạch "tái lập được" của `kb#38`.

Khác `ingest_callisto.py` (1.0) ở HAI chỗ, còn lại y hệt kỷ luật:
- **Nguồn**: `load_corpus_v2(docs/callisto-2.0/)` (80 doc / 800 chunk, role/doc_id từ tên file) thay
  cho `load_callisto()` (front-matter 1.0). `load_corpus_v2` là SSOT thư-mục→chunk, cùng `_cut_document`
  mà `KbPipeline.chunker` uỷ quyền — nên KHÔNG gọi `chunker` từng file lại (đó là entry 1-doc-lẻ).
- **Đường ghi**: `KbPipeline.embed_invoke` + `.index` (seam 2.0, tách embed khỏi index) thay cho
  `KbIngest.ingest`. Cùng `_UPSERT` + fence RLS `WITH CHECK`, cùng idempotency `ON CONFLICT DO UPDATE`.

## Pool **non-owner** + KHÔNG tự dựng schema (như 1.0)

Ghi qua `STUDIO_DATABASE_URL` (role `studio_app`) để vế `WITH CHECK` cắn — chunk mang `tenant_id` khác
biến phiên `app.tenant_id` bị DB từ chối ngay. DDL + grant là việc composition-root (`apps/studio
ensure_all_schemas`); script này CHỈ ghi dữ liệu, bảng chưa có thì lỗi phải nổi rõ.

## Vì sao KHÔNG còn `_FixtureEmbedding` (đổi ở PR-3)

Bản trước tiêm `_FixtureEmbedding` bọc `derive_vector` dim-8 làm mặc định, để đường ingest 2.0 đứng
được một mình trước khi có provider thật. Sau khi cột lên `vector(2048)` (PR-1), adapter đó trở
thành **cái bẫy**: mặc định của `derive_vector` bám `EMBEDDING_DIM` nên nó vẫn sinh vector 2048 chiều,
cột **nhận**, không lỗi nào nổ — và ta có 800 dòng bag-of-words nằm dưới cái nhãn
`gemini-embedding-001`, không phân biệt được bằng `count(*)` hay `vector_dims()`. Đó đúng lớp
"báo số của dim-8 dưới một cái nhãn khác" mà `MissingVectorError` được dựng ra để chặn.

Nên nó bị **xoá hẳn**, không phải hạ xuống làm phương án dự phòng: thiếu cache ⇒ `MissingVectorError`
nổ, tuyệt đối không rơi về một không gian vector khác. Test muốn tiêm double thì truyền tường minh
qua tham số `embedding`.

## Provider lấy từ `tests/embedding-tests/`, có chủ đích

`.importlinter` cấm `studio_kb` chạm `studio_app` (nơi giữ API key), và `VectorCache` neo `CACHE_DIR`
theo vị trí file của chính nó — chuyển module sang `src/studio_kb/` sẽ bỏ rơi blob cache 9 MB trừ khi
lôi cả nó vào wheel production. Một dòng `sys.path` trong script là cái giá rẻ hơn nhiều. Đây là
**dụng cụ đo dùng cho ingest**; bản production cho đường TRUY VẤN (`/chat`, `/runs`, `/publish`) là
PR-2, lane AIE-1 — xem `plans/real_embedding_plan.md` §5.1b.
"""

from __future__ import annotations

import asyncio
import os
import sys
from collections import Counter
from pathlib import Path
from uuid import UUID

from psycopg_pool import AsyncConnectionPool
from studio_contracts.protocols import EmbeddingService
from studio_kb.doc_factory_v2 import load_corpus_v2
from studio_kb.pipeline import KbPipeline
from studio_kb.postgres import Pool, _bind_tenant

_DSN_ENV = "STUDIO_DATABASE_URL"
_KB_ROOT = Path(__file__).resolve().parents[1]
CORPUS_2_0 = _KB_ROOT / "docs" / "callisto-2.0"

sys.path.insert(0, str(_KB_ROOT / "tests" / "embedding-tests"))
from providers import GeminiEmbedding  # noqa: E402  (phải sau khi vá sys.path ở trên)


class CachedGeminiEmbedding:
    """`EmbeddingService` bọc `providers.GeminiEmbedding` — vector THẬT, đọc từ cache đã commit.

    Hai việc lớp này làm, cả hai đều cần thiết:

    1. **Bắc cầu đồng bộ → bất đồng bộ.** `GeminiEmbedding.embed` là `def` thường (nó sinh ra cho
       script đo), còn `studio_contracts.protocols.EmbeddingService` đòi `async embed`. Không có
       lớp này thì `await` trong `KbPipeline.embed_invoke` rơi vào một `list`, nổ ở chỗ khó đọc.
    2. **Khoá `allow_network=False`.** Ingest đọc cache, không gọi API: chạy lại phải ra đúng vector
       cũ, và không lần chạy nào âm thầm tốn tiền. Thiếu text trong cache ⇒ `MissingVectorError`
       (fail-closed), KHÔNG rơi về provider khác.

    Gọi bọc trong `asyncio.to_thread` dù đường hiện tại thuần CPU (tra cache): nếu ai đó bật
    `allow_network=True` thì `urllib` chặn luồng sẽ treo cả event loop.
    """

    def __init__(self, *, allow_network: bool = False) -> None:
        self._inner = GeminiEmbedding(allow_network=allow_network)
        self.name = self._inner.name

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return await asyncio.to_thread(self._inner.embed, texts)


async def purge_tenants(pool: Pool, tenant_ids: list[UUID]) -> int:
    """Xoá sạch chunk của từng tenant TRƯỚC khi nạp lại. Trả số dòng đã xoá.

    **Vì sao cần**, dù PR-1 đã có `TRUNCATE` trong migration: khối đó **có điều kiện**, chỉ chạy khi
    chiều cột lệch. Nạp lại lần thứ hai trên DB đã đúng chiều thì nó không chạy, và `index` dùng
    `ON CONFLICT DO UPDATE` — upsert chỉ đụng `chunk_id` trùng. `chunk_id` 1.0 (`ankor-access-001#c1`)
    và 2.0 không trùng nhau, nên không có upsert nào dọn được dòng 1.0 còn sót.

    **Vì sao `DELETE` theo từng tenant chứ không `TRUNCATE`** — đã đo trên DB thật, không phải suy:
    `TRUNCATE` đòi quyền sở hữu bảng, mà script chạy bằng `studio_app` (non-owner) ⇒
    `permission denied for table chunks`. Còn `DELETE` **không** ràng buộc tenant thì gặp policy RLS
    `USING (tenant_id = app.tenant_id)`: biến phiên chưa đặt ⇒ khớp 0 dòng, xoá 0 dòng **trong im
    lặng**. Ràng buộc bằng `_bind_tenant` (đúng hàm mà `KbIngest`/`KbPipeline` dùng) thì `DELETE`
    xoá đúng phần của tenant đó — đã kiểm: `DELETE 1`.

    Mỗi tenant một giao dịch, cùng lý do như `KbIngest.ingest`: `app.tenant_id` là một giá trị cho
    cả giao dịch, không trộn hai tenant trong một transaction được.
    """
    deleted = 0
    for tenant_id in tenant_ids:
        async with pool.connection() as conn, conn.transaction():
            await _bind_tenant(conn, tenant_id)
            cursor = await conn.execute("DELETE FROM kb.chunks")
            deleted += cursor.rowcount
    return deleted


async def ingest_all(pool: Pool, embedding: EmbeddingService | None = None, *, purge: bool = False) -> int:
    """Nạp toàn bộ corpus 2.0 vào `kb.chunks` qua `KbPipeline` trên `pool` (non-owner). Trả số chunk ghi.

    Tách khỏi `main()` để test gọi được với pool của fixture (đã mở, đúng role) + tiêm embedding riêng,
    không phải dựng lại DSN/pool. `index` idempotent (`ON CONFLICT`) nên chạy lại an toàn.

    `embedding=None` ⇒ **provider THẬT** (`CachedGeminiEmbedding`), không phải một double dim-8. Xem
    "Vì sao KHÔNG còn `_FixtureEmbedding`" ở docstring module: mặc định rơi về bag-of-words là con
    đường tạo ra 800 dòng sai-nghĩa mà `count(*)`/`vector_dims()` không phân biệt được.

    `purge=False` mặc định để `ingest_all` giữ đúng tính idempotent mà `test_ingest_script_v2` canh
    (chạy lại vẫn 800, không nhân đôi). `main()` bật `purge=True` — nạp từ CLI là nạp LẠI, và phải
    dọn cả chunk 1.0 còn sót.
    """
    chunks = load_corpus_v2(CORPUS_2_0)
    if purge:
        removed = await purge_tenants(pool, sorted({c.tenant_id for c in chunks}))
        print(f"đã xoá {removed} chunk cũ (gồm cả corpus 1.0 nếu còn sót)")

    pipe = KbPipeline(pool, embedding or CachedGeminiEmbedding())
    await pipe.index(chunks, await pipe.embed_invoke(chunks))

    per_tenant = Counter(c.chunk_id.split("-", 1)[0] for c in chunks)
    for tenant in sorted(per_tenant):
        print(f"  {tenant}: {per_tenant[tenant]} chunk")
    print(f"đã ingest {len(chunks)} chunk / {len(per_tenant)} tenant vào kb.chunks (corpus 2.0)")
    return len(chunks)


async def _run(dsn: str) -> int:
    pool = AsyncConnectionPool(dsn, min_size=1, max_size=4, open=False)
    await pool.open(wait=True, timeout=10)
    try:
        return await ingest_all(pool, purge=True)
    finally:
        await pool.close()


def main() -> None:
    dsn = os.environ.get(_DSN_ENV)
    if not dsn:
        raise SystemExit(
            f"{_DSN_ENV} chưa đặt — cần pg sống + backend đã boot 1 lần (cấp grant DML cho "
            "studio_app). Đường chuẩn: kit README §'Các bước' (dev-stack). Tối thiểu:\n"
            "  docker compose up -d\n"
            f"  export {_DSN_ENV}=postgresql://studio_app:changeme@localhost:5432/studio"
        )
    asyncio.run(_run(dsn))


if __name__ == "__main__":
    main()
