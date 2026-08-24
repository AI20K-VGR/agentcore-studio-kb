"""Shape + renderer trung tính dùng chung cho golden-set 1.0 (`golden_set`) và 2.0 (`golden_set_v2`).

Tách ra để 1.0 xoá được mà 2.0 vẫn đứng (cùng lý do `doc_factory_core`): `GoldenCase` là hình dạng
8-field của một case (`docs/format.md` §2), `MANUAL_LABEL_VALUES` là vocab nhãn tay, `render_cases`
là generator yaml deterministic — không thứ nào thuộc riêng corpus 1.0 hay 2.0. Nội dung case + header
+ EDGE_AXES ở lại đúng module phiên bản.

`golden_set` re-export `GoldenCase`/`MANUAL_LABEL_VALUES` nên mọi import cũ giữ nguyên; đây là SSOT.
"""

from __future__ import annotations

from dataclasses import dataclass

# Vocab nhãn tay (D18) — hai lớp verdict LLM-judge sinh ra: trả-lời-được vs từ-chối. Cố ý binary khớp
# `success: bool` của `judge.judge()`; đủ hai lớp mới cho agreement sức phân biệt (§1 cấm judge hằng).
MANUAL_LABEL_VALUES: tuple[str, ...] = ("pass", "refuse")


@dataclass(frozen=True, slots=True)
class GoldenCase:
    """Một golden case — 8 field format (`docs/format.md` §2) + `note` (comment, KHÔNG phải field).

    `note` chỉ render thành comment trong yaml để giải thích ý đồ; nó không vào phần dữ liệu 8-field,
    nên loader của evalhub (#108) đọc y hệt smoke-5. `section_roles`/`expected_citation` là `tuple` để
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
    source: str | None = None
    """`"ai"` (sinh máy, `golden_from_kb`) hay `"human"` (người viết/sửa) — `None` = **chưa khai**.

    Mặc định `None` chứ không `"ai"`: 60 case viết tay của bộ 1.0/2.0 không mang field này, và một
    mặc định `"ai"` sẽ **khai hộ nguồn gốc** cho cả 60. Cùng luật `manual_label` ngay dưới. Tập giá
    trị đóng ở phía tiêu thụ (`studio_evalhub.GoldenCase`, `Literal["ai","human"]`); ở đây để `str`
    vì module này là bút tác giả, không phải cổng kiểm."""

    is_critical: bool | None = None
    """Case thuộc nhánh **không được sai một lần nào** — đầu vào cổng bảo mật zero-tolerance.

    `None` = chưa phân loại, KHÔNG phải `False`: mặc định `False` dán *"không quan trọng"* lên mọi
    case sẵn có, nên cổng đọc trục này sẽ gác một tập **rỗng** và vẫn xanh."""

    tier: str | None = None
    """`"core"` (chạy lúc gate Publish) hay `"full"` (chạy nền) — `None` = chưa phân tầng.

    Người bấm Publish chờ được 15–30s; bộ Core 30–50 case vừa khoảng đó, còn Full 100–500 case mất
    5–10 phút ⇒ spinner treo hoặc HTTP 504."""

    manual_label: str | None = None
    """Nhãn tay ground-truth (D18, DE) — chỉ subset có, còn lại `None`. Giá trị trong `MANUAL_LABEL_VALUES`:
    `"pass"` (case trả-lời-được: đáp án grounded, agent PHẢI trả lời đúng) · `"refuse"` (case bẫy hàng rào:
    agent PHẢI từ chối). Là **answer-key người kiểm** để AIE-2 đo `agreement` của LLM-judge — không suy máy
    móc từ `is_refusal`, mà DE đọc chunk nguồn xác nhận (dù giá trị PHẢI nhất quán với `is_refusal`, xem
    guard `test_manual_label_*`). AIE-2 sở hữu format/nơi-lưu (`scorecard.v1.md §9`); DE sở hữu giá trị."""

    @property
    def is_refusal(self) -> bool:
        """Case âm (leak-test) ⇔ không có citation kỳ vọng. Suy từ dữ liệu, không phải cờ riêng."""
        return not self.expected_citation


def _render_list(items: tuple[str, ...]) -> str:
    """Render tuple thành list yaml inline: `[public]`, `[]` — khớp shape smoke-5/grid."""
    if not items:
        return "[]"
    return "[" + ", ".join(items) + "]"


def _render_citation(items: tuple[str, ...]) -> str:
    """`expected_citation` phải quote (chứa `#`, `-`): `["ankor-remote-001#c1"]` hoặc `[]`."""
    if not items:
        return "[]"
    return "[" + ", ".join(f'"{item}"' for item in items) + "]"


def render_cases(header: tuple[str, ...], golden_set_ref: str, cases: tuple[GoldenCase, ...]) -> str:
    """Render `cases` thành text yaml deterministic — generator chung cho golden-set 1.0/2.0.

    Cùng đầu vào luôn ra **cùng byte** (tuple có thứ tự, không set/dict thứ-tự-bất-định): đó là điều
    kiện để test byte-identical so file trên đĩa với bản render lại, bắt drift gõ tay.
    """
    lines: list[str] = [*header, "", f"golden_set_ref: {golden_set_ref}", "", "cases:"]
    for case in cases:
        lines.append(f"  # {case.case_id}: {case.note}")
        lines.append(f"  - case_id: {case.case_id}")
        lines.append(f'    query: "{case.query}"')
        lines.append(f"    tenant: {case.tenant}")
        lines.append(f"    section_roles: {_render_list(case.section_roles)}")
        lines.append(f"    expected_tenant: {case.expected_tenant}")
        lines.append(f"    expected_section_role: {case.expected_section_role}")
        lines.append(f'    expected: "{case.expected}"')
        lines.append(f"    expected_citation: {_render_citation(case.expected_citation)}")
        if case.manual_label is not None:
            lines.append(f"    manual_label: {case.manual_label}")
        # Ba field dưới chỉ render KHI khai — bộ 1.0/2.0 để `None` nên byte render không đổi một ký
        # tự, và bài so byte-identical với file trên đĩa vẫn xanh. Emit vô điều kiện sẽ làm mọi bài
        # đó đỏ vì một thay đổi không liên quan tới nội dung case nào.
        if case.source is not None:
            lines.append(f"    source: {case.source}")
        if case.is_critical is not None:
            lines.append(f"    is_critical: {str(case.is_critical).lower()}")
        if case.tier is not None:
            lines.append(f"    tier: {case.tier}")
        lines.append("")
    return "\n".join(lines[:-1]) + "\n"
