"""Phase 5 gate tests — RLS-framework proof, GREEN Day-1 (F10): fail-closed via the app-conn
(money-shot), tenant-scoped visibility (2-conn dance: seed via admin-conn, assert via app-conn),
and `FORCE ROW LEVEL SECURITY` scoping the OWNER too + `WITH CHECK` blocking a cross-tenant WRITE.
Needs a live DB — see apps/studio/tests/test_schema.py module docstring for the fixture-skip
behavior (root conftest.py `admin_pool`/`pool` fixtures, shared across the whole workspace suite).

kb#47 review (dholmes0207, AIE-2) added two things once `kb.knowledge_bases`/`kb.documents`/
`kb.chunk_pointers` landed alongside `kb.chunks`:
  - findings #2/#3: the money-shot 5-test battery below was written for `kb.chunks` only, but all
    4 tables share the identical RLS policy shape (schema.py) — so it's parametrized across all 4
    via `_TABLE_FIXTURES` instead of re-deriving 4x the same 5 functions.
  - finding #1 (BLOCK): the 3 FKs (`documents.kb_id`, `chunk_pointers.kb_id`, `chunk_pointers.doc_id`)
    are plain `REFERENCES parent(id)` — Postgres FK referential-integrity checks run under the table
    OWNER and bypass RLS entirely, so a tenant-A row could legally FK-reference a tenant-B parent
    even though tenant-A can never SELECT that parent. `test_fk_documents_kb_id_rejects_cross_tenant`
    / `..._chunk_pointers_kb_id_...` / `..._chunk_pointers_doc_id_...` reproduce that leak directly
    (RED against the pre-fix single-column FK, GREEN once schema.py uses a composite
    `FOREIGN KEY (tenant_id, x) REFERENCES parent (tenant_id, id)` instead).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from uuid import UUID, uuid4

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


async def _seed_kb(pool: object, tenant_id: UUID, kb_id: UUID, name: str = "kb") -> None:
    """Insert one `kb.knowledge_bases` row scoped to `tenant_id` — same SET LOCAL / FORCE RLS
    reasoning as `_seed_chunk`."""
    async with pool.connection() as conn:  # type: ignore[attr-defined]
        await conn.execute(sql.SQL("SET LOCAL app.tenant_id = {}").format(sql.Literal(str(tenant_id))))
        await conn.execute(
            "INSERT INTO kb.knowledge_bases (id, tenant_id, name) VALUES (%s, %s, %s)",
            (kb_id, tenant_id, name),
        )


async def _seed_document(pool: object, tenant_id: UUID, doc_id: UUID, kb_id: UUID, filename: str = "doc.pdf") -> None:
    """Insert one `kb.documents` row scoped to `tenant_id`. Caller supplies `kb_id` — the FK parent
    must already exist (via `_seed_kb`), and callers deliberately pass a same- or cross-tenant
    `kb_id` depending on what they're testing."""
    async with pool.connection() as conn:  # type: ignore[attr-defined]
        await conn.execute(sql.SQL("SET LOCAL app.tenant_id = {}").format(sql.Literal(str(tenant_id))))
        await conn.execute(
            "INSERT INTO kb.documents (id, tenant_id, kb_id, filename) VALUES (%s, %s, %s, %s)",
            (doc_id, tenant_id, kb_id, filename),
        )


async def _seed_chunk_pointer(
    pool: object, tenant_id: UUID, chunk_id: str, kb_id: UUID, doc_id: UUID, text: str = "text"
) -> None:
    """Insert one `kb.chunk_pointers` row scoped to `tenant_id`. Caller supplies `kb_id`/`doc_id` —
    same same-/cross-tenant flexibility as `_seed_document`."""
    async with pool.connection() as conn:  # type: ignore[attr-defined]
        await conn.execute(sql.SQL("SET LOCAL app.tenant_id = {}").format(sql.Literal(str(tenant_id))))
        await conn.execute(
            "INSERT INTO kb.chunk_pointers (chunk_id, tenant_id, kb_id, doc_id, section_role, text) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (chunk_id, tenant_id, kb_id, doc_id, "public", text),
        )


@dataclass(frozen=True)
class _TableFixture:
    """One RLS-fenced table, driving the 5-test battery below generically. `new_row` inserts ONE
    valid row scoped to `tenant_id` — wiring any parent FK rows for the SAME tenant internally, so
    each fixture is self-contained (kb#47 review finding #2: 5 tests parametrized over 4 tables)."""

    table: str
    pk_col: str
    new_row: Callable[[object, UUID], Awaitable[str]]


