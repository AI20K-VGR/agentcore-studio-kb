"""Ghi (hoặc ghi đè) `golden/callisto-2.0-golden-30-v1.yaml` từ `golden_set_v2.GOLDEN_CASES_V2`.

    uv run --python 3.14 --package agentcore-studio-kb python packages/kb/scripts/emit_golden_set_v2.py

Chạy lại phải ra **byte-identical**; `git diff` khác rỗng nghĩa là `GOLDEN_CASES_V2` đã đổi mà quên
re-emit (`tests/test_golden_set_v2.py` byte-identical đã đỏ trước đó). Cùng mẫu `emit_golden_set.py`.
"""

from __future__ import annotations

from pathlib import Path

from studio_kb.golden_set_v2 import GOLDEN_CASES_V2, GOLDEN_SET_REF_V2, render_yaml

_OUT_PATH = Path(__file__).resolve().parents[1] / "src" / "studio_kb" / "golden" / "callisto-2.0-golden-30-v1.yaml"


def main() -> None:
    _OUT_PATH.write_text(render_yaml(), encoding="utf-8")
    positives = sum(1 for case in GOLDEN_CASES_V2 if not case.is_refusal)
    refusals = len(GOLDEN_CASES_V2) - positives
    print(f"đã ghi {_OUT_PATH.name} — {GOLDEN_SET_REF_V2}: {positives} case dương + {refusals} âm")


if __name__ == "__main__":
    main()
