"""doc-factory — luật cắt chunk (`callisto-doc-schema.md` §3/§5/§6).

Oracle là bộ 5 doc thật ở `docs/callisto/`: mọi `expected_citation` trong `golden/smoke-5.yaml` trỏ
vào `chunk_id` do module này sinh ra, nên một thay đổi lặng lẽ ở luật cắt sẽ làm cả golden-set ra 0
điểm mà không có lỗi nào nổi lên (`docs/format.md` §2). Các test dưới là cái chuông cho chuyện đó.
"""

from __future__ import annotations

import pytest
from studio_kb.doc_factory import SECTION_VOCAB, chunk_document, load_callisto

_DOC_IDS = [
    "ankor-expense-001",
    "ankor-leave-001",
    "ankor-salary-001",
    "borea-expense-001",
    "borea-leave-001",
]


def test_bo_callisto_ra_dung_25_chunk() -> None:
    """5 doc × 5 heading `##`. Số này neo vào `callisto-doc-schema.md` §8."""
    chunks = load_callisto()
    assert len(chunks) == 25
    assert {c.chunk_id.split("#")[0] for c in chunks} == set(_DOC_IDS)


def test_chunk_id_dung_dang_va_danh_so_lai_theo_tung_doc() -> None:
    """`{doc_id}#c{n}`, n từ 1, đếm riêng mỗi doc (§6) — KHÔNG phải số chạy toàn bộ."""
    chunks = load_callisto()
    for doc_id in _DOC_IDS:
        ids = [c.chunk_id for c in chunks if c.chunk_id.startswith(f"{doc_id}#")]
        assert ids == [f"{doc_id}#c{n}" for n in range(1, 6)]


def test_section_role_override_chi_an_dung_chunk_mang_no() -> None:
    """Luật §5 "1 chunk = đúng 1 `section_role`": `ankor-expense-001` có front-matter `public`
    nhưng heading `## Hạn mức phê duyệt {section: finance}` → RIÊNG `#c2` là `finance`.

    Đây là chunk override duy nhất trong bộ, nên cũng là thứ duy nhất kiểm được luật. Nó hỏng thì
    SC-03 (case dương đúng-vai) mất chỗ dựa.
    """
    roles = {c.chunk_id: c.section_role for c in load_callisto() if c.chunk_id.startswith("ankor-expense-001#")}
    assert roles["ankor-expense-001#c2"] == "finance"
    assert all(roles[f"ankor-expense-001#c{n}"] == "public" for n in (1, 3, 4, 5))


def test_moi_chunk_mang_section_role_thuoc_tu_vung_dong() -> None:
    """§3 — từ vựng đóng. Một giá trị lạ lọt qua sẽ tạo chunk không ai với tới được, và fence sẽ
    trông như đang chạy đúng."""
    assert {c.section_role for c in load_callisto()} <= SECTION_VOCAB


def test_heading_giu_lai_trong_text_cua_chunk() -> None:
    """Heading là câu tóm tắt sẵn có của đoạn và đóng góp thẳng vào điểm trùng token ở
    `static_search`. Mất nó thì SC-01 tụt hạng."""
    chunk = next(c for c in load_callisto() if c.chunk_id == "ankor-leave-001#c1")
    assert chunk.text.startswith("Thời hạn báo trước")
    assert "3 ngày làm việc" in chunk.text


def test_override_ngoai_tu_vung_bi_chan_ngay() -> None:
    """Fail-fast: gõ sai `section_role` phải nổ lúc cắt, không im lặng tạo chunk mồ côi."""
    raw = "---\ndoc_id: x-001\ntenant: ankor\nsection: public\n---\n\n## Đoạn  {section: markting}\n\nnội dung\n"
    with pytest.raises(ValueError, match="ngoài từ vựng"):
        chunk_document(raw)


def test_thieu_front_matter_bi_chan() -> None:
    with pytest.raises(ValueError, match="front-matter"):
        chunk_document("## Đoạn\n\nnội dung không có front-matter\n")
