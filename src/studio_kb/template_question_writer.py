"""Sinh câu hỏi golden theo **mẫu**, đọc cấu trúc Markdown của tài liệu.

## Vì sao thay `ExtractiveQuestionWriter`

Bản cũ dựng `query` bằng cách bọc nguyên văn chunk vào một khuôn cố định, và lấy chính đoạn văn đó
làm `expected`. Đo trên một bộ thật (`kb-hr-auto-v1`, 20 case):

    19/19 câu hỏi bắt đầu bằng "Tài liệu nói gì về: " + nguyên văn chunk
    19/19 `expected` là đoạn cắt ra từ chính câu hỏi
    độ dài `expected` trung vị: 102 ký tự

Ba con số đó nói cùng một chuyện: bộ chấm đang đòi agent **đọc lại nguyên văn tài liệu**, chứ không
đòi nó trả lời. Nấc 1 của bộ chấm khớp bằng chuỗi token LIỀN NHAU (`_contains_phrase`), nên một
`expected` dài 102 ký tự chỉ đúng khi agent chép lại gần như từng chữ — điều một câu trả lời tốt
không bao giờ làm.

## Nguyên tắc: thà bỏ qua còn hơn bịa

`write()` trả `None` khi không mẫu nào khớp. Đó là điểm khác biệt lớn nhất so với bản cũ (luôn sinh
được, vì khuôn của nó không cần hiểu gì cả). Năm case đúng hữu ích hơn hai mươi case đòi chép lại
tài liệu: bộ sau khiến `success_rate` thấp bất kể agent tốt đến đâu, và một cổng luôn đỏ thì không
còn là cổng.

## Mẫu nào

Tài liệu quy định nội bộ gần như luôn có cùng một hình dạng: **một tiêu đề nêu chủ đề, một câu trong
thân bài mang con số là đáp án**.

    ## Nghỉ phép năm
    Nhân viên chính thức được 12 ngày phép có lương.

    → query    "Nghỉ phép năm là bao nhiêu ngày?"
    → expected "12 ngày phép có lương"

`expected` bắt đầu **ngay tại con số** và kéo về sau tối đa `_MAX_EXPECTED_TOKENS` token, dừng ở dấu
câu. Chọn mốc neo là con số vì đó là phần một câu trả lời đúng chắc chắn phải nhắc tới, còn phần dẫn
trước nó ("Nhân viên chính thức được…") thì mỗi cách diễn đạt một khác.
"""

from __future__ import annotations

import re
import unicodedata

from studio_kb.golden_from_kb import DraftedQuestion, SourceChunk

# Trần token của `expected`, tính CẢ token chứa con số.
#
# Nấc 1 khớp bằng token liền nhau, nên mỗi token thêm vào là một cơ hội nữa để câu trả lời ĐÚNG bị
# chấm sai chỉ vì diễn đạt khác. Đo được ở mức 7: agent trả lời *"trong vòng 5 ngày sau khi nhân
# viên quay về"* — đúng hoàn toàn — mà cụm kỳ vọng `"5 ngày sau khi về"` không tồn tại nguyên vẹn
# trong đó. Bốn ca như vậy trên một lượt 15 case.
#
# 4 giữ được phần MANG THÔNG TIN (số + đơn vị + một bổ nghĩa) và bỏ phần diễn đạt: `50.000.000
# VNĐ/năm`, `12 ngày phép`, `30 ngày/năm`. Ngắn hơn thì `50.000.000` một mình khớp mọi câu tình cờ
# nhắc con số đó; dài hơn thì mua thêm rủi ro lệch cách nói mà không mua thêm sức phân biệt.
_MAX_EXPECTED_TOKENS = 4

# Trần độ dài chủ đề rút từ tiêu đề. Tiêu đề dài hơn mức này gần như luôn là một câu văn bị bắt nhầm
# thành tiêu đề, và nhét nguyên nó vào câu hỏi sẽ tái lập đúng lỗi của bản cũ.
_MAX_TOPIC_CHARS = 60

# Số dòng thân bài tối đa còn được coi là "thuộc về" tiêu đề phía trên. 2 vì tài liệu quy định gần
# như luôn đặt con số ở câu đầu hoặc câu thứ hai sau tiêu đề; xa hơn thế thì nó đang nói sang chuyện
# khác, và ghép nó vào câu hỏi của tiêu đề là dựng một cặp hỏi-đáp lệch nhau.
_MAX_LINES_FROM_TOPIC = 2

