"""Spine 3 node chạy THẬT — emit (engine) → sink (`obs.trace_events`) → reader (kb).

(Trước workbench#31, 2026-08-24: 4 node — `create_recipe_d4`/`d6` khi đó còn sinh thêm 1 node
`tool-call{kb_search}` chết, đã bị xoá; DAG thật hôm nay chỉ còn `kb-retrieve → llm-step → end`.)

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
from studio_contracts.kb import KbSearch, KbSearchResultItem
from studio_contracts.nodes import NodeType
from studio_contracts.recipe import Recipe
from studio_contracts.trace import TraceEvent
from studio_engine import RunResult, run
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

# Câu hỏi + chunk cho bài T6 (`test_t6_recipe_khai_section_roles_rong_hon_thi_phien_thang`).
# Chọn bằng ĐO, không bằng cảm giác: trên kho Callisto hiện tại, câu này với `section_roles=
# ["finance"]` cho `ankor-budget-001#c2` hạng nhất (score 0.875), còn với `["public"]` **không ra
# một chunk finance nào**. Cặp tương phản đó chính là thứ làm phép loại trừ của bài T6 có nghĩa —
# nếu câu hỏi không với tới được kho finance thì "không thấy finance" đúng cả khi hàng rào đã hỏng.
_FINANCE_QUERY = "Bộ phận điều chỉnh ngân sách nội bộ giữa các hạng mục trong phạm vi bao nhiêu?"
_FINANCE_CHUNK = "ankor-budget-001#c2"


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


class _RolesCapturingKbSearch:
    """Ghi lại `section_roles` mà `kb.search` **thật sự nhận**, rồi uỷ quyền nguyên vẹn cho
    `StaticKbSearch`. Dùng cho bài T6 (`test_t6_recipe_khai_section_roles_rong_hon_thi_phien_thang`).

    **Không phải "quadrant mock quadrant"** (luật `day-06.md:46`): đây không dựng giả quadrant khác
    — nó bọc chính `StaticKbSearch` của DE, ghi một biến rồi gọi thẳng bản thật, nên hành vi lọc
    đem ra assert vẫn là hành vi thật của kb, không phải hành vi bịa trong test.

    **Vì sao cần ghi lại input chứ không chỉ nhìn output.** Output (`chunks` trong trace) chứng minh
    *hệ quả* — không có chunk finance nào lọt. Input chứng minh *cơ chế* — kb.search nhận đúng
    `["public"]` của phiên chứ không phải `["finance"]` recipe khai. Hai vế hỏng độc lập nhau: một
    ngày `StaticKbSearch` lọc sai mà interpreter vẫn đè đúng thì vế output đỏ còn vế input xanh, và
    người đọc cần phân biệt được "hàng rào nào vừa gãy". Plan D20 §③ đòi đúng vế input:
    *"assert tại giá trị `section_roles` thực vào `kb.search`"*.
    """

    def __init__(self) -> None:
        self._inner = StaticKbSearch()
        self.seen_section_roles: list[str] | None = None
        """`None` = `kb.search` **chưa từng được gọi**, khác hẳn `[]` = *được gọi với danh sách rỗng*.
        Phân biệt hai ca này là cần: một run không bao giờ tới `kb-retrieve` cũng cho 0 chunk
        finance, tức xanh vì lý do sai."""

    async def search(
        self,
        query: str,
        tenant_id: UUID,
        section_roles: list[str],
        top_k: int,
    ) -> list[KbSearchResultItem]:
        # Chép ra `list(...)` chứ không giữ tham chiếu: interpreter dựng danh sách này rồi tiêm vào
        # `node.params`, và một bản ghi bị sửa sau khi ghi thì không còn là bằng chứng.
        self.seen_section_roles = list(section_roles)
        return await self._inner.search(query, tenant_id, section_roles, top_k)


def _voi_recipe_tu_che_khai_section_roles(recipe: Recipe, section_roles: list[str]) -> Recipe:
    """Trả bản sao của `recipe` với node `kb-retrieve` **tự khai** `section_roles` trong `node.params`.

    **Vì sao phải tự chế thay vì nhờ `create_recipe_d4(scope=...)` khai hộ.** Bản đầu của bài T6 lấy
    giá trị client-khai từ builder workbench — và ngày **13/08** SWE dọn `builder.py`
    (`workbench 47db2f9`, kit#122): `create_recipe_d4/d6` **thôi ghi** `tenant_id`/`section_roles` vào
    `node.params`, lý do *"interpreter luôn đè nên khai ở đây chỉ tạo ảo giác client kiểm soát được"*.
    Lý do đó **đúng cho builder**, nhưng nó xoá mất **vector tấn công** khỏi bài test: không còn giá
    trị client-khai nào thì phép "đè" không có gì để đè, và bài test **xanh mà chứng minh số 0** (đo
    được: bỏ cầu chì 2 ra thì bài vẫn PASS trên workbench mới).

    Mối đe doạ **không** biến mất cùng builder: `Node.params` là `dict[str, object]` tự do, nên một
    recipe **viết tay / do client POST lên** vẫn đặt `section_roles` vào đó được — đúng thứ
    `interpreter.py` phải vô hiệu hoá. Dựng thẳng ở đây làm bài test độc lập khỏi việc builder có
    tình cờ khai hộ hay không: từ nay workbench đổi cách gì cũng không làm bài này xanh-giả.
    """
    nodes = [
        node.model_copy(update={"params": {**node.params, "section_roles": section_roles}})
        if node.type is NodeType.KB_RETRIEVE
        else node
        for node in recipe.dag.nodes
    ]
    return recipe.model_copy(update={"dag": recipe.dag.model_copy(update={"nodes": nodes})})


async def _run_spine(
    pool: Pool,
    *,
    answer: str,
    tenant_id: UUID = ANKOR_ID,
    recipe_tenant_id: UUID | None = None,
    scope: str = "ankor/public",
    session_roles: list[str] | None = None,
    spoofed_section_roles: list[str] | None = None,
    query: str | None = None,
    kb_search: KbSearch | None = None,
) -> tuple[Recipe, RunResult]:
    """Chạy trọn một run với sink thật, trả `(recipe, RunResult)`.

    `trace_writer=PgTraceWriter(pool)` là mấu chốt của cả file: đây là chỗ event rời khỏi bộ nhớ
    tiến trình và xuống Postgres thật. Trả kèm `recipe` vì từ D6 chuỗi node kỳ vọng suy từ
    `recipe.dag`, không từ một hằng số.

    **Hai cặp (recipe tự khai / phiên server-resolve) tách rời được, vì cùng một lý do.** Hai nguồn
    khai cùng một giá trị thì không bài test nào phân biệt nổi hệ thống đang đọc nguồn nào — mặc
    định của cả hai cặp là *trùng nhau*, và chỉ bài kiểm hàng rào mới tách chúng ra:

    - `tenant_id` (phiên) vs `recipe_tenant_id` (recipe khai) — trục INV-1, xem
      `test_inv1_recipe_tu_khai_tenant_khac_thi_phien_thang`;
    - `session_roles` (phiên) vs `spoofed_section_roles` (recipe **tự chế** khai thẳng vào
      `node.params`) — trục T6, xem `test_t6_recipe_khai_section_roles_rong_hon_thi_phien_thang`.

    `kb_search` tiêm được để bài T6 quan sát **giá trị thực** đi vào `kb.search`; mặc định vẫn là
    `StaticKbSearch()` thật như trước.
    """
    # Hai nhánh gọi tường minh thay vì `**{...}` có điều kiện: `query=None` KHÔNG truyền được (nó là
    # `str` ở `create_recipe_d4`), mà chép lại giá trị mặc định của workbench vào đây thì tạo nguồn
    # sự thật thứ hai — ngày workbench đổi câu mặc định, bản chép ở test âm thầm lệch.
    recipe_tenant = tenant_id if recipe_tenant_id is None else recipe_tenant_id
    recipe = (
        create_recipe_d4(tenant_id=recipe_tenant, scope=scope)
        if query is None
        else create_recipe_d4(tenant_id=recipe_tenant, scope=scope, query=query)
    )
    if spoofed_section_roles is not None:
        recipe = _voi_recipe_tu_che_khai_section_roles(recipe, spoofed_section_roles)
    result = await run(
        recipe,
        # D8/INV-1: `run()` đòi `session_context` BẮT BUỘC (engine `a6967a2`, PR #12) — tenant đi qua
        # identity server-resolve, không lấy từ `recipe.tenant_id` nữa. Dùng thẳng `resolve_session`
        # của SWE thay vì tự dựng double: nhờ vậy file này thành chỗ DUY NHẤT trong kit chạy trọn
        # chuỗi thật resolver(SWE) → interpreter(AIE-1) → fence(DE) → Postgres → đọc lại, tức bằng
        # chứng chạy được cho DoD D8. Xem `docs/inv1_tenant_wall.md` §5.1.
        # (`ResolvedContext` là `@dataclass(frozen=True, slots=True)` đúng 3 field nên thoả
        # `SessionContext` Protocol về cấu trúc — `studio_engine/session.py:49-63`.)
        # `roles=["public"]` server-khai: chunk trích dẫn `ankor-leave-001#c1` là `section: public`.
        # Vắng `roles` → `resolve_session` mặc định `[]` (least-privilege) → sau khi interpreter
        # server-resolve `section_roles` từ `session.roles` (engine kit#111/PR21), `[]` = deny-all →
        # fence lọc hết chunk → mất trích dẫn. Khai đúng role tối thiểu để chuỗi thật vẫn truy được.
        session_context=resolve_session(
            {
                "tenant_id": tenant_id,
                "user": "spine-test",
                "roles": ["public"] if session_roles is None else session_roles,
            }
        ),
        kb_search=StaticKbSearch() if kb_search is None else kb_search,
        llm=_CitingLLM(answer),
        embedding=_UnusedEmbedding(),
        trace_writer=PgTraceWriter(pool),
    )
    return recipe, result


@pytest_asyncio.fixture
async def spine(pool: Pool) -> tuple[Recipe, RunResult, list[TraceEvent]]:
    """Chạy spine MỘT lần, dùng lại cho nhiều assert — mỗi lần chạy là một round-trip DB thật.

    Trả `(recipe, result, events_đọc_từ_DB)`. Cố ý **không** chỉ trả `result.events`: xem
    `test_events_come_from_db_not_memory`.
    """
    recipe, result = await _run_spine(pool, answer=f"Nhân viên cần báo trước 3 ngày làm việc. [{_CITED_CHUNK}]")
    events = await PgTraceReader(pool).read_run(result.run_id, ANKOR_ID)
    return recipe, result, events


def _chunks(e: TraceEvent) -> list[dict[str, str]]:
    """Lấy `outputs["chunks"]` với hàng rào runtime — `cast` chỉ là lời khai lúc biên dịch.

    Ba chỗ trong file cùng truy xuất `e.outputs["chunks"]` rồi duyệt dict bên trong.
    Dùng `cast(list[dict[str, object]], ...)` thì `{c["chunk_id"] for c in ...}` ra
    `set[object]`, nên `set(cited) <= retrieved_ids` vẫn type-check kể cả khi `cited`
    thôi không còn là `str` — annotation ghi ít hơn điều test đang assert.

    `assert isinstance` là hàng rào lúc chạy (cùng lập luận workbench#9).
    """
    chunks = e.outputs["chunks"]
    assert isinstance(chunks, list), f"outputs['chunks'] không phải list: {type(chunks)}"
    return chunks


async def test_walk_matches_the_recipe_dag(spine: tuple[Recipe, RunResult, list[TraceEvent]]) -> None:
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


async def test_events_come_from_db_not_memory(pool: Pool, spine: tuple[Recipe, RunResult, list[TraceEvent]]) -> None:
    """KHÓA: bản trong DB và bản trong RAM khớp nhau — sink thật sự đã ghi.

    Đây là bài chống lại cách viết test dễ sai nhất ở đây: assert vào `result.events` (bản sao
    trong bộ nhớ) chứng minh **số không** về chuyện `PgTraceWriter.write()` có chạy hay không.
    Nếu sink im lặng nuốt event, `result.events` vẫn đủ 4 còn bảng thì rỗng.
    """
    recipe, result, events = spine

    assert [e.event_id for e in events] == [e.event_id for e in result.events]
    assert len(events) == len(walk_from_dag(recipe.dag))


async def test_tenant_fence_on_read(pool: Pool, spine: tuple[Recipe, RunResult, list[TraceEvent]]) -> None:
    """KHÓA: đọc bằng tenant khác trả rỗng.

    `obs.trace_events` nay có RLS thật (GAP-1) CỘNG mệnh đề `WHERE ... AND tenant_id` trong
    `_READ_RUN` — 2 lớp độc lập, không lớp nào thay được lớp kia. Không có bài này thì ai đó xoá
    mệnh đề WHERE đi (RLS vẫn đứng) hoặc `SET LOCAL` (WHERE vẫn đứng) đều có thể vẫn xanh cả suite
    nhờ lớp còn lại — nhưng mất 1 trong 2 lớp là giảm-cấp-âm-thầm, và bài này là bài duy nhất khoá
    cả hai còn sống cùng lúc.
    """
    _recipe, result, _events = spine

    assert await PgTraceReader(pool).read_run(result.run_id, BOREA_ID) == []


async def test_reader_reports_missing_node(spine: tuple[Recipe, RunResult, list[TraceEvent]]) -> None:
    """KHÓA: reader có răng — bỏ node cuối thì phải kêu.

    Một reader chỉ biết in ra thì lúc nào cũng trông như thành công. Bài này chứng minh nhánh báo
    lỗi thật sự chạy được, chứ không phải chưa bao giờ được gọi tới.
    """
    _recipe, _result, events = spine

    check = check_walk(events[:-1])
    assert not check.ok
    assert NodeType.END in check.missing


async def test_inputs_hash_differs_per_node(spine: tuple[Recipe, RunResult, list[TraceEvent]]) -> None:
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


async def test_kb_retrieve_got_a_real_uuid_scoped_call(spine: tuple[Recipe, RunResult, list[TraceEvent]]) -> None:
    """KHÓA: `kb-retrieve` gọi được `kb.search` và lấy về chunk thật.

    Đây là vế `kb.search nhận call thật` của DoD. Rỗng ở đây nghĩa là đường slug→UUID lại tắc:
    executor phải nhận `tenant_id` kiểu `UUID` (do `run()` tiêm từ `recipe.tenant_id`), nếu rơi về
    sentinel nil-UUID thì lọc ra 0 chunk và `chunks` rỗng — hồi quy im lặng, không có exception nào.
    """
    _recipe, _result, events = spine
    retrieve = next(e for e in events if e.node_type is NodeType.KB_RETRIEVE)

    chunks = _chunks(retrieve)
    assert chunks, "kb-retrieve trả 0 chunk — nhiều khả năng tenant_id không tới được dạng UUID"
    assert all(c["tenant_id"] == str(ANKOR_ID) for c in chunks)


async def test_citations_are_grounded(spine: tuple[Recipe, RunResult, list[TraceEvent]]) -> None:
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

    retrieved_ids = {c["chunk_id"] for c in _chunks(retrieve)}
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
    chunks = _chunks(retrieve)

    # Cầu chì: rỗng thì hai assert dưới pass rỗng nghĩa, mà "không truy xuất được gì" cũng là cách
    # một fence hỏng có thể trông như đang chặn.
    assert chunks, "phải truy xuất được chunk ankor — rỗng thì phép loại trừ dưới vô nghĩa"
    assert all(c["tenant_id"] == str(ANKOR_ID) for c in chunks)
    assert not any(str(c["chunk_id"]).startswith("borea-") for c in chunks)

    assert all(e.tenant_id == ANKOR_ID for e in events), "trace phải mang tenant của phiên, không của recipe"

    assert await PgTraceReader(pool).read_run(result.run_id, BOREA_ID) == []


async def test_t6_recipe_khai_section_roles_rong_hon_thi_phien_thang(pool: Pool) -> None:
    """KHÓA T6 label-spoof (`kit#111`, `kb-search.v0.md` §3.3) — *"client tự khai VAI bị bỏ qua"*.

    **Bài anh em của `test_inv1_recipe_tu_khai_tenant_khac_thi_phien_thang`, trục thứ hai.** Bài kia
    tách `tenant_id` (bạn là ai); bài này tách `section_roles` (bạn được đọc mục nào). Cùng một
    tenant hợp lệ, cùng một phiên thật — kẻ tấn công không giả danh tenant khác mà **tự nới quyền
    trong tenant của chính mình**: recipe khai `kb_binding.scope="ankor/finance"`, phiên chỉ được
    server-resolve ra `roles=["public"]`.

    **Vì sao kb phải có bài này dù engine đã có bài của riêng nó.** `packages/engine/tests/
    test_section_roles_server_resolve.py` chứng minh override tại biên executor, bằng double của
    AIE-1 — đó là bằng chứng của lane engine. Bài này chứng minh cùng bất biến **trong kho kb**,
    trên chuỗi thật `resolve_session`(SWE) → `interpreter`(AIE-1) → `kb.search`(DE) → Postgres →
    đọc lại, với **kho tài liệu Callisto thật** của DE. Không có nó, evidence-pack của kb phải đi
    mượn bằng chứng ở repo khác cho một dòng DoD của chính mình (`#125` *"T6 label-spoof xanh"*), và
    người chấm chỉ đọc kb không kiểm lại được — đúng thứ chuẩn *"đủ để chấm không cần hỏi"* cấm.

    **Ba cầu chì trước hai vế khẳng định.** Ba thứ dưới đây đều có thể làm bài này xanh vì lý do
    sai, nên mỗi thứ bị chốt lại trước:

    1. *Đòn tấn công không ăn được ngay từ đầu.* Nếu câu hỏi không với tới kho `finance` thì "không
       thấy chunk finance" đúng cả khi hàng rào đã gãy. Chốt bằng phép đo ngược: đưa thẳng
       `["finance"]` cho `StaticKbSearch` phải **ra** chunk finance.
    2. *Recipe không thật sự khai `finance`.* **Cầu chì này đã cứu bài test một lần rồi** (13/08):
       SWE dọn `builder.py` (`workbench 47db2f9`) cho `create_recipe_d4` thôi ghi `section_roles` vào
       `node.params` — bản đầu của bài lấy giá trị client-khai từ đó, nên **mất sạch vector tấn
       công**, và nếu không có assert này thì bài **vẫn PASS** (đo được) trong khi không đè cái gì cả.
       Nay giá trị client-khai **tự chế tại chỗ** (`_voi_recipe_tu_che_khai_section_roles`), độc lập
       hoàn toàn khỏi builder — nhưng cầu chì vẫn giữ, vì nó canh cả ca "helper tự chế hỏng".
    3. *`kb.search` chưa từng được gọi.* Một run gãy trước `kb-retrieve` cũng cho 0 chunk finance.
       Chốt bằng `seen_section_roles is not None`.

    Rồi mới tới hai vế, cố ý phủ **cơ chế** và **hệ quả** — hỏng độc lập nhau:
      1. cơ chế — giá trị THỰC vào `kb.search` là `["public"]` của phiên, không phải `["finance"]`
         recipe khai (plan D20 §③: *"assert tại giá trị `section_roles` thực vào `kb.search`"*);
      2. hệ quả — đọc lại từ Postgres, không một chunk `finance` nào có mặt trong trace.
    """
    spy = _RolesCapturingKbSearch()

    # Cầu chì 1 — đòn tấn công phải THẬT SỰ ăn được nếu không ai chặn.
    neu_khong_chan = await StaticKbSearch().search(_FINANCE_QUERY, ANKOR_ID, ["finance"], 5)
    assert any(h.chunk_id == _FINANCE_CHUNK for h in neu_khong_chan), (
        f"tiền đề của bài: {_FINANCE_QUERY!r} phải với tới được {_FINANCE_CHUNK} khi vai finance "
        "được chấp nhận — nếu không, phép loại trừ bên dưới xanh mà không chứng minh gì"
    )

    recipe, result = await _run_spine(
        pool,
        answer="Ngân sách nội bộ điều chỉnh theo quy định của bộ phận tài chính.",
        scope="ankor/finance",  # scope recipe khai (workbench vẫn validate cấu trúc chuỗi này)
        spoofed_section_roles=["finance"],  # recipe TỰ CHẾ nhét thẳng vào params — vai kẻ tấn công
        session_roles=["public"],  # phiên: server-resolve, hẹp hơn hẳn
        query=_FINANCE_QUERY,
        kb_search=spy,
    )

    # Cầu chì 2 — recipe phải thật sự khai `finance` sau khi workbench parse `scope`.
    retrieve_node = next(n for n in recipe.dag.nodes if n.type is NodeType.KB_RETRIEVE)
    assert retrieve_node.params["section_roles"] == ["finance"], (
        "tiền đề của bài: node kb-retrieve phải mang vai recipe tự khai, nếu không thì không có "
        f"gì để đè — đang là {retrieve_node.params['section_roles']!r}"
    )

    # Cầu chì 3 + Vế 1 (cơ chế): `kb.search` được gọi, và nhận đúng vai của PHIÊN.
    assert spy.seen_section_roles is not None, "kb.search chưa từng được gọi — run gãy trước kb-retrieve?"
    assert spy.seen_section_roles == ["public"], (
        "interpreter phải ĐÈ vai recipe khai bằng vai phiên trước khi gọi kb.search — "
        f"kb.search nhận {spy.seen_section_roles!r}"
    )

    # Vế 2 (hệ quả): đọc lại từ Postgres — không chunk finance nào lọt vào trace.
    events = await PgTraceReader(pool).read_run(result.run_id, ANKOR_ID)
    retrieve = next(e for e in events if e.node_type is NodeType.KB_RETRIEVE)
    chunks = _chunks(retrieve)

    assert chunks, "phải truy xuất được chunk public — rỗng thì phép loại trừ dưới vô nghĩa"
    assert all(c["section_role"] == "public" for c in chunks)
    assert not any(c["chunk_id"] == _FINANCE_CHUNK for c in chunks)


async def test_trace_la_nguon_citation_dung_duoc_cho_bo_cham(spine: tuple[Recipe, RunResult, list[TraceEvent]]) -> None:
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
    """KHÓA: câu trả lời không trích được gì ⇒ `refused=True`, và spine vẫn đủ 3 node.

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
