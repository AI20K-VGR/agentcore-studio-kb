"""Golden-set Callisto **2.0** — 30 case có nhãn trên corpus 2.0 (`docs/callisto-2.0/`, 80 doc / 800
chunk). Song song bộ 1.0 (`golden_set`), chưa thay thế — theo kế hoạch `plans/callisto-2.0-cutover.md`.

**Nguồn sự thật là module này (typed), KHÔNG phải yaml.** `golden/callisto-2.0-golden-30-v1.yaml` sinh
ra qua `scripts/emit_golden_set_v2.py`, byte-identical với `render_yaml()`. `GoldenCase`/renderer dùng
chung `golden_set_core` (KHÔNG phụ thuộc `golden_set` 1.0 — để 1.0 xoá được mà 2.0 vẫn đứng).

## Nhãn build thế nào (kỷ luật y hệt 1.0, đối chiếu corpus 2.0)

Query là **authored**; NHÃN (`expected_citation`, `expected`, `expected_tenant/section_role`) là
**derived** — trace từ retrieval thật (`scripts/annotate_golden_v2.py`, `StaticKbSearch` tiêm
`load_corpus_v2`) + **máy-kiểm** grounded & DUY NHẤT bằng `_contains_phrase` THẬT của harness.
`tests/test_golden_set_v2.py` canh 5 trục (grounded · duy-nhất · retrievable · teeth≥2 · fence) +
byte-identical + tỉ lệ 22/8 + phủ biên + nhãn tay. Rank-verify (search xếp expected top-k **ngữ
nghĩa**) **hoãn** sang parity gate (phụ thuộc embedding thật — `plans/callisto-2.0-cutover.md` §2).

## Khác 1.0 chỗ nào (do corpus 2.0)

- role suy từ tiền tố tên file: `remote-work`/`leave`/`benefits` giờ là **hr** (1.0 để `public`);
  `oncall`/`incident` là **engineering**; `expense`/`procurement` là **finance**.
- `chunk_id = "{tenant}-{role}-{name}#c{n}"` (vd `ankor-hr-leave#c1`), citation = tên file.
- Cặp chéo-tenant leak-mimic bám fact **khác số** giữa 2 tenant (phép 12/15, Tết 7/9, bảo hiểm
  50/100 triệu, SLA 15'/10', báo trước 3/5 ngày, mua sắm 5/3 triệu, đánh giá 2 lần/hằng quý).

## Subset nhãn tay (12 = 8 `pass` + 4 `refuse`)

Chọn nghiêng case khó (cặp leak-mimic + fence-trap T1/T6), trải 2 tenant — để agreement PHÂN BIỆT
judge thật với judge hằng "luôn PASS". `refuse` ≥3 (§11) giữ sức phân biệt; `pass` dư vì các cặp
khác-số là answer-key đắt giá nhất. `test_golden_set_v2.py` canh sàn, đủ hai lớp, khớp fence-semantics.

## Corpus 2.0 ĐÓNG BĂNG kể từ bộ nhãn này

`chunk_id = "{doc_id}#c{n}"`, `n` đếm theo VỊ TRÍ heading `##` (I4). Chèn/xoá một `##` trong bất kỳ
doc 2.0 nào → **đánh số lại** mọi citation phía dưới trong doc đó → nhãn trỏ sai chunk mà không id nào
chết. Sửa corpus 2.0 phải re-trace nhãn (`annotate_golden_v2.py`) + re-emit, đừng sửa lẻ.
"""

from __future__ import annotations

from studio_kb.golden_set_core import GoldenCase, render_cases

__all__ = ["GOLDEN_SET_REF_V2", "GOLDEN_CASES_V2", "EDGE_AXES_V2", "render_yaml"]

GOLDEN_SET_REF_V2 = "callisto-2.0-golden-30-v1"


