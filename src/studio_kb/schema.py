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
-- `USING NULL` — GIỮ DÒNG, chỉ bỏ vector. Bản đầu (kb#43) dùng `TRUNCATE` và **đó là sai**; sửa
-- ở kb#44 sau review AIE-2. Lập luận cũ ("vector cũ ở không gian khác, phải embed lại hết") vẫn
-- đúng cho phần VECTOR, nhưng nó không kéo theo việc xoá `text`/`embed_text` — và hai cột đó là
-- thứ duy nhất không dựng lại được:
--
--   * `scripts/ingest_callisto_v2.py` dựng lại được 800 chunk corpus Callisto từ `docs/`;
--   * tài liệu **tenant tự upload** (`POST /api/admin/documents`, app#27) thì KHÔNG — route đó
--     chunk/embed/index thẳng vào bảng này và **không lưu file gốc ở đâu khác** (`core` schema
--     chỉ có tenants·users·sections·jobs·outbox, không bảng nào giữ blob). `kb.chunks` là **bản
--     sao duy nhất**. `TRUNCATE` ở đây là mất vĩnh viễn, không có đường phục hồi trong repo.
--
-- Sau `USING NULL`, dòng còn nguyên với `embedding IS NULL`, và trạng thái đó **đã được thiết kế
-- sẵn**: `_SEARCH` (postgres.py) lọc `AND embedding IS NOT NULL`, nên chunk chưa có vector không
-- bao giờ lọt vào kết quả — hạ cấp sạch, không phải rác. Dựng lại vector bằng
-- `KbPipeline.re_index(tenant_id)`: nó đọc `embed_text` **từ DB** nên không cần file gốc.
--
-- Vì sao migration KHÔNG tự gọi `re_index`: `re_index` cần một `EmbeddingService`, mà DDL thì
-- không có khe tiêm nào — `ensure_all_schemas()` chỉ thực thi chuỗi SQL. Hai tầng, hai việc:
-- DDL lo CẤU TRÚC, người vận hành lo DỮ LIỆU.
DO $$
DECLARE
    cur_dim  int;
    n_chunk  bigint;
BEGIN
    SELECT atttypmod INTO cur_dim
      FROM pg_attribute
     WHERE attrelid = 'kb.chunks'::regclass AND attname = 'embedding' AND NOT attisdropped;

    IF cur_dim IS NOT NULL AND cur_dim <> {EMBEDDING_DIM} THEN
        -- Đếm TRƯỚC khi đổi: con số này là thứ người vận hành cần để biết phải re_index bao nhiêu.
        -- `count(*)` chạy dưới owner-pool nhưng `FORCE RLS` fence cả owner, nên nó chỉ thấy dòng
        -- của `app.tenant_id` hiện tại (thường chưa đặt ⇒ 0). Dùng `pg_class.reltuples` (ước lượng
        -- của planner, không qua RLS) để con số phản ánh CẢ BẢNG.
        SELECT GREATEST(reltuples, 0)::bigint INTO n_chunk
          FROM pg_class WHERE oid = 'kb.chunks'::regclass;

        RAISE WARNING 'kb.chunks.embedding: vector(%) -> vector(%). ~% chunk MẤT VECTOR (dòng giữ '
                      'nguyên, embedding := NULL) và sẽ KHÔNG truy xuất được cho tới khi chạy '
                      'KbPipeline.re_index(tenant_id) hoặc scripts/ingest_callisto_v2.py.',
                      cur_dim, {EMBEDDING_DIM}, n_chunk;

        ALTER TABLE kb.chunks ALTER COLUMN embedding TYPE vector({EMBEDDING_DIM}) USING NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS kb_chunks_tenant_id_idx ON kb.chunks (tenant_id);

ALTER TABLE kb.chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE kb.chunks FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS kb_chunks_tenant_isolation ON kb.chunks;
CREATE POLICY kb_chunks_tenant_isolation ON kb.chunks
    USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);

-- ---------------------------------------------------------------------------------------------
-- Target schema từ `G:\\My Drive\\ERD.drawio` (xem `DATABASE-DESIGN-DAY30.md` — 3 bảng này KHÔNG
-- nằm trong phạm vi demo Day 30, land ở đây SỚM dưới dạng shell (cùng khuôn `obs.costs`/
-- `obs.golden_sets`: DDL tồn tại, CHƯA có writer nào trong `apps/studio`/`KbPipeline` ghi vào các
-- bảng này). `kb.chunks` ở trên GIỮ NGUYÊN không đổi — đây là bảng SONG SONG, không phải thay thế;
-- cắt-sang (cutover) dữ liệu + đổi code đọc/ghi là việc riêng, ngoài phạm vi lần sửa DDL này.
--
-- `kb.knowledge_bases` — 1 tenant có nhiều KB theo phòng ban (section_role). `collection_ref` là
-- CHUỖI ĐỊNH TUYẾN tới vector DB ngoài, KHÔNG PHẢI FK (đúng ERD).
--
-- `section_role NOT NULL DEFAULT 'public'` (review kb#47 finding #3): trước là nullable trong khi
-- `kb.chunks`/`kb.chunk_pointers` (bảng con) đòi NOT NULL — bất đối xứng ngay đúng cột fence nội
-- dung của `kb.search`. Đối xứng lại: cha KHÔNG được NULL, y hệt con.
--
-- `UNIQUE (tenant_id, id)` (review kb#47 finding #1): PK `id` một cột không đủ làm target cho FK
-- xuyên-tenant an toàn — cần cặp `(tenant_id, id)` để `kb.documents`/`kb.chunk_pointers` FK CHÍNH
-- XÁC vào cặp đó (xem constraint composite bên dưới) thay vì chỉ vào `id`.
--
-- `status` KHÔNG có CHECK giới hạn giá trị (review kb#47 finding #4, nhỏ): chưa writer nào ghi
-- bảng này, nên tập giá trị hợp lệ (`active`/`archived`/...) chưa có bằng chứng thật — bịa ra CHECK
-- lúc này là suy đoán logic nghiệp vụ không có căn cứ. Cùng khuôn evalhub#36 (schema.py:118-120):
-- quyết định khi có writer thật, ghi rõ lý do CHƯA quyết ở đây thay vì đoán liều.
CREATE TABLE IF NOT EXISTS kb.knowledge_bases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    section_role TEXT NOT NULL DEFAULT 'public',
    name TEXT NOT NULL,
    vector_provider TEXT,
    collection_ref TEXT,
    embedding_model TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT kb_knowledge_bases_tenant_id_uq UNIQUE (tenant_id, id)
);

CREATE INDEX IF NOT EXISTS kb_knowledge_bases_tenant_id_idx ON kb.knowledge_bases (tenant_id);

ALTER TABLE kb.knowledge_bases ENABLE ROW LEVEL SECURITY;
ALTER TABLE kb.knowledge_bases FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS kb_knowledge_bases_tenant_isolation ON kb.knowledge_bases;
CREATE POLICY kb_knowledge_bases_tenant_isolation ON kb.knowledge_bases
    USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);

-- `kb.documents` — quản lý file tài liệu upload (1 KB chứa nhiều file). `kb_id` là FK same-schema
-- (hợp lệ — luật "không cross-schema FK" chỉ áp dụng giữa các schema khác nhau, không áp dụng ở đây).
--
-- FK composite `(tenant_id, kb_id) REFERENCES kb.knowledge_bases (tenant_id, id)` (review kb#47
-- finding #1, BLOCK): FK một cột `kb_id -> knowledge_bases(id)` chỉ chứng minh KB đó TỒN TẠI, không
-- chứng minh nó thuộc CÙNG tenant — Postgres kiểm tra toàn vẹn tham chiếu chạy dưới quyền OWNER và
-- BỎ QUA row-level security (hành vi có tài liệu, không phải bug). Demo thật (review comment):
-- tenant A không SELECT được KB của tenant B (RLS đọc đúng), nhưng vẫn INSERT được document có
-- `kb_id` trỏ thẳng vào KB đó — ghi xuyên tenant lọt qua FK. Composite FK đóng lỗ này: Postgres
-- không cho `(tenant_id, kb_id)` của hàng con khớp với một `(tenant_id, id)` của KB thuộc tenant
-- khác, vì cặp đó không tồn tại trong `kb_knowledge_bases_tenant_id_uq`.
--
-- `section_role NOT NULL DEFAULT 'public'` — cùng lý do finding #3 ở `kb.knowledge_bases` trên.
--
-- `ON DELETE RESTRICT` (tường minh, review kb#47 finding #4): giữ đúng hành vi mặc định (không
-- clause = RESTRICT), nhưng ghi rõ ra thay vì ngầm định — xoá một KB còn document con sẽ báo lỗi
-- FK thay vì âm thầm cascade mất nội dung. Cùng tinh thần thận trọng với mất dữ liệu đã có ở
-- `kb.chunks` (cảnh báo TRUNCATE phía trên).
CREATE TABLE IF NOT EXISTS kb.documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    kb_id UUID NOT NULL,
    filename TEXT NOT NULL,
    filehash TEXT,
    section_role TEXT NOT NULL DEFAULT 'public',
    chunk_count INT NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT kb_documents_tenant_id_uq UNIQUE (tenant_id, id),
    CONSTRAINT kb_documents_kb_fk FOREIGN KEY (tenant_id, kb_id)
        REFERENCES kb.knowledge_bases (tenant_id, id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS kb_documents_tenant_id_idx ON kb.documents (tenant_id);
CREATE INDEX IF NOT EXISTS kb_documents_kb_id_idx ON kb.documents (kb_id);

ALTER TABLE kb.documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE kb.documents FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS kb_documents_tenant_isolation ON kb.documents;
CREATE POLICY kb_documents_tenant_isolation ON kb.documents
    USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);

-- `kb.chunk_pointers` — kế thừa hình dạng `kb.chunks` (text/embed_text/embedding) cộng `doc_id`
-- (1 file cắt nhiều chunk) + `kb_id` + `external_id` (route qua `knowledge_bases.collection_ref`
-- tới bản ghi thật trong vector DB ngoài). `embedding` NULLABLE — "cache tuỳ chọn" theo ERD, không
-- phải nguồn sự thật khi đã có vector DB ngoài đứng sau `external_id`.
--
-- Cả 2 FK composite theo cặp `(tenant_id, x)` — cùng lý do finding #1 ở `kb.documents` trên, áp
-- riêng cho TỪNG FK (không dựa transitively vào FK còn lại): `kb_id` có thể trỏ đúng tenant trong
-- khi `doc_id` trỏ sai tenant hoặc ngược lại, nên cả hai phải tự chặn độc lập.
CREATE TABLE IF NOT EXISTS kb.chunk_pointers (
    chunk_id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    tenant_id UUID NOT NULL,
    kb_id UUID NOT NULL,
    doc_id UUID NOT NULL,
    section_role TEXT NOT NULL,
    external_id TEXT,
    text TEXT NOT NULL,
    embed_text TEXT,
    embedding vector({EMBEDDING_DIM}),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT kb_chunk_pointers_kb_fk FOREIGN KEY (tenant_id, kb_id)
        REFERENCES kb.knowledge_bases (tenant_id, id) ON DELETE RESTRICT,
    CONSTRAINT kb_chunk_pointers_doc_fk FOREIGN KEY (tenant_id, doc_id)
        REFERENCES kb.documents (tenant_id, id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS kb_chunk_pointers_tenant_id_idx ON kb.chunk_pointers (tenant_id);
CREATE INDEX IF NOT EXISTS kb_chunk_pointers_kb_id_idx ON kb.chunk_pointers (kb_id);
CREATE INDEX IF NOT EXISTS kb_chunk_pointers_doc_id_idx ON kb.chunk_pointers (doc_id);

ALTER TABLE kb.chunk_pointers ENABLE ROW LEVEL SECURITY;
ALTER TABLE kb.chunk_pointers FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS kb_chunk_pointers_tenant_isolation ON kb.chunk_pointers;
CREATE POLICY kb_chunk_pointers_tenant_isolation ON kb.chunk_pointers
    USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
"""


def ddl() -> str:
    """Return this quadrant's idempotent DDL — safe to execute any number of times (`CREATE ...
    IF NOT EXISTS` throughout; the policy is `DROP ... IF EXISTS` then recreated identically)."""
    return _KB_DDL
