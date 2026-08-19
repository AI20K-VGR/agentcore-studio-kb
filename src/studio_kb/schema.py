"""kb.* schema DDL seam (schema-per-quadrant, Decision #4).

`ensure_all_schemas()` (apps/studio/src/studio_app/core/schema.py, Phase 3) direct-imports this
module and calls `ddl()` via the ADMIN (`studio_owner`) pool — that ownership is what lets `FORCE
ROW LEVEL SECURITY` below bite the owner too, instead of the owner silently bypassing the fence.

Fence mechanism (F10, plan.md Decision #3): `ENABLE`+`FORCE ROW LEVEL SECURITY` plus a policy with
BOTH `USING` (reads) and `WITH CHECK` (writes) keyed off
`NULLIF(current_setting('app.tenant_id', true), '')::uuid` — three layers, each fail-closed:
  - `current_setting(..., true)` — the `true` makes an UNSET session resolve to `NULL`, not raise;
  - `NULLIF(..., '')` — a session set to the EMPTY STRING (some set-paths produce `''`, not NULL)
    also collapses to `NULL`, because `''::uuid` would otherwise RAISE (loud, but wrong kind of
    loud — a fence must return 0 rows, not throw a 500 at the user);
  - `::uuid` — cast the text session var to `uuid` so it compares against the `uuid` column (D-13).
`tenant_id = NULL` is never true in SQL, so an unset/empty session sees/writes 0 rows (fail-closed,
not "everything"). `CREATE EXTENSION vector` is deliberately NOT here — it runs once, as the
`postgres` superuser, from `docker/postgres-init/01-extensions.sql` (Phase 3): both `studio_owner`
and `studio_app` are `NOSUPERUSER` and cannot create extensions at boot.

`tenant_id` is `UUID` (D-13 / DEC-B): tenant identity is the immutable `core.tenants.id`, never a
human-collidable slug. The producer (middleware) resolves a header slug → UUID before binding
`app.tenant_id`; ingest binds `str(tenant_id)` (see `postgres.py::_bind_tenant`).
"""

from __future__ import annotations

# Embedding vector dimension — pinned HERE (not in apps/studio) because quadrant packages may
# import ONLY `studio_contracts` (.importlinter layers-contract) and must never import
# `studio_app`. Đây là **chiều của cột** `kb.chunks.embedding`, không phải chiều của fixture đã
# ghi: `embeddings.FIXTURE_DIM` giữ riêng con số 8 của `golden/embeddings-callisto-v0.json`
# (bản ghi của thế giới 1.0 — xem DL-22.5).
#
# `.importlinter` cấm import chéo nên KHÔNG có cơ chế tự động so hằng số này với các bản khai lại
# bằng tay ở nơi khác. Nợ có ý thức: đổi ở đây thì phải đổi TAY cùng lúc cả bốn chỗ dưới `[PRIOR]`
#   - packages/engine/tests/test_embedding_service_contract.py::EXPECTED_DIM
#   - packages/engine/tests/fixtures/embedding/smoke-01.json      (vector replay, phải re-record)
#   - packages/engine/src/.../demo_stubs.py::StubEmbedding        (docstring "width fixed at 8")
#   - apps/studio/src/studio_app/providers/fakes.py::FakeEmbedding.dim
#
# 2048 chỉ hợp lệ VÌ không còn index HNSW (trần 2000) — xem `_KB_DDL` bên dưới. Hai con số khoá
# vào nhau; ai bật lại index phải hạ chiều xuống ≤2000 và đo lại.
EMBEDDING_DIM = 2048

