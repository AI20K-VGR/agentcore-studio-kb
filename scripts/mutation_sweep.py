"""Quét toàn bộ `packages/kb/src` bằng đột biến AST — tìm chỗ không bài test nào canh (D9, DE).

    docker compose -f docker-compose.test.yml up -d
    export STUDIO_DATABASE_URL_ADMIN=postgresql://studio_owner:changeme@localhost:5433/studio_test
    export STUDIO_DATABASE_URL=postgresql://studio_app:changeme@localhost:5433/studio_test
    uv run --python 3.14 python packages/kb/scripts/mutation_sweep.py   # ~100s (operator + mệnh đề SQL)

Khác `mutation_check.py` ở chỗ: bài kia là **bộ mutant tuyển chọn** có khai trước tên bài phải đỏ,
dùng làm bằng chứng nộp kèm. Bài này **quét mù** toàn bộ source để đi TÌM chỗ chưa ai canh.

Mỗi lần đổi ĐÚNG MỘT nút trong cây cú pháp, chạy lại suite, rồi trả file về nguyên trạng.
  - suite ĐỎ  → có bài test bắt được → chỗ đó có người canh.
  - suite XANH → không ai bắt → "mutant sống sót" = ứng viên lỗ hổng.

**Mutant sống sót KHÔNG tự động là lỗi.** Phần lớn là *tương đương*: đổi mà hành vi không đổi, nên
không test nào đỏ được. Bắt buộc đọc từng cái. Kết quả phân loại lần chạy 2026-07-30 (9 sống sót):

- `postgres.py` `if top_k <= 0 or not section_roles` → `and` — **tương đương**: SQL cũng
  fail-closed (`section_role = ANY('{}')` không khớp gì). Hai lớp độc lập cùng chặn.
- `postgres.py` `zip(..., strict=True)` → `False` — **tương đương**: phía trên đã có
  `if len(vectors) != len(batch): raise` bắt trước.
- `embeddings.py` `@lru_cache(maxsize=1)` → `2` — **tương đương**: kích thước cache
  không đổi hành vi.
- `trace_reader.py` `counts.get(nt, 0) > 1` → `(nt, 1)` — **tương đương**: cả 0 và 1
  đều cho `> 1` là False.
- `trace_reader.py` `ordered[0].run_id` → `[1]` — **tương đương** trong mọi ca đã test:
  mọi event cùng run chung `run_id`. Chỉ vỡ khi timeline có đúng 1 event, mà đây là
  công cụ gỡ lỗi.
- `Chunk` / `WalkCheck` `@dataclass(frozen=True, slots=True)` → `False` (4 mutant) —
  bất biến **thiết kế**, không bài nào khoá. Cố ý KHÔNG thêm test: khẳng định `frozen`
  là kiểm cái decorator, không kiểm một hành vi nào có người dùng.

Hai lỗ THẬT lần quét này tìm ra, đã vá:
  - `postgres.py` biên `top_k=1` — bản Static đã khoá, bản Postgres thì chưa (`test_pg_kb.py`).
  - `embeddings.py` nhánh vector-0 — docstring chốt hành vi mà không ai kiểm (`test_embedding_fixture.py`).

**Giới hạn phải biết:** bộ toán tử (`_points` là nguồn duy nhất — collect và apply cùng đi qua nó):
  1. so sánh — negation `Eq↔NotEq`, `Lt↔GtE`… (kind `cmp`) VÀ dịch biên `<`↔`<=`, `>`↔`>=`
     (kind `cmpbound`, bắt off-by-one như lỗ `top_k=1`);
  2. `and`↔`or` (kind `bool`), bỏ `not` (kind `not`);
  3. số học `+`↔`-`, `*`↔`/`, `%`↔`//` (kind `arith`);
  4. hằng bool đảo, hằng int `v→v+1 / v-1 / 0` (kind `const`);
  5. bỏ mệnh đề `AND`/`OR` trong hằng CHUỖI SQL (kind `sqlline`, thêm ở D17 sau khi lỗ mất
     `AND embedding IS NOT NULL` lọt qua toán tử node — xem `_sql_drop_line_indices`);
  6. xoá câu lệnh (kind `delstmt` — bắt lớp "quên gọi `_bind_tenant`"; body rỗng thì chèn `pass`).
     BỎ QUA thứ xoá-đi-runtime-không-đổi (mutant tương đương, không kill được): import/`pass`/
     `def`/`class`, chuỗi trần `Expr(str)` ở mọi vị trí, và khối `if TYPE_CHECKING:` — xem
     `_co_the_xoa`.
VẪN chưa phủ: đổi giá trị trả về tuỳ ý, hằng chuỗi phi-SQL, biên lát cắt, nhánh bắt ngoại lệ, đảo thứ
tự câu lệnh. "0 sống sót" nghĩa là sạch **theo các loại này**, không phải sạch tuyệt đối.
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

_KB = Path(__file__).resolve().parent.parent
ROOT = _KB.parent.parent
SRC = _KB / "src" / "studio_kb"
_ORIG_SUFFIX = ".mutation_sweep.orig"


def _restore_orig_files() -> None:
    """Khôi phục file `.orig` còn sót lại từ lần sweep bị kill giữa chừng.

    `finally: f.write_text(goc)` chỉ chạy khi Python kịp xử lý — bị `SIGKILL`, hết bộ nhớ,
    hoặc tiến trình cha hạ bằng tín hiệu không bắt được thì `finally` KHÔNG chạy và file
    nguồn nằm lại ở trạng thái đột biến. Mọi con số đo trên cây đó là vô nghĩa.

    Cơ chế: trước khi ghi mutant, lưu bản gốc sang `<file>.mutation_sweep.orig`. Sau khi
    restore, xoá `.orig`. Nếu `.orig` còn tồn tại lúc khởi động → lần trước bị kill, phải
    khôi phục trước khi đo bất cứ gì.
    """
    for orig in SRC.glob(f"*{_ORIG_SUFFIX}"):
        # `with_suffix` chỉ đổi suffix cuối; `.py` nằm trong stem nên phải cắt bằng
        # `removesuffix` — nếu không, `<tên>.py.mutation_sweep.orig` ra `<tên>.py.py`
        # (không bao giờ tồn tại) và nhánh restore không chạy.
        src_file = orig.with_name(orig.name.removesuffix(_ORIG_SUFFIX))
        # Luôn ghi bản gốc trước (write_text tự tạo file nếu nguồn đã bị xoá), rồi mới
        # xoá `.orig`. Tuyệt đối không xoá `.orig` khi chưa restore — đó là bản copy duy nhất.
        src_file.write_text(orig.read_text())
        print(f"⚠ Khôi phục {src_file.name} từ {orig.name} (lần sweep trước bị kill)")
        orig.unlink()


_CMP_SWAP = {
    ast.Eq: ast.NotEq,
    ast.NotEq: ast.Eq,
    ast.Lt: ast.GtE,
    ast.GtE: ast.Lt,
    ast.Gt: ast.LtE,
    ast.LtE: ast.Gt,
    ast.In: ast.NotIn,
    ast.NotIn: ast.In,
    ast.Is: ast.IsNot,
    ast.IsNot: ast.Is,
}

# Dịch BIÊN (khác negation ở trên): `<`↔`<=`, `>`↔`>=`. Bắt off-by-one/lẫn biên — đúng lớp lỗi
# `top_k=1` mà negation không cô lập được (đổi `<` thành `>=` là lật hẳn hướng, không phải xê biên).
_CMP_BOUND: dict[type[ast.cmpop], type[ast.cmpop]] = {
    ast.Lt: ast.LtE,
    ast.LtE: ast.Lt,
    ast.Gt: ast.GtE,
    ast.GtE: ast.Gt,
}

# Số học: `+`↔`-`, `*`↔`/`, `%`↔`//`. Bắt công thức sai dấu/sai phép (paginate, offset, chia lô…).
_ARITH_SWAP: dict[type[ast.operator], type[ast.operator]] = {
    ast.Add: ast.Sub,
    ast.Sub: ast.Add,
    ast.Mult: ast.Div,
    ast.Div: ast.Mult,
    ast.Mod: ast.FloorDiv,
    ast.FloorDiv: ast.Mod,
}


@dataclass
class Cand:
    kind: str
    line: int
    mo_ta: str


_SQL_START = ("SELECT", "INSERT", "UPDATE", "DELETE", "WITH")
_SQL_DROP_PREFIX = ("AND ", "OR ")


def _sql_drop_line_indices(s: str) -> list[int]:
    """Chỉ số các dòng mệnh đề `AND`/`OR` có thể bỏ trong một hằng chuỗi SQL nhiều dòng.

    Bỏ một conjunct = nới lỏng bộ lọc — đúng LỚP lỗ mà 4 toán tử cũ KHÔNG chạm tới: mệnh đề nằm
    trong hằng CHUỖI, không phải node so sánh/bool/int, nên `ast.walk` không có gì để đổi. Chính là
    chỗ `_SEARCH` mất `AND embedding IS NOT NULL` (hay `AND section_role = ANY(%s)`) lọt lưới.

    Chỉ nhận chuỗi **bắt đầu bằng lệnh SQL** (SELECT/INSERT/…) để không quét nhầm docstring/prose có
    chứa chữ "WHERE"/"AND". Bỏ dòng `AND`/`OR` trên câu `WHERE x AND y AND z` luôn còn cú pháp hợp lệ.
    """
    if "\n" not in s or not s.strip().upper().startswith(_SQL_START):
        return []
    return [i for i, ln in enumerate(s.split("\n")) if ln.strip().upper().startswith(_SQL_DROP_PREFIX)]


# ── apply-factory: mỗi cái trả một closure đổi node IN-PLACE ──
# Vì sao factory ở tầng module, không def-lồng trong `_points`: định nghĩa nhiều `def ap` cùng tên
# trong một scope là lỗi redefinition với mypy. Tách ra vừa qua type-check, vừa test được từng cái.
def _mk_cmp(node: ast.Compare, i: int, new: type[ast.cmpop]) -> Callable[[], None]:
    def ap() -> None:
        node.ops[i] = new()

    return ap


def _mk_bool(node: ast.BoolOp) -> Callable[[], None]:
    def ap() -> None:
        node.op = ast.Or() if isinstance(node.op, ast.And) else ast.And()

    return ap


def _mk_binop(node: ast.BinOp, new: type[ast.operator]) -> Callable[[], None]:
    def ap() -> None:
        node.op = new()

    return ap


def _mk_not(node: ast.UnaryOp) -> Callable[[], None]:
    def ap() -> None:
        node.op = ast.UAdd()  # `+X`: với bool/int gần như là chính X

    return ap


def _mk_const(node: ast.Constant, val: str | int) -> Callable[[], None]:
    def ap() -> None:
        node.value = val

    return ap


def _mk_del(body: list[ast.stmt], idx: int) -> Callable[[], None]:
    def ap() -> None:
        del body[idx]
        if not body:  # body rỗng → `ast.unparse` vỡ; chèn `pass` cho hợp lệ cú pháp
            body.append(ast.Pass())

    return ap


def _la_type_checking(test: ast.expr) -> bool:
    """`test` có phải cờ `TYPE_CHECKING` không — cả `TYPE_CHECKING` trần lẫn `typing.TYPE_CHECKING`."""
    return (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING") or (
        isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"
    )


def _co_the_xoa(stmt: ast.stmt) -> bool:
    """Câu lệnh có đáng thử xoá không. BỎ QUA cái xoá đi mà **runtime KHÔNG đổi** — chúng không đời
    nào có test đỏ được (mutant tương đương), chỉ làm loãng danh sách survivor:
      - `import`/`from`, `pass`, `def`/`class` (xoá cả khối lớn → hàng loạt test đỏ vì NameError,
        không định vị được lỗ nào);
      - **chuỗi trần** `Expr(Constant str)` ở BẤT KỲ vị trí — docstring HAY ghi-chú-as-string giữa
        body: Python tính rồi vứt, xoá là no-op;
      - **khối `if TYPE_CHECKING:`** — luôn False lúc chạy nên thân khối không bao giờ thực thi.
    Còn lại — gán, gọi, return, raise, if thường… — mới là chỗ "quên gọi `_bind_tenant`" lớp M7 mà
    toán tử node không chạm tới."""
    if isinstance(
        stmt,
        (ast.Import, ast.ImportFrom, ast.Pass, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef),
    ):
        return False
    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
        return False
    return not (isinstance(stmt, ast.If) and _la_type_checking(stmt.test))


def _tom_tat_stmt(stmt: ast.stmt) -> str:
    """Dòng đầu của câu lệnh (đã unparse), cắt gọn cho phần mô tả in ra."""
    return ast.unparse(stmt).strip().split("\n")[0][:44]


def _points(tree: ast.AST) -> Iterator[tuple[Cand, Callable[[], None]]]:
    """Nguồn DUY NHẤT liệt kê điểm đột biến — yield `(Cand, apply)` theo thứ tự ỔN ĐỊNH; `apply()`
    đổi node IN-PLACE trên CHÍNH `tree` được truyền vào. Cả collect (`_thu_thap`) lẫn apply
    (`_dot_bien`) đều đi qua đây nên bộ đếm `muc_tieu` không thể lệch khi thêm toán tử — trước kia
    hai hàm duyệt riêng, mỗi lần thêm kind là một lần suýt lệch counter."""
    # ── pass 1: điểm toán tử qua ast.walk ──
    for node in ast.walk(tree):
        line = getattr(node, "lineno", 0)
        if isinstance(node, ast.Compare):
            for i, op in enumerate(node.ops):
                t = type(op)
                if t in _CMP_SWAP:
                    yield Cand("cmp", line, f"{t.__name__} -> {_CMP_SWAP[t].__name__}"), _mk_cmp(node, i, _CMP_SWAP[t])
                if t in _CMP_BOUND:
                    yield (
                        Cand("cmpbound", line, f"{t.__name__} -> {_CMP_BOUND[t].__name__}"),
                        _mk_cmp(node, i, _CMP_BOUND[t]),
                    )
        elif isinstance(node, ast.BoolOp):
            moi = "Or" if isinstance(node.op, ast.And) else "And"
            yield Cand("bool", line, f"{type(node.op).__name__} -> {moi}"), _mk_bool(node)
        elif isinstance(node, ast.BinOp) and type(node.op) in _ARITH_SWAP:
            new = _ARITH_SWAP[type(node.op)]
            yield Cand("arith", line, f"{type(node.op).__name__} -> {new.__name__}"), _mk_binop(node, new)
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            yield Cand("not", line, "bỏ `not`"), _mk_not(node)
        elif isinstance(node, ast.Constant):
            v = node.value
            if isinstance(v, bool):
                yield Cand("const", line, f"{v} -> {not v}"), _mk_const(node, not v)
            elif isinstance(v, int):
                # v+1 (cũ) + v-1 + v→0 (nếu v≠0) — nhiều mutant hơn, bắt off-by và hằng-số-sai.
                for nv in (v + 1, v - 1, *((0,) if v != 0 else ())):
                    yield Cand("const", line, f"{v} -> {nv}"), _mk_const(node, nv)
            elif isinstance(v, str):
                lines = v.split("\n")
                for i in _sql_drop_line_indices(v):
                    new_sql = "\n".join(ln for j, ln in enumerate(lines) if j != i)
                    yield Cand("sqlline", line, f"bỏ mệnh đề `{lines[i].strip()[:44]}`"), _mk_const(node, new_sql)
    # ── pass 2: điểm xoá câu lệnh — cần parent body nên tự duyệt (ast.walk không cho parent) ──
    for node in ast.walk(tree):
        for field in ("body", "orelse", "finalbody"):
            body = getattr(node, field, None)
            if not isinstance(body, list):
                continue
            for idx, stmt in enumerate(body):
                if not isinstance(stmt, ast.stmt) or not _co_the_xoa(stmt):
                    continue
                yield Cand("delstmt", getattr(stmt, "lineno", 0), f"xoá `{_tom_tat_stmt(stmt)}`"), _mk_del(body, idx)


def _thu_thap(tree: ast.AST) -> list[Cand]:
    """Liệt kê ứng viên theo ĐÚNG thứ tự `_dot_bien` duyệt lại — wrapper mỏng quanh `_points`."""
    return [c for c, _ in _points(tree)]


def _dot_bien(tree: ast.AST, muc_tieu: int) -> ast.AST:
    """Đi lại đúng thứ tự `_points` và áp đúng ứng viên thứ `muc_tieu` (in-place trên `tree`)."""
    for j, (_c, ap) in enumerate(_points(tree)):
        if j == muc_tieu:
            ap()
            return tree
    return tree


def _chay_suite() -> tuple[bool, str]:
    """Trả `(suite_xanh, tom_tat)`. `-x` dừng ở lỗi đầu — đủ để biết CÓ ai bắt hay không."""
    # Xoá bytecode đã biên dịch TRƯỚC mỗi lần chạy, và cấm ghi lại (`-B`).
    # Vì sao bắt buộc: Python quyết định .pyc còn dùng được bằng (mtime giây, kích thước file). Mutant
    # đổi đúng một ký tự — `1`→`2`, `0`→`1` — giữ NGUYÊN kích thước, và sweep ghi file trong cùng một
    # giây, nên Python nạp lại bytecode CŨ và mutant không hề có hiệu lực. Triệu chứng đúng như đã
    # thấy: cùng một mutant lúc "sống sót" lúc "bị bắt" giữa các lần chạy.
    for pyc in SRC.rglob("__pycache__"):
        for f in pyc.glob("*.pyc"):
            f.unlink(missing_ok=True)
    try:
        p = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "pytest",
                "packages/kb",
                "-x",
                "-q",
                "--no-header",
                "--color=no",
                "-p",
                "no:cacheprovider",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=180,
        )
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT (coi như bị bắt)"
    out = p.stdout
    xanh = p.returncode == 0
    dong = [ln for ln in out.splitlines() if "passed" in ln or "failed" in ln or "error" in ln.lower()]
    return xanh, (dong[-1][:80] if dong else f"rc={p.returncode}")


def main() -> int:
    # Bước 0: khôi phục nếu lần trước bị kill giữa chừng.
    # Phải chạy TRƯỚC mọi phép đo — số đo trên cây còn mutant không dùng được.
    _restore_orig_files()

    if not os.environ.get("STUDIO_DATABASE_URL_ADMIN"):
        print("⚠ Chưa có biến DSN — 31 test DB sẽ skip và kết quả quét vô nghĩa.")
        return 1

    files = sorted(p for p in SRC.glob("*.py") if p.name != "__init__.py")
    song_sot: list[tuple[str, Cand]] = []
    tong = 0
    t0 = time.time()

    for f in files:
        goc = f.read_text()
        orig_path = f.with_suffix(f".py{_ORIG_SUFFIX}")
        tree = ast.parse(goc)
        cands = _thu_thap(tree)

        # Kiểm nền: unparse KHÔNG đột biến phải giữ suite xanh. Nếu không, mọi số dưới là nhiễu.
        orig_path.write_text(goc)
        f.write_text(ast.unparse(ast.parse(goc)))
        nen_xanh, tom = _chay_suite()
        f.write_text(goc)
        orig_path.unlink(missing_ok=True)
        if not nen_xanh:
            print(f"⚠ {f.name}: unparse trần đã làm suite đỏ ({tom}) — bỏ file này, số sẽ không tin được.")
            continue

        print(f"\n── {f.name}  ({len(cands)} ứng viên)")
        for i, c in enumerate(cands):
            tong += 1
            try:
                m = _dot_bien(ast.parse(goc), i)
                orig_path.write_text(goc)
                f.write_text(ast.unparse(m))
                xanh, tom = _chay_suite()
            except SyntaxError, ValueError, RecursionError:  # mutant không unparse/parse được
                continue
            finally:
                f.write_text(goc)
                orig_path.unlink(missing_ok=True)

            if xanh:
                song_sot.append((f.name, c))
                print(f"  SỐNG SÓT  dòng {c.line:<4} {c.kind:<6} {c.mo_ta}")

    print("\n" + "=" * 74)
    print(f"Đã thử {tong} mutant trong {time.time() - t0:.0f}s — {len(song_sot)} sống sót")
    print("=" * 74)
    theo_file: dict[str, list[Cand]] = {}
    for fn, c in song_sot:
        theo_file.setdefault(fn, []).append(c)
    for fn in sorted(theo_file, key=lambda k: -len(theo_file[k])):
        print(f"\n{fn}: {len(theo_file[fn])} sống sót")
        for c in theo_file[fn]:
            print(f"   dòng {c.line:<4} {c.kind:<6} {c.mo_ta}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
