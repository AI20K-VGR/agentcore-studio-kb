"""`mutation_sweep` self-test — khoá phần logic tinh vi của chính tool sweep (chạy **không cần
Postgres**).

- `_restore_orig_files` + path-inverse: bug đã bắt `with_suffix("").with_suffix(".py")` cho
  `<tên>.py.mutation_sweep.orig` ra `<tên>.py.py` (không bao giờ tồn tại) → restore không chạy mà
  `.orig` vẫn bị xoá ⇒ mutant thường trú.
- **Toán tử `sqlline` (D17):** bỏ mệnh đề `AND`/`OR` trong hằng chuỗi SQL — thêm vào tool sau khi lỗ
  mất `AND embedding IS NOT NULL` lọt qua 4 toán tử node. Logic này (`_sql_drop_line_indices` +
  nhánh `str` trong `_thu_thap`/`_dot_bien`) phải được test như mọi code khác — nếu collect↔apply
  lệch nhau thì bộ đếm `muc_tieu` trượt và mọi số sweep thành rác.
"""

from __future__ import annotations

import ast
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


# ── Toán tử sqlline (D17) ───────────────────────────────────────────────────────


def test_sqlline_chi_bat_and_or_trong_chuoi_sql() -> None:
    """Chỉ lấy dòng `AND`/`OR`, và chỉ trên chuỗi bắt đầu bằng lệnh SQL."""
    sql = "\nSELECT x\nFROM t\nWHERE a = %s\n  AND b = %s\n  AND c IS NOT NULL\n"
    idx = mutation_sweep._sql_drop_line_indices(sql)
    lines = sql.split("\n")
    assert [lines[i].strip() for i in idx] == ["AND b = %s", "AND c IS NOT NULL"]


def test_sqlline_bo_qua_prose_va_chuoi_mot_dong() -> None:
    """Văn xuôi/docstring chứa 'WHERE'/'AND' nhưng KHÔNG bắt đầu bằng lệnh SQL → bỏ qua (chống ngập
    survivor). Chuỗi một dòng cũng không có ứng viên."""
    prose = "Ghi chú: lọc theo WHERE tenant.\nAND đây là văn xuôi, không phải SQL"
    assert mutation_sweep._sql_drop_line_indices(prose) == []
    assert mutation_sweep._sql_drop_line_indices("SELECT 1 WHERE a AND b") == []


def test_sqlline_khop_search_that_cua_postgres() -> None:
    """Neo vào SQL THẬT: `_SEARCH` phải có đúng 2 mệnh đề `AND` bỏ được (chính là chỗ lỗ M3 từng
    lọt). Nếu ai đổi shape query, test này kêu."""
    from studio_kb import postgres

    idx = mutation_sweep._sql_drop_line_indices(postgres._SEARCH)
    dropped = [postgres._SEARCH.split("\n")[i].strip() for i in idx]
    assert dropped == ["AND section_role = ANY(%s)", "AND embedding IS NOT NULL"]


def test_sqlline_collect_va_apply_dong_bo() -> None:
    """collect↔apply phải khớp: ứng viên sqlline thứ k, `_dot_bien` bỏ ĐÚNG dòng đó (không lệch bộ
    đếm). Đây là chỗ dễ vỡ nhất khi thêm toán tử mới."""
    src = 'Q = """\nSELECT x\nFROM t\nWHERE a = %s\n  AND b = %s\n  AND c = %s\n"""\n'
    cands = mutation_sweep._thu_thap(ast.parse(src))
    sql_cands = [i for i, c in enumerate(cands) if c.kind == "sqlline"]
    assert len(sql_cands) == 2

    # Tách từng vế (không `and`): để mutation And->Or trên chính assert này bị bắt, và lỗi rõ vế nào.
    out0 = ast.unparse(mutation_sweep._dot_bien(ast.parse(src), sql_cands[0]))
    assert "AND b = %s" not in out0  # ứng viên đầu → bỏ đúng dòng "AND b"
    assert "AND c = %s" in out0  # dòng "AND c" phải còn nguyên
    out1 = ast.unparse(mutation_sweep._dot_bien(ast.parse(src), sql_cands[1]))
    assert "AND c = %s" not in out1  # ứng viên sau → bỏ đúng dòng "AND c"
    assert "AND b = %s" in out1  # dòng "AND b" phải còn nguyên


def test_sqlline_khong_sinh_tu_docstring() -> None:
    """`_thu_thap` không được sinh ứng viên `sqlline` từ docstring văn xuôi (chỉ `const` cho số)."""
    src = 'def f():\n    """WHERE tenant.\n    AND prose."""\n    return 1\n'
    cands = mutation_sweep._thu_thap(ast.parse(src))
    assert not any(c.kind == "sqlline" for c in cands)


# ── Toán tử mở rộng (cmpbound / arith / int-variant / delstmt) ───────────────────


def test_cmpbound_song_song_voi_cmp_negation() -> None:
    """Một `<` sinh HAI ứng viên độc lập: negation (`cmp`, `Lt->GtE`) và dịch biên (`cmpbound`,
    `Lt->LtE`). Biên là lớp bắt off-by-one mà negation bỏ lọt."""
    cands = mutation_sweep._thu_thap(ast.parse("y = x < 5\n"))
    cmp_ = [c for c in cands if c.kind == "cmp"]
    bound = [c for c in cands if c.kind == "cmpbound"]
    assert [c.mo_ta for c in cmp_] == ["Lt -> GtE"]
    assert [c.mo_ta for c in bound] == ["Lt -> LtE"]


