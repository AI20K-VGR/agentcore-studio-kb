"""Phase 5 gate tests — RLS-framework proof, GREEN Day-1 (F10): fail-closed via the app-conn
(money-shot), tenant-scoped visibility (2-conn dance: seed via admin-conn, assert via app-conn),
and `FORCE ROW LEVEL SECURITY` scoping the OWNER too + `WITH CHECK` blocking a cross-tenant WRITE.
Needs a live DB — see apps/studio/tests/test_schema.py module docstring for the fixture-skip
behavior (root conftest.py `admin_pool`/`pool` fixtures, shared across the whole workspace suite).
"""

from __future__ import annotations

from uuid import UUID

import psycopg
import pytest
from psycopg import sql

# Danh tính tenant là UUID (D-13). "tenant-a"/"tenant-b" cũ không phải UUID hợp lệ nên không dùng
# được nữa — cột `kb.chunks.tenant_id` giờ là `UUID`, và policy cast `::uuid`. Hai UUID rời rạc,
# chỉ cần khác nhau để chứng minh cách ly tenant; không cần khớp bảng phân giải nào.
TENANT_A = UUID("a0000000-0000-0000-0000-00000000000a")
TENANT_B = UUID("b0000000-0000-0000-0000-00000000000b")


async def _seed_chunk(pool: object, tenant_id: UUID, chunk_id: str, text: str) -> None:
    """Insert one `kb.chunks` row scoped to `tenant_id`. Sets `app.tenant_id` on the SAME
    connection/transaction FIRST — `FORCE ROW LEVEL SECURITY` (schema.py) means even the owner
    role (`admin_pool`) must satisfy `WITH CHECK` to insert a row at all.

    Binds `str(tenant_id)`: the session var is text, the policy casts it back with `::uuid`."""
    async with pool.connection() as conn:  # type: ignore[attr-defined]
        await conn.execute(sql.SQL("SET LOCAL app.tenant_id = {}").format(sql.Literal(str(tenant_id))))
        await conn.execute(
            "INSERT INTO kb.chunks (chunk_id, tenant_id, section_role, text) VALUES (%s, %s, %s, %s)",
            (chunk_id, tenant_id, "public", text),
        )


async def test_no_tenant_zero_rows(admin_pool: object, pool: object) -> None:
    """KHÓA (money-shot): app-conn (`studio_app`, non-owner) with NO `app.tenant_id` set sees
    0 rows even though a row exists for some tenant — fail-closed, not merely an empty table."""
    await _seed_chunk(admin_pool, TENANT_A, "chunk-1", "hello")

    async with pool.connection() as conn:  # type: ignore[attr-defined]
        cur = await conn.execute("SELECT count(*) FROM kb.chunks")
        row = await cur.fetchone()
    assert row is not None
    assert row[0] == 0


async def test_tenant_scoped_visibility(admin_pool: object, pool: object) -> None:
    """KHÓA: seed 2 tenants via the admin-conn, then the app-conn with `app.tenant_id` set to
    tenant-a sees ONLY tenant-a's row (2-conn dance)."""
    await _seed_chunk(admin_pool, TENANT_A, "chunk-a", "a-text")
    await _seed_chunk(admin_pool, TENANT_B, "chunk-b", "b-text")

    async with pool.connection() as conn:  # type: ignore[attr-defined]
        await conn.execute(sql.SQL("SET LOCAL app.tenant_id = {}").format(sql.Literal(str(TENANT_A))))
        cur = await conn.execute("SELECT chunk_id, tenant_id FROM kb.chunks")
        rows = await cur.fetchall()
    assert [row[0] for row in rows] == ["chunk-a"]
    assert {row[1] for row in rows} == {TENANT_A}


async def test_force_rls_and_with_check(admin_pool: object) -> None:
    """KHÓA F10: `FORCE ROW LEVEL SECURITY` scopes the OWNER role too (no-tenant-set on
    `admin_pool` -> 0 rows), and `WITH CHECK` blocks an INSERT whose `tenant_id` does not match
    the session's `app.tenant_id` — a cross-tenant WRITE, not just a read, gets rejected."""
    await _seed_chunk(admin_pool, TENANT_A, "chunk-owner", "owner-scoped-text")

    async with admin_pool.connection() as conn:  # type: ignore[attr-defined]
        cur = await conn.execute("SELECT count(*) FROM kb.chunks")
        row = await cur.fetchone()
    assert row is not None
    assert row[0] == 0

    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        async with admin_pool.connection() as conn:  # type: ignore[attr-defined]
            await conn.execute(sql.SQL("SET LOCAL app.tenant_id = {}").format(sql.Literal(str(TENANT_A))))
            await conn.execute(
                "INSERT INTO kb.chunks (chunk_id, tenant_id, section_role, text) VALUES (%s, %s, %s, %s)",
                ("chunk-cross-write", TENANT_B, "public", "cross-tenant-write-attempt"),
            )


async def test_empty_string_tenant_zero_rows_khong_raise(admin_pool: object, pool: object) -> None:
    """KHÓA (mục gate #25 của mentor: *"T1/T6 + **empty-string** xanh = leakage=0"*).

    Đây là bài kiểm **duy nhất** chạm tới `NULLIF(..., '')` trong policy (schema.py). Không có bài
    này thì `NULLIF` là code không ai kiểm — xoá đi mọi test khác vẫn xanh, nhưng fence vỡ với người
    gọi đặt `app.tenant_id = ''`.

    Vì sao `''` cần xử riêng, khác với "chưa set": `current_setting(..., true)` khi CHƯA set trả
    `NULL`; nhưng vài đường đặt biến lại cho **chuỗi rỗng** `''`, không phải NULL. Nếu policy cast
    thẳng `''::uuid` thì Postgres **raise** `invalid input syntax for type uuid: ""` — vỡ, nhưng vỡ
    **sai kiểu**: fence phải trả 0 dòng, không ném lỗi 500 vào mặt người dùng. `NULLIF(..., '')` biến
    `''` về `NULL`, và `tenant_id = NULL` không bao giờ đúng → 0 dòng, fail-closed.
    """
    await _seed_chunk(admin_pool, TENANT_A, "chunk-1", "hello")

    async with pool.connection() as conn:  # type: ignore[attr-defined]
        await conn.execute(sql.SQL("SET LOCAL app.tenant_id = {}").format(sql.Literal("")))
        cur = await conn.execute("SELECT count(*) FROM kb.chunks")
        row = await cur.fetchone()
    assert row is not None
    assert row[0] == 0  # 0 dòng, và không có exception nào nổi lên trên đường tới đây


async def test_ddl_idempotent(admin_pool: object) -> None:
    """KHÓA (Medium scenario, phase-5 test-scenario matrix): re-running `studio_kb.schema.ddl()`
    against a live DB a 2nd/3rd time (on top of the fixture's own `ensure_all_schemas` call) does
    not raise."""
    from studio_kb.schema import ddl

    async with admin_pool.connection() as conn:  # type: ignore[attr-defined]
        await conn.execute(ddl())
        await conn.execute(ddl())
