"""`extract.extract_text` — trích text thuần từ `.md`/`.txt`/`.docx`, raise cho đuôi khác."""

from __future__ import annotations

import io

import pytest
from docx import Document
from studio_kb.extract import UnsupportedFormatError, extract_text


@pytest.mark.parametrize("suffix", [".md", ".txt"])
def test_md_txt_doc_thang_utf8(suffix: str) -> None:
    text = "Xin chào thế giới, đây là văn bản tiếng Việt có dấu."
    assert extract_text(f"tai-lieu{suffix}", text.encode("utf-8")) == text


def test_md_txt_khong_bien_doi_noi_dung() -> None:
    # Cú pháp markdown giữ nguyên literal — extract KHÔNG parse heading (chunk_window mới xử lý).
    text = "## Heading\nĐoạn văn có `code` và **in đậm**."
    assert extract_text("doc.md", text.encode("utf-8")) == text


def test_utf8_khong_hop_le_raise() -> None:
    with pytest.raises(UnsupportedFormatError):
        extract_text("doc.txt", b"\xff\xfe\x00\x01khong-phai-utf8")


@pytest.mark.parametrize("filename", ["doc.doc", "doc.pdf", "doc", "doc.MD.exe"])
def test_duoi_file_khong_ho_tro_raise(filename: str) -> None:
    with pytest.raises(UnsupportedFormatError):
        extract_text(filename, b"noi dung gi cung duoc")


def test_duoi_hoa_thuong_deu_nhan() -> None:
    text = "nội dung"
    assert extract_text("DOC.TXT", text.encode("utf-8")) == text


def _build_docx(paragraphs: list[str]) -> bytes:
    doc = Document()
    for p in paragraphs:
        doc.add_paragraph(p)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def test_docx_noi_paragraph_bang_newline() -> None:
    raw = _build_docx(["Đoạn một.", "Đoạn hai có dấu tiếng Việt.", "Đoạn ba."])
    text = extract_text("tai-lieu.docx", raw)
    assert text == "Đoạn một.\nĐoạn hai có dấu tiếng Việt.\nĐoạn ba."


def test_docx_rong_ra_text_rong() -> None:
    raw = _build_docx([])
    assert extract_text("rong.docx", raw) == ""


def test_docx_giu_ca_paragraph_rong_giua_2_doan() -> None:
    raw = _build_docx(["Đoạn một.", "", "Đoạn ba."])
    assert extract_text("tai-lieu.docx", raw) == "Đoạn một.\n\nĐoạn ba."
