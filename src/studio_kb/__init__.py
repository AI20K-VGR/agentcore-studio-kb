"""AgentCore Studio KB — doc-factory, kb.search fence-DATA, trace/cost sink. Owner: DE.

Phase 5 (KB Fence): `kb.chunks` DDL + RLS fence lands in `schema.py`; `KbSearchService`
(`search.py`) and `KbPipeline` (`pipeline.py`) are spec-DE stubs (`NotImplementedError` bodies)
exported here as the stable public seam other packages/tests import against.
"""

from __future__ import annotations

from studio_kb.search import KbSearchService

__all__ = ["KbSearchService"]
