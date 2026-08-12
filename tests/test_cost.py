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

from uuid import UUID

import pytest
from studio_contracts.nodes import NodeType
from studio_contracts.trace import Tokens, TraceEvent
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
    """Trộn tenant khi cộng dồn là hở INV-1 (`obs.trace_events` không RLS) — phải từ chối."""
    events = [
        _event(NodeType.LLM_STEP, event_id="a", tenant_id=ANKOR_ID),
        _event(NodeType.LLM_STEP, event_id="b", tenant_id=BOREA_ID),
    ]
    with pytest.raises(CostAggregateError, match="tenant"):
        aggregate_run_cost(events)


def test_price_mismatches_bat_cost_lech_nguon_gia() -> None:
    """Lưới §4.1: event có `cost != cost_of(tokens)` bị chỉ mặt; khớp thì rỗng."""
    khop = _event(NodeType.LLM_STEP, event_id="ok", tokens=Tokens(prompt=1000, completion=0), cost=0.003)
    lech = _event(NodeType.LLM_STEP, event_id="bad", tokens=Tokens(prompt=1000, completion=0), cost=0.999)
    assert price_mismatches([khop]) == []
    assert price_mismatches([khop, lech]) == ["bad"]


def test_price_mismatches_hom_nay_toan_0_thi_khop() -> None:
    """Emit hôm nay: cost=0, tokens=0 → cost_of=0 → không lệch (honest-TODO: số thật khi AIE-1 nối)."""
    events = [_event(NodeType.KB_RETRIEVE, event_id="a"), _event(NodeType.LLM_STEP, event_id="b")]
    assert price_mismatches(events) == []


def test_cung_1_so_moi_mat_doc_cung_tong() -> None:
    """ "Cùng-1-số": mọi mặt đọc phải ra cùng tổng vì cùng gọi `aggregate_run_cost` trên cùng event —
    không mặt nào tự tính. Ở đây mô phỏng 2 mặt (reader expose ↔ số CLI in) đọc cùng nguồn."""
    events = [
        _event(NodeType.LLM_STEP, event_id="a", cost=0.001234),
        _event(NodeType.TOOL_CALL, event_id="b", cost=0.000766),
    ]
    surface_reader = aggregate_run_cost(events).cost
    surface_cli = aggregate_run_cost(events).cost
    assert surface_reader == surface_cli == 0.002


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


async def test_db_read_run_cost_khong_co_run_raise(admin_pool: object, pool: object) -> None:
    del admin_pool
    with pytest.raises(CostAggregateError):
        await PgCostReader(pool).read_run_cost("run-khong-co-that", ANKOR_ID)  # type: ignore[arg-type]


async def test_db_tenant_khac_khong_lot_vao_cost(admin_pool: object, pool: object) -> None:
    """Hàng rào tenant: event borea KHÔNG được lọt vào cost của ankor (obs.trace_events không RLS)."""
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
