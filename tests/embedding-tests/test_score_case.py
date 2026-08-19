"""Chốt nghĩa `score_case` bằng số tính tay — KHÔNG dựa vào provider/corpus thật. `test_embedding_gate.py`
chỉ so với `baseline-dim8.json` (freshness), và file baseline được RECORD bởi chính `score_case` —
một lỗi cắt-danh-sách hay đảo-điều-kiện trong `score_case` sẽ được ghi vào baseline như "đúng" và CI
vẫn xanh. Test này là chốt độc lập duy nhất, tính tay từng con số cho MỘT case dựng sẵn.
"""

from __future__ import annotations

import _harness as H
import pytest


def _case(*, expected: tuple[str, ...], decoy: tuple[str, ...] = (), stratum: str = "S3") -> H.Case:
    return H.Case(
        id="synthetic",
        query="q",
        tenant="ankor",
        section_roles=("hr",),
        expected_citation=expected,
        stratum=stratum,
        decoy_hint=decoy,
    )


def test_hit_mrr_decoy_tren_case_dung_san() -> None:
    """Hạng #1 = decoy · hạng #2 = nhiễu · hạng #3 = đáp án đúng — trúng hit3/hit5, trượt hit1,
    MRR@5 = 1/3, decoy_fall = 1.0 (hạng #1 đúng là chunk DE gán bẫy)."""
    case = _case(expected=("ankor-hr-x#c3",), decoy=("ankor-hr-y#c1",))
    results = [
        ("ankor-hr-y#c1", 0.9),
        ("ankor-hr-z#c2", 0.8),
        ("ankor-hr-x#c3", 0.7),
        ("ankor-hr-w#c4", 0.6),
        ("ankor-hr-v#c5", 0.5),
    ]
    r = H.score_case(case, results)
    assert r.hit1 == 0.0
    assert r.hit3 == 1.0
    assert r.hit5 == 1.0
    assert r.mrr5 == pytest.approx(1.0 / 3.0)
    assert r.decoy_fall == 1.0
    assert r.top_score == 0.9


def test_bien_hang_2_hit1_phai_truot() -> None:
    """Đáp án đúng ở HẠNG #2 — `hit1` phải là 0.0. Cố ý bẫy lỗi cắt `ids[:k]` thành `ids[:k+1]`:
    lỗi đó sẽ đọc nhầm hạng #2 vào top-1 và biến hit1 thành 1.0."""
    case = _case(expected=("ankor-hr-x#c2",))
    results = [("ankor-hr-a#c1", 0.9), ("ankor-hr-x#c2", 0.8), ("ankor-hr-b#c3", 0.7)]
    assert H.score_case(case, results).hit1 == 0.0


def test_bien_hang_4_hit3_phai_truot() -> None:
    """Đáp án đúng ở HẠNG #4 — `hit3` phải là 0.0 (cùng lý do bẫy như trên, ở biên k=3)."""
    case = _case(expected=("ankor-hr-x#c4",))
    results = [
        ("ankor-hr-a#c1", 0.9),
        ("ankor-hr-b#c2", 0.8),
        ("ankor-hr-c#c3", 0.7),
        ("ankor-hr-x#c4", 0.6),
    ]
    assert H.score_case(case, results).hit3 == 0.0


def test_bien_hang_6_hit5_phai_truot() -> None:
    """Đáp án đúng ở HẠNG #6 (ngoài `MAX_K`=5) — `hit5` phải là 0.0 (biên k=5)."""
    case = _case(expected=("ankor-hr-x#c6",))
    results = [(f"ankor-hr-noise#c{i}", 1.0 - i * 0.1) for i in range(5)] + [("ankor-hr-x#c6", 0.4)]
    assert H.score_case(case, results).hit5 == 0.0


def test_truot_han_ngoai_top5() -> None:
    """Đáp án đúng không nằm trong 5 kết quả trả về → hit1/hit3/hit5 = 0.0, mrr5 = 0.0."""
    case = _case(expected=("ankor-hr-x#c9",), decoy=("ankor-hr-y#c1",))
    results = [(f"ankor-hr-noise#c{i}", 1.0 - i * 0.1) for i in range(5)]
    r = H.score_case(case, results)
    assert r.hit1 == r.hit3 == r.hit5 == 0.0
    assert r.mrr5 == 0.0
    assert r.decoy_fall == 0.0  # hạng #1 không phải chunk decoy đã khai


def test_khong_khai_decoy_hint_thi_decoy_fall_none() -> None:
    """S1/S2 không khai `decoy_hint` (luật dựng case) → `decoy_fall` phải là None, không phải 0.0 —
    0.0 sẽ đọc nhầm thành 'không rơi vào bẫy nào' trong khi thực ra KHÔNG CÓ bẫy nào để rơi vào."""
    case = _case(expected=("ankor-hr-x#c3",), decoy=(), stratum="S1")
    results = [("ankor-hr-x#c3", 0.9)]
    r = H.score_case(case, results)
    assert r.decoy_fall is None
    assert r.hit1 == 1.0