async def _new_chunk_row(pool: object, tenant_id: UUID) -> str:
    chunk_id = str(uuid4())
    await _seed_chunk(pool, tenant_id, chunk_id, "fixture-text")
    return chunk_id


async def _new_kb_row(pool: object, tenant_id: UUID) -> str:
    kb_id = uuid4()
    await _seed_kb(pool, tenant_id, kb_id, name="fixture-kb")
    return str(kb_id)


async def _new_document_row(pool: object, tenant_id: UUID) -> str:
    kb_id, doc_id = uuid4(), uuid4()
    await _seed_kb(pool, tenant_id, kb_id, name="parent-kb")
    await _seed_document(pool, tenant_id, doc_id, kb_id, filename="fixture-doc.pdf")
    return str(doc_id)


async def _new_chunk_pointer_row(pool: object, tenant_id: UUID) -> str:
    kb_id, doc_id, chunk_id = uuid4(), uuid4(), str(uuid4())
    await _seed_kb(pool, tenant_id, kb_id, name="parent-kb")
    await _seed_document(pool, tenant_id, doc_id, kb_id, filename="parent-doc.pdf")
    await _seed_chunk_pointer(pool, tenant_id, chunk_id, kb_id, doc_id, text="fixture-text")
    return chunk_id


_TABLE_FIXTURES = (
    _TableFixture("kb.chunks", "chunk_id", _new_chunk_row),
    _TableFixture("kb.knowledge_bases", "id", _new_kb_row),
    _TableFixture("kb.documents", "id", _new_document_row),
    _TableFixture("kb.chunk_pointers", "chunk_id", _new_chunk_pointer_row),
)
_FIXTURE_IDS = [f.table for f in _TABLE_FIXTURES]


@pytest.mark.parametrize("fixture", _TABLE_FIXTURES, ids=_FIXTURE_IDS)
async def test_no_tenant_zero_rows(fixture: _TableFixture, admin_pool: object, pool: object) -> None:
    """KHÓA (money-shot), parametrized across all 4 RLS-fenced tables (kb#47 review finding #2):
    app-conn (`studio_app`, non-owner) with NO `app.tenant_id` set sees 0 rows even though a row
    exists for some tenant — fail-closed, not merely an empty table."""
    await fixture.new_row(admin_pool, TENANT_A)

    async with pool.connection() as conn:  # type: ignore[attr-defined]
        cur = await conn.execute(sql.SQL("SELECT count(*) FROM {}").format(sql.SQL(fixture.table)))
        row = await cur.fetchone()
    assert row is not None
    assert row[0] == 0


@pytest.mark.parametrize("fixture", _TABLE_FIXTURES, ids=_FIXTURE_IDS)
async def test_tenant_scoped_visibility(fixture: _TableFixture, admin_pool: object, pool: object) -> None:
    """KHÓA, parametrized across all 4 tables: seed 2 tenants via the admin-conn, then the app-conn
    with `app.tenant_id` set to tenant-a sees ONLY tenant-a's row (2-conn dance)."""
    row_a = await fixture.new_row(admin_pool, TENANT_A)
    await fixture.new_row(admin_pool, TENANT_B)

    async with pool.connection() as conn:  # type: ignore[attr-defined]
        await conn.execute(sql.SQL("SET LOCAL app.tenant_id = {}").format(sql.Literal(str(TENANT_A))))
        cur = await conn.execute(
            sql.SQL("SELECT {}, tenant_id FROM {}").format(sql.Identifier(fixture.pk_col), sql.SQL(fixture.table))
        )
        rows = await cur.fetchall()
    # `pk_col` may come back as `uuid.UUID` (id) or `str` (chunk_id, TEXT PK) depending on the
    # table — normalize to str for comparison, since `fixture.new_row` always returns a str.
    assert [str(row[0]) for row in rows] == [row_a]
    assert {row[1] for row in rows} == {TENANT_A}


