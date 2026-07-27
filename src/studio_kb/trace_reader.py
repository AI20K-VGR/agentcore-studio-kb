"""`trace` reader — đọc lại timeline một run từ `obs.trace_events` (bút DE, D5).

Đây là phía **ĐỌC** của tầng quan trắc. Phía **GHI** (`PgTraceWriter` + bảng 12 cột) đã tồn tại đầy
đủ ở `apps/studio/src/studio_app/obs/`, nơi DE chỉ có quyền READ — module này **tiêu thụ** cái đã
có, tuyệt đối không dựng lại. Ranh giới đó mentor chốt 24/07 (issue #21).

**Không import `studio_app`.** `.importlinter` cấm quadrant chạm composition-root; pool đi vào qua
tham số constructor, y hệt cách `PgKbSearch` nhận pool. Cùng lý do đó, module này đọc bảng bằng SQL
thô thay vì mượn helper của app.

Chia làm hai tầng có chủ đích:

| tầng | gồm | kiểm được khi KHÔNG có Postgres? |
|---|---|---|
| **thuần** | `sort_events` · `check_walk` · `render_timeline` | ✅ có — đây là toàn bộ phần logic |
| **DB** | `PgTraceReader.read_run` | ❌ cần DB sống |

Tách vậy vì phần dễ sai là **logic sắp xếp và phát hiện thiếu node**, mà phần đó không cần DB để
chứng minh. Gói tất cả vào một hàm chạm DB thì mọi bài test đều phải dựng Docker, và bài test khó
dựng là bài test không ai chạy.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool
from studio_contracts.nodes import NodeType
from studio_contracts.trace import Tokens, TraceEvent

Pool = AsyncConnectionPool[AsyncConnection[Any]]

EXPECTED_WALK: tuple[NodeType, ...] = (
    NodeType.KB_RETRIEVE,
    NodeType.LLM_STEP,
    NodeType.TOOL_CALL,
    NodeType.END,
)
"""Chuỗi node kỳ vọng của một run — **4 node, không phải 6**.

`NodeType` có 6 giá trị, nhưng `studio_engine.interpreter._WALK_ORDER` hardcode đúng 4 node
(`kb-retrieve → llm-step → tool-call → end`); `condition` và `hitl-pause` **không bao giờ chạy** ở
giai đoạn này (đọc `recipe.dag.edges` để đi động là Day-6 scope, phase hiện tại cấm). So với 6 là
báo thiếu oan hai node vốn không được dispatch.

Tham số hoá được ở `check_walk(expected=...)`: khi AIE-1 mở vòng đi động, truyền chuỗi thật của
recipe vào thay vì sửa hằng số này.
"""

_READ_RUN = """
SELECT event_id, run_id, agent_id, tenant_id, node_id, node_type, ts,
       inputs_hash, outputs, tokens, cost, citations
