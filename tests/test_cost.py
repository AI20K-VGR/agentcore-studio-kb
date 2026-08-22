"""Cost-lineage — cộng dồn `cost` per-run (bút DE, D19, #120).

Hai tầng như `test_trace_reader.py`:
- **thuần** (`cost_of` · `aggregate_run_cost` · `price_mismatches`) — chạy KHÔNG cần Postgres.
- **DB** (`PgCostReader`) — cần Docker (`docker compose -f docker-compose.test.yml up -d`); thiếu DSN
  thì fixture `conftest.py` gốc **skip**.

Bất biến cắn nhất (§4.1 `trace-event.v0.md`): **aggregation CỘNG `event.cost` đã lưu, KHÔNG tính lại từ
tokens**. `test_aggregate_cong_cost_da_luu_khong_tinh_lai` khoá đúng điều đó — event có `cost` cố ý LỆCH
`cost_of(tokens)`, tổng phải theo cost đã lưu.
"""

from __future__ import annotations

import ast
from pathlib import Path
from uuid import UUID

import pytest
from studio_contracts.nodes import NodeType
from studio_contracts.trace import Tokens, TraceEvent
from studio_kb import cost as cost_mod
from studio_kb.cost import (
    CostAggregateError,
    PgCostReader,
    aggregate_run_cost,
    cost_of,
    price_mismatches,
)

ANKOR_ID = UUID("a0000000-0000-0000-0000-000000000001")
BOREA_ID = UUID("b0000000-0000-0000-0000-000000000001")


def _event(
    node_type: NodeType,
    *,
    event_id: str | None = None,
    run_id: str = "run-1",
    tenant_id: UUID = ANKOR_ID,
    tokens: Tokens | None = None,
    cost: float = 0.0,
    ts: str = "2026-08-13T09:00:00.000000+00:00",
) -> TraceEvent:
    """`TraceEvent` hợp lệ; chỉ khai field bài test quan tâm (mặc định `cost`/`tokens` = 0 như emit hôm nay)."""
    return TraceEvent(
        event_id=event_id or f"ev-{node_type.value}",
        run_id=run_id,
        agent_id="agent-callisto-d4",
        tenant_id=tenant_id,
        node_id=f"n-{node_type.value}",
        node_type=node_type,
        ts=ts,
        inputs_hash="sha256:stub",
        outputs={},
        tokens=tokens or Tokens(prompt=0, completion=0),
        cost=cost,
        citations=None,
    )


# ── tầng thuần ────────────────────────────────────────────────────────────────────────────────────


def test_cost_of_tat_dinh_va_dung_don_gia() -> None:
    """`cost_of` = prompt/1k·0.003 + completion/1k·0.015, làm tròn 6 chữ số. Tokens=0 → 0."""
    assert cost_of(Tokens(prompt=0, completion=0)) == 0.0
    assert cost_of(Tokens(prompt=1000, completion=0)) == 0.003
    assert cost_of(Tokens(prompt=1000, completion=1000)) == 0.018
    assert cost_of(Tokens(prompt=137, completion=42)) == round(137 / 1000 * 0.003 + 42 / 1000 * 0.015, 6)


def test_aggregate_cong_cost_da_luu_khong_tinh_lai() -> None:
    """§4.1: aggregation CỘNG `event.cost` đã lưu, KHÔNG tính lại `cost_of(tokens)`.

    Event dưới có `cost` LỆCH hẳn `cost_of(tokens)` (tokens=1000/1000 → cost_of=0.018, nhưng lưu 0.5).
    Nếu aggregation lỡ tính lại từ tokens, tổng sẽ ra 0.036; đúng luật thì phải là 1.0 (0.5+0.5)."""
    events = [
        _event(NodeType.LLM_STEP, event_id="a", tokens=Tokens(prompt=1000, completion=1000), cost=0.5),
        _event(NodeType.TOOL_CALL, event_id="b", tokens=Tokens(prompt=1000, completion=1000), cost=0.5),
    ]
    rc = aggregate_run_cost(events)
    assert rc.cost == 1.0, "phải cộng cost ĐÃ LƯU (0.5+0.5), không tính lại từ tokens"
    assert rc.prompt_tokens == 2000
    assert rc.completion_tokens == 2000
    assert rc.event_count == 2
    assert rc.run_id == "run-1"
    assert rc.tenant_id == ANKOR_ID


