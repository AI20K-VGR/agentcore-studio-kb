"""Cost-lineage — cộng dồn `cost` per-run từ `obs.trace_events` (bút DE, D19, #120).

Đây là phía **CỘNG DỒN** (downstream) của cost-lineage. Luật F15 / `docs/contracts/trace-event.v0.md`
§7: `write()` là INSERT trần, **cộng dồn là việc của DE, KHÔNG thuộc seam ghi** — module này tiêu thụ
event thô (nguồn duy nhất) và suy ra số tổng, không đụng đường ghi.

## §4.1 (FROZEN) — một số, ba mặt

`cost` tính **ĐÚNG MỘT LẦN tại điểm emit**; UI-test · trace viewer · cost dashboard chỉ **ĐỌC LẠI**.
Nên `aggregate_run_cost` **CỘNG `event.cost` đã lưu** — **KHÔNG** tính lại `tokens × đơn giá` ở mặt đọc.
Recompute ở mặt đọc = vi phạm §4.1 *kể cả khi ra đúng cùng số* (hôm sau đơn giá đổi một chỗ là ba mặt
lệch mà không ai biết mặt nào đúng). Đây là lý do `cost_of` (dưới) **không** được gọi trong aggregation.

## `cost_of` + bảng đơn giá — đã nối (engine#38)

`cost_of`/`PROMPT_RATE_PER_1K`/`COMPLETION_RATE_PER_1K` **không còn định nghĩa ở đây** — dời xuống
`studio_contracts.cost` (mini-RFC `packages/contracts/docs/mini-rfc-cost-of-seam.md`) vì `.importlinter`
cấm `studio_engine` import `studio_kb`, mà đúng theo §4.1, `cost_of` phải áp **tại điểm emit**
(`studio_engine.interpreter`/`studio_engine.agent_loop`), không phải ở mặt đọc kb này. Ba tên dưới
được **re-export** để mọi call-site cũ trong package này (`price_mismatches`, test) không phải đổi gì.

Trạng thái nối: `interpreter.py`/`agent_loop.py` giờ gọi `cost=cost_of(tokens)` ngay tại dòng dựng
`TraceEvent` — engine#38 đóng, #121 đóng. `price_mismatches()` dưới vẫn là lưới kiểm (§4.1): nó KHÔNG
tự tính cost, chỉ so `event.cost` đã lưu với `cost_of(tokens)` để bắt drift nếu có nơi thứ hai tính giá.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from psycopg import AsyncConnection, sql
from psycopg_pool import AsyncConnectionPool
from studio_contracts.cost import COMPLETION_RATE_PER_1K, PROMPT_RATE_PER_1K, cost_of
from studio_contracts.trace import TraceEvent

from studio_kb.trace_reader import PgTraceReader

Pool = AsyncConnectionPool[AsyncConnection[Any]]

__all__ = [
    "COMPLETION_RATE_PER_1K",
    "PROMPT_RATE_PER_1K",
    "CostAggregateError",
    "PgCostReader",
    "RunCost",
    "aggregate_run_cost",
    "cost_of",
    "price_mismatches",
]


class CostAggregateError(ValueError):
    """Không cộng dồn được — kiểu riêng (không `ValueError` trần) để test khẳng định đúng lý do vỡ.

    Hai ca: (a) không có event nào cho run → không suy ra được `run_id`/`tenant_id`; (b) event trộn
    nhiều `run_id` hoặc nhiều `tenant_id` → "cost table PER-RUN" mất nghĩa, và trộn tenant là hở INV-1.
    """


@dataclass(frozen=True, slots=True)
class RunCost:
    """Tổng cost + tokens của **một** run, trong phạm vi **một** tenant. Một dòng của cost table per-run."""

    run_id: str
    tenant_id: UUID
    prompt_tokens: int
    completion_tokens: int
    cost: float
    event_count: int


def aggregate_run_cost(events: list[TraceEvent]) -> RunCost:
    """Cộng dồn event thô của **một** run → `RunCost`. **CỘNG `event.cost` đã lưu** (§4.1), không tính lại.

    Yêu cầu mọi event cùng một `run_id` VÀ một `tenant_id`: "per-run" mất nghĩa nếu trộn run, và trộn
    tenant là hở INV-1 (`obs.trace_events` KHÔNG có RLS — `tenant_id` là hàng rào duy nhất, xem
    `PgTraceReader`). Rỗng/trộn → `CostAggregateError`, không nuốt lỗi thành số 0 lặng lẽ.
    """
    if not events:
        raise CostAggregateError("không có event nào — không suy ra được run_id/tenant_id để cộng dồn")

    run_ids = {e.run_id for e in events}
    if len(run_ids) != 1:
        raise CostAggregateError(f"cost table per-run: event trộn nhiều run_id {sorted(run_ids)}")
    tenant_ids = {e.tenant_id for e in events}
    if len(tenant_ids) != 1:
        raise CostAggregateError(f"trộn tenant_id {sorted(map(str, tenant_ids))} — hở INV-1, từ chối cộng dồn")

    return RunCost(
        run_id=next(iter(run_ids)),
        tenant_id=next(iter(tenant_ids)),
        prompt_tokens=sum(e.tokens.prompt for e in events),
        completion_tokens=sum(e.tokens.completion for e in events),
        cost=round(sum(e.cost for e in events), 6),  # CỘNG cost đã lưu — KHÔNG cost_of (§4.1)
        event_count=len(events),
    )


def price_mismatches(events: list[TraceEvent]) -> list[str]:
    """`event_id` nào có `event.cost != cost_of(tokens)` — bằng chứng emit KHÔNG dùng nguồn giá duy nhất.

    Lưới răng cho §4.1: khi AIE-1 wire cost lúc emit, mỗi `event.cost` phải bằng `cost_of(tokens)` của
    chính nó. Lệch = có nơi thứ hai tính giá (drift). Hôm nay mọi cost=0 và tokens=0 → `cost_of=0`, khớp;
    ngày tokens thành thật mà quên nối giá, hàm này chỉ ra ngay event lệch thay vì để số sai trôi.
    """
    return [e.event_id for e in events if e.cost != cost_of(e.tokens)]


_LIST_RUNS = """
SELECT DISTINCT run_id
FROM obs.trace_events
WHERE tenant_id = %s
ORDER BY run_id
"""


class PgCostReader:
    """Đọc cost per-run từ Postgres — **tái dùng** `PgTraceReader.read_run` (không dựng lại đường đọc).

    RLS production trên `obs.trace_events` đang land (GAP-1, mini-RFC B đã ký đủ 4/4) — mọi truy vấn
    ở đây vẫn phải mang `tenant_id` (WHERE, lớp phòng thủ thứ hai) VÀ tự `SET LOCAL app.tenant_id`
    trên connection nó mở (lớp RLS thật). `read_run_cost`/`read_run_cost_with_drift` được vá miễn phí
    vì đi qua `PgTraceReader.read_run` (đã tự set); `list_run_ids` mở connection RIÊNG với query thô
    nên phải tự set lấy, không thể mượn.
    """

    def __init__(self, pool: Pool) -> None:
        self._pool = pool
        self._reader = PgTraceReader(pool)

    async def read_run_cost(self, run_id: str, tenant_id: UUID) -> RunCost:
        """Cost table một dòng cho `run_id` trong `tenant_id`. Run không tồn tại → `CostAggregateError`
        (khác `read_run` trả `[]`: ở đây "không có run" là câu hỏi sai, không phải kết quả rỗng hợp lệ)."""
        events = await self._reader.read_run(run_id, tenant_id)
        return aggregate_run_cost(events)

    async def read_run_cost_with_drift(self, run_id: str, tenant_id: UUID) -> tuple[RunCost, list[str]]:
        """`RunCost` + `event_id` nào **lệch nguồn giá** (`price_mismatches`), đọc event **một lần**.

        Mặt đọc-cho-người (CLI/dashboard) gọi cái này để vừa in cost vừa **cảnh báo drift**: ngày AIE-1
        nối tokens thật mà quên nối `cost_of` lúc emit, danh sách lệch khác rỗng → CLI kêu ngay thay vì
        in một con số trông sạch (đúng ca F-1 trong failure-mode). `read_run_cost` giữ nguyên cho mặt
        chỉ-cần-số. Không tính lại cost ở đây (§4.1) — `price_mismatches` chỉ so `event.cost` với nguồn giá.
        """
        events = await self._reader.read_run(run_id, tenant_id)
        return aggregate_run_cost(events), price_mismatches(events)

    async def list_run_ids(self, tenant_id: UUID) -> list[str]:
        """Mọi `run_id` của `tenant_id` — để cost table quét từng run. `tenant_id` bắt buộc (hàng rào)."""
        async with self._pool.connection() as conn:
            await conn.execute(sql.SQL("SET LOCAL app.tenant_id = {}").format(sql.Literal(str(tenant_id))))
            cur = await conn.execute(_LIST_RUNS, (tenant_id,))
            rows = await cur.fetchall()
        return [row[0] for row in rows]
