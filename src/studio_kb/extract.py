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
    """Đuôi file không nằm trong `SUPPORTED_SUFFIXES` — fail-closed, không đoán định dạng."""


def extract_text(filename: str, raw: bytes) -> str:
    """Trả text thuần từ `raw` theo đuôi `filename`. Raise `UnsupportedFormatError` cho đuôi lạ
    (kể cả `.doc`) — im lặng đoán định dạng từ nội dung là nguồn lỗi khó lần, không phải tiện lợi."""
    suffix = _suffix(filename)
    if suffix not in SUPPORTED_SUFFIXES:
        raise UnsupportedFormatError(
            f"{filename!r}: đuôi {suffix!r} không hỗ trợ — chỉ chấp nhận {sorted(SUPPORTED_SUFFIXES)}"
        )
    if suffix == ".docx":
        return _extract_docx(raw)
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise UnsupportedFormatError(f"{filename!r}: không phải UTF-8 hợp lệ: {exc}") from exc


def _suffix(filename: str) -> str:
    dot = filename.rfind(".")
    return filename[dot:].lower() if dot >= 0 else ""


def _extract_docx(raw: bytes) -> str:
    """Nối text từng paragraph bằng `\\n` — KHÔNG giữ heading style (bold/size/…): tầng cutter phía
    sau (`chunk_window.cut_window`) không phân biệt heading, nên giữ style ở đây vô nghĩa, chỉ tổ
    làm text nhiễu thêm ký hiệu không ai đọc."""
    document = Document(io.BytesIO(raw))
    return "\n".join(paragraph.text for paragraph in document.paragraphs)
