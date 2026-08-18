"""Ghi `baseline-dim8.json` — mốc TƯƠNG ĐỐI đóng băng của baseline dim-8 trên tập case hiện tại.

    uv run --python 3.14 python tests/embedding-tests/record_baseline.py

Chạy lại khi corpus/case đổi (có chủ đích) → `git diff` cho thấy con số dịch. `test_embedding_gate.py`
ở chế độ baseline so file này với phép chấm hiện tại (freshness); ở chế độ ứng viên đòi vượt file này
+ margin theo tầng. KHÔNG chạy trong pytest (đây là recorder, không phải test) — giống `record_embeddings.py`.
"""

from __future__ import annotations

import json
from typing import cast

import _harness as H

# Margin mỗi tầng = mức ứng viên phải VƯỢT baseline mới coi là hiệu quả. DE chỉnh; nằm trong git diff.
# S1 (dễ) yêu cầu nhỏ; S2/S3/S4 (ngữ nghĩa) yêu cầu bước nhảy rõ; S5 (sạch) vừa phải.
_DEFAULT_MARGIN = {"S1": 0.02, "S2": 0.10, "S3": 0.10, "S4": 0.10, "S5": 0.05}


def build_baseline_dict() -> dict[str, object]:
    report = H.build_report(H.BaselineDim8())
    strata: dict[str, object] = {}
    for s in H.STRATA:
        n = sum(1 for r in report.values() if r.stratum == s)
        strata[s] = {
            "recall": round(H.stratum_recall(report, s), 6),
            "mrr": round(H.stratum_mrr(report, s), 6),
            "n": n,
        }
    return {
        "provider": "baseline-dim8",
        "top_k": H.TOP_K,
        "note": "mốc tương đối đóng băng — ứng viên phải vượt recall + margin[tầng]. S5 recall = 1-top_sim (cao=sạch).",
        "strata": strata,
        "margin": _DEFAULT_MARGIN,
    }


def main() -> None:
    payload = build_baseline_dict()
    H.BASELINE_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    strata = cast("dict[str, dict[str, float]]", payload["strata"])
    margin = cast("dict[str, float]", payload["margin"])
    print(f"ghi {H.BASELINE_PATH.name}:")
    for s, v in strata.items():
        print(f"  {s}: recall={v['recall']:.4f} mrr={v['mrr']:.4f} n={v['n']} margin={margin[s]}")


if __name__ == "__main__":
    main()
