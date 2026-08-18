"""Gate hiệu quả — thanh **tương đối** so baseline dim-8 đóng băng (`baseline-dim8.json`).

Hai chế độ, tự nhận theo provider:
- provider = **baseline dim-8** (mặc định, CI hằng ngày): gate = *freshness* — recall/MRR mỗi tầng phải
  KHỚP file đóng băng. Chuông báo nếu corpus/công thức đổi mà quên re-record baseline → CI XANH khi khớp.
- provider = **model ứng viên** (tiêm qua fixture khi chọn model sau): gate = *cải thiện* —
  `recall@k(ứng viên) ≥ recall@k(baseline) + margin[tầng]`. Không lách được vì baseline nằm trong git diff.

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
    base_recall = baseline["strata"][stratum]["recall"]
    got_recall = H.stratum_recall(report, stratum)

    if _is_baseline(embedding_provider):
        # freshness: baseline đóng băng phải khớp phép chấm hiện tại của chính dim-8.
        assert got_recall == pytest.approx(base_recall, abs=_FRESHNESS_TOL), (
            f"{stratum}: baseline-dim8.json (recall={base_recall}) lệch phép chấm hiện tại "
            f"({got_recall}) — corpus/công thức đổi? re-record baseline có chủ đích."
        )
        return

    # ứng viên: phải VƯỢT baseline theo margin của tầng.
    margin = baseline["margin"][stratum]
    assert got_recall >= base_recall + margin, (
        f"{stratum}: recall@{H.TOP_K} ứng viên={got_recall:.4f} < baseline {base_recall:.4f} + margin {margin} "
        f"— chưa đủ tốt hơn dim-8 ở tầng này"
    )
