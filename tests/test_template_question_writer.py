"""`TemplateQuestionWriter` — soạn câu hỏi theo mẫu từ cấu trúc Markdown.

Thứ đang được chứng minh không phải "hàm chạy được" mà là **nó biết từ chối**. Bản soạn cũ
(`ExtractiveQuestionWriter`) luôn sinh được vì khuôn của nó không cần hiểu gì cả, và đó chính là lý
do bộ golden tự sinh đòi agent chép lại nguyên văn tài liệu. Nên phần lớn bài dưới đây đo ca
KHÔNG khớp mẫu, không phải ca khớp.
"""

from __future__ import annotations

from studio_kb.golden_from_kb import SourceChunk
from studio_kb.template_question_writer import _MAX_EXPECTED_TOKENS, TemplateQuestionWriter


def _chunk(text: str, chunk_id: str = "ankor-hr-leave#c1") -> SourceChunk:
    return SourceChunk(chunk_id=chunk_id, text=text, tenant="ankor", section_role="hr")


def test_heading_plus_quantity_gives_a_real_question_and_a_short_answer() -> None:
    """Hình dạng phổ biến nhất của tài liệu quy định: tiêu đề nêu chủ đề, thân bài mang con số.

    Kiểm cả hai vế vì chúng hỏng độc lập: `query` đúng mà `expected` dài thì nấc 1 vẫn chấm sai một
    câu trả lời tốt; `expected` ngắn mà `query` là nguyên văn chunk thì bộ vẫn đòi chép lại."""
    drafted = TemplateQuestionWriter().write(
        (_chunk("## Nghỉ phép năm\nNhân viên chính thức được 12 ngày phép có lương."),)
    )

    assert drafted is not None
    assert drafted.query == "Nghỉ phép năm là bao nhiêu ngày?"
    # Phần MANG THÔNG TIN, không phải cả mệnh đề: cắt tại `có` (từ nối mở ra bổ ngữ). Bản trước lấy
    # tới 7 token và đo được 4/15 case trượt chỉ vì cụm dài không sống sót qua cách diễn đạt của
    # agent — dù câu trả lời hoàn toàn đúng.
    assert drafted.expected == "12 ngày phép"
    assert drafted.source_chunk_id == "ankor-hr-leave#c1"
    # Không được bắt đầu bằng khuôn của bản cũ — đó là hồi quy đúng thứ PR này đi sửa.
    assert not drafted.query.startswith("Tài liệu nói gì về")


def test_expected_stops_at_punctuation_and_at_the_token_cap() -> None:
    """`expected` là đoạn token LIỀN NHAU bắt đầu tại con số — nấc 1 khớp bằng đúng cơ chế đó.

    Hai mốc dừng, và bài này ép cả hai cùng lúc: câu dài hơn trần token sẽ bị cắt ở trần, còn câu
    ngắn hơn thì dừng ở dấu câu chứ không nuốt sang mệnh đề sau."""
    dai = TemplateQuestionWriter().write(
        (_chunk("## Trợ cấp\nCông ty chi 50.000.000 VNĐ mỗi năm cho toàn bộ nhân sự khối vận hành."),)
    )
    assert dai is not None
    assert len(dai.expected.split()) <= _MAX_EXPECTED_TOKENS

    ngan = TemplateQuestionWriter().write(
        (_chunk("## Trợ cấp đi lại\nMức hỗ trợ là 500.000 đồng. Khoản này trả cùng lương tháng."),)
    )
    assert ngan is not None
    assert "Khoản này" not in ngan.expected, "không được nuốt sang câu sau dấu chấm"


def test_labelled_line_works_as_both_topic_and_answer() -> None:
    """Rất nhiều tài liệu nội bộ dùng dòng `Nhãn: giá trị` thay cho heading. Bỏ qua hình dạng này là
    bỏ trắng cả những tài liệu viết dạng bảng kê."""
    drafted = TemplateQuestionWriter().write((_chunk("- **Hạn mức nội trú**: 50.000.000 VNĐ/năm"),))

    assert drafted is not None
    assert drafted.query == "Hạn mức nội trú là bao nhiêu?"
    assert drafted.expected.startswith("50.000.000")