def test_aggregate_rong_raise() -> None:
    with pytest.raises(CostAggregateError):
        aggregate_run_cost([])


def test_aggregate_tron_run_id_raise() -> None:
    events = [
        _event(NodeType.LLM_STEP, event_id="a", run_id="run-1"),
        _event(NodeType.LLM_STEP, event_id="b", run_id="run-2"),
    ]
    with pytest.raises(CostAggregateError, match="run_id"):
        aggregate_run_cost(events)


def test_aggregate_tron_tenant_raise_ho_inv1() -> None:
    """Trộn tenant khi cộng dồn là hở INV-1 — phải từ chối, bất kể RLS DB có bật hay không (lưới
    thứ hai ở tầng ứng dụng, không thay RLS mà bổ sung — GAP-1, `obs.trace_events` nay đã có RLS)."""
    events = [
        _event(NodeType.LLM_STEP, event_id="a", tenant_id=ANKOR_ID),
        _event(NodeType.LLM_STEP, event_id="b", tenant_id=BOREA_ID),
    ]
    with pytest.raises(CostAggregateError, match="tenant"):
        aggregate_run_cost(events)


def test_price_mismatches_bat_cost_lech_nguon_gia() -> None:
    """Lưới §4.1: event có `cost != cost_of(tokens)` bị chỉ mặt; khớp thì rỗng.

    Có cả ca lệch **nhỏ** (~1e-4): so phải là `!=` thô, không phải `round(…,2)` nới dung — nếu ai đó thêm
    tolerance cho 'đỡ nhiễu' thì `nho` lọt và lưới im (review kb#22 F3 · món nhỏ 2, mutant Z-3).
    """
    khop = _event(NodeType.LLM_STEP, event_id="ok", tokens=Tokens(prompt=1000, completion=0), cost=0.003)
    lech = _event(NodeType.LLM_STEP, event_id="bad", tokens=Tokens(prompt=1000, completion=0), cost=0.999)
    nho = _event(NodeType.LLM_STEP, event_id="tiny", tokens=Tokens(prompt=1000, completion=0), cost=0.0031)
    assert price_mismatches([khop]) == []
    assert price_mismatches([khop, lech]) == ["bad"]
    assert price_mismatches([nho]) == ["tiny"]  # cost_of=0.003, lệch 1e-4 vẫn phải bắt


def test_price_mismatches_hom_nay_toan_0_thi_khop() -> None:
    """Emit hôm nay: cost=0, tokens=0 → cost_of=0 → không lệch (honest-TODO: số thật khi AIE-1 nối)."""
    events = [_event(NodeType.KB_RETRIEVE, event_id="a"), _event(NodeType.LLM_STEP, event_id="b")]
    assert price_mismatches(events) == []


