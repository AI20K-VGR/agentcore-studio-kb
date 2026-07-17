"""Spec-DE contract test (GREEN) — `KbSearchService.search` must raise `NotImplementedError`.
The retrieval logic itself is DE's own graded deliverable, not shipped by this template (P5 ships
the fence + the seam only). No live DB needed: the method raises before touching the pool."""

from __future__ import annotations

import pytest
from studio_kb.search import KbSearchService


async def test_search_not_implemented() -> None:
    service = KbSearchService(pool=object())  # type: ignore[arg-type]
    with pytest.raises(NotImplementedError):
        await service.search(query="q", tenant="tenant-a", section_roles=["public"], top_k=5)