_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+(?P<text>.+?)\s*#*\s*$")
# `.docx` không có `#`: `extract._extract_docx` nối paragraph bằng `\n`, nên cấu trúc còn ở dạng
# DÒNG nhưng dấu hiệu Markdown thì không. Tiêu đề Word nhìn từ text thuần là một dòng NGẮN, không
# kết bằng dấu câu — nhận thêm hình dạng đó, nếu không toàn bộ tài liệu Word bị bỏ trắng.
#
# Ràng buộc "không dấu câu kết" là thứ giữ luật này khỏi nới thành "dòng nào cũng là tiêu đề": một
# câu văn ngắn vẫn kết bằng `.`, còn tiêu đề thì không. Cộng với trần `_MAX_TOPIC_CHARS`, hai điều
# kiện cùng lúc mới đủ.
_BARE_HEADING = re.compile(rf"^\s*(?P<text>\S[^\n]{{2,{_MAX_TOPIC_CHARS}}}?)\s*$")
# Dòng "Nhãn: giá trị" cũng là tiêu đề trên thực tế — rất nhiều tài liệu nội bộ dùng nó thay heading.
_LABELLED_LINE = re.compile(r"^\s*[-*•]?\s*\*{0,2}(?P<label>[^:*\n]{3,60}?)\*{0,2}\s*:\s+(?P<body>\S.*)$")

_NUMBER = r"\d[\d.,]*"

# Đơn vị chia theo HỌ, vì mỗi họ nhận một đuôi câu hỏi khác nhau. Một danh sách phẳng sẽ buộc mọi câu
# hỏi dùng chung đuôi "là bao nhiêu?", và câu đó nghe sai với đơn vị thời gian.
_TIME_UNITS = ("ngày", "tuần", "tháng", "năm", "giờ", "phút", "quý")
_MONEY_UNITS = ("VNĐ", "VND", "đồng", "triệu", "nghìn", "tỷ", "USD")
_RATE_UNITS = ("%", "phần trăm")
_COUNT_UNITS = ("lần", "người", "nhân viên", "suất", "chỗ")

_ALL_UNITS = _TIME_UNITS + _MONEY_UNITS + _RATE_UNITS + _COUNT_UNITS


def _strip_diacritics(text: str) -> str:
    """Bỏ dấu tiếng Việt, GIỮ NGUYÊN độ dài chuỗi.

    Độ dài là điều kiện bắt buộc, không phải chi tiết: mọi `start()`/`end()` của regex chạy trên bản
    đã bỏ dấu đều được dùng để cắt trên chuỗi GỐC (`_expected_from`). Lệch một ký tự là `expected`
    cắt sai chỗ.

    Ký tự tiếng Việt dựng sẵn là một code point, nên NFD tách ra rồi bỏ dấu kết hợp cho lại đúng một
    ký tự — trừ `đ`/`Đ` (không có dấu kết hợp để tách), phải map tay.

    Cần vì tài liệu gõ không dấu là hình dạng có thật: chính fixture của repo viết *"12 ngay phep"*.
    Khớp đơn vị theo đúng chuỗi có dấu sẽ bỏ trắng cả nhóm tài liệu đó mà không báo gì — "không soạn
    được" là kết quả hợp lệ, nên nó không nổi lên thành lỗi ở đâu cả."""
    folded = "".join("d" if ch == "đ" else "D" if ch == "Đ" else unicodedata.normalize("NFD", ch)[0] for ch in text)
    assert len(folded) == len(text)
    return folded


# Con số phải ĐI KÈM đơn vị trong vòng 2 token, nếu không "3." của một danh sách đánh số cũng thành
# đáp án. Đây là chỗ phân biệt "một con số" với "một đại lượng".
# Mẫu chạy trên bản ĐÃ BỎ DẤU của dòng, nên danh sách đơn vị cũng phải bỏ dấu — và phải khử trùng
# lặp giữ thứ tự, vì bỏ dấu làm vài đơn vị trùng nhau.
_FOLDED_UNITS = tuple(dict.fromkeys(_strip_diacritics(u) for u in _ALL_UNITS))
# Đường về: mẫu bắt được đơn vị ở dạng ĐÃ BỎ DẤU, nhưng câu hỏi phải viết CÓ DẤU. Không có bảng này
# thì tài liệu gõ chuẩn cũng ra "… là bao nhiêu ngay?" — sửa được một nhóm tài liệu bằng cách làm
# hỏng nhóm còn lại. Ánh xạ đầu tiên thắng, nên `năm` (có dấu) là dạng chuẩn của `nam`.
_CANONICAL_UNIT: dict[str, str] = {}
for _unit in _ALL_UNITS:
    _CANONICAL_UNIT.setdefault(_strip_diacritics(_unit).lower(), _unit)
