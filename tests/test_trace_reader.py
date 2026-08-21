"""`trace_reader` — đọc lại timeline một run (DoD D5: *"đúng thứ tự + 0-gap"*).

Chia hai nhóm có chủ đích:

- **Nhóm thuần** (`sort_events` / `check_walk` / `render_timeline`) — chạy **không cần Postgres**.
  Đây là chỗ chứa toàn bộ logic dễ sai, nên nó phải chạy được trong mọi hoàn cảnh.
- **Nhóm DB** (`PgTraceReader.read_run`) — cần `docker compose -f docker-compose.test.yml up -d` và
  hai biến DSN; thiếu thì fixture ở `conftest.py` gốc **skip** (không fail).

Nhóm DB **không phụ thuộc** emit-hook (SWE #23) hay populate (AIE-1 #22): nó tự ghi event bằng
`PgTraceWriter` — thứ đã tồn tại đầy đủ ở `apps/studio` — rồi đọc lại. Đó là cách cắt phụ thuộc để
reader xong được trong ngày mà không chờ ai.

⚠️ Import `studio_app` chỉ xuất hiện **trong test**, không bao giờ trong `src/`. `.importlinter` ràng
buộc namespace `studio_kb` (tức `src/`), không ràng buộc thư mục test — và `conftest.py` ở repo cha
vốn đã import `studio_app` để dựng pool.
"""

from __future__ import annotations

from uuid import UUID

import pytest
from psycopg.errors import InvalidTextRepresentation
from studio_contracts.nodes import NodeType
from studio_contracts.trace import Tokens, TraceEvent
from studio_kb.trace_reader import (
    EXPECTED_WALK,
    PgTraceReader,
    TraceTimestampError,
    check_ts_monotonic,
    check_walk,
    render_timeline,
    sort_events,
)

# Danh tính tenant là UUID bất biến (D-13), slug "ankor"/"borea" chỉ còn là nhãn hiển thị.
# `ANKOR_ID` khớp nguyên văn hằng số SWE đã dùng (`studio_workbench/builder_d4.py:22`) để cả repo
# nói cùng một giá trị; `BOREA_ID` chưa ai đặt — theo cùng quy luật, chữ đầu khớp tên tenant.
ANKOR_ID = UUID("a0000000-0000-0000-0000-000000000001")
BOREA_ID = UUID("b0000000-0000-0000-0000-000000000001")


def _event(
    node_type: NodeType,
    ts: str,
    *,
    event_id: str | None = None,
    run_id: str = "run-1",
    tenant_id: UUID = ANKOR_ID,
    citations: list[str] | None = None,
    tokens: Tokens | None = None,
) -> TraceEvent:
    """Dựng một `TraceEvent` hợp lệ; chỉ khai những field bài test thực sự quan tâm."""
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
        cost=0.0,
        citations=citations,
    )


def _full_walk() -> list[TraceEvent]:
    """Một run đủ 4 node, ghi theo thứ tự thời gian tăng dần."""
    return [
        _event(NodeType.KB_RETRIEVE, "2026-07-24T09:00:00.000000+00:00"),
        _event(NodeType.LLM_STEP, "2026-07-24T09:00:01.000000+00:00"),
        _event(NodeType.TOOL_CALL, "2026-07-24T09:00:02.000000+00:00"),
        _event(NodeType.END, "2026-07-24T09:00:03.000000+00:00"),
    ]


# ─────────────────────────── nhóm THUẦN — không cần Postgres ───────────────────────────


def test_xao_tron_thu_tu_van_doc_ra_dung_thu_tu_ts() -> None:
    """DoD *"đúng thứ tự"*: đầu vào lộn xộn, đầu ra phải theo `ts` tăng dần."""
    walk = _full_walk()
    scrambled = [walk[2], walk[0], walk[3], walk[1]]

    ordered = sort_events(scrambled)

    assert [e.node_type for e in ordered] == [
        NodeType.KB_RETRIEVE,
        NodeType.LLM_STEP,
        NodeType.TOOL_CALL,
        NodeType.END,
    ]