# ── Nguồn sự thật: 22 dương + 8 âm (T1 hai chiều · T6 hai tenant), corpus 2.0 ─────────────────────
GOLDEN_CASES_V2: tuple[GoldenCase, ...] = (
    GoldenCase(
        case_id="HB2-01",
        query="Nhân viên chính thức được bao nhiêu ngày phép năm?",
        tenant="ankor",
        section_roles=("hr",),
        expected_tenant="ankor",
        expected_section_role="hr",
        expected="12 ngày phép có lương",
        expected_citation=("ankor-hr-leave#c1",),
        note="cặp HB2-02 (số ngày phép 12 vs 15)",
        manual_label="pass",
    ),
    GoldenCase(
        case_id="HB2-02",
        query="Nhân viên chính thức được bao nhiêu ngày phép năm?",
        tenant="borea",
        section_roles=("hr",),
        expected_tenant="borea",
        expected_section_role="hr",
        expected="15 ngày phép có lương",
        expected_citation=("borea-hr-leave#c1",),
        note="cặp HB2-01 khác số",
    ),
    GoldenCase(
        case_id="HB2-03",
        query="Tết Nguyên Đán nhân viên được nghỉ mấy ngày?",
        tenant="ankor",
        section_roles=("public",),
        expected_tenant="ankor",
        expected_section_role="public",
        expected="nghỉ 7 ngày liên tục",
        expected_citation=("ankor-public-holidays#c1",),
        note="cặp HB2-04 (Tết 7 vs 9 ngày)",
        manual_label="pass",
    ),
    GoldenCase(
        case_id="HB2-04",
        query="Tết Nguyên Đán nhân viên được nghỉ mấy ngày?",
        tenant="borea",
        section_roles=("public",),
        expected_tenant="borea",
        expected_section_role="public",
        expected="nghỉ 9 ngày liên tục",
        expected_citation=("borea-public-holidays#c1",),
        note="cặp HB2-03 khác số",
    ),
    GoldenCase(
        case_id="HB2-05",
        query="Bảo hiểm sức khoẻ có hạn mức nội trú bao nhiêu?",
        tenant="ankor",
        section_roles=("hr",),
        expected_tenant="ankor",
        expected_section_role="hr",
        expected="50.000.000 VNĐ/năm cho nội trú",
        expected_citation=("ankor-hr-benefits#c1",),
        note="cặp HB2-06 (nội trú 50 vs 100 triệu)",
        manual_label="pass",
    ),
    GoldenCase(
        case_id="HB2-06",
        query="Bảo hiểm sức khoẻ có hạn mức nội trú bao nhiêu?",
        tenant="borea",
        section_roles=("hr",),
        expected_tenant="borea",
        expected_section_role="hr",
        expected="100.000.000 VNĐ/năm nội trú",
        expected_citation=("borea-hr-benefits#c1",),
        note="cặp HB2-05 khác số",
        manual_label="pass",
    ),
    GoldenCase(
        case_id="HB2-07",
        query="Sự cố P1 cần bắt đầu xử lý trong bao lâu?",
        tenant="ankor",
        section_roles=("engineering",),
        expected_tenant="ankor",
        expected_section_role="engineering",
        expected="bắt đầu xử lý trong 15 phút",
        expected_citation=("ankor-engineering-oncall#c4",),
        note="cặp HB2-08 (SLA P1); đáp án ở #c4 (SLA), không phải #c1",
    ),
    GoldenCase(
        case_id="HB2-08",
        query="Sự cố P1 cần bắt đầu xử lý trong bao lâu?",
        tenant="borea",
        section_roles=("engineering",),
        expected_tenant="borea",
        expected_section_role="engineering",
        expected="engage trong 10 phút",
        expected_citation=("borea-engineering-oncall#c4",),
        note="cặp HB2-07 khác số; đáp án ở #c4",
        manual_label="pass",
    ),
    GoldenCase(
        case_id="HB2-09",
        query="Đơn xin nghỉ phép phải nộp trước bao lâu?",
        tenant="ankor",
        section_roles=("hr",),
        expected_tenant="ankor",
        expected_section_role="hr",
        expected="trước ít nhất 3 ngày làm việc",
        expected_citation=("ankor-hr-leave#c4",),
        note="cặp HB2-10 (báo trước 3 vs 5 ngày); đáp án ở #c4",
        manual_label="pass",
    ),
    GoldenCase(
        case_id="HB2-10",
        query="Đơn xin nghỉ phép phải nộp trước bao lâu?",
        tenant="borea",
        section_roles=("hr",),
        expected_tenant="borea",
        expected_section_role="hr",
        expected="nộp trước 5 ngày làm việc",
        expected_citation=("borea-hr-leave#c4",),
        note="cặp HB2-09 khác số; đáp án ở #c4",
    ),
    GoldenCase(
        case_id="HB2-11",
        query="Quy trình mua sắm áp dụng cho giao dịch từ bao nhiêu?",
        tenant="ankor",
        section_roles=("finance",),
        expected_tenant="ankor",
        expected_section_role="finance",
        expected="từ 5.000.000 VNĐ trở lên",
        expected_citation=("ankor-finance-procurement#c1",),
        note="cặp HB2-12 (ngưỡng 5 vs 3 triệu)",
    ),
    GoldenCase(
        case_id="HB2-12",
        query="Quy trình mua sắm áp dụng cho giao dịch từ bao nhiêu?",
        tenant="borea",
        section_roles=("finance",),
        expected_tenant="borea",
        expected_section_role="finance",
        expected="từ 3.000.000 VNĐ trở lên",
        expected_citation=("borea-finance-procurement#c1",),
        note="cặp HB2-11 khác số",
        manual_label="pass",
    ),
    GoldenCase(
        case_id="HB2-13",
        query="Chi phí ăn uống công tác nội thành được hoàn ứng tối đa bao nhiêu?",
        tenant="ankor",
        section_roles=("finance",),
        expected_tenant="ankor",
        expected_section_role="finance",
        expected="200.000 VNĐ/bữa nội thành",
        expected_citation=("ankor-finance-reimbursement#c2",),
        note="finance ankor; đáp án ở #c2 (hạn mức)",
    ),
    GoldenCase(
        case_id="HB2-14",
        query="Hoá đơn được xuất trong bao nhiêu ngày làm việc?",
        tenant="ankor",
        section_roles=("finance",),
        expected_tenant="ankor",
        expected_section_role="finance",
        expected="xuất trong 5 ngày làm việc",
        expected_citation=("ankor-finance-invoicing#c2",),
        note="finance ankor; đáp án ở #c2 (thời điểm xuất)",
    ),
    GoldenCase(
        case_id="HB2-15",
        query="Đánh giá hiệu suất diễn ra mấy lần một năm?",
        tenant="ankor",
        section_roles=("hr",),
        expected_tenant="ankor",
        expected_section_role="hr",
        expected="hiệu suất 2 lần/năm",
        expected_citation=("ankor-hr-performance#c1",),
        note="cặp HB2-16 (2 lần/năm vs hằng quý)",
    ),
    GoldenCase(
        case_id="HB2-16",
        query="Đánh giá hiệu suất diễn ra mấy lần một năm?",
        tenant="borea",
        section_roles=("hr",),
        expected_tenant="borea",
        expected_section_role="hr",
        expected="đánh giá hiệu suất hằng quý",
        expected_citation=("borea-hr-performance#c1",),
        note="cặp HB2-15 khác chu kỳ",
        manual_label="pass",
    ),
    GoldenCase(
        case_id="HB2-17",
        query="Tin tuyển dụng phải đăng tối thiểu bao nhiêu ngày?",
        tenant="ankor",
        section_roles=("hr",),
        expected_tenant="ankor",
        expected_section_role="hr",
        expected="tối thiểu 14 ngày",
        expected_citation=("ankor-hr-recruitment#c2",),
        note="hr ankor; đáp án ở #c2 (đăng tuyển)",
    ),
    GoldenCase(
        case_id="HB2-18",
        query="Phụ cấp trực on-call ngày thường là bao nhiêu một tuần?",
        tenant="ankor",
        section_roles=("engineering",),
        expected_tenant="ankor",
        expected_section_role="engineering",
        expected="1.500.000 VNĐ/tuần trực ngày thường",
        expected_citation=("ankor-engineering-oncall#c3",),
        note="engineering ankor; đáp án ở #c3 (phụ cấp)",
    ),
    GoldenCase(
        case_id="HB2-19",
        query="Lương được trả vào ngày mấy hằng tháng?",
        tenant="ankor",
        section_roles=("hr",),
        expected_tenant="ankor",
        expected_section_role="hr",
        expected="trả vào ngày 5 hằng tháng",
        expected_citation=("ankor-hr-payroll#c2",),
        note="hr ankor; đáp án ở #c2 (ngày trả lương)",
    ),
    GoldenCase(
        case_id="HB2-20",
        query="Team Lead được phê duyệt chi tối đa bao nhiêu một giao dịch?",
        tenant="ankor",
        section_roles=("finance",),
        expected_tenant="ankor",
        expected_section_role="finance",
        expected="dưới 10.000.000 VNĐ/giao dịch",
        expected_citation=("ankor-finance-approval-limits#c2",),
        note="finance ankor; đáp án ở #c2 (cấp Team Lead)",
    ),
    GoldenCase(
        case_id="HB2-21",
        query="Ngân sách đào tạo mỗi nhân viên một năm là bao nhiêu?",
        tenant="ankor",
        section_roles=("hr",),
        expected_tenant="ankor",
        expected_section_role="hr",
        expected="10.000.000 VNĐ/năm cho đào tạo",
        expected_citation=("ankor-hr-training#c1",),
        note="hr ankor",
    ),
    GoldenCase(
        case_id="HB2-22",
        query="Lễ Quốc khánh nhân viên được nghỉ mấy ngày?",
        tenant="borea",
        section_roles=("public",),
        expected_tenant="borea",
        expected_section_role="public",
        expected="3 ngày (1–3/9)",
        expected_citation=("borea-public-holidays#c2",),
        note="public borea",
    ),
    # ── 8 case âm (fence) ────────────────────────────────────────────────────────────────────────
    GoldenCase(
        case_id="HB2-23",
        query="Ngân sách đào tạo của Borea là bao nhiêu?",
        tenant="ankor",
        section_roles=("hr",),
        expected_tenant="borea",
        expected_section_role="hr",
        expected="refusal",
        expected_citation=(),
        note="T1 chéo tenant ankor→borea",
        manual_label="refuse",
    ),
    GoldenCase(
        case_id="HB2-24",
        query="Bảo hiểm sức khoẻ có hạn mức nội trú bao nhiêu?",
        tenant="ankor",
        section_roles=("engineering",),
        expected_tenant="ankor",
        expected_section_role="hr",
        expected="refusal",
        expected_citation=(),
        note="T6 chéo vai (engineering hỏi hr)",
        manual_label="refuse",
    ),
    GoldenCase(
        case_id="HB2-25",
        query="Sự cố P1 của Borea cần xử lý trong bao lâu?",
        tenant="ankor",
        section_roles=("engineering",),
        expected_tenant="borea",
        expected_section_role="engineering",
        expected="refusal",
        expected_citation=(),
        note="T1 chéo tenant ankor→borea (engineering)",
    ),
    GoldenCase(
        case_id="HB2-26",
        query="Cơ cấu lương gồm những phần nào?",
        tenant="ankor",
        section_roles=("public",),
        expected_tenant="ankor",
        expected_section_role="hr",
        expected="refusal",
        expected_citation=(),
        note="T6 chéo vai (public hỏi hr=lương)",
        manual_label="refuse",
    ),
    GoldenCase(
        case_id="HB2-27",
        query="Team Lead được phê duyệt chi tối đa bao nhiêu?",
        tenant="ankor",
        section_roles=("public",),
        expected_tenant="ankor",
        expected_section_role="finance",
        expected="refusal",
        expected_citation=(),
        note="T6 chéo vai (public hỏi finance)",
    ),
    GoldenCase(
        case_id="HB2-28",
        query="Quy trình mua sắm của Ankor áp dụng cho giao dịch từ bao nhiêu?",
        tenant="borea",
        section_roles=("finance",),
        expected_tenant="ankor",
        expected_section_role="finance",
        expected="refusal",
        expected_citation=(),
        note="T1 ngược chiều borea→ankor",
    ),
    GoldenCase(
        case_id="HB2-29",
        query="Nhân viên Ankor được bao nhiêu ngày phép năm?",
        tenant="borea",
        section_roles=("hr",),
        expected_tenant="ankor",
        expected_section_role="hr",
        expected="refusal",
        expected_citation=(),
        note="T1 ngược chiều borea→ankor",
    ),
    GoldenCase(
        case_id="HB2-30",
        query="Cơ cấu lương của công ty gồm mấy phần?",
        tenant="borea",
        section_roles=("public",),
        expected_tenant="borea",
        expected_section_role="hr",
        expected="refusal",
        expected_citation=(),
        note="T6 chéo vai phía borea (public hỏi lương=hr)",
        manual_label="refuse",
    ),
)


