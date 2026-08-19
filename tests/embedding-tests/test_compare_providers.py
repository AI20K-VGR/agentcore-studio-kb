"""Khoá `compare_providers.py` — chống đúng thứ đã làm PR#33 bị đóng.

Phản hồi đóng #33: *"Toàn bộ bảng recall/MRR quyết định khuyến nghị cuối được tạo bằng script không
có trong PR — nên không ai review được, không ai chạy lại được."* Commit script vào repo mới giải
quyết được nửa vấn đề; nửa còn lại là **script có thật sự đi cùng đường với gate CI không**, hay chỉ
là một bản "tương đương" viết tay cho ra số khác. Bài `test_so_khop_fixture_report` dưới đây là chỗ
duy nhất chốt điều đó.
"""

from __future__ import annotations

import _harness as H
import pytest
from compare_providers import HEADLINE, STRATA, available_providers, macro, render


def test_so_khop_fixture_report(report: dict[str, H.CaseResult]) -> None:
    """Số của script KHỚP TỪNG CASE với fixture `report` mà `test_embedding_gate.py` chấm.

    Đây là bài trả lời trực tiếp `kb#38` gạch 2 ("gọi qua đúng `conftest.py::embedding_provider`,
    không dùng bản tương đương viết tay"). Nếu ai đó sau này chép công thức chấm vào
    `compare_providers.py` cho tiện, bài này đỏ ngay khi hai đường lệch nhau một case.
    """
    from_script = H.build_report(H.BaselineDim8(), "all")
    assert from_script.keys() == report.keys()
    for case_id, expected in report.items():
        assert from_script[case_id] == expected, f"{case_id}: script và fixture cho hai kết quả khác nhau"


def test_macro_la_trung_binh_co_trong_so_khong_phai_trung_binh_don() -> None:
    """`macro` phải weighted theo `n` mỗi tầng. Các tầng KHÔNG bằng nhau (S1=65 … S4=55), nên trung
    bình đơn ngầm khuếch đại tầng nhỏ — sai lệch nhỏ nhưng có hệ thống, và vô hình trong bảng."""
    rep = H.build_report(H.BaselineDim8(), "all")
    got = macro(rep, "hit1")
    assert got is not None

    per_stratum = [(H.stratum_metric(rep, s, "hit1"), sum(1 for r in rep.values() if r.stratum == s)) for s in STRATA]
    applicable = [(v, n) for v, n in per_stratum if v is not None]
    weighted = sum(v * n for v, n in applicable) / sum(n for _, n in applicable)
    unweighted = sum(v for v, _ in applicable) / len(applicable)

    assert got == pytest.approx(weighted)
    # Phản chứng: hai công thức PHẢI cho hai số khác nhau trên bộ case này, nếu không bài trên
    # không phân biệt được weighted với unweighted và assert kia là vô nghĩa.
    assert weighted != pytest.approx(unweighted)


def test_macro_bo_qua_tang_khong_ap_dung_duoc_metric() -> None:
    """S5 không có `expected_citation` ⇒ `hit1` là `None` ở tầng đó. `macro` phải BỎ tầng ấy khỏi cả
    tử lẫn mẫu — cộng nó như 0.0 sẽ kéo mọi provider xuống theo cùng một tỉ lệ, trông như hợp lệ."""
    rep = H.build_report(H.BaselineDim8(), "all")
    assert H.stratum_metric(rep, "S5", "hit1") is None

    n_s5 = sum(1 for r in rep.values() if r.stratum == "S5")
    assert n_s5 > 0, "bộ case phải có S5 thì bài này mới kiểm được điều nó định kiểm"

    got = macro(rep, "hit1")
    assert got is not None
    as_if_zero = sum(
        (H.stratum_metric(rep, s, "hit1") or 0.0) * sum(1 for r in rep.values() if r.stratum == s) for s in STRATA
    ) / len(rep)
    assert got != pytest.approx(as_if_zero)


def test_part_test_khong_giao_validation() -> None:
    """Số báo cáo mặc định chấm trên tập KHÔNG bị tune — bất biến trung tâm của việc tách tập."""
    rep = H.build_report(H.BaselineDim8(), "test")
    assert set(rep) & H.load_validation_ids() == set()
    assert len(rep) == len(H.cases_for("test"))


def test_baseline_luon_co_mat_trong_bang() -> None:
    """`baseline-dim8` không phụ thuộc cache/mạng nên PHẢI luôn chấm được. Bảng rỗng vì mọi provider
    bị bỏ qua là một cách 'thành công' không ai muốn."""
    assert "baseline-dim8" in available_providers()


def test_render_khong_nuot_provider_nao() -> None:
    rep = {"baseline-dim8": H.build_report(H.BaselineDim8(), "test")}
    out = render(rep, "test")
    assert "baseline-dim8" in out
    for metric in HEADLINE:
        assert metric in out
