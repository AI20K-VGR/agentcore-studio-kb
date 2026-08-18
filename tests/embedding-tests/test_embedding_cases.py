"""300 case eval — mỗi case 1 test (parametrize). Đây là artifact TEST-FIRST: bảo vệ tính toàn vẹn
của ground-truth + cưỡng chế luật dựng từng tầng (đặc biệt chống bẫy vòng-lặp lexical ở S2/S3/S4).

**KHÔNG** assert retrieval thành công per-case ở đây — hiệu quả đo bằng gate per-stratum tương đối
(`test_embedding_gate.py`). Phần integrity dưới đây XANH với mọi provider (kể cả baseline), nên nó
kiểm *dữ liệu*, không kiểm *model*.
"""

from __future__ import annotations

import _harness as H
import pytest
from studio_kb.doc_factory import SECTION_VOCAB

_CASES = H.load_cases()
_IDS = [c.id for c in _CASES]

# Ngưỡng luật dựng (tính bằng token phân biệt). DE chỉnh khi soạn case; test cưỡng chế để một case
# "gán nhãn ẩu" không lọt vào bộ và thổi phồng kết quả.
_S2_MAX_OVERLAP = 2  # paraphrase: query trùng ÍT token với chunk đúng
_S1_MIN_OVERLAP = 1  # lexical-easy: có ít nhất 1 token chung (sàn tỉnh táo)


@pytest.fixture(scope="session")
def _by_id() -> dict[str, H.Case]:
    return {c.id: c for c in _CASES}


def test_dataset_khong_rong_va_du_tang() -> None:
    """Bộ case phải tồn tại + phủ đủ 5 tầng — chuông báo nếu quên nạp file cases."""
    assert _CASES, "chưa có case nào trong cases/*.json"
    covered = {c.stratum for c in _CASES}
    assert covered == set(H.STRATA), f"thiếu tầng: {set(H.STRATA) - covered}"


@pytest.mark.parametrize("cid", _IDS)
def test_case(
    cid: str,
    _by_id: dict[str, H.Case],
    corpus_texts: dict[str, str],
    report: dict[str, H.CaseResult],
) -> None:
    """Integrity + bất biến tầng cho một case. (300 item = 300 case.)"""
    case = _by_id[cid]

    # — hợp lệ cơ bản —
    assert case.stratum in H.STRATA, f"{cid}: tầng lạ {case.stratum!r}"
    assert case.tenant in {"ankor", "borea"}, f"{cid}: tenant lạ {case.tenant!r}"
    assert case.section_roles, f"{cid}: section_roles rỗng"
    assert set(case.section_roles) <= SECTION_VOCAB, f"{cid}: role ngoài từ vựng {case.section_roles}"
    assert case.query.strip(), f"{cid}: query rỗng"
    assert cid in report, f"{cid}: harness không chấm được case (thiếu trong report)"

    if case.stratum == "S5":
        # negative/no-answer: KHÔNG có expected; và không được vô tình neo vào chunk thật.
        assert not case.expected_citation, f"{cid}: S5 phải rỗng expected_citation"
        return

    # — expected phải phân giải ra chunk THẬT, đúng tenant + trong section_roles —
    assert case.expected_citation, f"{cid}: {case.stratum} phải có expected_citation"
    allowed = set(case.section_roles)
    for exp in case.expected_citation:
        assert exp in corpus_texts, f"{cid}: expected {exp!r} không có trong corpus 2.0"
        assert exp.startswith(f"{case.tenant}-"), f"{cid}: expected {exp!r} không thuộc tenant {case.tenant}"
        role = exp.split("-", 2)[1]
        assert role in allowed, f"{cid}: expected {exp!r} (role {role}) ngoài section_roles {allowed}"

    exp_id = case.expected_citation[0]
    exp_role = exp_id.split("-", 2)[1]
    exp_overlap = H.token_overlap(case.query, corpus_texts[exp_id])

    # decoy_hint (nếu khai) phải là chunk thật cùng tenant — tài liệu hoá near-miss, không bắt buộc.
    for decoy in case.decoy_hint:
        assert decoy in corpus_texts, f"{cid}: decoy {decoy!r} không có trong corpus"
        assert decoy.startswith(f"{case.tenant}-"), f"{cid}: decoy {decoy!r} không thuộc tenant {case.tenant}"

    # — luật dựng theo tầng (chống vòng-lặp lexical). S3/S4 TÍNH TỪ CORPUS: phải TỒN TẠI một chunk
    #   'mồi' trùng query ≥ đáp án → lexical đơn thuần KHÔNG đủ tách, buộc phải nhờ ngữ nghĩa. —
    if case.stratum == "S1":
        assert exp_overlap >= _S1_MIN_OVERLAP, f"{cid}: S1 phải có ≥{_S1_MIN_OVERLAP} token chung với đáp án"

    if case.stratum == "S2":
        assert exp_overlap <= _S2_MAX_OVERLAP, (
            f"{cid}: S2 paraphrase nhưng query trùng {exp_overlap} token với đáp án "
            f"(> {_S2_MAX_OVERLAP}) — lexical baseline sẽ thắng, case không chứng minh ngữ nghĩa"
        )

    # mồi phải trùng ≥ max(đáp án, 1): có ĐỐI THỦ lexical thật (≥1 token) tie/beat đáp án → lexical
    # đơn thuần không tách được, buộc nhờ ngữ nghĩa. Chặn kẽ hở 'đáp án 0-overlap' làm luật vô nghĩa.
    trap_floor = max(exp_overlap, 1)

    if case.stratum == "S3":
        competitors = [
            c
            for c, t in corpus_texts.items()
            if c != exp_id
            and c.startswith(f"{case.tenant}-")
            and c.split("-", 2)[1] == exp_role
            and H.token_overlap(case.query, t) >= trap_floor
        ]
        assert competitors, (
            f"{cid}: S3 near-miss nhưng KHÔNG có chunk cùng role trùng ≥ max({exp_overlap},1) token "
            f"— lexical đã đủ tách, không phải near-miss thật"
        )

    if case.stratum == "S4":
        competitors = [
            c
            for c, t in corpus_texts.items()
            if c.startswith(f"{case.tenant}-")
            and c.split("-", 2)[1] in allowed
            and c.split("-", 2)[1] != exp_role
            and H.token_overlap(case.query, t) >= trap_floor
        ]
        assert competitors, (
            f"{cid}: S4 cross-role nhưng KHÔNG có chunk role khác (∈ {allowed}) trùng ≥ max({exp_overlap},1) "
            f"token — chưa phải bẫy chéo-vai thật"
        )
