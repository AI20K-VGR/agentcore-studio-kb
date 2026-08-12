"""Cost-lineage — cộng dồn `cost` per-run từ `obs.trace_events` (bút DE, D19, #120).

Đây là phía **CỘNG DỒN** (downstream) của cost-lineage. Luật F15 / `docs/contracts/trace-event.v0.md`
§7: `write()` là INSERT trần, **cộng dồn là việc của DE, KHÔNG thuộc seam ghi** — module này tiêu thụ
event thô (nguồn duy nhất) và suy ra số tổng, không đụng đường ghi.

## §4.1 (FROZEN) — một số, ba mặt

`cost` tính **ĐÚNG MỘT LẦN tại điểm emit**; UI-test · trace viewer · cost dashboard chỉ **ĐỌC LẠI**.
Nên `aggregate_run_cost` **CỘNG `event.cost` đã lưu** — **KHÔNG** tính lại `tokens × đơn giá` ở mặt đọc.
Recompute ở mặt đọc = vi phạm §4.1 *kể cả khi ra đúng cùng số* (hôm sau đơn giá đổi một chỗ là ba mặt
lệch mà không ai biết mặt nào đúng). Đây là lý do `cost_of` (dưới) **không** được gọi trong aggregation.

## `cost_of` + bảng đơn giá — nguồn giá duy nhất, áp tại EMIT (chưa nối)

`cost_of` là **nguồn giá** (đơn giá) — thứ áp `tokens → cost` **một lần** tại điểm emit (interpreter).
Ở đây nó chỉ dùng để **KIỂM** (`price_mismatches`), tuyệt đối không phải để mặt đọc tính cost.

**Trạng thái nối (điểm ghép AIE-1, #121):** interpreter đang để `cost=_NO_COST=0.0`
(`engine:interpreter.py:300`), executor chỉ cấp `tokens` (Q-3 ✅, engine#15). Số cost thật xuất hiện khi
AIE-1 **wire `cost_of` lúc emit**. Vì §4.1 cấm hai nơi tính, `cost_of` cuối cùng phải nằm nơi
interpreter import được — **`contracts`** (Q-A, `trace-event.v0.md §8`) — mà DE **không sửa `contracts`**
(GITFLOWS §5). Nên bản kb này là **đề xuất-tham chiếu + lưới kiểm**; tới khi nó land ở `contracts` và
AIE-1 nối, `event.cost` còn 0 và `aggregate_run_cost` trả 0 — honest-TODO, không tô hồng.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool
from studio_contracts.trace import Tokens, TraceEvent

from studio_kb.trace_reader import PgTraceReader

Pool = AsyncConnectionPool[AsyncConnection[Any]]

# ── Bảng đơn giá (USD / 1000 token) — NGUỒN GIÁ DUY NHẤT ──────────────────────────────────────────
# Giá trị placeholder-deterministic (không mạng/không thời gian): cost-lineage kiểm BẤT BIẾN "một số,
# ba mặt", không kiểm độ chính xác giá thị trường. Đơn giá theo model là honest-TODO (§failure-mode):
# `TraceEvent` chưa mang `model`, nên hôm nay một mức phẳng cho mọi node.
PROMPT_RATE_PER_1K = 0.003
COMPLETION_RATE_PER_1K = 0.015


def cost_of(tokens: Tokens) -> float:
    """`tokens → cost` (USD) — nguồn giá duy nhất, áp **một lần tại điểm emit** (§4.1).

    Ở tầng kb dùng để **KIỂM** (`price_mismatches`), KHÔNG để mặt đọc tính cost. Tất định: cùng tokens
    luôn ra cùng số (làm tròn 6 chữ số để tổng cộng dồn không trôi float)."""
    return round(
        tokens.prompt / 1000 * PROMPT_RATE_PER_1K + tokens.completion / 1000 * COMPLETION_RATE_PER_1K,
        6,
    )


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

    Cùng luật hàng rào: `obs.trace_events` không có RLS, nên mọi truy vấn ở đây phải mang `tenant_id`.
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
            cur = await conn.execute(_LIST_RUNS, (tenant_id,))
            rows = await cur.fetchall()
        return [row[0] for row in rows]
