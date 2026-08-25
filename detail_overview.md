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
- **2026-08-22:** bù D16→D23 sau khi pull `origin/main` mới của kit + fast-forward 9 submodule lên chính `main` của nó. Nội dung chính: D17 lật `KbSearchService`→`PgKbSearch` (fence tại retrieval, T1 gate cứng), D18 nhãn tay + mini-RFC schema-drift, D19 cost-lineage + T6 integration-close (bằng chứng riêng của kb, không mượn engine), **D20 GATE-2** (điểm tạm tính DE 91.91/band I), D21 Callisto 2.0 (80 doc/800 chunk) + `KbPipeline` 5-method wired + eval harness 300 case (S1–S5), D22 sửa 3 lỗi đo (metric name, top_k=10→3, chẩn đoán trần 80% do mất tiêu đề chunk) + embed-view (`embed_text`), **D23 — `EMBEDDING_DIM` 8→2048, bỏ HNSW, nạp lại 800 chunk bằng vector `gemini-embedding-001` thật (từ cache, offline)**. Cập nhật §3.5/§4.4 (embedding không còn thuần bag-of-words ở production), §5 (D16-D23), §6 thay bằng trạng thái D23, thêm §6b (GAP-1/GAP-2 bên `apps/studio`, 22/08).
- **2026-08-25:** bù D24→D27 (20→24/08) sau khi pull `origin/main` mới của kit (32 commit) + refresh 8 submodule (packages/kb chuyển thẳng lên `origin/main` — PR kb#57, việc D27 của chính phiên này, đã merge trước khi kịp ghi log). Nội dung chính: D24 chốt `EMBEDDING_DIM=2048` + migration-không-phá-dữ-liệu (kb#43/#44); D25–D26 `GatewayEmbedding` (app#30) nối THẬT vào `build_embedding()` — cả `chat.py`/`publish.py` (và giờ cả `documents.py` mới) đều dùng chung 1 đường, đóng hẳn "còn treo" đã ghi ở §3.5 từ D23; AIE-1 gửi shell `kb.knowledge_bases`/`kb.documents`/`kb.chunk_pointers` (kb#46/#47, chưa dùng); D27 (24/08) chốt cửa sổ cắt 850/170 bằng benchmark A/B/C thật (kb#53), cutter đa định dạng `chunk_window.py` (kb#50), route `POST /api/admin/documents` chạy thật lần đầu (app#27, dùng `cut_window` không phải `KbPipeline.chunker`), và cột `kb.chunks.doc_id` + `KbPipeline.delete_by_doc_id` (kb#57, PR của chính phiên cập nhật này). Cập nhật §3.5 (đóng "còn treo" embedding), §4 (thêm §4.9 `chunk_window.py`, §4.10 `doc_id`/`delete_by_doc_id`, §4.11 route upload), §5 (D24-D27), §6 (trạng thái 25/08), §7 (quyết định doc_id vs chunk_id). Ghi nhận cross-lane (không phải việc DE, không sửa): AIE-1 đổi kiến trúc interpreter từ DAG-walk 4-node cố định sang **agent-loop 1-LLM-N-tool** (engine#33/#36, giữ `interpreter.run()` cũ làm fallback, đã nối vào 3 call site production ở `apps/studio` #48); AIE-2/SWE chuyển golden-set từ file tĩnh sang bảng `eval.golden_sets` (evalhub#46/#47/#48, tenant-scoped UNIQUE + RLS, route cho tenant tự nạp — studio#56); `create_recipe_d4` bị khai tử toàn workspace, thay bằng `create_recipe` (workbench#42/43, studio#55/57, kb#56); cost seam `cost_of()` giờ wire ở MỌI điểm emit trace (engine#38/#41, contracts#11).

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
| `StaticKbSearch` | kb/static_search.py | doc `.md` trong RAM (`load_callisto`) | **token-overlap thô** | v0 S1, còn dùng cho `test_grid_inputs.py` (nhãn không phụ thuộc số chiều vector) |
| `PgKbSearch` | kb/postgres.py | `kb.chunks` + pgvector | **cosine `<=>`** | bản thật, canon từ **D17** |

**D17 (#110, kb#19, MERGED):** `KbSearchService` (kb/search.py) hết là seam `NotImplementedError` — **un-ratchet xong**: delegate thẳng sang `PgKbSearch`, `test_search_contract.py` xoá, xfail T1/T6 gỡ. Từ đây `KbSearchService` = cửa chính thức, fail-closed tại retrieval, T1 IDOR là gate cứng (đỏ nếu rò). T6 label-spoof đóng **hai lần độc lập**: engine (`test_section_roles_server_resolve.py`, D17/kit#111) + kb tự chứng minh (D20, `358c475`, `test_spine_live.py` — gỡ dòng inject `section_roles` khỏi `interpreter.py` thì 238 test kb cũ vẫn xanh, chứng minh coverage thật chứ không mượn bằng chứng repo khác).

### 3.5 EmbeddingService (AIE-1 giữ bút, #81/#32) — **D23: hết là dim-8 thuần**
Protocol `async embed(texts: list[str]) -> list[list[float]]`. `KbIngest`/`KbPipeline.embed_invoke`/`PgKbSearch` **nhận EmbeddingService tiêm vào** — cùng một impl cho ingest & search để vector cùng không gian.

- **`EMBEDDING_DIM`** (`schema.py`) = chiều **cột** `kb.chunks.embedding`: **8 → 2048** từ D23 (kb#43), bỏ index HNSW (pgvector chặn HNSW ở >2000 chiều; brute-force `<=>` khớp đúng `_harness.cosine` của eval, không lệch do ANN xấp xỉ).
- **`FIXTURE_DIM = 8`** (`embeddings.py`, mới D23) = chiều **fixture đã ghi** (`golden/embeddings-callisto-v0.json`, 140 vector của Callisto 1.0) — **tách khỏi** `EMBEDDING_DIM` cố ý (DL-22.5): re-record fixture ở 2048 chỉ tốn dung lượng git mà không đổi nội dung nói. `derive_vector(text, dim=EMBEDDING_DIM)` mặc định vẫn bám cột; nơi đọc/ghi fixture phải truyền `dim=FIXTURE_DIM` tường minh.
- **Production (`kb.chunks`, 800 chunk Callisto 2.0):** nạp bằng vector **`gemini-embedding-001` @2048 thật** — đọc từ cache đã commit ở kb#40 (`allow_network=False`, không gọi API lúc ingest; chuỗi tin cậy dừng ở lần ghi cache). `_FixtureEmbedding` (adapter dim-8 cũ) đã **xoá hẳn**, không giữ làm fallback — mặc định của `derive_vector` bám `EMBEDDING_DIM` nên nếu giữ lại nó sẽ âm thầm ghi vector bag-of-words 2048-ô dưới nhãn `gemini-embedding-001` mà `count(*)`/`vector_dims()` không phân biệt được (đây là lý do có `MissingVectorError` + test so-từng-số DB↔cache).
- **Đã đóng (25/08, không phải việc DE nhưng chạm đúng seam này):** "còn treo" ghi ở D23 đã hết — `apps/studio/src/studio_app/providers/embeddings.py::GatewayEmbedding` (app#30, `google/gemini-embedding-001` @2048 qua OpenRouter, `async def embed`, đúng contract) giờ là **đường production thật** sau `build_embedding()` (`providers/factory.py`). `routes/chat.py`, `routes/publish.py`, và `routes/documents.py` (mới, D27) đều gọi `build_embedding()` — 3 đường hỏi/nạp giờ đi qua **cùng một** `EmbeddingService`, không còn khoảng lệch ingest-thật/query-giả. AIE-2 route golden-set (§ dưới, D25-26) cũng đã rời khỏi `golden_set_ref="callisto-golden-30-v1"` hardcode — chuyển sang đọc từ `eval.golden_sets` theo tenant (evalhub#47, studio#59), không còn là việc DE cần theo dõi riêng.

---

## 4. KB pipeline chi tiết (DE flagship)

### 4.1 `doc_factory.py` / `doc_factory_v2.py` — hai máy cắt, hai lứa corpus
**v1 (Callisto 1.0, 42 doc/140 chunk, S1-S2):** `load_callisto()`: `glob("docs/callisto/*.md")` (sorted) → `chunk_document` cắt theo heading `##`. `chunk_id = "{doc_id}#c{n}"` (n đếm từ 1/doc, **deterministic**). 1 chunk = đúng 1 `section_role`; heading `{section: X}` override riêng chunk. `SECTION_VOCAB = {public, hr, finance, engineering}` (đóng, giá trị lạ → raise). `TENANT_IDS` ankor/borea = UUID cứng (S1 fixture).

**v2 (Callisto 2.0, 80 doc/800 chunk, D21/#a919c3c, S3):** cutter viết mới, **bỏ hẳn front-matter**. `tenant` lấy từ **tên thư mục** (mô phỏng đúng production: tenant phải đến từ session upload, không phải nội dung file tự khai), `section_role` lấy từ **tiền tố tên file** (vd `hr-benefits.md`). **Cấm tuyệt đối override** qua `{section: X}` — vi phạm `raise` ngay. `doc_id = "{tenant}-{stem}"` (đổi từ v1: 2 tenant cùng tên file sẽ trùng `chunk_id` nếu không tiền tố tenant — bắt bằng test-first **trước khi** viết code). Mỗi file đúng 10 chunk × 2 tenant × 4 role = 800, không filler.

**`Chunk.embed_text`** (mới D22, `doc_factory_core.py`): field tách khỏi `.text`, mặc định `""` → property `embedding_input` rơi về `.text` nếu rỗng (Callisto 1.0 không khai field này nên vector 1.0 không đổi 1 bit). `_cut_document` (v2) nhồi **tiêu đề tài liệu** vào `embed_text` của mọi chunk (v1 vứt hẳn phần trước heading `##` đầu — đây là nguyên nhân chính khiến `#c1` "nuốt" 45% truy vấn dù chỉ là đáp án đúng cho 11%, xem §4.7).

### 4.2 `schema.py` — `kb.chunks` DDL + RLS + migration có điều kiện (D23)
```
kb.chunks(chunk_id TEXT PK, tenant_id UUID NOT NULL, section_role TEXT NOT NULL,
          text TEXT, embed_text TEXT, embedding vector(EMBEDDING_DIM), created_at)
+ idx(tenant_id)          -- KHÔNG còn HNSW từ D23 (pgvector chặn index >2000 chiều;
                            --  brute-force <=> khớp đúng _harness.cosine của eval, không có
                            --  sai lệch "vô hình" do ANN xấp xỉ mà report không mô phỏng được)
ENABLE + FORCE ROW LEVEL SECURITY
POLICY USING/WITH CHECK: tenant_id = NULLIF(current_setting('app.tenant_id', true),'')::uuid
```
`EMBEDDING_DIM`: **8 → 2048** (D23, kb#43). Migration là khối `DO $$` **có điều kiện** (đọc `atttypmod` cột hiện tại, chỉ `ALTER ... USING NULL` khi chiều lệch) — bắt buộc có điều kiện vì `ensure_all_schemas()` chạy **mỗi lần backend boot**; vô điều kiện sẽ xoá vector mỗi lần khởi động lại. `ALTER TABLE ... ADD COLUMN IF NOT EXISTS embed_text` (D22) vì `CREATE TABLE IF NOT EXISTS` không vá bảng đã tồn tại.

Ba lớp fail-closed (RLS): `current_setting(...,true)` (unset→NULL không raise), `NULLIF(...,'')` (empty→NULL), `::uuid`. `CREATE EXTENSION vector` chạy ở `docker/postgres-init/01-extensions.sql`. Hai role `studio_owner` (owns, FORCE cũng cắn owner — `TRUNCATE` cần role này, `DELETE` non-tenant-bound sẽ khớp 0 dòng **im lặng**, đo thật D23 §Quyết định 2) / `studio_app` (non-owner, DML-only, phải `_bind_tenant` trước mọi `DELETE`).

### 4.3 `postgres.py` — tầng thật, canon từ D17
- `KbIngest.ingest(chunks)`: gom `by_tenant` → `embed([c.embedding_input for c in chunks])` (dim-check fail-fast) → mỗi tenant 1 transaction, `_bind_tenant`, `_UPSERT` ghi cả `text` lẫn `embed_text` (D22) `ON CONFLICT DO UPDATE` (idempotent). Pool **non-owner** để `WITH CHECK` cắn.
- `PgKbSearch.search(...)`: `top_k<=0 or not section_roles → []`; `embed([query])` → `_SEARCH` SQL cosine `<=>` với `WHERE tenant_id=%s AND section_role = ANY(%s)`, `_bind_tenant`; `score = 1 - distance`. Fail-closed. **Đây là backend của `KbSearchService`** (D17), không còn "chưa nối vào".

### 4.4 `embeddings.py` — `derive_vector` (bag-of-words) + `FIXTURE_DIM` tách khỏi `EMBEDDING_DIM` (D23)
`derive_vector(text, dim=EMBEDDING_DIM)`: bag-of-words — mỗi token `blake2b(digest_size=2) % dim` vào bucket, đếm, chuẩn hoá L2; vector-0 → `[1,0,…]`. **Đây vẫn là hàm dùng cho fixture-CI** (deterministic, không cần model thật) — **không còn là nguồn vector của `kb.chunks` production** kể từ D23 (xem §3.5). `build_fixture` ghi `golden/embeddings-callisto-v0.json` **ở `dim=FIXTURE_DIM=8`** tường minh (140 vector Callisto 1.0, byte không đổi qua D23). `load_callisto_embeddings()` = đường đọc duy nhất.

### 4.5 Script ingest — hai lệnh, hai lứa
- `scripts/ingest_callisto.py` (D13): `load_callisto()` (v1) → `KbIngest`. Docstring/lệnh mẫu vá khớp README ở D20 (kb#28, thứ tự đúng: seed → **backend boot (cấp grants)** → ingest → frontend — ingest trước backend thì `permission denied for schema kb`, grants cấp ở `app.py` lifespan).
- `scripts/build_callisto.py` + `emit_golden_set.py` (D16): "1 lệnh 2 sản phẩm" — cùng `load_callisto()` phát **cả** KB (embeddings fixture + manifest) **lẫn** golden-set 30 case, nên `chunk_id` khớp *do kiến tạo* (không hai máy cắt lệch nhau).
- Nạp corpus 2.0 vào production (D23, script trong `kb#43`): đọc cache `gemini-embedding-001` @2048 đã commit từ kb#40 (`allow_network=False`), `TRUNCATE` (owner) + `_UPSERT` 800 chunk — chạy **2.1 giây**, offline, tái lập được từ `main`.

### 4.6 `pipeline.py` — `KbPipeline` 5-method, wired D21 (#6ef53d2)
Trước D21 là seam "ships-only" (`NotImplementedError` cả 5 hàm, spec-DE S2). D21 điền ruột **không đụng `KbIngest` cũ** (hai luồng chạy song song — `KbIngest` vẫn là đường production/CI hiện tại; `KbPipeline` là bản đầy đủ hơn cho giai đoạn chuyển giao):
- `chunker` → `_cut_document` (v2). `embed_invoke` → tiêm `EmbeddingService`, fail-fast dim-check, dùng `embedding_input` (D22) chứ không phải `.text` thẳng.
- `index` → tái dùng `_UPSERT`/`_bind_tenant` của `postgres.py` (một nguồn ghi DB, không viết SQL mới).
- `consent_purge` → `DELETE` theo tenant sau `_bind_tenant` (không phải `TRUNCATE` — non-owner không có quyền, và `DELETE` thiếu bind sẽ xoá 0 dòng câm lặng, xem §4.2).
- `re_index` → dựng lại `Chunk` **từ cột `embed_text` trong DB**, không suy lại từ `text` (suy lại sẽ mất tiêu đề đã nhồi + thống kê boilerplate theo scope — không tái tạo được từ 1 dòng đơn lẻ).

### 4.7 embed-view — tách "chữ để hiển thị" khỏi "chữ để tính vector" (D22)
Phát hiện gốc: 55% ca trượt của model tốt nhất có top-1 **đúng tài liệu, sai chunk**; `#c1` được trả về gấp 4 lần tần suất nó thực sự là đáp án. Nguyên nhân: `doc_factory` (v1 lẫn v2 bản đầu) vứt tiêu đề tài liệu khi cắt theo heading `##` đầu tiên → chủ đề cấp-tài-liệu không nằm trong chunk nào ngoài chunk đầu, khiến `#c1` "nuốt" mọi truy vấn liên quan chủ đề. Thêm câu lặp (boilerplate, 14.3% số câu trong một scope lặp ≥2 chunk) càng pha loãng.

Vá: `Chunk.embed_text` (§4.1) mang tiêu đề doc + đã cắt boilerplate (đếm **theo scope** `(tenant,role)`, ngưỡng 3 lần — ngưỡng 2 cắt oan nội dung thật, ngưỡng 1 cắt sạch); `text` (hiển thị + chấm golden) giữ nguyên. Hiệu quả đo trên hash-512: hit@3 0.3651→0.3942 (+8.0%), hit@10 0.4813→0.5477 (+13.8%). **Trên `EMBEDDING_DIM=8` gần như không đổi** (8 chiều không đủ chỗ biểu diễn thêm token) — lợi ích thật chỉ hiện khi có embedding dense (D23 giải quyết đúng phần này).

### 4.9 `chunk_window.py` — cutter cửa sổ trượt cho nội dung tự do (D27, kb#50/#53)
Máy cắt **thứ ba** (khác `doc_factory`/`doc_factory_v2` §4.1 — cả hai cắt theo heading `## `, raise khi thiếu cấu trúc). `cut_window(text, doc_id, tenant_id, role, *, size=850, overlap=170)`: cắt theo `str.split()` (SỐ TỪ, không phải token — repo không kéo `tiktoken` vì phá INV-4 "CI offline"), `chunk_id = f"{doc_id}#c{n}"` cùng khuôn `_cut_document` (idempotent qua `ON CONFLICT DO UPDATE`). Text/khoảng trắng rỗng → `[]`, không raise (khác I7 của `_cut_document`).

**850/170 chốt bằng benchmark A/B/C thật (kb#53), không suy luận:** đo trên 100 câu hỏi × 3 cấu hình (200/50 · 500/100 · 850/170) + `gemini-embedding-001` thật. Cấu hình hẹp hơn (200/50) tưởng "bắt ngữ nghĩa chính xác hơn" nhưng thực ra sinh 140 chunk cạnh tranh (so với 33 ở 850/170) — nhiều chunk "gần đúng chủ đề" chen vào top-k, cosine cao hơn không đồng nghĩa đúng nhiều hơn. Stress test ngữ cảnh dài (150 từ) dứt khoát hơn: 850/170 Hit@1 không đổi, 200/50 sụp (Hit@1 rớt >50%, giữ-nguyên-vẹn-ngữ-cảnh chỉ 31.6%). Số 850 neo vào trần input 2048 token của `gemini-embedding-001` (đo `tiktoken` cl100k_base offline-once trên 15 file thật: tệ nhất 2.32 token/từ → 850 từ ≈ 1972 token, đệm ~76 token). Xem `packages/kb/chunking/report.md` cho số liệu đầy đủ.

### 4.10 `kb.chunks.doc_id` + `KbPipeline.delete_by_doc_id` (D27, kb#57 — PR của phiên cập nhật này)
**Vấn đề:** `kb.chunks` trước giờ không có cột `doc_id` riêng — mã tài liệu chỉ tồn tại NHÚNG trong tiền tố `chunk_id` (PK toàn bảng, không tenant-scoped, nên phải mang thêm `tenant_hex`+hash để tránh đụng PK). Không có cột riêng ⇒ không viết được `WHERE doc_id = ...` để xoá một tài liệu.

**Thiết kế:** tách `chunk_id` (PK, KHÔNG đổi — vẫn `{tenant_hex}-{slug(role)}-{slug(stem)}-{hash8}#c{n}`) khỏi `doc_id` MỚI (cột riêng, = `_slugify(stem)` thuần, KHÔNG mang hash/tenant). `Chunk` (`doc_factory_core.py`) thêm field `doc_id: str = ""` (mặc định rỗng, cùng khuôn `embed_text` — chunk dựng từ `doc_factory`/`doc_factory_v2` không khai field này, không đổi hành vi cũ). `schema.py`: `ALTER TABLE kb.chunks ADD COLUMN IF NOT EXISTS doc_id TEXT` + `idx(tenant_id, doc_id)`. `_UPSERT`/`KbPipeline.index`/`re_index` (`postgres.py`/`pipeline.py`) ghi và giữ nguyên cột qua vòng đời re-index.

```python
async def delete_by_doc_id(self, tenant_id: UUID, doc_id: str) -> int:
    # DELETE FROM kb.chunks WHERE tenant_id = %s AND doc_id = %s — tenant-scoped y hệt
    # consent_purge (RLS USING/WITH CHECK + WHERE tường minh, phòng thủ chiều sâu).
```

**Quyết định KHÔNG làm** (đã cân nhắc, chốt cùng lúc): **không UNIQUE(tenant_id, doc_id)** — `kb.chunks` là 1-dòng-1-chunk nên nhiều dòng của CÙNG một tài liệu BẮT BUỘC chia sẻ 1 `doc_id`; UNIQUE trực tiếp trên bảng này là sai kỹ thuật (sẽ chặn cả chunk thứ 2 của 1 doc hợp lệ). Hệ quả chấp nhận: 2 file GỐC khác nhau trùng slug (vd `"Doc 123.md"`/`"doc-123.md"` → cùng `"doc-123"`) sẽ **ghi đè êm** lẫn nhau — không dựng bảng đăng ký tên gốc riêng để chặn cứng (ngoài phạm vi).

### 4.11 `POST /api/admin/documents` (`apps/studio/routes/documents.py`, app#27/#58) — route upload chạy thật
Không thuộc `packages/kb` nhưng là consumer DUY NHẤT hiện tại của `chunk_window.py`+`doc_id`, nên ghi ở đây để bức tranh liền mạch. Nhận 1 file `.md`/`.txt`/`.docx` (≤1 MiB, ≤200k từ sau trích) → `extract_text` → `cut_window` (§4.9, KHÔNG dùng `KbPipeline.chunker`/`_cut_document` vì nội dung tự do không đảm bảo có heading `##`) → stamp `doc_id` lên từng chunk (`dataclasses.replace`) → `pipeline.delete_by_doc_id(tenant_id, doc_id)` (xoá bản cũ TRƯỚC, đóng lỗ "chunk mồ côi" khi re-upload bản ít chunk hơn) → `embed_invoke` + `index`. `section_role` validate qua `fetch_tenant_section_names` (KHÔNG `SECTION_VOCAB` cố định — khớp tên phòng ban thật của tenant, cùng nguồn `routes/chat.py::as_roles` dùng để fence).

---

### 4.12 `tests/embedding-tests/` — bộ đấu trường 300 case, 5 tầng (D21-D22)
Sinh D21, sửa số đo D22. 300 case (S1 65 · S2 61 · S3 60 · S4 55 · S5 59 — mỗi file `cases/s{1..5}.json`), mỗi case **đúng 1** `expected_citation` (verify bằng script, không đoán) nên đơn vị đo là **`hit@k`** (0/1), không phải `recall`/`precision` (cả hai vô nghĩa khi mẫu số luôn = 1). `k=3` khớp production (`workbench/builder.py` dựng node `kb-retrieve` với `top_k=3`; sửa từ `k=10` sai-thực-nghiệm ở D22). Tầng S5 dùng riêng `clean(1-top_sim)` (không có đáp án đúng để "trúng").

`InMemoryRetriever` (harness) mô phỏng đúng thứ tự `PgKbSearch`: lọc `(tenant, section_roles)` **trước**, tính cosine **sau** — nếu lọc sau xếp hạng, điểm sẽ méo. Harness `model-agnostic` qua `EmbeddingService` — không ghim chiều vector, so được nhiều provider trên cùng bộ case. Baseline `EMBEDDING_DIM=8` (bag-of-words) đo được ở tầng S2 = **0.0984 ≈ mức ngẫu nhiên** (mỗi scope 100-200 chunk) — cơ sở thật cho quyết định D23 phải đổi sang dense.

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
- **D16 (08-10, #105, kb#18):** golden-set 30 → **recorded** — `golden_set.py` typed (`GOLDEN_CASES`, `render_yaml()` tái tạo byte-identical bộ D14), `scripts/build_callisto.py`+`emit_golden_set.py` = "1 lệnh 2 sản phẩm" cùng nguồn `load_callisto()`. Rename `draft`→`v1` (pure-rename, R100, 0 nội dung đổi). kb 199 passed/2 xfailed. Dọn đường D17: đọc hết contract frozen thấy 3/4 "blocker" tự gỡ (B1 embedding optional+factory, B2/B4 khoá bởi `kb-search.v0.md §5.2`, B3 carrier có sẵn ở `trace-event.v0.md §7`) — chỉ còn 1 coordinate thật (timing #112).
- **D17 (08-11, #110, kb#19+kb#20):** **fence tại retrieval, un-ratchet `KbSearchService`** — delegate → `PgKbSearch`, xoá `test_search_contract.py`, gỡ xfail T1 (gate cứng) + viết test T6 label-spoof. kb#20 (follow-up): mở rộng operator `mutation_sweep.py` (`cmpbound`/`arith`/`delstmt`, gộp `_points` một nguồn duyệt, bỏ qua mutant tương đương) — 3 tầng kiểm chứng (self-test → meta-mutation → test-mutation). kb 222 passed/1 xfailed; sweep 519 mutant/79 sống sót/0 rác vĩnh viễn.
- **D18 (08-12, #115, kb#21+kb#24+kb#22):** nhãn tay `manual_label` cho 10/30 case (6 pass+4 refuse) — DE giữ **giá trị**, AIE-2 giữ **shape/tên/nơi lưu**. Mini-RFC schema-drift (#5): chốt nhị phân **CẦN**/**KHÔNG CẦN** RLS cho 11 bảng theo bản-chất-data (bỏ nhóm "HOÃN"). Cost-lineage (D19) kéo sớm: `aggregate_run_cost` cộng dồn `event.cost` **on-read** từ `obs.trace_events`, không dựng bảng tổng hợp mới.
- **D19 (08-13, #120, kb#22/#24/#25 MERGED):** khép 3 PR treo + **T6 integration-close bằng bài của chính kb** (`358c475`, không mượn bằng chứng từ `packages/engine`) — self-mutation M-1 (gỡ inject `section_roles`) → 1 failed/238 passed, chứng minh coverage thật. kb **239 passed, 0 xfailed, 0 skipped**. DE tự phát hiện + đính chính công khai một lỗi phát biểu về con trỏ (fetch submodule mà quên fetch kit).
- **D20 (08-14) — GATE-2:** không code mới, ngày trình bằng chứng. kit#158 vá lỗ README (thiếu bước ingest, sai thứ tự backend/ingest — `permission denied for schema kb` nếu ingest trước backend). Tự-chấm 12 ô, khớp 11/12 mentor, 1 ô bất đồng (`S2.4 Tooling`, tự A vs mentor I, kèm 3 artifact). **Điểm tạm tính DE: 91.91, band I** (cách band A đúng 0.59). Callisto 2.0 khởi động **local, chưa push** (nhánh `day20/de-callisto-2.0-experiment`, `doc_factory_v2` + 11 test đỏ-trước→xanh).
- **D21 (08-17, sprint 3 mở):** push hạ tầng Callisto 2.0 (`a919c3c` doc_factory_v2 + 80 doc, `4d8bb92` tinh 800 chunk, `6ef53d2` `KbPipeline` 5-method wired). Dựng local 100-case eval harness (S1-S5) + `InMemoryRetriever` — chưa push.
- **D22 (08-18):** tự vặn thước đo harness — đổi `recall`/`precision` (vô nghĩa khi mẫu số luôn=1) sang `hit@k`; `top_k 10→3` khớp production; chẩn đoán trần ~80% là do mất tiêu đề chunk (`#c1` "nuốt" 45% truy vấn dù chỉ đúng 11%) chứ không phải model kém → vá **embed-view** (`embed_text` tách khỏi `text`), +8-13.8% hit trên hash-512. Golden-set 2.0: đổi `expected` từ cụm ngắn sang cả câu verbatim (khớp chấm-bằng-embedding của AIE-2). CI toàn repo **1320 passed** với Postgres thật.
- **D23 (08-19, kb#43 MERGED):** **`EMBEDDING_DIM` 8→2048, bỏ HNSW, nạp 800 chunk 2.0 bằng vector `gemini-embedding-001` thật** (từ cache kb#40, offline). Tách `FIXTURE_DIM=8` khỏi `EMBEDDING_DIM`. Xoá hẳn `_FixtureEmbedding` (bẫy: mặc định `derive_vector` bám cột nên sẽ âm thầm ghi bag-of-words dưới nhãn gemini). 3 lần tự phát hiện "màu xanh giả" trong ngày (57 test skip câm do sai tên biến DSN, vòng gieo mutation không thực sự ghi file, cả hai tự bắt trước khi báo cáo). kb **756 passed, 0 skip**; kit toàn bộ **1441 passed**.
- **D24 (08-20, kb#44 MERGED):** vá migration `EMBEDDING_DIM` — bản đầu (kb#43) dùng `TRUNCATE` khi đổi chiều cột, **sai** (xoá cả `text`/`embed_text` — hai cột KHÔNG dựng lại được từ đâu khác, vì tài liệu tenant tự upload không lưu file gốc ở nơi thứ hai). Sửa: `ALTER COLUMN embedding TYPE vector(N) USING NULL` — **giữ dòng**, chỉ bỏ vector; dòng còn `embedding IS NULL` thì `_SEARCH` (đã lọc `AND embedding IS NOT NULL`) tự loại nó khỏi kết quả — hạ cấp sạch, không phải rác; phục hồi bằng `KbPipeline.re_index(tenant_id)` (đọc lại `embed_text` từ DB, không cần file gốc). Review AIE-2 bắt.
- **D25 (08-22, kb#46/#47, tác giả AIE-1 — DE chỉ nhận/xác nhận):** shell schema mới `kb.knowledge_bases`/`kb.documents`/`kb.chunk_pointers` (kế thừa hình dạng `kb.chunks` + thêm `doc_id UUID NOT NULL` FK tới `kb.documents`, composite `(tenant_id, doc_id)`) — nền móng cho một mô hình "kho tri thức" nhiều-kho-mỗi-tenant trong tương lai, **song song, KHÔNG thay** `kb.chunks` hiện có. Chưa route/pipeline nào đọc/ghi bảng này (§4.10 dùng cột `doc_id` khác, thêm trực tiếp vào `kb.chunks`, không phải bảng `kb.chunk_pointers` này — hai thứ tên gần giống nhau, đừng nhầm).
- **D26 (08-22→23, không phải PR kb):** `apps/studio` nối `GatewayEmbedding` (app#30) thật vào `build_embedding()` — đóng "còn treo" §3.5 đã ghi từ D23 (routes `chat`/`publish` dùng chung 1 `EmbeddingService` thật, không còn lệch ingest-thật/query-giả).
- **D27 (08-24, kb#50/#53/#57 MERGED):** ba việc trong một ngày. (1) **kb#50** — `chunk_window.py`: cutter cửa sổ trượt cho nội dung tự do (§4.9), không đòi heading `##`. (2) **kb#53** — benchmark A/B/C thật (100 câu, 3 cấu hình, embedding thật) chốt `WORDS_PER_CHUNK=850`/`WORDS_OVERLAP=170` (§4.9), thắng cả benchmark chính lẫn stress-test ngữ cảnh dài. (3) **kb#57** — cột `kb.chunks.doc_id` (tách khỏi PK `chunk_id`) + `KbPipeline.delete_by_doc_id` (§4.10); cùng ngày `apps/studio` route `POST /api/admin/documents` (app#27/#58) lần đầu chạy thật — tab "Tài liệu" trên UI hết là placeholder tĩnh. Test-first cả 3: viết test đỏ trước, tự gieo mutation vào `_DELETE_DOC` (bỏ `AND doc_id = %s`) xác nhận đỏ đúng chỗ trước khi coi là xong. kb full suite **455→460 passed** (kb#57 +5 test), `apps/studio` route suite **13→15 passed** (1 assertion đổi có chủ đích do đổi ý nghĩa `UploadDocumentResponse.doc_id`, 2 test mới).

---

## 6. Trạng thái hiện tại (25/08, sau D27) — chi tiết

**PR đang mở/theo dõi:** không có PR kb nào mở tính tới 25/08; nhánh gần nhất đã merge là `de/kb-doc-id-column-delete-by-doc-id` (kb#57, D27, `origin/main` giờ ở `e705951`). PR anh em `de/documents-doc-id-column-delete-orphan-fix` (app#58, route `POST /api/admin/documents` dùng cột `doc_id`) **vẫn OPEN** ở `apps/studio` tính tới giờ ghi log — merge PR đó sau/cùng lúc kb#57 vì nó phụ thuộc cột `doc_id` mới.

**Trạng thái Callisto 2.0 (production `kb.chunks`):** 800 chunk curate tay (ankor 400 · borea 400) + N chunk mới do tenant tự upload qua `POST /api/admin/documents` (§4.11, kể từ D27) — cả hai loại giờ **cùng một bảng, cùng cơ chế embed thật** (`GatewayEmbedding`, đóng ở D26). Không còn index HNSW (brute-force `<=>` cố ý, xem §4.2). Golden-set production **đã rời khỏi hardcode** `callisto-golden-30-v1` — evalhub#47/studio#59 (D25-26, không phải việc DE) chuyển sang đọc `eval.golden_sets` theo tenant, cho phép tenant tự nạp bộ câu mẫu của mình (studio#56).

**Khoảng trống đã biết, cố ý chưa vá (không phải bug đang bị khai thác, không đổi từ D23):** hàng rào `section_role` vẫn chỉ lọc bằng `WHERE` trong `postgres.py`, **chưa có RLS policy riêng** như `tenant_id`. `core.user_sections` (GAP-2, merge 22/08) vẫn chưa có reader/writer nào dùng — tiền đề chưa được tận dụng.

**Khoảng trống MỚI, cố ý chưa vá (D27, ghi nhận cùng lúc thêm `doc_id`):** 2 file gốc khác nhau trùng `_slugify(stem)` sẽ ghi đè êm lẫn nhau qua `delete_by_doc_id` — không có UNIQUE/bảng đăng ký tên gốc chặn (xem §4.10, lý do kỹ thuật vì sao KHÔNG thể UNIQUE trực tiếp trên `kb.chunks`). Route upload chưa có màn hình xoá-toàn-bộ/re-index-toàn-bộ dùng `consent_purge`/`re_index` dù cả hai đã có sẵn ở `KbPipeline` từ D21 — 2 nút tương ứng trên UI (`DocumentsPlaceholderTab.tsx`) vẫn cố ý để `disabled`.

**Cross-lane đáng chú ý, không phải việc DE (20→24/08):** kiến trúc lõi interpreter (AIE-1) đổi từ DAG-walk 4-node cố định sang **agent-loop 1-LLM-N-tool** (engine#33/#36, `interpreter.run()` cũ giữ làm fallback, đã nối 3 call site production ở `apps/studio` — engine#48), có tool thật ngoài `kb_search` (calculator/current_datetime, engine#32/#35). Cost tracking (`cost_of()`, contracts#11) giờ wire ở MỌI điểm emit `TraceEvent` (engine#38/#41), trước đó rải rác. `create_recipe_d4` bị khai tử toàn workspace, thay bằng `create_recipe` chung (workbench#42/43, studio#55/57, kb#56) — không đụng bất kỳ `chunk_id`/`doc_id` nào của kb.

---

## 7. Quyết định & invariant then chốt

- **D-13:** danh tính tenant = `core.tenants.id` **UUID bất biến**, slug chỉ là nhãn hiển thị.
- **INV-1:** session→{tenant,user,roles} server-side; client khai tenant bị ignore; fail-closed. Chống T1 IDOR + T6 label-spoof.
- **D-5/D-6:** fixtures-first; gateway/embedding thật là Phase-2 tùy chọn (ZTNA+credential+quota).
- **Fence 2 trục:** RLS(tenant, từ D13) + WHERE(section_role, vẫn vậy tới 25/08 — chưa đổi qua D24-D27). T6 label-spoof đóng D17 (server-side role resolution, engine #111) + D20 (kb tự chứng minh coverage, `358c475`) — nhưng đó là chặn ở **tầng interpreter**, không phải RLS ở tầng DB cho `section_role`; xem §6 "khoảng trống đã biết".
- **1-script-2-deliverable:** cùng `load_callisto()` nuôi cả KB data lẫn golden-set → tách máy cắt = lệch chunk_id = mọi case 0 điểm im lặng. Giữ nguyên nguyên tắc ở D16 (`build_callisto.py`).
- **Additive corpus (1.0):** chỉ thêm doc, 5 doc gốc đóng-băng-tham-chiếu (bảo vệ smoke-5/10). **Corpus 2.0 là lứa riêng** (80 doc/800 chunk, D21), không additive lên 1.0 — hai bộ song song, không trộn.
- **`EMBEDDING_DIM` = chiều cột, đổi theo hạ tầng thật:** 8 (S1-S2 fixture) → **2048 (D23, `gemini-embedding-001`)**. **`FIXTURE_DIM` = 8 cố định** (D23) — chiều riêng của fixture-CI, tách khỏi cột để không phải re-record blob nhị phân mỗi lần đổi provider.
- **test-first, không sửa test để pass;** un-ratchet là hành vi RIÊNG có phối hợp — đã áp dụng đúng ở D17 (un-ratchet `KbSearchService`) và D21 (`doc_factory_v2` 11 test đỏ-trước→xanh, mutation-proven).
- **"Xanh không phải bằng chứng, chỉ là vắng mặt bằng chứng ngược lại" (D23):** ba lần tự phát hiện màu-xanh-giả trong cùng một ngày (skip câm do sai biến DSN, vòng mutation không ghi file thật, mini-corpus quá nhỏ để lộ bug filter) — luôn `rm -rf __pycache__` giữa các vòng gieo đột biến, luôn kiểm số `skipped` như một cảnh báo chứ không phải phần nền.
- **`chunk_id` (PK) ≠ `doc_id` (cột xoá) — không gộp làm một (D27, §4.10):** `chunk_id` PHẢI mang đủ thông tin để không đụng PK toàn bảng (tenant-hex + hash tên gốc); `doc_id` PHẢI thân thiện với người dùng/caller (slug thuần) để dùng làm khoá xoá. Một biến duy nhất không thoả được cả hai yêu cầu — tách thành 2 giá trị riêng thay vì ép chung, đánh đổi lấy: **không** UNIQUE(tenant_id, doc_id) được (nhiều chunk/1 doc dùng chung 1 giá trị — về cấu trúc), nên 2 file gốc trùng slug ghi đè êm nhau (chấp nhận, không chặn).
- **Xoá-trước-rồi-ghi, không dựa vào `ON CONFLICT` để dọn rác (D27):** `_UPSERT` idempotent theo `chunk_id` xử lý đúng trường hợp "chunk_id trùng thì ghi đè", nhưng KHÔNG dọn được chunk THỪA khi bản mới có ít chunk hơn bản cũ (chunk_id mới không trùng gì để "đè" lên). Route upload gọi `delete_by_doc_id` TRƯỚC `index` để đóng đúng lỗ này — bài học chung: idempotent-ghi không thay được idempotent-xoá khi số lượng bản ghi có thể GIẢM giữa hai lần chạy.

---

## 8. Cách chạy / kiểm (đúng lệnh CI)

```bash
docker compose -f docker-compose.test.yml up -d --wait          # pg17+pgvector, port 5433
export STUDIO_DATABASE_URL_ADMIN=postgresql://studio_owner:changeme@localhost:5433/studio_test
export STUDIO_DATABASE_URL=postgresql://studio_app:changeme@localhost:5433/studio_test
uv run pytest                      # full workspace (conftest gốc cấp admin_pool/pool)
uv run ruff check . && uv run mypy packages apps && uv run lint-imports
uv run python packages/kb/scripts/ingest_callisto.py            # nạp 140 chunk (Callisto 1.0)
uv run python packages/kb/scripts/ingest_callisto_v2.py         # nạp 800 chunk (Callisto 2.0, vector gemini @2048 từ cache)
uv run python packages/kb/scripts/mutation_sweep.py             # ~141s, 500+ mutant
uv run pytest packages/kb/tests/embedding-tests/                # 300-case eval harness (S1-S5), cần DB thật
```
Pin **3.14** (`.venv/bin/python` hoặc `uv run --python 3.14`), cấm `python3` trần. skip ≠ pass — bật DB trước, export **cả** `STUDIO_DATABASE_URL_ADMIN` lẫn `STUDIO_DATABASE_URL` (D23: sai tên biến DSN từng làm skip câm 57 bài Postgres mà trông như suite xanh).

---

## 9. Tham chiếu file

- Luồng runtime: `packages/kb/flow.md`
- Hợp đồng: `packages/kb/docs/contracts/` (`kb-search.v0.md`, `trace-event.v0.md`)
- Schema/pipeline: `packages/kb/src/studio_kb/{schema,postgres,pipeline,doc_factory,doc_factory_core,doc_factory_v2,embeddings,static_search,search}.py`
- Cutter nội dung tự do + upload (D27): `packages/kb/src/studio_kb/chunk_window.py` · `packages/kb/chunking/report.md` (số liệu benchmark A/B/C) · route consumer `apps/studio/src/studio_app/routes/documents.py`
- Golden-set: `golden_set.py`/`golden_set_core.py`/`golden_set_v2.py` (v1 30 case · v2 tương ứng Callisto 2.0)
- Trace viewer (đọc): `packages/kb/src/studio_kb/trace_reader.py` (`render_timeline` · `check_walk` · `check_ts_monotonic` · `PgTraceReader`)
- Golden grid (D14): `packages/kb/src/studio_kb/grid_queries.py` + `scripts/emit_grid_queries.py` → `golden/callisto-grid-queries-v0.yaml`
- Eval harness 300-case S1-S5 (D21-D23): `packages/kb/tests/embedding-tests/` (`_harness.py`, `cases/s{1..5}.json`, `providers.py`, `embedding_report.md`)
- Mini-RFC schema-drift: `packages/kb/docs/mini-rfc-tenant-schema-unify.md`
- Đề bài gốc: `docs/requirements/00-orientation/{brief-overview,pre-reading,decisions-locked}.md`
- Kế hoạch/nhật ký DE: `packages/kb/plans/`, `docs/reports/daily-notes/`, GATE-2: `docs/reports/gate-2/de-DongAnh2704.md`
- Bản non-tech: `packages/kb/overview.md`