def test_time_money_and_rate_get_different_question_tails() -> None:
    """Đuôi câu hỏi đi theo HỌ đơn vị. Một danh sách đơn vị phẳng sẽ buộc mọi câu dùng chung đuôi
    "là bao nhiêu?", và câu đó nghe sai với đơn vị thời gian ("Thời gian thử việc là bao nhiêu?")."""
    writer = TemplateQuestionWriter()
    thoi_gian = writer.write((_chunk("## Thời gian thử việc\nÁp dụng 2 tháng cho vị trí chính thức."),))
    tien = writer.write((_chunk("## Ngân sách đào tạo\nMỗi người 10.000.000 VNĐ."),))
    ty_le = writer.write((_chunk("## Tỷ lệ đóng bảo hiểm\nNgười lao động đóng 10.5% lương."),))

    assert thoi_gian is not None and thoi_gian.query.endswith("là bao nhiêu tháng?")
    assert tien is not None and tien.query.endswith("là bao nhiêu?")
    assert ty_le is not None and ty_le.query.endswith("là bao nhiêu phần trăm?")


def test_returns_none_when_there_is_no_quantity_to_ask_about() -> None:
    """**Bài trung tâm.** Văn xuôi không có đại lượng ⇒ không soạn được ⇒ `None`.

    Bản cũ sinh ra case ở đúng ca này, và case đó đòi agent đọc lại nguyên văn đoạn văn. Một bộ ít
    case mà đúng còn dùng được; một bộ đủ số lượng nhưng luôn sai thì làm cổng publish đỏ vĩnh viễn,
    và một cổng luôn đỏ thì không còn là cổng."""
    drafted = TemplateQuestionWriter().write(
        (_chunk("## Văn hóa công ty\nChúng tôi đề cao sự trung thực và tinh thần hợp tác."),)
    )
    assert drafted is None


def test_returns_none_when_a_quantity_has_no_heading_above_it() -> None:
    """Có con số nhưng không có chủ đề ⇒ không có gì để hỏi. Dựng câu hỏi từ chính đoạn văn ở đây là
    quay đúng về khuôn cũ."""
    assert TemplateQuestionWriter().write((_chunk("Mức hỗ trợ là 500.000 đồng mỗi tháng."),)) is None


def test_bare_number_without_a_unit_is_not_an_answer() -> None:
    """`3.` của một danh sách đánh số không phải đại lượng. Thiếu ràng buộc đơn vị, mọi tài liệu có
    danh sách đánh số đều sinh ra case hỏi về số thứ tự."""
    drafted = TemplateQuestionWriter().write(
        (_chunk("## Quy trình duyệt chi\n3. Kế toán trưởng ký xác nhận trước khi chuyển khoản."),)
    )
    assert drafted is None


def test_all_caps_cover_title_is_not_a_topic() -> None:
    """Tiêu đề toàn chữ HOA là trang bìa — nó nêu TÊN tài liệu, không nêu chủ đề của một quy định.

    Đây là ca đo được trên bộ thật: case đầu tiên của `kb-hr-auto-v1` hỏi về "CẨM NANG NỘI QUY VÀ
    VĂN HÓA DOANH NGHIỆP SỔ TAY QUY ĐỊNH LÀM VIỆC…", một câu không hỏi gì cả."""
    # Thân bài PHẢI mang một đại lượng khớp được ("30 ngày"), nếu không bài này xanh vì không có gì
    # để hỏi chứ không phải vì tiêu đề bị loại — đo được bằng mutation: gỡ chặn all-caps mà bài vẫn
    # xanh với fixture cũ ("Ban hành năm 2026 gồm 5 chương", không đại lượng nào khớp).
    drafted = TemplateQuestionWriter().write(
        (_chunk("# CẨM NANG NỘI QUY VÀ VĂN HÓA DOANH NGHIỆP\nHiệu lực sau 30 ngày kể từ ngày ký."),)
    )
    assert drafted is None

    # Đối trọng: cùng thân bài đó, tiêu đề viết thường thì SOẠN ĐƯỢC. Thiếu vế này, ai đó "sửa" ca
    # trên bằng cách chặn luôn mọi tiêu đề và bài vẫn xanh.
    thuong = TemplateQuestionWriter().write((_chunk("## Hiệu lực thi hành\nHiệu lực sau 30 ngày kể từ ngày ký."),))
    assert thuong is not None
    assert thuong.query == "Hiệu lực thi hành là bao nhiêu ngày?"


