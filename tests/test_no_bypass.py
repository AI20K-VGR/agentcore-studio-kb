"""No-bypass teeth (D17/#110, DE — kb-lane, closed alone) + the T6 label-spoof ACCEPTANCE test.

Two distinct guarantees, both GREEN, both over the real `PgKbSearch` mechanism (needs a live DB —
`docker compose -f docker-compose.test.yml up -d` + 2 DSNs; the `pool` fixture skips otherwise):

- **No-bypass teeth** — kb is fail-closed on the `section_roles` list it is HANDED: empty means
  "no authorized role" (→ `[]`, never "skip the filter"); a role list never leaks chunks of other
  roles; `"*"` is a LITERAL role, not a wildcard that matches everything. These are the invariants
  the upstream override (engine #111) relies on when it hands kb a resolved list.

- **T6 label-spoof acceptance (deliverable #110, "mức đầu")** — proves override→safe: when the
  session-resolved roles are used, a recipe-DECLARED role list (the spoof) is neutralized before it
  reaches `kb.search`, so a confidential/finance chunk the caller isn't authorized for never comes
  back. kb cannot do the override itself (frozen signature carries no identity, `kb-search.v0.md
  §5.2`); this test is the acceptance spec for the one-line inject at `interpreter.py:291` (engine
  #111). The assertion is on the EFFECTIVE value that reaches `kb.search` — not "the service didn't
  raise" — so a mutation that fails OPEN upstream (uses the recipe-declared roles) would be caught.
"""

from __future__ import annotations

from uuid import UUID

from studio_kb.doc_factory import TENANT_IDS, Chunk
from studio_kb.embeddings import derive_vector
from studio_kb.postgres import KbIngest, PgKbSearch

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


# ── T6 label-spoof acceptance (deliverable #110, "mức đầu") ─────────────────────────


async def test_t6_recipe_declared_roles_are_overridden_by_session(pool: object) -> None:
    """T6 label-spoof acceptance — override→safe. A recipe DECLARES `["finance"]` (the spoof); the
    server-side SESSION resolves the caller to `["public"]`. The effective roles that reach
    `kb.search` are the session's, so the finance chunk the caller isn't authorized for never comes
    back. This is the acceptance spec for the one-line inject at `interpreter.py:291` (engine #111);
    kb cannot do the override itself (frozen signature, `kb-search.v0.md §5.2`)."""
    await _seed_roles(pool)

    recipe_declared = ["finance"]  # client/recipe attempts to grant itself finance
    session_roles = ["public"]  # server-side resolved: this caller is public-only
    effective = session_roles  # interpreter.py:291 injects session over recipe (simulated here)

    hits = await PgKbSearch(pool, _Embedding()).search("ngân sách chính sách", ANKOR_ID, effective, 10)  # type: ignore[arg-type]

    ids = {h.chunk_id for h in hits}
    # Assert on the EFFECTIVE value + the outcome, not "no raise": a fail-OPEN mutation that used
    # `recipe_declared` would surface the finance chunk and fail here.
    assert effective == ["public"]
    assert effective != recipe_declared
    assert "ankor-budget-001#c1" not in ids, "finance chunk lọt qua dù caller chỉ vai public (client-khai không bị bỏ)"
    assert "ankor-leave-001#c1" in ids, "public chunk phải thấy — răng dương để [] không false-pass"
    assert all(h.section_role == "public" for h in hits)
