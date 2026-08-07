<!--
detail_overview.md — bản KỸ THUẬT ĐẦY ĐỦ của overview.md. Đối tượng: người đọc có nền kỹ thuật.
Viết tự do, chi tiết nhất, dùng đúng tên file/class/hợp đồng thật. Cặp đôi với overview.md (bản non-tech).
Cập nhật MỖI NGÀY sau khi pull main mới nhất của kit (xem "Nhật ký cập nhật"). Người giữ: DE (DongAnh2704).
Lưu ý: đây là văn bản do DongAnh2704 tự thiết kế và không có trong yêu cầu của mentor nhằm giúp nắm rõ flow hiện tại của dự án được cập nhật hằng ngày, owner của submodule khác không cần chú ý đến đây.
-->

# AgentCore Studio — Bản kỹ thuật đầy đủ (detail_overview)

> Bản đầy đủ của `overview.md`. Không tối giản cho non-tech: dùng đúng tên module/class/contract, ghi
> rõ signature, cơ chế fence, và trạng thái code thật theo từng ngày. Đọc kèm `packages/kb/flow.md`
> (bản đồ runtime chi tiết của DE) và `docs/requirements/00-orientation/` (đề bài gốc + decisions-locked).

## 🗓️ Nhật ký cập nhật
- **2026-08-05 (D13):** tạo lần đầu — tổng hợp D1→D12 + trạng thái D13 (pg pipeline live).
- **2026-08-06 (D14):** +D14 — golden query grid (`grid_queries.py` + `emit_grid_queries.py` → `callisto-grid-queries-v0.yaml`, 20 case) cho AIE-1 đo chunking×embedding. PR kb#15 merged.
- **2026-08-07 (D15):** +D15 — trace viewer bổ `tokens` + `check_ts_monotonic` trong `render_timeline`; vá drift docstring `postgres.py` (PgKbSearch wired D13 vs seam `KbSearchService` để D17). PR kb#16 mở. **Không đổi cơ chế ghi trace** (sink D5 giữ nguyên).

---

## 1. Kiến trúc tổng thể

**Sản phẩm:** AgentCore Studio — nền tảng "Create→Test→Trust" cho phép đội sản phẩm tạo agent bằng
**recipe khai báo**, không chạm engine lõi. Ranh giới cứng **engine | recipe**: đổi hành vi = sửa
YAML recipe, không sửa code động cơ.

**Mono-repo (submodule):**

| Submodule | Quadrant / vai | Nội dung chính |
|---|---|---|
| `packages/contracts` | shared | `studio_contracts`: 4 hợp đồng + Protocol (KbSearch, EmbeddingService, LLM), NodeType, Recipe, TraceEvent, Tokens |
| `packages/kb` | **DE** | doc-factory, `kb.search` (Static + Pg), `kb.chunks` schema + RLS fence, embeddings fixture, trace_reader |
| `packages/engine` | **AIE-1** | interpreter (DAG walk), 6 node-type executor, demo_stubs (EmptyKbSearch/FixtureLLM) |
| `packages/workbench` | **SWE** | recipe builder, graph-lint, tenant_wall |
| `packages/evalhub` | **AIE-2** | eval harness, scorecard, citation-accuracy scorer |
| `apps/studio` | **mentor** | composition root: middleware (slug→tenant_id UUID), `ensure_all_schemas`, EngineAgentRunner adapter |
| `apps/web` | SWE | frontend standalone |
| `docs/requirements` | — | đề bài gốc (read-only) |
| `docs/reports` | — | daily-notes, gate reports, sprint reports |

**Nguyên tắc nền:**
- **fixtures-first (VCR-style, D-5):** CI chạy 100% trên response ghi sẵn; model/gateway thật chỉ bật
  qua flag lúc demo, và là **tùy chọn** (Phase-2/S3, cần ZTNA+credential+quota). Điểm chấm = pipeline/
  fence/trace, không phải IQ của LLM.
- **contract-freeze (D11):** 4 hợp đồng đóng băng; đổi phải mini-RFC + 4/4 chữ ký.
- **Python 3.14**, `uv` workspace, `.importlinter` layers-contract (quadrant package chỉ import
  `studio_contracts`, cấm chạm `studio_app`).