def test_s5_negative_khong_co_hit_hay_mrr() -> None:
    """S5 (`expected_citation` rỗng) → hit1/hit3/hit5/mrr5 đều None (không có gì để 'trúng'), nhưng
    `top_score` vẫn phải tính được (dùng cho `max_cosine_mean`)."""
    case = _case(expected=(), stratum="S5")
    results = [("ankor-hr-x#c1", 0.42)]
    r = H.score_case(case, results)
    assert r.hit1 is None
    assert r.hit3 is None
    assert r.hit5 is None
    assert r.mrr5 is None
    assert r.decoy_fall is None
    assert r.top_score == 0.42


def test_rong_khong_co_ket_qua_nao() -> None:
    """`results` rỗng (fence chặn hết) → top_score=0.0, hit*=0.0 (không trúng), không NaN/crash."""
    case = _case(expected=("ankor-hr-x#c3",))
    r = H.score_case(case, [])
    assert r.top_score == 0.0
    assert r.hit1 == r.hit3 == r.hit5 == 0.0
    assert r.mrr5 == 0.0


# ── gate_verdict ─────────────────────────────────────────────────────────────
# Chốt LOGIC gate bằng số tính tay. `test_embedding_gate.py` chỉ chạy được ở chế độ freshness (so
# baseline dim-8 với chính nó) nên KHÔNG bao giờ chạm nhánh 'ứng viên' — nhánh duy nhất thực sự phán
# xét một model mới. Không có test này thì nhánh đó chỉ được kiểm lần đầu khi có người tiêm model
# thật, lúc đó lỗi đảo dấu/nhầm chế độ sẽ hiện ra dưới dạng "model tốt bị đánh trượt".


def test_gate_tuong_doi_chieu_cao() -> None:
    """`higher`: đúng bằng baseline+margin thì QUA (biên), thiếu một chút thì TRƯỢT."""
    assert H.gate_verdict("hit3", got=0.60, baseline=0.50, margin=0.10)
    assert not H.gate_verdict("hit3", got=0.599, baseline=0.50, margin=0.10)


def test_gate_tuong_doi_chieu_thap() -> None:
    """`lower` (max_cosine_mean@S5): phải THẤP hơn baseline−margin, cao hơn là trượt."""
    assert H.gate_verdict("max_cosine_mean", got=0.40, baseline=0.45, margin=0.05)
    assert not H.gate_verdict("max_cosine_mean", got=0.4001, baseline=0.45, margin=0.05)


def test_gate_tuyet_doi_bo_qua_baseline() -> None:
    """`decoy_fall` gate bằng ngưỡng tuyệt đối: baseline/margin KHÔNG được ảnh hưởng phán quyết.

    Chốt đúng cái bug đã sửa — bản cũ so tương đối với dim-8 (`0.0667 − 0.10 < 0`) nên MỌI provider
    trượt vì số học. Ở đây baseline để 0.0 và margin 0.99 (giá trị vô lý nhất có thể) mà một giá trị
    dưới ngưỡng vẫn phải QUA."""
    ceiling = H.ABSOLUTE_MAX["decoy_fall"]
    assert H.gate_verdict("decoy_fall", got=ceiling - 0.01, baseline=0.0, margin=0.99)
    assert H.gate_verdict("decoy_fall", got=ceiling, baseline=0.0, margin=0.99)  # biên: bằng ⇒ qua
    assert not H.gate_verdict("decoy_fall", got=ceiling + 0.01, baseline=0.0, margin=0.99)


def test_gate_tuyet_doi_cho_qua_moi_provider_da_do() -> None:
    """Giá trị `decoy_fall` CAO NHẤT từng quan sát ở một provider chạy được (0.2333 — S3 của
    `hash1024`/`bge-m3`) phải QUA, kèm biên an toàn ≥2·SE(0.055) để gate không nhấp nháy vì nhiễu."""
    worst_observed = 0.2333
    assert H.gate_verdict("decoy_fall", got=worst_observed, baseline=0.0, margin=None)
    assert H.ABSOLUTE_MAX["decoy_fall"] >= worst_observed + 2 * 0.055


def test_gate_tuong_doi_thieu_margin_thi_raise() -> None:
    """Metric gate tương đối mà thiếu margin ⇒ raise, KHÔNG âm thầm cho qua (cấu hình sai phải ồn)."""
    with pytest.raises(ValueError, match="thiếu margin"):
        H.gate_verdict("hit3", got=0.9, baseline=0.5, margin=None)
