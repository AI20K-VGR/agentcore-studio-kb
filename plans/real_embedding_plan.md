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

- [x] **Xác nhận seq scan chấp nhận được** — ĐO XONG 19/08: **p50 2.03ms · p95 4.24ms · max 8.07ms**
      (800 dòng `vector(2048)`, stack test 5433 sau khi `ALTER` sang 2048, `EXPLAIN` xác nhận Seq
      Scan, 60 truy vấn). Cả 800 dòng cùng một `section_role` ⇒ ca **xấu nhất về độ chọn lọc của
      filter**, tức chặn trên bảo thủ. Dưới xa mốc ~50ms ⇒ §2 không phải mở lại.
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

- [x] Class `GeminiEmbedding` riêng, chỉ cần `async embed(texts) -> list[list[float]]`.
      **Không phải method trên `GeminiProvider`** (§1.4).
- [x] Đặt tại `tests/embedding-tests/` — là test code nên không vi phạm `.importlinter`, và không
      kéo `google-genai` vào dependency của kb package.
- [x] `tests/embedding-tests/compare_providers.py` — script so provider, gọi qua đúng
      `conftest.py::embedding_provider` (đúng chữ trong `kb#38`), không viết bản "tương đương".
- [x] Cache theo `sha256(text)` **commit kèm** → chạy lại 0 API call, CI không bao giờ quay ra
      ngoài. Đây vừa là INV-4 vừa là gạch "tái lập được từ main" của `kb#38`.
- [x] **Bề mặt cache — nới sau phản hồi AIE-2 (`kb#40`)**: bản đầu chỉ phủ thứ `build_report` hỏi tới
      ⇒ 22/22 query golden-set 2.0 vắng mặt ⇒ mọi đường chấm golden 2.0 qua provider đã chốt nổ
      `MissingVectorError` (fail-closed đúng thiết kế, nhưng giới hạn không được viết ở đâu). Nay
      `record_provider_cache` tách `harness_texts()` + `golden_v2_texts()`; **cố ý không phủ** golden
      1.0 + grid `GQ-` (chạy trên corpus 1.0 mà cache không giữ vector chunk 1.0 nào).
- [x] Gọi qua `urllib` (không thêm dep). **Thiếu `STUDIO_GEMINI_API_KEY` ⇒ skip có lý do**, tuyệt đối
      không âm thầm rơi về dim-8 — đó là cách CI xanh trong khi đang đo nhầm provider.
- [x] Tách **validation set** khỏi 300 case báo cáo, TRƯỚC khi tune bất kỳ ngưỡng nào
      (`kb#38` gạch 3; hiện `cases/` vẫn chỉ có `s1..s5.json`).
- [x] **Giữ `output_dimensionality=2048`** (§2) → số provider API trong report **không phải đo
      lại**. Việc còn lại là làm chúng *tái lập được*, không phải làm lại chúng. Xem §4.
- [x] Cập nhật `embedding_report.md`: bổ sung **mục "cách chạy"** (report hiện không có) + ghi rõ
      2048 giờ là con số đã chốt, kèm lý do bỏ HNSW.
- [x] Viết **DEC chốt provider mặc định** — `docs/decisions/decision-log-kb-search.md` §D22
      (DL-22.1 provider · DL-22.2 bỏ HNSW · DL-22.3 ngưỡng quy mô · DL-22.4 CI offline + bề mặt
      cache), index nội bộ `docs/decisions/decision-log.md` đã trỏ tới. Theo §0 đây là việc kb tự
      làm được; **chờ AIE-1 ack**, không chặn.

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

## §5. PR-2 — re-pin dim + migration (thay đổi phối hợp 3 repo)

**Điều kiện tiên quyết: `kb#39` phải merge trước.** `re_index` đọc `embed_text` đã lưu là thứ làm
migration dim tái lập được đúng chuỗi đã embed mà không cần dựng lại corpus. Trước khi có cột đó,
mọi lần đổi dim sẽ âm thầm đổi vector của mọi chunk.

### §5.0 — Sai sót đã sửa: đổi dim KHÔNG phải kb-local

