"""`extract.extract_text` — trích text thuần từ `.md`/`.txt`/`.docx`, raise cho đuôi khác."""

from __future__ import annotations

import io
import zipfile

import pytest
from docx import Document
from studio_kb.extract import DocumentTooLongError, UnsupportedFormatError, extract_text


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


# ── `.docx` hỏng — phải là 422 (UnsupportedFormatError), KHÔNG phải 500 ────
def _zip_khong_phai_ooxml() -> bytes:
    """Zip HỢP LỆ nhưng không có part OOXML nào — vỏ đúng, ruột sai."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("a.txt", "hello")
    return buf.getvalue()


def _docx_document_xml_hong() -> bytes:
    """`.docx` thật rồi ghi đè `word/document.xml` bằng XML rúng — ca hỏng SÂU nhất, lỗi bật ra
    từ lxml lúc parse chứ không phải từ zipfile lúc mở gói."""
    origin = io.BytesIO(_build_docx(["Đoạn một."]))
    src = zipfile.ZipFile(origin)
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        for item in src.infolist():
            data = b"<w:document><chua-dong-the" if item.filename.endswith("document.xml") else src.read(item)
            z.writestr(item, data)
    return out.getvalue()


@pytest.mark.parametrize(
    "raw",
    [
        pytest.param(b"# Chinh sach nghi phep\nnoi dung", id="md-doi-duoi-thanh-docx"),
        pytest.param(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3", id="pdf-doi-duoi-thanh-docx"),
        pytest.param(b"", id="upload-dut-hoac-rong"),
        pytest.param(_zip_khong_phai_ooxml(), id="zip-hop-le-khong-phai-ooxml"),
        pytest.param(_docx_document_xml_hong(), id="document-xml-rung"),
    ],
)
def test_docx_hong_raise_unsupported_format(raw: bytes) -> None:
    """5 kiểu hỏng này bật ra 3 HỌ exception khác nhau từ `python-docx` (`zipfile.BadZipFile`,
    `KeyError` thiếu part, `lxml.etree.XMLSyntaxError`) và KHÔNG cái nào là `ValueError` — nên
    trước bản vá, cả 5 thoát thẳng qua `except UnsupportedFormatError` ở `routes/documents.py`
    và thành HTTP 500. Đổi đuôi `.doc`/`.pdf` thành `.docx` là đúng thao tác người dùng làm khi
    bị báo "chỉ nhận .md/.txt/.docx", nên đây là đường đi thường chứ không phải ca hiếm."""
    with pytest.raises(UnsupportedFormatError):
        extract_text("tai-lieu.docx", raw)


def test_docx_hong_giu_nguyen_nhan_goc_trong_cause() -> None:
    """Quy về `UnsupportedFormatError` cho client (422) nhưng KHÔNG nuốt nguyên nhân: exception
    gốc phải còn trong `__cause__` để log server còn lần được hỏng ở đâu."""
    with pytest.raises(UnsupportedFormatError) as exc_info:
        extract_text("tai-lieu.docx", b"khong phai zip")
    assert isinstance(exc_info.value.__cause__, zipfile.BadZipFile)


def test_docx_hop_le_van_doc_binh_thuong_sau_ban_va() -> None:
    """Vế đối xứng của test trên — bản vá KHÔNG được biến mọi `.docx` thành lỗi."""
    raw = _build_docx(["Đoạn một.", "Đoạn hai."])
    assert extract_text("tai-lieu.docx", raw) == "Đoạn một.\nĐoạn hai."


def test_extraction_stops_before_a_compression_bomb_blows_memory() -> None:
    """`.docx` nén, nên số byte KHÔNG chặn được lượng chữ — phải chặn ngay lúc trích.

    Đo trên hạn mức 1 MiB: `.txt` thuần ~168.000 từ, còn `.docx` nội dung lặp ~**14.400.000** từ.
    Nâng hạn mức byte lên 10 MiB là scale con số đó lên ~144 triệu từ ≈ ~1 GB chuỗi — và
    `_extract_docx` dựng TOÀN BỘ chuỗi trong bộ nhớ trước khi bất kỳ phép kiểm số từ nào chạy.

    Nên `max_words` phải cưỡng chế **trong lúc trích**, không phải sau. Không có nó, nâng hạn mức
    kích thước là biến một giới hạn thành một lỗ nuốt bộ nhớ."""
    body = " ".join(["lap"] * 5_000)
    raw = _build_docx([body] * 20)  # 100.000 từ, nén rất nhỏ

    with pytest.raises(DocumentTooLongError) as exc:
        extract_text("bom.docx", raw, max_words=1_000)
    assert exc.value.max_words == 1_000


def test_extraction_under_the_budget_returns_everything() -> None:
    """Đối trọng: dưới hạn mức thì trả về ĐỦ, không cắt bớt.

    Thiếu vế này, "dừng sớm" dễ nới thành cắt ngang mọi tài liệu — và một tài liệu bị cắt im lặng
    sẽ sinh ra bộ golden thiếu mục mà không gì báo."""
    raw = _build_docx(["Nghỉ phép năm 12 ngày.", "Thử việc 2 tháng."])

    assert extract_text("ok.docx", raw, max_words=1_000) == "Nghỉ phép năm 12 ngày.\nThử việc 2 tháng."


def test_a_plain_text_file_is_bounded_by_the_same_budget() -> None:
    """`.md`/`.txt` cũng phải chịu cùng hạn mức.

    Byte của chúng tỉ lệ với chữ nên nguy cơ thấp hơn `.docx`, nhưng hai đường đi qua cùng một hàm
    và cùng một cổng — chỉ chặn một bên là để lại một cửa mở mà không ai nhớ vì sao nó mở."""
    with pytest.raises(DocumentTooLongError):
        extract_text("dai.txt", (" ".join(["tu"] * 5_000)).encode(), max_words=100)


def test_omitting_the_budget_keeps_the_old_behaviour() -> None:
    """`max_words=None` (mặc định) ⇒ không chặn gì — mọi call-site cũ không đổi một dòng."""
    raw = (" ".join(["tu"] * 5_000)).encode()
    assert len(extract_text("dai.txt", raw).split()) == 5_000
