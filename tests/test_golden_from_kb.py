"""`golden_from_kb` — sinh golden case từ KB người dùng đã upload.

Bốn thứ được khoá, và ba trong bốn nói về **case bẫy** — vì đó là phần khó và là phần mà một bộ sinh
cẩu thả sẽ làm sai một cách im lặng: sinh thừa case trả-lời-được thì lộ ra ngay ở điểm số, còn sinh
thiếu/sai case bẫy thì bộ chấm mất nhánh hàng rào mà mọi con số vẫn trông bình thường.
"""

from __future__ import annotations

from studio_kb.golden_from_kb import (
    DEFAULT_CHUNKS_PER_CASE,
    ExtractiveQuestionWriter,
    SourceChunk,
    build_cases,
    sample_report,
)
from studio_kb.golden_set_core import render_cases


def _chunks(tenant: str, role: str, n: int, offset: int = 0) -> list[SourceChunk]:
    return [
        SourceChunk(
            chunk_id=f"{tenant}-{role}-{offset + i:03d}#c1",
            text=f"Quy định {role} số {offset + i}. Chi tiết áp dụng cho {tenant}.",
            tenant=tenant,
            section_role=role,
        )
        for i in range(n)
    ]


def _two_tenant_corpus() -> list[SourceChunk]:
    return [
        *_chunks("ankor", "hr", 21),
        *_chunks("ankor", "finance", 14, offset=100),
        *_chunks("borea", "hr", 14, offset=200),
    ]


def test_deterministic_two_runs_same_bytes() -> None:
    """Cùng đầu vào ⇒ **cùng byte** sau `render_cases`.

    Không so hai `tuple` bằng `==` mà so **chuỗi render**: một bộ sinh dùng `set`/`dict` thứ-tự-bất-định
    ở giữa vẫn có thể cho hai tuple bằng nhau về nội dung nhưng khác thứ tự, và thứ tự là thứ file
    yaml trên đĩa ghi lại. Đây đúng bất biến `render_cases` tồn tại để phục vụ."""
    corpus = _two_tenant_corpus()
    mot = render_cases(("# fx",), "fx-v1", build_cases(corpus))
    hai = render_cases(("# fx",), "fx-v1", build_cases(list(reversed(corpus))))

    assert mot == hai, "đảo thứ tự đầu vào mà đầu ra đổi ⇒ bộ sinh không tất định"


def test_density_honours_chunks_per_case() -> None:
    """21 chunk cùng `(tenant, role)` với mật độ 7 ⇒ đúng 3 case trả-lời-được cho nhóm đó.

    Mật độ sai là lỗi im lặng nhất trong ba quy tắc mẫu: bộ vẫn chạy, điểm vẫn ra, chỉ là mỗi case
    phủ nhiều/ít nội dung hơn ý định và không ai thấy."""
    cases = build_cases(_chunks("ankor", "hr", 21), chunks_per_case=7)
    tra_loi = [c for c in cases if not c.is_refusal]

    assert len(tra_loi) == 3
    assert all(len(c.expected_citation) == 7 for c in tra_loi)


def test_trap_case_infers_refusal_from_BOTH_independent_paths() -> None:
    """**Bài quan trọng nhất.** Case bẫy phải cho `expects_refusal = True` theo **hai** đường suy
    độc lập, và cả hai phải cùng kết luận:

    - `studio_kb.GoldenCase.is_refusal` ⇐ `expected_citation` **rỗng**;
    - `studio_evalhub.GoldenCase.expects_refusal` ⇐ `expected_tenant != tenant` **hoặc**
      `expected_section_role not in section_roles`.

    Hai quadrant, hai cách suy, không import được nhau. Nếu bộ sinh chỉ thoả một đường — ví dụ để
    `expected_citation` rỗng nhưng gán `expected_tenant == tenant` và vai trùng — thì kb nói *"case
    bẫy"* còn evalhub chấm nó ở **nhánh trả-lời-được**, và agent từ chối đúng sẽ bị tính FAIL. Không
    exception nào nổi lên; chỉ có `success_rate` tụt và không ai biết vì sao.

    Bài này mô phỏng đường suy của evalhub tại chỗ (không import chéo được) và đòi hai đường khớp
    trên **từng** case."""
    cases = build_cases(_two_tenant_corpus())
    bay = [c for c in cases if c.is_refusal]
    assert bay, "corpus 2 tenant phải sinh được case bẫy"

    for case in bay:
        theo_evalhub = (case.expected_tenant != case.tenant) or (case.expected_section_role not in case.section_roles)
        assert theo_evalhub, (
            f"{case.case_id}: kb coi là bẫy (expected_citation rỗng) nhưng theo luật của evalhub thì "
            f"đây là case TRẢ-LỜI-ĐƯỢC (tenant={case.tenant}/{case.section_roles}, "
            f"đáp án ở {case.expected_tenant}/{case.expected_section_role})"
        )