def test_scans_the_whole_batch_and_pins_the_chunk_it_actually_used() -> None:
    """Lô nhiều chunk: bỏ qua chunk không khớp, và `source_chunk_id` phải trỏ chunk THẬT SỰ dùng.

    Trỏ nhầm về `chunks[0]` là lỗi không lộ ra ở số lượng case — bộ vẫn đủ case, chỉ có
    `citation_accuracy` sai mà không ai truy được về đâu."""
    drafted = TemplateQuestionWriter().write(
        (
            _chunk("Không có tiêu đề, không có số.", chunk_id="ankor-hr-a#c1"),
            _chunk("## Văn hóa\nĐề cao trung thực.", chunk_id="ankor-hr-b#c1"),
            _chunk("## Nghỉ phép năm\nĐược 12 ngày phép có lương.", chunk_id="ankor-hr-c#c1"),
        )
    )
    assert drafted is not None
    assert drafted.source_chunk_id == "ankor-hr-c#c1"


def test_is_deterministic() -> None:
    """Cùng đầu vào ⇒ cùng đầu ra. Cả `render_cases` lẫn test byte-identical của repo dựa vào tính
    chất này, và nó là lý do bản soạn mặc định KHÔNG gọi LLM."""
    chunk = _chunk("## Nghỉ phép năm\nNhân viên chính thức được 12 ngày phép có lương.")
    writer = TemplateQuestionWriter()
    assert writer.write((chunk,)) == writer.write((chunk,))


def test_a_date_is_not_a_quantity() -> None:
    """`31/03` là NGÀY THÁNG, không phải đại lượng — dù `03` đứng ngay trước chữ "năm".

    Đo được trên bộ thật sau lần sinh đầu bằng bản soạn này: case AI-035 hỏi *"Nghỉ phép chưa dùng
    là bao nhiêu năm?"* và chờ đáp án *"31/03 năm kế tiếp"*. Câu hỏi vô nghĩa, đáp án là một cái mốc
    chứ không phải một lượng — nhưng mọi ràng buộc khác (có tiêu đề, có số, có đơn vị) đều thoả."""
    drafted = TemplateQuestionWriter().write(
        (_chunk("## Nghỉ phép chưa dùng\nPhép chưa dùng hết hạn 31/03 năm kế tiếp, không quy đổi."),)
    )
    assert drafted is None


def test_question_does_not_repeat_a_unit_the_topic_already_carries() -> None:
    """Tiêu đề đã mang đơn vị thì đuôi câu hỏi không lặp lại nó.

    Đo được: *"Mục tiêu 30-60-90 ngày là bao nhiêu ngày?"* — câu hỏi tự vấp vào chính nó."""
    drafted = TemplateQuestionWriter().write(
        (_chunk("## Mục tiêu 30-60-90 ngày\nQuản lý và nhân viên mới chốt trong 7 ngày đầu."),)
    )
    assert drafted is not None
    assert drafted.query == "Mục tiêu 30-60-90 ngày là bao nhiêu?"


def test_expected_does_not_end_on_a_dangling_number_or_conjunction() -> None:
    """Cắt ở trần token không được để lại một con số cụt hay một liên từ treo.

    Đo được: `"50.000.000 VNĐ/năm cho nội trú và 15.000.000"` — token cuối là một con số chưa có đơn
    vị, và nấc 1 khớp token LIỀN NHAU nên cả cụm đó gần như không bao giờ khớp câu trả lời thật."""
    drafted = TemplateQuestionWriter().write(
        (_chunk("## Bảo hiểm sức khoẻ\nHạn mức 50.000.000 VNĐ/năm cho nội trú và 15.000.000 VNĐ cho ngoại trú."),)
    )
    assert drafted is not None
    last = drafted.expected.split()[-1]
    assert not last[0].isdigit(), f"token cuối là số cụt: {drafted.expected!r}"
    assert last.lower() not in {"và", "hoặc", "cho", "của", "với", "trong"}, f"liên từ treo: {drafted.expected!r}"


