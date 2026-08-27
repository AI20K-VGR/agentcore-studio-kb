"""Sinh golden ở tầng TÀI LIỆU thay vì tầng chunk.

## Sự cố đã đo

`cut_window` cắt cửa sổ trượt 850 từ/overlap 170, **không quan tâm cấu trúc**: mỗi chunk bắt đầu và
kết thúc giữa câu, và tiêu đề của một mục có thể nằm ở chunk này còn con số đáp án nằm ở chunk sau.
Bộ sinh đọc từng chunk **như thể đó là một tài liệu**, nên nó dựng câu hỏi từ những mảnh vụn.

Con số nói hết: một tài liệu 179 từ nằm trọn MỘT chunk cho ra bộ 10 câu hỏi sạch; cùng bộ sinh đó
chạy trên tài liệu 31 chunk × 835 từ cho ra *"Xuất bản: Hà Nội & TP. Hồ Chí Minh là bao nhiêu năm?"*.
Bộ sinh không đổi — chỉ có TẦNG nó đọc là đổi.

## Vì sao truyền toàn văn vào chứ không ghép lại từ chunk

Ghép chunk lại được (chúng chồng lấn nhau), nhưng phép dò phần chồng bằng nội dung **cắt mất chữ**
trên văn bản lặp lại — mà tài liệu nội quy đầy boilerplate lặp ("Tập đoàn ... Group" ở mọi trang).
Mất chữ thì im lặng: văn bản vẫn đọc trôi chảy ở từng đoạn. Nên toàn văn được LƯU lúc upload
(`extract_text` chạy trước `cut_window`) và đọc lại nguyên vẹn.
"""

from __future__ import annotations

from uuid import UUID

from studio_kb.chunk_window import cut_window
from studio_kb.golden_from_kb import SourceChunk, SourceDocument, build_cases

_TENANT = UUID("a0000000-0000-0000-0000-000000000001")

# Tiêu đề ở đầu, đáp án ở cuối, ở giữa là đủ chữ để `cut_window` cắt ngang mục.
_SPLIT_DOC = (
    "## Phan mo dau\n"
    + " ".join(["dem"] * 30)
    + "\n## Nghi phep nam\n"
    + "Nhan vien chinh thuc duoc 12 ngay phep co luong moi nam."
)


def _chunks_of(text: str, doc_id: str = "ankor-hr-noi-quy") -> list[SourceChunk]:
    """Cắt bằng CHÍNH `cut_window` — fixture tự chế chỉ chứng minh được chính nó."""
    return [
        SourceChunk(chunk_id=c.chunk_id, text=c.text, tenant="ankor", section_role="hr")
        for c in cut_window(text, doc_id, _TENANT, "hr", size=12, overlap=3)
    ]


def _document(text: str, doc_id: str = "ankor-hr-noi-quy") -> SourceDocument:
    return SourceDocument(doc_id=doc_id, text=text, tenant="ankor", section_role="hr")


def test_a_section_split_across_chunks_yields_its_question() -> None:
    """**Bài trung tâm.** Tiêu đề ở chunk này, đáp án ở chunk sau ⇒ tầng chunk không dựng nổi,
    tầng tài liệu dựng được."""
    chunks = _chunks_of(_SPLIT_DOC)
    # Điều kiện làm bài này có nghĩa: KHÔNG chunk đơn lẻ nào chứa cả tiêu đề lẫn đáp án.
    assert not any("## Nghi phep nam" in c.text and "12 ngay" in c.text for c in chunks)

    without = [c for c in build_cases(chunks) if not c.is_refusal]
    with_doc = [c for c in build_cases(chunks, documents=[_document(_SPLIT_DOC)]) if not c.is_refusal]

    assert not any("Nghi phep nam" in c.query for c in without), "tầng chunk lẽ ra không dựng được"
    assert any("Nghi phep nam" in c.query for c in with_doc), "tầng tài liệu phải dựng được"


def test_citation_still_points_at_a_real_retrievable_chunk() -> None:
    """Câu hỏi dựng từ toàn văn, nhưng `expected_citation` phải trỏ chunk agent TRUY XUẤT ĐƯỢC.

    Trỏ vào `doc_id` (thứ không nằm trong `kb.chunks`) sẽ cho `citation_accuracy = 0` vĩnh viễn mà
    không ai truy được về đâu — một id trông hợp lệ chỉ vào hư không."""
    chunks = _chunks_of(_SPLIT_DOC)
    real_ids = {c.chunk_id for c in chunks}

    cases = [c for c in build_cases(chunks, documents=[_document(_SPLIT_DOC)]) if not c.is_refusal]

    assert cases
    assert all(c.expected_citation[0] in real_ids for c in cases)


def test_an_answer_no_chunk_contains_is_dropped() -> None:
    """Đáp án không nằm nguyên vẹn trong chunk nào ⇒ bỏ case, không bịa trích dẫn.

    Xảy ra thật khi cụm đáp án vắt qua ranh giới chunk. Gán đại một `chunk_id` sẽ cho một case luôn
    trượt trục citation mà nhìn từ ngoài giống hệt "agent trích sai"."""
    chunks = _chunks_of("## Muc\nKhong co dai luong nao o day ca.")
    # Tài liệu khai một đáp án KHÔNG có trong chunk nào của nó.
    doc = _document("## Nghi phep nam\nNhan vien duoc 12 ngay phep co luong.")

    cases = [c for c in build_cases(chunks, documents=[doc]) if not c.is_refusal]
    assert cases == []


def test_documents_without_text_fall_back_to_chunk_level() -> None:
    """Tài liệu chưa có toàn văn (nạp trước khi hệ thống lưu lại) vẫn sinh được như cũ.

    Không có vế này thì mọi KB đã nạp từ trước bỗng dưng ra bộ rỗng sau khi nâng cấp — một lần
    "cải tiến" xoá sạch dữ liệu chấm đang dùng."""
    text = "## Nghi phep nam\nNhan vien duoc 12 ngay phep co luong moi nam."
    chunks = [SourceChunk(chunk_id="ankor-hr-cu#c1", text=text, tenant="ankor", section_role="hr")]

    assert [c for c in build_cases(chunks) if not c.is_refusal]


def test_a_document_view_does_not_leak_into_another_document() -> None:
    """Hai tài liệu cùng vai vẫn là hai khối riêng: câu hỏi không được vắt qua ranh giới tài liệu."""
    a = "## Nghi phep nam\nNhan vien duoc 12 ngay phep."
    b = "## Thu viec\nThoi gian thu viec la 2 thang."
    chunks = [*_chunks_of(a, "ankor-hr-a"), *_chunks_of(b, "ankor-hr-b")]
    docs = [_document(a, "ankor-hr-a"), _document(b, "ankor-hr-b")]

    cases = [c for c in build_cases(chunks, documents=docs) if not c.is_refusal]
    by_doc = {c.expected_citation[0].split("#", 1)[0] for c in cases}

    assert by_doc == {"ankor-hr-a", "ankor-hr-b"}
