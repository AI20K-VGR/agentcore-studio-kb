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
SPLIT_PATH = _HERE / "validation-split.json"  # NGOÀI `cases/` — `load_cases` glob `cases/*.json`

# top-k cho hit@k/MRR. ĐÚNG BẰNG `top_k` recipe production dựng ra (`workbench/builder.py:219,292`
# — node `kb-retrieve` hardcode `"top_k": 3`), nên "trúng" ở đây nghĩa là LLM THẬT SỰ nhìn thấy chunk
# đúng. Trước đây là 10 với chú thích "cùng bậc top_k thực nghiệm wire 2.0" — sai: không call-site
# production nào dùng 10 (builder=3, `KbRetrieveExecutor` fallback=5), nên recall@10 tính điểm cho cả
# những lần chunk đúng xếp hạng 4–10 mà production không bao giờ đưa vào prompt.
TOP_K = 3
# Độ sâu retrieve dùng để tính hit@5/MRR@5 — luôn lấy 5, rồi hit@1/hit@3 cắt từ CHÍNH danh sách này
# (không retrieve lại), nên thứ hạng nhất quán giữa ba con số. TOP_K=3 khớp `builder.py:219,292`
# (mặc định production); MAX_K=5 khớp fallback của `KbRetrieveExecutor` (`search.py`) — cả hai đều
# là call-site thật, không phải số chọn tuỳ ý cho "ngữ cảnh".
MAX_K = 5
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


# ── tách validation / test ───────────────────────────────────────────────────
# Vì sao phải tách (kb#38, sai sót phương pháp #2): ngưỡng gate `decoy_fall` 0.35 của bản báo cáo
# trước được chọn bằng cách quét trên CHÍNH 300 case dùng để báo cáo. Fit tham số vào nhiễu của tập
# mình sẽ công bố ⇒ con số công bố đẹp hơn thực tế một cách có hệ thống, và không còn tập độc lập
# nào để phát hiện.
#
# Split ĐÓNG BĂNG trong `cases/validation-split.json`, KHÔNG tính lại lúc chạy. Tính lại thì thêm
# một case là đảo cả hai tập — tham số tune trên val cũ bỗng được chấm trên val mới mà không ai hay.
# Sinh một lần bằng `make_validation_split.py`; `test_validation_split.py` khoá tính toàn vẹn.


@lru_cache(maxsize=1)
def load_validation_ids() -> frozenset[str]:
    """Tập id thuộc validation (đọc từ file đóng băng). Thiếu file ⇒ lỗi rõ, không âm thầm coi là rỗng
    — validation rỗng nghĩa là mọi tham số lại được tune trên tập báo cáo, đúng thứ split này ngăn."""
    if not SPLIT_PATH.exists():
        raise FileNotFoundError(f"chưa có {SPLIT_PATH.name} — chạy `make_validation_split.py` để sinh")
    return frozenset(json.loads(SPLIT_PATH.read_text(encoding="utf-8"))["validation"])


def cases_for(part: str = "test") -> tuple[Case, ...]:
    """Case của một phần: `"validation"` (tune tham số) · `"test"` (báo cáo số cuối) · `"all"`.

    Mặc định `"test"` chứ không `"all"`: mặc định an toàn phải là tập KHÔNG bị tune trên nó."""
    if part not in ("validation", "test", "all"):
        raise ValueError(f"part phải là 'validation'/'test'/'all', không phải {part!r}")
    if part == "all":
        return load_cases()
    val = load_validation_ids()
    want_in = part == "validation"
    return tuple(c for c in load_cases() if (c.id in val) is want_in)


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
    # `embedding_input` (không phải `.text`) — CÙNG chuỗi mà đường ghi thật embed (`pipeline.py::
    # embed_invoke`). Nếu harness embed `.text` còn production embed `embedding_input` thì mọi con số
    # ở đây đo một hệ thống không tồn tại.
    vectors = to_vectors(provider, [c.embedding_input for c in chunks])
    indexed = [Indexed(c.chunk_id, c.tenant_id, c.section_role, tuple(v)) for c, v in zip(chunks, vectors, strict=True)]
    texts = {c.chunk_id: c.text for c in chunks}
    return InMemoryRetriever(indexed), texts


