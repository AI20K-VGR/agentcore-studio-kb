"""Sinh `cases/validation-split.json` — tách 33% validation, phân tầng, tất định.

    uv run --python 3.14 python packages/kb/tests/embedding-tests/make_validation_split.py

CHẠY MỘT LẦN rồi commit kết quả. Không phải thứ chạy lại mỗi lần test: split phải ĐÓNG BĂNG, vì
tune tham số trên một tập rồi đổi tập đó dưới chân mình thì việc tách mất sạch ý nghĩa
(`_harness.load_validation_ids` đọc file, không gọi lại hàm này).

## Vì sao 33%, và vì sao phân tầng

Tỉ lệ do chủ repo chốt. Phân tầng (`stratum`) là bắt buộc chứ không phải tinh tế thừa: 5 tầng S1–S5
đo năm thứ khác nhau (S2 paraphrase, S5 no-answer...). Lấy mẫu ngẫu nhiên trên toàn bộ 300 case có
thể rút validation gần như không có S4, và ngưỡng tune ra sẽ chưa từng nhìn thấy tầng đó.

## Vì sao `Random(seed).sample` chứ không cắt N case đầu

Id case mang thông tin (`s1-001`... sinh theo lô, cùng khuôn). Cắt theo thứ tự là để validation trúng
trọn một lô — cùng chủ đề, cùng tenant. Bốc ngẫu nhiên có seed vừa trải đều vừa tái lập được.
"""

from __future__ import annotations

import json
import random
from collections import defaultdict

import _harness as H

SEED = 20260819
"""Seed đóng băng. Ghi cả vào file kết quả để ai cũng dựng lại được đúng split này."""

RATIO = 0.33


def build_split(seed: int = SEED, ratio: float = RATIO) -> dict[str, object]:
    by_stratum: dict[str, list[str]] = defaultdict(list)
    for case in H.load_cases():
        by_stratum[case.stratum].append(case.id)

    rng = random.Random(seed)  # noqa: S311 — lấy mẫu tái lập được, không phải mục đích mật mã
    validation: list[str] = []
    per_stratum: dict[str, dict[str, int]] = {}
    for stratum in sorted(by_stratum):
        ids = sorted(by_stratum[stratum])  # sắp trước khi bốc — thứ tự đọc file không được ảnh hưởng
        k = round(len(ids) * ratio)
        picked = rng.sample(ids, k)
        validation.extend(picked)
        per_stratum[stratum] = {"total": len(ids), "validation": k, "test": len(ids) - k}

    return {
        "seed": seed,
        "ratio": ratio,
        "generated_by": "tests/embedding-tests/make_validation_split.py",
        "per_stratum": per_stratum,
        "validation": sorted(validation),
    }


if __name__ == "__main__":
    split = build_split()
    H.SPLIT_PATH.write_text(json.dumps(split, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    counts = split["per_stratum"]
    assert isinstance(counts, dict)
    print(f"ghi {H.SPLIT_PATH.name}: {len(split['validation'])}/{len(H.load_cases())} case vào validation")  # type: ignore[arg-type]
    for stratum, row in sorted(counts.items()):
        print(f"  {stratum}: val={row['validation']:>3}  test={row['test']:>3}  (tổng {row['total']})")
