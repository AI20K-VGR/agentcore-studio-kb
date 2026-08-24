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

from psycopg import AsyncConnection, sql
from psycopg_pool import AsyncConnectionPool
from studio_contracts.nodes import NodeType
from studio_contracts.recipe import Dag
from studio_contracts.trace import Tokens, TraceEvent

Pool = AsyncConnectionPool[AsyncConnection[Any]]

EXPECTED_WALK: tuple[NodeType, ...] = (
    NodeType.KB_RETRIEVE,
    NodeType.LLM_STEP,
    NodeType.END,
)
"""Chuỗi node **mặc định** — 3 node, đúng với recipe D4/D6 của SWE.

⚠️ **Đây không còn là nguồn sự thật.** Tới D6 (#27) AIE-1 đã bỏ hằng số
`studio_engine.interpreter._WALK_ORDER` và đi động theo `recipe.dag.edges`. Thứ tự node giờ do
**recipe quyết định**, không do một hằng số ở đây quyết định — nguồn đúng là
`walk_from_dag(recipe.dag)`.

Hằng số này ở lại vì hai lý do, không phải vì quán tính:

1. `create_recipe_d4`/`create_recipe_d6` đều dựng chuỗi thẳng `kb-retrieve → llm-step → end`
   (workbench#31, 2026-08-24: node `tool-call{kb_search}` — dead code, `kb_search` có kind
   `kb-retrieve` chứ không bao giờ là `tool-call` — đã bị xoá khỏi cả hai builder), nên nó vẫn là
   câu trả lời đúng cho mọi recipe đang chạy hôm nay;
2. nó là mặc định để gọi `check_walk(events)` một tham số lúc đang gỡ lỗi, khi trong tay chỉ có
   event chứ không có recipe.

`NodeType` có 6 giá trị nhưng ở đây chỉ 3: `tool-call` không recipe nào hiện dựng (xem lý do (1));
`condition` cần đánh giá `Edge.when` (chưa có — `_build_next_map` của engine **raise** khi một node
có >1 edge ra); `hitl-pause` cần lưu-và-tiếp-tục trạng thái run. So với 6 là báo thiếu oan ba node
không recipe nào hiện dựng.

**Khi chấm một run có recipe trong tay, truyền `expected=walk_from_dag(recipe.dag)`** — đừng dựa
vào hằng số này.
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


class RecipeWalkError(ValueError):
    """`dag` không mô tả một chuỗi đi được, nên không suy ra được chuỗi node kỳ vọng.

    Kiểu riêng vì cùng lý do như `TraceTimestampError`: phân biệt được "recipe có hình dạng sai"
    với "reader hỏng". Bốn hình dạng bị từ chối — xem `walk_from_dag`.
    """


def walk_from_dag(dag: Dag) -> tuple[NodeType, ...]:
    """Suy chuỗi `NodeType` mà interpreter SẼ đi, từ chính `recipe.dag`.

    Đây là thứ thay cho `EXPECTED_WALK` kể từ khi AIE-1 mở vòng đi động (#27): thứ tự node đến từ
    `dag.edges`, nên chuỗi kỳ vọng cũng phải đến từ đó. Dùng:

        check_walk(events, expected=walk_from_dag(recipe.dag))

    **Soi theo đúng `studio_engine.interpreter.run()`**, không phải một cách đi tự nghĩ ra. Bốn luật
    dưới đây chép lại nguyên vẹn hành vi của nó, kể cả các nhánh vỡ:

    1. **Đúng 1 node vào** (không edge nào trỏ tới) — `_find_start_node_id`. 0 nghĩa là cả đồ thị
       nằm trong vòng; >1 nghĩa là không biết bắt đầu từ đâu.
    2. **Mỗi node ≤ 1 edge ra** — `_build_next_map`. >1 là rẽ nhánh `condition`, mà `Edge.when`
       chưa được đánh giá ở phase này.
    3. **Không thăm lại node đã thăm** — biến `visited` trong vòng `while`. "Thòng lọng" (`a→b→b`)
       lọt cả hai luật trên và sẽ quay vô hạn.
    4. **Phải kết ở node `end`** — nhánh `next_id is None`. Hết edge trước khi tới `end` là run
       cụt, mà `RunResult` không mang cờ nào nói nó cụt nên không ai ở dưới phát hiện được.

    **Không import `studio_engine`** — `.importlinter` cấm quadrant chạm quadrant. Vì thế đây là
    bản chép, và bản chép thì trôi được: nếu engine đổi cách đi (đánh giá `when` chẳng hạn), hàm
    này phải đổi theo. Đổi mà quên thì reader báo thiếu/thừa oan, nên chỗ này neo bằng bảng trên.

    **Recipe có `condition` thì hàm này vỡ, và vỡ là đúng.** Khi rẽ nhánh chạy thật, tập node đi qua
    **phụ thuộc dữ liệu** — không có chuỗi kỳ vọng tĩnh nào tồn tại, nên đoán một chuỗi rồi chấm
    theo nó còn tệ hơn là không chấm. Lúc đó "0-gap" phải định nghĩa lại theo đường đi thực tế.
    """
    targets = {edge.to for edge in dag.edges}
    starts = [node.id for node in dag.nodes if node.id not in targets]
    if len(starts) != 1:
        raise RecipeWalkError(f"dag phải có đúng 1 node vào (không edge nào trỏ tới), thấy {len(starts)}: {starts}")

    next_by_id: dict[str, str] = {}
    for edge in dag.edges:
        if edge.from_ in next_by_id:
            raise RecipeWalkError(
                f"node {edge.from_!r} có >1 edge ra — rẽ nhánh `condition` chưa được đánh giá, "
                "không suy ra được một chuỗi kỳ vọng duy nhất"
            )
        next_by_id[edge.from_] = edge.to

    nodes_by_id = {node.id: node for node in dag.nodes}
    walk: list[NodeType] = []
    visited: set[str] = set()
    current_id = starts[0]
    while True:
        if current_id in visited:
            raise RecipeWalkError(f"dag có chu trình — node {current_id!r} bị thăm lại")
        if current_id not in nodes_by_id:
            raise RecipeWalkError(f"edge trỏ tới node {current_id!r} không tồn tại trong dag.nodes")
        visited.add(current_id)
        node_type = nodes_by_id[current_id].type
        walk.append(node_type)
        if node_type is NodeType.END:
            return tuple(walk)
        next_id = next_by_id.get(current_id)
        if next_id is None:
            raise RecipeWalkError(
                f"dag hết edge ở node {current_id!r} mà chưa tới node `end` — chuỗi cụt, "
                f"đã đi {len(visited)} node: {sorted(visited)}"
            )
        current_id = next_id


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


def check_ts_monotonic(events: list[TraceEvent]) -> int | None:
    """Kiểm `ts` có **đơn điệu không-giảm theo đúng thứ tự PHÁT** (thứ tự `events` được truyền vào,
    TRƯỚC khi `sort_events` xếp lại) không. Trả `None` nếu đơn điệu; nếu không, trả **index 1-based**
    của event đầu tiên có `ts` **nhỏ hơn** event ngay trước nó.

    Vì sao đo trên thứ tự gốc chứ không phải sau khi sort: sau `sort_events` mọi chuỗi đều đơn điệu —
    kiểm lúc đó luôn xanh, vô nghĩa. Câu hỏi thật là *"đường ghi có phát event đúng thứ tự thời gian
    không"* (bất biến D9 "0-gap ordering"); một `ts` giảm giữa dòng nghĩa là emit-hook ghi lệch hoặc
    đồng hồ nhảy lùi — reader phải **kêu** thay vì lặng lẽ sort đi rồi trông như mọi thứ vẫn ổn.

    **Trùng `ts` KHÔNG phải đảo** (dùng `<` chứ không `<=`): hai node chạy trong cùng mili-giây là
    chuyện bình thường (xem `sort_events`/`test_ts_trung_nhau`), không phải sự cố.

    **Đo trên `ts` (cột TEXT ISO-8601), không phải cột `seq/ordering`.** Reader hiện chỉ đọc `ts`
    (`_READ_RUN`); nếu sau này hợp đồng `trace-event.v0.md` chốt đo monotonic trên `seq` thì đổi ở
    đây + select thêm cột — honest-TODO, chưa mở rộng khi chưa cần (chốt với #104).
    """
    for i in range(1, len(events)):
        if _parse_ts(events[i].ts) < _parse_ts(events[i - 1].ts):
            return i + 1
    return None


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

    **`expected` lấy từ đâu.** Từ D6 (#27) interpreter đi theo `recipe.dag.edges`, nên chuỗi kỳ vọng
    thuộc về recipe chứ không thuộc về hằng số trong module này. Có recipe trong tay thì truyền
    `expected=walk_from_dag(recipe.dag)`; mặc định `EXPECTED_WALK` chỉ đúng vì mọi recipe hiện có
    (`create_recipe_d4`/`d6`) đều là chuỗi thẳng 3 node — nó là tiện lợi lúc gỡ lỗi, không phải
    hợp đồng.
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
        tokens = f"{event.tokens.prompt}/{event.tokens.completion}"
        lines.append(
            f"  {i}. {event.ts}  {event.node_type.value:<12} "
            f"node={event.node_id:<6} tok={tokens:<9} cost={event.cost:<8} citations=[{citations}]"
        )

    check = check_walk(ordered, expected)
    if check.ok:
        lines.append("  ✅ 0-gap — đủ node, mỗi node đúng 1 event")
    else:
        if check.missing:
            lines.append("  ❌ THIẾU node: " + ", ".join(nt.value for nt in check.missing))
        if check.duplicated:
            lines.append("  ❌ TRÙNG node: " + ", ".join(nt.value for nt in check.duplicated))

    # Ordering monotonic — đo trên thứ tự PHÁT gốc (`events`), KHÔNG phải `ordered`.
    # F1 (review AIE-2 #16): chỉ khẳng định được chiều PHỦ ĐỊNH. `check_ts_monotonic() is None` là
    # NHẬP NHẰNG — hoặc chuỗi phát đơn điệu thật, hoặc nguồn đã bị sort trước khi tới đây
    # (`PgTraceReader.read_run` + `ORDER BY ts` LUÔN trả None cho mọi run). `render_timeline` không
    # phân biệt được hai ca đó từ `ts`, nên **fail-closed**: không in `✅` mình không chứng minh được.
    # Một dòng nói thẳng "chưa kết luận" tốt hơn một `✅` sai. Đo chắc thứ tự phát cần cột `seq`/
    # thứ tự chèn (đường thật hôm nay không khôi phục được — xem `check_ts_monotonic`, chốt với #104).
    inversion = check_ts_monotonic(events)
    if inversion is not None:
        lines.append(
            f"  ⚠ ordering KHÔNG monotonic — ts giảm tại event {inversion} "
            "(đường ghi phát lệch thứ tự; đã sort lại để hiển thị)"
        )
    else:
        lines.append(
            "  ◦ ordering: chưa kết luận monotonic từ nguồn này — ts không giảm, nhưng chuỗi có thể "
            "đã được sort thượng nguồn (read_run/ORDER BY ts); đo chắc cần cột seq"
        )
    return "\n".join(lines)


class PgTraceReader:
    """Đọc `obs.trace_events` từ Postgres.

    RLS production trên bảng này đang land (GAP-1, mini-RFC
    `packages/kb/docs/mini-rfc-tenant-schema-unify.md`, phần B đã ký đủ 4/4) — `apps/studio/obs/
    schema.py` sẽ bật `ENABLE`+`FORCE ROW LEVEL SECURITY`. Trước đây mệnh đề `tenant_id` trong câu
    SQL là hàng rào DUY NHẤT; giờ là lớp THỨ HAI bổ cho RLS, đúng khuôn `kb.chunks` đã có — nhưng để
    lớp RLS đó thật sự cho INSERT/SELECT của kết nối này đi qua, `read_run` phải tự `SET LOCAL
    app.tenant_id` trên CHÍNH transaction nó mở, cùng idiom `PgTraceWriter.write()`
    (`apps/studio/obs/trace_writer.py`) đã dùng cho phía ghi — thiếu dòng này, `WITH CHECK`/`USING`
    của policy sẽ thấy session chưa set gì → 0 dòng, kể cả khi WHERE tenant_id đã đúng.
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
            await conn.execute(sql.SQL("SET LOCAL app.tenant_id = {}").format(sql.Literal(str(tenant_id))))
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