def test_matches_units_written_without_vietnamese_diacritics() -> None:
    """Tài liệu gõ KHÔNG DẤU vẫn phải soạn được câu hỏi.

    Không hiếm: tài liệu xuất từ hệ thống cũ, người gõ tắt, hoặc file mất encoding trên đường đi.
    Chính fixture của repo cũng viết như vậy (`test_golden_sets_routes._VALID_MD`: *"Nhan vien chinh
    thuc duoc 12 ngay phep nam moi nam"*). Khớp đơn vị theo đúng chuỗi có dấu sẽ bỏ trắng toàn bộ
    nhóm tài liệu đó — im lặng, vì "không soạn được" là kết quả hợp lệ."""
    drafted = TemplateQuestionWriter().write(
        (_chunk("## Nghi phep\nNhan vien chinh thuc duoc 12 ngay phep nam moi nam."),)
    )
    assert drafted is not None
    assert drafted.query == "Nghi phep la bao nhieu ngay?" or drafted.query.startswith("Nghi phep")
    assert drafted.expected.startswith("12 ngay")


def test_a_short_standalone_line_acts_as_a_heading_for_docx() -> None:
    """`.docx` KHÔNG có `##` — tiêu đề của nó là một **đoạn văn ngắn, không dấu câu kết**.

    `extract._extract_docx` nối các paragraph bằng `\\n`, nên cấu trúc còn nguyên ở dạng dòng; chỉ
    có dấu hiệu Markdown là không có. Chỉ nhận `#{1,6}` sẽ bỏ trắng toàn bộ tài liệu Word — mà đó
    đúng là định dạng người dùng nạp lên nhiều nhất."""
    drafted = TemplateQuestionWriter().write(
        (_chunk("Chế độ nghỉ phép\nNhân viên chính thức được 12 ngày phép có lương mỗi năm."),)
    )
    assert drafted is not None
    assert drafted.query == "Chế độ nghỉ phép là bao nhiêu ngày?"


def test_a_long_prose_line_is_not_mistaken_for_a_heading() -> None:
    """Đối trọng: một câu văn dài KHÔNG được nhận là tiêu đề.

    Thiếu vế này thì luật "dòng ngắn = tiêu đề" nới ra thành "dòng nào cũng là tiêu đề", và ta quay
    về đúng khuôn cũ — câu hỏi là nguyên văn tài liệu."""
    cau_van = (
        "Công ty cam kết xây dựng môi trường làm việc chuyên nghiệp, minh bạch và tôn trọng "
        "sự khác biệt của mỗi cá nhân trong tổ chức."
    )
    assert TemplateQuestionWriter().write((_chunk(f"{cau_van}\nMức thưởng là 5.000.000 đồng."),)) is None


def test_expected_stops_at_a_comma_instead_of_crossing_into_the_next_clause() -> None:
    """Dấu phẩy là mốc dừng, ngang hàng dấu chấm.

    Đo được trên một lượt chấm thật: `expected` sinh ra là `"3 ngày, phải uỷ quyền bằng văn"` —
    vắt qua dấu phẩy sang mệnh đề sau rồi bị trần token cắt cụt giữa chừng. Agent trả lời ĐÚNG
    (*"Uỷ quyền phải được thực hiện bằng văn bản khi người có thẩm quyền vắng mặt trên 3 ngày"*) mà
    vẫn bị chấm sai, vì nấc 1 khớp token LIỀN NHAU và cụm kỳ vọng đó không tồn tại nguyên vẹn trong
    bất kỳ câu trả lời tự nhiên nào.

    Dấu phẩy trong SỐ (`50.000.000`, `1,5`) không tính — cùng luật với dấu chấm phân cách hàng
    nghìn."""
    drafted = TemplateQuestionWriter().write(
        (_chunk("## Uỷ quyền phê duyệt\nKhi vắng mặt trên 3 ngày, phải uỷ quyền bằng văn bản."),)
    )
    assert drafted is not None
    assert drafted.expected == "3 ngày"


def test_a_comma_inside_a_number_is_not_a_stop() -> None:
    """Đối trọng: `1,5` là một con số, không phải hai mệnh đề."""
    drafted = TemplateQuestionWriter().write((_chunk("## Hệ số làm thêm\nÁp dụng 1,5 lần lương giờ."),))
    assert drafted is not None
    assert drafted.expected.startswith("1,5")


