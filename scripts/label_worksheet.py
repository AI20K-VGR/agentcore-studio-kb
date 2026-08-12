"""Phiếu chấm nhãn tay (D18, DE) — đặt văn bản chunk nguồn trước mặt để adjudicate subset golden-30.

    uv run --python 3.14 --package agentcore-studio-kb python packages/kb/scripts/label_worksheet.py

CHỈ IN, không ghi gì. Nhãn tay THẬT do DE gõ tay vào `src/studio_kb/golden_set.py` sau khi ĐỌC chunk
— script này không quyết thay người, chỉ gom sẵn thứ cần đọc để quyết (`format.md §10`: tay, không
nhờ model). In cho MỖI case có `manual_label`:
  - case `pass`: chunk được trích + cụm `expected` → người xác nhận grounded · duy nhất · trong scope.
  - case `refuse`: lý do fence (T1/T6) + một chunk LẼ RA bị rò → người xác nhận đúng là ngoài quyền.

Cùng họ với `annotate_golden.py` (đọc-để-chấm) nhưng ngược chiều: annotate suy nhãn `expected` từ
retrieval; đây bày nguồn cho người tự chấm `manual_label`. Read-only nên không vào CI, không test.
"""

from __future__ import annotations

from studio_kb.doc_factory import load_callisto, resolve_tenant_id
from studio_kb.golden_set import GOLDEN_CASES


def main() -> None:
    by_id = {c.chunk_id: c for c in load_callisto()}
    labeled = [c for c in GOLDEN_CASES if c.manual_label is not None]

    for c in labeled:
        print("=" * 92)
        print(f"{c.case_id}  ·  DRAFT = {c.manual_label!r}")
        print(f"  Câu hỏi   : {c.query}")
        print(f"  Người hỏi : tenant={c.tenant}  roles={list(c.section_roles)}")
        print(f"  Đáp án ở  : tenant={c.expected_tenant}  role={c.expected_section_role}")
        if not c.is_refusal:
            print(f"  Cụm expected (phải grounded & DUY NHẤT): {c.expected!r}")
            print("  --- CHUNK ĐƯỢC TRÍCH (đọc để xác nhận đáp án đúng & nằm trong scope người hỏi) ---")
            for cid in c.expected_citation:
                ch = by_id.get(cid)
                if ch is None:
                    print(f"    [{cid}] KHÔNG có trong corpus!")
                    continue
                print(f"    [{cid}]  (tenant={ch.tenant_id}, role={ch.section_role})")
                for line in ch.text.splitlines():
                    print(f"        {line}")
            print("  → HỎI: agent CÓ nên trả lời không? cụm expected đúng & duy nhất? → pass/refuse?")
        else:
            want_t = resolve_tenant_id(c.expected_tenant) if c.expected_tenant else None
            print("  --- CASE BẪY HÀNG RÀO (không có citation) ---")
            if c.expected_tenant != c.tenant:
                print(f"    • T1: hỏi dữ liệu tenant '{c.expected_tenant}' nhưng người hỏi ở '{c.tenant}'")
            if c.expected_section_role not in c.section_roles:
                print(
                    f"    • T6: đáp án ở vai '{c.expected_section_role}' mà người hỏi chỉ giữ {list(c.section_roles)}"
                )
            leaks = [
                ch
                for ch in by_id.values()
                if (want_t is None or ch.tenant_id == want_t) and ch.section_role == c.expected_section_role
            ][:1]
            if leaks:
                ch = leaks[0]
                head = ch.text.splitlines()[0] if ch.text else ""
                print(f"    (dữ liệu agent PHẢI CHẶN — ví dụ [{ch.chunk_id}] role={ch.section_role}): {head} ...")
            print("  → HỎI: có đúng người hỏi KHÔNG được phép thấy đáp án này? → refuse?")
        print()

    print("=" * 92)
    passes = sum(c.manual_label == "pass" for c in labeled)
    refuses = sum(c.manual_label == "refuse" for c in labeled)
    print(f"Tổng: {len(labeled)} case cần nhãn tay  |  pass={passes}  refuse={refuses}")


if __name__ == "__main__":
    main()
