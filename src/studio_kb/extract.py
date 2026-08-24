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


def extract_text(filename: str, raw: bytes) -> str:
    """Trả text thuần từ `raw` theo đuôi `filename`. Raise `UnsupportedFormatError` cho đuôi lạ
    (kể cả `.doc`) — im lặng đoán định dạng từ nội dung là nguồn lỗi khó lần, không phải tiện lợi."""
    suffix = _suffix(filename)
    if suffix not in SUPPORTED_SUFFIXES:
        raise UnsupportedFormatError(
            f"{filename!r}: đuôi {suffix!r} không hỗ trợ — chỉ chấp nhận {sorted(SUPPORTED_SUFFIXES)}"
        )
    if suffix == ".docx":
        return _extract_docx(raw, filename)
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise UnsupportedFormatError(f"{filename!r}: không phải UTF-8 hợp lệ: {exc}") from exc


def _suffix(filename: str) -> str:
    dot = filename.rfind(".")
    return filename[dot:].lower() if dot >= 0 else ""


def _extract_docx(raw: bytes, filename: str) -> str:
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
        return "\n".join(paragraph.text for paragraph in document.paragraphs)
    except Exception as exc:
        raise UnsupportedFormatError(
            f"{filename!r}: không đọc được như .docx ({type(exc).__name__}) — file hỏng hoặc chỉ "
            f"được đổi đuôi từ định dạng khác: {exc}"
        ) from exc
