"""Quét toàn bộ `packages/kb/src` bằng đột biến AST — tìm chỗ không bài test nào canh (D9, DE).

    docker compose -f docker-compose.test.yml up -d
    export STUDIO_DATABASE_URL_ADMIN=postgresql://studio_owner:changeme@localhost:5433/studio_test
    export STUDIO_DATABASE_URL=postgresql://studio_app:changeme@localhost:5433/studio_test
    uv run python packages/kb/scripts/mutation_sweep.py     # ~60s, 93 mutant

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

**Giới hạn phải biết:** chỉ 4 loại toán tử (so sánh, and/or, `not`, hằng bool/int). KHÔNG phủ: xoá
câu lệnh, đổi giá trị trả về, hằng chuỗi, biên của lát cắt, nhánh bắt ngoại lệ. "0 sống sót" nghĩa là
sạch **theo bốn loại này**, không phải sạch tuyệt đối.
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

_KB = Path(__file__).resolve().parent.parent
ROOT = _KB.parent.parent
SRC = _KB / "src" / "studio_kb"

_CMP_SWAP = {
    ast.Eq: ast.NotEq, ast.NotEq: ast.Eq,
    ast.Lt: ast.GtE, ast.GtE: ast.Lt,
    ast.Gt: ast.LtE, ast.LtE: ast.Gt,
    ast.In: ast.NotIn, ast.NotIn: ast.In,
    ast.Is: ast.IsNot, ast.IsNot: ast.Is,
}


@dataclass
class Cand:
    kind: str
    line: int
    mo_ta: str


def _thu_thap(tree: ast.AST) -> list[Cand]:
    """Liệt kê ứng viên theo ĐÚNG thứ tự mà `_dot_bien` sẽ duyệt lại."""
    out: list[Cand] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            for op in node.ops:
                if type(op) in _CMP_SWAP:
                    out.append(Cand("cmp", getattr(node, "lineno", 0),
                                    f"{type(op).__name__} -> {_CMP_SWAP[type(op)].__name__}"))
        elif isinstance(node, ast.BoolOp):
            out.append(Cand("bool", getattr(node, "lineno", 0),
                            f"{type(node.op).__name__} -> {'Or' if isinstance(node.op, ast.And) else 'And'}"))
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            out.append(Cand("not", getattr(node, "lineno", 0), "bỏ `not`"))
        elif isinstance(node, ast.Constant):
            v = node.value
            if isinstance(v, bool):
                out.append(Cand("const", getattr(node, "lineno", 0), f"{v} -> {not v}"))
            elif isinstance(v, int) and not isinstance(v, bool):
                out.append(Cand("const", getattr(node, "lineno", 0), f"{v} -> {v + 1}"))
    return out


def _dot_bien(tree: ast.AST, muc_tieu: int) -> ast.AST:
    """Đi lại đúng thứ tự `ast.walk` và đổi ứng viên thứ `muc_tieu`."""
    dem = -1
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            for i, op in enumerate(node.ops):
                if type(op) in _CMP_SWAP:
                    dem += 1
                    if dem == muc_tieu:
                        node.ops[i] = _CMP_SWAP[type(op)]()
                        return tree
        elif isinstance(node, ast.BoolOp):
            dem += 1
            if dem == muc_tieu:
                node.op = ast.Or() if isinstance(node.op, ast.And) else ast.And()
                return tree
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            dem += 1
            if dem == muc_tieu:
                # thay `not X` bằng `X` — NodeTransformer không tiện ở đây nên đánh dấu
                node.op = ast.UAdd()  # `+X` : với bool/int gần như là chính X
                return tree
        elif isinstance(node, ast.Constant):
            v = node.value
            if isinstance(v, bool):
                dem += 1
                if dem == muc_tieu:
                    node.value = not v
                    return tree
            elif isinstance(v, int):
                dem += 1
                if dem == muc_tieu:
                    node.value = v + 1
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
            [sys.executable, "-B", "-m", "pytest", "packages/kb", "-x", "-q", "--no-header",
             "--color=no", "-p", "no:cacheprovider"],
            cwd=ROOT, capture_output=True, text=True, timeout=180,
        )
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT (coi như bị bắt)"
    out = p.stdout
    xanh = p.returncode == 0
    dong = [ln for ln in out.splitlines() if "passed" in ln or "failed" in ln or "error" in ln.lower()]
    return xanh, (dong[-1][:80] if dong else f"rc={p.returncode}")


def main() -> int:
    if not os.environ.get("STUDIO_DATABASE_URL_ADMIN"):
        print("⚠ Chưa có biến DSN — 31 test DB sẽ skip và kết quả quét vô nghĩa.")
        return 1

    files = sorted(p for p in SRC.glob("*.py") if p.name != "__init__.py")
    song_sot: list[tuple[str, Cand]] = []
    tong = 0
    t0 = time.time()

    for f in files:
        goc = f.read_text()
        tree = ast.parse(goc)
        cands = _thu_thap(tree)

        # Kiểm nền: unparse KHÔNG đột biến phải giữ suite xanh. Nếu không, mọi số dưới là nhiễu.
        f.write_text(ast.unparse(ast.parse(goc)))
        nen_xanh, tom = _chay_suite()
        f.write_text(goc)
        if not nen_xanh:
            print(f"⚠ {f.name}: unparse trần đã làm suite đỏ ({tom}) — bỏ file này, số sẽ không tin được.")
            continue

        print(f"\n── {f.name}  ({len(cands)} ứng viên)")
        for i, c in enumerate(cands):
            tong += 1
            try:
                m = _dot_bien(ast.parse(goc), i)
                f.write_text(ast.unparse(m))
                xanh, tom = _chay_suite()
            except (SyntaxError, ValueError, RecursionError):  # mutant không unparse/parse được
                continue
            finally:
                f.write_text(goc)

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
