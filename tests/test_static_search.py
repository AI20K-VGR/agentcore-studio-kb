"""`StaticKbSearch` — bản `kb.search` thô của Sprint 1.

Hai nhóm test, đừng trộn vào nhau:

- **Hình dạng seam** — chữ ký 4 tham số, `[]` là kết quả hợp lệ. Đây là thứ AIE-1 wiring dựa vào.
- **Hành vi lọc** — tenant + `section_roles`. Naive ở v0, nhưng SC-04/SC-05 đã dựa vào nó rồi, nên
  nó vẫn phải đúng; cái hoãn tới S3 là *phân giải server-side* + *fail-closed*, không phải bản thân
  mệnh đề lọc.

Lưu ý về cách kiểm conformance: **gọi thật đủ 4 keyword-arg**, KHÔNG dùng
`isinstance(x, KbSearch)`. `KbSearch` có `@runtime_checkable`, nhưng `isinstance` với Protocol chỉ
kiểm **tên method có tồn tại, không kiểm chữ ký** — một stub 3 tham số vẫn trả `True`. Dùng nó làm
cổng kiểm sẽ xanh đúng ở trường hợp cần chặn (`day03_plan.md` §D3-1b).
"""

from __future__ import annotations

from uuid import UUID

import pytest
from studio_kb.doc_factory import TENANT_IDS, Chunk
from studio_kb.static_search import StaticKbSearch

ANKOR_ID = TENANT_IDS["ankor"]
BOREA_ID = TENANT_IDS["borea"]


@pytest.fixture
def kb() -> StaticKbSearch:
    return StaticKbSearch()


# ── Hình dạng seam ──────────────────────────────────────────────────────────────


async def test_goi_duoc_bang_dung_4_keyword_arg(kb: StaticKbSearch) -> None:
    """Chữ ký chốt D3 (`kb-search.v0.md` v0.1 §1). Sai số tham số → `TypeError` ngay tại đây, đúng
    chỗ AIE-1 sẽ vỡ nếu wiring lệch."""
    hits = await kb.search(query="báo trước bao lâu", tenant_id=ANKOR_ID, section_roles=["public"], top_k=5)
    # Cầu chì chống rỗng-nghĩa: `all([])` là True, nên `hits` rỗng làm assert dưới xanh mà không kiểm
    # gì. Răng thật của bài này là lời gọi 4-kwarg ở trên không raise `TypeError`; assert dưới chỉ là
    # phụ, và chính vì phụ mà nó dễ bị tưởng là đang kiểm nội dung.
    # Đo được: cho `StaticKbSearch.search` trả `[]` (mô phỏng impl hỏng) → 9 test khác trong suite đỏ,
    # riêng bài này VẪN XANH. Có dòng này thì nó đỏ theo. Cùng khuôn `test_leak.py:46-50`.
    assert hits, "gọi được chữ ký rồi thì phải ra chunk — rỗng nghĩa là assert dưới không kiểm gì"
    assert all(h.chunk_id and h.text and h.tenant_id and h.section_role for h in hits)


async def test_khong_khop_gi_thi_tra_rong_chu_khong_raise(kb: StaticKbSearch) -> None:
    """`[]` là kết quả HỢP LỆ (`kb-search.v0.md` §6.1) — `kb-retrieve` phải đi tiếp sang `llm-step`.
    Đây cũng đã là hình dạng của fail-closed sau này."""
    # UUID không có chunk nào trong bộ Callisto (chỉ có ankor + borea) — đứng cho "tenant lạ".
    khong_ton_tai = UUID("c0000000-0000-0000-0000-000000000001")
    assert await kb.search("zzzzz", ANKOR_ID, ["public"], 5) == []
    assert await kb.search("báo trước", khong_ton_tai, ["public"], 5) == []
    assert await kb.search("báo trước", ANKOR_ID, [], 5) == []
    assert await kb.search("báo trước", ANKOR_ID, ["public"], 0) == []


async def test_top_k_cat_dung_so_luong(kb: StaticKbSearch) -> None:
    assert len(await kb.search("nghỉ phép báo trước đơn", ANKOR_ID, ["public"], 2)) == 2


async def test_xep_hang_tat_dinh_khi_diem_bang_nhau() -> None:
    """`chunk_id` làm khoá phụ. Không có nó, golden-set sẽ xanh/đỏ đổi theo thứ tự đọc file."""
    chunks = [
        Chunk(chunk_id=f"d-001#c{n}", text="cùng một nội dung", tenant_id=ANKOR_ID, section_role="public")
        for n in (3, 1, 2)
    ]
    hits = await StaticKbSearch(chunks).search("cùng một nội dung", ANKOR_ID, ["public"], 3)
    assert [h.chunk_id for h in hits] == ["d-001#c1", "d-001#c2", "d-001#c3"]


# ── Hành vi lọc ─────────────────────────────────────────────────────────────────


