"""Spec-DE contract test (GREEN) — `KbSearchService.search` must raise `NotImplementedError`.
The retrieval logic itself is DE's own graded deliverable, not shipped by this template (P5 ships
the fence + the seam only). No live DB needed: the method raises before touching the pool."""

from __future__ import annotations

from uuid import UUID

import pytest
from studio_kb.search import KbSearchService


async def test_search_not_implemented() -> None:
    service = KbSearchService(pool=object())  # type: ignore[arg-type]
    with pytest.raises(NotImplementedError):
        # `tenant_id: UUID` (D-13) — chữ ký khớp `studio_contracts.KbSearch`. Vẫn raise trước khi
        # chạm pool, nên UUID nào cũng được, chỉ cần đúng kiểu để không vỡ ở khâu gọi.
        await service.search(
            query="q", tenant_id=UUID("a0000000-0000-0000-0000-000000000001"), section_roles=["public"], top_k=5
        )