Bản trước viết: *"Nhiều khả năng đổi dim là kb-local"* — dựa trên việc quét `FakeEmbedding` chứ
**không quét số 8 ghim cứng ở engine**. Sai. Đổi `EMBEDDING_DIM` bên kb mà không sửa engine thì:

- `StubEmbedding` vẫn replay fixture `smoke-01.json` → vector 8 chiều → **xanh**
- `EXPECTED_DIM = 8` (`test_embedding_service_contract.py:29`) vẫn khớp stub → **xanh**
- Docstring `StubEmbedding` (`demo_stubs.py:172-176`) vẫn tuyên bố "width fixed at 8, matching
  `packages/kb/…::EMBEDDING_DIM`" → **tuyên bố thành sai mà không ai biết**
- Comment ở `EXPECTED_DIM` (dòng 27-28) viết: *"Đổi một bên mà quên bên kia thì
  `test_e2_…` đỏ ở đây"* → **điều đó không đúng.** Test chạy trên `_conforming_impls()` (stub
  của chính engine), không phải vector từ kb. `.importlinter` cấm engine import kb nên hằng số
  được khai lại bằng tay; **không có cơ chế nào so sánh hai bên với nhau.** Đây là nợ có ý thức,
  nhưng cơ chế phát hiện mà comment hứa thì **không tồn tại**.

PR-2 thực chất là **thay đổi phối hợp 3 repo**: kb (schema + fixture) · engine (stub + 3 test +
script, lane AIE-1) · apps/studio (`FakeEmbedding.dim`).

### §5.1 — kb (schema + fixture + migration)

- [ ] **Bỏ HNSW**: xoá `CREATE INDEX ... USING hnsw` (`schema.py:53-54`) + sửa dòng bảng
      `callisto-doc-schema.md:121`. Kèm docstring nêu **ngưỡng quy mô** làm quyết định này hết đúng
      (§2). Migration phải `DROP INDEX IF EXISTS` cho DB đã tồn tại, không chỉ ngừng tạo mới.
- [ ] `EMBEDDING_DIM = 8` → **2048**. Sửa comment `schema.py:29-32` — comment cũ bảo pin cùng
      `FakeEmbedding.dim` nhưng **không nhắc engine**, là thiếu. Comment mới phải liệt cả 3 nơi:
      `packages/engine/tests/test_embedding_service_contract.py::EXPECTED_DIM` ·
      `packages/engine/tests/fixtures/embedding/smoke-01.json` ·
      `apps/studio/src/studio_app/providers/fakes.py::FakeEmbedding.dim`.
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
- [ ] **Regenerate `golden/embeddings-callisto-v0.json`** — fixture dim-8 recorded
      (`embeddings.py:78 FIXTURE_PATH`), có `test_embedding_fixture.py` soi. Re-pin dim làm nó vô
      hiệu ⇒ regenerate là **một phần của migration**, không phải việc dọn sau.
- [ ] Re-record `baseline-dim8.json` + xem lại `GATED_METRICS`: baseline đang neo vào dim-8. Đổi
      provider mặc định thì gate "tương đối so dim-8" còn nghĩa gì không — quyết định tường minh,
      đừng để trôi.

### §5.2 — engine (stub + test + script + contract, lane AIE-1)

**`.importlinter` cấm engine import kb.** Mọi hằng số dim ở engine là khai lại bằng tay. Liệt kê
đầy đủ các chỗ phải sửa (grep `= 8` + `== 8` + `"EMBEDDING_DIM"` trong `packages/engine`):

- [ ] `EXPECTED_DIM = 8` → **2048** (`test_embedding_service_contract.py:29`). Sửa **comment dòng
      25-28**: bỏ khẳng định sai "đổi một bên mà quên bên kia thì test đỏ ở đây", viết lại cho
      đúng: *"Nợ có ý thức — không có cơ chế tự động so hai bên, phải đổi bằng tay cùng lúc với
      `packages/kb/…::EMBEDDING_DIM`."*
- [ ] Fixture `tests/fixtures/embedding/smoke-01.json` — re-record vector **2048 chiều** (hiện
      ghi cứng 8 chiều). Nếu không re-record thì `test_e2_…` đỏ vì `StubEmbedding` replay 8 chiều
      mà `EXPECTED_DIM` đã là 2048.
