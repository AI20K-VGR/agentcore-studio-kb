"""Ghi (hoặc ghi đè) `golden/callisto-grid-queries-v0.yaml` từ `grid_queries.GRID_CASES` (D14, DE).

    uv run --python 3.14 --package agentcore-studio-kb python packages/kb/scripts/emit_grid_queries.py

Chạy lại phải ra **byte-identical**; `git diff` khác rỗng nghĩa là `GRID_CASES` đã đổi mà quên
re-emit — có chủ đích thì commit file mới, vô tình thì `tests/test_grid_inputs.py` đã đỏ trước đó.

CLI ở script chứ không phải `python -m studio_kb.grid_queries`: `studio_kb/__init__.py` không kéo
`grid_queries` nên `-m` không nạp hai lần, nhưng giữ cùng mẫu với `record_embeddings.py` cho nhất quán
— logic ở module để test import được, chỉ phần ghi file nằm đây.
"""

from __future__ import annotations

from pathlib import Path

from studio_kb.grid_queries import GRID_CASES, GRID_SET_REF, render_yaml

_OUT_PATH = Path(__file__).resolve().parents[1] / "golden" / "callisto-grid-queries-v0.yaml"


def main() -> None:
    _OUT_PATH.write_text(render_yaml(), encoding="utf-8")
    positives = sum(1 for case in GRID_CASES if not case.is_refusal)
    refusals = len(GRID_CASES) - positives
    print(f"đã ghi {_OUT_PATH.name} — {GRID_SET_REF}: {positives} case dương + {refusals} âm")


if __name__ == "__main__":
    main()