_QUANTITY = re.compile(
    rf"(?P<value>{_NUMBER})\s*(?:\S+\s+){{0,1}}?(?P<unit>{'|'.join(re.escape(u) for u in _FOLDED_UNITS)})",
    re.IGNORECASE,
)

# Dấu chấm KHÔNG tính là hết câu khi nó nằm giữa hai chữ số: tiếng Việt dùng `.` làm dấu phân cách
# hàng nghìn, nên `50.000.000 VNĐ/năm` bị cắt ngay sau `50` nếu bỏ ràng buộc này — `expected` còn
# đúng hai ký tự, và bộ chấm sẽ tính là ĐÚNG cho bất kỳ câu trả lời nào tình cờ chứa số 50.
# Dấu chấm VÀ dấu phẩy đều là mốc dừng, và cả hai đều không tính khi nằm giữa hai chữ số: tiếng
# Việt dùng `.` phân cách hàng nghìn và `,` phân cách thập phân. Bỏ ràng buộc đó thì `50.000.000
# VNĐ` cắt còn `50`, và `1,5 lần` cắt còn `1`.
#
# Vì sao dấu phẩy phải là mốc dừng: `expected` vắt qua dấu phẩy sang mệnh đề sau rồi bị trần token
# cắt cụt giữa chừng — đo được `"3 ngày, phải uỷ quyền bằng văn"`, một cụm không tồn tại nguyên vẹn
# trong bất kỳ câu trả lời tự nhiên nào. Nấc 1 khớp token LIỀN NHAU, nên cụm đó chấm sai cả những
# câu trả lời đúng.
# Ngoặc mở cũng là mốc dừng: một mệnh đề trong ngoặc là chú thích, không phải phần tiếp nối của
# cụm. Không dừng ở đó thì trần token cắt cụt GIỮA ngoặc — đo được `"2 lần/năm (tháng 4 và tháng"`
# và `"7 ngày (nội địa) hoặc 14 ngày"`, hai cụm không tồn tại trong bất kỳ câu trả lời nào.
_SENTENCE_END = re.compile(r"(?<!\d)[.,](?!\d)|[;:!?\n(\[]")

# Ngày tháng KHÔNG phải đại lượng, dù chữ số của nó đứng ngay trước một đơn vị thời gian. `31/03 năm
# kế tiếp` thoả mọi ràng buộc khác (có tiêu đề, có số, có đơn vị) và vẫn sinh ra câu hỏi vô nghĩa
# *"… là bao nhiêu năm?"* với đáp án là một cái MỐC chứ không phải một LƯỢNG.
_DATE_LIKE = re.compile(r"\b\d{1,2}\s*[/-]\s*\d{1,2}(\s*[/-]\s*\d{2,4})?\b")

# `ngày 15 của tháng` là một MỐC lịch, không phải "15 tháng". Cùng lớp lỗi với `31/03`: một con số
# đứng cạnh đơn vị thời gian không tự động là một LƯỢNG thời gian.
#
# Đo được: câu hỏi *"Báo cáo dự báo là bao nhiêu tháng?"* với đáp án `"15 tháng dự báo"`, sinh từ
# câu *"gửi trước ngày 15 của tháng dự báo"* — con số là ngày trong tháng, đơn vị bắt được là từ
# `tháng` nằm mãi phía sau.
# Viết ở dạng ĐÃ BỎ DẤU: `_find_quantity` che mẫu này trên bản đã bỏ dấu của dòng, nên `ngày` ở đây
# phải là `ngay`. Để nguyên dạng có dấu thì mẫu không bao giờ khớp và cả bộ chặn thành vô hiệu —
# đúng loại hỏng im lặng mà một bài test có thật mới bắt được.
_ORDINAL_DATE = re.compile(r"\b(ngay|thang|quy|tuan)\s+\d{1,4}\b", re.IGNORECASE)

