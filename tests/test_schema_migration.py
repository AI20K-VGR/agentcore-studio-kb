"""Migration chiều cột `kb.chunks.embedding` trên DB ĐÃ TỒN TẠI (D22, DE).

`schema.ddl()` idempotent bằng `CREATE ... IF NOT EXISTS`, và chính điều đó làm nó **không**
migrate được: `CREATE TABLE IF NOT EXISTS` gặp bảng đã có thì bỏ qua toàn bộ định nghĩa cột, nên
đổi `EMBEDDING_DIM` 8 → 2048 mà chỉ dựa vào DDL cũ sẽ để lại cột `vector(8)` y nguyên. Fail-fast ở
`pipeline.py`/`postgres.py` so vector với hằng số MỚI nên nó **lọt**, rồi lỗi rơi xuống tận Postgres
dưới dạng `expected 8 dimensions, not 2048` — xa chỗ thật sự sai.

Hai bài dưới đây canh hai nửa ngược nhau của cùng một khối `DO $$`, và không bài nào thay được bài
kia: một bài chứng minh nó **có** chạy khi chiều lệch, bài kia chứng minh nó **không** chạy khi
chiều đã khớp. Bỏ bài thứ hai thì một khối migration vô điều kiện (wipe sạch `kb.chunks` mỗi lần
boot) vẫn xanh — đó là chế độ hỏng tệ nhất trong cả hai.

Chạy trên `admin_pool` (`studio_owner`) vì DDL là việc của owner — đúng đường
`ensure_all_schemas` gọi lúc backend boot.
"""

from __future__ import annotations

from uuid import UUID

import pytest
from psycopg_pool import AsyncConnectionPool as _Pool  # noqa: F401  (kiểu cho annotation dưới)
from studio_kb.pipeline import KbPipeline
from studio_kb.postgres import _bind_tenant
from studio_kb.schema import EMBEDDING_DIM, ddl

pytestmark = pytest.mark.asyncio

_LEGACY_SHAPE = """
DROP SCHEMA IF EXISTS kb CASCADE;
CREATE SCHEMA kb;
CREATE TABLE kb.chunks (
    chunk_id TEXT PRIMARY KEY,
    tenant_id UUID NOT NULL,
    section_role TEXT NOT NULL,
    text TEXT NOT NULL,
    embedding vector(8),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX kb_chunks_embedding_hnsw_idx ON kb.chunks USING hnsw (embedding vector_cosine_ops);
INSERT INTO kb.chunks (chunk_id, tenant_id, section_role, text, embedding)
    VALUES ('ankor-access-001#c1', '11111111-1111-1111-1111-111111111111', 'public',
            'chunk 1.0 còn sót', '[1,0,0,0,0,0,0,0]');
ALTER TABLE kb.chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE kb.chunks FORCE ROW LEVEL SECURITY;

-- Policy PHẢI có trong hình "DB cũ": DDL thật có nó từ đầu, và thiếu nó thì `FORCE RLS` thành
-- deny-all — tiền đề sai sẽ làm test đỏ vì lý do chẳng liên quan gì tới migration.
CREATE POLICY kb_chunks_tenant_isolation ON kb.chunks
    USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
"""

_DIM = """
SELECT atttypmod FROM pg_attribute
 WHERE attrelid = 'kb.chunks'::regclass AND attname = 'embedding' AND NOT attisdropped
"""

_TENANT = UUID("11111111-1111-1111-1111-111111111111")

_HNSW = "SELECT count(*) FROM pg_indexes WHERE schemaname='kb' AND indexname='kb_chunks_embedding_hnsw_idx'"


async def _scalar(conn: object, sql: str) -> int:
    cur = await conn.execute(sql)  # type: ignore[attr-defined]
    row = await cur.fetchone()
    return int(row[0])