FROM obs.trace_events
WHERE run_id = %s AND tenant_id = %s
ORDER BY ts, event_id
"""


class TraceTimestampError(ValueError):
    """`ts` không parse được thành ISO-8601.

    Có kiểu riêng thay vì `ValueError` trần để test khẳng định được **đúng lý do vỡ**: một bài
    `pytest.raises(ValueError)` sẽ xanh cả khi hàm vỡ vì lý do khác hoàn toàn.
    """


def _parse_ts(raw: str) -> datetime:
    """Parse `ts` (cột **TEXT**, chứa ISO-8601) thành `datetime`. Hỏng thì **raise**.

    Vì sao không tin `ORDER BY ts` của SQL: cột là `TEXT`, nên đó là **so chuỗi**. So chuỗi chỉ trùng
    với thứ tự thời gian khi mọi timestamp cùng định dạng và cùng độ dài — có/không `Z`, có/không
    micro-giây, lệch múi giờ đều làm thứ tự sai. Và sai **im lặng**: không có ngoại lệ nào nổi lên,
    timeline chỉ đơn giản hiện ra sai thứ tự.

    Raise thay vì bỏ qua dòng hỏng: một event không đọc được **là** một sự cố quan trắc. Lặng lẽ giữ
    nguyên thứ tự đọc từ DB sẽ cho ra một timeline trông vẫn hợp lý mà không ai biết là nó sai.
    """
    try:
        return datetime.fromisoformat(raw)
    except (ValueError, TypeError) as exc:
        raise TraceTimestampError(f"ts không phải ISO-8601: {raw!r}") from exc


def sort_events(events: list[TraceEvent]) -> list[TraceEvent]:
    """Xếp event theo thời gian tăng dần.

    **Không** assert `ts` tăng nghiêm ngặt: hai node chạy trong cùng một mili-giây hoàn toàn có thể
    trùng `ts`, đó là chuyện bình thường chứ không phải lỗi. Trùng `ts` thì giữ nguyên thứ tự đầu
    vào (`sorted` của Python ổn định) — mà đầu vào từ `read_run` đã có `ORDER BY ts, event_id`, nên
    kết quả **tất định** giữa các lần chạy thay vì đổi theo thứ tự Postgres trả về.

    Việc kiểm "có sót node không" **không** nằm ở đây — xem `check_walk`. Trộn hai việc lại là chỗ
    dễ sai nhất của reader: dùng khoảng cách thời gian để suy ra thiếu node sẽ báo động giả mỗi khi
    một node chạy lâu.
    """
    return sorted(events, key=lambda e: _parse_ts(e.ts))


@dataclass(frozen=True, slots=True)
class WalkCheck:
    """Kết quả đối chiếu **tập node đã emit** với **chuỗi node kỳ vọng**."""

    missing: tuple[NodeType, ...]
    """Node có trong chuỗi kỳ vọng nhưng KHÔNG có event nào — đây là "gap"."""

    duplicated: tuple[NodeType, ...]
    """Node có nhiều hơn 1 event. Luật là *"mọi node emit event"*, số ít — hai event cho cùng một
    node nghĩa là emit-hook chạy hai lần, cũng sai như thiếu, và cũng phải kêu."""

    @property
    def ok(self) -> bool:
        """`True` khi **0-gap**: đủ node, mỗi node đúng 1 event."""
        return not self.missing and not self.duplicated


def check_walk(
    events: list[TraceEvent],
    expected: tuple[NodeType, ...] = EXPECTED_WALK,
) -> WalkCheck:
    """Đối chiếu event đã emit với chuỗi node kỳ vọng.

    **"0-gap" nghĩa là "không sót node", không phải "thời gian liên tục".** Hai cách hiểu này cho ra
    hai reader khác hẳn nhau, nên chốt bằng chữ ở đây (và ở `docs/contracts/trace-event.v0.md`) thay
    vì để mỗi người đọc code tự suy:

    - *thời gian liên tục* — không có khoảng trống giữa các `ts`. **Vô nghĩa**: node chạy nhanh chậm
      khác nhau là bình thường, mọi run đều sẽ "có gap".
    - *không sót node* — mỗi node trong chuỗi phải có **đúng một** event. ← chọn cái này, đúng chữ
      DoD *"Mọi node của 1 run emit event (không sót node)"*.

    So theo `node_type` chứ không theo `node_id`: `node_id` do người viết recipe đặt (`"n1"`,
    `"n2"`…), không đoán trước được; `node_type` thuộc tập đóng 6 giá trị và là thứ chuỗi kỳ vọng
    nói tới.
    """
    counts: dict[NodeType, int] = {}
    for event in events:
        counts[event.node_type] = counts.get(event.node_type, 0) + 1

    return WalkCheck(
        missing=tuple(nt for nt in expected if counts.get(nt, 0) == 0),
        duplicated=tuple(nt for nt in expected if counts.get(nt, 0) > 1),
    )


def render_timeline(
    events: list[TraceEvent],
    expected: tuple[NodeType, ...] = EXPECTED_WALK,
) -> str:
    """In timeline cho người đọc, kèm kết luận 0-gap.

    Sắp xếp bên trong (gọi `sort_events`) để gọi trực tiếp trên kết quả thô cũng ra đúng thứ tự —
    hàm này là thứ người ta gõ lúc đang gỡ lỗi, không phải lúc đang cẩn thận.

    Luôn nói rõ **đủ hay thiếu**: một reader chỉ biết in ra thì lúc nào cũng trông như thành công.
    Dòng cuối là chỗ nó bắt buộc phải kêu.
    """
    if not events:
        return "(rỗng — không có event nào cho run này)"

    ordered = sort_events(events)
    run_id = ordered[0].run_id

    lines = [f"run {run_id} — {len(ordered)} event"]
    for i, event in enumerate(ordered, start=1):
        citations = ", ".join(event.citations) if event.citations else "—"
        lines.append(
            f"  {i}. {event.ts}  {event.node_type.value:<12} "
            f"node={event.node_id:<6} cost={event.cost:<8} citations=[{citations}]"
        )

    check = check_walk(ordered, expected)
    if check.ok:
        lines.append("  ✅ 0-gap — đủ node, mỗi node đúng 1 event")
    else:
        if check.missing:
            lines.append("  ❌ THIẾU node: " + ", ".join(nt.value for nt in check.missing))
        if check.duplicated:
            lines.append("  ❌ TRÙNG node: " + ", ".join(nt.value for nt in check.duplicated))
    return "\n".join(lines)


class PgTraceReader:
    """Đọc `obs.trace_events` từ Postgres.

    Bảng này **không có RLS** (khác hẳn `kb.chunks`) — trace là hành động của composition-root, không
    phải của tenant, nên không có policy nào chặn. Vì thế mệnh đề `tenant_id` trong câu SQL là hàng
    rào **duy nhất** ở đây, không phải lớp thứ hai bổ cho RLS như bên `kb.chunks`. Bỏ nó ra là đọc
    chéo tenant, và không có lưới nào đỡ.
    """

    def __init__(self, pool: Pool) -> None:
        self._pool = pool

    async def read_run(self, run_id: str, tenant_id: UUID) -> list[TraceEvent]:
        """Trả mọi event của `run_id` trong phạm vi `tenant_id`, đã xếp đúng thứ tự thời gian.

        `tenant_id` là **UUID**, không phải slug (D-13 — danh tính tenant là `core.tenants.id` bất
        biến, vì tên người-đọc-được thì trùng nhau được). Truyền `"ankor"` vào đây sẽ vỡ ngay ở
        psycopg với `invalid input syntax for type uuid` — vỡ to tiếng, đúng ý muốn: một hàng rào
        nhận nhầm kiểu mà vẫn chạy tiếp là hàng rào đã hỏng.

        `run_id` không tồn tại → trả `[]`, **không raise**: rỗng là một câu trả lời hợp lệ (chưa có
        event nào được ghi), không phải lỗi.
        """
        async with self._pool.connection() as conn:
            cursor = await conn.execute(_READ_RUN, (run_id, tenant_id))
            rows = await cursor.fetchall()

        return sort_events([_row_to_event(row) for row in rows])


def _row_to_event(row: tuple[Any, ...]) -> TraceEvent:
    """Dựng `TraceEvent` từ một dòng `obs.trace_events`, đúng thứ tự cột của `_READ_RUN`.

    `cost` là `NUMERIC` nên psycopg trả `Decimal` — ép `float` để khớp contract. `tokens`/`outputs`
    là `JSONB`, psycopg đã trả sẵn `dict`. `citations` `NULL` được → `None` là giá trị hợp lệ của
    contract, giữ nguyên chứ không đổi thành `[]`: "chưa có trích dẫn nào" và "không áp dụng" là hai
    chuyện khác nhau.
    """
    return TraceEvent(
        event_id=row[0],
        run_id=row[1],
        agent_id=row[2],
        tenant_id=row[3],
        node_id=row[4],
        node_type=NodeType(row[5]),
        ts=row[6],
        inputs_hash=row[7],
        outputs=row[8],
        tokens=Tokens(**row[9]),
        cost=float(row[10]),
        citations=row[11],
    )


if TYPE_CHECKING:  # pragma: no cover
    # Không có Protocol nào ở `studio_contracts` cho phía ĐỌC trace (`TraceWriter` chỉ mô tả phía
    # ghi), nên không có dòng conformance-check như `static_search.py`/`postgres.py`. Nếu sau này
    # seam `TraceReader` được thêm vào contracts, gắn kiểm ở đây theo đúng khuôn đó.
    pass