def test_khong_mat_doc_nao_ngoai_cost_py_goi_cost_of() -> None:
    """§4.1 "một số, ba mặt" dạng **test-được**: KHÔNG module đọc nào ngoài `cost.py` tham chiếu `cost_of`.

    Thay bài `test_cung_1_so_moi_mat_doc_cung_tong` cũ (review kb#22 F1): bài đó gọi cùng một hàm thuần
    hai lần rồi assert bằng nhau — `f(x)==f(x)` đúng với mọi hàm tất định, không mutant nào làm nó đỏ
    (một `aggregate_run_cost` trả hằng số vẫn PASS). "Cùng-1-số" nói về **các mặt đọc**, mà kb chỉ có một
    hàm cộng dồn, nên bất biến thật không phải "hai mặt ra cùng số" (hư cấu) mà là **không mặt nào tự
    tính**: recompute `tokens × giá` ở mặt đọc = có nguồn giá thứ hai (drift), vi phạm §4.1 kể cả khi ra
    đúng số. `cost_of` chỉ được sống trong `cost.py` (nguồn giá, dùng cho `price_mismatches`).

    Quét AST **đệ quy** `src/studio_kb/**/*.py` + `scripts/**/*.py` (mọi mặt đọc trong lane kb, kể cả
    subpackage sâu — `glob` một tầng để lọt file lồng, review kb#22 F3); bài DB
    `test_db_read_run_cost_khop_aggregate` mới là bài so hai-đường-thật (DB ↔ thuần), giữ nguyên.

    Canh cả hằng đơn giá (`PROMPT_RATE_PER_1K`/`COMPLETION_RATE_PER_1K`) và alias import (`cost_of as _x`):
    mặt đọc tự nhân `tokens × đơn giá` bằng chính hằng nguồn giá cũng là drift (review kb#22 F3 · món nhỏ 1).
    Còn số magic thô (`… * 0.003`) thì ngoài tầm quét-theo-tên — đó là trần đã biết, không phải bất biến ẩn.
    """
    src_pkg = Path(cost_mod.__file__).parent  # …/src/studio_kb
    kb_root = src_pkg.parent.parent  # …/packages/kb
    scripts_dir = kb_root / "scripts"
    # Guard xanh-giả: resolve sai gốc (cài non-editable) → glob rỗng → vi phạm lọt trong im lặng (F3).
    # Mỗi NGUỒN quét tự chứng minh nó còn sống — KHÔNG núp sau tổng của nguồn kia (review kb#22 lượt 3):
    # `len(surfaces) > 5` chỉ chứng minh TỔNG khác rỗng; nếu `src/` resolve rỗng thì riêng 9 file `scripts/`
    # vẫn thoả (9 > 5), 12 mặt đọc trong `src/` — nơi mọi mặt đọc lane kb thật sự sống — bị bỏ qua câm.
    assert scripts_dir.is_dir(), f"không thấy {scripts_dir} — quét rỗng thì bài này xanh giả"
    src_files = sorted(src_pkg.rglob("*.py"))
    script_files = sorted(scripts_dir.rglob("*.py"))
    assert len(src_files) >= 8, f"quét src/studio_kb chỉ được {len(src_files)} file — nghi resolve sai gốc"
    assert len(script_files) >= 4, f"quét scripts/ chỉ được {len(script_files)} file — nghi resolve sai gốc"
    surfaces = src_files + script_files

    price_names = {"cost_of", "PROMPT_RATE_PER_1K", "COMPLETION_RATE_PER_1K"}
    offenders: list[str] = []
    for path in surfaces:
        if path.name == "cost.py":
            continue  # nguồn giá duy nhất được phép giữ cost_of + đơn giá (price_mismatches)
        tree = ast.parse(path.read_text(encoding="utf-8"))
        watched = set(price_names)  # + alias cục bộ: `from …cost import cost_of as _gia` → canh cả `_gia`
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                watched |= {a.asname for a in node.names if a.name in price_names and a.asname}
        for node in ast.walk(tree):
            if (isinstance(node, ast.Name) and node.id in watched) or (
                isinstance(node, ast.Attribute) and node.attr in watched
            ):
                offenders.append(f"{path.relative_to(kb_root)}:{node.lineno}")

    assert offenders == [], f"mặt đọc tự tính cost qua nguồn giá (vi phạm §4.1 'không mặt nào tự tính'): {offenders}"


# ── tầng DB (cần Docker) ────────────────────────────────────────────────────────────────────────


async def _write(pool: object, events: list[TraceEvent]) -> None:
    """Ghi bằng chính sink `apps/studio` — không dựng lại đường ghi (trace-event.v0.md §7/F15)."""
    from studio_app.obs.trace_writer import PgTraceWriter

    writer = PgTraceWriter(pool)  # type: ignore[arg-type]
    for event in events:
        await writer.write(event)


