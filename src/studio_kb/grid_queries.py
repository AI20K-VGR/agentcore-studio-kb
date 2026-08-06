"""Golden query + expected chunks cho grid `chunking×embedding` (D14, DE) — issue #95, tiêu thụ #96.

**Nguồn sự thật là module này (typed), KHÔNG phải file yaml.** `golden/callisto-grid-queries-v0.yaml`
là artifact **sinh ra** (`scripts/emit_grid_queries.py`), byte-identical với `render_yaml()` — cùng kỷ
luật "recorded" của `embeddings.py`. Lý do không để yaml làm nguồn: kb cố ý **KHÔNG kéo `pyyaml`**
(`doc_factory.parse_front_matter` docstring), nên không có đường đọc-lại yaml trong test; nguồn typed +
generator cho phép `tests/test_grid_inputs.py` canh drift mà không thêm dependency.

## Vì sao bộ này TÁCH khỏi smoke-5/10 và golden-30 (D16)

Đây **không** phải golden-set 30 case (đó là DoD **D16 / #105**). Đây là **đầu vào đo** cho grid
`chunking×embedding` của AIE-1 (#96): mỗi case cho một `query` + `expected_citation` để #96 tính
recall@k / precision **có nhãn** trên 2 trục (chunk-size × embedding). `case_id` tiền tố `GQ-` để không
đụng `SC-` (smoke) và `HB-` (draft golden).

## Teeth (finding D11, 03/08): mỗi case dương phải để lại ≥2 ứng viên cùng scope

`citation_accuracy` **không có răng** khi fence lọc còn đúng 1 ứng viên hợp lệ — case xanh vì lý do
sai, embedding tốt/xấu không phân biệt được. Mọi case dương ở đây được annotate-verified là có **≥2
chunk cùng `tenant`+`section_role`** cạnh tranh (token-overlap > 0), nên thứ hạng THẬT SỰ phụ thuộc chất
lượng embedding. Ví dụ nặng nhất: `ankor-remote-001#c1` (0.846) chỉ hơn `#c2` (0.769) **0.077** ở điểm
token của `StaticKbSearch` (xấp xỉ cấu trúc mà embedding phải tách) — đúng "thiếu headroom" F-8. Đây là
các case để #96 đo trục embedding thứ 2 có phân biệt tốt hơn không; **trục đó phải giữ `EMBEDDING_DIM=8`**
vì `kb.chunks` là `vector(8)` và `PgKbSearch` là nơi DUY NHẤT embedding ảnh hưởng ranking.

## Nhãn KHÔNG gõ tay

Mọi `expected_citation` kiểm bằng `scripts/annotate_golden.py` chạy `StaticKbSearch` THẬT trên corpus
140-chunk (kỷ luật D6/D13). `tests/test_grid_inputs.py` chạy lại phép kiểm đó trong CI: expected chunk
truy xuất được TRONG scope + ≥2 ứng viên cùng scope (dương) · fence chặn chunk ngoài kho/vai (âm).
"""

from __future__ import annotations

from dataclasses import dataclass

GRID_SET_REF = "callisto-grid-queries-v0"


@dataclass(frozen=True, slots=True)
class GridCase:
    """Một case grid — 8 field format (`docs/format.md` §2) + `note` (comment, KHÔNG phải field).

    `note` chỉ render thành comment trong yaml để giải thích ý đồ; nó không vào phần dữ liệu 8-field,
    nên loader của evalhub/AIE-1 đọc y hệt smoke-5. `section_roles`/`expected_citation` là `tuple` để
    dataclass frozen hashable — render thành list yaml inline (`[public]`).
    """

    case_id: str
    query: str
    tenant: str
    section_roles: tuple[str, ...]
    expected_tenant: str
    expected_section_role: str
    expected: str
    expected_citation: tuple[str, ...]
    note: str

    @property
    def is_refusal(self) -> bool:
        """Case âm (leak-test) ⇔ không có citation kỳ vọng. Suy từ dữ liệu, không phải cờ riêng."""
        return not self.expected_citation


