"""Leak-test WITH TEETH (F5) — RED-by-design until `kb.search` (search.py) is implemented as a
real, non-leaky retrieval (spec DE). Real cross-tenant EXCLUSION assertions through the
`KbSearchService` APP PATH — a leaky implementation still FAILS these (NEVER
`pytest.raises(NotImplementedError)`, per plan.md Decision #3 + phase-5 Risks table: "leak-test
'xanh giả'"). Marked `xfail(strict=False)` so the aggregate suite stays green while these keep
real teeth. Un-ratchet (F5): the moment DE makes `kb.search` pass these for real, remove the
`xfail` marker below (README documents who/when to flip — P5/P9) and this becomes a hard gate.
"""

from __future__ import annotations

import pytest
from psycopg import sql
from studio_kb.search import KbSearchService


async def _seed_chunk(pool: object, tenant_id: str, chunk_id: str, text: str, section_role: str = "public") -> None:
    async with pool.connection() as conn:  # type: ignore[attr-defined]
        await conn.execute(sql.SQL("SET LOCAL app.tenant_id = {}").format(sql.Literal(tenant_id)))
        await conn.execute(
            "INSERT INTO kb.chunks (chunk_id, tenant_id, section_role, text) VALUES (%s, %s, %s, %s)",
            (chunk_id, tenant_id, section_role, text),
        )


@pytest.mark.xfail(reason="spec DE fills kb.search; un-ratchet removes this", strict=False)
async def test_t1_idor(admin_pool: object, pool: object) -> None:
    """T1 IDOR: tenant-a searches; tenant-b owns a chunk that must never surface in tenant-a's
    results. Real assertion — a leaky impl that returns everyone's chunks still fails this."""
    await _seed_chunk(admin_pool, "tenant-a", "chunk-a-1", "tenant-a secret doc")
    await _seed_chunk(admin_pool, "tenant-b", "chunk-b-1", "tenant-b secret doc")

    service = KbSearchService(pool)  # type: ignore[arg-type]
    results = await service.search(query="secret doc", tenant="tenant-a", section_roles=["public"], top_k=10)

    result_chunk_ids = {item.chunk_id for item in results}
    # Positive inclusion FIRST — the requesting tenant's own matching chunk MUST come back. Without
    # this, a lazy/broken impl that returns an empty list would false-pass the exclusion assertion
    # below (∅ trivially excludes everything). Retrieval must actually work before exclusion means
    # anything (dual-review catch: gemini F4).
    assert "chunk-a-1" in result_chunk_ids
    assert "chunk-b-1" not in result_chunk_ids
    assert all(item.tenant == "tenant-a" for item in results)


@pytest.mark.xfail(reason="spec DE fills kb.search; un-ratchet removes this", strict=False)
async def test_t6_label_spoof(admin_pool: object, pool: object) -> None:
    """T6 label-spoof: tenant-a owns a `section_role="confidential"` chunk. The request itself
    declares `section_roles=["confidential"]` — the server must resolve authorized roles itself
    (never trust the client-declared list) — server-side resolution not shipped in P5's spec-DE
    stub means the confidential chunk must still be excluded from what an unauthorized caller
    gets back."""
    await _seed_chunk(admin_pool, "tenant-a", "chunk-public", "public doc", section_role="public")
    await _seed_chunk(admin_pool, "tenant-a", "chunk-confidential", "confidential doc", section_role="confidential")

    service = KbSearchService(pool)  # type: ignore[arg-type]
    results = await service.search(query="doc", tenant="tenant-a", section_roles=["confidential"], top_k=10)

    result_chunk_ids = {item.chunk_id for item in results}
    assert "chunk-confidential" not in result_chunk_ids