async def test_sc01_sc02_cung_cau_hoi_khac_tenant_ra_dap_an_khac(kb: StaticKbSearch) -> None:
    """**Phép thử fence rẻ nhất trong bộ** (`callisto-doc-schema.md:276`). Cùng query, cùng
    `section_roles`, khác tenant. Ra cùng kết quả = fence hở.

    Hai doc cố ý viết khác nội dung (3 ngày vs 7 ngày): nếu chúng giống nhau thì rò rỉ xảy ra mà
    test vẫn xanh.
    """
    query = "Nhân viên xin nghỉ phép cần báo trước bao lâu?"
    ankor = await kb.search(query, ANKOR_ID, ["public"], 3)
    borea = await kb.search(query, BOREA_ID, ["public"], 3)

    assert ankor[0].chunk_id == "ankor-leave-001#c1"
    assert borea[0].chunk_id == "borea-leave-001#c1"
    assert "3 ngày làm việc" in ankor[0].text
    assert "7 ngày làm việc" in borea[0].text


async def test_sc03_dung_vai_thi_lay_duoc_chunk_finance(kb: StaticKbSearch) -> None:
    """Chunk override `#c2` — hỏi từ vai `finance` thì thấy, và CHỈ thấy chunk mang đúng vai đó."""
    hits = await kb.search("Trưởng nhóm được duyệt chi tối đa bao nhiêu?", ANKOR_ID, ["finance"], 5)
    assert hits[0].chunk_id == "ankor-expense-001#c2"
    assert "20 triệu đồng" in hits[0].text
    assert all(h.section_role == "finance" for h in hits)


async def test_sc04_cheo_tenant_khong_ro_ri_chunk_cua_tenant_kia(kb: StaticKbSearch) -> None:
    """Mầm leak-test T1. Hỏi từ `ankor` về hạn mức của Borea: có thể trả về vài chunk `ankor` điểm
    thấp (chuyện của tầng trả lời), nhưng **tuyệt đối không** chunk nào của `borea`.

    Assert theo hướng LOẠI TRỪ chứ không assert `== []`: bản naive vẫn trả kết quả yếu, và siết
    thành rỗng ở đây sẽ khoá cứng một hành vi mà S2 (xếp hạng vector) chắc chắn đổi.
    """
    hits = await kb.search("Hạn mức chi của Borea là bao nhiêu?", ANKOR_ID, ["public"], 5)
    # Cầu chì chống rỗng-nghĩa: cả ba assert dưới đều theo hướng LOẠI TRỪ, nên `hits` rỗng làm cả ba
    # xanh vô nghĩa (`all([])` True, `any([])` False) — tập rỗng loại trừ được mọi thứ. Đây là bản
    # `StaticKbSearch` của đúng lỗi SWE bắt ở `test_tenant_wall.py` chiều B→A (kb#4, vá 77dd9e4).
    # Đo được: cho `StaticKbSearch.search` trả `[]` → 9 test khác đỏ, riêng bài này VẪN XANH — tức là
    # bài canh rò-rỉ-chéo-tenant lại không phát hiện nổi một impl chết. Có dòng này thì nó đỏ theo.
    # Khẳng định không-rỗng, KHÔNG chốt số lượng: docstring trên nói rõ S2 (xếp hạng vector) sẽ đổi
    # tập chunk yếu này, chốt số là khoá cứng hành vi mà chính bài test không định khoá.
    assert hits, "phải ra vài chunk ankor điểm thấp — nếu rỗng thì ba phép loại trừ dưới vô nghĩa"
    assert all(h.tenant_id == ANKOR_ID for h in hits)
    assert not any("borea" in h.chunk_id for h in hits)
    assert not any("77 triệu" in h.text for h in hits)


async def test_sc05_cheo_vai_khong_ro_ri_chunk_ngoai_vai(kb: StaticKbSearch) -> None:
    """Mầm leak-test T6 — cạnh yếu nhất: RLS trong `schema.py` CHỈ khoá `tenant_id`, `section_role`
    không có RLS đứng sau. Hỏi từ vai `engineering` về thang lương (`hr`) phải không thấy gì."""
    hits = await kb.search("Thang lương của công ty gồm những bậc nào?", ANKOR_ID, ["engineering"], 5)
    assert hits == []

    # cùng câu hỏi, đúng vai `hr` thì thấy — chứng minh case trên rỗng vì LỌC VAI,
    # không phải vì câu hỏi không khớp gì trong kho.
    with_role = await kb.search("Thang lương của công ty gồm những bậc nào?", ANKOR_ID, ["hr"], 5)
    assert with_role[0].chunk_id == "ankor-salary-001#c1"


async def test_loc_truoc_roi_moi_cat_top_k(kb: StaticKbSearch) -> None:
    """Thứ tự quan trọng kể cả ở bản naive: cắt `top_k` trước rồi mới lọc sẽ để chunk ngoài phạm vi
    chiếm chỗ rồi bị loại — mất một kết quả hợp lệ, và số lượng trả về phụ thuộc dữ liệu của tenant
    khác. `top_k=1` với vai `finance` vẫn phải ra đúng chunk finance."""
    hits = await kb.search("Trưởng nhóm được duyệt chi tối đa bao nhiêu?", ANKOR_ID, ["finance"], 1)
    assert [h.chunk_id for h in hits] == ["ankor-expense-001#c2"]
