"""Spine 4 node chạy THẬT — emit (engine) → sink (`obs.trace_events`) → reader (kb).

Đây là bằng chứng cho DoD D6 *"trace sink nhận call thật từ interpreter (không stub rỗng)"*: chạy
`studio_engine.run()` thật trên recipe thật của SWE, với `StaticKbSearch` thật của DE và
`PgTraceWriter` thật của mentor, rồi **đọc lại từ Postgres** bằng reader của DE.

**Khác `test_trace_reader.py` ở một điểm quyết định.** Bài đó tự tay dựng `TraceEvent` rồi ghi —
nó kiểm reader, không kiểm interpreter. Bài này không dựng event nào: mọi event trong bảng đều do
`interpreter.run()` đẻ ra. Nếu emit-hook biến mất (vd con trỏ submodule `packages/engine` lùi về
bản còn `del trace_writer`, `events=[]`) thì bảng rỗng và bài này **đỏ ngay dòng assert đầu** —
đúng ý muốn, vì "không có event nào" là một hồi quy, không phải một trạng thái hợp lệ.

⚠️ Import `studio_app` / `studio_engine` / `studio_workbench` chỉ xuất hiện **trong test**, không
bao giờ trong `src/`. `.importlinter` ràng buộc namespace `studio_kb` (tức `src/`), không quét thư
mục test — cùng đường mà `test_trace_reader.py` và `test_leak.py` đã dùng.

**`_CitingLLM` không phải "quadrant mock quadrant".** Luật `day-06.md:46` cấm một quadrant dựng giả
quadrant khác để né tích hợp. `LLM` là seam nhà cung cấp bên ngoài, không phải một trong 4 quadrant;
cả `studio_engine.demo_stubs.FixtureLLM` lẫn `studio_app.providers.fakes.FakeLLM` đều là double
theo đúng thiết kế. Dùng double cục bộ ở đây thay `FixtureLLM` vì cần điều khiển **nội dung trích
dẫn** để kiểm luật grounding (xem `test_citations_are_grounded`) — fixture `smoke-01.json` trích
`[chunk-001]`, một id không tồn tại trong kho Callisto, nên không kiểm được gì.

Cần Postgres: `docker compose -f docker-compose.test.yml up -d` + hai biến DSN. Thiếu thì fixture
`pool` ở `conftest.py` gốc **skip**, không fail.
"""

from __future__ import annotations

from uuid import UUID

import pytest_asyncio
from studio_app.core._db import Pool
from studio_app.obs.trace_writer import PgTraceWriter
from studio_contracts.nodes import NodeType
from studio_engine import run
from studio_kb.doc_factory import TENANT_IDS
from studio_kb.static_search import StaticKbSearch
from studio_kb.trace_reader import PgTraceReader, check_walk, walk_from_dag
from studio_workbench import create_recipe_d4

ANKOR_ID = TENANT_IDS["ankor"]
BOREA_ID = TENANT_IDS["borea"]

# Chunk có thật trong kho Callisto (`docs/callisto/ankor-leave-001.md`), là `expected_citation` của
# SC-01 trong `golden/smoke-5.yaml`. Dùng đúng id thật, không bịa: một id bịa sẽ bị luật grounding
# loại và mọi assert về citation thành rỗng — xanh mà không chứng minh gì.
_CITED_CHUNK = "ankor-leave-001#c1"


class _CitingLLM:
    """`LLM` double: trả một câu có trích dẫn `[chunk_id]` theo đúng cú pháp engine parse.

    Không đọc `prompt`: node `llm-step` của `create_recipe_d4` có `params={"temperature": 0.0}`,
    không có khoá `"prompt"`, nên executor truyền chuỗi rỗng xuống. Câu trả lời vì thế phải cố
    định — và đó cũng là điều kiện để bài test tất định.
    """

    def __init__(self, answer: str) -> None:
        self._answer = answer

    async def complete(self, prompt: str, **kwargs: object) -> str:
        del prompt, kwargs
        return self._answer


class _UnusedEmbedding:
    """`EmbeddingService` double. `LlmStepExecutor` nhận `embedding` qua constructor nhưng **không
    dùng** ở phase này (docstring của nó ghi rõ: recipe D3–D6 không có bước embed). Trả `[]` cho
    đúng chữ ký; nếu ngày nào đó executor bắt đầu dùng thật thì chỗ này phải đổi — và bài test sẽ
    là nơi phát hiện ra."""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        del texts
        return []