# Token CẮT `expected`. Nấc 1 khớp token LIỀN NHAU, nên mỗi từ sau con số là một cơ hội lệch cách
# diễn đạt. Những từ dưới đây mở ra một bổ ngữ — cắt tại đó giữ lại đúng phần mang thông tin:
# `"5 ngày sau khi về"` → `"5 ngày"`, `"12 ngày phép có lương"` → `"12 ngày phép"`.
_STOP_TOKENS = frozenset(
    {
        # liên từ / giới từ
        "và",
        "hoặc",
        "cho",
        "của",
        "với",
        "trong",
        "theo",
        "từ",
        "đến",
        "là",
        "bằng",
        "về",
        # từ nối thời gian — đuôi hay gặp nhất, và cũng là chỗ mỗi người diễn đạt một khác
        "sau",
        "trước",
        "khi",
        "kể",
        "trên",
        "dưới",
        "mỗi",
        "trở",
        # động từ nối
        "có",
        "được",
        "phải",
        "gồm",
        "kèm",
        "tính",
    }
)


def _question_tail(unit: str, topic: str) -> str:
    """Đuôi câu hỏi theo HỌ đơn vị — nhưng bỏ đơn vị nếu chủ đề đã mang nó.

    *"Mục tiêu 30-60-90 ngày là bao nhiêu ngày?"* là câu tự vấp vào chính nó; *"… là bao nhiêu?"*
    hỏi đúng cùng một chuyện mà đọc được."""
    lowered = unit.lower()
    # Viết lại đơn vị về dạng CÓ DẤU cho câu hỏi; phép so khớp bên dưới vẫn chạy trên dạng bỏ dấu.
    spelled = _CANONICAL_UNIT.get(lowered, unit).lower()
    if lowered in _strip_diacritics(topic).lower():
        return "là bao nhiêu?"
    if lowered in {_strip_diacritics(u).lower() for u in _TIME_UNITS}:
        return f"là bao nhiêu {spelled}?"
    if lowered in {_strip_diacritics(u).lower() for u in _RATE_UNITS}:
        return "là bao nhiêu phần trăm?"
    if lowered in {_strip_diacritics(u).lower() for u in _COUNT_UNITS}:
        return f"là bao nhiêu {spelled}?"
    return "là bao nhiêu?"


def _find_quantity(line: str) -> re.Match[str] | None:
    """Đại lượng đầu tiên KHÔNG nằm trong một cụm ngày tháng.

    Che ngày tháng bằng khoảng trắng cùng độ dài thay vì xoá: mọi `start()`/`end()` trả về sau đó vẫn
    trỏ đúng vị trí trong dòng GỐC, nên `_expected_from` cắt được từ chính dòng đó."""
    masked = _DATE_LIKE.sub(lambda m: " " * len(m.group(0)), _strip_diacritics(line))
    masked = _ORDINAL_DATE.sub(lambda m: " " * len(m.group(0)), masked)
    return _QUANTITY.search(masked)


def _clean_topic(raw: str) -> str | None:
    """Rút chủ đề từ một dòng tiêu đề. `None` nếu dòng đó không dùng làm chủ đề được."""
    topic = raw.strip().strip("#").strip()
    topic = re.sub(r"^[-*•]\s*", "", topic)
    topic = topic.replace("**", "").replace("__", "").strip().rstrip(":").strip()
    if not topic or len(topic) > _MAX_TOPIC_CHARS:
        return None
    # Tiêu đề toàn chữ HOA là kiểu trình bày của trang bìa ("CẨM NANG NỘI QUY VÀ VĂN HÓA…") — nó nêu
    # tên tài liệu chứ không nêu chủ đề của một quy định, nên câu hỏi dựng từ nó không hỏi gì cả.
    if topic.isupper():
        return None
    return topic


