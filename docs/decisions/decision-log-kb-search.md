---
id: studio.decision-log.kb-search
type: decision-log
owner: DE — Nguyễn Đông Anh
scope: contract `kb.search.v0` (1 trong 2 contract DE cầm)
sibling: decision-log-trace-event.md
started: 2026-08-03
canonical_location: PENDING (Q-2)
---

# Decision-log — kb.search (DE)

> **⚠️ Vị trí canon chưa chốt (Q-2).** DoD #80 đòi *"decision-log ghi"* nhưng repo chưa có file
> decision-log dùng chung. File này là **bản ghi kb-local của DE** cho các quyết chốt ở D11 **thuộc
> contract `kb.search.v0`**; nếu mentor/leader chỉ định một decision-log chung (kit? contracts?),
> **di về đó** và để lại con trỏ. Không tự quyết vị trí canon thay leader.
>
> Nguồn luật freeze: umbrella §3 (`:92-93`) · **D-12** · **INV-5** · GITFLOWS §5. Đổi contract sau
> freeze = **mini-RFC + 4/4 chữ ký + decision-log**.
>
> **Tách file (D11):** decision-log gốc chia đôi theo 2 contract DE cầm — nửa `trace-event` ở
> [`decision-log-trace-event.md`](decision-log-trace-event.md). Hai quyết **schema-drift** (DL-11.8
> `core.jobs`/`core.outbox` không read-RLS · DL-11.9 `wb` `tenant_id`/`obs.golden_sets` DROP) **không
> thuộc riêng contract nào** → canon ở [`../mini-rfc-tenant-schema-unify.md`](../mini-rfc-tenant-schema-unify.md).

## D11 · 2026-08-03 · Contract-freeze workshop (#84)

