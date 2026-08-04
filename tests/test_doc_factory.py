"""doc-factory — luật cắt chunk (`callisto-doc-schema.md` §3/§5/§6).

Oracle golden là bộ **5 doc stub gốc** ở `docs/callisto/` (§8): mọi `expected_citation` trong
`golden/smoke-5.yaml` trỏ vào `chunk_id` do module này sinh ra, nên một thay đổi lặng lẽ ở luật cắt
làm cả golden-set ra 0 điểm mà không có lỗi nào nổi lên (`docs/format.md` §2). Các test dưới là cái
chuông cho chuyện đó.

**D12 (Callisto Handbook, S2):** corpus mở rộng 5 → **42 doc / 140 chunk** (`callisto-doc-schema.md`
§8b). 5 doc gốc **giữ nguyên từng ký tự** (vẫn 5 chunk/doc) để oracle smoke-5 không dịch; các test
canary bên dưới vừa neo tổng số mới, vừa khẳng định 5 doc gốc còn nguyên.
"""

from __future__ import annotations

import pytest
from studio_kb.doc_factory import SECTION_VOCAB, TENANT_IDS, chunk_document, load_callisto

# 5 doc stub gốc (§8) — nền của golden/smoke-5.yaml, KHÔNG được dịch chunk_id.
_ORIGINAL_DOC_IDS = [
    "ankor-expense-001",
    "ankor-leave-001",
    "ankor-salary-001",
    "borea-expense-001",
    "borea-leave-001",
]

# Neo vào callisto-doc-schema.md §8b. Số tĩnh, suy được từ file trên đĩa (deterministic).
_EXPECTED_DOC_COUNT = 42
_EXPECTED_TOTAL_CHUNKS = 140


def test_corpus_dung_so_chunk_va_giu_nguyen_5_doc_goc() -> None:
    """Canary tổng: 42 doc / 140 chunk (§8b) VÀ 5 doc gốc còn nguyên 5 chunk mỗi doc.

    Đổi luật cắt lặng lẽ → tổng lệch → chuông kêu. Lỡ tay re-cut 1 trong 5 doc gốc → nhánh dưới
    kêu, bảo vệ trực tiếp `golden/smoke-5.yaml`.
    """
    chunks = load_callisto()
    assert len(chunks) == _EXPECTED_TOTAL_CHUNKS
    doc_ids = {c.chunk_id.split("#")[0] for c in chunks}
    assert len(doc_ids) == _EXPECTED_DOC_COUNT
    assert set(_ORIGINAL_DOC_IDS) <= doc_ids
    for doc_id in _ORIGINAL_DOC_IDS:
        ids = sorted(
            (c.chunk_id for c in chunks if c.chunk_id.startswith(f"{doc_id}#")),
            key=lambda x: int(x.split("#c")[1]),
        )
        assert ids == [f"{doc_id}#c{n}" for n in range(1, 6)], doc_id


def test_chunk_id_dung_dang_va_danh_so_lai_theo_tung_doc() -> None:
    """`{doc_id}#c{n}`, n từ 1, đếm riêng mỗi doc (§6) — KHÔNG phải số chạy toàn bộ.

    Kiểm cho TOÀN corpus (không riêng 5 doc gốc): mỗi doc phải có dãy `#c1..#cK` liên tục, không
    trùng, không hụt — bất biến mà re-index (S3) dựa vào.
    """
    chunks = load_callisto()
    by_doc: dict[str, list[str]] = {}
    for c in chunks:
        by_doc.setdefault(c.chunk_id.split("#")[0], []).append(c.chunk_id)
    for doc_id, ids in by_doc.items():
        ordered = sorted(ids, key=lambda x: int(x.split("#c")[1]))
        assert ordered == [f"{doc_id}#c{n}" for n in range(1, len(ids) + 1)], doc_id


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


# ── Handbook D12: phủ tenant/vai + override ở quy mô mới ─────────────────────────


def test_corpus_chi_gom_hai_tenant_ankor_borea() -> None:
    """§1 — Callisto chỉ có `ankor`/`borea`. `tenant_id` mọi chunk phải nằm trong bảng phân giải;
    slug lạ đã raise lúc cắt, đây là chốt chặn thứ hai ở tầng corpus."""
    tenant_ids = {c.tenant_id for c in load_callisto()}
    assert tenant_ids == set(TENANT_IDS.values())


def test_moi_tenant_phu_du_bon_vai() -> None:
    """Handbook D12 nuôi fence/leak-test: mỗi tenant phải có chunk ở CẢ 4 vai, nếu không thì
    case chéo-vai (T6) của tenant đó không có nguồn thật để dựng."""
    chunks = load_callisto()
    for slug in ("ankor", "borea"):
        roles = {c.section_role for c in chunks if c.chunk_id.startswith(f"{slug}-")}
        assert roles == SECTION_VOCAB, (slug, sorted(roles))


def test_doc_override_van_giu_luat_mot_chunk_mot_vai() -> None:
    """§5 ở quy mô mới: ngoài `ankor-expense-001`, D12 thêm doc override (conduct→hr,
    facilities→engineering). Doc override phải mang CẢ vai front-matter LẪN vai override — không
    nuốt cả doc sang một vai, cũng không bỏ sót override."""
    chunks = load_callisto()
    for doc_id, front_role, override_role in (
        ("ankor-facilities-001", "public", "engineering"),
        ("ankor-conduct-001", "public", "hr"),
        ("borea-facilities-001", "public", "engineering"),
        ("borea-conduct-001", "public", "hr"),
    ):
        roles = {c.section_role for c in chunks if c.chunk_id.startswith(f"{doc_id}#")}
        assert front_role in roles, (doc_id, sorted(roles))
        assert override_role in roles, (doc_id, sorted(roles))


def test_tenant_ngoai_bang_bi_chan() -> None:
    """Fail-fast: slug tenant lạ nổ lúc cắt, không im lặng tạo chunk mang UUID rác."""
    raw = "---\ndoc_id: x-001\ntenant: carthage\nsection: public\n---\n\n## Đoạn\n\nnội dung\n"
    with pytest.raises(ValueError, match="tenant slug"):
        chunk_document(raw)


def test_section_front_matter_ngoai_tu_vung_bi_chan() -> None:
    """§3 — `section` mặc định ở front-matter cũng phải thuộc từ vựng đóng, không chỉ override."""
    raw = "---\ndoc_id: x-001\ntenant: ankor\nsection: legal\n---\n\n## Đoạn\n\nnội dung\n"
    with pytest.raises(ValueError, match="ngoài từ vựng"):
        chunk_document(raw)


def test_doc_khong_co_heading_bi_chan() -> None:
    """Doc không có `## ` nào không cắt được chunk → raise, không trả list rỗng im lặng."""
    raw = "---\ndoc_id: x-001\ntenant: ankor\nsection: public\n---\n\n# Tiêu đề\n\nthân không có heading\n"
    with pytest.raises(ValueError, match="không cắt được chunk"):
        chunk_document(raw)
