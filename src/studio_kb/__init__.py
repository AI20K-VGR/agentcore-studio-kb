"""AgentCore Studio KB — doc-factory, kb.search fence-DATA, trace/cost sink. Owner: DE.

Phase 5 (KB Fence): `kb.chunks` DDL + RLS fence lands in `schema.py`; `KbSearchService`
(`search.py`) and `KbPipeline` (`pipeline.py`) ship as the stable public seam other packages/tests
import against. At D17 (#110) `KbSearchService` is un-ratcheted — its body now delegates to the real
`PgKbSearch` (see below); `KbPipeline` stays a spec-DE stub (`NotImplementedError` bodies).

Sprint 1 (D4) thêm **bản tĩnh** để xâu kim end-to-end trước khi tầng Postgres chạy được:
`load_callisto` cắt `docs/callisto/*.md` thành chunk, `StaticKbSearch` tìm trên đó và thoả
`studio_contracts.KbSearch`. Đây là thứ AIE-1 tiêm vào `KbRetrieveExecutor` ở D4 thay cho
`EmptyKbSearch` — KHÔNG phải `KbSearchService` (bản fenced + Postgres, vẫn là spec-DE cho S2–S3).
Xem docstring `static_search.py` để biết đường nâng cấp giữa hai bản.

Sprint 1 (D7) thêm `load_callisto_embeddings` — **đường đọc duy nhất** cho vector của 140 chunk
Callisto (`golden/embeddings-callisto-v0.json`, corpus phình 25→140 ở D12). Ai cần vector thì gọi
nó, cấm tự tính sha256 tại chỗ: hai chỗ tự tính là hai nguồn sự thật. Xem docstring `embeddings.py`.

Sprint 2 (D13) thêm tầng Postgres thật (`postgres.py`) vào seam công khai: `KbIngest` (ghi:
`Chunk` → embed → `kb.chunks` per-tenant, idempotent, non-owner pool để `WITH CHECK` cắn) và
`PgKbSearch` (đọc: cosine trên pgvector, lọc fail-closed `tenant_id`+`section_role`). Cả hai thoả
`studio_contracts.KbSearch`/nhận `EmbeddingService` tiêm vào — đây là thứ AIE-1 tiêm vào
`KbRetrieveExecutor` thay `StaticKbSearch`/`EmptyKbSearch` (ghép thật DE×AIE-1, #91).

Sprint 2 (D17, #110) **lật seam chính thức**: `KbSearchService.search` (`search.py`) nay uỷ quyền một
dòng sang `PgKbSearch.search` — đường vào chính thức chạy fence fail-closed thật (RLS tenant + `WHERE
section_role`). T1 IDOR thành gate cứng ở `test_leak.py`; T6 label-spoof (client tự khai) đóng mức đầu,
override thật nằm upstream (`interpreter.py:291`, engine #111) — xem `test_no_bypass.py`.
"""

from __future__ import annotations

from studio_kb.doc_factory import Chunk, load_callisto
from studio_kb.embeddings import load_callisto_embeddings
from studio_kb.postgres import KbIngest, PgKbSearch
from studio_kb.search import KbSearchService
from studio_kb.static_search import StaticKbSearch

__all__ = [
    "Chunk",
    "KbIngest",
    "KbSearchService",
    "PgKbSearch",
    "StaticKbSearch",
    "load_callisto",
    "load_callisto_embeddings",
]
