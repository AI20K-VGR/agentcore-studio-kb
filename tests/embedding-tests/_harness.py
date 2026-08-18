"""Logic thuần cho bộ eval embedding (test-first, model-agnostic) — không fixture, import được.

Đây là *dụng cụ đo* để CHỌN phương thức embedding sau, KHÔNG chọn model ở đây. Harness nhận bất kỳ
provider shape `EmbeddingService` (`embed(texts) -> list[list[float]]`, sync hoặc async), chấm nó trên
tập case có nhãn (DE sở hữu giá trị) qua retrieval in-memory mô phỏng `PgKbSearch` (lọc tenant+role →
cosine → top-k), rồi so **tương đối** với baseline dim-8 đóng băng.

Ràng buộc: `.importlinter` cấm `studio_kb` chạm `studio_app` → chỉ import `studio_kb`/`studio_contracts`
+ stdlib. KHÔNG ghim `EMBEDDING_DIM` — provider số chiều nào cũng chấm được.
"""

from __future__ import annotations

import inspect
import json
import math
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import cast
from uuid import UUID

from studio_kb.doc_factory_v2 import load_corpus_v2
from studio_kb.embeddings import derive_vector

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def tokens(text: str) -> set[str]:
    """Token thô: hạ chữ thường, giữ chữ-số Unicode (tiếng Việt), bỏ dấu câu — CÙNG luật `_tokens`
    của `static_search.py` để phép đo trùng-token của test integrity khớp thứ một lexical baseline thấy."""
    return set(_TOKEN_RE.findall(text.lower()))


def token_overlap(query: str, text: str) -> int:
    """Số token phân biệt query chia sẻ với text — thước đo 'độ dễ với lexical' cho luật dựng case."""
    return len(tokens(query) & tokens(text))


# ── đường dẫn ────────────────────────────────────────────────────────────────
_HERE = Path(__file__).resolve().parent
CORPUS_ROOT = _HERE.parents[1] / "docs" / "callisto-2.0"
CASES_DIR = _HERE / "cases"
BASELINE_PATH = _HERE / "baseline-dim8.json"

TOP_K = 10  # top-k cho recall@k/MRR — cùng bậc top_k thực nghiệm wire 2.0
STRATA = ("S1", "S2", "S3", "S4", "S5")


# ── mô hình case ─────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Case:
    """Một case eval có nhãn. DE sở hữu GIÁ TRỊ (query/expected/decoy); harness chỉ tiêu thụ.

    `expected_citation` rỗng ⇒ negative/no-answer (S5): retrieval KHÔNG nên trả gì trong tenant+role."""

    id: str
    query: str
    tenant: str
    section_roles: tuple[str, ...]
    expected_citation: tuple[str, ...]
    stratum: str
    decoy_hint: tuple[str, ...] = field(default=())
    notes: str = ""


@lru_cache(maxsize=1)
def load_cases() -> tuple[Case, ...]:
    """Đọc mọi `cases/*.json` → tuple[Case] sắp theo id (ổn định). JSON, không YAML (kb không kéo pyyaml)."""
    cases: list[Case] = []
    seen: set[str] = set()
    for path in sorted(CASES_DIR.glob("*.json")):
        for raw in json.loads(path.read_text(encoding="utf-8")):
            cid = raw["id"]
            if cid in seen:
                raise ValueError(f"case id trùng: {cid!r} (file {path.name})")
            seen.add(cid)
            cases.append(
                Case(
                    id=cid,
                    query=raw["query"],
                    tenant=raw["tenant"],
                    section_roles=tuple(raw["section_roles"]),
                    expected_citation=tuple(raw.get("expected_citation", ())),
                    stratum=raw["stratum"],
                    decoy_hint=tuple(raw.get("decoy_hint", ())),
                    notes=raw.get("notes", ""),
                )
            )
    return tuple(sorted(cases, key=lambda c: c.id))


# ── vector / cosine ──────────────────────────────────────────────────────────
def to_vectors(provider: object, texts: list[str]) -> list[list[float]]:
    """Gọi `provider.embed(texts)`; chấp nhận sync hoặc async (coroutine → chạy nền)."""
    result = provider.embed(texts)  # type: ignore[attr-defined]
    if inspect.iscoroutine(result):
        import asyncio

        result = asyncio.run(result)
    return cast("list[list[float]]", result)


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    """Cosine đầy đủ (không giả định đã L2 — provider ứng viên có thể chưa chuẩn hoá). Vector 0 → 0.0."""
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