def test_cmpbound_apply_doi_lt_thanh_lte() -> None:
    """`_dot_bien` áp ứng viên `cmpbound` phải đổi ĐÚNG `<` thành `<=` (không lật hướng)."""
    src = "y = x < 5\n"
    cands = mutation_sweep._thu_thap(ast.parse(src))
    idx = next(i for i, c in enumerate(cands) if c.kind == "cmpbound")
    assert ast.unparse(mutation_sweep._dot_bien(ast.parse(src), idx)).strip() == "y = x <= 5"


def test_arith_apply_doi_cong_thanh_tru() -> None:
    """Toán tử số học: `+` → `-` đúng chỗ (kind `arith`)."""
    src = "z = a + b\n"
    cands = mutation_sweep._thu_thap(ast.parse(src))
    idx = [i for i, c in enumerate(cands) if c.kind == "arith"]
    assert len(idx) == 1
    assert ast.unparse(mutation_sweep._dot_bien(ast.parse(src), idx[0])).strip() == "z = a - b"


def test_int_sinh_du_ba_bien_the() -> None:
    """Hằng int `v` (≠0) sinh đủ ba biến thể: `v+1`, `v-1`, `0`."""
    const = [c for c in mutation_sweep._thu_thap(ast.parse("n = 5\n")) if c.kind == "const"]
    assert {c.mo_ta for c in const} == {"5 -> 6", "5 -> 4", "5 -> 0"}


def test_int_zero_bo_bien_the_zero() -> None:
    """`v == 0` thì bỏ biến thể `v→0` (trùng chính nó, mutant vô nghĩa) — chỉ còn `+1`/`-1`."""
    const = [c for c in mutation_sweep._thu_thap(ast.parse("n = 0\n")) if c.kind == "const"]
    assert {c.mo_ta for c in const} == {"0 -> 1", "0 -> -1"}


def test_int_collect_va_apply_dong_bo() -> None:
    """collect↔apply đồng bộ cho int: mỗi ứng viên `const`, `_dot_bien` sinh ĐÚNG giá trị mô tả."""
    src = "n = 5\n"
    cands = mutation_sweep._thu_thap(ast.parse(src))
    for i, c in enumerate(cands):
        if c.kind != "const":
            continue
        want = c.mo_ta.split("-> ")[1]
        assert ast.unparse(mutation_sweep._dot_bien(ast.parse(src), i)).strip() == f"n = {want}"


def test_delstmt_xoa_dung_cau_lenh() -> None:
    """`delstmt` xoá đúng từng câu lệnh trong body (không đụng `def`); ứng viên đầu bỏ `a = 1`."""
    src = "def f():\n    a = 1\n    b = 2\n    return a\n"
    cands = mutation_sweep._thu_thap(ast.parse(src))
    dels = [i for i, c in enumerate(cands) if c.kind == "delstmt"]
    assert len(dels) == 3  # a=1, b=2, return a — KHÔNG có `def`
    out0 = ast.unparse(mutation_sweep._dot_bien(ast.parse(src), dels[0]))
    assert "a = 1" not in out0
    assert "b = 2" in out0
    assert "return a" in out0


def test_delstmt_chen_pass_khi_body_rong() -> None:
    """Xoá câu lệnh duy nhất → body rỗng → chèn `pass` cho `ast.unparse` khỏi vỡ."""
    src = "def g():\n    x = 1\n"
    cands = mutation_sweep._thu_thap(ast.parse(src))
    dels = [i for i, c in enumerate(cands) if c.kind == "delstmt"]
    assert len(dels) == 1
    out = ast.unparse(mutation_sweep._dot_bien(ast.parse(src), dels[0]))
    assert "x = 1" not in out
    assert out.strip() == "def g():\n    pass"


def test_delstmt_bo_qua_docstring_import_pass_def() -> None:
    """`delstmt` bỏ qua docstring / import / from / `def` / `pass` — chỉ câu lệnh thường mới xoá."""
    src = '"""module doc."""\nimport os\nfrom sys import path\ndef g():\n    pass\ny = 1\n'
    dels = [c for c in mutation_sweep._thu_thap(ast.parse(src)) if c.kind == "delstmt"]
    assert len(dels) == 1  # chỉ `y = 1`
    assert "y = 1" in dels[0].mo_ta


def test_delstmt_bo_qua_chuoi_chu_thich_tran_giua_body() -> None:
    """Chuỗi trần KHÔNG ở đầu body (ghi-chú-as-string) cũng bị bỏ — xoá là no-op runtime, nếu không
    skip sẽ thành survivor rác vĩnh viễn (không test nào kill được)."""
    src = "def f():\n    x = 1\n    'ghi chú giữa body'\n    return x\n"
    dels = [c for c in mutation_sweep._thu_thap(ast.parse(src)) if c.kind == "delstmt"]
    assert not any("ghi chú" in c.mo_ta for c in dels)  # chuỗi trần không sinh mutant
    assert any("x = 1" in c.mo_ta for c in dels)  # câu lệnh thật vẫn có
    assert any("return x" in c.mo_ta for c in dels)


def test_delstmt_bo_qua_if_type_checking() -> None:
    """Khối `if TYPE_CHECKING:` luôn False lúc chạy → thân không thực thi → xoá là no-op → không sinh
    mutant (rác vĩnh viễn nếu để lọt). Nhận cả `TYPE_CHECKING` trần lẫn `typing.TYPE_CHECKING`."""
    for guard in ("TYPE_CHECKING", "typing.TYPE_CHECKING"):
        src = f"import typing\nif {guard}:\n    from x import Y\nz = 1\n"
        dels = [c for c in mutation_sweep._thu_thap(ast.parse(src)) if c.kind == "delstmt"]
        assert not any("TYPE_CHECKING" in c.mo_ta for c in dels)  # khối if không bị đề xuất xoá
        assert any("z = 1" in c.mo_ta for c in dels)
