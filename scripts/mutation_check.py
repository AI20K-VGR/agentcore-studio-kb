"""Kiểm test negative có CẮN THẬT hay không, bằng cách đột biến source rồi đếm test đỏ (D9, DE).

    docker compose -f docker-compose.test.yml up -d
    export STUDIO_DATABASE_URL_ADMIN=postgresql://studio_owner:changeme@localhost:5433/studio_test
    export STUDIO_DATABASE_URL=postgresql://studio_app:changeme@localhost:5433/studio_test
    uv run python packages/kb/scripts/mutation_check.py

Vì sao script này tồn tại: DoD `day-09.md:52` đòi *"test negative bắt lỗi thật (không phải test
giả)"*. Câu đó không kiểm được bằng cách chạy suite — suite xanh là điều kiện cần, không phải bằng
chứng. Bằng chứng là: **làm hỏng source rồi xem test có đỏ không**. Một bài test không đỏ dưới bất kỳ
đột biến nào là bài test không khoá gì.

**Đột biến ở `src/`, KHÔNG ở test.** Bẻ input của test (truyền tenant không tồn tại chẳng hạn) chỉ
chứng minh assert cắn khi chính bài test truyền sai. `:52` đòi bắt được **impl hỏng** — đúng khuôn
mentor ghi ở `test_leak.py:46-50`: *"a lazy/broken impl that returns an empty list would false-pass
the exclusion assertion"*. Nên mutant phải nằm ở source.

Script tự trả lại nguyên trạng qua `try/finally`, kể cả khi pytest vỡ hoặc bị Ctrl-C. Kiểm lại bằng
`git status --short` sau khi chạy — phải sạch. Không ghi gì vào `src/` một cách lâu dài, và không
phải feature (`:45` cấm thêm feature): đây là dụng cụ đo test.

Đọc bảng kết quả thế nào: `bắt` là số test đỏ dưới mutant đó. Một mutant mà `bắt == 0` nghĩa là hành
vi đó **không được bài test nào khoá** — đó là phát hiện, không phải điều đáng mừng.
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

_KB = Path(__file__).resolve().parent.parent
_ROOT = _KB.parent.parent
_SRC = _KB / "src" / "studio_kb"
_EVALHUB = _ROOT / "packages" / "evalhub" / "src" / "studio_evalhub"
_ENGINE = _ROOT / "packages" / "engine" / "src" / "studio_engine"


@dataclass(frozen=True)
class Mutant:
    """Một phép làm-hỏng-có-chủ-đích.

    `anchor` phải xuất hiện **đúng một lần** trong file — script khẳng định điều đó và dừng nếu
    không, vì một anchor trùng nghĩa là đang sửa chỗ mình không định sửa, và kết quả đo sẽ vô nghĩa.
    """

    ten: str
    mo_ta: str
    duong_dan: Path
    anchor: str
    thay_bang: str
    ky_vong_bat: tuple[str, ...]
    """Test PHẢI đỏ dưới mutant này. Script so thực tế với danh sách đây và báo lệch — nhờ vậy file
    này là một bài test của chính bộ test, không chỉ là một bảng số in ra."""


MUTANTS = (
    Mutant(
        ten="M1 kb-search-chet",
        mo_ta="StaticKbSearch.search trả [] — impl truy xuất chết (lazy/broken impl)",
        duong_dan=_SRC / "static_search.py",
        anchor="        if top_k <= 0:\n            return []\n",
        thay_bang="        return []  # MUTANT\n        if top_k <= 0:\n            return []\n",
        ky_vong_bat=(
            "test_goi_duoc_bang_dung_4_keyword_arg",
            "test_sc04_cheo_tenant_khong_ro_ri_chunk_cua_tenant_kia",
        ),
    ),
    Mutant(
        ten="M2 reader-nuot-event",
        mo_ta="PgTraceReader.read_run trả [] — reader nuốt hết event",
        duong_dan=_SRC / "trace_reader.py",
        anchor=(
            "        async with self._pool.connection() as conn:\n"
            "            cursor = await conn.execute(_READ_RUN, (run_id, tenant_id))"
        ),
        thay_bang=(
            "        return []  # MUTANT\n"
            "        async with self._pool.connection() as conn:\n"
            "            cursor = await conn.execute(_READ_RUN, (run_id, tenant_id))"
        ),
        ky_vong_bat=("test_inputs_hash_differs_per_node",),
    ),
    Mutant(
        ten="M3 reader-roi-citations",
        mo_ta="PgTraceReader đánh rơi citations (citations=None) — trace còn nhưng nguồn chấm rỗng",
        duong_dan=_SRC / "trace_reader.py",
        anchor="        citations=row[11],",
        thay_bang="        citations=None,  # MUTANT\n",
        ky_vong_bat=(
            "test_citations_are_grounded",
            "test_trace_la_nguon_citation_dung_duoc_cho_bo_cham",
        ),
    ),
    Mutant(
        # M5/M6 là hai cột mà TRƯỚC D9 không một bài nào khoá: đột biến chúng cho 0 test đỏ. Giữ lại
        # trong bộ vì đó là hai cột "im lặng" — sai mà không có triệu chứng nào ngoài con số hiển thị.
        ten="M5 reader-roi-tokens",
        mo_ta="PgTraceReader trả tokens 0/0 — số token mọi node thành 0",
        duong_dan=_SRC / "trace_reader.py",
        anchor="        tokens=Tokens(**row[9]),",
        thay_bang="        tokens=Tokens(prompt=0, completion=0),  # MUTANT\n",
        ky_vong_bat=("test_db_doc_lai_nguyen_ven_tung_truong",),
    ),
    Mutant(
        ten="M6 reader-roi-cost",
        mo_ta="PgTraceReader trả cost=0.0 — contract đòi cost khớp trên cả 3 mặt hiển thị",
        duong_dan=_SRC / "trace_reader.py",
        anchor="        cost=float(row[10]),",
        thay_bang="        cost=0.0,  # MUTANT\n",
        ky_vong_bat=("test_db_doc_lai_nguyen_ven_tung_truong",),
    ),
    Mutant(
        # M7/M8 đánh thẳng vào INV-1: lấy tenant từ recipe (client tự khai) thay vì từ phiên. TRƯỚC
        # khi có `test_inv1_recipe_tu_khai_tenant_khac_thi_phien_thang`, cả hai cho 0 test đỏ — tức
        # bất biến trung tâm của D8 không được bài nào trong kb khoá, dù cả file đã truyền
        # `session_context`. Truyền được API mới không đồng nghĩa với chứng minh được bất biến.
        ten="M7 tenant-tu-recipe-kb",
        mo_ta="interpreter tiêm recipe.tenant_id vào kb-retrieve thay vì session (INV-1 vỡ ở tầng dữ liệu)",
        duong_dan=_ENGINE / "interpreter.py",
        anchor='"tenant_id": session_context.tenant_id',
        thay_bang='"tenant_id": recipe.tenant_id',
        ky_vong_bat=("test_inv1_recipe_tu_khai_tenant_khac_thi_phien_thang",),
    ),
    Mutant(
        ten="M8 tenant-tu-recipe-trace",
        mo_ta="TraceEvent mang recipe.tenant_id thay vì session (INV-1 vỡ ở tầng quan trắc)",
        duong_dan=_ENGINE / "interpreter.py",
        anchor="tenant_id=session_context.tenant_id,",
        thay_bang="tenant_id=recipe.tenant_id,  # MUTANT",
        ky_vong_bat=("test_inv1_recipe_tu_khai_tenant_khac_thi_phien_thang",),
    ),
    Mutant(
        # Mutant DUY NHẤT nằm ngoài kb. Có mặt vì `:53` (*"một nguồn số"*) là hợp đồng GIỮA hai
        # quadrant: hỏng ở phía bộ chấm thì con số citation-accuracy sai, mà không bài nào trong kb
        # đỏ — trừ bài khoá đúng cái bắt tay đó. Đây là phép đo cho câu hỏi Q-B trong plan D9.
        ten="M4 bo-cham-siet-node",
        mo_ta="citations_from_trace siết theo node_type kb-retrieve (node này citations=None)",
        duong_dan=_EVALHUB / "harness.py",
        anchor="    for event in events:\n        if event.citations is not None:",
        thay_bang=(
            "    for event in events:\n"
            "        if event.node_type is NodeType.KB_RETRIEVE and event.citations is not None:"
        ),
        ky_vong_bat=("test_trace_la_nguon_citation_dung_duoc_cho_bo_cham",),
    ),
)


_MA_MAU = re.compile(r"\x1b\[[0-9;]*m")


def _bo_mau(text: str) -> str:
    """Gỡ mã màu ANSI. Xem chú thích trong `_chay_suite` về vì sao đây không phải chuyện thẩm mỹ."""
    return _MA_MAU.sub("", text)


def _chay_suite() -> tuple[int, int, set[str]]:
    """Chạy suite kb, trả `(so_pass, so_fail, ten_cac_test_do)`.

    Đọc tên test đỏ từ dòng `FAILED ...::ten_test` thay vì chỉ lấy số đếm: số đếm nói "có gì đó
    đổi", tên nói "đúng bài cần đỏ đã đỏ". Chỉ so số đếm thì một mutant làm đỏ 2 bài KHÁC vẫn ra
    cùng con số và trông như đạt.
    """
    proc = subprocess.run(
        # `--color=no`: pytest vẫn phun mã màu ANSI kể cả khi stdout là pipe, và `\x1b[31m` đứng
        # trước `FAILED` làm regex neo đầu dòng không khớp — lúc đó script báo "không cắn" cho MỌI
        # mutant trong khi số đếm vẫn đúng. Đã dính đúng bẫy này một lần; `_bo_mau` bên dưới là lớp
        # chặn thứ hai phòng khi cờ này bị bỏ qua.
        [sys.executable, "-m", "pytest", "packages/kb", "-q", "--no-header", "--color=no", "-p", "no:cacheprovider"],
        cwd=_ROOT,
        capture_output=True,
        text=True,
    )
    out = _bo_mau(proc.stdout)
    do = set(re.findall(r"^FAILED \S+::(\w+)", out, re.MULTILINE))
    so_pass = int(m.group(1)) if (m := re.search(r"(\d+) passed", out)) else 0
    so_fail = int(m.group(1)) if (m := re.search(r"(\d+) failed", out)) else 0
    return so_pass, so_fail, do


def main() -> int:
    print("=" * 78)
    print("Nền: suite sạch, không mutant")
    goc_pass, goc_fail, goc_do = _chay_suite()
    print(f"  {goc_pass} passed, {goc_fail} failed")
    if goc_fail:
        print(f"  ⚠ suite đã đỏ TRƯỚC khi đột biến ({sorted(goc_do)}) — sửa cho xanh rồi hãy đo.")
        return 1
    if goc_pass == 0:
        print("  ⚠ 0 test chạy. Postgres chưa bật hoặc thiếu biến DSN — xem docstring đầu file.")
        return 1

    lech: list[str] = []
    print("=" * 78)
    for m in MUTANTS:
        goc_text = m.duong_dan.read_text()
        if goc_text.count(m.anchor) != 1:
            print(f"  ⚠ {m.ten}: anchor xuất hiện {goc_text.count(m.anchor)} lần (phải đúng 1) — bỏ qua.")
            lech.append(f"{m.ten}: anchor không khớp, source đã đổi kể từ D9")
            continue
        try:
            m.duong_dan.write_text(goc_text.replace(m.anchor, m.thay_bang, 1))
            _p, f, do = _chay_suite()
        finally:
            m.duong_dan.write_text(goc_text)  # trả nguyên trạng, kể cả khi pytest vỡ

        thieu = set(m.ky_vong_bat) - do
        print(f"{m.ten}  — {m.mo_ta}")
        print(f"  bắt: {f} test đỏ")
        for ten in sorted(do):
            danh_dau = "←" if ten in m.ky_vong_bat else " "
            print(f"    {danh_dau} {ten}")
        if thieu:
            print(f"  ✗ KHÔNG đỏ dù phải đỏ: {sorted(thieu)}")
            lech.append(f"{m.ten}: {sorted(thieu)} không cắn")
        if f == 0:
            lech.append(f"{m.ten}: không test nào đỏ — hành vi này chưa được khoá")
        print()

    print("=" * 78)
    if lech:
        print("KẾT: có lệch — test không cắn đúng như khai:")
        for d in lech:
            print(f"  - {d}")
        return 1
    print(f"KẾT: {len(MUTANTS)}/{len(MUTANTS)} mutant đều bị bắt đúng bài đã khai.")
    print("Nhớ kiểm `git status --short` ở kb và evalhub — phải sạch.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