_KB_DDL = f"""
CREATE SCHEMA IF NOT EXISTS kb;

CREATE TABLE IF NOT EXISTS kb.chunks (
    chunk_id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    tenant_id UUID NOT NULL,
    section_role TEXT NOT NULL,
    text TEXT NOT NULL,
    embed_text TEXT,
    embedding vector({EMBEDDING_DIM}),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- `CREATE TABLE IF NOT EXISTS` ở trên KHÔNG thêm cột vào bảng đã tồn tại, nên DB cũ phải được vá
-- riêng — không có dòng này thì mọi môi trường đã chạy trước đây sẽ đỏ ở `_UPSERT` với "column
-- embed_text does not exist". NULL cho dòng cũ là đúng: `re_index` rơi về `text` y như trước.
ALTER TABLE kb.chunks ADD COLUMN IF NOT EXISTS embed_text TEXT;

-- KHÔNG dựng index HNSW trên `embedding` (DL-22.2). Ba lý do, đầy đủ ở
-- `plans/real_embedding_plan.md` §2:
--   1. ở 800 chunk brute force là 800 phép cosine (đo được p50 2.03ms · p95 4.24ms · max 8.07ms
--      trên `vector(2048)`, `EXPLAIN` xác nhận Seq Scan) — HNSW sinh ra cho hàng triệu vector;
--   2. HNSW là ANN **xấp xỉ**, sẽ làm production mất recall mà harness eval (cosine chính xác)
--      KHÔNG mô phỏng — chênh lệch đó vô hình, đúng thứ đang được đo;
--   3. trần 2000 chiều của HNSW chặn `EMBEDDING_DIM = 2048`.
-- **Ngưỡng làm quyết định này hết đúng:** khoảng ~10⁵–10⁶ chunk, seq scan sập và index quay lại —
-- lúc đó trần 2000 quay lại theo, và chiều phải hạ xuống 1536 (nấc MRL gần nhất) + đo lại toàn bộ.
-- Ngừng `CREATE` là chưa đủ: DB đã chạy trước đây vẫn còn index cũ, nên phải xoá tường minh.
DROP INDEX IF EXISTS kb.kb_chunks_embedding_hnsw_idx;

-- Migration chiều cột — `CREATE TABLE IF NOT EXISTS` ở trên KHÔNG đổi cột của bảng đã tồn tại,
-- nên đổi `EMBEDDING_DIM` mà không có khối này thì cột vẫn giữ chiều cũ: fail-fast của
-- `pipeline.py`/`postgres.py` so với hằng số MỚI nên lọt, rồi lỗi rơi xuống Postgres dưới dạng
-- "expected N dimensions". Có điều kiện (`<>`) nên boot bình thường không đụng gì.
--
-- TRUNCATE chứ không `ALTER ... USING`: vector cũ nằm ở KHÔNG GIAN khác (provider khác, chiều
-- khác), ép kiểu chỉ tạo ra số đúng-định-dạng-sai-nghĩa. Mọi chunk PHẢI được embed lại
-- (`scripts/ingest_callisto_v2.py`). TRUNCATE cũng là đường duy nhất xoá sạch được ở đây:
-- `FORCE ROW LEVEL SECURITY` bên dưới fence cả owner, nên `DELETE` không có `app.tenant_id`
-- sẽ xoá 0 dòng **im lặng** rồi ALTER vỡ.
DO $$
DECLARE
    cur_dim int;
BEGIN
    SELECT atttypmod INTO cur_dim
      FROM pg_attribute
     WHERE attrelid = 'kb.chunks'::regclass AND attname = 'embedding' AND NOT attisdropped;

    IF cur_dim IS NOT NULL AND cur_dim <> {EMBEDDING_DIM} THEN
        RAISE NOTICE 'kb.chunks.embedding: vector(%) -> vector(%); TRUNCATE + re-ingest bắt buộc',
                     cur_dim, {EMBEDDING_DIM};
        TRUNCATE TABLE kb.chunks;
        ALTER TABLE kb.chunks ALTER COLUMN embedding TYPE vector({EMBEDDING_DIM});
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS kb_chunks_tenant_id_idx ON kb.chunks (tenant_id);

ALTER TABLE kb.chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE kb.chunks FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS kb_chunks_tenant_isolation ON kb.chunks;
CREATE POLICY kb_chunks_tenant_isolation ON kb.chunks
    USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
"""


def ddl() -> str:
    """Return this quadrant's idempotent DDL — safe to execute any number of times (`CREATE ...
    IF NOT EXISTS` throughout; the policy is `DROP ... IF EXISTS` then recreated identically)."""
    return _KB_DDL