@pytest.mark.parametrize("fixture", _TABLE_FIXTURES, ids=_FIXTURE_IDS)
async def test_force_rls_and_with_check(fixture: _TableFixture, admin_pool: object) -> None:
    """KHÓA F10, parametrized across all 4 tables: `FORCE ROW LEVEL SECURITY` scopes the OWNER role
    too (no-tenant-set on `admin_pool` -> 0 rows), and `WITH CHECK` blocks an INSERT whose row-level
    `tenant_id` does not match the session's `app.tenant_id` — a cross-tenant WRITE, not just a
    read, gets rejected.

    The row's FK parents (if any) are seeded under `TENANT_B` — the SAME tenant the mismatched row
    claims to belong to — so a post-fix composite FK (kb#47 finding #1) still resolves cleanly and
    this test isolates the `tenant_id`/`WITH CHECK` mismatch alone, not the FK. The `_TABLE_FIXTURES`
    FK-cross-tenant fixture-only tests below (`test_fk_*_rejects_cross_tenant`) cover the FK case."""
    await fixture.new_row(admin_pool, TENANT_A)

    async with admin_pool.connection() as conn:  # type: ignore[attr-defined]
        cur = await conn.execute(sql.SQL("SELECT count(*) FROM {}").format(sql.SQL(fixture.table)))
        row = await cur.fetchone()
    assert row is not None
    assert row[0] == 0

    # Wire the mismatched row's FK parents (if any) under TENANT_B FIRST, own-tenant to that row's
    # claimed tenant_id — isolates this test to the tenant_id/WITH CHECK mismatch alone.
    kb_id = doc_id = None
    if fixture.table in ("kb.documents", "kb.chunk_pointers"):
        kb_id = uuid4()
        await _seed_kb(admin_pool, TENANT_B, kb_id, name="mismatch-parent-kb")
        # Nested (not a sibling `if`): "kb.chunk_pointers" is a subset of the outer condition, so
        # this is the same runtime behavior — but nesting lets mypy narrow `kb_id` from
        # `UUID | None` to `UUID` here, which two independent `if`s cannot (arg-type false positive).
        if fixture.table == "kb.chunk_pointers":
            doc_id = uuid4()
            await _seed_document(admin_pool, TENANT_B, doc_id, kb_id, filename="mismatch-parent-doc.pdf")

    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        async with admin_pool.connection() as conn:  # type: ignore[attr-defined]
            await conn.execute(sql.SQL("SET LOCAL app.tenant_id = {}").format(sql.Literal(str(TENANT_A))))
            if fixture.table == "kb.chunks":
                await conn.execute(
                    "INSERT INTO kb.chunks (chunk_id, tenant_id, section_role, text) VALUES (%s, %s, %s, %s)",
                    (str(uuid4()), TENANT_B, "public", "cross-tenant-write-attempt"),
                )
            elif fixture.table == "kb.knowledge_bases":
                await conn.execute(
                    "INSERT INTO kb.knowledge_bases (id, tenant_id, name) VALUES (%s, %s, %s)",
                    (uuid4(), TENANT_B, "cross-tenant-write-attempt"),
                )
            elif fixture.table == "kb.documents":
                await conn.execute(
                    "INSERT INTO kb.documents (id, tenant_id, kb_id, filename) VALUES (%s, %s, %s, %s)",
                    (uuid4(), TENANT_B, kb_id, "cross-tenant-write-attempt.pdf"),
                )
            else:
                await conn.execute(
                    "INSERT INTO kb.chunk_pointers (chunk_id, tenant_id, kb_id, doc_id, section_role, text) "
                    "VALUES (%s, %s, %s, %s, %s, %s)",
                    (str(uuid4()), TENANT_B, kb_id, doc_id, "public", "cross-tenant-write-attempt"),
                )


@pytest.mark.parametrize("fixture", _TABLE_FIXTURES, ids=_FIXTURE_IDS)
async def test_empty_string_tenant_zero_rows_khong_raise(
    fixture: _TableFixture, admin_pool: object, pool: object
) -> None:
    """KHÓA (mục gate #25 của mentor: *"T1/T6 + **empty-string** xanh = leakage=0"*), parametrized
    across all 4 tables.

    Đây là bài kiểm **duy nhất** chạm tới `NULLIF(..., '')` trong policy (schema.py). Không có bài
    này thì `NULLIF` là code không ai kiểm — xoá đi mọi test khác vẫn xanh, nhưng fence vỡ với người
    gọi đặt `app.tenant_id = ''`.

    Vì sao `''` cần xử riêng, khác với "chưa set": `current_setting(..., true)` khi CHƯA set trả
    `NULL`; nhưng vài đường đặt biến lại cho **chuỗi rỗng** `''`, không phải NULL. Nếu policy cast
    thẳng `''::uuid` thì Postgres **raise** `invalid input syntax for type uuid: ""` — vỡ, nhưng vỡ
    **sai kiểu**: fence phải trả 0 dòng, không ném lỗi 500 vào mặt người dùng. `NULLIF(..., '')` biến
    `''` về `NULL`, và `tenant_id = NULL` không bao giờ đúng → 0 dòng, fail-closed.
    """
    await fixture.new_row(admin_pool, TENANT_A)

    async with pool.connection() as conn:  # type: ignore[attr-defined]
        await conn.execute(sql.SQL("SET LOCAL app.tenant_id = {}").format(sql.Literal("")))
        cur = await conn.execute(sql.SQL("SELECT count(*) FROM {}").format(sql.SQL(fixture.table)))
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