def test_a_parenthesis_ends_the_expected_span() -> None:
    """Ngoặc mở là một mệnh đề mới ⇒ mốc dừng.

    Đo được: `"2 lần/năm (tháng 4 và tháng"` và `"7 ngày (nội địa) hoặc 14 ngày"` — cả hai bị trần
    token cắt cụt GIỮA ngoặc, thành cụm không tồn tại trong bất kỳ câu trả lời nào. Agent trả lời
    đúng cả hai mà vẫn bị chấm sai."""
    writer = TemplateQuestionWriter()
    a = writer.write((_chunk("## Chu kỳ dự báo\nAnkor dự báo 2 lần/năm (tháng 4 và tháng 8)."),))
    b = writer.write((_chunk("## Phê duyệt công tác\nNộp trước 7 ngày (nội địa) hoặc 14 ngày (quốc tế)."),))
    # `"2 lần"` chứ không phải `"2 lần/năm"`: gạch chéo giữa hai đơn vị cũng là mốc dừng — xem
    # `test_expected_stops_at_a_slash_between_units`.
    assert a is not None and a.expected == "2 lần"
    assert b is not None and b.expected == "7 ngày"


def test_expected_does_not_trail_off_into_a_preposition() -> None:
    """Cụm kỳ vọng không được kết thúc bằng giới từ treo.

    Đo được: `"5 ngày sau khi về"` — agent trả lời *"trong vòng 5 ngày sau khi nhân viên quay về"*,
    đúng hoàn toàn, nhưng cụm kỳ vọng không tồn tại nguyên vẹn ở đó. Càng nhiều token đuôi càng
    nhiều cơ hội lệch cách diễn đạt, trong khi phần mang thông tin luôn là số + đơn vị."""
    drafted = TemplateQuestionWriter().write(
        (_chunk("## Báo cáo sau công tác\nNộp trong vòng 5 ngày sau khi nhân viên quay về."),)
    )
    assert drafted is not None
    assert drafted.expected == "5 ngày"


def test_a_quantity_far_below_its_heading_is_not_used_as_the_answer() -> None:
    """Đại lượng phải nằm GẦN tiêu đề đã đặt ra câu hỏi.

    Đo được sai lệch tệ nhất: câu hỏi *"PR từ 5–50 triệu là bao nhiêu?"* nhận đáp án
    `"50–200 triệu: tối thiểu 3 báo giá"` — của một khoảng KHÁC. Tiêu đề được cập nhật ở một dòng,
    còn đại lượng khớp được mãi mấy dòng sau, và không gì ràng hai thứ đó lại với nhau. Đây là loại
    sai nguy hiểm hơn cả cụm dài: câu hỏi và đáp án đều đọc trôi chảy, chỉ có điều chúng nói về hai
    thứ khác nhau."""
    drafted = TemplateQuestionWriter().write(
        (
            _chunk(
                "## Số báo giá\n"
                "PR từ 5–50 triệu: tối thiểu hai báo giá.\n"
                "PR từ 50–200 triệu: tối thiểu ba báo giá.\n"
                "Hồ sơ lưu 7 năm theo quy định."
            ),
        )
    )
    # Không có đại lượng nào khớp gần tiêu đề ⇒ thà bỏ qua còn hơn ghép nhầm.
    assert drafted is None


def test_a_day_of_month_is_not_a_quantity_of_months() -> None:
    """`ngày 15 của tháng` là một MỐC lịch, không phải "15 tháng".

    Đo được: câu hỏi *"Báo cáo dự báo là bao nhiêu tháng?"* với đáp án `"15 tháng dự báo"`, sinh từ
    câu *"gửi trước ngày 15 của tháng dự báo"*. Cùng lớp lỗi với `31/03` — một con số đứng cạnh đơn
    vị thời gian không tự động là một lượng thời gian."""
    drafted = TemplateQuestionWriter().write(
        (_chunk("## Báo cáo dự báo\nBáo cáo gửi trước ngày 15 của tháng dự báo."),)
    )
    assert drafted is None


def test_a_labelled_line_answers_only_from_its_own_clause() -> None:
    """Dòng `Nhãn: giá trị` chỉ được lấy đáp án trong **mệnh đề của chính nó**.

    Đo được sai lệch tệ nhất còn lại: *"PR từ 5–50 triệu là bao nhiêu?"* nhận đáp án
    `"50–200 triệu: tối thiểu"` — của khoảng KHÁC nằm cùng dòng sau dấu chấm phẩy. Câu hỏi và đáp án
    đều đọc trôi chảy, chỉ có điều chúng nói về hai thứ khác nhau; không con số tổng nào lộ ra lỗi
    này."""
    drafted = TemplateQuestionWriter().write(
        (_chunk("## Số báo giá\nPR từ 5–50 triệu: tối thiểu 2 báo giá; PR từ 50–200 triệu: tối thiểu 3 báo giá."),)
    )
    # Mệnh đề đầu không có đại lượng nào khớp ("báo giá" không phải đơn vị) ⇒ thà bỏ qua.
    assert drafted is None


