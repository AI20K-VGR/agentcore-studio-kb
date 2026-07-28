"""AgentCore Studio KB — doc-factory, kb.search fence-DATA, trace/cost sink. Owner: DE.

Phase 5 (KB Fence): `kb.chunks` DDL + RLS fence lands in `schema.py`; `KbSearchService`
(`search.py`) and `KbPipeline` (`pipeline.py`) are spec-DE stubs (`NotImplementedError` bodies)
exported here as the stable public seam other packages/tests import against.

Sprint 1 (D4) thêm **bản tĩnh** để xâu kim end-to-end trước khi tầng Postgres chạy được:
`load_callisto` cắt `docs/callisto/*.md` thành chunk, `StaticKbSearch` tìm trên đó và thoả
`studio_contracts.KbSearch`. Đây là thứ AIE-1 tiêm vào `KbRetrieveExecutor` ở D4 thay cho
`EmptyKbSearch` — KHÔNG phải `KbSearchService` (bản fenced + Postgres, vẫn là spec-DE cho S2–S3).
Xem docstring `static_search.py` để biết đường nâng cấp giữa hai bản.

Sprint 1 (D7) thêm `load_callisto_embeddings` — **đường đọc duy nhất** cho vector của 25 chunk
Callisto (`golden/embeddings-callisto-v0.json`). Ai cần vector thì gọi nó, cấm tự tính sha256 tại
chỗ: hai chỗ tự tính là hai nguồn sự thật. Xem docstring `embeddings.py`.
"""

from __future__ import annotations

from studio_kb.doc_factory import Chunk, load_callisto
from studio_kb.embeddings import load_callisto_embeddings
from studio_kb.search import KbSearchService
from studio_kb.static_search import StaticKbSearch

__all__ = [
    "Chunk",
    "KbSearchService",
    "StaticKbSearch",
    "load_callisto",
    "load_callisto_embeddings",
]