# ── metric ───────────────────────────────────────────────────────────────────
# Sáu con số, MỘT nghĩa cố định mỗi con số (không đổi nghĩa theo tầng như bản `recall`/`clean` cũ):
#
#   hit1/hit3/hit5   — chunk cần thiết CÓ nằm trong top-1/3/5 không (1.0/0.0; None nếu tầng không có
#                       `expected_citation` — chỉ S5).
#   mrr5             — 1/hạng của chunk đúng đầu tiên trong top-5; 0.0 nếu trượt hẳn; None ở S5.
#   decoy_fall       — hạng #1 CÓ phải đúng chunk `decoy_hint` (bẫy DE gán tay) không (1.0/0.0);
#                       None nếu case không khai `decoy_hint` (S1/S2/S5 — hiện tại luôn None).
#   max_cosine_mean  — trung bình cosine của hạng #1 mỗi case. LUÔN có giá trị kể cả S5 (không có
#                       "trúng" để đo, nhưng vẫn có điểm cosine cao nhất để đo độ tự tin).
#
# `decoy_fall` hẹp hơn tên gọi: nó chỉ bắt "hạng #1 trúng ĐÚNG chunk DE đã gán nhãn là bẫy", KHÔNG
# phải "hạng #1 sai bất kỳ chunk nào". `test_dataset_case.py` chỉ kiểm decoy_hint là chunk thật cùng
# tenant — KHÔNG kiểm nó là đối thủ trùng-token mạnh nhất, nên số DFR thấp không tự động nghĩa là
# "ít bị nhiễu", có thể là nhãn decoy chưa phải bẫy mạnh nhất.


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    stratum: str
    retrieved: tuple[str, ...]  # top-MAX_K chunk_id, sắp giảm dần theo cosine
    top_score: float
    hit1: float | None
    hit3: float | None
    hit5: float | None
    mrr5: float | None
    decoy_fall: float | None


def score_case(case: Case, results: list[tuple[str, float]]) -> CaseResult:
    """Chấm một case trên top-`MAX_K` kết quả (`results`) → 6 con số cố định nghĩa, xem khối comment
    phía trên. `expected_citation` rỗng (S5) ⇒ hit*/mrr5 = None (không có gì để 'trúng')."""
    ids = tuple(cid for cid, _ in results)
    top_score = results[0][1] if results else 0.0
    expected = set(case.expected_citation)

    decoy_fall = None
    if case.decoy_hint:
        decoy_fall = 1.0 if ids and ids[0] in set(case.decoy_hint) else 0.0

    if not expected:
        return CaseResult(case.id, case.stratum, ids, top_score, None, None, None, None, decoy_fall)

    def hit_at(k: int) -> float:
        return 1.0 if expected & set(ids[:k]) else 0.0

    mrr5 = next((1.0 / rank for rank, cid in enumerate(ids, 1) if cid in expected), 0.0)
    return CaseResult(case.id, case.stratum, ids, top_score, hit_at(1), hit_at(3), hit_at(5), mrr5, decoy_fall)


def build_report(provider: object, part: str = "all") -> dict[str, CaseResult]:
    """Chấm case một lần cho provider → {case_id: CaseResult}. Order-independent. Retrieve luôn ở
    `MAX_K` — hit@1/hit@3 cắt từ CÙNG danh sách này, không retrieve lại ở k khác.

    `part` mặc định `"all"` chứ KHÔNG phải `"test"` — ngược với `cases_for()`, và có chủ đích:
    `baseline-dim8.json` được record trên cả 300 case, nên đổi mặc định ở đây là làm lệch gate hiện
    có một cách âm thầm. Chỗ nào cần tách tập (so provider, tune ngưỡng) thì truyền tường minh."""
    retriever, _ = build_retriever(provider)
    from studio_kb.doc_factory import resolve_tenant_id

    cases = cases_for(part)
    qvecs = to_vectors(provider, [c.query for c in cases]) if cases else []
    out: dict[str, CaseResult] = {}
    for case, qv in zip(cases, qvecs, strict=True):
        results = retriever.search(qv, resolve_tenant_id(case.tenant), case.section_roles, MAX_K)
        out[case.id] = score_case(case, results)
    return out


def _stratum_mean(report: dict[str, CaseResult], stratum: str, field: str) -> float | None:
    vals = [v for r in report.values() if r.stratum == stratum and (v := getattr(r, field)) is not None]
    return sum(vals) / len(vals) if vals else None


def stratum_metric(report: dict[str, CaseResult], stratum: str, metric: str) -> float | None:
    """Trung bình một trong 6 metric cho một tầng; `None` nếu tầng đó không có case nào áp dụng được
    metric này (vd `hit1` ở S5, `decoy_fall` ở S1/S2/S5)."""
    if metric == "max_cosine_mean":
        vals = [r.top_score for r in report.values() if r.stratum == stratum]
        return sum(vals) / len(vals) if vals else None
    return _stratum_mean(report, stratum, metric)


ALL_METRICS = ("hit1", "hit3", "hit5", "mrr5", "decoy_fall", "max_cosine_mean")

# Chiều 'tốt hơn' của từng metric. higher: ứng viên phải VƯỢT baseline+margin. lower: ứng viên phải
# THẤP HƠN baseline-margin — `decoy_fall`/`max_cosine_mean` càng thấp càng ít bị nhiễu/ít tự tin ẩu.
METRIC_DIRECTION: dict[str, str] = {
    "hit1": "higher",
    "hit3": "higher",
    "hit5": "higher",
    "mrr5": "higher",
    "decoy_fall": "lower",
    "max_cosine_mean": "lower",
}

