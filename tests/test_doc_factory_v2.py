"""Test ĐỎ-TRƯỚC cho loader Callisto 2.0 (`doc_factory_v2` — CHƯA hiện thực).

Bộ này định nghĩa HỢP ĐỒNG của cutter 2.0 trước khi viết code (test-first): tenant từ thư mục, role
từ tên file, KHÔNG front-matter, KHÔNG override, citation = tên file. Chạy bây giờ = **ĐỎ** vì module
`doc_factory_v2` chưa tồn tại → hiện thực nó cho tới khi xanh.

Song song với corpus 1.0 — bộ này **không đụng** `test_doc_factory.py` (1.0) và không đọc corpus thật;
mọi test tự dựng mini-corpus trong `tmp_path`.

Ánh xạ test ↔ bất biến schema (`docs/callisto-2.0-schema.md` §5): I1..I9.
Mỗi test raise phải chứng minh CÓ raise; mỗi test dương phải chốt giá trị cụ thể (không chỉ "không sai").
"""

from __future__ import annotations

from pathlib import Path

import pytest
from studio_kb.doc_factory import SECTION_VOCAB, resolve_tenant_id
from studio_kb.doc_factory_v2 import load_corpus_v2  # ĐỎ: module chưa tồn tại


def _doc(dir_path: Path, filename: str, sections: list[tuple[str, str]]) -> None:
    """Ghi 1 file .md 2.0 — markdown thuần (KHÔNG khối `---`), mỗi section = '## title\\nbody'."""
    dir_path.mkdir(parents=True, exist_ok=True)
    text = "\n\n".join(f"## {title}\n{body}" for title, body in sections)
    (dir_path / filename).write_text(text, encoding="utf-8")


@pytest.fixture
def corpus(tmp_path: Path) -> Path:
    """Mini-corpus 2.0 hợp lệ: cùng tên file `hr-onboarding.md` ở cả 2 tenant, nội dung khác nhau."""
    _doc(tmp_path / "ankor", "hr-onboarding.md", [("Ngày đầu", "Nhận thẻ và laptop.")])
    _doc(tmp_path / "borea", "hr-onboarding.md", [("Ngày đầu", "Ký hợp đồng trước.")])
    return tmp_path


# ── I2 · role lấy từ tên file ────────────────────────────────────────────────
def test_role_lay_tu_ten_file(corpus: Path) -> None:
    chunks = load_corpus_v2(corpus)
    ankor = [c for c in chunks if c.tenant_id == resolve_tenant_id("ankor")]
    assert ankor, "phải có chunk cho ankor"
    assert all(c.section_role == "hr" for c in ankor)  # role suy từ 'hr-onboarding.md'
    assert "Nhận thẻ và laptop." in ankor[0].text  # chốt dương: đọc đúng thân chunk


# ── I1 · I8 · tenant lấy từ thư mục, 2 tenant khác nhau ──────────────────────
def test_tenant_lay_tu_thu_muc(corpus: Path) -> None:
    tenants = {c.tenant_id for c in load_corpus_v2(corpus)}
    assert resolve_tenant_id("ankor") in tenants
    assert resolve_tenant_id("borea") in tenants
    assert resolve_tenant_id("ankor") != resolve_tenant_id("borea")


# ── I4 · chunk_id = {tenant}-{stem}#c{n} (citation = tên file) ───────────────
def test_chunk_id_mang_tenant_va_ten_file(corpus: Path) -> None:
    ids = {c.chunk_id for c in load_corpus_v2(corpus)}
    assert "ankor-hr-onboarding#c1" in ids
    assert "borea-hr-onboarding#c1" in ids


# ── I9 · chunk_id duy nhất dù 2 tenant cùng tên file ────────────────────────
def test_chunk_id_duy_nhat(corpus: Path) -> None:
    ids = [c.chunk_id for c in load_corpus_v2(corpus)]
    assert len(ids) == len(set(ids))  # 'hr-onboarding.md' ở 2 tenant KHÔNG đụng id


# ── I6 · nhiều heading: đánh số c1..cN, cả doc CÙNG role ─────────────────────
def test_nhieu_heading_danh_so_va_cung_role(tmp_path: Path) -> None:
    _doc(tmp_path / "ankor", "finance-budget.md", [("A", "x"), ("B", "y"), ("C", "z")])
    chunks = load_corpus_v2(tmp_path)
    assert [c.chunk_id for c in chunks] == [
        "ankor-finance-budget#c1",
        "ankor-finance-budget#c2",
        "ankor-finance-budget#c3",
    ]
    assert all(c.section_role == "finance" for c in chunks)  # I6: không chunk nào lệch role


# ── 2.0 bỏ front-matter: file không có khối `---` vẫn nạp được ───────────────
def test_khong_can_front_matter(tmp_path: Path) -> None:
    _doc(tmp_path / "ankor", "public-holidays.md", [("Tết", "Nghỉ 5 ngày.")])
    chunks = load_corpus_v2(tmp_path)
    assert chunks and chunks[0].section_role == "public"


# ── I2 · role ngoài SECTION_VOCAB → raise ───────────────────────────────────
def test_role_ngoai_tu_vung_raise(tmp_path: Path) -> None:
    _doc(tmp_path / "ankor", "marketing-launch.md", [("A", "x")])  # 'marketing' ∉ vocab
    assert "marketing" not in SECTION_VOCAB  # chốt tiền đề
    with pytest.raises(ValueError):
        load_corpus_v2(tmp_path)


# ── I1 · thư mục tenant lạ → raise ──────────────────────────────────────────
def test_thu_muc_tenant_la_raise(tmp_path: Path) -> None:
    _doc(tmp_path / "acme", "hr-x.md", [("A", "x")])  # 'acme' không phải tenant
    with pytest.raises(ValueError):
        load_corpus_v2(tmp_path)


# ── I3 · tên file thiếu '{role}-' → raise ───────────────────────────────────
def test_ten_file_thieu_role_raise(tmp_path: Path) -> None:
    _doc(tmp_path / "ankor", "onboarding.md", [("A", "x")])  # không có dấu '-' → không tách role
    with pytest.raises(ValueError):
        load_corpus_v2(tmp_path)


# ── I5 · CẤM override: heading mang {section:X} → raise (không im lặng áp dụng) ─
def test_override_bi_cam_raise(tmp_path: Path) -> None:
    d = tmp_path / "ankor"
    d.mkdir(parents=True)
    (d / "public-notice.md").write_text("## Hạn mức {section: finance}\nTối đa 20 triệu.", encoding="utf-8")
    with pytest.raises(ValueError):
        load_corpus_v2(tmp_path)


# ── I7 · thân heading rỗng → raise (giữ 'đủ số chunk', không âm thầm thành 9) ─
def test_than_heading_rong_raise(tmp_path: Path) -> None:
    _doc(tmp_path / "ankor", "hr-mixed.md", [("Có nội dung", "ok"), ("Rỗng", "")])
    with pytest.raises(ValueError):
        load_corpus_v2(tmp_path)
