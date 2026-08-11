"""No-bypass teeth (D17/#110, DE — kb-lane, closed alone). Needs a live DB (`docker compose -f
docker-compose.test.yml up -d` + 2 DSNs; the `pool` fixture skips otherwise).

kb is fail-closed on the `section_roles` list it is HANDED: empty means "no authorized role"
(→ `[]`, never "skip the filter"); a role list never leaks chunks of other roles; `"*"` is a LITERAL
role, not a wildcard. These are the invariants the upstream override (engine #111) relies on.

**Two of these run THROUGH `KbSearchService`, not just `PgKbSearch`** — the seam D17 flipped is the
thing under test, so the role axis must be exercised through it (otherwise a mutation on the
delegation line — e.g. hardcoding the roles argument — survives with the whole suite still green;
that gap was review kb#19 F1). The pure-SQL properties (empty/`"*"`) stay on `PgKbSearch` directly.

**Scope note — this does NOT close T6.** Neutralizing a CLIENT/recipe-declared `section_roles` (the
label-spoof vector) is the inject at `interpreter.py:291` (engine #111), NOT in kb — the frozen 4-arg
signature carries no caller identity (`kb-search.v0.md §5.2`). These teeth only prove kb honours the
list it is given. The end-to-end T6 proof is an engine test (#111); the kb-side xfail marker on
`test_leak.py::test_t6_label_spoof` is `strict=True` so an unexpected XPASS is loud, not swallowed.
"""

from __future__ import annotations

from uuid import UUID

from studio_kb.doc_factory import TENANT_IDS, Chunk
from studio_kb.embeddings import derive_vector
from studio_kb.postgres import KbIngest, PgKbSearch
from studio_kb.search import KbSearchService

ANKOR_ID = TENANT_IDS["ankor"]


class _Embedding:
    """dim-8 bag-of-words over `derive_vector` — SSOT space shared with ingest and T3."""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [derive_vector(text) for text in texts]


def _chunk(chunk_id: str, section_role: str, text: str, tenant_id: UUID = ANKOR_ID) -> Chunk:
    return Chunk(chunk_id=chunk_id, text=text, tenant_id=tenant_id, section_role=section_role)


async def _seed_roles(pool: object) -> None:
    """Seed one chunk per role (public/hr/finance) for tenant ankor."""
    await KbIngest(pool, _Embedding()).ingest(  # type: ignore[arg-type]
        [
            _chunk("ankor-leave-001#c1", "public", "chính sách nghỉ phép công khai"),
            _chunk("ankor-salary-001#c1", "hr", "thang lương gồm 6 bậc nhân sự"),
            _chunk("ankor-budget-001#c1", "finance", "ngân sách quý tài chính bí mật"),
        ]
    )


# ── No-bypass teeth ───────────────────────────────────────────────────────────────


async def test_empty_roles_is_no_grant_not_skip_filter(pool: object) -> None:
    """`section_roles=[]` = "no authorized role" → `[]`. The classic fence leak is reading empty as
    "no filter" (request declares nothing → sees everything)."""
    await _seed_roles(pool)
    assert await PgKbSearch(pool, _Embedding()).search("chính sách", ANKOR_ID, [], 10) == []  # type: ignore[arg-type]


async def test_role_list_never_leaks_other_roles(pool: object) -> None:
    """Asking for `["hr"]` returns hr only — never a finance or public chunk. Losing the
    `WHERE section_role = ANY(...)` clause is the silent T6 hole with no RLS behind it."""
    await _seed_roles(pool)
    hits = await PgKbSearch(pool, _Embedding()).search("ngân sách lương chính sách", ANKOR_ID, ["hr"], 10)  # type: ignore[arg-type]

    ids = {h.chunk_id for h in hits}
    assert "ankor-salary-001#c1" in ids, "đúng vai hr phải thấy — răng dương để [] không false-pass"
    assert "ankor-budget-001#c1" not in ids, "rò chunk finance sang caller chỉ có vai hr"
    assert "ankor-leave-001#c1" not in ids, "rò chunk public sang caller chỉ có vai hr"
    assert all(h.section_role == "hr" for h in hits)


async def test_star_is_a_literal_role_not_a_wildcard(pool: object) -> None:
    """`"*"` must be treated as an ordinary role string, never a wildcard that returns everything.
    No seeded chunk has role `"*"`, so the result must be empty — a wildcard reading would return
    all three."""
    await _seed_roles(pool)
    assert await PgKbSearch(pool, _Embedding()).search("chính sách lương ngân sách", ANKOR_ID, ["*"], 10) == []  # type: ignore[arg-type]


# ── No-bypass THROUGH the flipped seam (KbSearchService — review kb#19 F1) ───────────


async def test_seam_honours_caller_roles(pool: object) -> None:
    """The role axis, exercised through `KbSearchService` (the seam D17 flipped) — NOT `PgKbSearch`
    directly. Asking for `["hr"]` returns hr only. This is the tooth that dies when the delegation
    line drops/hardcodes `section_roles`; without it that mutation survives green (review kb#19 F1)."""
    await _seed_roles(pool)
    hits = await KbSearchService(pool).search("ngân sách lương chính sách", ANKOR_ID, ["hr"], 10)  # type: ignore[arg-type]

    ids = {h.chunk_id for h in hits}
    assert "ankor-salary-001#c1" in ids, "đúng vai hr phải thấy — răng dương để [] không false-pass"
    assert "ankor-budget-001#c1" not in ids, "seam rò chunk finance sang caller chỉ có vai hr"
    assert "ankor-leave-001#c1" not in ids, "seam rò chunk public sang caller chỉ có vai hr"
    assert all(h.section_role == "hr" for h in hits)


async def test_seam_public_caller_sees_no_finance(pool: object) -> None:
    """Second role value through the seam (public) — a public-only caller never sees the finance
    chunk. Kills the delegation mutant from the other direction (hardcoded roles incl. finance would
    surface `ankor-budget-001#c1` here). NOT a T6 proof: whether the caller's roles are the session-
    resolved ones (vs recipe-declared) is decided upstream at `interpreter.py:291` (#111)."""
    await _seed_roles(pool)
    hits = await KbSearchService(pool).search("ngân sách chính sách", ANKOR_ID, ["public"], 10)  # type: ignore[arg-type]

    ids = {h.chunk_id for h in hits}
    assert "ankor-leave-001#c1" in ids, "public chunk phải thấy — răng dương để [] không false-pass"
    assert "ankor-budget-001#c1" not in ids, "seam rò chunk finance sang caller chỉ có vai public"
    assert all(h.section_role == "public" for h in hits)
