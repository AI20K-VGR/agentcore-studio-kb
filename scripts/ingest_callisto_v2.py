"""Nạp corpus Callisto **2.0** vào `kb.chunks` per-tenant qua `KbPipeline` (cutover Phase C, DE).

    # Cùng đường hạ tầng như ingest_callisto.py (1.0): pg sống + backend đã boot 1 lần (grant DML).
    docker compose up -d                                        # dev-stack, port 5432
    uv run python apps/studio/scripts/seed_demo_tenants.py      # tenants (owner-pool)
    # → khởi động backend apps/studio 1 lần (ensure_all_schemas + grant_app_privileges), rồi:
    export STUDIO_DATABASE_URL=postgresql://studio_app:changeme@localhost:5432/studio
    uv run python packages/kb/scripts/ingest_callisto_v2.py     # → ankor 400 · borea 400 · 800 chunk / 2 tenant
    # (Test/CI: docker-compose.test.yml port 5433/studio_test — harness tự apply grant.)

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

## `EmbeddingService` **cục bộ** dim-8 (tạm) — bản thật là AIE-1

`_FixtureEmbedding` bọc `derive_vector` (dim-8) để đường ingest 2.0 **đứng một mình** ngay hôm nay,
không chờ engine AIE-1. Đây KHÔNG phải EmbeddingService công khai (protocol ghi *"Owner impl: AIE-1"*).
Khi bản thật của AIE-1 chạy, chỉ **đổi chỗ tiêm** ở dòng `KbPipeline(pool, <embedding>)` — không đụng
phần còn lại. ⚠️ dim-8 là *known-bad* cho 800 chunk (đụng độ băm — xem `plans/callisto-2.0-cutover.md`
§2): đủ để CHỨNG MINH đường ghi thông, KHÔNG phải chất lượng ranking (rank-verify hoãn parity gate).
"""

from __future__ import annotations

import asyncio
import os
from collections import Counter
from pathlib import Path

from psycopg_pool import AsyncConnectionPool
from studio_contracts.protocols import EmbeddingService
from studio_kb.doc_factory_v2 import load_corpus_v2
from studio_kb.embeddings import derive_vector
from studio_kb.pipeline import KbPipeline
from studio_kb.postgres import Pool

_DSN_ENV = "STUDIO_DATABASE_URL"
CORPUS_2_0 = Path(__file__).resolve().parents[1] / "docs" / "callisto-2.0"


class _FixtureEmbedding:
    """`EmbeddingService` tất định cục bộ (bọc `derive_vector` dim-8). Adapter tạm, KHÔNG phải
    EmbeddingService công khai — `EmbeddingService` do AIE-1 sở hữu (xem docstring module)."""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [derive_vector(t) for t in texts]


async def ingest_all(pool: Pool, embedding: EmbeddingService | None = None) -> int:
    """Nạp toàn bộ corpus 2.0 vào `kb.chunks` qua `KbPipeline` trên `pool` (non-owner). Trả số chunk ghi.

    Tách khỏi `main()` để test gọi được với pool của fixture (đã mở, đúng role) + tiêm embedding riêng,
    không phải dựng lại DSN/pool. `index` idempotent (`ON CONFLICT`) nên chạy lại an toàn."""
    chunks = load_corpus_v2(CORPUS_2_0)
    pipe = KbPipeline(pool, embedding or _FixtureEmbedding())
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
