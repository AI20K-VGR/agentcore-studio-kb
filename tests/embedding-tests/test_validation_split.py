"""Khoá tính toàn vẹn của `cases/validation-split.json` (kb#38, sai sót phương pháp #2).

File split là một artifact ĐÓNG BĂNG, commit vào repo — nên nó trôi khỏi bộ case theo đúng kiểu
hỏng câm: thêm/xoá case thì split cũ vẫn đọc được, vẫn chia ra hai tập trông hợp lệ, chỉ là case
mới lặng lẽ rơi hết vào `test` và tỉ lệ phân tầng lệch dần. Không bài nào ở đây kiểm chất lượng
retrieval — chỉ kiểm phép chia còn khớp bộ case hay không.
"""

from __future__ import annotations

import json

import _harness as H
import pytest
from make_validation_split import RATIO, SEED, build_split


@pytest.fixture(scope="module")
def split_ids() -> list[str]:
    """Danh sách id validation đọc thẳng từ file đã commit — KHÔNG qua `H.load_validation_ids()`.

    Cố ý đọc bằng đường khác: dùng chính hàm đang được kiểm để lấy dữ liệu kiểm nó thì mọi bài dưới
    đây sẽ vẫn xanh khi hàm đó hỏng theo cách nhất quán."""
    raw: list[str] = json.loads(H.SPLIT_PATH.read_text(encoding="utf-8"))["validation"]
    return raw


def test_moi_id_trong_split_deu_la_case_that(split_ids: list[str]) -> None:
    """Không có id ma. Xoá một case mà quên sinh lại split thì bài này đỏ — nếu không, `cases_for`
    vẫn chạy êm và tập validation âm thầm nhỏ đi."""
    known = {c.id for c in H.load_cases()}
    unknown = sorted(set(split_ids) - known)
    assert not unknown, f"split trỏ tới case không tồn tại: {unknown[:5]}"


def test_validation_va_test_chia_het_bo_case() -> None:
    """Hai phần rời nhau VÀ phủ kín. Đây là bất biến `cases_for` dựa vào để 'test' nghĩa là
    'mọi case không thuộc validation' — chồng lấn là rò rỉ tập tune vào tập báo cáo."""
    val = {c.id for c in H.cases_for("validation")}
    test = {c.id for c in H.cases_for("test")}
    allc = {c.id for c in H.cases_for("all")}
    assert not (val & test), f"case nằm cả hai phần: {sorted(val & test)[:5]}"
    assert val | test == allc
    assert len(allc) == len(H.load_cases())


def test_moi_tang_deu_co_mat_trong_validation() -> None:
    """Phân tầng thật sự có tác dụng: KHÔNG tầng nào vắng mặt khỏi validation.

    Đây là lý do phải phân tầng thay vì bốc ngẫu nhiên trên cả 300 case — một validation thiếu hẳn
    S4 vẫn trông bình thường (vẫn ~98 case), nhưng ngưỡng tune trên nó chưa từng thấy tầng đó."""
    by_stratum: dict[str, int] = {}
    for case in H.cases_for("validation"):
        by_stratum[case.stratum] = by_stratum.get(case.stratum, 0) + 1
    strata = {c.stratum for c in H.load_cases()}
    assert set(by_stratum) == strata, f"tầng vắng mặt khỏi validation: {sorted(strata - set(by_stratum))}"


@pytest.mark.parametrize("stratum", sorted({c.stratum for c in H.load_cases()}))
def test_ti_le_moi_tang_dung_bang_ratio(stratum: str) -> None:
    """Tỉ lệ từng tầng khớp `RATIO` (làm tròn), không phải chỉ tổng thể khớp.

    Tổng 33% vẫn có thể đạt được bằng một phép chia lệch hẳn giữa các tầng — kiểm từng tầng mới
    chốt được là phép lấy mẫu CÓ phân tầng."""
    total = sum(1 for c in H.load_cases() if c.stratum == stratum)
    got = sum(1 for c in H.cases_for("validation") if c.stratum == stratum)
    assert got == round(total * RATIO)


def test_sinh_lai_bang_seed_ra_dung_file_da_commit(split_ids: list[str]) -> None:
    """Split tái lập được từ `SEED` — không phải một danh sách gõ tay không ai dựng lại nổi.

    Cũng là chuông báo khi bộ case đổi: `build_split` chạy trên `load_cases()` HIỆN TẠI, nên thêm
    một case là kết quả lệch file đã commit, và bài này đỏ trước khi số liệu kịp sai."""
    assert build_split(SEED, RATIO)["validation"] == split_ids


def test_mac_dinh_cases_for_la_test_khong_phai_all() -> None:
    """Mặc định an toàn: gọi `cases_for()` trống tay phải ra tập KHÔNG bị tune trên nó.

    Nếu mặc định là `all`, mọi chỗ quên truyền tham số sẽ lặng lẽ báo cáo trên cả tập validation —
    đúng thứ kb#38 gạch, chỉ khác là lần này do quên chứ không do cố ý."""
    assert H.cases_for() == H.cases_for("test")
    assert len(H.cases_for()) < len(H.load_cases())


def test_part_la_khong_hop_le_thi_bao_loi() -> None:
    with pytest.raises(ValueError, match="part phải là"):
        H.cases_for("val")  # gõ tắt sai — phải nổ, không được coi là 'test'