| # | Quyết | Lý do | Trạng thái / người ký |
|---|---|---|---|
| **DL-11.5** | **Q-G (slug→UUID thật) ĐÓNG theo D-13:** producer/middleware resolve header slug→UUID qua `core.tenants`; kb khoá theo UUID. | Đường resolve **ngoài lằn kb**; kb chỉ nhận UUID. Không chặn freeze kb.search. | ✅ đóng theo D-13 |
| **DL-11.6** | **Q-D stub (`kb.search`) hoãn-có-ghi:** mặc định AIE-1 tự dựng double; bản chung nếu cần đặt `src/studio_kb/stubs.py` class riêng, **không đụng** `KbSearchService`. | `day-03.md:38` + tiền lệ `FakeEmbedding`. Không chặn freeze. | ✅ **AIE-1 xác nhận (engine#15):** tự dựng double **bên engine** — stub sống trong kb thì engine-test không gọi tới được, `.importlinter:20` cấm `studio_engine → studio_kb` (4 quadrant sibling độc lập). Ràng buộc cứng, không phải khẩu vị |

> **Schema-drift (DL-11.8 · DL-11.9)** không thuộc contract này — canon ở
> [`../mini-rfc-tenant-schema-unify.md`](../mini-rfc-tenant-schema-unify.md). Liên quan kb.search ở
> chỗ **`kb.chunks` là mẫu RLS tham chiếu** (`kb_chunks_tenant_isolation`) mà DL-11.8 dựa theo để chốt
> phạm vi bật/loại-trừ; `obs.golden_sets` DROP (DL-11.9) không đụng golden-set thật của kb (`kb/golden/`).

## D13 · 2026-08-05 · Chữ ký ctor `KbSearchService` khi un-ratchet (seam DE×AIE-1, #91/PR-app#3)

| # | Quyết | Lý do | Trạng thái / người ký |
|---|---|---|---|
| **DL-13.1** | **`KbSearchService.__init__` khi un-ratchet (D17) = `(pool, embedding)`, KHÔNG giữ `(pool)`.** `pool` = **non-owner `get_pool()`** — đường dữ liệu kích RLS (`_bind_tenant` đặt `app.tenant_id`, policy `kb_chunks_tenant_isolation` cắn). `embedding` = `EmbeddingService` vector-hoá `query` để cosine với `kb.chunks.embedding`, **cùng không gian với vector seed** (`derive_vector`). `search()` **giữ frozen** (`kb-search.v0.md §0.2`) — `embedding` là collaborator lúc-dựng, không phải tham số mỗi-lần-gọi. | (1) **`.importlinter` cấm `studio_kb → studio_app`/engine** → không import được `EmbeddingService` graded của AIE-1; DI qua ctor là đường DUY NHẤT sạch để nhận đúng embedding, tránh hard-code bag-of-words D13 vào service chính thức (S3 đổi embedding không phải sửa `KbSearchService`). (2) **Đồng dạng `PgKbSearch(pool, embedding)`** — un-ratchet là ủy nhiệm/thay bằng `PgKbSearch`, vốn đã cần `embedding`. (3) Tiêm **một** `EmbeddingService` cho cả `KbIngest` (seed) lẫn search ở composition-root → chống drift seed-space ≠ query-space. (4) Đổi stub↔gateway không sửa class. | 🟡 **Quyết DE — chờ AIE-1 ack.** Đổi `__init__` được phép (chỉ `search()` đóng băng). **Việc D17** (`__init__.py`: un-ratchet sang `PgKbSearch` là RIÊNG của D17); hôm nay `KbSearchService` giữ `NotImplementedError` là **đúng lịch**. **Coordinate PR-app#3:** T3 phải đổi `KbSearchService(pool)` → `KbSearchService(pool, embedding)` tại/sau flip — nếu quên, guard `raises=NotImplementedError` biến `KbSearchService(pool)` thành `TypeError` = FAIL thật lúc land. |

## D22 · 2026-08-19 · Provider embedding mặc định cho retrieval (`kb#38` DoD gạch 4)

> **Vì sao quyết này nằm ở decision-log kb.search:** `EmbeddingService` KHÔNG phải 1 trong 4
> freeze-contract (`umbrella-contract.md:156`) nên không cần mini-RFC 4 chữ ký. Và kb là **consumer
> duy nhất** của seam đó — cả 3 call site `.embed(` trong workspace đều ở `packages/kb`
> (`postgres.py:144,205` · `pipeline.py:54`); `LlmStepExecutor` nhận qua DI rồi **không gọi**
> (`executors.py:236` tự khai "unused here"). Provider embedding chỉ ảnh hưởng **thứ hạng của
> `kb.search`**, nên đây là chỗ ở đúng của nó (lập luận đầy đủ: `plans/real_embedding_plan.md` §0).

| # | Quyết | Lý do | Trạng thái / người ký |
|---|---|---|---|
| **DL-22.1** | **Provider mặc định cho retrieval = `gemini-embedding-001`, gọi qua OpenRouter, `output_dimensionality=2048`, KHÔNG rerank.** | Thắng cả 4 provider chính ở **mọi** metric trên 300 case có nhãn (macro S1–S4 weighted): Hit@1 **0.5726** vs `e5-large` 0.4440 · `bge-m3` 0.4357 · `hash1024` 0.2822 · `dim-8` 0.0207; Hit@3 **0.7137**; MRR@5 **0.6492**; và Decoy Fall **0.0783** — thấp nhất nhóm dense. Qua **toàn bộ** gate per-tầng vs baseline + margin. Không rerank vì cross-encoder **hại** bi-encoder mạnh ở rank-1 (xem §rerank của report), chỉ thêm một tầng tính toán. $0.15/M token, không giới hạn ngày (khác free-tier gọi thẳng Google — đã dính quota ngày thật khi đo). | 🟡 **Quyết DE.** `kb#38` giao gạch này cho AIE-1, nhưng theo §0 nêu trên thì kb tự chốt được — **chờ AIE-1 ack**, không chặn. |
| **DL-22.2** | **Bỏ index HNSW trên `kb.chunks.embedding`** — đây là thứ làm 2048 hợp lệ. | pgvector chặn HNSW ở **2000 chiều** (đã probe: `vector(2000)` ✅, `vector(2001)` ❌). Giữ index ⇒ phải hạ xuống 1536 ⇒ **đo lại toàn bộ report**. Bỏ index ⇒ `<=>` cho kết quả **chính xác tuyệt đối**, khớp `_harness.cosine` (ANN là một nguồn mất recall mà harness không mô phỏng — chênh đó vô hình). Đo thật sau khi bỏ: 800 dòng × `vector(2048)`, seq scan (EXPLAIN xác nhận), 60 truy vấn ⇒ **p50 2.03ms · p95 4.24ms · max 8.07ms**; cả 800 dòng cùng một `section_role` nên đây là ca **xấu nhất về độ chọn lọc**, tức chặn trên bảo thủ. | ✅ chốt (Quyết định #0, `plans/real_embedding_plan.md` §2) |
| **DL-22.3** | **NGƯỠNG QUY MÔ của DL-22.2**: quyết bỏ index chỉ đúng ở cỡ ~800 chunk. Tới ~10⁵–10⁶ chunk thì seq scan sập ⇒ phải dựng lại index ⇒ trần 2000 quay lại ⇒ dim phải hạ xuống ≤2000 (nấc MRL gần nhất **1536**) và **đo lại report ở 1536**. | Viết ngưỡng ra để người sau không phải suy lại, và để "bỏ index" không bị đọc thành một luật vĩnh viễn. | ✅ chốt, đã ghi vào docstring `schema.py::ddl()` |
| **DL-22.4** | **CI vẫn 100% offline (INV-4)**: vector provider API đọc từ `cache/` đã commit, đường ra mạng duy nhất là `record_provider_cache.py` chạy tay. Bề mặt cache phủ = `harness_texts()` (800 `embedding_input` corpus 2.0 + 300 query benchmark) **+ `golden_v2_texts()`** (22 query golden-set 2.0). **CỐ Ý không phủ** golden 1.0 + grid `GQ-`. | Thiếu cache ⇒ `MissingVectorError`, **không** rơi êm về `dim-8` (xanh-giả). Golden 2.0 thêm sau phản hồi AIE-2 ở `kb#40`: 22/22 query vắng mặt nên mọi đường chấm golden 2.0 qua provider đã chốt đều nổ. Không phủ 1.0/`GQ-` vì chúng chạy trên corpus **1.0** mà cache không giữ vector chunk 1.0 nào — ghi query của chúng không mua được gì. | ✅ chốt |

### KHÔNG chọn — ghi lại để khỏi đo lại

| Bị loại | Vì sao |
|---|---|
| `gemini-embedding-2` | Không tốt hơn bản 001 (chênh dưới nhiễu ở Hit@3/Hit@5), **đắt hơn 33%**; lợi thế context 8192 vô nghĩa với chunk ~59 token. |
| `qwen3-embedding-8b` | Rẻ hơn **15×** và hoà ở Hit@3/Hit@5 — nhưng thua **Hit@1 −5.4đ** và Decoy Fall **+4.3đ**. Chỉ quay lại khi **chi phí thành ràng buộc** VÀ sản phẩm đưa cả top-3/5 cho LLM tự chọn; không hợp nếu hiển thị thẳng một kết quả. |
| `bge-m3` / `e5-large` (self-hosted) | Là lựa chọn ĐÚNG nếu tiêu chí đổi thành "không phụ thuộc dịch vụ ngoài" — lúc đó dùng **kèm reranker** (+4–5đ Hit@1, rerank có lợi thật với bi-encoder yếu hơn). Hiện chấp nhận phụ thuộc OpenRouter nên không chọn. |
| `dim-8`, `hash1024` | Thuần lexical, sập hoàn toàn ở S2 (paraphrase). `dim-8` là **fixture baseline**, chưa bao giờ là ứng viên. |

> **Bài học lặp lại, đáng hơn mọi lựa chọn ở trên:** khoảng cách `dense ↔ lexical` là **hàng chục
> điểm**, khoảng cách **nội bộ nhóm dense chỉ vài điểm**. Và §Trần theo K của report cho thấy đáp án
> đúng nằm trong top-50 ở **97.9%** số case trong khi Hit@5 thực tế mới **78.0%** ⇒ **dư địa còn lại
> nằm ở tầng xếp hạng/lọc, không nằm ở model embedding.** Đổi model nữa không mua thêm được gì đáng kể.

### Hệ quả phải xử lý (KHÔNG thuộc quyết này, ghi để không rơi)

- **`EMBEDDING_DIM` 8 → 2048 là thay đổi phối hợp 3 repo**, không phải kb-local: kb (`schema.py` +
  fixture + migration) · engine (`EXPECTED_DIM`, fixture `smoke-01.json`, 2 assert `== 8`, docstring
  `StubEmbedding`, contract `embedding-service.v0.md`) · apps/studio (`FakeEmbedding.dim`, và công
  thức `digest[i % len(digest)]` **thoái hoá** ở dim cao). `.importlinter` cấm engine import kb nên
  **không có cơ chế nào so hai bên** — đây là nợ có ý thức. *(lane khác tự wire — DE chỉ khai)*
- **Migration cột trên DB đã có dữ liệu**: `ALTER COLUMN embedding TYPE vector(2048)` **gãy** nếu
  bảng còn dòng dim cũ (`ERROR: expected 2048 dimensions, not 8` — reproduce trên stack test 5433);
  phải `USING NULL` rồi `re_index`. Suite kb không lộ ra vì nó dọn sạch dòng trước khi chạy.
- **Gate S5 mất nghĩa khi baseline re-record ở 2048**: `max_cosine_mean` phụ thuộc thang cosine của
  từng provider; baseline dim-2048 hạ xuống ~0.296 làm `gemini-001` (0.724) **đỏ** dù chất lượng
  retrieval không đổi. Phải chuyển S5 sang **ngưỡng tuyệt đối** (như `decoy_fall` đã làm) hoặc bỏ
  khỏi `GATED_METRICS` — quyết tường minh, đừng để trôi.

## Câu CHẶN chưa đóng — kb.search (không đóng được trong lằn kb — cần người)

| # | Hỏi ai | Nội dung | Ảnh hưởng |
|---|---|---|---|
| **Q-1** | mentor / leader | Bản `FROZEN` nằm ở draft kb (lật cờ) hay PR bump `SCHEMA_VERSION` ở `contracts` (mentor CODEOWNERS)? | **CHẶN DoD ô 1** (contract commit + freeze). Nếu là contracts → DE cần đường cross-repo, không đóng solo |
| **Q-2** | mentor / leader | decision-log canon ở đâu (chưa có file chung)? + hình thức "4 chữ ký"? | **CHẶN DoD ô 3 & 4** — file này chỉ là bản kb-local tạm |
| **Q-3** | AIE-1 | stub `kb.search` (DL-11.6) | chặn ký kb.search *(vế cost-source/carrier → xem decision-log-trace-event)* |
| **Q-5** | AIE-2 | `expected_citation` khớp `chunk_id` | chặn ký kb.search *(vế field eval đọc trace → xem decision-log-trace-event)* |

> **Chưa có chữ ký nào (0/4).** Bảng chữ ký sống trong contract (`kb-search.v0.md` §0.2). Không ký
> khống — ký sau khi đóng Q-3/Q-5 và đọc delta.