async def _run_spine(pool: Pool, *, answer: str, tenant_id: UUID = ANKOR_ID):
    """Chạy trọn một run với sink thật, trả `(recipe, RunResult)`.

    `trace_writer=PgTraceWriter(pool)` là mấu chốt của cả file: đây là chỗ event rời khỏi bộ nhớ
    tiến trình và xuống Postgres thật. Trả kèm `recipe` vì từ D6 chuỗi node kỳ vọng suy từ
    `recipe.dag`, không từ một hằng số.
    """
    recipe = create_recipe_d4(tenant_id=tenant_id)
    result = await run(
        recipe,
        kb_search=StaticKbSearch(),
        llm=_CitingLLM(answer),
        embedding=_UnusedEmbedding(),
        trace_writer=PgTraceWriter(pool),
    )
    return recipe, result


@pytest_asyncio.fixture
async def spine(pool: Pool):
    """Chạy spine MỘT lần, dùng lại cho nhiều assert — mỗi lần chạy là một round-trip DB thật.

    Trả `(recipe, result, events_đọc_từ_DB)`. Cố ý **không** chỉ trả `result.events`: xem
    `test_events_come_from_db_not_memory`.
    """
    recipe, result = await _run_spine(pool, answer=f"Nhân viên cần báo trước 3 ngày làm việc. [{_CITED_CHUNK}]")
    events = await PgTraceReader(pool).read_run(result.run_id, ANKOR_ID)
    return recipe, result, events


async def test_walk_matches_the_recipe_dag(spine) -> None:
    """KHÓA: chuỗi node đã emit khớp chuỗi mà **recipe** khai, ĐÚNG thứ tự.

    Đối chiếu với `walk_from_dag(recipe.dag)` chứ không với hằng số `EXPECTED_WALK`: từ D6 (#27)
    interpreter đi theo `recipe.dag.edges`, nên chuỗi kỳ vọng thuộc về recipe. Neo vào hằng số sẽ
    vẫn xanh khi ai đó đổi DAG của recipe — tức bài test ngừng kiểm đúng thứ nó phải kiểm.

    Assert cả thứ tự chứ không chỉ `check_walk().ok`: `WalkCheck` chỉ kiểm *thiếu* và *trùng*, nó
    **không** kiểm thứ tự — bốn event đúng loại nhưng đảo lộn vẫn cho `ok is True`.
    """
    recipe, _result, events = spine
    expected = walk_from_dag(recipe.dag)

    assert [e.node_type for e in events] == list(expected)
    assert check_walk(events, expected).ok


async def test_events_come_from_db_not_memory(pool: Pool, spine) -> None:
    """KHÓA: bản trong DB và bản trong RAM khớp nhau — sink thật sự đã ghi.

    Đây là bài chống lại cách viết test dễ sai nhất ở đây: assert vào `result.events` (bản sao
    trong bộ nhớ) chứng minh **số không** về chuyện `PgTraceWriter.write()` có chạy hay không.
    Nếu sink im lặng nuốt event, `result.events` vẫn đủ 4 còn bảng thì rỗng.
    """
    recipe, result, events = spine

    assert [e.event_id for e in events] == [e.event_id for e in result.events]
    assert len(events) == len(walk_from_dag(recipe.dag))


async def test_tenant_fence_on_read(pool: Pool, spine) -> None:
    """KHÓA: đọc bằng tenant khác trả rỗng.

    `obs.trace_events` **không có RLS** (khác `kb.chunks`), nên mệnh đề `WHERE ... AND tenant_id`
    trong `_READ_RUN` là hàng rào **duy nhất**. Không có bài này thì ai đó xoá mệnh đề đó đi vẫn
    xanh cả suite, và lỗ hổng là đọc chéo tenant.
    """
    _recipe, result, _events = spine

    assert await PgTraceReader(pool).read_run(result.run_id, BOREA_ID) == []


async def test_reader_reports_missing_node(spine) -> None:
    """KHÓA: reader có răng — bỏ node cuối thì phải kêu.

    Một reader chỉ biết in ra thì lúc nào cũng trông như thành công. Bài này chứng minh nhánh báo
    lỗi thật sự chạy được, chứ không phải chưa bao giờ được gọi tới.
    """
    _recipe, _result, events = spine

    check = check_walk(events[:-1])
    assert not check.ok
    assert NodeType.END in check.missing


async def test_inputs_hash_differs_per_node(spine) -> None:
    """KHÓA: `inputs_hash` là hash thật của `node.params`, không phải hằng số.

    Bốn node có `params` khác nhau ⇒ bốn hash khác nhau. Không có assert này thì một hiện thực trả
    chuỗi rỗng (hoặc hash trước khi tiêm `tenant_id`/`retrieved_chunks`) vẫn xanh — mà lúc đó
    `inputs_hash` mất hoàn toàn giá trị định danh input.
    """
    _recipe, _result, events = spine

    assert len({e.inputs_hash for e in events}) == len(events)
    assert all(e.inputs_hash for e in events)