# Metric nào THỰC SỰ bị gate (ứng viên không vượt ⇒ CI đỏ) ở từng tầng. Metric còn lại trong
# `ALL_METRICS` vẫn được ghi vào baseline để tham khảo/freshness nhưng KHÔNG chặn CI.
#
# S1–S4: hit*/mrr5 (có `expected_citation`). S3/S4 thêm `decoy_fall` (chỉ hai tầng này khai
# `decoy_hint`). S5: KHÔNG hit*/mrr5 (không có `expected_citation` — vô nghĩa) — gate duy nhất là
# `max_cosine_mean` thấp, ĐÚNG LÀ gate 'clean' cũ, chỉ bỏ phép nghịch đảo `1-top_sim` cho dễ đọc.
GATED_METRICS: dict[str, tuple[str, ...]] = {
    "S1": ("hit1", "hit3", "hit5", "mrr5"),
    "S2": ("hit1", "hit3", "hit5", "mrr5"),
    "S3": ("hit1", "hit3", "hit5", "mrr5", "decoy_fall"),
    "S4": ("hit1", "hit3", "hit5", "mrr5", "decoy_fall"),
    "S5": ("max_cosine_mean",),
}

# Metric gate bằng NGƯỠNG TUYỆT ĐỐI, KHÔNG so tương đối với baseline dim-8.
#
# Vì sao `decoy_fall` phải nằm ngoài cơ chế "vượt baseline + margin": **dim-8 thắng metric này một
# cách TẦM THƯỜNG.** Nó xếp hạng gần như ngẫu nhiên trên toàn corpus, nên hạng #1 của nó hiếm khi
# trúng đúng chunk decoy đã gán nhãn — thấp vì KHÔNG HIỂU GÌ ĐỂ BỊ BẪY, không phải vì chống bẫy giỏi.
# Đo được: dim-8 `decoy_fall` = 0.0435 (macro S3+S4), chỉ ~5.7× mức xếp-hạng-ngẫu-nhiên-thuần
# (1/|scope| ≈ 0.0076), trong khi mọi model ngữ nghĩa nằm ở 0.078–0.165 vì chúng ĐỦ hiểu để bị
# near-miss decoy kéo lên hạng #1.
#
# Hệ quả số học của bản cũ: gate đòi `got <= base - margin` = `0.0667 - 0.10 = -0.033` (S3) và
# `0.0182 - 0.10 = -0.082` (S4) — **NGƯỠNG ÂM, không tỉ lệ nào đạt được**. Mọi provider trượt đúng 2
# ô này vì số học, không vì chất lượng (đo được trên cả 7 provider). Đó là gate hỏng, không phải
# gate nghiêm.
#
# Ngưỡng 0.35 lấy từ dữ liệu, không phải cảm tính: giá trị cao nhất quan sát được ở một provider
# CHẠY ĐƯỢC là 0.2333 (S3, `hash1024` và `bge-m3`); với n=60 ở tầng S3 thì SE ≈ 0.055, nên
# 0.2333 + 2·SE ≈ 0.343. Chọn 0.35 để một model tệ-ngang-`bge-m3` vẫn qua chắc chắn (không nhấp
# nháy vì nhiễu lấy mẫu), nhưng vẫn bắt được thứ thật sự bệnh — vd 1/2 số truy vấn rơi vào bẫy.
#
# ĐỌC KÈM: metric này KHÔNG dùng để CHỌN model được (model càng ngẫu nhiên càng "thắng"). Nó là
# thanh chắn an toàn một chiều: bắt provider bị bẫy một cách bệnh hoạn, KHÔNG xếp hạng provider tốt.
ABSOLUTE_MAX: dict[str, float] = {"decoy_fall": 0.35}


def gate_verdict(metric: str, got: float, baseline: float, margin: float | None) -> bool:
    """Ứng viên có QUA gate của một metric không. Hai chế độ, chọn theo `ABSOLUTE_MAX`:

    - **tuyệt đối** (metric ∈ `ABSOLUTE_MAX`): `got <= ngưỡng`; `baseline`/`margin` bị BỎ QUA hoàn
      toàn. Dùng khi baseline dim-8 không phải mốc có ý nghĩa cho metric đó (xem `ABSOLUTE_MAX`).
    - **tương đối** (còn lại): theo `METRIC_DIRECTION` — `higher` đòi `got >= baseline + margin`,
      `lower` đòi `got <= baseline - margin`.

    `margin` chỉ được phép `None` khi metric gate tuyệt đối; thiếu margin ở chế độ tương đối là lỗi
    cấu hình, raise chứ không âm thầm cho qua.
    """
    ceiling = ABSOLUTE_MAX.get(metric)
    if ceiling is not None:
        return got <= ceiling
    if margin is None:
        raise ValueError(f"metric {metric!r} gate tương đối nhưng thiếu margin")
    if METRIC_DIRECTION[metric] == "higher":
        return got >= baseline + margin
    return got <= baseline - margin