# ── Nguồn sự thật: 14 case dương (≥2 ứng viên cùng scope) + 6 case âm T1/T6 ─────────────────────
# Cặp chéo-tenant GQ-01↔02 (remote) · GQ-03↔04 (training) · GQ-05↔06 (oncall) · GQ-11↔12 (holidays):
# cùng query, khác tenant → đáp án PHẢI khác số. `expected` kế thừa nhãn tay D12 (HB draft) / trích chunk
# thật; `expected_citation` annotate-verified lại ở test.
#
# ⚠️ SỐ 20 CASE LÀ CHỌN CỦA DE, KHÔNG PHẢI QUY ĐỊNH. #95/#99/roadmap D14 không nêu số golden query
# (chỉ nêu grid "≥2×2" = kích thước bảng, không phải số case); bộ đủ 30 là mốc D16 (#105). Chọn 20 để
# grid recall/precision đủ hạt (mỗi ô ~x/14 thay vì x/7). Xem plans/day14_plan.md §6 + nên hỏi #96 số đủ.
GRID_CASES: tuple[GridCase, ...] = (
    GridCase(
        case_id="GQ-01",
        query="Nhân viên được làm việc từ xa tối đa mấy ngày một tuần?",
        tenant="ankor",
        section_roles=("public",),
        expected_tenant="ankor",
        expected_section_role="public",
        expected="3 ngày",
        expected_citation=("ankor-remote-001#c1",),
        note="teeth NẶNG: #c1(0.846) chỉ hơn #c2(0.769) 0.077 ở dim=8 — ứng viên cùng scope: remote #c1/#c2 + leave",
    ),
    GridCase(
        case_id="GQ-02",
        query="Nhân viên được làm việc từ xa tối đa mấy ngày một tuần?",
        tenant="borea",
        section_roles=("public",),
        expected_tenant="borea",
        expected_section_role="public",
        expected="2 ngày",
        expected_citation=("borea-remote-001#c1",),
        note="CẶP với GQ-01, khác tenant → 2 ngày (không phải 3); #c1/#c2 borea cách 0.000 ở dim=8 (hoà điểm)",
    ),
    GridCase(
        case_id="GQ-03",
        query="Ngân sách đào tạo mỗi năm là bao nhiêu?",
        tenant="ankor",
        section_roles=("hr",),
        expected_tenant="ankor",
        expected_section_role="hr",
        expected="8 triệu",
        expected_citation=("ankor-training-001#c1",),
        note="teeth: training #c1(0.50)/#c2(0.4375) cạnh tranh cùng hr",
    ),
    GridCase(
        case_id="GQ-04",
        query="Ngân sách đào tạo mỗi năm là bao nhiêu?",
        tenant="borea",
        section_roles=("hr",),
        expected_tenant="borea",
        expected_section_role="hr",
        expected="12 triệu",
        expected_citation=("borea-training-001#c1",),
        note="CẶP với GQ-03, khác tenant → 12 triệu; ứng viên cùng hr: training/benefits/conduct/performance",
    ),
    GridCase(
        case_id="GQ-05",
        query="Cảnh báo nghiêm trọng cần phản hồi trong bao lâu?",
        tenant="ankor",
        section_roles=("engineering",),
        expected_tenant="ankor",
        expected_section_role="engineering",
        expected="15 phút",
        expected_citation=("ankor-oncall-001#c2",),
        note="teeth biên rộng: oncall #c2(0.69)/#c1(0.31) cùng engineering — đối chứng với ca biên hẹp GQ-01",
    ),
    GridCase(
        case_id="GQ-06",
        query="Cảnh báo nghiêm trọng cần phản hồi trong bao lâu?",
        tenant="borea",
        section_roles=("engineering",),
        expected_tenant="borea",
        expected_section_role="engineering",
        expected="10 phút",
        expected_citation=("borea-oncall-001#c2",),
        note="CẶP với GQ-05, khác tenant → 10 phút; oncall #c2/#c1 + access cùng engineering",
    ),
    GridCase(
        case_id="GQ-07",
        query="Khoản mua từ bao nhiêu thì cần hai báo giá?",
        tenant="ankor",
        section_roles=("finance",),
        expected_tenant="ankor",
        expected_section_role="finance",
        expected="50 triệu",
        expected_citation=("ankor-procurement-001#c2",),
        note="teeth: procurement #c2 + invoicing/budget/procurement #c1 cùng finance",
    ),
    GridCase(
        case_id="GQ-08",
        query="Thang lương của công ty gồm những bậc nào?",
        tenant="ankor",
        section_roles=("hr",),
        expected_tenant="ankor",
        expected_section_role="hr",
        expected="6 bậc",
        expected_citation=("ankor-salary-001#c1",),
        note="teeth NẶNG: salary #c1(0.444) HOÀ điểm #c3(0.444) cùng hr — embedding phải tự phá hoà",
    ),
    GridCase(
        case_id="GQ-09",
        query="Thang lương của công ty gồm những bậc nào?",
        tenant="borea",
        section_roles=("hr",),
        expected_tenant="borea",
        expected_section_role="hr",
        expected="6 bậc",
        expected_citation=("borea-salary-001#c1",),
        note="salary borea trùng đáp án '6 bậc' với ankor (KHÔNG là cặp tương phản); #c1 sau #c3 — nhiều ứng viên hr",
    ),
    GridCase(
        case_id="GQ-10",
        query="Gói bảo hiểm sức khoẻ gồm những quyền lợi gì?",
        tenant="ankor",
        section_roles=("hr",),
        expected_tenant="ankor",
        expected_section_role="hr",
        expected="30 triệu",
        expected_citation=("ankor-benefits-001#c1",),
        note="teeth: benefits #c1(0.50) + conduct/recruitment/salary cùng hr",
    ),
    GridCase(
        case_id="GQ-11",
        query="Một năm có bao nhiêu ngày nghỉ lễ?",
        tenant="ankor",
        section_roles=("public",),
        expected_tenant="ankor",
        expected_section_role="public",
        expected="11 ngày",
        expected_citation=("ankor-holidays-001#c1",),
        note="teeth CỰC NẶNG: holidays #c1/#c2/#c3 HOÀ 0.50 ba chiều + leave cùng public [cặp GQ-12]",
    ),
    GridCase(
        case_id="GQ-12",
        query="Một năm có bao nhiêu ngày nghỉ lễ?",
        tenant="borea",
        section_roles=("public",),
        expected_tenant="borea",
        expected_section_role="public",
        expected="14 ngày",
        expected_citation=("borea-holidays-001#c1",),
        note="CẶP với GQ-11, khác tenant → 14 ngày (không phải 11); #c1/#c2 + leave hoà 0.50",
    ),
    GridCase(
        case_id="GQ-13",
        query="Mức công tác phí mỗi ngày là bao nhiêu?",
        tenant="ankor",
        section_roles=("finance",),
        expected_tenant="ankor",
        expected_section_role="finance",
        expected="500 nghìn",
        expected_citation=("ankor-reimbursement-001#c1",),
        note="teeth biên vừa: reimbursement #c1(0.667)/#c2(0.333) + invoicing cùng finance",
    ),
    GridCase(
        case_id="GQ-14",
        query="Sự cố được phân thành mấy mức nghiêm trọng?",
        tenant="ankor",
        section_roles=("engineering",),
        expected_tenant="ankor",
        expected_section_role="engineering",
        expected="ba mức",
        expected_citation=("ankor-incident-001#c1",),
        note="teeth chéo-doc: incident #c1(0.444) HOÀ oncall#c2(0.444) cùng engineering",
    ),
    # ── Âm: mầm leak-test, chấm refusal (fence phải để rỗng) ────────────────────────────────────
    GridCase(
        case_id="GQ-15",
        query="Ngân sách đào tạo của Borea là bao nhiêu?",
        tenant="ankor",
        section_roles=("hr",),
        expected_tenant="borea",
        expected_section_role="hr",
        expected="refusal",
        expected_citation=(),
        note="T1 chéo tenant: người ankor/hr hỏi số borea → scope ankor KHÔNG với tới chunk borea nào",
    ),
    GridCase(
        case_id="GQ-16",
        query="Gói bảo hiểm sức khoẻ bổ sung hạn mức bao nhiêu?",
        tenant="ankor",
        section_roles=("engineering",),
        expected_tenant="ankor",
        expected_section_role="hr",
        expected="refusal",
        expected_citation=(),
        note="T6 chéo vai: người engineering hỏi phúc lợi (vai hr) → scope engineering KHÔNG với tới chunk hr",
    ),
    GridCase(
        case_id="GQ-17",
        query="Cảnh báo nghiêm trọng của Borea phản hồi trong bao lâu?",
        tenant="ankor",
        section_roles=("engineering",),
        expected_tenant="borea",
        expected_section_role="engineering",
        expected="refusal",
        expected_citation=(),
        note="T1 chéo tenant: ankor/engineering hỏi oncall borea → scope ankor không với tới",
    ),
    GridCase(
        case_id="GQ-18",
        query="Thang lương của công ty gồm những bậc nào?",
        tenant="ankor",
        section_roles=("public",),
        expected_tenant="ankor",
        expected_section_role="hr",
        expected="refusal",
        expected_citation=(),
        note="T6 chéo vai: CÙNG query GQ-08 nhưng người hỏi vai public → salary(hr) ngoài tầm → refusal",
    ),
    GridCase(
        case_id="GQ-19",
        query="Hạn mức ngân sách phòng ban trong năm là bao nhiêu?",
        tenant="ankor",
        section_roles=("public",),
        expected_tenant="ankor",
        expected_section_role="finance",
        expected="refusal",
        expected_citation=(),
        note="T6 chéo vai: public hỏi ngân sách (vai finance) → refusal",
    ),
    GridCase(
        case_id="GQ-20",
        query="Khoản mua của Ankor từ bao nhiêu thì cần hai báo giá?",
        tenant="borea",
        section_roles=("finance",),
        expected_tenant="ankor",
        expected_section_role="finance",
        expected="refusal",
        expected_citation=(),
        note="T1 ngược chiều borea→ankor: borea/finance hỏi procurement ankor → refusal",
    ),
)