- [ ] `test_stub_embedding.py:28` — `assert all(len(vector) == 8 …)` → **2048**.
- [ ] `test_fixture_missing_fails_loud.py:264` — `assert all(len(vector) == 8 …)` → **2048**.
- [ ] `StubEmbedding` docstring (`demo_stubs.py:172-176`) — sửa "width fixed at 8" → **2048**.
- [ ] `scripts/measure_chunk_embed.py` — **chép công thức có chủ đích**, không import. Sẽ KHÔNG tự
      đổi theo, phải sửa tay.
- [ ] Contract `docs/contracts/embedding-service.v0.md` — sửa dòng 74 (`hiện \`8\``) và dòng
      78-81 (khẳng định sai về cơ chế phát hiện). Bảng §3 dòng 98 (`E-2: ✅ (8)`) → 2048.

### §5.3 — apps/studio (`FakeEmbedding`)

- [ ] `FakeEmbedding.dim = 8` → **2048** (`fakes.py:107`).
- [ ] `FakeEmbedding` ở dim cao **thoái hoá**: `fakes.py:114` là `digest[i % len(digest)]` trên
      sha256 32 byte → từ chiều thứ 33 trở đi vector tuần hoàn, mọi chunk giống nhau ở đuôi. Nếu
      PR-2 đụng tới nó thì phải kèm công thức fixture mới, kẻo INV-4 (CI 100% fixtures) thành
      xanh-vô-nghĩa.

### §5.4 — Làm cho contract kb↔engine có "răng thật"

Hiện tại contract chỉ là **hai hằng số rời nhau cộng một docstring hứa suông**. Không có gì
chạy ở CI so sánh `EMBEDDING_DIM` (kb) với `EXPECTED_DIM` (engine). Đề xuất:

- [ ] Thêm **CI step** ở kit (`agentcore-studio-kit`) grep cả hai giá trị và fail nếu lệch. Vì
      `.importlinter` cấm import chéo, đây là cách duy nhất có cơ chế phát hiện **tự động** thay vì
      dựa vào trí nhớ con người. Hình thức đơn giản nhất: script shell trong `.github/workflows/`
      parse cả hai file rồi `diff`.
- [ ] Hoặc: khai hằng số **trong `studio_contracts`** (layer cả engine lẫn kb đều được import) —
      cần DEC mới vì đụng tới `studio_contracts`. Giải triệt để nhưng chi phí cao hơn.

## §5b. Ngưỡng chuyển cache sang artifact store (ghi để nhớ, chưa chặn gì)

Mỗi lần re-record là một blob **8.9 MB mới nguyên** trong git history — nhị phân float32 gần như
không delta được, nên git không nén chồng lên bản cũ. Nếu HNSW quay lại và phải đo ở 1536 thì thêm
~6.7 MB nữa; thêm mỗi provider API là thêm một blob cùng cỡ.

Ngưỡng đề xuất để rời git: **khi tổng `cache/` vượt ~50 MB, hoặc khi có lần re-record thứ ba.** Lúc
đó chuyển sang artifact store (release asset / bucket) + commit **checksum** thay vì nội dung, và
đổi `test_cache_da_commit_CO_MAT_va_phu_du_moi_text_harness_can` thành kiểm checksum + hướng dẫn
tải. Hiện tại một blob 8.9 MB đổi lấy "tái lập được offline từ main" là đáng.

Không chặn PR nào — ghi ở đây để người sau không phải tự phát hiện khi repo đã nặng.

## §6. Thứ tự

```
kb#39 merge
   └─> PR-1  provider + cache + compare_providers + validation set   (dim KHÔNG đổi)
          └─> DEC chốt provider   (dim đã chốt sẵn ở §2 = 2048, không chờ)
                 └─> PR-2  bỏ HNSW + re-pin dim 8→2048 + migration + regenerate fixture
```

Tách 2 PR có chủ đích: chế độ hỏng độc lập nhau. Gộp một PR thì rollback mất cả hai.