async def test_ddl_migrate_cot_vector_8_sang_chieu_dang_ghim(admin_pool) -> None:  # type: ignore[no-untyped-def]
    """DB hình CŨ (`vector(8)` + index HNSW + 1 dòng 1.0) → chạy `ddl()` → cột đúng
    `EMBEDDING_DIM`, index HNSW biến mất, và dòng cũ bị dọn.

    Ba assert là ba hỏng khác nhau, không phải ba cách viết lại một phép kiểm:

    - **chiều cột** — thứ mà `CREATE TABLE IF NOT EXISTS` một mình không bao giờ đổi được;
    - **index HNSW** — ngừng `CREATE` là chưa đủ, DB cũ vẫn giữ index; và nó phải đi TRƯỚC
      `ALTER TYPE` (index trên cột đang đổi kiểu sẽ chặn), nên nếu thứ tự trong DDL sai thì bài
      này đỏ ngay ở bước chạy, không phải ở assert;
    - **vector cũ bị bỏ, DÒNG THÌ KHÔNG** — vector 1.0 nằm ở không gian khác nên giữ lại là giữ
      số đúng-định-dạng-sai-nghĩa; nhưng `text`/`embed_text` phải sống, xem bài
      `test_tai_lieu_tenant_upload_song_sot_migration_va_re_index_duoc` ngay dưới.

    **Đổi so với kb#43 — có chủ đích, KHÔNG phải sửa test cho xanh.** Bản đầu dùng `TRUNCATE` và
    bài này assert `count(*) == 0`. Review AIE-2 chỉ ra tài liệu tenant tự upload
    (`POST /api/admin/documents`, app#27) **không có bản sao nào khác** — `kb.chunks` là bản duy
    nhất — nên `TRUNCATE` là mất vĩnh viễn, không đường phục hồi. Nay `ALTER ... USING NULL`:
    dòng giữ nguyên, `embedding := NULL`, dựng lại bằng `re_index`. Assert đổi từ "0 dòng" sang
    "đủ dòng, 0 vector" — đổi vì HÀNH VI đổi, và hành vi mới mới là hành vi đúng.
    """
    async with admin_pool.connection() as conn:
        await conn.execute(_LEGACY_SHAPE)
        assert await _scalar(conn, _DIM) == 8, "tiền đề hỏng: bảng dựng ra đã không phải vector(8)"
        assert await _scalar(conn, _HNSW) == 1, "tiền đề hỏng: index HNSW chưa được dựng"

        await conn.execute(ddl())

        assert await _scalar(conn, _DIM) == EMBEDDING_DIM
        assert await _scalar(conn, _HNSW) == 0, "index HNSW phải bị xoá tường minh, không chỉ ngừng tạo"
        # Bind tenant TRƯỚC khi đếm: `FORCE ROW LEVEL SECURITY` fence cả owner, không bind thì
        # `count(*)` trả 0 và bài này xanh-giả đúng vào lúc dữ liệu đã bị xoá thật.
        await conn.execute("SELECT set_config('app.tenant_id', %s, false)", (str(_TENANT),))
        assert await _scalar(conn, "SELECT count(*) FROM kb.chunks") == 1, "dòng KHÔNG được biến mất"
        assert await _scalar(conn, "SELECT count(*) FROM kb.chunks WHERE embedding IS NULL") == 1