def _expected_from(line: str, match: re.Match[str]) -> str:
    """Đoạn token liền nhau bắt đầu tại con số, dừng ở dấu câu hoặc trần token.

    Sau khi cắt còn phải **gọt đuôi**: cắt ở trần token hay để lại đúng một token vô nghĩa — một liên
    từ (`… cho nội trú và`) hoặc một con số chưa kịp có đơn vị (`… và 15.000.000`). Cả hai làm cụm
    gần như không bao giờ khớp câu trả lời thật, mà lỗi thì không lộ ra ở đâu ngoài `success_rate`."""
    tail = line[match.start("value") :]
    stop = _SENTENCE_END.search(tail)
    clause = tail[: stop.start()] if stop else tail

    # Gạch chéo giữa hai đơn vị (`2 lần/năm`, `1.500.000 VNĐ/tháng`) là mốc dừng: tài liệu viết
    # tắt như vậy, còn agent đọc ra thành chữ (*"2 lần một năm"*). Nấc 1 khớp token LIỀN NHAU nên
    # hai cách viết đó không bao giờ gặp nhau. Chỉ cắt khi hai bên gạch chéo đều là CHỮ — `5/2024`
    # hay `1/2` là một giá trị, không phải hai đơn vị.
    unit_slash = re.search(r"(?<=[^\W\d_])/(?=[^\W\d_])", clause)
    if unit_slash:
        clause = clause[: unit_slash.start()]

    tokens: list[str] = []
    for index, token in enumerate(clause.split()):
        # Cắt tại từ nối ĐẦU TIÊN, không phải gọt đuôi. Gọt đuôi chỉ bỏ token cuối nên vẫn để lại
        # mảnh cụt (`"7 năm theo quy"`); cắt tại từ nối giữ đúng phần mang thông tin (`"7 năm"`).
        # Không cắt ở token đầu: nó là chính con số đã neo cả cụm.
        if index > 0 and token.strip(",.").lower() in _STOP_TOKENS:
            break
        if index >= _MAX_EXPECTED_TOKENS:
            break
        tokens.append(token)
    # Token số cuối chưa kịp có đơn vị là mảnh cụt (`"... và 15.000.000"`); bỏ đi.
    while len(tokens) > 1 and tokens[-1][0].isdigit():
        tokens.pop()
    # Gọt ngoặc đóng còn sót: cụm bắt đầu GIỮA ngoặc (`VAT (10%)` → span mở tại `10`) nên dấu đóng
    # nằm lại ở cuối. `"10%)"` không xuất hiện trong bất kỳ câu trả lời tự nhiên nào, nên case đó
    # trượt bất kể agent đúng hay sai.
    return " ".join(tokens).strip().rstrip(",").rstrip(")]}")


def _draft_all_from_chunk(chunk: SourceChunk) -> list[DraftedQuestion]:
    """Quét một chunk và sinh **mọi** cặp hỏi-đáp trong đó, không dừng ở cặp đầu tiên.

    `cut_window` cắt theo SỐ TỪ (200 từ/chunk), nên một tài liệu quy định gọn nằm trọn trong một
    chunk dù có mười mục. Dừng ở mục đầu biến mười mục thành đúng một case — đo được: tài liệu 10
    tiêu đề upload xong ra bộ golden 2 case, không đủ để chấm bất cứ thứ gì.

    Mỗi tiêu đề đóng góp NHIỀU NHẤT một cặp: dòng mang đại lượng đầu tiên dưới nó. Các dòng sau
    thuộc cùng mục nên câu hỏi dựng từ chúng sẽ trùng chủ đề, và `expected_citation` (đúng một
    `chunk_id`) không phân biệt được chúng."""
    drafts: list[DraftedQuestion] = []
    seen_topics: set[str] = set()
    topic: str | None = None
    # Đại lượng phải nằm trong `_MAX_LINES_FROM_TOPIC` dòng kể từ tiêu đề. Không ràng buộc thì tiêu
    # đề được đặt ở một dòng còn đại lượng khớp được mãi mấy dòng sau, và hai thứ nói về hai chuyện
    # khác nhau — đo được: câu hỏi *"PR từ 5–50 triệu là bao nhiêu?"* nhận đáp án của khoảng
    # *50–200 triệu*. Sai kiểu này nguy hiểm hơn cụm dài: cả câu hỏi lẫn đáp án đều đọc trôi chảy.
    lines_since_topic = 0
    for line in chunk.text.splitlines():
        heading = _HEADING.match(line)
        if heading:
            topic = _clean_topic(heading.group("text"))
            lines_since_topic = 0
            continue

        bare = _BARE_HEADING.match(line)
        if bare and not line.rstrip().endswith((".", ",", ";", ":", "!", "?")) and _find_quantity(line) is None:
            bare_topic = _clean_topic(bare.group("text"))
            if bare_topic:
                topic = bare_topic
                lines_since_topic = 0
                continue

        # Đếm cho MỌI dòng không phải tiêu đề, kể cả dòng `Nhãn: giá trị` không sinh case. Bỏ sót
        # chúng thì một danh sách dài nằm giữa tiêu đề và đại lượng vẫn đọc là "kề nhau".
        if topic is not None:
            lines_since_topic += 1
            if lines_since_topic > _MAX_LINES_FROM_TOPIC:
                topic = None

        labelled = _LABELLED_LINE.match(line)
        # Dòng "Nhãn: giá trị" vừa là chủ đề vừa là thân bài — thử khớp đại lượng ngay trong phần giá
        # trị trước, và chỉ khi không có mới hạ nó xuống làm tiêu đề cho các dòng sau.
        if labelled:
            body = labelled.group("body")
            # Chỉ mệnh đề ĐẦU của phần giá trị. Một dòng `Nhãn: giá trị` thường kê nhiều khoảng
            # ngăn bằng `;`, và lấy đại lượng từ mệnh đề sau là gán đáp án của khoảng NÀY cho nhãn
            # của khoảng KIA — đo được: *"PR từ 5–50 triệu là bao nhiêu?"* nhận đáp án của khoảng
            # 50–200 triệu. Cả câu hỏi lẫn đáp án đều đọc trôi chảy nên không con số tổng nào lộ ra.
            clause_end = _SENTENCE_END.search(body)
            first_clause = body[: clause_end.start()] if clause_end else body
            quantity = _find_quantity(first_clause)
            body = first_clause
            label_topic = _clean_topic(labelled.group("label")) if quantity else None
            if quantity and label_topic and label_topic not in seen_topics:
                seen_topics.add(label_topic)
                drafts.append(
                    DraftedQuestion(
                        query=f"{label_topic} {_question_tail(quantity.group('unit'), label_topic)}",
                        expected=_expected_from(body, quantity),
                        source_chunk_id=chunk.chunk_id,
                        topic=label_topic,
                    )
                )
            # Không khớp được ở phần giá trị thì BỎ HẲN dòng — không rơi xuống cách xử lý dòng
            # thường, và cũng không làm tiêu đề cho các dòng sau.
            #
            # Rơi xuống sẽ lấy đại lượng ở vế TRÁI (phần nhãn) làm đáp án cho tiêu đề phía trên:
            # dòng *"PR từ 5–50 triệu: tối thiểu 2 báo giá"* dưới tiêu đề *"Số báo giá"* sinh ra
            # *"Số báo giá là bao nhiêu?"* → `"5–50 triệu"`. Câu hỏi hỏi một đằng, đáp án trả một
            # nẻo, và cả hai đều đọc trôi chảy.
            #
            # Làm tiêu đề cho dòng sau cũng sai theo cách tương tự: một mục danh sách là anh em với
            # dòng kế tiếp, không phải cha của chúng.
            continue

        if topic is None:
            continue
        quantity = _find_quantity(line)
        if quantity and topic not in seen_topics:
            seen_topics.add(topic)
            drafts.append(
                DraftedQuestion(
                    query=f"{topic} {_question_tail(quantity.group('unit'), topic)}",
                    expected=_expected_from(line, quantity),
                    source_chunk_id=chunk.chunk_id,
                    topic=topic,
                )
            )
            # Tiêu đề đã dùng xong: các dòng còn lại thuộc cùng mục, và câu hỏi dựng từ chúng sẽ
            # trùng chủ đề. Bỏ tiêu đề ra để chờ tiêu đề kế tiếp.
            topic = None
    return drafts