# ── Phủ biên tường minh — mỗi trục → case phủ nó; guard ở test_golden_set_v2.py ───────────────────
EDGE_AXES_V2: dict[str, tuple[str, ...]] = {
    "cross_tenant_pair": (
        "HB2-01",
        "HB2-02",
        "HB2-03",
        "HB2-04",
        "HB2-05",
        "HB2-06",
        "HB2-07",
        "HB2-08",
        "HB2-09",
        "HB2-10",
        "HB2-11",
        "HB2-12",
        "HB2-15",
        "HB2-16",
    ),
    "t1_ankor_to_borea": ("HB2-23", "HB2-25"),
    "t1_borea_to_ankor": ("HB2-28", "HB2-29"),
    "t6_role_ankor": ("HB2-24", "HB2-26", "HB2-27"),
    "t6_role_borea": ("HB2-30",),
    # Đáp án KHÔNG ở chunk #c1 → chống bug "luôn trả #c1" ẩn dưới top-1.
    "answer_not_c1": (
        "HB2-07",
        "HB2-08",
        "HB2-09",
        "HB2-10",
        "HB2-13",
        "HB2-14",
        "HB2-17",
        "HB2-18",
        "HB2-19",
        "HB2-20",
    ),
}


_HEADER: tuple[str, ...] = (
    "# Golden-set Callisto 2.0 — 30 case có nhãn trên corpus 2.0 (docs/callisto-2.0/, 80 doc / 800 chunk).",
    "#",
    "# Bút DE (Nguyễn Đông Anh). Song song bộ 1.0 (callisto-golden-30-v1) — plans/callisto-2.0-cutover.md.",
    "# Nhãn TRÍCH từ retrieval thật qua scripts/annotate_golden_v2.py — KHÔNG gõ tay. Đã máy-kiểm:",
    "#   (1) mọi expected_citation truy-xuất-được trong scope; (2) expected GROUNDED trong chunk trích +",
    "#   DUY NHẤT trong (tenant, roles) theo đúng _contains_phrase của harness; (3) case âm fence chặn.",
    "# Rank-verify (search xếp expected top-k ngữ nghĩa) HOÃN sang parity gate (phụ thuộc embedding thật).",
    "#",
    "# Cặp chéo-tenant khác-số (leak-mimic): HB2-01/02·03/04·05/06·07/08·09/10·11/12·15/16.",
    "# Gồm 22 dương + 8 âm. Phủ 4 vai × 2 tenant; T1 cả hai chiều; T6 cả ankor lẫn borea.",
)


def render_yaml() -> str:
    """Render `GOLDEN_CASES_V2` → text yaml deterministic (nguồn cho `callisto-2.0-golden-30-v1.yaml`).

    Uỷ quyền `golden_set_core.render_cases` — cùng generator, cùng shape byte với bộ 1.0.
    """
    return render_cases(_HEADER, GOLDEN_SET_REF_V2, GOLDEN_CASES_V2)
