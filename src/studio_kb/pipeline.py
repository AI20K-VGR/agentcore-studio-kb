"""KB ingestion pipeline seam (spec DE) — chunker -> embed_invoke -> index, plus
`consent_purge`/`re_index` for tenant data lifecycle. All 5 methods are intentionally
`NotImplementedError`: this class exists so composition/tests have a stable import target, not as
a working pipeline. DE fills these in as a graded deliverable; P5 ships the seam only.
"""

from __future__ import annotations

from uuid import UUID


class KbPipeline:
    """Doc-factory pipeline stub (P5, DE). Every method below raises `NotImplementedError` —
    filling in real behavior is out of P5's WIRE scope (plan.md "Out of scope": no reference
    business logic for the 4 quadrants).

    `tenant_id: UUID` throughout (D-13, #25): these are spec-DE seams DE fills later, so keeping
    the vocabulary consistent with the rest of `studio_kb` avoids a future landmine where the real
    implementation would otherwise inherit a stale `str` slug type."""

    async def chunker(self, document: str, *, tenant_id: UUID) -> list[str]:
        """Split `document` into retrieval-sized chunks. Contract: a chunk boundary must never
        span two different `section_role` labels — each chunk carries exactly one (R-SPEC A3)."""
        raise NotImplementedError("KbPipeline.chunker is spec DE")

    async def embed_invoke(self, chunks: list[str]) -> list[list[float]]:
        """Invoke the (AIE-1-owned) `EmbeddingService` for `chunks`. Contract: every returned
        vector's width must equal `studio_kb.schema.EMBEDDING_DIM`."""
        raise NotImplementedError("KbPipeline.embed_invoke is spec DE")

    async def index(
        self,
        tenant_id: UUID,
        section_role: str,
        chunks: list[str],
        embeddings: list[list[float]],
    ) -> None:
        """Persist `chunks`+`embeddings` into `kb.chunks` scoped to `tenant_id`. Contract: every
        inserted row's `tenant_id` must equal the current RLS session's `app.tenant_id` — a
        mismatch is rejected by the `WITH CHECK` policy (schema.py), never silently corrected."""
        raise NotImplementedError("KbPipeline.index is spec DE")

    async def consent_purge(self, tenant_id: UUID) -> int:
        """Delete every `kb.chunks` row for `tenant_id` (consent / right-to-erasure). Contract:
        fail-closed — must never delete a row belonging to another tenant."""
        raise NotImplementedError("KbPipeline.consent_purge is spec DE")

    async def re_index(self, tenant_id: UUID) -> int:
        """Re-embed and rewrite every `kb.chunks` row for `tenant_id` (e.g. after an embedding-model
        upgrade). Contract: must preserve each row's `chunk_id`/`section_role`."""
        raise NotImplementedError("KbPipeline.re_index is spec DE")