async def test_kb_retrieve_got_a_real_uuid_scoped_call(spine) -> None:
    """KHÓA: `kb-retrieve` gọi được `kb.search` và lấy về chunk thật.

    Đây là vế `kb.search nhận call thật` của DoD. Rỗng ở đây nghĩa là đường slug→UUID lại tắc:
    executor phải nhận `tenant_id` kiểu `UUID` (do `run()` tiêm từ `recipe.tenant_id`), nếu rơi về
    sentinel nil-UUID thì lọc ra 0 chunk và `chunks` rỗng — hồi quy im lặng, không có exception nào.
    """
    _recipe, _result, events = spine
    retrieve = next(e for e in events if e.node_type is NodeType.KB_RETRIEVE)

    chunks = retrieve.outputs["chunks"]
    assert isinstance(chunks, list)
    assert chunks, "kb-retrieve trả 0 chunk — nhiều khả năng tenant_id không tới được dạng UUID"
    assert all(c["tenant_id"] == str(ANKOR_ID) for c in chunks)


async def test_citations_are_grounded(spine) -> None:
    """KHÓA: chỉ chunk ĐÃ truy xuất mới được trích.

    Luật grounding (engine `1e25a3a`): citation phải vừa được `kb-retrieve` trả về, vừa được nhắc
    trong ngoặc vuông ở câu trả lời. Trích "mọi thứ đã truy xuất" hoặc trích một id model tự bịa
    đều là lỗi thật — cái sau từng làm citation-accuracy của smoke-eval dương tính giả.

    Viết dưới dạng tập con thay vì so bằng một danh sách cứng: thứ hạng của `StaticKbSearch` có thể
    đổi khi kho tài liệu đổi, nhưng luật *"không trích thứ chưa truy xuất"* thì không được phép đổi.
    """
    _recipe, _result, events = spine
    retrieve = next(e for e in events if e.node_type is NodeType.KB_RETRIEVE)
    llm = next(e for e in events if e.node_type is NodeType.LLM_STEP)

    retrieved_ids = {c["chunk_id"] for c in retrieve.outputs["chunks"]}
    cited = llm.citations or []

    assert set(cited) <= retrieved_ids
    # `_CITED_CHUNK` là id có thật; nó được trích khi và chỉ khi nó nằm trong tập truy xuất.
    assert cited == [c for c in [_CITED_CHUNK] if c in retrieved_ids]


async def test_refusal_is_derived_from_grounding(pool: Pool) -> None:
    """KHÓA: câu trả lời không trích được gì ⇒ `refused=True`, và spine vẫn đủ 4 node.

    Hợp đồng `refused` đã đổi **hai lần**, nên bài này neo bản hiện hành thay vì giả định:

    - `71caeb8` — `not retrieved_chunks`. Bỏ vì SC-04 truy xuất **không** rỗng: fence bỏ hết chunk
      Borea nhưng ranker vẫn trả 3 chunk ankor theo hư từ ⇒ `refused=False`, hỏng nhánh từ chối.
    - `1c88728` — `answer == "[[REFUSED]]"`. Bỏ vì không prompt nào trong workspace bảo model phát
      sentinel đó ⇒ `refused` luôn `False` trên mọi câu trả lời thật.
    - `22627e7` — **`not citations`**, bản hiện hành. Citation đã vừa grounded vừa được nhắc, nên
      "không grounded gì" được đọc là "không trả lời được từ thứ được đưa".

    ⚠️ **Giới hạn phải biết, và nó nguy hiểm một chiều.** `not citations` cho `refused=True` với
    một câu trả lời **bịa đặt trọn vẹn mà quên đóng ngoặc** — đo được: một câu bịa "Hạn mức chi của
    Borea là 500 triệu đồng" ở SC-04 vẫn ra `refused=True`, tức case leak-test **PASS dù agent đã
    bịa**. Đây đúng là dương-tính-giả mà `1c88728` từng ghi là lý do bỏ `not retrieved_chunks`.
    Với một bài kiểm hàng rào, xanh-giả nguy hiểm hơn đỏ-giả. Bài test này KHÔNG chứng minh nhánh
    từ chối đúng — nó chỉ chốt hành vi hiện hành để lần đổi sau không âm thầm.
    """
    _recipe, result = await _run_spine(pool, answer="Tôi không có thông tin về việc này.")
    events = await PgTraceReader(pool).read_run(result.run_id, ANKOR_ID)
    llm = next(e for e in events if e.node_type is NodeType.LLM_STEP)

    assert (llm.citations or []) == []
    assert llm.outputs["refused"] is True
    # Từ chối là một câu trả lời hợp lệ, không phải một run hỏng.
    assert check_walk(events).ok
