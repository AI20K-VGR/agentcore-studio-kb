"""Canh bộ golden query cho grid `chunking×embedding` (D14, DE) — issue #95, tiêu thụ #96.

Ba nhóm assert, mỗi cái bắt một kiểu hỏng khác nhau (không phải ba cách viết lại cùng phép kiểm):

- **nhãn dương annotate-verified** — mỗi `expected_citation` phải truy xuất được TRONG scope người hỏi,
  và scope đó còn **≥2 ứng viên cùng `tenant`+`section_role`** (teeth, finding D11). Gõ sai một ký tự
  `chunk_id`, hoặc chọn câu hỏi mà fence lọc còn đúng 1 ứng viên, thì đỏ ở đây — không để lọt xuống #96.
- **case âm fence-kín** — câu T1/T6 phải để `expected_citation` rỗng VÀ không ứng viên nào rơi vào
  (`expected_tenant`, `expected_section_role`) bị hỏi chéo. Guard hồi quy nếu ai nới lỏng bộ lọc.
- **yaml == nguồn** — `golden/callisto-grid-queries-v0.yaml` phải trùng từng byte với `render_yaml()`;
  đây là cái duy nhất chứng minh file check-in không bị sửa tay lệch khỏi `grid_queries.GRID_CASES`.

Dùng `StaticKbSearch` (token-overlap, không cần Postgres) — đúng đường `scripts/annotate_golden.py`
sinh nhãn, nên test này là phép kiểm lại chính công cụ đã gán nhãn. Chất lượng embedding (dim-8 vs khác)
đo qua `PgKbSearch`/pgvector là việc #96, KHÔNG kiểm ở đây.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from studio_kb.doc_factory import load_callisto, resolve_tenant_id
from studio_kb.grid_queries import GRID_CASES, GridCase, render_yaml
from studio_kb.static_search import StaticKbSearch

_YAML_PATH = Path(__file__).resolve().parents[1] / "src" / "studio_kb" / "golden" / "callisto-grid-queries-v0.yaml"

# top_k rộng để ĐẾM hết ứng viên trong scope (StaticKbSearch cắt còn top_k), không phải đo rank.
_COUNT_K = 50

_POSITIVES = [c for c in GRID_CASES if not c.is_refusal]
_REFUSALS = [c for c in GRID_CASES if c.is_refusal]


@pytest.fixture
def kb() -> StaticKbSearch:
    return StaticKbSearch()


def test_co_du_ca_duong_lan_am() -> None:
    """Bộ phải có cả hai loại — nếu tách nhầm hết về một phía thì các test parametrize dưới rỗng lặng."""
    assert len(_POSITIVES) >= 2
    assert len(_REFUSALS) >= 2


@pytest.mark.parametrize("case", _POSITIVES, ids=[c.case_id for c in _POSITIVES])
async def test_case_duong_nhan_truy_xuat_duoc_va_con_it_nhat_2_ung_vien(case: GridCase, kb: StaticKbSearch) -> None:
    """Nhãn dương phải truy xuất được TRONG scope, và scope còn ≥2 ứng viên cùng tenant+section_role.

    Hai vế, cả hai đều là điều kiện của một golden query dùng được cho grid:
    - `expected_citation ⊆ ứng viên` — nhãn trỏ vào chunk THẬT lấy được, không phải id chết.
    - `≥2 ứng viên cùng scope` — fence không rút gọn còn 1, nên thứ hạng THẬT SỰ đo được embedding
      (teeth). Đây là điều `citation_accuracy` cần để có răng (finding D11).
    """
    hits = await kb.search(case.query, resolve_tenant_id(case.tenant), list(case.section_roles), _COUNT_K)
    ids = {hit.chunk_id for hit in hits}

    for citation in case.expected_citation:
        assert citation in ids, f"{case.case_id}: nhãn {citation!r} KHÔNG truy xuất được trong scope"

    same_scope = [h for h in hits if h.section_role == case.expected_section_role]
    assert len(same_scope) >= 2, (
        f"{case.case_id}: chỉ {len(same_scope)} ứng viên cùng vai {case.expected_section_role!r} "
        f"— không đủ teeth (cần ≥2 để ranking phân biệt được embedding)"
    )


@pytest.mark.parametrize("case", _REFUSALS, ids=[c.case_id for c in _REFUSALS])
async def test_case_am_fence_kin_khong_ro_ri(case: GridCase, kb: StaticKbSearch) -> None:
    """Case âm: `expected_citation` rỗng VÀ không ứng viên nào thuộc scope cấm (kho/vai bị hỏi chéo).

    `expected_citation == ()` là hình dạng refusal (`format.md` §4). Phần thứ hai kiểm fence THẬT: không
    một chunk nào của (`expected_tenant`, `expected_section_role`) — thứ mà người hỏi KHÔNG được phép —
    lọt vào kết quả. StaticKbSearch v0 lọc tenant+role nên điều này phải đúng; test khoá lại để ai nới
    lỏng bộ lọc (T1/T6) thì đỏ ngay.
    """
    assert case.expected_citation == (), f"{case.case_id}: case âm phải rỗng citation"

    hits = await kb.search(case.query, resolve_tenant_id(case.tenant), list(case.section_roles), _COUNT_K)
    forbidden_tenant = resolve_tenant_id(case.expected_tenant)
    leaked = [
        h.chunk_id for h in hits if h.tenant_id == forbidden_tenant and h.section_role == case.expected_section_role
    ]
    forbidden = f"{case.expected_tenant}/{case.expected_section_role}"
    assert not leaked, f"{case.case_id}: RÒ RỈ scope cấm {forbidden}: {leaked}"


def test_moi_nhan_duong_ton_tai_trong_corpus() -> None:
    """Mọi `expected_citation` (dương) phải là `chunk_id` thật trong corpus — chặn id chết ngay cả khi
    câu hỏi tình cờ không token-khớp (test trên đi qua search, test này đi thẳng vào tập chunk_id)."""
    corpus_ids = {chunk.chunk_id for chunk in load_callisto()}
    for case in _POSITIVES:
        for citation in case.expected_citation:
            assert citation in corpus_ids, f"{case.case_id}: {citation!r} không có trong corpus"


def test_yaml_tren_dia_trung_nguon_typed() -> None:
    """File yaml check-in PHẢI trùng từng byte với `render_yaml()`.

    Đây là assert đắt nhất và là cái duy nhất chứng minh yaml không bị sửa tay lệch khỏi `GRID_CASES`.
    Đỏ thì chạy `scripts/emit_grid_queries.py` rồi commit — có chủ đích là re-emit hợp lệ, vô tình thì
    `git diff` chỉ ra ngay đã lệch gì.
    """
    assert _YAML_PATH.read_text(encoding="utf-8") == render_yaml()
