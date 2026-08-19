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


# ── embed-view: text ĐEM EMBED khác text LƯU (fix "#c1 tổng quan nuốt truy vấn") ─
#
# Vì sao tách hai chuỗi thay vì sửa `text`: `text` là thứ golden-set 2.0 chấm grounded lên
# (`_contains_phrase(chunk.text, expected)`) và là thứ `StaticKbSearch` xếp hạng. Đổi nó = phải
# re-trace toàn bộ nhãn. `embed_text` chỉ đi vào vector, không ai chấm nhãn lên nó.
def _doc_co_tieu_de(dir_path: Path, filename: str, tieu_de: str, sections: list[tuple[str, str]]) -> None:
    """Như `_doc` nhưng có dòng tiêu đề tài liệu '# ...' ở đầu — thứ `_cut_document` vứt đi (`:48`)."""
    dir_path.mkdir(parents=True, exist_ok=True)
    body = "\n\n".join(f"## {title}\n{b}" for title, b in sections)
    (dir_path / filename).write_text(f"# {tieu_de}\n\n{body}", encoding="utf-8")


def test_embed_text_mang_tieu_de_doc_con_text_thi_khong(tmp_path: Path) -> None:
    """MỌI chunk phải mang chủ đề cấp-tài-liệu khi đem embed — hết cảnh chỉ `#c1` độc quyền giữ nó.

    Đồng thời `text` KHÔNG được đổi: nhãn golden 2.0 chấm trên `text`, đổi là trôi nhãn."""
    _doc_co_tieu_de(
        tmp_path / "ankor",
        "hr-leave.md",
        "Chính sách nghỉ phép",
        [("Số ngày phép năm", "12 ngày."), ("Nghỉ ốm", "Tối đa 30 ngày/năm.")],
    )
    chunks = sorted(load_corpus_v2(tmp_path), key=lambda c: c.chunk_id)

    for c in chunks:
        assert "Chính sách nghỉ phép" in c.embed_text, f"{c.chunk_id}: embed_text thiếu tiêu đề doc"
        assert "Chính sách nghỉ phép" not in c.text, f"{c.chunk_id}: tiêu đề doc rò vào text → trôi nhãn golden"
    # `text` giữ đúng hình dạng cũ, byte-identical với trước khi có embed-view.
    assert chunks[0].text == "## Số ngày phép năm\n12 ngày."
    assert chunks[1].text == "## Nghỉ ốm\nTối đa 30 ngày/năm."
    # thân riêng của mục vẫn còn trong embed_text (tiêu đề THÊM VÀO, không thay thế).
    assert "Tối đa 30 ngày/năm." in chunks[1].embed_text


def test_embed_text_cat_boilerplate_lap_trong_scope(tmp_path: Path) -> None:
    """Câu lặp ≥3 chunk trong CÙNG scope (tenant, role) bị cắt khỏi `embed_text`, còn nguyên ở `text`.

    Đây là câu 'thủ tục chung' không nói gì về mục nó đứng, nhưng vẫn góp từ vựng vào vector — và tệ
    hơn, có thể cấp nhầm bằng chứng (vd boilerplate chứa '30 ngày' cho câu hỏi về nghỉ ốm)."""
    boiler = "Chính sách được cập nhật hằng năm."
    _doc_co_tieu_de(
        tmp_path / "ankor",
        "hr-leave.md",
        "Nghỉ phép",
        [("A", f"Nội dung A.\n{boiler}"), ("B", f"Nội dung B.\n{boiler}"), ("C", f"Nội dung C.\n{boiler}")],
    )
    chunks = load_corpus_v2(tmp_path)
    assert len(chunks) == 3
    for c in chunks:
        assert boiler in c.text, f"{c.chunk_id}: text phải GIỮ boilerplate (nhãn golden chấm trên text)"
        assert boiler not in c.embed_text, f"{c.chunk_id}: embed_text vẫn dính boilerplate"
        assert "Nội dung" in c.embed_text, f"{c.chunk_id}: cắt nhầm cả nội dung thật"


def test_boilerplate_khong_cat_khi_duoi_nguong(tmp_path: Path) -> None:
    """Chốt NGƯỠNG: lặp 2 chunk là CHƯA đủ để coi là boilerplate — chống cắt oan câu nội dung thật.

    Không có bài này thì hạ ngưỡng xuống 2 (hoặc 1) vẫn xanh, mà ngưỡng 1 thì cắt sạch mọi thứ."""
    lap2 = "Câu này chỉ lặp hai lần."
    _doc_co_tieu_de(
        tmp_path / "ankor",
        "hr-leave.md",
        "Nghỉ phép",
        [("A", f"Nội dung A.\n{lap2}"), ("B", f"Nội dung B.\n{lap2}"), ("C", "Nội dung C.")],
    )
    for c in load_corpus_v2(tmp_path):
        assert lap2 in c.embed_text or "Nội dung C." in c.text


def test_boilerplate_dem_theo_SCOPE_khong_phai_toan_corpus(tmp_path: Path) -> None:
    """Cùng một câu lặp 3 lần ở vai `hr` nhưng chỉ 1 lần ở vai `finance` → chỉ cắt bên `hr`.

    Fence lọc theo (tenant, role) TRƯỚC khi xếp hạng, nên chunk `finance` không bao giờ cạnh tranh
    với chunk `hr`; đếm gộp toàn corpus sẽ cắt oan câu vốn đặc trưng trong scope của nó."""
    cau = "Thông báo trước 2 tuần."
    _doc_co_tieu_de(
        tmp_path / "ankor", "hr-leave.md", "Nghỉ phép", [("A", f"a.\n{cau}"), ("B", f"b.\n{cau}"), ("C", f"c.\n{cau}")]
    )
    _doc_co_tieu_de(tmp_path / "ankor", "finance-budget.md", "Ngân sách", [("D", f"d.\n{cau}")])
    by_role = {c.chunk_id: c for c in load_corpus_v2(tmp_path)}
    assert cau not in by_role["ankor-hr-leave#c1"].embed_text, "hr: lặp 3 → phải cắt"
    assert cau in by_role["ankor-finance-budget#c1"].embed_text, "finance: lặp 1 → KHÔNG được cắt"


def test_tieu_de_doc_KHONG_bi_chinh_bo_loc_boilerplate_xoa(tmp_path: Path) -> None:
    """Hồi quy: tiêu đề tài liệu lặp ở MỌI chunk của doc (10 mục ⇒ 10 lần ≥ ngưỡng 3), nên bộ lọc
    boilerplate sẽ ăn mất chính thứ vừa nhồi vào nếu nó không được miễn trừ.

    Bài `test_embed_text_mang_tieu_de_doc_...` KHÔNG bắt được: doc ở đó chỉ có 2 mục → lặp 2 lần →
    dưới ngưỡng. Phải ≥3 mục mới lộ. (Đo thật lúc phát hiện: 138/800 chunk giữ được tiêu đề thay vì
    800/800.)"""
    _doc_co_tieu_de(
        tmp_path / "ankor",
        "hr-leave.md",
        "Chính sách nghỉ phép",
        [(f"Mục {i}", f"Nội dung riêng {i}.") for i in range(1, 6)],
    )
    chunks = load_corpus_v2(tmp_path)
    assert len(chunks) == 5
    for c in chunks:
        assert "Chính sách nghỉ phép" in c.embed_text, (
            f"{c.chunk_id}: tiêu đề doc bị bộ lọc boilerplate xoá — embed-view mất tác dụng"
        )