class TemplateQuestionWriter:
    """`QuestionWriter` khớp mẫu trên cấu trúc Markdown. Tất định, 0 call mạng.

    Duyệt từng chunk trong lô theo thứ tự và trả về bản nháp ĐẦU TIÊN khớp được — không gộp nhiều
    chunk vào một câu hỏi. Gộp là đúng thứ sinh ra `expected_citation` 7 phần tử ở bản cũ.
    """

    def write_all(self, chunks: tuple[SourceChunk, ...]) -> tuple[DraftedQuestion, ...]:
        """Mọi cặp hỏi-đáp soạn được trong lô, khử trùng theo CHỦ ĐỀ.

        Khử trùng vì `cut_window` cắt cửa sổ TRƯỢT có overlap: cùng một mục xuất hiện ở hai chunk
        liền kề là chuyện bình thường. Không khử thì một tài liệu dài sinh hàng loạt case hỏi đúng
        cùng một chuyện, và `success_rate` thành phép đo trên một câu hỏi được đếm nhiều lần."""
        drafts: list[DraftedQuestion] = []
        seen: set[str] = set()
        for chunk in chunks:
            for drafted in _draft_all_from_chunk(chunk):
                if drafted.topic in seen:
                    continue
                seen.add(drafted.topic)
                drafts.append(drafted)
        return tuple(drafts)

    def write(self, chunks: tuple[SourceChunk, ...]) -> DraftedQuestion | None:
        """Cặp ĐẦU TIÊN soạn được — giữ lại cho `QuestionWriter` cũ và cho test đọc một cặp."""
        drafts = self.write_all(chunks)
        return drafts[0] if drafts else None
