"""Ghi `baseline-dim8.json` — mốc TƯƠNG ĐỐI đóng băng của baseline dim-8 trên tập case hiện tại.

    uv run --python 3.14 python tests/embedding-tests/record_baseline.py

Chạy lại khi corpus/case/công thức chấm đổi (có chủ đích) → `git diff` cho thấy con số dịch.
`test_embedding_gate.py` ở chế độ baseline so file này với phép chấm hiện tại (freshness); ở chế độ
ứng viên đòi vượt file này + margin theo tầng, CHỈ trên các metric trong `H.GATED_METRICS[tầng]`.
KHÔNG chạy trong pytest (đây là recorder, không phải test) — giống `record_embeddings.py`.
"""

from __future__ import annotations

import json

import _harness as H

# Margin mỗi (tầng, metric) = mức ứng viên phải VƯỢT baseline mới coi là hiệu quả — chỉ áp dụng cho
# metric nằm trong `H.GATED_METRICS[tầng]`, còn lại bỏ qua dù có mặt ở đây. S1 (dễ) yêu cầu nhỏ;
# S2–S4 (ngữ nghĩa) yêu cầu bước nhảy rõ; `max_cosine_mean` chiều 'lower' — margin vẫn là một khoảng
# cách dương, `test_embedding_gate.py` tự đảo dấu theo `H.METRIC_DIRECTION`.
#
# **`decoy_fall` CỐ Ý VẮNG MẶT ở đây** — nó gate bằng ngưỡng tuyệt đối `H.ABSOLUTE_MAX`, không so
# tương đối với dim-8 (dim-8 thắng metric này một cách tầm thường vì xếp hạng gần như ngẫu nhiên; so
# tương đối cho ra ngưỡng ÂM, bất khả thi — xem docstring `H.ABSOLUTE_MAX`). Để margin `decoy_fall`
# ở đây là cấu hình chết, gây hiểu nhầm rằng nó còn hiệu lực.
_DEFAULT_MARGIN: dict[str, dict[str, float]] = {
    "S1": {"hit1": 0.02, "hit3": 0.02, "hit5": 0.02, "mrr5": 0.02},
    "S2": {"hit1": 0.10, "hit3": 0.10, "hit5": 0.10, "mrr5": 0.10},
    "S3": {"hit1": 0.10, "hit3": 0.10, "hit5": 0.10, "mrr5": 0.10},
    "S4": {"hit1": 0.10, "hit3": 0.10, "hit5": 0.10, "mrr5": 0.10},
    "S5": {"max_cosine_mean": 0.05},
}


def build_baseline_dict() -> dict[str, object]:
    report = H.build_report(H.BaselineDim8())
    strata: dict[str, object] = {}
    for s in H.STRATA:
        n = sum(1 for r in report.values() if r.stratum == s)
        metrics = {m: H.stratum_metric(report, s, m) for m in H.ALL_METRICS}
        strata[s] = {"n": n, **{m: (round(v, 6) if v is not None else None) for m, v in metrics.items()}}
    return {
        "provider": "baseline-dim8",
        "top_k": H.TOP_K,
        "max_k": H.MAX_K,
        "note": (
            "mốc đóng băng — ứng viên phải vượt các metric trong gated_metrics[tầng] + margin[tầng]. "
            "Metric ngoài gated_metrics chỉ để tham khảo, không chặn CI. Metric trong absolute_max "
            "gate bằng NGƯỠNG TUYỆT ĐỐI (got <= ngưỡng), bỏ qua baseline+margin."
        ),
        "strata": strata,
        "gated_metrics": {s: list(ms) for s, ms in H.GATED_METRICS.items()},
        "margin": _DEFAULT_MARGIN,
        "absolute_max": H.ABSOLUTE_MAX,
    }


def main() -> None:
    payload = build_baseline_dict()
    H.BASELINE_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    strata = payload["strata"]
    assert isinstance(strata, dict)
    print(f"ghi {H.BASELINE_PATH.name}:")
    for s, v in strata.items():
        assert isinstance(v, dict)
        parts = ", ".join(f"{m}={v[m]}" for m in H.ALL_METRICS)
        print(f"  {s}: n={v['n']} {parts}")


if __name__ == "__main__":
    main()