def test_trap_case_is_critical_and_every_case_has_source_ai() -> None:
    """Bẫy ⇒ `is_critical=True` (trục cổng zero-tolerance đọc). Mọi case sinh máy ⇒ `source="ai"`.

    `source` khai đúng nguồn gốc là điều kiện của *"human ground-truth always wins"* lúc hợp nhất:
    không có nó thì bản người sửa và bản máy sinh không phân biệt được, và dedup sẽ giữ bừa."""
    cases = build_cases(_two_tenant_corpus())

    assert all(c.source == "ai" for c in cases)
    assert all(c.is_critical is True for c in cases if c.is_refusal)
    assert all(c.is_critical is None for c in cases if not c.is_refusal)


def test_single_tenant_corpus_still_yields_T6_traps_without_breaking() -> None:
    """Corpus **một** tenant không dựng được bẫy chéo-tenant (T1) — nhưng vẫn phải ra bẫy chéo-vai
    (T6), không raise.

    Đây là ca thật: tenant đầu tiên nạp tài liệu lên hệ thống chỉ có kho của chính họ. Một bộ sinh
    raise ở đây sẽ chặn đúng người dùng đầu tiên."""
    cases = build_cases([*_chunks("ankor", "hr", 14), *_chunks("ankor", "finance", 14, offset=100)])
    bay = [c for c in cases if c.is_refusal]

    assert bay
    assert all(c.expected_tenant == c.tenant for c in bay), "một tenant thì không có bẫy T1"
    assert all(c.expected_section_role not in c.section_roles for c in bay), "phải là bẫy T6"


def test_trap_ratio_lands_within_20_30_percent() -> None:
    """Quy tắc mẫu 2. Dưới ngưỡng ⇒ nhánh từ-chối không đủ mẫu để nói gì; trên ngưỡng ⇒
    `success_rate` bị chi phối bởi hàng rào chứ không phải chất lượng trả lời."""
    report = sample_report(build_cases(_two_tenant_corpus()))

    assert report.trap_ratio_met, f"tỷ lệ bẫy {report.trap_ratio} ngoài khoảng 0.20–0.30"
    assert report.n_traps > 0


def test_sample_report_names_roles_below_minimum_instead_of_raising() -> None:
    """Quy tắc mẫu 3 — **báo cáo, không raise**. Một bộ lệch vẫn dùng được nếu người dựng biết nó
    lệch; thứ nguy hiểm là lệch mà không ai khai.

    `roles_below_minimum` đọc được thành *"vai này sẽ bị vai khác che trong con số gộp"* — đúng lệch đã đo
    trên bộ 2.0 (`hr` chiếm 43%)."""
    cases = build_cases([*_chunks("ankor", "hr", 70), *_chunks("ankor", "finance", 7, offset=100)])
    report = sample_report(cases, min_cases_per_role=5)

    assert "finance" in report.roles_below_minimum
    assert "hr" not in report.roles_below_minimum
    assert not report.meets_all_rules


def test_writer_is_a_seam_another_impl_can_plug_into() -> None:
    """`QuestionWriter` là seam: cắm một bản khác đổi được `query`/`expected` mà **không** đụng phần
    sinh (nhãn tenant/vai, `expected_citation`, case bẫy).

    Đó là ranh giới cho phép cắm LLM sau này mà không làm bộ sinh mất tính tất định — bản mặc định
    `ExtractiveQuestionWriter` cố ý 0 call mạng."""

    class _Hoa:
        def write(self, chunks: tuple[SourceChunk, ...]) -> tuple[str, str]:
            return (f"CÂU HỎI RIÊNG ({len(chunks)} chunk)", "ĐÁP ÁN RIÊNG")

    mac_dinh = build_cases(_chunks("ankor", "hr", 14))
    rieng = build_cases(_chunks("ankor", "hr", 14), writer=_Hoa())

    assert all(c.query.startswith("CÂU HỎI RIÊNG") for c in rieng if not c.is_refusal)
    assert [c.expected_citation for c in rieng] == [c.expected_citation for c in mac_dinh]
    assert DEFAULT_CHUNKS_PER_CASE == 7
    assert isinstance(ExtractiveQuestionWriter().write(tuple(_chunks("ankor", "hr", 1)))[0], str)