async def test_db_read_run_cost_khop_aggregate(admin_pool: object, pool: object) -> None:
    """Vòng tròn: ghi event có cost thật → `PgCostReader.read_run_cost` = `aggregate_run_cost` cùng bộ."""
    del admin_pool  # chỉ cần thứ tự dựng schema
    events = [
        _event(
            NodeType.LLM_STEP, event_id="c-a", run_id="run-cost", tokens=Tokens(prompt=137, completion=42), cost=0.001
        ),
        _event(
            NodeType.TOOL_CALL, event_id="c-b", run_id="run-cost", tokens=Tokens(prompt=10, completion=5), cost=0.002
        ),
    ]
    await _write(pool, events)

    rc = await PgCostReader(pool).read_run_cost("run-cost", ANKOR_ID)  # type: ignore[arg-type]

    assert rc == aggregate_run_cost(events)
    assert rc.cost == 0.003
    assert rc.prompt_tokens == 147


async def test_db_read_run_cost_with_drift_canh_bao_lech(admin_pool: object, pool: object) -> None:
    """Đường CLI dùng (F2 review kb#22): event có `cost` LỆCH `cost_of(tokens)` bị chỉ mặt; khớp thì rỗng.

    Cùng round-trip Postgres `NUMERIC → Decimal → float` mà `price_mismatches` phải chịu thật (AIE-2 nghi
    dương-tính-giả nhưng đo 0 lệch) — bài này chạy nó qua DB, không chỉ tầng thuần.
    """
    del admin_pool
    lech = _event(
        NodeType.LLM_STEP, event_id="d-bad", run_id="run-drift", tokens=Tokens(prompt=1000, completion=0), cost=0.999
    )  # cost_of=0.003 nhưng lưu 0.999 → lệch
    khop = _event(
        NodeType.TOOL_CALL, event_id="d-ok", run_id="run-drift", tokens=Tokens(prompt=1000, completion=0), cost=0.003
    )  # cost_of=0.003, khớp
    await _write(pool, [lech, khop])

    rc, mismatches = await PgCostReader(pool).read_run_cost_with_drift("run-drift", ANKOR_ID)  # type: ignore[arg-type]

    assert mismatches == ["d-bad"], "chỉ event lệch nguồn giá bị chỉ mặt, sống qua round-trip NUMERIC→float"
    assert rc == aggregate_run_cost([lech, khop]), "cost vẫn CỘNG số đã lưu (§4.1), drift không đổi tổng"
    assert rc.cost == round(0.999 + 0.003, 6)


async def test_db_read_run_cost_khong_co_run_raise(admin_pool: object, pool: object) -> None:
    del admin_pool
    with pytest.raises(CostAggregateError):
        await PgCostReader(pool).read_run_cost("run-khong-co-that", ANKOR_ID)  # type: ignore[arg-type]


async def test_db_tenant_khac_khong_lot_vao_cost(admin_pool: object, pool: object) -> None:
    """Hàng rào tenant: event borea KHÔNG được lọt vào cost của ankor (2 lớp — WHERE tenant_id ở
    query + RLS thật từ GAP-1; bài này khoá kết quả cuối, không khoá cơ chế nào cụ thể)."""
    del admin_pool
    await _write(pool, [_event(NodeType.LLM_STEP, event_id="bo", run_id="run-x", tenant_id=BOREA_ID, cost=9.9)])
    await _write(pool, [_event(NodeType.LLM_STEP, event_id="an", run_id="run-x", tenant_id=ANKOR_ID, cost=0.01)])

    rc = await PgCostReader(pool).read_run_cost("run-x", ANKOR_ID)  # type: ignore[arg-type]

    assert rc.cost == 0.01, "cost borea (9.9) không được lọt vào tổng của ankor"
    assert rc.event_count == 1


async def test_db_list_run_ids_theo_tenant(admin_pool: object, pool: object) -> None:
    del admin_pool
    await _write(pool, [_event(NodeType.LLM_STEP, event_id="l1", run_id="run-l-ankor", tenant_id=ANKOR_ID)])
    await _write(pool, [_event(NodeType.LLM_STEP, event_id="l2", run_id="run-l-borea", tenant_id=BOREA_ID)])

    runs = await PgCostReader(pool).list_run_ids(ANKOR_ID)  # type: ignore[arg-type]

    assert "run-l-ankor" in runs
    assert "run-l-borea" not in runs, "run của borea không được hiện trong list của ankor"
