"""`golden_from_kb` — sinh golden case từ KB người dùng đã upload.

Bốn thứ được khoá, và ba trong bốn nói về **case bẫy** — vì đó là phần khó và là phần mà một bộ sinh
cẩu thả sẽ làm sai một cách im lặng: sinh thừa case trả-lời-được thì lộ ra ngay ở điểm số, còn sinh
thiếu/sai case bẫy thì bộ chấm mất nhánh hàng rào mà mọi con số vẫn trông bình thường.
"""

from __future__ import annotations

from studio_kb.golden_from_kb import (
    DEFAULT_CHUNKS_PER_CASE,
    DraftedQuestion,
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
            # Hình dạng Markdown THẬT: một tiêu đề nêu chủ đề, một dòng thân bài mang đại lượng.
            # Đây là thứ `TemplateQuestionWriter` (bản soạn mặc định) đọc được — fixture cũ là văn
            # bản phẳng không có tiêu đề lẫn con số, nên bản soạn từ chối sạch và mọi bài về mật độ/
            # tỷ lệ bẫy/cân vai đều đo trên một bộ RỖNG mà vẫn xanh nếu ngưỡng đặt lỏng.
            text=(f"## Quy định {role} số {offset + i}\nMức áp dụng cho {tenant} là {12 + i} ngày làm việc."),
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
    chunks = _chunks("ankor", "hr", 21)
    cases = build_cases(chunks, chunks_per_case=7)
    tra_loi = [c for c in cases if not c.is_refusal]

    # `chunks_per_case` là cỡ LÔ QUÉT, không phải hạn ngạch case.
    #
    # Bản trước lấy đúng một cặp mỗi lô ⇒ 21 chunk ra 3 case, và ý định "mỗi case phủ 5–10 chunk"
    # được thực thi bằng cách **phát chậm**. Cách đó vứt nội dung: một tài liệu quy định gọn nằm
    # trọn trong MỘT chunk dù có mười mục, nên nó ra đúng một case — đo được trên hệ thật, tài liệu
    # 10 tiêu đề upload xong ra bộ golden 2 case.
    #
    # Giờ mỗi tiêu đề phân biệt đóng góp một case, và ý định cũ ("case không trùng nội dung") được
    # thực thi TRỰC TIẾP bằng khử trùng theo chủ đề — đo đúng thứ cần đo thay vì hạn chế số lượng.
    assert len(tra_loi) > 3
    assert len({c.query for c in tra_loi}) == len(tra_loi), "case trùng câu hỏi — khử trùng chủ đề hỏng"
    # ĐÚNG MỘT trích dẫn mỗi case — không phải cả lô 7 chunk như trước.
    #
    # Mật độ 7 vẫn là mật độ 7: nó điều khiển bao nhiêu chunk được XÉT cho một câu hỏi (và do đó
    # sinh ra 3 case từ 21 chunk), không phải bao nhiêu chunk bị khai là đáp án. Gộp hai khái niệm đó
    # là thứ kéo `citation_accuracy` xuống 0.07 trên bộ thật: agent lấy top-k vài chunk thì không đời
    # nào trích đủ 7 `chunk_id`, và nó bị chấm sai vì một chuyện nó không làm sai.
    assert all(len(c.expected_citation) == 1 for c in tra_loi)

    # Và trích dẫn đó phải là chunk CÓ THẬT trong lô đã sinh ra case, không phải một id bịa.
    lo = {c.chunk_id for c in chunks}
    assert all(c.expected_citation[0] in lo for c in tra_loi)
    # Mỗi case trỏ một chunk KHÁC nhau: cùng một id lặp lại nghĩa là bản soạn luôn lấy chunk đầu của
    # toàn corpus thay vì chunk đã thật sự sinh ra đáp án — một lỗi off-by-batch mà tổng số case
    # không lộ ra.
    assert len({c.expected_citation[0] for c in tra_loi}) == len(tra_loi)


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
    # Ngưỡng đo nâng lên thay vì thu nhỏ fixture, vì `by_role` đếm CẢ case bẫy: bẫy chia round-robin
    # theo vai và số lượng tỷ lệ với TỔNG case, nên một vai chỉ 3 chunk vẫn nhận cả chục case bẫy.
    # Bản cũ giữ được `min_cases_per_role=5` chỉ nhờ mỗi lô 7 chunk ra đúng 1 case, tức nhờ một hệ
    # quả của luật sinh chứ không phải nhờ điều bài này muốn đo.
    cases = build_cases([*_chunks("ankor", "hr", 70), *_chunks("ankor", "finance", 3, offset=100)])
    report = sample_report(cases, min_cases_per_role=20)

    assert "finance" in report.roles_below_minimum
    assert "hr" not in report.roles_below_minimum
    assert not report.meets_all_rules


def test_writer_is_a_seam_another_impl_can_plug_into() -> None:
    """`QuestionWriter` là seam: cắm một bản khác đổi được `query`/`expected` mà **không** đụng phần
    sinh (nhãn tenant/vai, `expected_citation`, case bẫy).

    Đó là ranh giới cho phép cắm LLM sau này mà không làm bộ sinh mất tính tất định — bản mặc định
    `ExtractiveQuestionWriter` cố ý 0 call mạng."""

    class _Custom:
        def write(self, chunks: tuple[SourceChunk, ...]) -> DraftedQuestion:
            return DraftedQuestion(
                query=f"CÂU HỎI RIÊNG ({len(chunks)} chunk)",
                expected="ĐÁP ÁN RIÊNG",
                source_chunk_id=chunks[0].chunk_id,
            )

        def write_all(self, chunks: tuple[SourceChunk, ...]) -> tuple[DraftedQuestion, ...]:
            return (self.write(chunks),)

    mac_dinh = build_cases(_chunks("ankor", "hr", 14), writer=ExtractiveQuestionWriter())
    rieng = build_cases(_chunks("ankor", "hr", 14), writer=_Custom())

    assert all(c.query.startswith("CÂU HỎI RIÊNG") for c in rieng if not c.is_refusal)
    # Cả hai bản soạn đều neo `expected_citation` vào chunk ĐẦU của lô, nên hai bộ trùng nhau ở đây —
    # đúng ý "cắm bản khác không đụng phần sinh". So sánh này chỉ còn nghĩa khi citation đến từ bản
    # nháp: nếu `build_cases` quay lại gán cả lô, hai vế vẫn bằng nhau và bài mất khả năng phát hiện.
    assert [c.expected_citation for c in rieng] == [c.expected_citation for c in mac_dinh]
    assert all(len(c.expected_citation) == 1 for c in rieng if not c.is_refusal)
    assert DEFAULT_CHUNKS_PER_CASE == 7
    # `ExtractiveQuestionWriter` KHÔNG BAO GIỜ từ chối — đó là lý do nó còn tồn tại sau khi
    # `TemplateQuestionWriter` thay chỗ mặc định. `assert ... is not None` ghim đúng tính chất đó.
    fallback = ExtractiveQuestionWriter().write(tuple(_chunks("ankor", "hr", 1)))
    assert fallback is not None
    assert isinstance(fallback.query, str)


def test_traps_survive_when_a_roles_first_chunk_is_unaskable() -> None:
    """Case bẫy KHÔNG được phụ thuộc vào việc chunk ĐẦU của một vai có soạn được câu hỏi hay không.

    `_pick_trap_source` đưa cho bản soạn một nhóm chunk để lấy nội dung hỏi. Nếu nó chỉ đưa đúng
    chunk đầu, và chunk đó là trang bìa (không đại lượng nào để hỏi), thì bản soạn từ chối — và vì
    nó luôn là CÙNG một chunk cho mọi lượt, **toàn bộ** case bẫy của vai đó biến mất cùng lúc.

    Đo được trên tenant thật sau khi `TemplateQuestionWriter` thành mặc định: 59 case trả-lời-được,
    **0 case bẫy**, tỷ lệ bẫy 0% so với quy tắc 20–30%. Hỏng ở đây im lặng hơn hỏng ở nhánh trả lời:
    bộ vẫn đủ case, điểm vẫn ra, chỉ là cổng hàng rào không còn đo gì cả."""
    trang_bia = SourceChunk(
        chunk_id="ankor-hr-000#c1",
        text="# SỔ TAY NHÂN SỰ\nTài liệu nội bộ, vui lòng không phát tán ra ngoài.",
        tenant="ankor",
        section_role="hr",
    )
    # `offset=1` để chunk sinh ra bắt đầu ở `...-001`: `groups` xếp theo `chunk_id`, nên trang bìa
    # `...-000` phải đứng ĐẦU thì bài mới dựng được đúng cảnh cần đo. Dùng `offset=0` sẽ tạo một
    # chunk trùng id với trang bìa và thứ tự thành ngẫu nhiên — bài xanh mà không chứng minh gì.
    cases = build_cases(
        [trang_bia, *_chunks("ankor", "hr", 20, offset=1), *_chunks("ankor", "finance", 20, offset=200)]
    )

    traps = [c for c in cases if c.is_refusal]
    asking_roles = {t.section_roles[0] for t in traps}

    # Chiều CHẾT là chiều `finance` hỏi: nội dung đáp án của nó lấy từ vai `hr`, mà chunk đầu của
    # `hr` là trang bìa. Bẫy chiều `hr` hỏi thì vẫn sống vì nó lấy nội dung từ `finance` — assert
    # nhầm chiều sẽ cho một bài xanh vĩnh viễn không chứng minh gì.
    assert "finance" in asking_roles, (
        "vai `finance` mất sạch case bẫy vì chunk ĐẦU của vai `hr` không soạn được câu hỏi — "
        f"bẫy dựng được cho: {sorted(asking_roles)}"
    )


def test_traps_for_one_asking_role_are_distinct_questions() -> None:
    """Nhiều case bẫy cùng một vai hỏi phải là những câu hỏi KHÁC nhau.

    `_pick_trap_source` duyệt `keys` và trả về nhóm khớp ĐẦU TIÊN, nên mọi case bẫy hỏi dưới cùng
    một vai đều lấy nội dung từ cùng một nhóm — ra cùng một câu hỏi. Chúng sống sót qua `build_cases`
    nhưng bị `_drop_key_collisions` (khoá `(tenant, câu hỏi chuẩn hoá, vai)`) gộp lại còn một.

    Hệ quả đo được: sinh trên cả tenant ankor ra 20 case bẫy chia đều 5 mỗi vai, nhưng bộ THẬT SỰ
    ghi xuống cho `hr` chỉ còn **1** — tỷ lệ bẫy tụt từ 25% xuống ~6%, dưới hẳn quy tắc 20–30%. Con
    số trước khi lọc trông vẫn đúng, nên chỗ hụt không lộ ra ở đâu cả."""
    cases = build_cases(
        [
            # 49 chunk/vai (7 case/vai) để `_traps_needed` cấp đủ nhiều bẫy mà chia round-robin ra
            # vẫn còn ≥2 cho mỗi vai hỏi — dưới mức đó thì "trùng câu hỏi" không quan sát được.
            *_chunks("ankor", "hr", 49),
            *_chunks("ankor", "finance", 49, offset=100),
            *_chunks("ankor", "engineering", 49, offset=200),
        ]
    )
    hr_traps = [c for c in cases if c.is_refusal and c.section_roles[0] == "hr"]

    assert len(hr_traps) >= 2, f"cần ít nhất 2 case bẫy hỏi dưới vai hr để đo, thấy {len(hr_traps)}"
    assert len({c.query for c in hr_traps}) == len(hr_traps), (
        "case bẫy cùng vai hỏi trùng câu hỏi nhau — chúng sẽ bị gộp lúc ghi và tỷ lệ bẫy tụt "
        f"dưới quy tắc: {[c.query for c in hr_traps]}"
    )


def test_a_case_answerable_from_two_documents_is_dropped() -> None:
    """Cụm đáp án xuất hiện ở NHIỀU tài liệu ⇒ bỏ case, không dựng.

    `expected_citation` khai đúng một `chunk_id`, và `citation_accuracy` chấm theo đúng id đó. Nếu
    cùng một cụm ("7 năm") có mặt ở hai tài liệu khác nhau thì agent trả lời ĐÚNG và trích một
    nguồn ĐÚNG vẫn bị chấm 0 — chỉ vì nó chọn tài liệu kia.

    Đo được: câu *"Lưu trữ là bao nhiêu năm?"* dựng từ `ankor-finance-budget#c10`, agent trả lời
    *"Hồ sơ mua sắm được lưu trữ trong 7 năm"* và trích `ankor-finance-procurement#c10`. Không ai
    sai cả — câu hỏi mới là thứ mơ hồ.

    Bỏ case là lựa chọn đúng thay vì nới `expected_citation` thành nhiều id: `citation_accuracy`
    chia cho `len(expected)`, nên thêm id thứ hai làm một lượt trích đúng tụt xuống 0.5."""
    common = "Hồ sơ lưu trữ 7 năm theo quy định."
    chunks = [
        SourceChunk(
            chunk_id="ankor-finance-budget#c1", text=f"## Lưu trữ\n{common}", tenant="ankor", section_role="finance"
        ),
        SourceChunk(
            chunk_id="ankor-finance-procurement#c1",
            text=f"## Lưu trữ\n{common}",
            tenant="ankor",
            section_role="finance",
        ),
    ]
    assert [c for c in build_cases(chunks) if not c.is_refusal] == []


def test_the_same_phrase_repeated_inside_ONE_document_is_still_usable() -> None:
    """Đối trọng: cùng cụm lặp lại trong CÙNG một tài liệu không phải mơ hồ.

    `cut_window` cắt cửa sổ trượt có overlap, nên một câu nằm ở hai chunk liền kề là chuyện bình
    thường — chặn cả ca đó sẽ xoá phần lớn bộ case mà không đổi lấy gì."""
    common = "Hồ sơ lưu trữ 7 năm theo quy định."
    chunks = [
        SourceChunk(
            chunk_id="ankor-finance-budget#c1", text=f"## Lưu trữ\n{common}", tenant="ankor", section_role="finance"
        ),
        SourceChunk(
            chunk_id="ankor-finance-budget#c2",
            text=f"## Lưu trữ tiếp\n{common}",
            tenant="ankor",
            section_role="finance",
        ),
    ]
    assert [c for c in build_cases(chunks) if not c.is_refusal]


def test_the_same_phrase_under_a_DIFFERENT_role_is_not_ambiguity() -> None:
    """Cụm trùng ở một VAI khác không phải mơ hồ — agent hỏi dưới vai này không truy được vai kia.

    Hàng rào chặn ở tầng retrieval, nên tài liệu `finance` không phải một lựa chọn của agent đang
    hỏi dưới vai `hr`. Quét toàn corpus thay vì quét trong lô sẽ bỏ nhầm phần lớn case chỉ vì các
    phòng ban dùng chung cách diễn đạt — đo được: đổi sang quét toàn corpus làm 2 bài về case bẫy
    đỏ luôn, vì fixture của chúng dùng cùng một khuôn câu cho mọi vai."""
    common = "Hồ sơ lưu trữ 7 năm theo quy định."
    chunks = [
        SourceChunk(chunk_id="ankor-hr-records#c1", text=f"## Lưu trữ\n{common}", tenant="ankor", section_role="hr"),
        SourceChunk(
            chunk_id="ankor-finance-budget#c1",
            text=f"## Lưu trữ ngân sách\n{common}",
            tenant="ankor",
            section_role="finance",
        ),
    ]
    assert [c for c in build_cases(chunks) if not c.is_refusal]


def test_ambiguity_check_ignores_letter_case() -> None:
    """Chủ đề trùng nhưng khác hoa/thường vẫn là trùng.

    Đo được ca cuối cùng còn trượt trên một lượt chấm thật: chủ đề `"Phê duyệt công tác"` (tiêu đề,
    viết hoa đầu từ) cũng nằm trong một tài liệu khác dưới dạng `"...thời gian phê duyệt công tác
    tối đa..."` — giữa câu nên viết thường. Phép so phân biệt hoa/thường bỏ lọt, và câu hỏi mơ hồ đó
    kéo `citation_accuracy` xuống 0.92 trên một bộ 13 case."""
    chunks = [
        SourceChunk(
            chunk_id="ankor-finance-travel#c1",
            text="## Phê duyệt công tác\nYêu cầu nộp trước 7 ngày.",
            tenant="ankor",
            section_role="finance",
        ),
        SourceChunk(
            chunk_id="ankor-finance-reimbursement#c1",
            text="## Hoàn ứng\nThời gian phê duyệt công tác tối đa là 3 ngày làm việc.",
            tenant="ankor",
            section_role="finance",
        ),
    ]
    queries = [c.query for c in build_cases(chunks) if not c.is_refusal]
    assert not any("Phê duyệt công tác" in q for q in queries), (
        f"chủ đề có mặt ở hai tài liệu (khác hoa/thường) mà vẫn dựng thành câu hỏi: {queries}"
    )
