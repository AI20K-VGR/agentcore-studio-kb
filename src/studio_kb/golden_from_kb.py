"""Sinh golden case từ **KB người dùng đã upload** — bộ dựng bộ chấm cho tài liệu thật.

Bộ 1.0/2.0 (`golden_set.py`/`golden_set_v2.py`) là case **viết tay** cho corpus Callisto curate sẵn.
Module này giải bài khác: người dùng nạp tài liệu của họ (`POST /api/admin/documents` → `cut_window`
→ `kb.chunks`), và cần một bộ chấm **cho chính tài liệu đó** — không ai ngồi viết tay 30 case cho mỗi
tenant.

## Thứ module này sinh, và thứ nó CỐ Ý không sinh

Sinh được **tất định**, không cần mạng: chọn chunk theo mật độ, gán nhãn tenant/vai, dựng case bẫy
hai trục, `expected_citation` lấy từ `chunk_id` thật, và kiểm ba quy tắc mẫu.

**KHÔNG** sinh: câu hỏi và đáp án bằng ngôn ngữ tự nhiên. Đó là việc của một mô hình, và nhét một
lời gọi LLM vào đây sẽ làm bộ sinh mất tính tất định — thứ mà cả `render_cases` lẫn test byte-identical
của repo này dựa vào. Thay vào đó `QuestionWriter` là **seam**: bản mặc định trích thẳng từ chunk (tất
định, dùng được ngay và trung thực về chất lượng), một bản LLM cắm vào sau mà không đụng phần sinh.

Ranh giới đó cũng là lý do `source` mặc định `"ai"` cho case sinh máy: nó khai đúng nguồn gốc, và
người sửa lại câu nào thì đổi thành `"human"` — `DEC-Q5` (DE sở hữu giá trị, AIE-2 sở hữu shape) vẫn
đứng, chỉ khác là giá trị giờ do máy đề xuất trước.

## Ba quy tắc mẫu, cưỡng chế bằng `sample_report`, không bằng lời

1. **mật độ** — 5–10 chunk cho 1 cặp QA. Dày hơn thì case trùng nội dung; thưa hơn thì bộ không phủ.
2. **tỷ lệ bẫy 20–30%** — dưới ngưỡng thì nhánh từ-chối không đủ mẫu để nói gì; trên ngưỡng thì
   `success_rate` bị chi phối bởi hàng rào chứ không phải chất lượng trả lời.
3. **cân phòng ban** — mỗi `section_role` ≥5 case, nếu không một vai đông case sẽ che một vai ít case
   trong con số gộp (đúng lệch đã đo ở `260824-golden-30-sample`: `hr` chiếm 43% bộ 2.0).

`sample_report` **báo cáo** ba con số đó thay vì raise: một bộ lệch vẫn dùng được nếu người dựng biết
nó lệch — thứ nguy hiểm là lệch mà không ai khai. Caller quyết định chặn hay không.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from studio_kb.golden_set_core import GoldenCase

# 5–10 chunk → 1 cặp QA; 7 là giữa khoảng, chọn để một corpus nhỏ vẫn ra được vài case.
DEFAULT_CHUNKS_PER_CASE = 7
# 20–30% case bẫy; 0.25 là giữa khoảng.
DEFAULT_TRAP_RATIO = 0.25
MIN_CASES_PER_ROLE = 5


@dataclass(frozen=True, slots=True)
class SourceChunk:
    """Một chunk đã index, đủ thông tin để dựng case. Hình dạng tối thiểu — cố ý KHÔNG dùng
    `KbSearchResultItem`: cái đó mang `score` (thuộc về một truy vấn cụ thể) và `tenant_id` UUID,
    trong khi golden case khai `tenant` bằng **slug** (`GoldenCase.tenant`). Nhận một kiểu riêng ở
    đây giữ bộ sinh độc lập với đường truy xuất."""

    chunk_id: str
    text: str
    tenant: str
    section_role: str


class QuestionWriter(Protocol):
    """Sinh `(query, expected)` từ một nhóm chunk. Seam để cắm LLM sau mà không đụng phần sinh."""

    def write(self, chunks: tuple[SourceChunk, ...]) -> tuple[str, str]: ...


class ExtractiveQuestionWriter:
    """Bản mặc định — **tất định, 0 call mạng**: lấy câu đầu của chunk đầu làm `expected`, và dựng
    `query` bằng một khuôn cố định quanh nó.

    Chất lượng thấp và **nó khai đúng như thế**: case sinh ra mang `source="ai"`, và mục đích của
    bản này là làm cho đường ống chạy được đầu-cuối + kiểm được bằng test, không phải thay người
    viết câu hỏi. Một `QuestionWriter` gọi LLM cắm vào chỗ này không đổi một dòng nào của
    `build_cases`."""

    def write(self, chunks: tuple[SourceChunk, ...]) -> tuple[str, str]:
        head = chunks[0].text.strip()
        first_sentence = head.split(".")[0].strip() if "." in head else head
        expected = first_sentence[:120]
        return (f"Tài liệu nói gì về: {expected}?", expected)


def _group_by_role(chunks: Sequence[SourceChunk]) -> dict[tuple[str, str], list[SourceChunk]]:
    """Gom theo `(tenant, section_role)`, giữ thứ tự tất định bằng `chunk_id`."""
    groups: dict[tuple[str, str], list[SourceChunk]] = {}
    for chunk in sorted(chunks, key=lambda c: c.chunk_id):
        groups.setdefault((chunk.tenant, chunk.section_role), []).append(chunk)
    return groups


def build_cases(
    chunks: Sequence[SourceChunk],
    *,
    writer: QuestionWriter | None = None,
    chunks_per_case: int = DEFAULT_CHUNKS_PER_CASE,
    trap_ratio: float = DEFAULT_TRAP_RATIO,
) -> tuple[GoldenCase, ...]:
    """Dựng bộ case từ chunk đã index. Tất định: cùng đầu vào ra **cùng** danh sách.

    Hai loại case, và loại thứ hai mới là thứ khó:

    - **trả-lời-được** — nhóm `chunks_per_case` chunk cùng `(tenant, role)`, `expected_citation` là
      `chunk_id` thật của chúng. `expects_refusal` suy ra `False` vì `expected_tenant == tenant` và
      vai đáp án nằm trong vai người hỏi.
    - **bẫy** — hai trục, dựng từ chunk **có thật của tenant/vai khác**, nên đáp án tồn tại nhưng
      **không** thuộc người hỏi:
        - **T1 chéo-tenant**: hỏi bằng danh tính tenant A về nội dung chỉ có ở tenant B;
        - **T6 chéo-vai**: cùng tenant, đáp án ở vai người hỏi không giữ.

      Cả hai để `expected_citation` **rỗng** — `GoldenCase.is_refusal` suy từ đó, và bộ chấm của
      evalhub suy `expects_refusal` từ hai trục tenant/vai. Hai đường suy độc lập phải cùng kết luận;
      đó là lý do không đặt một cờ `is_trap` riêng.

    Case bẫy mang `is_critical=True`: rò một case bẫy là **vi phạm hàng rào**, khác về chất với sai
    một câu nghiệp vụ. Đó là trục cổng bảo mật zero-tolerance đọc.
    """
    writer = writer or ExtractiveQuestionWriter()
    groups = _group_by_role(chunks)
    if not groups:
        return ()

    cases: list[GoldenCase] = []
    seq = 0

    for (tenant, role), role_chunks in sorted(groups.items()):
        for i in range(0, len(role_chunks), chunks_per_case):
            batch = tuple(role_chunks[i : i + chunks_per_case])
            if not batch:
                continue
            query, expected = writer.write(batch)
            seq += 1
            cases.append(
                GoldenCase(
                    case_id=f"AI-{seq:03d}",
                    query=query,
                    tenant=tenant,
                    section_roles=(role,),
                    expected_tenant=tenant,
                    expected_section_role=role,
                    expected=expected,
                    expected_citation=tuple(c.chunk_id for c in batch),
                    note=f"sinh máy từ {len(batch)} chunk của {tenant}/{role}",
                    source="ai",
                    tier="full",
                )
            )

    trap_count = _traps_needed(len(cases), trap_ratio)
    cases.extend(_build_trap_cases(groups, trap_count, writer, start_index=seq))
    return tuple(cases)


def _traps_needed(answerable_cases: int, trap_ratio: float) -> int:
    """`n` case bẫy để tỷ lệ bẫy trên TỔNG đạt `trap_ratio`.

    Giải `n / (answerable_cases + n) = ratio` ⇒ `n = ratio * m / (1 - ratio)`, làm tròn lên. Tính trên
    **tổng** chứ không trên số case trả-lời-được: `trap_ratio` là *"bao nhiêu phần trăm của bộ là
    bẫy"*, và nhầm mẫu số ở đây cho một bộ lệch ~1/3 so với ý định."""
    if answerable_cases == 0 or trap_ratio <= 0:
        return 0
    return max(1, round(trap_ratio * answerable_cases / (1 - trap_ratio)))