async def test_ddl_chay_lai_tren_db_dung_chieu_KHONG_dong_du_lieu(admin_pool) -> None:  # type: ignore[no-untyped-def]
    """Chạy `ddl()` lần hai trên DB đã đúng chiều **không được** xoá gì.

    Đây là bài giữ cho khối migration có điều kiện — `ensure_all_schemas()` chạy MỖI lần backend
    boot, nên migration vô điều kiện sẽ cắn ở mọi lần khởi động lại.

    **Phải assert cả VECTOR, không chỉ đếm dòng** — bài học từ chính lần sửa này (kb#44). Khi
    migration còn là `TRUNCATE`, đếm dòng là đủ: mất dữ liệu ⇒ mất dòng. Sau khi đổi sang
    `USING NULL` thì dòng **luôn** sống, và một migration vô điều kiện sẽ âm thầm `NULL` sạch
    vector ở mỗi lần boot — tài liệu còn nguyên nhưng `_SEARCH` (lọc `embedding IS NOT NULL`)
    không trả về gì nữa. Quét đột biến bắt đúng chỗ này: đổi điều kiện thành `IF true` thì bản
    chỉ-đếm-dòng của bài này **vẫn xanh**, phải có assert vector mới đỏ.
    """
    tenant = "11111111-1111-1111-1111-111111111111"
    async with admin_pool.connection() as conn:
        await conn.execute(ddl())
        # `app.tenant_id` phải đặt kể cả cho owner: `FORCE ROW LEVEL SECURITY` làm vế `WITH CHECK`
        # cắn cả chủ bảng, nên INSERT không có biến phiên sẽ bị từ chối thẳng (đúng thiết kế fence
        # — và cũng là lý do migration ở trên dùng TRUNCATE chứ không DELETE).
        await conn.execute("SELECT set_config('app.tenant_id', %s, false)", (tenant,))
        await conn.execute(
            "INSERT INTO kb.chunks (chunk_id, tenant_id, section_role, text, embedding)"
            " VALUES ('sau-migration', %s, 'public', 'đã ở đúng chiều', %s)",
            (tenant, str([0.0] * EMBEDDING_DIM)),
        )
        await conn.execute(ddl())

        assert await _scalar(conn, "SELECT count(*) FROM kb.chunks") == 1, "boot lại KHÔNG được wipe"
        assert await _scalar(conn, _DIM) == EMBEDDING_DIM
        assert await _scalar(conn, "SELECT count(*) FROM kb.chunks WHERE embedding IS NOT NULL") == 1, (
            "boot lại làm MẤT VECTOR — dòng còn nhưng `_SEARCH` lọc `embedding IS NOT NULL`, "
            "nên tài liệu biến mất khỏi truy xuất một cách im lặng"
        )


