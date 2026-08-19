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

import pytest
from psycopg_pool import AsyncConnectionPool as _Pool  # noqa: F401  (kiểu cho annotation dưới)
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
    VALUES ('ankor-access-001#c1', gen_random_uuid(), 'public', 'chunk 1.0 còn sót',
            '[1,0,0,0,0,0,0,0]');
ALTER TABLE kb.chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE kb.chunks FORCE ROW LEVEL SECURITY;
"""

_DIM = """
SELECT atttypmod FROM pg_attribute
 WHERE attrelid = 'kb.chunks'::regclass AND attname = 'embedding' AND NOT attisdropped
"""

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
    - **dòng cũ** — vector 1.0 nằm ở không gian khác (provider khác, chiều khác); giữ lại là
      giữ số đúng-định-dạng-sai-nghĩa. Đây cũng là chỗ duy nhất trong repo dọn 140 chunk 1.0:
      cả hai script ingest đều `ON CONFLICT DO UPDATE`, không xoá gì (`chunk_id` 1.0 và 2.0
      không trùng nhau nên upsert không đụng tới dòng cũ).

    `TRUNCATE` chứ không `DELETE`: `FORCE ROW LEVEL SECURITY` fence cả owner, nên `DELETE` khi
    `app.tenant_id` chưa đặt sẽ xoá **0 dòng trong im lặng** (đã đo: `DELETE 0`) rồi `ALTER` vỡ.
    """
    async with admin_pool.connection() as conn:
        await conn.execute(_LEGACY_SHAPE)
        assert await _scalar(conn, _DIM) == 8, "tiền đề hỏng: bảng dựng ra đã không phải vector(8)"
        assert await _scalar(conn, _HNSW) == 1, "tiền đề hỏng: index HNSW chưa được dựng"

        await conn.execute(ddl())

        assert await _scalar(conn, _DIM) == EMBEDDING_DIM
        assert await _scalar(conn, _HNSW) == 0, "index HNSW phải bị xoá tường minh, không chỉ ngừng tạo"
        assert await _scalar(conn, "SELECT count(*) FROM kb.chunks") == 0


async def test_ddl_chay_lai_tren_db_dung_chieu_KHONG_dong_du_lieu(admin_pool) -> None:  # type: ignore[no-untyped-def]
    """Chạy `ddl()` lần hai trên DB đã đúng chiều **không được** xoá gì.

    Đây là bài giữ cho khối migration có điều kiện. `ensure_all_schemas()` chạy MỖI lần backend
    boot; một `TRUNCATE` vô điều kiện sẽ làm mọi lần khởi động lại xoá sạch corpus đã ingest —
    xanh ở bài trên, mất dữ liệu ở production. Quét đột biến: bỏ mệnh đề `IF cur_dim <> ...` thì
    bài trên vẫn xanh, chỉ bài này đỏ.
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