# ---------------------------------------------------------------------------------------------
# kb#47 review finding #1 (BLOCK): Postgres FK referential-integrity checks run under the table
# OWNER and bypass RLS entirely. A single-column `kb_id UUID NOT NULL REFERENCES
# kb.knowledge_bases (id)` only proves the KB exists SOMEWHERE — not that it belongs to the
# writer's own tenant. Each test below seeds a valid PARENT row under TENANT_B, then — as
# TENANT_A, with TENANT_A's own (valid, matching) `tenant_id` on the CHILD row — attempts to point
# the FK column at that TENANT_B parent. Pre-fix this INSERT succeeds (the leak, demoed live by
# dholmes0207 in the PR review comment); post-fix (composite `FOREIGN KEY (tenant_id, x)
# REFERENCES parent (tenant_id, id)`) it must raise `ForeignKeyViolation`. Each test also asserts
# the same insert against an OWN-tenant parent still succeeds (regression guard — the fix must not
# break legitimate same-tenant writes).


async def test_fk_documents_kb_id_rejects_cross_tenant(admin_pool: object) -> None:
    foreign_kb_id = uuid4()
    await _seed_kb(admin_pool, TENANT_B, foreign_kb_id, name="foreign-kb")

    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        await _seed_document(admin_pool, TENANT_A, uuid4(), foreign_kb_id, filename="leak-attempt.pdf")

    own_kb_id = uuid4()
    await _seed_kb(admin_pool, TENANT_A, own_kb_id, name="own-kb")
    await _seed_document(admin_pool, TENANT_A, uuid4(), own_kb_id, filename="legit.pdf")  # still works


async def test_fk_chunk_pointers_kb_id_rejects_cross_tenant(admin_pool: object) -> None:
    foreign_kb_id = uuid4()
    await _seed_kb(admin_pool, TENANT_B, foreign_kb_id, name="foreign-kb")
    own_doc_id, own_kb_id = uuid4(), uuid4()
    await _seed_kb(admin_pool, TENANT_A, own_kb_id, name="own-kb")
    await _seed_document(admin_pool, TENANT_A, own_doc_id, own_kb_id, filename="own-doc.pdf")

    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        await _seed_chunk_pointer(admin_pool, TENANT_A, str(uuid4()), foreign_kb_id, own_doc_id, text="leak-attempt")

    await _seed_chunk_pointer(admin_pool, TENANT_A, str(uuid4()), own_kb_id, own_doc_id, text="legit")  # still works


async def test_fk_chunk_pointers_doc_id_rejects_cross_tenant(admin_pool: object) -> None:
    foreign_kb_id, foreign_doc_id = uuid4(), uuid4()
    await _seed_kb(admin_pool, TENANT_B, foreign_kb_id, name="foreign-kb")
    await _seed_document(admin_pool, TENANT_B, foreign_doc_id, foreign_kb_id, filename="foreign-doc.pdf")
    own_kb_id = uuid4()
    await _seed_kb(admin_pool, TENANT_A, own_kb_id, name="own-kb")

    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        await _seed_chunk_pointer(admin_pool, TENANT_A, str(uuid4()), own_kb_id, foreign_doc_id, text="leak-attempt")

    own_doc_id = uuid4()
    await _seed_document(admin_pool, TENANT_A, own_doc_id, own_kb_id, filename="own-doc.pdf")
    await _seed_chunk_pointer(admin_pool, TENANT_A, str(uuid4()), own_kb_id, own_doc_id, text="legit")  # still works


