"""Nạp corpus Callisto vào `kb.chunks` per-tenant (D13, DE) — biến `KbIngest` từ *có class* thành
*có lệnh chạy được*.

    # Chạy tay = kit README §"Các bước" (dev-stack, port 5432). BẮT BUỘC backend apps/studio đã boot
    # MỘT LẦN trước: lifespan của nó cấp grant DML cho studio_app (xem "Không tự dựng schema" dưới) —
    # chạy trước đó sẽ gãy "permission denied for schema kb".
    docker compose up -d                                       # dev-stack, port 5432
    uv run python apps/studio/scripts/seed_demo_tenants.py     # tenants (owner-pool)
    # → khởi động backend apps/studio 1 lần (ensure_all_schemas + grant_app_privileges), rồi:
    export STUDIO_DATABASE_URL=postgresql://studio_app:changeme@localhost:5432/studio
    uv run python packages/kb/scripts/ingest_callisto.py       # → ankor 71 · borea 69 · 140 chunk / 2 tenant
    # (Test/CI: test-stack riêng docker-compose.test.yml port 5433/studio_test — harness tự apply grant.)

Đây là DoD "KB ingest→embed→index per-tenant **chạy**": `load_callisto()` (42 doc / 140 chunk) →
embed → `kb.chunks`, gom theo tenant. Idempotent — chạy lại không nhân đôi (`KbIngest` dùng
`ON CONFLICT DO UPDATE`), nên an toàn để lặp trong demo và trong test.

## Vì sao pool **non-owner** (`STUDIO_DATABASE_URL`, role `studio_app`), KHÔNG phải admin

`kb.chunks` có `FORCE ROW LEVEL SECURITY` với cả `WITH CHECK` (`schema.py`). Ghi qua non-owner là
điều kiện để vế `WITH CHECK` **cắn** — một chunk mang `tenant_id` khác biến phiên `app.tenant_id` bị
DB từ chối ngay. Ingest qua owner-pool sẽ đi lọt và ta mất đúng lớp kiểm mà cả pipeline này tồn tại
để có. `KbIngest` tự đặt `app.tenant_id` mỗi giao dịch (một tenant / một transaction), nên chỉ cần
đưa nó một pool non-owner đã mở.

**Không tự dựng schema ở đây.** DDL + grant là việc của composition-root
(`apps/studio ... ensure_all_schemas` qua owner-pool, xem `schema.py` docstring). Script này chỉ
GHI DỮ LIỆU; nếu bảng chưa tồn tại thì lỗi phải nổi lên rõ ("bảng chưa dựng"), không phải im lặng
tự vá bằng quyền owner mà script này cố ý không có.

## Vì sao adapter embedding **cục bộ**, KHÔNG export một `EmbeddingService`

`studio_contracts.protocols.EmbeddingService` ghi rõ *"Owner impl: AIE-1"*. DE không ship một
EmbeddingService cạnh tranh vào seam công khai. Nhưng để nạp DB **đứng một mình** (không chờ engine
của AIE-1), script cần *một cái gì đó* thoả protocol. `_FixtureEmbedding` dưới đây là adapter
cục bộ bọc `derive_vector` — **cùng công thức** `golden/embeddings-callisto-v0.json` được ghi ra
(xem `embeddings.py`), nên vector nạp vào `kb.chunks` khớp từng số với fixture, và khớp với vector
truy vấn khi `PgKbSearch` embed câu hỏi bằng cùng hàm. Đây đúng là mẫu `test_pg_kb.py` đã dùng
(`BagOfWordsEmbedding` cục bộ trong test), không phải một nguồn sự thật mới.

Khi engine của AIE-1 (#91) chạy thật, EmbeddingService của AIE-1 là chỗ tiêm ở composition; adapter
này chỉ phục vụ đường ingest standalone của DE.

## Vì sao script chứ không `python -m`

`studio_kb/__init__.py` import sẵn nhiều module con, nên `-m studio_kb.xxx` nạp module hai lần và
Python cảnh báo `RuntimeWarning`. Logic ở lại trong package để test import được; chỉ phần gọi (mở
pool, `asyncio.run`) nằm đây. Cùng lý do đã ghi ở `record_embeddings.py`.
"""

from __future__ import annotations

import asyncio
import os
from collections import Counter

from psycopg_pool import AsyncConnectionPool
from studio_kb.doc_factory import load_callisto
from studio_kb.embeddings import derive_vector
from studio_kb.postgres import KbIngest

_DSN_ENV = "STUDIO_DATABASE_URL"


class _FixtureEmbedding:
    """`EmbeddingService` tất định cục bộ (bọc `derive_vector`). Xem docstring module vì sao adapter
    này KHÔNG phải một EmbeddingService công khai — `EmbeddingService` do AIE-1 sở hữu."""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [derive_vector(t) for t in texts]


async def ingest_all(pool: AsyncConnectionPool) -> int:
    """Nạp toàn bộ corpus Callisto vào `kb.chunks` qua `pool` (non-owner). Trả về số dòng đã ghi.

    Tách khỏi `main()` để `tests/test_ingest_script.py` gọi được với pool của fixture (đã mở, đúng
    role) mà không phải dựng lại DSN/pool riêng."""
    chunks = load_callisto()
    per_tenant = Counter(c.chunk_id.split("-", 1)[0] for c in chunks)
    written = await KbIngest(pool, _FixtureEmbedding()).ingest(chunks)
    for tenant in sorted(per_tenant):
        print(f"  {tenant}: {per_tenant[tenant]} chunk")
    print(f"đã ingest {written} chunk / {len(per_tenant)} tenant vào kb.chunks")
    return written


async def _run(dsn: str) -> int:
    pool = AsyncConnectionPool(dsn, min_size=1, max_size=4, open=False)
    await pool.open(wait=True, timeout=10)
    try:
        return await ingest_all(pool)
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