def test_ts_trung_nhau_giu_nguyen_thu_tu_dau_vao_khong_raise() -> None:
    """Hai node chạy cùng mili-giây → `ts` trùng. Đó là bình thường, không phải lỗi.

    Không assert tăng NGHIÊM NGẶT — chỉ cần sắp ổn định và tất định. `sorted` của Python ổn định,
    nên thứ tự đầu vào được giữ; mà đầu vào từ `read_run` đã `ORDER BY ts, event_id`.
    """
    same = "2026-07-24T09:00:00.000000+00:00"
    events = [
        _event(NodeType.KB_RETRIEVE, same, event_id="ev-a"),
        _event(NodeType.LLM_STEP, same, event_id="ev-b"),
    ]

    ordered = sort_events(events)

    assert [e.event_id for e in ordered] == ["ev-a", "ev-b"]


def test_ts_sai_dinh_dang_thi_raise_khong_sap_bua() -> None:
    """Bẫy so-chuỗi: cột `ts` là TEXT. Định dạng hỏng phải **kêu**, không được lặng lẽ giữ nguyên
    thứ tự đọc từ DB — timeline sai im lặng là thứ khó lần ra nhất."""
    events = [
        _event(NodeType.KB_RETRIEVE, "2026-07-24T09:00:00+00:00"),
        _event(NodeType.LLM_STEP, "hôm qua lúc 9 giờ"),
    ]

    with pytest.raises(TraceTimestampError, match="ISO-8601"):
        sort_events(events)


def test_du_4_node_thi_0_gap() -> None:
    """DoD *"0-gap"*: đủ node, mỗi node đúng 1 event."""
    check = check_walk(_full_walk())

    assert check.ok
    assert check.missing == ()
    assert check.duplicated == ()


def test_bo_1_node_thi_reader_bao_thieu_khong_im_lang() -> None:
    """**Bài có răng.** Một reader chỉ biết in ra thì lúc nào cũng trông như thành công — đây là
    bài bắt buộc nó phải kêu. Cố ý bỏ `tool-call`."""
    walk = [e for e in _full_walk() if e.node_type is not NodeType.TOOL_CALL]

    check = check_walk(walk)

    assert not check.ok
    assert check.missing == (NodeType.TOOL_CALL,)


def test_mot_node_emit_hai_lan_cung_bi_bao() -> None:
    """Luật là *"mọi node emit event"* — số ít. Emit-hook chạy hai lần cũng sai như thiếu."""
    walk = _full_walk()
    walk.append(_event(NodeType.LLM_STEP, "2026-07-24T09:00:04.000000+00:00", event_id="ev-dup"))

    check = check_walk(walk)

    assert not check.ok
    assert check.duplicated == (NodeType.LLM_STEP,)


def test_khong_bao_thieu_condition_va_hitl_pause() -> None:
    """`NodeType` có 6 giá trị nhưng interpreter chỉ đi 4 (`_WALK_ORDER` hardcode). So với 6 là báo
    thiếu oan hai node vốn không bao giờ được dispatch ở phase này."""
    assert NodeType.CONDITION not in EXPECTED_WALK
    assert NodeType.HITL_PAUSE not in EXPECTED_WALK

    check = check_walk(_full_walk())

    assert check.ok


def test_render_timeline_noi_ro_du_hay_thieu() -> None:
    """Bản in phải kết luận, không chỉ liệt kê."""
    du = render_timeline(_full_walk())
    assert "0-gap" in du
    assert "run-1" in du

    thieu = render_timeline([e for e in _full_walk() if e.node_type is not NodeType.END])
    assert "THIẾU" in thieu
    assert "end" in thieu