def _build_trap_cases(
    groups: dict[tuple[str, str], list[SourceChunk]],
    trap_count: int,
    writer: QuestionWriter,
    *,
    start_index: int,
) -> list[GoldenCase]:
    """Xen kẽ hai trục bẫy để không bộ nào chỉ có một loại.

    Trục T1 cần ≥2 tenant; corpus một tenant chỉ dựng được T6. Không raise khi thiếu — báo qua
    `sample_report`, vì một corpus một-tenant vẫn là đầu vào hợp lệ."""
    keys = sorted(groups)
    tenants = sorted({t for t, _ in keys})
    cases: list[GoldenCase] = []
    seq = start_index

    for i in range(trap_count):
        asking_tenant, asking_role = keys[i % len(keys)]
        cross_tenant = len(tenants) > 1 and i % 2 == 0
        trap_source = _pick_trap_source(groups, keys, asking_tenant, asking_role, cross_tenant)
        if trap_source is None:
            continue
        (answer_tenant, answer_role), batch = trap_source
        query, expected = writer.write(batch)
        seq += 1
        axis = "T1 chéo-tenant" if answer_tenant != asking_tenant else "T6 chéo-vai"
        cases.append(
            GoldenCase(
                case_id=f"AI-TRAP-{seq:03d}",
                query=query,
                tenant=asking_tenant,
                section_roles=(asking_role,),
                expected_tenant=answer_tenant,
                expected_section_role=answer_role,
                expected="refusal",
                expected_citation=(),
                note=f"bẫy {axis}: đáp án ở {answer_tenant}/{answer_role}, người hỏi là {asking_tenant}/{asking_role}",
                manual_label="refuse",
                source="ai",
                is_critical=True,
                tier="core",
            )
        )
        del expected
    return cases


