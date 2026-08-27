"""Trích text thuần từ file upload/crawl (`.md`/`.txt`/`.docx`) — tầng ĐẦU của pipeline "tự do",
đứng trước `chunk_window.cut_window`. Cố ý CHỈ `.docx` (XML/zip, đọc được thuần Python qua
`python-docx`), KHÔNG `.doc` nhị phân cũ (Word 97-2003) — định dạng đó cần công cụ ngoài
(LibreOffice headless/`antiword`), không portable qua CI, để riêng ngoài phạm vi (xem
`plans/multiformat_chunker_plan.md`)."""

from __future__ import annotations

import io

from docx import Document

SUPPORTED_SUFFIXES = frozenset({".md", ".txt", ".docx"})
"""Public — `apps/studio/routes/documents.py` import trực tiếp để validate đuôi file phía route,
tránh chép lại danh sách này ở 2 nơi (một nguồn sự thật, đúng nguyên tắc `FIXTURE_REF`/`_UPSERT`)."""


class UnsupportedFormatError(ValueError):
    """`raw` không dùng được: đuôi ngoài `SUPPORTED_SUFFIXES`, hoặc đúng đuôi nhưng nội dung không
    đọc được như định dạng đó (`.docx` hỏng, `.md`/`.txt` không phải UTF-8). Một kiểu lỗi DUY NHẤT
    cho cả hai vế là cố ý: bên gọi (`routes/documents.py`) chỉ cần một `except` để trả 422, và mọi
    thất bại ở tầng này đều cùng một nghĩa — "file người dùng đưa lên không xài được", không phải
    lỗi server."""


class DocumentTooLongError(ValueError):
    """Tài liệu vượt hạn mức SỐ TỪ, phát hiện ngay TRONG lúc trích.

    Tách khỏi `UnsupportedFormatError`: file hoàn toàn hợp lệ, chỉ là quá dài — gộp hai thứ lại thì
    người dùng nhận thông điệp "không đọc được như .docx" cho một file đọc được rất tốt."""

    def __init__(self, max_words: int) -> None:
        super().__init__(f"tài liệu vượt {max_words} từ")
        self.max_words = max_words


def extract_text(filename: str, raw: bytes, *, max_words: int | None = None) -> str:
    """Trả text thuần từ `raw` theo đuôi `filename`. Raise `UnsupportedFormatError` cho đuôi lạ
    (kể cả `.doc`) — im lặng đoán định dạng từ nội dung là nguồn lỗi khó lần, không phải tiện lợi.

    `max_words` cưỡng chế **trong lúc trích**, không phải sau. Lý do là `.docx` nén: số byte KHÔNG
    chặn được lượng chữ. Đo trên hạn mức 1 MiB — `.txt` thuần ~168.000 từ, `.docx` nội dung lặp
    ~**14.400.000** từ. Nâng hạn mức byte lên 10 MiB là scale con số đó lên ~144 triệu từ ≈ ~1 GB
    chuỗi, mà bản trước dựng TOÀN BỘ chuỗi trong bộ nhớ rồi mới để caller đếm.

    `None` (mặc định) ⇒ không chặn, nên mọi call-site cũ không đổi một dòng."""
    suffix = _suffix(filename)
    if suffix not in SUPPORTED_SUFFIXES:
        raise UnsupportedFormatError(
            f"{filename!r}: đuôi {suffix!r} không hỗ trợ — chỉ chấp nhận {sorted(SUPPORTED_SUFFIXES)}"
        )
    if suffix == ".docx":
        return _extract_docx(raw, filename, max_words)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise UnsupportedFormatError(f"{filename!r}: không phải UTF-8 hợp lệ: {exc}") from exc
    # `.md`/`.txt` có byte tỉ lệ với chữ nên nguy cơ thấp hơn `.docx`, nhưng hai đường đi qua CÙNG
    # một hàm và cùng một cổng — chỉ chặn một bên là để lại một cửa mở mà không ai nhớ vì sao mở.
    if max_words is not None and len(text.split()) > max_words:
        raise DocumentTooLongError(max_words)
    return text


def _suffix(filename: str) -> str:
    dot = filename.rfind(".")
    return filename[dot:].lower() if dot >= 0 else ""


def _extract_docx(raw: bytes, filename: str, max_words: int | None = None) -> str:
    """Nối text từng paragraph bằng `\\n` — KHÔNG giữ heading style (bold/size/…): tầng cutter phía
    sau (`chunk_window.cut_window`) không phân biệt heading, nên giữ style ở đây vô nghĩa, chỉ tổ
    làm text nhiễu thêm ký hiệu không ai đọc.

    Mọi thất bại lúc mở/parse gói quy về `UnsupportedFormatError` (→ 422), KHÔNG để thoát nguyên
    dạng ra ngoài (→ 500): `raw` là bytes NGƯỜI DÙNG đưa lên nên hỏng là đường đi thường, không
    phải ca hiếm — thao tác điển hình là bị báo "chỉ nhận .md/.txt/.docx" rồi đổi thẳng đuôi
    `.doc`/`.pdf` thành `.docx`.

    Bắt RỘNG (`Exception`) là chủ đích, không phải lười: đo thật 5 kiểu hỏng cho ra 3 họ exception
    rời nhau — `zipfile.BadZipFile` (không phải zip), `KeyError` (zip hợp lệ, thiếu part OOXML),
    `lxml.etree.XMLSyntaxError` (`word/document.xml` rúng) — và KHÔNG cái nào là `ValueError`.
    Liệt kê tay một bộ hẹp chính là cách đã sinh ra lỗi này, và nó sẽ hỏng lại ở kiểu thứ 6 mà
    `python-docx`/`lxml` ném ra sau một lần nâng phiên bản. Nguyên nhân gốc giữ trong `__cause__`
    (`raise … from exc`) nên log server không mất gì."""
    try:
        document = Document(io.BytesIO(raw))
        # Gom từng paragraph và ĐẾM DẦN, thay vì `"\n".join(...)` một phát: dừng ngay khi vượt hạn
        # mức là điểm khác biệt duy nhất giữa một giới hạn và một lỗ nuốt bộ nhớ. `.docx` nén, nên
        # tới lúc caller đếm được thì chuỗi đã nằm trọn trong RAM rồi.
        parts: list[str] = []
        seen = 0
        for paragraph in document.paragraphs:
            parts.append(paragraph.text)
            if max_words is not None:
                seen += len(paragraph.text.split())
                if seen > max_words:
                    raise DocumentTooLongError(max_words)
        return "\n".join(parts)
    except DocumentTooLongError:
        # Không nuốt vào nhánh `UnsupportedFormatError` bên dưới: file đọc được rất tốt, chỉ là quá
        # dài, và hai thông điệp đó dẫn người dùng đi hai hướng khác hẳn nhau.
        raise
    except Exception as exc:
        raise UnsupportedFormatError(
            f"{filename!r}: không đọc được như .docx ({type(exc).__name__}) — file hỏng hoặc chỉ "
            f"được đổi đuôi từ định dạng khác: {exc}"
        ) from exc