def test_render_timeline_tu_sap_xep_dau_vao_lon_xon() -> None:
    """Gọi thẳng trên kết quả thô vẫn ra đúng thứ tự — hàm này là thứ người ta gõ lúc đang gỡ lỗi."""
    walk = _full_walk()
    out = render_timeline([walk[3], walk[1], walk[0], walk[2]])

    lines = [ln for ln in out.splitlines() if ln.strip().startswith(("1.", "2.", "3.", "4."))]
    assert "kb-retrieve" in lines[0]
    assert "end" in lines[3]


def test_run_rong_khong_raise() -> None:
    """Rỗng là câu trả lời hợp lệ, không phải lỗi."""
    assert sort_events([]) == []
    assert "rỗng" in render_timeline([])


def test_render_timeline_hien_tokens() -> None:
    """DoD D15 ô 1 (*"…+tokens+…"*): mỗi dòng phải phơi `tokens{prompt,completion}` từ event, không
    phải chỉ cost+citations như trước. Số lấy thẳng từ `event.tokens`, không tính lại."""
    walk = [
        _event(NodeType.KB_RETRIEVE, "2026-07-24T09:00:00.000000+00:00"),
        _event(
            NodeType.LLM_STEP,
            "2026-07-24T09:00:01.000000+00:00",
            tokens=Tokens(prompt=137, completion=42),  # khác nhau VÀ khác 0 để bắt hardcode
        ),
    ]

    out = render_timeline(walk)

    # Kiểm ĐÚNG THỨ TỰ, không chỉ "có mặt" — nếu không, hoán prompt/completion (`tok=42/137`) vẫn
    # lọt (F3, review AIE-2 #16). D19 dựng cost-lineage trên đúng 2 số này, hoán ở đây = sai số về sau.
    llm_line = next(ln for ln in out.splitlines() if "llm-step" in ln)
    assert "tok=137/42" in llm_line


def test_check_ts_monotonic_thu_tu_dung_tra_none() -> None:
    """Chuỗi `ts` không-giảm (kể cả trùng nhau) là đơn điệu → không có đảo, trả `None`."""
    same = "2026-07-24T09:00:00.000000+00:00"
    walk = [
        _event(NodeType.KB_RETRIEVE, "2026-07-24T09:00:00.000000+00:00", event_id="a"),
        _event(NodeType.LLM_STEP, same, event_id="b"),  # trùng ts — hợp lệ, không phải đảo
        _event(NodeType.TOOL_CALL, "2026-07-24T09:00:02.000000+00:00", event_id="c"),
    ]

    assert check_ts_monotonic(walk) is None


def test_check_ts_monotonic_ts_dao_tra_vi_tri_dau_tien() -> None:
    """`ts` GIẢM so với event ngay trước (theo thứ tự GỐC) → trả index 1-based của lần đầu đảo."""
    walk = [
        _event(NodeType.KB_RETRIEVE, "2026-07-24T09:00:02.000000+00:00", event_id="a"),
        _event(NodeType.LLM_STEP, "2026-07-24T09:00:01.000000+00:00", event_id="b"),  # đảo tại đây
    ]

    assert check_ts_monotonic(walk) == 2


def test_render_timeline_noi_ro_monotonic_hay_dao() -> None:
    """DoD D15 ô 1 (*"ordering monotonic"*): viewer NÓI RA thứ tự phát. F1 (review AIE-2 #16):
    `ts` không giảm là NHẬP NHẰNG (đơn điệu thật vs đã bị sort thượng nguồn) → **fail-closed**
    "chưa kết luận", KHÔNG in `✅`. Chỉ chiều ĐẢO mới khẳng định được (`⚠`).

    Hai nhánh phải mang **marker riêng biệt** — nếu chỉ kiểm chung chữ "monotonic" thì mutant
    "viewer luôn báo ⚠" (nhánh fail-closed không bao giờ chạy) vẫn lọt."""
    walk = _full_walk()

    # Không đảo (ts tăng) → fail-closed, KHÔNG phải ⚠, KHÔNG khẳng định monotonic.
    khong_dao = render_timeline(walk)
    assert "chưa kết luận" in khong_dao
    assert "⚠" not in khong_dao
    assert "KHÔNG monotonic" not in khong_dao

    # Gốc có ts đảo ở giữa → khẳng định ⚠, KHÔNG phải fail-closed.
    dao = render_timeline([walk[0], walk[2], walk[1], walk[3]])
    assert "⚠" in dao and "KHÔNG monotonic" in dao
    assert "chưa kết luận" not in dao