def _pick_trap_source(
    groups: dict[tuple[str, str], list[SourceChunk]],
    keys: list[tuple[str, str]],
    asking_tenant: str,
    asking_role: str,
    cross_tenant: bool,
) -> tuple[tuple[str, str], tuple[SourceChunk, ...]] | None:
    """Nhóm chunk làm nguồn đáp án cho một case bẫy — phải KHÁC người hỏi ở đúng trục đang dựng."""
    for k in keys:
        tenant, role = k
        matches = tenant != asking_tenant if cross_tenant else (tenant == asking_tenant and role != asking_role)
        if matches and groups[k]:
            return k, tuple(groups[k][:1])
    return None


@dataclass(frozen=True, slots=True)
class SampleReport:
    """Ba quy tắc mẫu, đo được. **Báo cáo, không raise** — một bộ lệch vẫn dùng được nếu người dựng
    biết nó lệch; thứ nguy hiểm là lệch mà không ai khai."""

    n_case: int
    n_traps: int
    trap_ratio: float
    by_tenant: dict[str, int]
    by_role: dict[str, int]
    roles_below_minimum: tuple[str, ...]
    trap_ratio_met: bool

    @property
    def meets_all_rules(self) -> bool:
        return self.trap_ratio_met and not self.roles_below_minimum


def sample_report(cases: Sequence[GoldenCase], *, min_cases_per_role: int = MIN_CASES_PER_ROLE) -> SampleReport:
    """Đo ba quy tắc mẫu trên bộ vừa sinh (hoặc bộ viết tay — hàm không giả định nguồn).

    `is_refusal` suy từ `expected_citation` rỗng, đúng như `GoldenCase` đã khai — không đếm bằng
    `case_id` có tiền tố `AI-TRAP`, vì một bộ viết tay sẽ không mang tiền tố đó và phép đo phải dùng
    được cho cả hai."""
    n = len(cases)
    n_traps = sum(1 for c in cases if c.is_refusal)
    ratio = n_traps / n if n else 0.0
    by_role = Counter(role for c in cases for role in c.section_roles)
    return SampleReport(
        n_case=n,
        n_traps=n_traps,
        trap_ratio=round(ratio, 4),
        by_tenant=dict(sorted(Counter(c.tenant for c in cases).items())),
        by_role=dict(sorted(by_role.items())),
        roles_below_minimum=tuple(sorted(v for v, sl in by_role.items() if sl < min_cases_per_role)),
        trap_ratio_met=0.20 <= ratio <= 0.30,
    )
