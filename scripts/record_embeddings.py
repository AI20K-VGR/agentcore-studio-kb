"""Ghi (hoặc ghi đè) `golden/embeddings-callisto-v0.json` (D7, DE).

    uv run python packages/kb/scripts/record_embeddings.py

Chạy lại phải ra **byte-identical**; `git diff` khác rỗng nghĩa là corpus hoặc công thức
`derive_vector` đã đổi. Đổi có chủ đích (vd gateway thật về) thì commit file mới — đó là re-record
hợp lệ; còn không thì đó là hồi quy, và `tests/test_embedding_fixture.py` đã đỏ trước khi bạn chạy
lệnh này.

Vì sao CLI nằm ở script chứ không phải `python -m studio_kb.embeddings`: `studio_kb/__init__.py`
import sẵn `embeddings`, nên `-m` nạp module hai lần (một lần qua package, một lần dưới tên
`__main__`) và Python cảnh báo `RuntimeWarning`. Logic ở lại module để test import được; chỉ phần
gọi nằm đây.
"""

from __future__ import annotations

from studio_kb.embeddings import FIXTURE_PATH, build_fixture, dump_fixture


def main() -> None:
    fixture = build_fixture()
    FIXTURE_PATH.write_text(dump_fixture(fixture), encoding="utf-8")
    vectors = fixture["vectors"]
    assert isinstance(vectors, dict)
    print(f"đã ghi {FIXTURE_PATH.name} — {len(vectors)} chunk, {fixture['dim']} chiều")


if __name__ == "__main__":
    main()