# ─────────────────────────── nhóm DB — cần Postgres sống ───────────────────────────


async def _write(pool: object, events: list[TraceEvent]) -> None:
    """Ghi event bằng chính sink đã có ở `apps/studio` — không dựng lại đường ghi."""
    from studio_app.obs.trace_writer import PgTraceWriter

    writer = PgTraceWriter(pool)  # type: ignore[arg-type]
    for event in events:
        await writer.write(event)


async def test_db_doc_lai_nguyen_ven_tung_truong(admin_pool: object, pool: object) -> None:
    """KHÓA phần còn thiếu của *"rebuild-read"* (`day-09.md:36`): đọc lại đúng **NỘI DUNG**, không
    chỉ đúng thứ tự.

    Mọi test DB khác trong file này chỉ khẳng định `node_type`, `event_id`, hoặc tập rỗng — tức là
    **thứ tự và danh tính**. Không bài nào kiểm payload đọc lên có khớp payload đã ghi. Đo được bằng
    cách đột biến từng cột trong `_row_to_event`:

        outputs     → 3 test đỏ, nhưng toàn ở `test_spine_live.py`
        inputs_hash → 1 test đỏ, cũng ở `test_spine_live.py`
        citations   → 2 test đỏ, cũng ở `test_spine_live.py`
        tokens      → KHÔNG ai đỏ
        cost        → KHÔNG ai đỏ

    `cost` là chỗ đau nhất: docstring của `TraceEvent` chốt *"`cost` must be the SAME number surfaced
    on all 3 downstream surfaces (UI test/trace/dashboard)"*. Reader trả `0.0` cho mọi event thì cả
    suite vẫn xanh, và ba mặt kia cùng hiển thị sai một cách nhất quán — kiểu hỏng không ai nghi ngờ.

    **Vì sao phải dựng event riêng thay vì dùng `_full_walk()`.** Factory `_event()` để mọi payload ở
    mặc định — `outputs={}`, `tokens=0/0`, `cost=0.0`, `citations=None` — mà đó đúng bằng giá trị một
    reader hỏng sẽ trả về. So sánh round-trip trên dữ liệu đó luôn xanh dù reader có đọc cột hay
    không. Event dưới đây cố ý cho mỗi trường một giá trị **không trùng mặc định nào**.

    So bằng `==` cả model thay vì liệt từng trường: `TraceEvent` là pydantic frozen nên `==` là so
    field-by-field, và cách này tự phủ luôn trường được thêm vào contract sau này — liệt tay thì
    trường mới lặng lẽ không ai kiểm, đúng kiểu hở mà bài này đang vá.
    """
    del admin_pool  # chỉ cần thứ tự dựng schema

    goc = TraceEvent(
        event_id="ev-payload-1",
        run_id="run-payload",
        agent_id="agent-callisto-d4",
        tenant_id=ANKOR_ID,
        node_id="n-kb-retrieve",
        node_type=NodeType.KB_RETRIEVE,
        ts="2026-07-30T09:00:00.000000+00:00",
        inputs_hash="sha256:0123456789abcdef",
        outputs={"chunks": [{"chunk_id": "ankor-leave-001#c1"}], "so_luong": 1},
        tokens=Tokens(prompt=137, completion=42),  # khác nhau VÀ khác 0
        cost=0.001234,  # khác 0, đủ lẻ để không trùng hằng số nào
        citations=["ankor-leave-001#c1", "ankor-expense-001#c2"],
    )
    await _write(pool, [goc])

    events = await PgTraceReader(pool).read_run("run-payload", ANKOR_ID)  # type: ignore[arg-type]

    assert events == [goc], "event đọc lại phải khớp từng trường với event đã ghi"