# ---------------------------------------------------------------------------------------------
# kb#48 (nợ tách từ review kb#47, finding B): 3 bài trên chỉ có răng trên DB SẠCH. `CREATE TABLE
# IF NOT EXISTS` (schema.py) là no-op trên bảng đã tồn tại — không có DROP TABLE nào ở
# `conftest.py`/`ensure_all_schemas`, nên nếu 3 bảng này đã có sẵn (vd DB dev checkout nhánh
# kb#47 ở bản TRƯỚC bản vá composite-FK), `ddl()` không bao giờ nâng cấp ràng buộc — DB tình cờ
# giữ nguyên ràng buộc CŨ, và 3 bài trên (test HÀNH VI: insert cross-tenant có raise không) vẫn
# xanh nhờ ràng buộc cũ đó, bất kể `schema.py` hiện khai gì. Đo bằng cách gieo mutation (composite
# FK -> FK đơn cột) rồi KHÔNG drop bảng trước khi chạy lại: `20 passed` — xanh giả.
#
# Bài dưới đây khác 3 bài trên ở CHỖ NÓ SO SÁNH VỚI: không so kết quả một INSERT (hành vi, gián
# tiếp), mà đọc THẲNG `pg_get_constraintdef` từ `pg_constraint` — định nghĩa ràng buộc THẬT đang
# có trên DB — rồi so với một chuỗi HẰNG SỐ khai ngay trong bài test (không dựng lại từ
# `schema.py`, cố ý: nếu so với chính `schema.py` thì bài test và code luôn đồng bộ với NHAU,
# không đồng bộ với DB — mất đúng thứ cần bắt). `CREATE TABLE IF NOT EXISTS` là no-op nên bài này
# CŨNG mù trước đúng kịch bản "sửa `schema.py`, không đụng DB" như 3 bài kia — đó không phải lỗ hổng
# của bài này, đó là giới hạn vật lý của MỌI bài chỉ đọc DB. Giá trị thật của bài này là bắt được
# một lớp khác: DB đã trôi khỏi ý định `schema.py` vì lý do KHÁC ngoài "vừa sửa code chưa deploy"
# — hotfix tay, migration chạy dở, restore từ backup cũ. Verify bằng `ALTER TABLE` tay thẳng vào DB
# test (không qua `schema.py`) — xem PR description.
async def test_fk_constraint_dinh_nghia_khop_pg_catalog(admin_pool: object) -> None:
    """3 FK composite (`documents.kb_fk`, `chunk_pointers.kb_fk`, `chunk_pointers.doc_fk`) phải
    khớp ĐÚNG chuỗi `pg_get_constraintdef` kỳ vọng — không chỉ "có FK nào đó", mà đúng hình dạng
    composite `(tenant_id, x)` chặn cross-tenant (kb#47 finding #1), đọc trực tiếp từ DB đang chạy
    chứ không suy luận qua hành vi INSERT."""
    ky_vong = {
        "kb_documents_kb_fk": (
            "FOREIGN KEY (tenant_id, kb_id) REFERENCES kb.knowledge_bases(tenant_id, id) ON DELETE RESTRICT"
        ),
        "kb_chunk_pointers_kb_fk": (
            "FOREIGN KEY (tenant_id, kb_id) REFERENCES kb.knowledge_bases(tenant_id, id) ON DELETE RESTRICT"
        ),
        "kb_chunk_pointers_doc_fk": (
            "FOREIGN KEY (tenant_id, doc_id) REFERENCES kb.documents(tenant_id, id) ON DELETE RESTRICT"
        ),
    }
    async with admin_pool.connection() as conn:  # type: ignore[attr-defined]
        cur = await conn.execute(
            "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint "
            "WHERE conrelid IN ('kb.documents'::regclass, 'kb.chunk_pointers'::regclass) AND contype = 'f'"
        )
        thuc_te = dict(await cur.fetchall())

    for conname, dinh_nghia in ky_vong.items():
        assert conname in thuc_te, f"{conname} không tồn tại trên DB — bảng chưa được tạo hoặc constraint bị đổi tên"
        assert thuc_te[conname] == dinh_nghia, (
            f"{conname}: DB có {thuc_te[conname]!r}, kỳ vọng {dinh_nghia!r} — "
            "DB đã trôi khỏi schema.py (CREATE TABLE IF NOT EXISTS là no-op trên bảng đã tồn tại, "
            "kb#48)"
        )
