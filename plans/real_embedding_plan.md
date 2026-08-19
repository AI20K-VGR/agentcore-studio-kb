# Plan: nối embedding THẬT vào kb

Trạng thái: **Quyết định #0 ĐÃ CHỐT — bỏ HNSW, giữ 2048 chiều** (xem §2). Viết sau khi kiểm lại quyền sở hữu seam
`EmbeddingService` (xem §0) — kết luận khác với giả định trước đó, nên plan này thay cho cách
đóng khung "cross-lane, chờ AIE-1" ở các thảo luận trước.

Liên quan: [`kb#38`](https://github.com/AI20K-VGR/agentcore-studio-kb/issues/38) ·
[`kb#39`](https://github.com/AI20K-VGR/agentcore-studio-kb/pull/39) (điều kiện tiên quyết, xem §5).

---

## §0. Ai thật sự dùng `EmbeddingService` — đã kiểm, không phải suy đoán

Giả định cũ ("embedding là deliverable được chấm của AIE-1, kb không được đụng") **sai về mặt
chức năng**. Ba phép grep:

| Kiểm | Kết quả |
|---|---|
| `grep -rn "\.embed(" packages/*/src apps/*/src` | **3 call site, cả 3 nằm trong `packages/kb`** — `postgres.py:144,205` · `pipeline.py:54` |
| `LlmStepExecutor` (engine) có gọi không? | **Không.** Nhận qua constructor-DI rồi để đó; docstring tự khai: *"`embedding` is wired via constructor-DI but **unused here**"* (`executors.py:236`) |
| `get_embedding()` có ai gọi không? | **Không ai.** 0 call site ngoài chính định nghĩa → **dead code** |
| Provider chạy thật ở route là gì? | `CallistoEmbedding` (`providers/factory.py:16`) — lớp vỏ 2 dòng quanh **`studio_kb.embeddings.derive_vector` của chính kb** |

**Kết luận: kb là consumer duy nhất của seam này.** Doctrine F3 / "deliverable được chấm của
AIE-1" đang bảo vệ đúng cái selector chết (`get_embedding()`), không phải đường ingest của kb.

Hệ quả cho `kb#38`: gạch cuối của DoD — *"Provider mặc định cho retrieval chốt bằng văn bản"* —
issue giao cho AIE-1, nhưng **kb tự viết được**, vì không module nào khác chịu ảnh hưởng. Cần nêu
lại điều này trong issue thay vì chờ.

## §1. Thứ THẬT SỰ ràng buộc (không phải quyền sở hữu)

1. **INV-4 fixtures-first** (`umbrella-contract.md:219`) — CI chạy 100% recorded fixtures; live
   chỉ qua flag. Đây là ràng buộc cứng, không thương lượng.
2. **`EMBEDDING_DIM = 8`** (`schema.py:33`) ↔ cột `vector(8)`. Trần 2000 chiều của HNSW **không
   còn ràng buộc** sau §2 (bỏ index), nhưng con số 8 thì vẫn — nó ghim cả cột lẫn fixture.
3. **`.importlinter`** — `studio_kb` không được import `studio_app`. Provider mới không đặt trong
   kb package được nếu nó cần `settings` của app.
4. **F3** — không thêm `embed()` vào `GeminiProvider`. `apps/studio/tests/test_providers.py:39`
   assert `not hasattr(provider, "embed")`. Provider embedding phải là **class riêng**.
   (Không sửa test cho pass.)

`umbrella-contract.md:156` nói rõ `EmbeddingService` **không phải 1 trong 4 freeze-contract** →
**không cần mini-RFC 4 chữ ký**.

## §2. QUYẾT ĐỊNH #0 — ĐÃ CHỐT: **bỏ HNSW, giữ `output_dimensionality=2048`**

Hai vế của quyết định này khoá vào nhau: **bỏ HNSW là thứ làm 2048 dùng được.**

| | Giữ HNSW | **Bỏ HNSW (đã chọn)** |
|---|---|---|
| Trần chiều | **2000** (đã probe: `vector(2000)` ✅, `vector(2001)` ❌ *"cannot have more than 2000 dimensions for hnsw index"*) | **không có trần** |
| Dim dùng được | 1536 (nấc MRL duy nhất lọt dưới trần) | **2048** — đúng dim report đã đo |
| Truy xuất | ANN **xấp xỉ** | seq scan **chính xác tuyệt đối** |
| Số trong report | phải **đo lại toàn bộ** ở 1536 | **giữ nguyên, dùng được ngay** |
| Chi phí đổi | 0 | sửa `schema.py:53-54` + 1 dòng `callisto-doc-schema.md:121` |

### Ba lý do

1. **Ở 800 chunk, HNSW là lỗ vốn.** Brute force = 800 phép so cosine, tính bằng micro-giây. HNSW
   sinh ra cho hàng triệu vector; ở quy mô này nó gần như không tiết kiệm gì mà vẫn phải trả trần
   2000 chiều + thời gian dựng + RAM.
2. **HNSW làm lệch chính thứ đang đo.** Toàn bộ eval của kb đo độ chính xác retrieval, và
   `_harness.cosine` (`_harness.py:116-123`) tính cosine **chính xác** bằng Python thuần. Production
   có HNSW thì thêm một nguồn mất recall mà harness **không mô phỏng** — hit@1/hit@3 trong report sẽ
   cao hơn thực tế chạy thật, và chênh đó **vô hình**. Bỏ index thì `<=>` của pgvector cho kết quả
   đúng bằng brute force, hai bên khớp nhau.
3. **Giữ được toàn bộ công đo đã bỏ ra.** Cả 3 provider API trong report đo ở 2048
   (`embedding_report.md:75-77`). Chọn 1536 nghĩa là đo lại từ đầu — thêm API call, thêm quota, thêm
   một vòng đối chiếu. Bỏ HNSW làm 2048 hợp lệ, số hiện có dùng thẳng.

### Chi phí đổi — nhỏ và đã khoanh vùng

**Ai đang ghim HNSW:** chỉ `schema.py:53-54` và một dòng bảng trong `callisto-doc-schema.md:121`.
**Không test nào assert index đó tồn tại** (`grep -rn kb_chunks_embedding_hnsw_idx --include="*.py"`
→ 0 kết quả ngoài chính DDL).

### Đánh đổi đã nhận, không phải bỏ qua

- [ ] **Xác nhận seq scan chấp nhận được** — đo p95 của `<=>` trên `vector(2048)` × 800 dòng. Đây là
      **kiểm chứng quyết định đã chốt**, không phải cổng để chốt lại. Nếu p95 xấu bất ngờ (> ~50ms)
      thì mở lại §2, nhưng dự kiến ở mức micro-giây → mili-giây.
- [ ] **Ghi rõ ngưỡng quy mô làm quyết định này hết đúng.** Bỏ HNSW đúng ở 800 chunk; ở ~10⁵–10⁶
      chunk thì seq scan sập và phải quay lại index — lúc đó trần 2000 quay lại, và 2048 sẽ phải hạ
      xuống 1536. Viết ngưỡng đó vào docstring `schema.py` để người sau không phải suy lại.
- [ ] **Không dùng 3072 dù bỏ HNSW đã cho phép.** 3072 được Google chuẩn hoá sẵn (hết bẫy
      normalize), nhưng đổi lại phải đo lại toàn bộ. Chọn 2048 là ưu tiên giữ số đã đo. Ghi lại lựa
      chọn này để nó là một quyết định, không phải một sự tình cờ.

### Bẫy normalize — theo dõi, không chặn

Docs Google: *"If you are using `gemini-embedding-001`, you must manually normalize non-3072
dimensions."* 2048 là non-3072 ⇒ vector Gemini-001 trả về **chưa chuẩn hoá**.

**Không hỏng ở cấu hình hiện tại**, vì cosine bất biến với tỉ lệ: `_harness.cosine` chia cho tích hai
norm, và `<=>` của pgvector là cosine distance cũng tự chuẩn hoá. Thứ hạng đúng ở cả hai đường.

Nó **chỉ cắn nếu ai đó đổi `<=>` sang `<#>`** (inner product) cho nhanh — lúc đó vector chưa chuẩn
hoá cho thứ hạng sai **âm thầm**.

- [ ] L2-normalize ngay trong `GeminiEmbedding.embed()` như phòng thủ (rẻ, một dòng), **và** ghi
      comment cạnh `_SEARCH` trong `postgres.py` nói rõ vì sao toán tử phải là `<=>`.

## §3. PR-1 — provider + cache, KHÔNG đổi dim

Mục tiêu: đóng `kb#38` (số tái lập được từ `main`), chưa đụng schema. Rollback độc lập.

- [ ] Class `GeminiEmbedding` riêng, chỉ cần `async embed(texts) -> list[list[float]]`.
      **Không phải method trên `GeminiProvider`** (§1.4).
- [ ] Đặt tại `tests/embedding-tests/` — là test code nên không vi phạm `.importlinter`, và không
      kéo `google-genai` vào dependency của kb package.
- [ ] `tests/embedding-tests/compare_providers.py` — script so provider, gọi qua đúng
      `conftest.py::embedding_provider` (đúng chữ trong `kb#38`), không viết bản "tương đương".
- [ ] Cache theo `sha256(text)` **commit kèm** → chạy lại 0 API call, CI không bao giờ quay ra
      ngoài. Đây vừa là INV-4 vừa là gạch "tái lập được từ main" của `kb#38`.
- [ ] `google-genai` import lazy. **Thiếu `STUDIO_GEMINI_API_KEY` ⇒ skip có lý do**, tuyệt đối
      không âm thầm rơi về dim-8 — đó là cách CI xanh trong khi đang đo nhầm provider.
- [ ] Tách **validation set** khỏi 300 case báo cáo, TRƯỚC khi tune bất kỳ ngưỡng nào
      (`kb#38` gạch 3; hiện `cases/` vẫn chỉ có `s1..s5.json`).
- [ ] **Giữ `output_dimensionality=2048`** (§2) → số provider API trong report **không phải đo
      lại**. Việc còn lại là làm chúng *tái lập được*, không phải làm lại chúng. Xem §4.
- [ ] Cập nhật `embedding_report.md`: bổ sung **mục "cách chạy"** (report hiện không có) + ghi rõ
      2048 giờ là con số đã chốt, kèm lý do bỏ HNSW.
- [ ] Viết **DEC chốt provider mặc định** — theo §0, đây là việc kb tự làm được.

## §4. Số provider API trong report — GIỮ, không đo lại

Trước §2 mục này viết "phải bỏ vì 2048 vượt trần HNSW 2000". **Quyết định bỏ HNSW làm lý do đó biến
mất.** Ghi lại nguyên văn diễn biến để người sau không đọc nhầm là bỏ sót.

Cả 3 provider API đo ở `output_dimensionality=2048` (`embedding_report.md:75-77`). Sau §2:

| Vấn đề nêu trước đây | Còn đúng không |
|---|---|
| Vượt trần HNSW 2000 → không index được | ❌ **Hết** — không còn index |
| Không nằm trong 3 nấc khuyến nghị của Google (768/1536/3072) | ✅ Vẫn đúng, nhưng **vô hại**: khuyến nghị là về chất lượng cắt MRL, không phải ràng buộc kỹ thuật |
| Không phải dim gốc (gốc 3072) | ✅ Vẫn đúng, và **là lựa chọn có chủ đích** (§2) |

**Thứ hạng trong report vẫn đúng ngay cả khi vector chưa chuẩn hoá**: `_harness.cosine`
(`_harness.py:116-123`) chia cho tích hai norm — cosine thật, không phải dot-product giả định vector
đơn vị. Xem §2 "bẫy normalize".

⇒ **Việc còn lại với số provider KHÔNG phải là đo lại, mà là làm cho tái lập được** — commit
`compare_providers.py` + cache, đúng như `kb#38` đòi. Bốn provider local (8/1024) không dính vấn đề
nào ở trên.

## §5. PR-2 — re-pin dim + migration (chỉ chạy sau khi PR-1 có số)

**Điều kiện tiên quyết: `kb#39` phải merge trước.** `re_index` đọc `embed_text` đã lưu là thứ làm
migration dim tái lập được đúng chuỗi đã embed mà không cần dựng lại corpus. Trước khi có cột đó,
mọi lần đổi dim sẽ âm thầm đổi vector của mọi chunk.

- [ ] **Bỏ HNSW**: xoá `CREATE INDEX ... USING hnsw` (`schema.py:53-54`) + sửa dòng bảng
      `callisto-doc-schema.md:121`. Kèm docstring nêu **ngưỡng quy mô** làm quyết định này hết đúng
      (§2). Migration phải `DROP INDEX IF EXISTS` cho DB đã tồn tại, không chỉ ngừng tạo mới.
- [ ] `EMBEDDING_DIM = 8` → **2048**. Comment `schema.py:29-32` bảo re-pin **cùng lúc với
      `FakeEmbedding.dim`** — **kiểm lại: comment này đã cũ.** `FakeEmbedding` chỉ còn được dùng ở
      `get_embedding()` (dead) và 4 file test của apps/studio, nơi nó được truyền vào
      `EngineAgentRunner` mà `LlmStepExecutor` không bao giờ gọi. `test_embedding_fixture.py:11`
      còn nói rõ **cố ý không assert `FakeEmbedding.dim`**. ⇒ Nhiều khả năng đổi dim là
      **kb-local**. Xác nhận lại rồi sửa comment `schema.py` cho khớp thực tế.
- [ ] Migration cột: `DROP INDEX IF EXISTS kb_chunks_embedding_hnsw_idx` →
      `ALTER COLUMN embedding TYPE vector(2048)` → re-embed qua `re_index`. **Không dựng lại index.**
      Idempotent như `ALTER ... IF NOT EXISTS` của #39.
- [ ] Đo p95 `<=>` trên `vector(2048)` × 800 dòng SAU migration, ghi số vào §2 (gạch đầu tiên của
      "Đánh đổi đã nhận").
- [ ] **Fan-out của `derive_vector(text, dim=EMBEDDING_DIM)`** — đổi default là đổi hết những chỗ
      này, liệt kê sẵn để không phát hiện giữa chừng:
  - `apps/studio/providers/factory.py::CallistoEmbedding`
  - `packages/kb/scripts/ingest_callisto.py` (+ `ingest_callisto_v2.py`)
  - `scripts/e2e_smoke_eval.py::_CallistoEmbedding`
  - `packages/engine/scripts/measure_chunk_embed.py` (**chép công thức có chủ đích**, không import
    — sẽ KHÔNG tự đổi theo, phải sửa tay)
- [ ] **Regenerate `golden/embeddings-callisto-v0.json`** — fixture dim-8 recorded
      (`embeddings.py:78 FIXTURE_PATH`), có `test_embedding_fixture.py` soi. Re-pin dim làm nó vô
      hiệu ⇒ regenerate là **một phần của migration**, không phải việc dọn sau.
- [ ] Re-record `baseline-dim8.json` + xem lại `GATED_METRICS`: baseline đang neo vào dim-8. Đổi
      provider mặc định thì gate "tương đối so dim-8" còn nghĩa gì không — quyết định tường minh,
      đừng để trôi.
- [ ] `FakeEmbedding` ở dim cao thoái hoá: `fakes.py:114` là `digest[i % len(digest)]` trên
      blake2b 64 byte → từ ~768 chiều vector thành tuần hoàn, mọi chunk giống nhau. Nếu PR-2 đụng
      tới nó thì phải kèm công thức fixture mới, kẻo INV-4 (CI 100% fixtures) thành xanh-vô-nghĩa.

## §6. Thứ tự

```
kb#39 merge
   └─> PR-1  provider + cache + compare_providers + validation set   (dim KHÔNG đổi)
          └─> DEC chốt provider   (dim đã chốt sẵn ở §2 = 2048, không chờ)
                 └─> PR-2  bỏ HNSW + re-pin dim 8→2048 + migration + regenerate fixture
```

Tách 2 PR có chủ đích: chế độ hỏng độc lập nhau. Gộp một PR thì rollback mất cả hai.
