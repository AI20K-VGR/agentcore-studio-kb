"""KB ingestion pipeline seam (spec DE) — chunker -> embed_invoke -> index, plus
`consent_purge`/`re_index` for tenant data lifecycle. All 5 methods are intentionally
`NotImplementedError`: this class exists so composition/tests have a stable import target, not as
a working pipeline. DE fills these in as a graded deliverable; P5 ships the seam only.
"""

from __future__ import annotations


class KbPipeline:
    """Doc-factory pipeline stub (P5, DE). Every method below raises `NotImplementedError` —
    filling in real behavior is out of P5's WIRE scope (plan.md "Out of scope": no reference
    business logic for the 4 quadrants)."""

    async def chunker(self, document: str, *, tenant: str) -> list[str]:
        """Split `document` into retrieval-sized chunks. Contract: a chunk boundary must never
        span two different `section_role` labels — each chunk carries exactly one (R-SPEC A3)."""
        raise NotImplementedError("KbPipeline.chunker is spec DE")

    async def embed_invoke(self, chunks: list[str]) -> list[list[float]]:
        """Invoke the (AIE-1-owned) `EmbeddingService` for `chunks`. Contract: every returned
        vector's width must equal `studio_kb.schema.EMBEDDING_DIM`."""
        raise NotImplementedError("KbPipeline.embed_invoke is spec DE")

    async def index(
        self,
        tenant: str,
        section_role: str,
        chunks: list[str],
        embeddings: list[list[float]],
    ) -> None:
        """Persist `chunks`+`embeddings` into `kb.chunks` scoped to `tenant`. Contract: every
        inserted row's `tenant_id` must equal the current RLS session's `app.tenant_id` — a
        mismatch is rejected by the `WITH CHECK` policy (schema.py), never silently corrected."""
        raise NotImplementedError("KbPipeline.index is spec DE")

    async def consent_purge(self, tenant: str) -> int:
        """Delete every `kb.chunks` row for `tenant` (consent / right-to-erasure). Contract:
        fail-closed — must never delete a row belonging to another tenant."""
        raise NotImplementedError("KbPipeline.consent_purge is spec DE")

    async def re_index(self, tenant: str) -> int:
        """Re-embed and rewrite every `kb.chunks` row for `tenant` (e.g. after an embedding-model
        upgrade). Contract: must preserve each row's `chunk_id`/`section_role`."""
        raise NotImplementedError("KbPipeline.re_index is spec DE")
