r"""Guard cho golden-set `callisto-2.0-golden-30-v1` — nhãn không trôi trên corpus 2.0 (cutover Phase B).

Cùng 5 trục như bộ 1.0 (`test_golden_set.py`) nhưng chấm trên **corpus 2.0** (`load_corpus_v2`) và đọc
**nguồn typed** `GOLDEN_CASES_V2` trực tiếp (không parse lại yaml — byte-identical đã có test riêng):
- **citation truy-xuất-được**: `expected_citation` lấy được khi search đúng scope (không id chết).
- **grounded**: `expected` nằm trong chunk được trích.
- **DUY NHẤT**: `expected` không khớp chunk nào khác trong (tenant, roles) — chống PASS oan; then chốt
  ở corpus 2.0 vì các doc chia sẻ câu boilerplate nguyên văn giữa 2 tenant.
- **teeth ≥ 2**: cùng vai có ≥2 ứng viên (retrieval có thứ để phân biệt).
- **fence**: case âm rỗng citation + scope cấm không lọt.

Cố ý **KHÔNG import `studio_evalhub`** (`.importlinter`: `studio_kb` < `studio_evalhub`) và **KHÔNG kéo
`pyyaml`** — `_contains_phrase`/`_tokenize` mirror đúng thuật toán `harness` tại chỗ (cùng kỷ luật test 1.0).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from studio_kb.doc_factory_core import Chunk, resolve_tenant_id
from studio_kb.doc_factory_v2 import load_corpus_v2
from studio_kb.golden_set_core import MANUAL_LABEL_VALUES, GoldenCase
from studio_kb.golden_set_v2 import EDGE_AXES_V2, GOLDEN_CASES_V2, GOLDEN_SET_REF_V2, render_yaml
from studio_kb.static_search import StaticKbSearch

_CORPUS = Path(__file__).resolve().parents[1] / "docs" / "callisto-2.0"
_GOLDEN = Path(__file__).resolve().parents[1] / "src" / "studio_kb" / "golden" / "callisto-2.0-golden-30-v1.yaml"

_POS = [c for c in GOLDEN_CASES_V2 if not c.is_refusal]
_NEG = [c for c in GOLDEN_CASES_V2 if c.is_refusal]


def _tokenize(text: str) -> list[str]:
    """Mirror `studio_evalhub.harness._tokenize` — giữ đồng bộ luật chấm success mà không import chéo tầng."""
    return re.findall(r"\w+", text.lower())


def _contains_phrase(text: str, phrase: str) -> bool:
    """True khi token `phrase` xuất hiện LIÊN TIẾP trong token `text` (mirror harness._contains_phrase)."""
    pt = _tokenize(phrase)
    if not pt:
        return False
    tt = _tokenize(text)
    n = len(pt)
    return any(tt[i : i + n] == pt for i in range(len(tt) - n + 1))


@pytest.fixture(scope="module")
def kb() -> StaticKbSearch:
    return StaticKbSearch(chunks=load_corpus_v2(_CORPUS))


@pytest.fixture(scope="module")
def by_id() -> dict[str, Chunk]:
    return {c.chunk_id: c for c in load_corpus_v2(_CORPUS)}


def test_dung_ref_va_du_30_case() -> None:
    """Đúng tên bộ + đủ 30 (22 dương, 8 âm) — chặn bộ bị cắt lặng."""
    assert GOLDEN_SET_REF_V2 == "callisto-2.0-golden-30-v1"
    assert len(GOLDEN_CASES_V2) == 30
    assert len(_POS) == 22 and len(_NEG) == 8


@pytest.mark.parametrize("case", _POS, ids=[c.case_id for c in _POS])
async def test_case_duong_citation_grounded_va_duy_nhat(
    case: GoldenCase, kb: StaticKbSearch, by_id: dict[str, Chunk]
) -> None:
    hits = await kb.search(case.query, resolve_tenant_id(case.tenant), list(case.section_roles), 50)
    ids = {h.chunk_id for h in hits}
    for c in case.expected_citation:
        assert c in by_id, f"{case.case_id}: {c} không có trong corpus 2.0"
        assert c in ids, f"{case.case_id}: {c} KHÔNG truy xuất được trong scope"
        assert _contains_phrase(by_id[c].text, case.expected), (
            f"{case.case_id}: expected {case.expected!r} không nằm trong chunk trích {c} → FAIL oan"
        )
    tid = resolve_tenant_id(case.tenant)
    rset = set(case.section_roles)
    collide = [
        ch.chunk_id
        for ch in by_id.values()
        if ch.tenant_id == tid
        and ch.section_role in rset
        and ch.chunk_id not in case.expected_citation
        and _contains_phrase(ch.text, case.expected)
    ]
    assert not collide, f"{case.case_id}: expected {case.expected!r} KHÔNG duy nhất — cũng khớp {collide} → PASS oan"
    same_scope = [h for h in hits if h.section_role == case.expected_section_role]
    assert len(same_scope) >= 2, f"{case.case_id}: chỉ {len(same_scope)} ứng viên cùng vai (teeth < 2)"


@pytest.mark.parametrize("case", _NEG, ids=[c.case_id for c in _NEG])
async def test_case_am_fence_kin(case: GoldenCase, kb: StaticKbSearch) -> None:
    assert case.expected_citation == (), f"{case.case_id}: case âm phải rỗng citation"
    hits = await kb.search(case.query, resolve_tenant_id(case.tenant), list(case.section_roles), 50)
    forbidden = resolve_tenant_id(case.expected_tenant)
    leaked = [h.chunk_id for h in hits if h.tenant_id == forbidden and h.section_role == case.expected_section_role]
    assert not leaked, f"{case.case_id}: RÒ RỈ scope cấm {case.expected_tenant}/{case.expected_section_role}: {leaked}"

    # "Có bí mật để rò" — `StaticKbSearch` lọc theo scope người-hỏi TRƯỚC khi xếp hạng nên `leaked` luôn
    # rỗng dù case vô nghĩa (gõ sai topic vẫn pass). Probe: cùng query trong ĐÚNG scope CẤM
    # (expected_tenant, expected_section_role) PHẢI ra non-empty → chứng minh fence thật sự chặn thứ
    # đáng lẽ với tới được. Đây là analogue của teeth≥2 cho case âm.
    if_unfenced = await kb.search(case.query, forbidden, [case.expected_section_role], 50)
    assert if_unfenced, (
        f"{case.case_id}: scope cấm {case.expected_tenant}/{case.expected_section_role} KHÔNG token-khớp "
        f"query → case âm rỗng nghĩa (không có gì để rò, pass cả khi fence gãy)"
    )


@pytest.mark.parametrize("case", GOLDEN_CASES_V2, ids=[c.case_id for c in GOLDEN_CASES_V2])
def test_refusal_semantics_khop_scope(case: GoldenCase) -> None:
    """`is_refusal` ⟺ người hỏi NGOÀI scope đáp án: `(expected_tenant != tenant) OR (expected_section_role
    ∉ section_roles)`. Bắt nhãn refusal lệch với (tenant/roles người hỏi vs expected)."""
    out_of_scope = (case.expected_tenant != case.tenant) or (case.expected_section_role not in case.section_roles)
    assert case.is_refusal == out_of_scope, (
        f"{case.case_id}: rỗng-citation={case.is_refusal} nhưng ngoài-scope={out_of_scope}"
    )


@pytest.mark.parametrize("case", _POS, ids=[c.case_id for c in _POS])
def test_citation_khop_expected_tenant_role(case: GoldenCase, by_id: dict[str, Chunk]) -> None:
    """Mọi chunk citation PHẢI thuộc đúng `(expected_tenant, expected_section_role)` đã khai."""
    want_tenant = resolve_tenant_id(case.expected_tenant)
    for c in case.expected_citation:
        assert c in by_id, f"{case.case_id}: {c} không có trong corpus"
        assert by_id[c].tenant_id == want_tenant, f"{case.case_id}: {c} thuộc tenant khác expected_tenant"
        assert by_id[c].section_role == case.expected_section_role, (
            f"{case.case_id}: {c} vai {by_id[c].section_role!r} ≠ expected_section_role={case.expected_section_role!r}"
        )


def test_yaml_byte_identical_voi_module_typed() -> None:
    """`callisto-2.0-golden-30-v1.yaml` trên đĩa PHẢI `==` `render_yaml()` — nguồn là module typed,
    yaml là artifact sinh (`scripts/emit_golden_set_v2.py`). Bắt drift sửa-tay-yaml hoặc quên-re-emit."""
    assert _GOLDEN.read_text(encoding="utf-8") == render_yaml(), (
        "yaml trên đĩa lệch render_yaml() — chạy scripts/emit_golden_set_v2.py rồi commit lại"
    )


@pytest.mark.parametrize("axis", sorted(EDGE_AXES_V2), ids=sorted(EDGE_AXES_V2))
def test_phu_bien_moi_truc_co_case(axis: str) -> None:
    referenced = EDGE_AXES_V2[axis]
    assert referenced, f"trục biên {axis!r} rỗng — không case nào phủ"
    ids = {c.case_id for c in GOLDEN_CASES_V2}
    missing = [cid for cid in referenced if cid not in ids]
    assert not missing, f"trục biên {axis!r} trỏ case_id không tồn tại: {missing}"


def test_khoa_ti_le_22_8() -> None:
    assert sum(not c.is_refusal for c in GOLDEN_CASES_V2) == 22, "số case dương phải là 22"
    assert sum(c.is_refusal for c in GOLDEN_CASES_V2) == 8, "số case âm phải là 8"


# ── Nhãn tay ground-truth — canh answer-key giữ sức phân biệt cho agreement ───────────────────────
_LABELED = tuple(c for c in GOLDEN_CASES_V2 if c.manual_label is not None)


def test_manual_label_du_hai_lop_va_vocab_hop_le() -> None:
    assert len(_LABELED) >= 8, f"nhãn tay chỉ {len(_LABELED)} — dưới sàn 8"
    bad = [c.case_id for c in _LABELED if c.manual_label not in MANUAL_LABEL_VALUES]
    assert not bad, f"nhãn ngoài vocab {MANUAL_LABEL_VALUES}: {bad}"
    assert {c.manual_label for c in _LABELED} == set(MANUAL_LABEL_VALUES), "subset thiếu lớp verdict"
    refuses = sum(c.manual_label == "refuse" for c in _LABELED)
    assert refuses >= 3, f"chỉ {refuses} nhãn `refuse` — dưới sàn 3"


def test_manual_label_khop_fence_semantics() -> None:
    lech = [c.case_id for c in _LABELED if (c.manual_label == "refuse") != c.is_refusal]
    assert not lech, f"nhãn tay ngược fence-semantics (refuse⇎is_refusal): {lech}"


def test_manual_label_trai_hai_tenant() -> None:
    tenants = {c.tenant for c in _LABELED}
    assert {"ankor", "borea"} <= tenants, f"subset nhãn tay không trải đủ tenant: {tenants}"
