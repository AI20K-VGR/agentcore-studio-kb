"""`KbSearchService` — the OFFICIAL fence-DATA retrieval seam (P5 wire, DE impl at D17/#110).

Un-ratcheted at D17: the body no longer raises `NotImplementedError`. `search()` now DELEGATES,
one line, to `PgKbSearch.search` (`postgres.py`) — the real fenced retrieval that has been on the
spine since D13 (RLS `FORCE` on `tenant_id` + `WHERE section_role = ANY(...)` + empty-roles→`[]` +
filter-IN-SQL, never return-all-then-filter). This flip makes the official import seam
(`KbRetrieveExecutor` composition wires `KbSearchService`) run that same mechanism, instead of the
D13 direct-inject `PgKbSearch` shim.

Contract satisfied (umbrella-contract.md:138-144, R-SPEC A3/A1#3):
- Filter AT RETRIEVAL, fail-closed — a chunk outside `{tenant_id, section_roles}` never leaves this
  function (`PgKbSearch` filters in the SQL WHERE, not after the fact via the LLM).
- Runs over `get_pool()` (non-owner `studio_app`), where RLS (schema.py) actually bites.

Honest boundary — what this seam does NOT do (T6 "mức đầu", see plan D17 §0):
`section_roles` is treated as the **server-resolved authorized list** and trusted (fail-closed on
it: empty → `[]`, no wildcard). Neutralizing a CLIENT-declared `section_roles` (the T6 label-spoof
vector) happens UPSTREAM — the interpreter injects the session-resolved roles over the recipe-
declared ones before calling `search`, exactly as it already injects `tenant_id`
(`interpreter.py:291`, engine lane #111). The frozen 4-arg signature carries no caller identity
(`kb-search.v0.md §5.2`), so kb cannot resolve roles from inside this function — it can only be
fail-closed on the list it is handed. That is why #114 scopes T6 to "mức đầu".

Embedding wiring (B1, decided 2026-08-11):
`PgKbSearch(pool, embedding)` needs an embedding to embed the query; `KbSearchService(pool)` (T3
composition, `apps/studio`) constructs with the pool only. So `embedding` is OPTIONAL: when `None`,
this self-provisions a deterministic dim-8 bag-of-words stub over `studio_kb.embeddings.
derive_vector` — the SAME vector space the corpus is seeded in (`KbIngest`/T3's `_CallistoEmbedding`
both use `derive_vector`), so `KbSearchService(pool)` retrieves real hits and T3 self-XPASSes with
AIE-1 changing no call-site (QĐ-U1). Production injects a real `EmbeddingService` via the factory —
kb does not hardcode a gateway (EmbeddingService owner = AIE-1).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool
from studio_contracts.kb import KbSearchResultItem
from studio_contracts.protocols import EmbeddingService

from studio_kb.embeddings import derive_vector
from studio_kb.postgres import PgKbSearch

Pool = AsyncConnectionPool[AsyncConnection[Any]]


class _BagOfWordsEmbedding:
    """Default `EmbeddingService` when none is injected — deterministic dim-8 bag-of-words over
    `derive_vector`. NOT a semantic model: same SSOT space as `KbIngest`/T3 seeding, so query and
    seeded chunks live in one cosine space. Production replaces this via the factory (see module
    docstring)."""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [derive_vector(text) for text in texts]


class KbSearchService:
    """Implements `studio_contracts.kb.KbSearch` (P2). Constructed with the request-scoped
    `get_pool()` connection pool (composition wires this at the `kb-retrieve` node executor) so
    `kb.chunks`' RLS policy actually applies. `embedding` is optional — see module docstring."""

    def __init__(self, pool: Pool, embedding: EmbeddingService | None = None) -> None:
        self._pg = PgKbSearch(pool, embedding or _BagOfWordsEmbedding())

    async def search(
        self,
        query: str,
        tenant_id: UUID,
        section_roles: list[str],
        top_k: int,
    ) -> list[KbSearchResultItem]:
        """Fail-closed retrieval over `{tenant_id, section_roles}` — delegates to `PgKbSearch.search`
        (chữ ký 4 tham số frozen, `kb-search.v0.md`). See module docstring for the honest boundary on
        `section_roles` (client-declared neutralization is upstream, engine #111)."""
        return await self._pg.search(query, tenant_id, section_roles, top_k)
