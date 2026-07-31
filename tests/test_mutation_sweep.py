"""`mutation_sweep._restore_orig_files` — khoá tính nghịch đảo của cặp đường dẫn `.orig`.

Chạy **không cần Postgres**: chỉ đụng số học đường dẫn và I/O trên `tmp_path`, đúng chỗ suite
mutation phủ 0%. Bug đã bắt: `with_suffix("").with_suffix(".py")` cho `<tên>.py.mutation_sweep.orig`
ra `<tên>.py.py` (không bao giờ tồn tại) → nhánh restore không chạy mà `.orig` vẫn bị xoá ⇒ mutant
thường trú. `test_orig_va_src_nghich_dao` khoá đúng một dòng số học đó; `test_restore_khoi_phuc_mutant`
chạy thẳng hàm trên cây giả để chốt hành vi round-trip.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_MUT = Path(__file__).resolve().parent.parent / "scripts" / "mutation_sweep.py"
_spec = importlib.util.spec_from_file_location("mutation_sweep", _MUT)
assert _spec is not None and _spec.loader is not None
mutation_sweep = importlib.util.module_from_spec(_spec)
# Đăng ký vào sys.modules trước khi exec: `@dataclass` trong module tra `sys.modules[__module__]`.
sys.modules[_spec.name] = mutation_sweep
_spec.loader.exec_module(mutation_sweep)


def test_orig_va_src_nghich_dao() -> None:
    """`orig_path(src)` và `src_path(orig)` phải là nghịch đảo — kể cả tên nhiều dấu chấm."""
    for name in ("trace_reader.py", "a.b.py"):
        f = mutation_sweep.SRC / name
        orig = f.with_suffix(f".py{mutation_sweep._ORIG_SUFFIX}")
        assert orig.with_name(orig.name.removesuffix(mutation_sweep._ORIG_SUFFIX)) == f


def test_restore_khoi_phuc_mutant(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`.orig` còn sót (lần sweep bị kill) → source phải trở về bản gốc, `.orig` bị dọn."""
    monkeypatch.setattr(mutation_sweep, "SRC", tmp_path)
    src = tmp_path / "trace_reader.py"
    orig = src.with_suffix(f".py{mutation_sweep._ORIG_SUFFIX}")
    src.write_text("MUTANT")
    orig.write_text("GOC")

    mutation_sweep._restore_orig_files()

    assert src.read_text() == "GOC"  # mutant đã bị thay bằng bản gốc
    assert not orig.exists()  # .orig đã được dọn sau khi restore


def test_restore_ghi_lai_ca_khi_nguon_da_bi_xoa(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Nguồn đã mất mà `.orig` còn → vẫn dựng lại nguồn rồi mới xoá `.orig` (không mất bản copy)."""
    monkeypatch.setattr(mutation_sweep, "SRC", tmp_path)
    orig = tmp_path / f"trace_reader.py{mutation_sweep._ORIG_SUFFIX}"
    orig.write_text("GOC")

    mutation_sweep._restore_orig_files()

    assert (tmp_path / "trace_reader.py").read_text() == "GOC"
    assert not orig.exists()
