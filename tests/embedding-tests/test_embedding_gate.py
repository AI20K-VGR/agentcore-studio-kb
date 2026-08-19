"""Gate hiệu quả — thanh **tương đối** so baseline dim-8 đóng băng (`baseline-dim8.json`).

Hai chế độ, tự nhận theo provider:
- provider = **baseline dim-8** (mặc định, CI hằng ngày): gate = *freshness* — CẢ SÁU metric mỗi
  tầng phải KHỚP file đóng băng (kể cả metric không bị gate — freshness bắt lệch dữ liệu/công thức
  bất kể metric đó có chặn CI hay không). Chuông báo nếu corpus/công thức đổi mà quên re-record.
- provider = **model ứng viên** (tiêm qua fixture khi chọn model sau): gate = *cải thiện* — CHỈ trên
  metric nằm trong `baseline["gated_metrics"][tầng]`. Hai chế độ, xem `H.gate_verdict`:
  *tương đối* (hit1/hit3/hit5/mrr5 đòi ≥ baseline + margin; max_cosine_mean@S5 đòi ≤ baseline −
  margin) và *tuyệt đối* (`decoy_fall` đòi ≤ `H.ABSOLUTE_MAX` — KHÔNG so với dim-8, vì dim-8 thắng
  metric đó một cách tầm thường và so tương đối cho ra ngưỡng ÂM bất khả thi; xem `H.ABSOLUTE_MAX`).
  Không lách được vì cả baseline lẫn ngưỡng đều nằm trong git diff.

`hit1`/`hit3`/`hit5` = chunk cần thiết có nằm trong top-1/3/5 không — `hit3` khớp `top_k` mặc định
production (`workbench/builder.py:219,292`), `hit5` khớp fallback của `KbRetrieveExecutor`
(`src/studio_kb/search.py`); cả hai đều là call-site thật. `mrr5` = 1/hạng trong top-5. `decoy_fall`
= hạng #1 có trúng ĐÚNG chunk DE gán nhãn bẫy không (chỉ S3/S4 có `decoy_hint`). `max_cosine_mean` =
trung bình cosine hạng #1 — ở S5 đây là gate duy nhất (không có `expected_citation` để tính hit/mrr),
tương đương gate 'clean' cũ, chỉ bỏ phép nghịch đảo `1-top_sim`.

Đây là nơi "chứng minh độ hiệu quả": 300 case ở `test_embedding_cases.py` là bằng chứng, gate này đọc
chúng theo tầng và phán.
"""

from __future__ import annotations

import json
from typing import Any, cast

import _harness as H
import pytest

_FRESHNESS_TOL = 1e-6  # khớp round(6) trong baseline-dim8.json (đủ chặt để bắt corpus/công thức đổi)


def _load_baseline() -> dict[str, Any]:
    assert H.BASELINE_PATH.exists(), (
        f"thiếu {H.BASELINE_PATH.name} — sinh bằng `python tests/embedding-tests/record_baseline.py` trước"
    )
    return cast("dict[str, Any]", json.loads(H.BASELINE_PATH.read_text(encoding="utf-8")))


def _is_baseline(provider: object) -> bool:
    return getattr(provider, "name", "") == "baseline-dim8"


@pytest.mark.parametrize("stratum", H.STRATA)
def test_gate_theo_tang(stratum: str, embedding_provider: object, report: dict[str, H.CaseResult]) -> None:
    baseline = _load_baseline()
    assert baseline["top_k"] == H.TOP_K, "top_k của baseline lệch harness — re-record baseline"
    assert baseline["max_k"] == H.MAX_K, "max_k của baseline lệch harness — re-record baseline"
    # Ngưỡng tuyệt đối phải nằm trong file đóng băng: đổi `H.ABSOLUTE_MAX` (nới/siết thanh chắn
    # `decoy_fall`) mà quên re-record thì lộ ra ở đây, không âm thầm gate theo ngưỡng mới.
    assert baseline["absolute_max"] == H.ABSOLUTE_MAX, (
        f"baseline ghi absolute_max={baseline['absolute_max']} nhưng harness nay dùng "
        f"{H.ABSOLUTE_MAX} — re-record baseline"
    )
    # Danh sách metric bị gate mỗi tầng phải khớp — đổi `H.GATED_METRICS` (thêm/bớt metric chặn CI ở
    # một tầng) mà quên re-record thì phải lộ ra ở đây, không được âm thầm gate theo bảng cũ.
    assert baseline["gated_metrics"][stratum] == list(H.GATED_METRICS[stratum]), (
        f"{stratum}: baseline ghi gated_metrics={baseline['gated_metrics'][stratum]} nhưng harness nay "
        f"gate {list(H.GATED_METRICS[stratum])!r} — re-record baseline"
    )

    base_strata = baseline["strata"][stratum]
    is_baseline = _is_baseline(embedding_provider)

    for metric in H.ALL_METRICS:
        got = H.stratum_metric(report, stratum, metric)
        base = base_strata[metric]

        if base is None:
            assert got is None, f"{stratum}.{metric}: baseline None nhưng harness hiện tính ra {got}"
            continue
        assert got is not None, f"{stratum}.{metric}: baseline={base} nhưng harness hiện trả None"

        if is_baseline:
            # freshness: baseline đóng băng phải khớp phép chấm hiện tại của chính dim-8 — kiểm CẢ
            # metric không bị gate, để lệch dữ liệu/công thức lộ ra dù metric đó không chặn CI.
            assert got == pytest.approx(base, abs=_FRESHNESS_TOL), (
                f"{stratum}.{metric}: baseline-dim8.json ({base}) lệch phép chấm hiện tại ({got}) — "
                f"corpus/công thức đổi? re-record baseline có chủ đích."
            )
            continue

        if metric not in H.GATED_METRICS[stratum]:
            continue  # ghi nhận tham khảo, không chặn CI cho metric ngoài danh sách gate của tầng
        margin = baseline["margin"][stratum].get(metric)
        assert H.gate_verdict(metric, got, base, margin), f"{stratum}.{metric}: ứng viên={got:.4f} trượt gate — " + (
            f"ngưỡng tuyệt đối tối đa {H.ABSOLUTE_MAX[metric]}"
            if metric in H.ABSOLUTE_MAX
            else f"cần vượt baseline {base:.4f} theo margin {margin} "
            f"(chiều {H.METRIC_DIRECTION[metric]}) — chưa đủ tốt hơn dim-8 ở tầng này"
        )