---

## 2. Bốn hợp đồng (`studio_contracts`) + tập node đóng

### 2.1 `recipe` (SWE giữ bút)
`Recipe`: `agent_id` · `tenant_id: UUID` · `dag` (nodes + edges) · `kb_binding` (`kb_id` + `section_roles: list[str]`) · `golden_set_ref` · `scorecard_threshold`. `agent_config` gồm chỉ dẫn + model + `tool_whitelist`.

### 2.2 `trace-event` (DE giữ bút, #80)
Một `TraceEvent`/node. Sink là bảng `obs.trace_events` (12 cột: run_id, tenant_id, seq/ordering, node_type, tokens{prompt,completion}, cost, citations[chunk_id], timestamps…). Owner sink = obs (mentor ship); DE viết `trace_reader` để đọc lại timeline. Bất biến: **0-gap ordering** + **rebuild-verify** (dựng lại được từ event).

### 2.3 `kb.search` (DE giữ bút)
Protocol `studio_contracts.kb.KbSearch`:
```python
async def search(query: str, tenant_id: UUID, section_roles: list[str], top_k: int) -> list[KbSearchResultItem]
```
`KbSearchResultItem`: `chunk_id · text · score · tenant_id: UUID · section_role`. `[]` là kết quả hợp lệ (không raise). Ràng buộc contract (docstring `search.py`): lọc **fail-closed tại retrieval**, `section_roles` phân giải **server-side**, chạy qua pool **non-owner** để RLS có hiệu lực, cấm return-all-then-filter.

### 2.4 `scorecard` (AIE-2 giữ bút, #83)
Bảng điểm/case: `success` (Đạt/Không) + `citation_accuracy`. `citation_accuracy` đọc từ **trace** (không phải `answer.citations`). Refusal case (T1/T6) = agent từ chối ∧ không có citation trace thuộc `expected_tenant`. eval-gate: điểm < ngưỡng → chặn publish (exit-code CI style).

### 2.5 NodeType — tập đóng 6 (`studio_contracts.nodes`)
`kb-retrieve · llm-step · tool-call · end · condition · hitl-pause`. Thêm loại thứ 7 = breaking change (mini-RFC + 4/4). Cấm DSL Turing-complete.

---

## 3. Luồng runtime a→z (đầy đủ, tên thật)

