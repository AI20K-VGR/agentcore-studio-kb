"""`KbSearchService` — fence-DATA implementation seam (P5, DE). Body intentionally
`NotImplementedError`: the real retrieval logic is DE's own graded deliverable (spec DE, R-SPEC
A1#3/A4), not shipped by this template. P5 ships the WIRE (schema + RLS fence + this stable
import seam) only.

Binding contract for the real implementation, when DE builds it (umbrella-contract.md:138-144,
R-SPEC A3, A1#3):
- Filter AT RETRIEVAL, fail-closed — a chunk outside the caller's authorized scope must never
  leave this function. Filtering "after the fact" via the LLM (return-everything-then-let-the-
  model-decide) is a forbidden anti-pattern.
- `section_roles` resolves SERVER-SIDE — a client-declared `section_roles` value is a request,
  not a grant; the server must independently resolve which roles the caller is actually
  authorized for. Trusting the client-declared list verbatim is exactly what enables T6
  label-spoof.
- Must run over `get_pool()` (non-owner `studio_app` role), never `get_admin_pool()` — RLS
  (schema.py) only applies to a non-owner connection.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool
from studio_contracts.kb import KbSearchResultItem

Pool = AsyncConnectionPool[AsyncConnection[Any]]


class KbSearchService:
    """Implements `studio_contracts.kb.KbSearch` (P2). Constructed with the request-scoped
    `get_pool()` connection pool (composition wires this at P6+/AIE-1's `kb-retrieve` node
    executor) so `kb.chunks`' RLS policy actually applies."""

    def __init__(self, pool: Pool) -> None:
        self._pool = pool

    async def search(
        self,
        query: str,
        tenant_id: UUID,
        section_roles: list[str],
        top_k: int,
    ) -> list[KbSearchResultItem]:
        """Spec DE — intentionally unimplemented. See module docstring for the binding contract
        the real implementation must satisfy (fail-closed retrieval, server-side section_roles,
        no return-all-then-filter)."""
        raise NotImplementedError("KbSearchService.search is spec DE — see module docstring contract")