class BaselineDim8:
    """Provider mặc định = bag-of-words dim-8 `derive_vector` (baseline hiện tại của spine)."""

    name = "baseline-dim8"

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [derive_vector(t) for t in texts]


# ── retrieval in-memory (lọc TRƯỚC rồi xếp hạng — cùng ngữ nghĩa PgKbSearch) ─
@dataclass(frozen=True)
class Indexed:
    chunk_id: str
    tenant_id: UUID
    section_role: str
    vector: tuple[float, ...]


class InMemoryRetriever:
    """Cosine trên corpus đã embed, lọc `{tenant_id, section_roles}` TRƯỚC khi xếp hạng. Tie-break
    `chunk_id` cho thứ hạng tất định (đúng như `StaticKbSearch`/`PgKbSearch`)."""

    def __init__(self, indexed: list[Indexed]) -> None:
        self._indexed = indexed

    def search(
        self, query_vec: Sequence[float], tenant_id: UUID, section_roles: Sequence[str], top_k: int
    ) -> list[tuple[str, float]]:
        """Trả `[(chunk_id, cosine)]` top-k đã lọc + xếp giảm dần. Kèm score để S5 (no-answer) đo
        'độ tự tin trả nhầm' — retriever không có ngưỡng cứng nên top-k luôn có phần tử."""
        if top_k <= 0:
            return []
        allowed = set(section_roles)
        scored: list[tuple[float, str]] = []
        for row in self._indexed:
            if row.tenant_id != tenant_id or row.section_role not in allowed:
                continue
            scored.append((cosine(query_vec, row.vector), row.chunk_id))
        scored.sort(key=lambda pair: (-pair[0], pair[1]))
        return [(cid, score) for score, cid in scored[:top_k]]


def build_retriever(provider: object) -> tuple[InMemoryRetriever, dict[str, str]]:
    """Embed toàn corpus 2.0 bằng provider → retriever + {chunk_id: text} (để test integrity soi token)."""
    chunks = load_corpus_v2(CORPUS_ROOT)
    vectors = to_vectors(provider, [c.text for c in chunks])
    indexed = [Indexed(c.chunk_id, c.tenant_id, c.section_role, tuple(v)) for c, v in zip(chunks, vectors, strict=True)]
    texts = {c.chunk_id: c.text for c in chunks}
    return InMemoryRetriever(indexed), texts


# ── metric ───────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class CaseResult:
    case_id: str
    stratum: str
    retrieved: tuple[str, ...]
    top_score: float  # cosine của hit#1 (S5: đo 'độ tự tin trả nhầm')
    recall_at_k: float  # non-S5: |expected ∩ retrieved|/|expected|. S5: 1 - top_score ('độ sạch', cao=tốt)
    reciprocal_rank: float  # 1/hạng expected đầu; 0 nếu trượt (không dùng cho S5)


def score_case(case: Case, results: list[tuple[str, float]]) -> CaseResult:
    ids = tuple(cid for cid, _ in results)
    top_score = results[0][1] if results else 0.0
    expected = set(case.expected_citation)
    if not expected:  # S5 negative: cùng chiều recall (cao=tốt) = mức KHÔNG tự tin trả nhầm.
        return CaseResult(case.id, case.stratum, ids, top_score, 1.0 - top_score, 0.0)
    hit = expected & set(ids)
    recall = len(hit) / len(expected)
    rr = next((1.0 / rank for rank, cid in enumerate(ids, 1) if cid in expected), 0.0)
    return CaseResult(case.id, case.stratum, ids, top_score, recall, rr)


def build_report(provider: object) -> dict[str, CaseResult]:
    """Chấm TOÀN BỘ case một lần cho provider → {case_id: CaseResult}. Order-independent."""
    retriever, _ = build_retriever(provider)
    from studio_kb.doc_factory import resolve_tenant_id

    cases = load_cases()
    qvecs = to_vectors(provider, [c.query for c in cases]) if cases else []
    out: dict[str, CaseResult] = {}
    for case, qv in zip(cases, qvecs, strict=True):
        results = retriever.search(qv, resolve_tenant_id(case.tenant), case.section_roles, TOP_K)
        out[case.id] = score_case(case, results)
    return out


def stratum_recall(report: dict[str, CaseResult], stratum: str) -> float:
    vals = [r.recall_at_k for r in report.values() if r.stratum == stratum]
    return sum(vals) / len(vals) if vals else 0.0


def stratum_mrr(report: dict[str, CaseResult], stratum: str) -> float:
    vals = [r.reciprocal_rank for r in report.values() if r.stratum == stratum and stratum != "S5"]
    return sum(vals) / len(vals) if vals else 0.0