async def test_tai_lieu_tenant_upload_song_sot_migration_va_re_index_duoc(admin_pool, pool) -> None:  # type: ignore[no-untyped-def]
    """Bài hồi quy cho finding của AIE-2 ở kb#43: **tài liệu tenant tự upload không được mất**.

    Vì sao bài này tồn tại riêng, không gộp vào bài migrate ở trên: bài kia chứng minh *cấu trúc*
    đổi đúng (chiều cột, index), bài này chứng minh *dữ liệu không chết* — và dữ liệu ở đây là loại
    **không dựng lại được**. `scripts/ingest_callisto_v2.py` phát lại được 800 chunk corpus Callisto
    từ `docs/`; còn `POST /api/admin/documents` (app#27) chunk/embed/index thẳng vào `kb.chunks` và
    **không lưu file gốc ở đâu khác** — `core` schema chỉ có tenants·users·sections·jobs·outbox,
    không bảng nào giữ blob. `kb.chunks` là bản sao DUY NHẤT.

    Ba chặng, mỗi chặng khoá một nửa của "phục hồi được":

    1. **sống sót** — sau `ddl()`, `text` và `embed_text` còn nguyên từng ký tự. Đây là điều
       `TRUNCATE` của kb#43 phá, và không assert nào lúc đó bắt được.
    2. **không rác** — `embedding IS NULL` nên `PgKbSearch` không trả nó về (`_SEARCH` lọc
       `AND embedding IS NOT NULL`). Hạ cấp sạch: tài liệu tạm thời không truy xuất được, chứ
       không phải trả về vector sai không gian.
    3. **dựng lại được** — `re_index` đọc `embed_text` TỪ DB (không cần file gốc) và nạp lại
       vector đúng chiều mới. Đây là chặng biến "mất vector" thành "cần một lệnh".

    Quét đột biến: đổi `USING NULL` về `TRUNCATE` thì chặng 1 đỏ ngay.
    """
    tenant = _TENANT
    van_ban = "Qui trình nội bộ do tenant tự tải lên"
    embed_view = "## Tài liệu nội bộ\nQui trình nội bộ do tenant tự tải lên"

    # dựng DB hình CŨ + một "tài liệu upload" (vector 8 chiều, đúng thứ app#27 ghi trước migration)
    async with admin_pool.connection() as conn:
        await conn.execute(_LEGACY_SHAPE)
        await conn.execute("ALTER TABLE kb.chunks ADD COLUMN IF NOT EXISTS embed_text TEXT")
        # `_bind_tenant` đặt is_local=true (chỉ sống trong 1 giao dịch); các execute dưới đây rời
        # nhau nên phải bind phạm vi PHIÊN. FORCE RLS fence cả owner — không bind thì WITH CHECK chặn.
        await conn.execute("SELECT set_config('app.tenant_id', %s, false)", (str(tenant),))
        await conn.execute(
            "INSERT INTO kb.chunks (chunk_id, tenant_id, section_role, text, embed_text, embedding)"
            " VALUES ('upload-tenant-001#c1', %s, 'public', %s, %s, '[1,0,0,0,0,0,0,0]')",
            (tenant, van_ban, embed_view),
        )
        await conn.execute(ddl())
        # `_LEGACY_SHAPE` mở đầu bằng `DROP SCHEMA kb CASCADE` nên grant mà `admin_pool` cấp lúc
        # setup bị cuốn theo. Cấp lại bằng SQL trần thay vì gọi `grant_app_privileges` của
        # `studio_app`: `.importlinter` xếp `studio_kb` dưới `studio_app`, một `import studio_app`
        # ở đây sẽ làm đỏ `lint-imports`.
        await conn.execute("GRANT USAGE ON SCHEMA kb TO studio_app")
        await conn.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON kb.chunks TO studio_app")
        await conn.execute("SELECT set_config('app.tenant_id', %s, false)", (str(tenant),))

        # ① sống sót — nội dung còn NGUYÊN VẸN, không chỉ còn dòng
        cur = await conn.execute(
            "SELECT text, embed_text, embedding IS NULL FROM kb.chunks WHERE chunk_id = 'upload-tenant-001#c1'"
        )
        row = await cur.fetchone()
        assert row is not None, "tài liệu tenant BIẾN MẤT sau migration — không có đường phục hồi"
        assert row[0] == van_ban, "text bị đổi"
        assert row[1] == embed_view, "embed_text bị đổi — re_index sẽ embed sai chuỗi"
        # ② chưa có vector thì không được coi là dữ liệu dùng được
        assert row[2] is True, "vector cũ (8 chiều) phải bị bỏ, không được ép kiểu sang không gian mới"

    # ③ dựng lại được — re_index đọc embed_text từ DB, không cần file gốc
    class _Embedding:
        async def embed(self, texts: list[str]) -> list[list[float]]:
            return [[0.1] * EMBEDDING_DIM for _ in texts]

    # 2 = dòng upload + `ankor-access-001#c1` của `_LEGACY_SHAPE` (cùng tenant). Con số này chính
    # là bằng chứng thứ hai của bài: CẢ HAI loại dòng đều sống qua migration, không riêng dòng nào.
    assert await KbPipeline(pool, _Embedding()).re_index(tenant) == 2

    async with pool.connection() as conn, conn.transaction():
        await _bind_tenant(conn, tenant)
        cur = await conn.execute(
            "SELECT vector_dims(embedding), text FROM kb.chunks WHERE chunk_id = 'upload-tenant-001#c1'"
        )
        dims, text_sau = await cur.fetchone()
    assert dims == EMBEDDING_DIM, "re_index phải nạp vector đúng chiều mới"
    assert text_sau == van_ban, "re_index không được đụng vào text"