def _render_list(items: tuple[str, ...]) -> str:
    """Render tuple thành list yaml inline: `[public]`, `["a#c1"]`, `[]` — khớp shape smoke-5."""
    if not items:
        return "[]"
    return "[" + ", ".join(items) + "]"


def _render_citation(items: tuple[str, ...]) -> str:
    """`expected_citation` phải quote (chứa `#`, `-`): `["ankor-remote-001#c1"]` hoặc `[]`."""
    if not items:
        return "[]"
    return "[" + ", ".join(f'"{item}"' for item in items) + "]"


def render_yaml() -> str:
    """Render `GRID_CASES` thành text yaml deterministic — nguồn cho file check-in.

    Cùng đầu vào luôn ra **cùng byte** (không có set/dict thứ tự-bất-định): đó là điều kiện để
    `test_grid_inputs.py` so file trên đĩa với bản render lại, bắt drift gõ tay. Shape khớp
    `golden/smoke-5.yaml` để loader evalhub/AIE-1 đọc y hệt.
    """
    lines: list[str] = [
        "# Golden query + expected chunks cho grid chunking×embedding (D14, DE) — issue #95 → #96.",
        "#",
        "# ⚠️ FILE SINH RA — nguồn là src/studio_kb/grid_queries.py. Sửa ở đây sẽ bị",
        "#    tests/test_grid_inputs.py bắt (byte-identical). Sửa case → sửa module → chạy",
        "#    scripts/emit_grid_queries.py.",
        "#",
        "# Shape: docs/format.md §2 (8 field). Nhãn annotate-verified trên corpus 140-chunk; mọi case",
        "# dương để lại ≥2 ứng viên cùng tenant+section_role (teeth, finding D11). Xem module để biết ý đồ.",
        "",
        f"golden_set_ref: {GRID_SET_REF}",
        "",
        "cases:",
    ]
    for case in GRID_CASES:
        lines.append(f"  # {case.case_id}: {case.note}")
        lines.append(f"  - case_id: {case.case_id}")
        lines.append(f'    query: "{case.query}"')
        lines.append(f"    tenant: {case.tenant}")
        lines.append(f"    section_roles: {_render_list(case.section_roles)}")
        lines.append(f"    expected_tenant: {case.expected_tenant}")
        lines.append(f"    expected_section_role: {case.expected_section_role}")
        lines.append(f'    expected: "{case.expected}"')
        lines.append(f"    expected_citation: {_render_citation(case.expected_citation)}")
        lines.append("")
    return "\n".join(lines[:-1]) + "\n"