def test_a_colon_ends_the_expected_span() -> None:
    """Dấu hai chấm mở ra một vế mới ⇒ mốc dừng, ngang hàng dấu chấm và dấu phẩy.

    Dựng cảnh trên một dòng `Nhãn: giá trị` (đường duy nhất còn lại có dấu hai chấm sau khi dòng
    kiểu đó không rơi xuống cách xử lý dòng thường nữa) — phần giá trị mang đại lượng rồi mới tới
    dấu hai chấm thứ hai."""
    drafted = TemplateQuestionWriter().write((_chunk("- **Hạn mức**: 200 triệu: cần thêm phê duyệt của giám đốc."),))
    assert drafted is not None
    assert drafted.expected == "200 triệu"


def test_expected_stops_at_a_slash_between_units() -> None:
    """Gạch chéo giữa hai đơn vị là mốc dừng: `2 lần/năm` → `2 lần`.

    Tài liệu viết tắt bằng gạch chéo (`2 lần/năm`, `30 ngày/năm`, `1.500.000 VNĐ/tháng`), còn agent
    đọc ra thành chữ (*"2 lần một năm"*, *"2 lần mỗi năm"*). Nấc 1 khớp token LIỀN NHAU nên hai cách
    viết đó không bao giờ gặp nhau — đo được một case trả lời hoàn toàn đúng vẫn bị chấm sai chỉ vì
    dấu `/`.

    Bỏ vế sau gạch chéo làm mất thông tin "trên mỗi năm", và đó là đánh đổi có ý thức: phần MANG
    THÔNG TIN vẫn là con số, còn tỷ suất thì mỗi người viết một kiểu."""
    writer = TemplateQuestionWriter()
    a = writer.write((_chunk("## Chu kỳ dự báo\nAnkor dự báo 2 lần/năm."),))
    b = writer.write((_chunk("## Trợ cấp đi lại\nCông ty trả 1.500.000 VNĐ/tháng."),))
    assert a is not None and a.expected == "2 lần"
    assert b is not None and b.expected == "1.500.000 VNĐ"


def test_expected_does_not_keep_a_dangling_closing_bracket() -> None:
    """`VAT (10%)` ⇒ `10%`, không phải `10%)`.

    Cụm bắt đầu GIỮA ngoặc nên dấu đóng nằm lại ở cuối. Nấc 1 khớp token liền nhau, mà không câu trả
    lời tự nhiên nào viết `10%)` — nên case đó trượt bất kể agent trả lời đúng hay sai. Đo được trên
    một lượt chấm thật, và nó kéo cả `success_rate` lẫn `citation_accuracy` xuống dưới ngưỡng
    publish trên một bộ chỉ 13 case."""
    drafted = TemplateQuestionWriter().write(
        (_chunk("## Thuế suất\nHoá đơn bán hàng chịu thuế GTGT (10%) theo quy định."),)
    )
    assert drafted is not None
    assert drafted.expected == "10%"


def test_every_heading_in_a_chunk_yields_a_question() -> None:
    """Một chunk chứa nhiều mục ⇒ nhiều câu hỏi, không phải một.

    `cut_window` cắt theo SỐ TỪ (200 từ/chunk), nên một tài liệu quy định gọn nằm trọn trong một
    chunk dù có mười mục. Bộ soạn dừng ở mục đầu tiên biến mười mục đó thành đúng **một** case —
    đo được trên hệ thật: tài liệu 10 tiêu đề, upload xong ra bộ golden 2 case, không đủ để chấm
    bất cứ thứ gì."""
    chunk = _chunk(
        "## Nghỉ phép năm\nNhân viên được 12 ngày phép có lương.\n\n"
        "## Thử việc\nThời gian thử việc là 2 tháng.\n\n"
        "## Trợ cấp đi lại\nHỗ trợ 500.000 đồng mỗi tháng."
    )
    drafts = TemplateQuestionWriter().write_all((chunk,))

    assert len(drafts) == 3
    assert {d.topic for d in drafts} == {"Nghỉ phép năm", "Thử việc", "Trợ cấp đi lại"}


