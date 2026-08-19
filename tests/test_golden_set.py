r"""Guard cho golden-set `callisto-golden-30-v1` — canh nhãn không trôi khi corpus đổi (D14, DE).

**Vì sao có test này:** corpus phình 5→42 doc (D12) từng làm vỡ tính DUY NHẤT của nhãn `expected` mà
không phép kiểm nào bắt — một câu trả lời **sai chủ đề** vẫn chứa cụm chung ("3 ngày", "20 triệu") nên
`_contains_phrase` chấm **PASS oan** (phát hiện QA D14). Bộ này theo AIE-2 lâu dài, nên biến phép kiểm
tay thành CI gate: mỗi lần đổi corpus hoặc golden, chạy lại là bắt được collision mới.

Bốn trục, mỗi cái một kiểu trôi:
- **citation truy-xuất-được**: `expected_citation` phải lấy được khi search đúng scope (không id chết).
- **grounded**: `expected` phải nằm trong chunk được trích (nếu không → FAIL oan mọi lúc).
- **DUY NHẤT**: `expected` KHÔNG được khớp chunk nào khác trong (tenant, roles) người hỏi (nếu không →
  PASS oan khi agent trả lời sai chủ đề mà trúng cụm chung).
- **fence**: case âm phải để rỗng citation VÀ scope cấm không lọt.

Cố ý **KHÔNG import `studio_evalhub`** (`.importlinter`: `studio_kb` < `studio_evalhub`) và **KHÔNG kéo
`pyyaml`** (kb chưa từng khai) — `_contains_phrase`/parser tái hiện tại chỗ, mirror có chủ đích đúng thuật
toán `harness._tokenize` (`re.findall(r"\w+", lower)`, so token liên tiếp) + shape 8-field DE tự sinh.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from studio_kb.doc_factory import Chunk, load_callisto, resolve_tenant_id
from studio_kb.golden_set import EDGE_AXES, GOLDEN_CASES, MANUAL_LABEL_VALUES, render_yaml
from studio_kb.static_search import StaticKbSearch

_GOLDEN = Path(__file__).resolve().parents[1] / "src" / "studio_kb" / "golden" / "callisto-golden-30-v1.yaml"
_EXPECTED_REF = "callisto-golden-30-v1"


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


class _Case:
    __slots__ = ("case_id", "query", "tenant", "roles", "exp_tenant", "exp_role", "expected", "citation")

    def __init__(self, d: dict[str, str]) -> None:
        self.case_id = d["case_id"]
        self.query = d["query"]
        self.tenant = d["tenant"]
        self.roles = _parse_list(d["section_roles"])
        self.exp_tenant = d["expected_tenant"]
        self.exp_role = d["expected_section_role"]
        self.expected = d["expected"]
        self.citation = _parse_list(d["expected_citation"])

    @property
    def is_refusal(self) -> bool:
        return not self.citation


def _unquote(v: str) -> str:
    v = v.strip()
    return v[1:-1] if len(v) >= 2 and v[0] == '"' and v[-1] == '"' else v


def _parse_list(v: str) -> list[str]:
    inner = v.strip()[1:-1].strip()  # bỏ [ ]
    if not inner:
        return []
    return [_unquote(x) for x in inner.split(",")]


def _parse_golden() -> tuple[str, list[_Case]]:
    """Parser tối giản cho ĐÚNG shape DE sinh (8-field, mỗi field một dòng). Bỏ dòng comment `#`."""
    ref = ""
    cases: list[dict[str, str]] = []
    cur: dict[str, str] | None = None
    for raw in _GOLDEN.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("golden_set_ref:"):
            ref = line.split(":", 1)[1].strip()
            continue
        if line.startswith("- case_id:"):
            cur = {"case_id": line.split(":", 1)[1].strip()}
            cases.append(cur)
            continue
        if cur is not None and ":" in line:
            key, _, val = line.partition(":")
            cur[key.strip()] = val.strip()
    return ref, [_Case(c) for c in cases]


_REF, _CASES = _parse_golden()
_POS = [c for c in _CASES if not c.is_refusal]
_NEG = [c for c in _CASES if c.is_refusal]


@pytest.fixture(scope="module")
def kb() -> StaticKbSearch:
    return StaticKbSearch()


@pytest.fixture(scope="module")
def by_id() -> dict[str, Chunk]:
    return {c.chunk_id: c for c in load_callisto()}


def test_dung_ref_va_du_30_case() -> None:
    """Đúng tên bộ AIE-2 chờ + đủ 30 (14+ dương, có âm) — chặn parser hỏng lặng hoặc bộ bị cắt."""
    assert _REF == _EXPECTED_REF
    assert len(_CASES) == 30
    assert len(_POS) >= 15 and len(_NEG) >= 4


@pytest.mark.parametrize("case", _POS, ids=[c.case_id for c in _POS])
async def test_case_duong_citation_grounded_va_duy_nhat(
    case: _Case, kb: StaticKbSearch, by_id: dict[str, Chunk]
) -> None:
    hits = await kb.search(case.query, resolve_tenant_id(case.tenant), case.roles, 50)
    ids = {h.chunk_id for h in hits}
    for c in case.citation:
        assert c in by_id, f"{case.case_id}: {c} không có trong corpus"
        assert c in ids, f"{case.case_id}: {c} KHÔNG truy xuất được trong scope"
        assert _contains_phrase(by_id[c].text, case.expected), (
            f"{case.case_id}: expected {case.expected!r} không nằm trong chunk trích {c} → FAIL oan"
        )
    tid = resolve_tenant_id(case.tenant)
    rset = set(case.roles)
    collide = [
        ch.chunk_id
        for ch in by_id.values()
        if ch.tenant_id == tid
        and ch.section_role in rset
        and ch.chunk_id not in case.citation
        and _contains_phrase(ch.text, case.expected)
    ]
    assert not collide, f"{case.case_id}: expected {case.expected!r} KHÔNG duy nhất — cũng khớp {collide} → PASS oan"
    same_scope = [h for h in hits if h.section_role == case.exp_role]
    assert len(same_scope) >= 2, f"{case.case_id}: chỉ {len(same_scope)} ứng viên cùng vai (teeth < 2)"


@pytest.mark.parametrize("case", _NEG, ids=[c.case_id for c in _NEG])
async def test_case_am_fence_kin(case: _Case, kb: StaticKbSearch) -> None:
    assert case.citation == [], f"{case.case_id}: case âm phải rỗng citation"
    hits = await kb.search(case.query, resolve_tenant_id(case.tenant), case.roles, 50)
    forbidden = resolve_tenant_id(case.exp_tenant)
    leaked = [h.chunk_id for h in hits if h.tenant_id == forbidden and h.section_role == case.exp_role]
    assert not leaked, f"{case.case_id}: RÒ RỈ scope cấm {case.exp_tenant}/{case.exp_role}: {leaked}"


@pytest.mark.parametrize("case", _CASES, ids=[c.case_id for c in _CASES])
def test_refusal_semantics_khop_scope(case: _Case) -> None:
    """Invariant refusal (`GoldenCase.expects_refusal`, golden_case.py:88,109): case rỗng citation
    ⟺ người hỏi NGOÀI scope đáp án — `(expected_tenant != tenant) OR (expected_section_role ∉
    section_roles)`. Bắt hai lỗi nhãn: (a) case answerable mà lỡ để rỗng citation, (b) case gán
    citation nhưng scope hỏi thực ra không với tới — cả hai làm harness chấm sai nhánh."""
    out_of_scope = (case.exp_tenant != case.tenant) or (case.exp_role not in case.roles)
    assert case.is_refusal == out_of_scope, (
        f"{case.case_id}: rỗng-citation={case.is_refusal} nhưng ngoài-scope={out_of_scope} — "
        f"nhãn refusal lệch với (tenant/roles người hỏi vs expected_tenant/section_role)"
    )


@pytest.mark.parametrize("case", _POS, ids=[c.case_id for c in _POS])
def test_citation_khop_expected_tenant_role(case: _Case, by_id: dict[str, Chunk]) -> None:
    """Case dương: mọi chunk trong `expected_citation` PHẢI thuộc đúng `(expected_tenant,
    expected_section_role)` đã khai. Chặn nhãn `expected_tenant`/`expected_section_role` mô tả một
    scope khác với chunk thật sự được trích — thứ `chunk_id` không tự tố (`chunk_id` mã hoá tenant ở
    tiền tố nhưng KHÔNG mã hoá vai, golden_case.py:69)."""
    want_tenant = resolve_tenant_id(case.exp_tenant)
    for c in case.citation:
        assert c in by_id, f"{case.case_id}: {c} không có trong corpus"
        assert by_id[c].tenant_id == want_tenant, (
            f"{case.case_id}: {c} thuộc tenant khác expected_tenant={case.exp_tenant!r}"
        )
        assert by_id[c].section_role == case.exp_role, (
            f"{case.case_id}: {c} vai {by_id[c].section_role!r} ≠ expected_section_role={case.exp_role!r}"
        )


def test_yaml_byte_identical_voi_module_typed() -> None:
    """`callisto-golden-30-v1.yaml` trên đĩa PHẢI `==` `golden_set.render_yaml()` (D16, recorded).

    Nguồn sự thật là `studio_kb.golden_set.GOLDEN_CASES` (typed); yaml là artifact sinh ra qua
    `scripts/emit_golden_set.py`. Ca này bắt hai kiểu drift: (a) ai đó sửa tay yaml mà không sửa
    module → file lệch render; (b) sửa module mà quên re-emit → cũng lệch. Cùng kỷ luật
    `test_grid_inputs.py` (grid) / `test_embedding_fixture.py` (embeddings)."""
    assert _GOLDEN.read_text(encoding="utf-8") == render_yaml(), (
        "yaml trên đĩa lệch render_yaml() — chạy scripts/emit_golden_set.py rồi commit lại"
    )


@pytest.mark.parametrize("axis", sorted(EDGE_AXES), ids=sorted(EDGE_AXES))
def test_phu_bien_moi_truc_co_case(axis: str) -> None:
    """ "expected + expected-citations phủ biên" (#105) thành CI gate: mỗi trục biên khai trong
    `EDGE_AXES` phải có ≥1 case, và mọi `case_id` tham chiếu phải TỒN TẠI trong bộ (chống liệt kê
    một case_id đã bị xoá/đổi tên mà bảng phủ-biên vẫn khai 'đã phủ')."""
    referenced = EDGE_AXES[axis]
    assert referenced, f"trục biên {axis!r} rỗng — không case nào phủ"
    ids = {c.case_id for c in GOLDEN_CASES}
    missing = [cid for cid in referenced if cid not in ids]
    assert not missing, f"trục biên {axis!r} trỏ case_id không tồn tại: {missing}"


def test_module_is_refusal_khop_yaml_va_khoa_ti_le() -> None:
    """Canh CHÍNH `GoldenCase.is_refusal` của module (không phải `_Case.is_refusal` parser riêng ở
    trên): phân loại refusal của nguồn typed phải khớp file yaml đã parse, và khoá tỉ lệ 22 dương /
    8 âm. Bịt mutant `is_refusal` bỏ `not` (mutation sweep D16) + bắt drift module↔yaml."""
    module_ref = {c.case_id for c in GOLDEN_CASES if c.is_refusal}
    yaml_ref = {c.case_id for c in _CASES if c.is_refusal}
    assert module_ref == yaml_ref, f"refusal lệch giữa module typed và yaml: {module_ref ^ yaml_ref}"
    assert sum(not c.is_refusal for c in GOLDEN_CASES) == 22, "số case dương phải là 22"
    assert sum(c.is_refusal for c in GOLDEN_CASES) == 8, "số case âm phải là 8"


# ── Nhãn tay ground-truth (D18 / #115) — canh answer-key giữ sức phân biệt cho agreement ──────────
# Nhãn tay tiêu thụ ở AIE-2 (#118) đo `agreement` LLM-judge. Guard ở đây KHÔNG chấm giá trị đúng/sai
# (đó là phán đoán người DE), mà canh các TÍNH CHẤT khiến agreement có nghĩa: đủ hai lớp, vocab hợp lệ,
# nhất quán fence-semantics, trải tenant. Byte-identical (test trên) đã canh nhãn khớp yaml.

_LABELED = tuple(c for c in GOLDEN_CASES if c.manual_label is not None)


def test_manual_label_du_hai_lop_va_vocab_hop_le() -> None:
    """Subset nhãn tay phải đủ 'sàn' + CẢ HAI lớp verdict + **sàn tỷ lệ `refuse`** + vocab hợp lệ.

    Vì sao 'cả hai lớp': agreement trên tập toàn `pass` cho một judge hằng *"luôn PASS"* điểm 100% —
    không phân biệt được với judge thật (`scorecard.v1.md §1` cấm judge hằng). Sức phân biệt = có ĐỦ
    `refuse` để bắt judge tồi. Chỉ *"có mặt cả hai lớp"* chưa đủ: subset thoái hoá về 9 `pass`/1
    `refuse` vẫn đủ-hai-lớp mà gần như mất sức phân biệt — §11 chốt tỷ lệ 6/4, nên canh **sàn cứng
    `refuse >= 3`** để CI không xanh câm khi subset trôi dần về một lớp. Sàn ≥8 (khuyến nghị 10) đủ số
    agreement đọc được + dư trần ≤100/ngày."""
    assert len(_LABELED) >= 8, f"nhãn tay chỉ {len(_LABELED)} — dưới sàn 8 (khuyến nghị 10)"
    bad = [c.case_id for c in _LABELED if c.manual_label not in MANUAL_LABEL_VALUES]
    assert not bad, f"nhãn ngoài vocab {MANUAL_LABEL_VALUES}: {bad}"
    classes = {c.manual_label for c in _LABELED}
    assert classes == set(MANUAL_LABEL_VALUES), (
        f"subset thiếu lớp verdict — có {classes}, cần đủ {set(MANUAL_LABEL_VALUES)} để agreement phân biệt"
    )
    refuses = sum(c.manual_label == "refuse" for c in _LABELED)
    assert refuses >= 3, (
        f"chỉ {refuses} nhãn `refuse` — dưới sàn 3 (§11 chốt 6/4); subset đang trôi về một lớp, "
        f"agreement mất sức phân biệt"
    )


def test_manual_label_khop_fence_semantics() -> None:
    """`refuse` CHỈ trên case bẫy-hàng-rào, `pass` CHỈ trên case trả-lời-được — answer-key nhất quán
    với `is_refusal`. Bắt lỗi gán nhãn ngược (vd dán `pass` cho case T1 rò-rỉ), thứ làm agreement đo
    sai chiều mà không lỗi nào nổi lên."""
    lech = [c.case_id for c in _LABELED if (c.manual_label == "refuse") != c.is_refusal]
    assert not lech, f"nhãn tay ngược fence-semantics (refuse⇎is_refusal): {lech}"


def test_manual_label_trai_hai_tenant() -> None:
    """Subset trải CẢ HAI tenant — một judge có thể chắc ở ankor mà rò ở borea; tập một-tenant giấu
    điều đó. Không thiên trục."""
    tenants = {c.tenant for c in _LABELED}
    assert {"ankor", "borea"} <= tenants, f"subset nhãn tay không trải đủ tenant: {tenants}"
