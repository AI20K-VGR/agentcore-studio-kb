"""Ghi (hoặc ghi đè) `golden/callisto-golden-30-v1.yaml` từ `golden_set.GOLDEN_CASES` (D16, DE).

    uv run --python 3.14 --package agentcore-studio-kb python packages/kb/scripts/emit_golden_set.py

Chạy lại phải ra **byte-identical**; `git diff` khác rỗng nghĩa là `GOLDEN_CASES` đã đổi mà quên
re-emit — có chủ đích thì commit file mới, vô tình thì `tests/test_golden_set.py` đã đỏ trước đó
(ca byte-identical). Cùng mẫu `emit_grid_queries.py` / `record_embeddings.py`.

CLI ở script chứ không phải `python -m studio_kb.golden_set`: `studio_kb/__init__.py` có thể nạp
module hai lần qua `-m`; giữ logic ở module để test import được, chỉ phần ghi file nằm đây.
"""

from __future__ import annotations

from pathlib import Path

from studio_kb.golden_set import GOLDEN_CASES, GOLDEN_SET_REF, render_yaml

_OUT_PATH = Path(__file__).resolve().parents[1] / "src" / "studio_kb" / "golden" / "callisto-golden-30-v1.yaml"


def main() -> None:
    _OUT_PATH.write_text(render_yaml(), encoding="utf-8")
    positives = sum(1 for case in GOLDEN_CASES if not case.is_refusal)
    refusals = len(GOLDEN_CASES) - positives
    print(f"đã ghi {_OUT_PATH.name} — {GOLDEN_SET_REF}: {positives} case dương + {refusals} âm")


if __name__ == "__main__":
    main()