def test_the_same_topic_twice_yields_one_question() -> None:
    """Chunk chồng lấn (`cut_window` có overlap) lặp lại cùng tiêu đề ⇒ chỉ một câu hỏi.

    Thiếu khử trùng, một tài liệu dài sinh ra hàng loạt case hỏi đúng cùng một chuyện, và
    `success_rate` thành phép đo trên một câu hỏi được đếm nhiều lần."""
    a = _chunk("## Nghỉ phép năm\nNhân viên được 12 ngày phép.", chunk_id="d#c1")
    b = _chunk("## Nghỉ phép năm\nNhân viên được 12 ngày phép.", chunk_id="d#c2")
    assert len(TemplateQuestionWriter().write_all((a, b))) == 1


def test_quy_trinh_is_not_the_unit_quy() -> None:
    """`Quy trình`/`Quy định`/`Quy chế` KHÔNG phải đơn vị `quý`.

    Phép khớp đơn vị chạy trên bản đã BỎ DẤU (để đọc được tài liệu gõ không dấu), và bỏ dấu biến
    `quý` → `quy`. Mà `quy` cũng là `Quy` trong `Quy trình` — từ có mặt ở gần như mọi tài liệu quy
    định nội bộ.

    Đo được trên bộ thật: `"4.1 Nguyên tắc Tuyển dụng Nhân tài là bao nhiêu quý?"` với đáp án
    `"4.2 Quy trình Tuyển"` — cả câu hỏi lẫn đáp án đều vô nghĩa, và cả hai đọc trôi chảy."""
    assert TemplateQuestionWriter().write((_chunk("## Tuyển dụng\n4.2 Quy trình Tuyển dụng gồm năm bước."),)) is None


def test_a_section_number_is_not_a_quantity() -> None:
    """`3.3`, `9.2` là SỐ MỤC, không phải đại lượng.

    Cùng lớp lỗi với `31/03` và `ngày 15`: một con số đứng cạnh chữ không tự động là một lượng. Số
    mục đứng ở ĐẦU dòng, ngay trước phần chữ của tiêu đề."""
    assert (
        TemplateQuestionWriter().write((_chunk("## Chương 3\n3.3 Chính sách Hybrid Work & Work From Home."),)) is None
    )


def test_a_numbered_heading_loses_its_number_in_the_question() -> None:
    """Số mục bị gỡ khỏi câu hỏi: hỏi *"3.3 Chính sách làm việc từ xa là bao nhiêu ngày?"* đọc như
    một lỗi đánh máy, và số mục không phải thứ người trả lời cần biết."""
    drafted = TemplateQuestionWriter().write(
        (_chunk("## 3.3 Chính sách làm việc từ xa\nNhân viên được làm từ xa 2 ngày mỗi tuần."),)
    )
    assert drafted is not None
    assert drafted.query == "Chính sách làm việc từ xa là bao nhiêu ngày?"


def test_a_document_written_without_diacritics_still_matches_quarters() -> None:
    """Đối trọng: tài liệu gõ KHÔNG DẤU vẫn phải khớp được `quy` = `quý`.

    Đây là lý do phép khớp bỏ dấu tồn tại. Chặn `quy` vô điều kiện sẽ sửa một nhóm tài liệu bằng
    cách làm hỏng nhóm còn lại — nên phải phân biệt theo việc DÒNG ĐÓ có dấu hay không."""
    drafted = TemplateQuestionWriter().write((_chunk("## Danh gia hieu suat\nDien ra 2 quy mot lan."),))
    assert drafted is not None
    assert drafted.expected.startswith("2 quy")


def test_a_money_amount_at_the_start_of_a_line_is_not_a_section_number() -> None:
    """`50.000.000` đứng đầu dòng là SỐ TIỀN, không phải số mục.

    Hai thứ cùng hình dạng `chữ số . chữ số . chữ số`. Phân biệt bằng độ dài nhóm: dấu phân cách
    hàng nghìn luôn đúng 3 chữ số, số mục thì không (`3.3`, `9.2`, `11.1`). Thiếu ràng buộc đó thì
    mọi dòng mở đầu bằng số tiền bị che mất và đọc thành 'không có đại lượng'."""
    drafted = TemplateQuestionWriter().write((_chunk("## Hạn mức nội trú\n50.000.000 VNĐ mỗi năm."),))
    assert drafted is not None
    assert drafted.expected.startswith("50.000.000")