async def test_db_doc_lai_dung_thu_tu_va_bao_0_gap(admin_pool: object, pool: object) -> None:
    """Vòng tròn đầy đủ: ghi 4 event **xáo trộn thứ tự** → đọc lại đúng thứ tự, kết luận 0-gap."""
    del admin_pool  # chỉ cần thứ tự dựng schema
    walk = _full_walk()
    await _write(pool, [walk[2], walk[0], walk[3], walk[1]])

    events = await PgTraceReader(pool).read_run("run-1", ANKOR_ID)  # type: ignore[arg-type]

    assert [e.node_type for e in events] == list(EXPECTED_WALK)
    assert check_walk(events).ok


async def test_db_thieu_node_thi_bao_thieu(admin_pool: object, pool: object) -> None:
    """Cố ý không ghi `tool-call` → reader phải báo thiếu, không im lặng."""
    del admin_pool
    await _write(pool, [e for e in _full_walk() if e.node_type is not NodeType.TOOL_CALL])

    events = await PgTraceReader(pool).read_run("run-1", ANKOR_ID)  # type: ignore[arg-type]

    assert check_walk(events).missing == (NodeType.TOOL_CALL,)


async def test_db_hai_run_xen_ke_khong_lan_nhau(admin_pool: object, pool: object) -> None:
    """Cách ly theo `run_id`: đọc run A không được dính event của run B."""
    del admin_pool
    a = _event(NodeType.KB_RETRIEVE, "2026-07-24T09:00:00+00:00", event_id="ev-a", run_id="run-A")
    b = _event(NodeType.LLM_STEP, "2026-07-24T09:00:00.5+00:00", event_id="ev-b", run_id="run-B")
    await _write(pool, [a, b])

    events = await PgTraceReader(pool).read_run("run-A", ANKOR_ID)  # type: ignore[arg-type]

    assert [e.event_id for e in events] == ["ev-a"]


async def test_db_khong_doc_cheo_tenant(admin_pool: object, pool: object) -> None:
    """`obs.trace_events` nay có RLS thật (GAP-1) cộng mệnh đề `tenant_id` trong câu SQL — 2 lớp độc
    lập. Cùng `run_id`, khác tenant, phải không thấy gì."""
    del admin_pool
    await _write(pool, [_event(NodeType.KB_RETRIEVE, "2026-07-24T09:00:00+00:00", tenant_id=ANKOR_ID)])

    events = await PgTraceReader(pool).read_run("run-1", BOREA_ID)  # type: ignore[arg-type]

    assert events == []


async def test_db_run_khong_ton_tai_tra_rong_khong_raise(admin_pool: object, pool: object) -> None:
    """Rỗng là hợp lệ, không phải lỗi."""
    del admin_pool

    events = await PgTraceReader(pool).read_run("run-khong-co-that", ANKOR_ID)  # type: ignore[arg-type]

    assert events == []


async def test_db_truyen_slug_thay_uuid_thi_vo_to_tieng(admin_pool: object, pool: object) -> None:
    """D-13: `tenant_id` là UUID strict. Truyền slug `"ankor"` phải **vỡ**, tuyệt đối không được
    lặng lẽ trả `[]` — một hàng rào nhận nhầm kiểu mà vẫn chạy tiếp là hàng rào đã hỏng.

    Bắt đúng `InvalidTextRepresentation` chứ không phải `Exception` trần: một bài
    `pytest.raises(Exception)` sẽ xanh cả khi hàm vỡ vì mất kết nối, sai tên bảng, hay bất cứ lý do
    nào khác — tức là xanh mà không chứng minh được điều đang muốn chứng minh.
    """
    del admin_pool

    with pytest.raises(InvalidTextRepresentation, match='invalid input syntax for type uuid: "ankor"'):
        await PgTraceReader(pool).read_run("run-1", "ankor")  # type: ignore[arg-type]