# ── ngưỡng tuyệt đối phải DẪN TỪ VALIDATION, không phải từ tập báo cáo ────────


def test_nguong_decoy_fall_dan_tu_validation_khong_phai_tap_bao_cao() -> None:
    """`ABSOLUTE_MAX["decoy_fall"]` đang commit phải PHỦ được ngưỡng dẫn từ validation.

    Đây là gạch DoD cuối của `kb#38` mà kb tự làm được (sai sót phương pháp #2). Ngưỡng 0.35 của
    bản trước quét trên chính 300 case dùng để báo cáo — fit tham số vào nhiễu của tập mình sẽ công
    bố. Bài này chốt hai điều mà một hằng số trần trụi không nói được:

    1. **Không nhấp nháy**: ngưỡng commit ≥ ngưỡng dẫn ra. Thấp hơn nghĩa là một provider LÀNH MẠNH
       vẫn có thể rớt gate vì nhiễu lấy mẫu chứ không vì chất lượng — đúng thứ `Z=2·SE` sinh ra để
       tránh.
    2. **Không phải số tuỳ ý**: chênh lệch chỉ được là phép làm tròn lên. Nới thoải mái thì gate còn
       tồn tại trên giấy nhưng không chặn gì — cách hỏng ngược lại, và im lặng hơn.

    Bài này KHÔNG kiểm chất lượng retrieval; nó kiểm **phép chọn tham số có hợp lệ hay không**.
    """
    from tune_decoy_threshold import TUNE_PART, derive

    assert TUNE_PART == "validation", (
        f"ngưỡng đang được tune trên {TUNE_PART!r} — tune trên tập báo cáo là tái phạm kb#38 sai sót #2"
    )

    dan_ra, rows = derive()
    assert rows, "không đo được provider nào — phép lấy max rỗng thì ngưỡng vô nghĩa"

    commit = H.ABSOLUTE_MAX["decoy_fall"]
    assert commit >= dan_ra, f"ngưỡng commit {commit} THẤP hơn mức dẫn từ validation {dan_ra:.4f} — gate sẽ nhấp nháy"
    assert commit - dan_ra < 0.02, (
        f"ngưỡng commit {commit} cao hơn mức dẫn ra {dan_ra:.4f} tới {commit - dan_ra:.4f} — "
        f"chênh lệch chỉ được là làm tròn lên, không phải một con số nới tuỳ ý"
    )


def test_phep_dan_nguong_chi_doc_case_validation() -> None:
    """`derive()` chỉ được nhìn case validation.

    `TUNE_PART == "validation"` mới là khai báo; bài này kiểm HÀNH VI: số case mà phép dẫn dựa vào
    phải đúng bằng cỡ tập validation, và mọi id phải nằm trong đó. Đổi `build_report(p, TUNE_PART)`
    thành `build_report(p)` (mặc định `"all"`) sẽ lọt qua bài trên nhưng đỏ ở đây.
    """
    from tune_decoy_threshold import TUNE_PART, derive, gated_strata

    _, rows = derive()
    val_ids = H.load_validation_ids()
    for stratum in gated_strata():
        n_val = sum(1 for c in H.cases_for(TUNE_PART) if c.stratum == stratum and c.decoy_hint)
        got = {n for _, s, _, n in rows if s == stratum}
        assert got == {n_val}, f"{stratum}: phép dẫn dựa trên n={got}, cỡ validation là {n_val}"
    assert all(c.id in val_ids for c in H.cases_for(TUNE_PART))
