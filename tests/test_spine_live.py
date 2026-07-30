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
from studio_workbench.tenant_wall import resolve_session

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


async def _run_spine(pool: Pool, *, answer: str, tenant_id: UUID = ANKOR_ID, recipe_tenant_id: UUID | None = None):
    """Chạy trọn một run với sink thật, trả `(recipe, RunResult)`.

    `trace_writer=PgTraceWriter(pool)` là mấu chốt của cả file: đây là chỗ event rời khỏi bộ nhớ
    tiến trình và xuống Postgres thật. Trả kèm `recipe` vì từ D6 chuỗi node kỳ vọng suy từ
    `recipe.dag`, không từ một hằng số.

    `tenant_id` là tenant **của phiên** (server-resolve). `recipe_tenant_id` là tenant **recipe tự
    khai** — mặc định trùng phiên, và tách rời được là điều kiện để kiểm INV-1: hai nguồn khai cùng
    một giá trị thì không bài test nào phân biệt nổi hệ thống đang đọc nguồn nào.
    """
    recipe = create_recipe_d4(tenant_id=tenant_id if recipe_tenant_id is None else recipe_tenant_id)
    result = await run(
        recipe,
        # D8/INV-1: `run()` đòi `session_context` BẮT BUỘC (engine `a6967a2`, PR #12) — tenant đi qua
        # identity server-resolve, không lấy từ `recipe.tenant_id` nữa. Dùng thẳng `resolve_session`
        # của SWE thay vì tự dựng double: nhờ vậy file này thành chỗ DUY NHẤT trong kit chạy trọn
        # chuỗi thật resolver(SWE) → interpreter(AIE-1) → fence(DE) → Postgres → đọc lại, tức bằng
        # chứng chạy được cho DoD D8. Xem `docs/inv1_tenant_wall.md` §5.1.
        # (`ResolvedContext` là `@dataclass(frozen=True, slots=True)` đúng 3 field nên thoả
        # `SessionContext` Protocol về cấu trúc — `studio_engine/session.py:49-63`.)
        session_context=resolve_session({"tenant_id": tenant_id, "user": "spine-test"}),
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

    # Cầu chì chống rỗng-nghĩa: `events` rỗng làm CẢ HAI assert dưới xanh vô nghĩa —
    # `len(set()) == len([])` là `0 == 0`, và `all([])` là True.
    # Đo được: cho `PgTraceReader.read_run` trả `[]` (reader nuốt hết event) → 9 test khác đỏ, riêng
    # bài này VẪN XANH. Có dòng này thì nó đỏ theo.
    # Chỉ khẳng định không-rỗng, KHÔNG chốt `== 4`: chuỗi node thuộc về recipe kể từ D6 (#27) và
    # `test_walk_matches_the_recipe_dag` mới là chỗ sở hữu phép kiểm đó — chốt 4 ở đây là chụp ảnh
    # hình dạng recipe hôm nay vào một bài test không nói gì về hình dạng recipe.
    assert events, "spine phải emit event — rỗng thì hai assert dưới không khoá gì"
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


async def test_inv1_recipe_tu_khai_tenant_khac_thi_phien_thang(pool: Pool) -> None:
    """KHÓA INV-1 (`day-08.md`, issue #40) — *"client tự khai tenant bị bỏ qua"*.

    **Vì sao bài này phải tồn tại dù cả file đã truyền `session_context`.** Mọi bài khác trong file
    dựng recipe và phiên với CÙNG một `tenant_id`, nên hai nguồn không phân biệt được: hệ thống đọc
    nguồn nào cũng ra cùng kết quả. Đo được — đổi `interpreter.py` để lấy `recipe.tenant_id` thay vì
    `session_context.tenant_id` (đúng cái INV-1 cấm) thì **cả suite kb 66 test vẫn xanh**, kể cả bài
    `test_kb_retrieve_got_a_real_uuid_scoped_call` vốn trông như đang canh chỗ đó.

    Nói cách khác: trước bài này, "đã truyền `session_context`" mới là *chạy qua* được API mới, chưa
    phải *bằng chứng* cho DoD D8.

    Bài này tách hai nguồn ra: recipe tự khai **borea** (vai kẻ tấn công — client khai bừa để với
    sang kho tenant khác), phiên server-resolve ra **ankor**. Mọi thứ hạ nguồn phải đi theo PHIÊN.

    Ba vế, cố ý phủ ba tầng khác nhau chứ không phải lặp lại một ý:
      1. tầng dữ liệu — chunk truy xuất được thuộc ankor, không một chunk borea nào;
      2. tầng quan trắc — `TraceEvent.tenant_id` là ankor, vì trace sai tenant thì kiểm toán sau này
         quy trách nhiệm nhầm chỗ;
      3. tầng đọc lại — đọc bằng borea (tenant recipe khai) trả rỗng.
    """
    recipe, result = await _run_spine(
        pool,
        answer=f"Nhân viên cần báo trước 3 ngày làm việc. [{_CITED_CHUNK}]",
        tenant_id=ANKOR_ID,  # phiên: server-resolve
        recipe_tenant_id=BOREA_ID,  # recipe tự khai — phải bị bỏ qua
    )
    assert recipe.tenant_id == BOREA_ID, "tiền đề của bài: recipe phải thật sự khai tenant khác phiên"

    events = await PgTraceReader(pool).read_run(result.run_id, ANKOR_ID)
    retrieve = next(e for e in events if e.node_type is NodeType.KB_RETRIEVE)
    chunks = retrieve.outputs["chunks"]

    # Cầu chì: rỗng thì hai assert dưới pass rỗng nghĩa, mà "không truy xuất được gì" cũng là cách
    # một fence hỏng có thể trông như đang chặn.
    assert chunks, "phải truy xuất được chunk ankor — rỗng thì phép loại trừ dưới vô nghĩa"
    assert all(c["tenant_id"] == str(ANKOR_ID) for c in chunks)
    assert not any(str(c["chunk_id"]).startswith("borea-") for c in chunks)

    assert all(e.tenant_id == ANKOR_ID for e in events), "trace phải mang tenant của phiên, không của recipe"

    assert await PgTraceReader(pool).read_run(result.run_id, BOREA_ID) == []


async def test_trace_la_nguon_citation_dung_duoc_cho_bo_cham(spine) -> None:
    """KHÓA phần DE của DoD `day-09.md:53` — *"smoke-eval lấy citation TỪ TRACE (một nguồn số)"*.

    DE sở hữu **nguồn**: `obs.trace_events` → `PgTraceReader`. AIE-2 sở hữu **bộ chấm** (#44). Chỗ
    hai bên gặp nhau là kiểu của `TraceEvent.citations`, và đó là chỗ "một nguồn số" hỏng được mà
    không ai đỏ: reader đọc ra một dạng, bộ chấm mong một dạng khác, mỗi bên tự tính một con số.
    Bài này khoá đúng cái bắt tay đó bằng cách cho hàm THẬT của AIE-2 ăn event THẬT đọc từ Postgres.

    Hai điều được khẳng định, và chúng khác nhau:

    1. **Dùng được** — `citations_from_trace` trên event đọc-từ-DB phải ra đúng chunk mà LLM trích.
       Không có vế này thì "nối vào trace" chỉ là nói.
    2. **Không mất mát qua DB** — bản đọc-từ-DB và bản trong-RAM cho CÙNG kết quả.
       `test_events_come_from_db_not_memory` chỉ so `event_id`, nên một reader đánh rơi `citations`
       vẫn xanh ở đó; con số chấm điểm thì đã sai. Vế này là chỗ bắt điều đó.

    Không assert `isinstance(list[str])`: `TraceEvent` là pydantic `BaseModel` nên `citations=row[11]`
    đã bị validate ngay tại biên reader — JSONB sai kiểu là `ValidationError` lúc dựng event, không
    phải lúc chấm. Thêm một assert kiểu ở đây là kiểm lại việc pydantic đã làm.

    Import `studio_evalhub` trong test là cố ý và cùng đường đã dùng cho `studio_engine` /
    `studio_workbench` ở đầu file: `.importlinter` ràng namespace `studio_kb` (tức `src/`), không quét
    test. Gọi hàm thật của AIE-2 thay vì chép lại logic gom — chép lại thì khớp với bản chép, không
    khớp với bộ chấm.
    """
    from studio_evalhub.harness import citations_from_trace

    _recipe, result, events = spine

    tu_db = citations_from_trace(events)
    tu_ram = citations_from_trace(result.events)

    assert tu_db == [_CITED_CHUNK], "bộ chấm phải lấy được đúng chunk đã trích, từ trace đọc-từ-DB"
    assert tu_db == tu_ram, "đường xuống Postgres làm lệch citations — hai bên sẽ chấm ra hai số"


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