### 3.1 Composition & walk
`apps/studio` middleware phân giải header slug → `tenant_id: UUID` từ `core.tenants`, dựng session context, gọi `studio_engine.interpreter.run(recipe, session)`. Interpreter đi DAG. **Trạng thái hiện tại:** sau refactor D12 (#86) interpreter **đọc recipe** thay danh sách cứng; vòng đi lõi vẫn 4 node `(kb-retrieve → llm-step → tool-call → end)`; đủ 6 node-type + đọc `edges` động (condition/hitl-pause) là **D14 (#96)**. `condition`/`hitl-pause` executor còn `NotImplementedError`.

### 3.2 Node executors (AIE-1)
- **kb-retrieve** — fence-EXECUTOR trên fence-DATA. Input `node.params`: `query·tenant_id·section_roles·top_k`. Gọi `KbSearch.search(...)`. Output `list[KbSearchResultItem]`. Luật: `section_roles` truyền nguyên vẹn (server-resolved), cấm lấy rộng rồi lọc bằng LLM.
- **llm-step** — input `node.params` + `retrieved_chunks` (interpreter inject từ kb-retrieve). Output `{answer, tokens, citations, refused}`. **Luật citation:** hợp lệ ⟺ chunk **vừa được retrieve VỪA được nhắc `[chunk_id]` trong answer** (trích "tất cả retrieve" là bug). `tokens` hiện hardcode `Tokens(0,0)` (LLM là fixture replay). `refused = not retrieved_chunks` — chưa đủ cho ca "trong-scope-không-đáp-án" (SC-04): retrieve không rỗng mà vẫn phải từ chối (xem `kb-search.v0.md §6.1a`).
- **tool-call** — chỉ tool trong `agent_config.tool_whitelist`; gác 2 lớp (validator SWE + dispatcher engine). Ngoài whitelist → raise.
- **end** — chốt run, trả `RunResult{run_id, events[], final_state}`.

### 3.3 Fence hai trục (điểm cốt lõi an ninh)
| Trục | Ai chặn | Cơ chế |
|---|---|---|
| `tenant_id` | **RLS** (DB) | policy `FORCE` khoá `app.tenant_id` phiên |
| `section_role` | **chỉ `WHERE section_role = ANY(...)`** | không có RLS policy — mất mệnh đề = hở T6, im lặng |
Đây là lý do `WHERE tenant_id` vẫn viết tường minh dù có RLS: phòng thủ chiều sâu (một refactor quên `set_config` là RLS bốc hơi). Khoảng trống v0 còn lại: `section_roles` hiện dùng **giá trị client khai**, chưa phân giải server-side — chữ ký `search()` không mang danh tính người gọi nên không giải được trong module; đóng T6 hoàn toàn cần **INV-1 tầng session (SWE #112, D17)**.

### 3.4 Ba impl `KbSearch` — phân biệt
| Impl | File | Nguồn | Xếp hạng | Vai |
|---|---|---|---|---|
| `EmptyKbSearch` | engine/demo_stubs | — | luôn `[]` | demo stub |
| `StaticKbSearch` | kb/static_search.py | 42 doc `.md` trong RAM (`load_callisto`) | **token-overlap thô** | v0 S1, `KbRetrieveExecutor` tiêm vào |
| `PgKbSearch` | kb/postgres.py | `kb.chunks` + pgvector | **cosine `<=>`** | bản thật S2 (D13), fail-closed RLS |
`KbSearchService` (kb/search.py) = seam canon, **giữ `NotImplementedError`** (test_search_contract XANH khẳng định; test_leak T1/T6 `xfail`). Un-ratchet (delegate → PgKbSearch + gỡ xfail) là **D17**, không phải D13. AIE-1 D13 tiêm thẳng `PgKbSearch`.

### 3.5 EmbeddingService (AIE-1 giữ bút, #81/#32)
Protocol `async embed(texts: list[str]) -> list[list[float]]`. "2-impl": stub local fixtures (CI) + gateway (INV-4, tùy chọn). `KbIngest`/`PgKbSearch` **nhận EmbeddingService tiêm vào** — cùng một impl cho ingest & search để vector cùng không gian. Ràng buộc DE↔AIE-1: `EMBEDDING_DIM = 8` (`schema.py`, khớp `FakeEmbedding.dim`).

---

## 4. KB pipeline chi tiết (DE flagship)

### 4.1 `doc_factory.py` — máy cắt tĩnh
`load_callisto()`: `glob("docs/callisto/*.md")` (sorted) → `chunk_document` cắt theo heading `##`. `chunk_id = "{doc_id}#c{n}"` (n đếm từ 1/doc, **deterministic**, không UUID — vì `re_index` bắt giữ nguyên chunk_id). 1 chunk = đúng 1 `section_role`; heading `{section: X}` override riêng chunk. `SECTION_VOCAB = {public, hr, finance, engineering}` (đóng, giá trị lạ → raise). `TENANT_IDS` ankor/borea = UUID cứng (S1 fixture, `resolve_tenant_id`; xoá khi Q-G chốt đường phân giải thật). **Đây KHÔNG phải `KbPipeline.chunker`** (spec-DE S2, `NotImplementedError`).

### 4.2 `schema.py` — `kb.chunks` DDL + RLS
```
kb.chunks(chunk_id TEXT PK, tenant_id UUID NOT NULL, section_role TEXT NOT NULL,
          text TEXT, embedding vector(8), created_at)
+ HNSW (embedding vector_cosine_ops) + idx(tenant_id)
ENABLE + FORCE ROW LEVEL SECURITY
POLICY USING/WITH CHECK: tenant_id = NULLIF(current_setting('app.tenant_id', true),'')::uuid
```
Ba lớp fail-closed: `current_setting(...,true)` (unset→NULL không raise), `NULLIF(...,'')` (empty→NULL), `::uuid`. `tenant_id = NULL` không bao giờ đúng → phiên chưa bind thấy 0 dòng. `CREATE EXTENSION vector` chạy ở `docker/postgres-init/01-extensions.sql` (superuser). Hai role `studio_owner` (owns, FORCE cũng cắn owner) / `studio_app` (non-owner, DML-only).

### 4.3 `postgres.py` — tầng thật (đã có sẵn từ trước D13, "CHƯA nối vào")
- `KbIngest.ingest(chunks)`: gom `by_tenant` → `embed([texts])` (dim-check fail-fast) → mỗi tenant 1 transaction, `_bind_tenant`, `_UPSERT ... ON CONFLICT DO UPDATE` (idempotent, giữ chunk_id). Pool **non-owner** để `WITH CHECK` cắn. Trả số dòng ghi.
- `PgKbSearch.search(...)`: `top_k<=0 or not section_roles → []`; `embed([query])` → `_SEARCH` SQL cosine `<=>` với `WHERE tenant_id=%s AND section_role = ANY(%s)`, `_bind_tenant`; `score = 1 - distance` (similarity, khớp quy ước StaticKbSearch). Fail-closed.

### 4.4 `embeddings.py` — fixture vector deterministic (D7)
`derive_vector(text, dim=8)`: bag-of-words — mỗi token `blake2b(digest_size=2) % dim` vào bucket, đếm, chuẩn hoá L2; vector-0 (text rỗng) → `[1,0,…]`. `blake2b` (không `hash()` — tránh `PYTHONHASHSEED`). `build_fixture` khoá theo `chunk_id`, ghi `golden/embeddings-callisto-v0.json` (140 vector). `load_callisto_embeddings()` = **đường đọc duy nhất** (đọc file, không tính lại). **Chọn bag-of-words thay sha256 có đo:** sha256 cosine cùng-doc 0.754 / khác-doc 0.752 (+0.002 nhiễu) vs bag-of-words 0.885/0.867 (+0.018) — nạp vector không-cấu-trúc-cosine vào index cosine thì ranking vô nghĩa. **Không phải embedding ngữ nghĩa**; gateway thật về → **re-record**, migrate `EMBEDDING_DIM 8→768/1536` + rebuild HNSW + re-embed (db_plan Q5).

### 4.5 `scripts/ingest_callisto.py` (D13, mới)
CLI: `load_callisto()` → `KbIngest(pool, _FixtureEmbedding()).ingest()`. Pool non-owner từ `STUDIO_DATABASE_URL`. `_FixtureEmbedding` = adapter cục bộ bọc `derive_vector` (không export EmbeddingService — Owner AIE-1). `main()` thiếu DSN → `SystemExit`. Không tự dựng schema. Chạy thật: ankor 71 · borea 69 = 140, idempotent.

---

## 5. Nhật ký 12 ngày (kỹ thuật, kèm issue #)

**S1 · Tuần 1**
- **D1 (07-20):** kickoff — env 3.14, `pytest` kit tuần-0 (36 pass/24 skip), NDA, teach-back 4 quadrant. Không code mới.
- **D2–D3 (07-21/22):** stub đầu tiên mỗi mảng. DE viết **5 doc Callisto** (D3, 25 chunk), bảng chunk_id phát vào `format.md §8`.
- **D4 (07-23):** DE `StaticKbSearch` v0 (token-overlap, lọc tenant `==` + section_role) + `golden/smoke-5.yaml` (nhãn tay). Quyết không điền `KbSearchService` (giữ NotImplementedError).
- **D5 (07-24, #25/#59):** trace vào Postgres (`obs.trace_events`) + **weekly demo #1**: smoke-eval a→z 4 quadrant, **5/5 PASS**. Adapter `EngineAgentRunner` (RunResult→CaseRun).
- **D6 (07-27, #26–30):** "xâu-kim" — thay mối nối giả bằng gọi thật: interpreter đọc recipe (#27), kb.search + trace nhận call thật (#26).
- **D7 (07-28, #31–35):** `EmbeddingService` Protocol + `StubEmbedding` (AIE-1 #32); DE cấp fixtures embed 25 chunk (#31); CI 100% fixtures.
- **D8 (07-29, #36–40):** INV-1 skeleton — middleware session→{tenant,user,roles} server-side (SWE #38); DE áp tenant filter server-side cho kb.search + trace (#36); client-khai-tenant bị ignore.
- **D9 (07-30, #41–45):** harden happy+negative + evidence-pack. DE: trace 0-gap ordering + rebuild-read + kb.search (#41). Backfill daily-notes D1–D9.
- **D10 (07-31, #46–50):** **GATE-1** — walking-skeleton a→z thật xuyên 4 quadrant + INV-1 ignore demo + trace timeline đọc lại đúng thứ tự + teach-back "fence & eval-gate là LUẬT".

**S2 · Tuần 3**
- **D11 (08-03, #80–84):** **freeze 4 hợp đồng** (trace-event DE #80 · recipe SWE #82 · scorecard AIE-2 #83 · EmbeddingService AIE-1 #81) + design-note/người. Vá drift schema (tenant_id UUID).
- **D12 (08-04, #85–89):** DE doc-factory **5→42 doc / 25→140 chunk** (additive, giữ 5 doc gốc, mỗi tenant đủ 4 vai, 5 override), re-record embeddings 140, annotation skeleton + golden Handbook 30 draft; SWE bắt đầu canvas React Flow 6-node (#87); AIE-1 refactor interpreter đọc recipe (#86).
- **D13 (08-05, #90):** DE lật KB tĩnh → **pgvector thật** — `scripts/ingest_callisto.py` (ankor 71·borea 69=140, idempotent), export `KbIngest`/`PgKbSearch` trong `__init__`; AIE-1 tiêm thẳng `PgKbSearch` vào `KbRetrieveExecutor` (ghép thật DE×AIE-1). `KbSearchService` giữ `NotImplementedError` (un-ratchet=D17). PR kb#13/#14 merged.
- **D14 (08-06, #95):** DE cấp **golden query grid + expected chunks** — `grid_queries.py` (typed) → `emit_grid_queries.py` → `callisto-grid-queries-v0.yaml` (20 case: 14 dương **teeth ≥2 ứng viên cùng scope** + 6 âm T1/T6), `test_grid_inputs.py` annotate-verified. Ground-truth cho AIE-1 (#96) đo recall/precision qua ES 2-impl. Không đổi `EMBEDDING_DIM=8`. PR kb#15 merged.
- **D15 (08-07, #100):** DE hoàn thiện **trace viewer** — `render_timeline` bổ `tokens{prompt/completion}` (số đã thu, trước chưa in) + thêm `check_ts_monotonic` (đo thứ tự phát đơn điệu trên `ts` gốc, `<` nên trùng ts không tính đảo) → viewer báo `✅ monotonic`/`⚠ đảo`. Vá drift docstring `postgres.py`. tenant-filter tại retrieve: **verify** `PgKbSearch` 0-leak (16 passed, 2 xfailed) + scaffold D17, **KHÔNG lật `KbSearchService`**. 4 test mới; kb 190 passed/2 xfailed. PR kb#16 mở.

---

## 6. Trạng thái D13 (05-08) — chi tiết

**#90 (DE, cha #94):** lật KB tĩnh → pgvector thật. Đã đẩy 2 nhánh (chưa PR):
- `agentcore-studio-kb: day13/de-kb-pipeline-live` — `scripts/ingest_callisto.py`, export `KbIngest`/`PgKbSearch` trong `__init__`, `tests/test_ingest_script.py`, `plans/day13_plan.md`, `overview.md`, `detail_overview.md`.
- `agentcore-report: docs/daily-d13-de` — daily-note.

**Bằng chứng (pg 5433, pin 3.14):** kb suite **80 passed / 2 xfailed** (2 xfail = leak qua KbSearchService, cố ý); workspace **355 passed / 8 skipped / 4 xfailed**; ruff/mypy/lint-imports sạch; mutation 93/9 (9 sống sót đều tương đương, có sẵn). Lệnh ingest: ankor 71 · borea 69 = 140.

**Quyết định D13:** không lật `KbSearchService`/un-ratchet xfail (→ D17); AIE-1 tiêm thẳng `PgKbSearch`; adapter embedding cục bộ (không đụng ownership AIE-1); chỉ WRITE trong kb.

**Embedding hiện tại:** cosine `<=>` trên **vector bag-of-words** (chưa ngữ nghĩa). Đổi sang model thật = S3/Phase-2, có điều kiện hạ tầng — không nằm trong D11–20 hay Day 30 (#67 là test-acceptance-set).

**Roadmap D14→D20:** ✅ #95 golden query grid (D14, merged) · ✅ #100 trace viewer tokens+monotonic (D15, PR#16) · **tiếp:** #105 golden-set 30 (D16) · **#110+#112+#114 fence T1/T6 + INV-1 server-side = nơi lật `KbSearchService` (D17)** · #115 nhãn tay (D18) · #120 cost-lineage (D19) · **#125/#129 GATE-2 (D20)** spine 4 mảng chạy thật lần đầu.

> **Ghi chú lật `KbSearchService` (D17, #110):** un-ratchet CẦN 3 bước (delegate `PgKbSearch` + xoá `test_search_contract.py` + gỡ xfail `test_leak` T1/T6) và **phụ thuộc SWE #112** (resolve `section_role` server-side — không có #112 thì **chỉ đóng được T1, T6 vẫn rò**). Ctor đổi `(pool)`→`(pool, embedding)` (DL-13.1) + đồng bộ T3 bên apps lockstep. Các dependency đều là issue **D17 same-day** — phải chốt interface #112 TRƯỚC D17.

---

## 7. Quyết định & invariant then chốt

- **D-13:** danh tính tenant = `core.tenants.id` **UUID bất biến**, slug chỉ là nhãn hiển thị.
- **INV-1:** session→{tenant,user,roles} server-side; client khai tenant bị ignore; fail-closed. Chống T1 IDOR + T6 label-spoof.
- **D-5/D-6:** fixtures-first; gateway/embedding thật là Phase-2 tùy chọn (ZTNA+credential+quota).
- **Fence 2 trục:** RLS(tenant) + WHERE(section_role); T6 đóng hoàn toàn cần server-side role resolution (D17).
- **1-script-2-deliverable:** cùng `load_callisto()` nuôi cả KB data lẫn golden-set → tách máy cắt = lệch chunk_id = mọi case 0 điểm im lặng.
- **Additive corpus:** chỉ thêm doc, 5 doc gốc đóng-băng-tham-chiếu (bảo vệ smoke-5/10).
- **EMBEDDING_DIM = 8** (S1 fixture); re-pin cùng lúc với `FakeEmbedding.dim` khi model thật về.
- **test-first, không sửa test để pass;** un-ratchet là hành vi RIÊNG có phối hợp (P5/P9/D17).

---

## 8. Cách chạy / kiểm (đúng lệnh CI)

```bash
docker compose -f docker-compose.test.yml up -d --wait          # pg17+pgvector, port 5433
export STUDIO_DATABASE_URL_ADMIN=postgresql://studio_owner:changeme@localhost:5433/studio_test
export STUDIO_DATABASE_URL=postgresql://studio_app:changeme@localhost:5433/studio_test
uv run pytest                      # full workspace (conftest gốc cấp admin_pool/pool)
uv run ruff check . && uv run mypy packages apps && uv run lint-imports
uv run python packages/kb/scripts/ingest_callisto.py            # nạp 140 chunk
uv run python packages/kb/scripts/mutation_sweep.py            # ~141s, 93 mutant
```
Pin **3.14** (`.venv/bin/python` hoặc `uv run --python 3.14`), cấm `python3` trần. skip ≠ pass — bật DB trước.

---

## 9. Tham chiếu file

- Luồng runtime: `packages/kb/flow.md`
- Hợp đồng: `packages/kb/docs/contracts/` (`kb-search.v0.md`, `trace-event.v0.md`)
- Schema/pipeline: `packages/kb/src/studio_kb/{schema,postgres,doc_factory,embeddings,static_search,search}.py`
- Trace viewer (đọc): `packages/kb/src/studio_kb/trace_reader.py` (`render_timeline` · `check_walk` · `check_ts_monotonic` · `PgTraceReader`)
- Golden grid (D14): `packages/kb/src/studio_kb/grid_queries.py` + `scripts/emit_grid_queries.py` → `golden/callisto-grid-queries-v0.yaml`
- Đề bài gốc: `docs/requirements/00-orientation/{brief-overview,pre-reading,decisions-locked}.md`
- Kế hoạch/nhật ký DE: `packages/kb/plans/`, `docs/reports/daily-notes/`
- Bản non-tech: `packages/kb/overview.md`
