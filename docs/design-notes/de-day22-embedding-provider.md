# Note DE → AIE-1 + SWE: provider embedding thật đã chốt — chỗ hai lane phải nối vào

**Ngày:** 2026-08-19 (Day 22) · **Người viết:** DE (Nguyễn Đông Anh) · **Gửi:** AIE-1 (Trần Bá Đạt) ·
SWE (Dozyboy) · **Liên quan:** `kb#38` (bộ đo), `kb#40` (harness + cache), decision-log
[`decisions/decision-log-kb-search.md` §D22](../decisions/decision-log-kb-search.md), plan
[`plans/real_embedding_plan.md`](../../plans/real_embedding_plan.md).

## TL;DR

Provider embedding cho retrieval **đã chốt: `gemini-embedding-001`, gọi qua OpenRouter, 2048 chiều,
KHÔNG rerank** (DL-22.1). Kèm theo: **bỏ index HNSW** vì đó là thứ làm 2048 hợp lệ (DL-22.2).

Hệ quả: `EMBEDDING_DIM` đi từ **8 → 2048**, và đây **không phải thay đổi kb-local** — nó là **thay
đổi phối hợp 3 repo**. `.importlinter` cấm engine import kb, nên mọi hằng số dim ở engine/app là
**khai lại bằng tay** và **không có cơ chế nào so hai bên với nhau**. Note này liệt kê đúng những
dòng hai lane phải đổi, để không ai phải tự đi tìm.

## Vì sao là `gemini-embedding-001` (số, không phải khẩu vị)

Đo trên 300 case có nhãn (5 tầng S1–S5, corpus 2.0 800 chunk), qua đúng harness mà CI enforce.
Macro S1–S4 (weighted theo `n` mỗi tầng):

| metric | dim-8 | hash1024 | bge-m3 | e5-large | **gemini-001** |
|---|---:|---:|---:|---:|---:|
| Hit@1 | 0.0207 | 0.2822 | 0.4357 | 0.4440 | **0.5726** |
| Hit@3 | 0.0954 | 0.4191 | 0.6183 | 0.6432 | **0.7137** |
| MRR@5 | 0.0557 | 0.3501 | 0.5320 | 0.5494 | **0.6492** |
| Decoy Fall | 0.0435 | 0.1478 | 0.1652 | 0.1304 | **0.0783** |

Thắng mọi metric, qua **toàn bộ** gate per-tầng. `gemini-embedding-2` (đắt hơn 33%, không tốt hơn)
và `qwen3-embedding-8b` (rẻ 15× nhưng Hit@1 −5.4đ) đã đo và **không chọn** — lý do đầy đủ ở §D22.

> Điều đáng nhớ hơn cả lựa chọn: khoảng cách **dense ↔ lexical** là hàng chục điểm, khoảng cách
> **nội bộ nhóm dense chỉ vài điểm**. Đáp án đúng nằm trong top-50 ở **97.9%** số case trong khi
> Hit@5 thực tế mới **78.0%** ⇒ dư địa còn lại nằm ở **tầng xếp hạng/lọc**, không ở model.

## AIE-1 (engine) — 7 chỗ ghim số 8, phải đổi tay

`.importlinter:20` cấm `studio_engine → studio_kb`, nên không import chéo được. Grep `= 8` / `== 8`
trong `packages/engine` ra đúng các chỗ này:

| Chỗ | Việc |
|---|---|
| `tests/test_embedding_service_contract.py:29` | `EXPECTED_DIM = 8` → **2048** |
| `tests/test_embedding_service_contract.py:25-28` | **Comment đang nói sai**: nó hứa *"đổi một bên mà quên bên kia thì test đỏ ở đây"*. Test chạy trên `_conforming_impls()` (stub của chính engine), không phải vector từ kb ⇒ **không có cơ chế phát hiện nào**. Viết lại thành "nợ có ý thức, phải đổi tay cùng lúc". |
| `tests/fixtures/embedding/smoke-01.json` | Re-record vector **2048 chiều** (hiện ghi cứng 8). Không re-record thì `StubEmbedding` replay 8 chiều trong khi `EXPECTED_DIM` đã 2048 ⇒ đỏ. |
| `tests/test_stub_embedding.py:28` | `assert all(len(vector) == 8 …)` → **2048** |
| `tests/test_fixture_missing_fails_loud.py:264` | `assert all(len(vector) == 8 …)` → **2048** |
| `demo_stubs.py:172-176` | Docstring `StubEmbedding` *"width fixed at 8, matching kb::EMBEDDING_DIM"* → **2048** |
| `scripts/measure_chunk_embed.py` | **Chép công thức có chủ đích**, không import ⇒ sẽ KHÔNG tự đổi theo |
| `docs/contracts/embedding-service.v0.md` | Dòng 74 (`hiện \`8\``) · dòng 78-81 (khẳng định sai về cơ chế phát hiện) · bảng §3 dòng 98 (`E-2: ✅ (8)`) |

**Đã đo để khỏi tranh luận:** với kb ở 2048 trong cây làm việc,
`pytest packages/engine/tests/test_embedding_service_contract.py test_stub_embedding.py` cho
**12 passed**. Tức engine **xanh trong khi docstring của nó khẳng định điều sai** — đúng hình dạng
trôi âm thầm mà `EmbeddingService` contract nói là không thể xảy ra.

## SWE (apps/studio) — 2 chỗ, và một cái bẫy

1. `providers/fakes.py:107` — `FakeEmbedding.dim = 8` → **2048**.
2. `providers/fakes.py:114` — **công thức thoái hoá ở dim cao**: `digest[i % len(digest)]` trên
   digest 32 byte ⇒ từ chiều thứ 33 trở đi vector **tuần hoàn**, mọi chunk giống nhau ở đuôi. Bump
   con số mà không đổi công thức thì INV-4 (CI chạy 100% recorded fixtures) thành **xanh-vô-nghĩa**.
   Đổi `dim` phải kèm công thức fixture mới.

**Chỗ này chưa ai chạm và nó mới là đích cuối:** `providers/factory.py:24` (`CallistoEmbedding`) vẫn
`return derive_vector(text)` — tức đường chạy thật vẫn là bag-of-words, chỉ rộng ra 2048 chiều.
`GeminiEmbedding` hiện sống ở `kb/tests/embedding-tests/providers.py` (**test code**) vì
`.importlinter` cấm `studio_kb` chạm `studio_app` — nơi giữ settings/API key. Muốn provider thật lên
runtime thì class đó phải sống **bên apps/studio**, đọc key từ settings, và **không** thêm `embed()`
vào `GeminiProvider` (F3: `apps/studio/tests/test_providers.py:39` assert
`not hasattr(provider, "embed")` — phải là class riêng).

## Ba cạm bẫy đã đo, đừng đâm lại

1. **Migration gãy trên DB có dữ liệu.** `ALTER COLUMN embedding TYPE vector(2048)` chỉ lọt khi bảng
   **rỗng**; còn dòng dim cũ thì `ERROR: expected 2048 dimensions, not 8` (reproduce trên stack test
   5433). Phải `USING NULL` rồi `re_index`. Suite kb không lộ ra vì nó dọn sạch dòng trước khi chạy.
2. **Gate S5 mất nghĩa khi baseline re-record ở 2048.** `max_cosine_mean` phụ thuộc thang cosine của
   từng provider; `derive_vector(text, dim=EMBEDDING_DIM)` nghĩa là re-pin **đổi luôn provider
   baseline** sang bag-of-words 2048 chiều, kéo baseline S5 xuống ~0.296 ⇒ `gemini-001` (0.724) hoá
   **đỏ** dù chất lượng retrieval không đổi. Phải chuyển S5 sang ngưỡng tuyệt đối hoặc bỏ khỏi
   `GATED_METRICS` — quyết tường minh.
3. **Code CŨ chạy trên DB ĐÃ migrate cũng gãy — chiều ngược lại của bẫy #1.** DDL trước khi bỏ
   HNSW vẫn có `CREATE INDEX ... USING hnsw`; chạy nó trên DB đã ở `vector(2048)` thì pgvector từ
   chối vì **trần 2000 chiều**. Nghĩa là sau khi migrate, ai checkout nhánh cũ và chạy test có DB sẽ
   đỏ ở chỗ trông chẳng liên quan. Ai giữ một stack test dùng chung thì biết trước điều này.
4. **Không có răng cho contract kb↔engine.** Hai hằng số rời nhau + một docstring hứa suông. Đề xuất
   ở plan §5.4: một CI step ở kit grep cả hai giá trị và fail nếu lệch (rẻ), hoặc khai hằng số trong
   `studio_contracts` (triệt để, cần DEC vì đụng contracts). **Chưa làm — cần AIE-1 + SWE đồng ý.**

## Đường đo vẫn 100% offline (INV-4)

CI không bao giờ ra mạng: vector provider đọc từ `cache/` đã commit; đường ra mạng duy nhất là
`record_provider_cache.py` chạy tay. Bề mặt phủ = 800 `embedding_input` corpus 2.0 + 300 query
benchmark + **22 query golden-set 2.0** (thêm ở `kb#40` sau phản hồi AIE-2). **Cố ý không phủ**
golden 1.0 và grid `GQ-` — chúng chạy trên corpus 1.0 mà cache không giữ vector chunk 1.0 nào.
Thiếu cache thì `MissingVectorError` **nổ**, không rơi êm về `dim-8`.

## Thứ tự đề nghị

```
kb: re-pin dim + migration (USING NULL) + quyết gate S5
      ├─> engine: 7 chỗ ở bảng trên  (AIE-1)
      └─> apps/studio: FakeEmbedding.dim + công thức  (SWE)
             └─> (sau) provider thật lên runtime: class riêng bên apps/studio
```

Ba nhánh sau độc lập nhau; nhánh kb đi trước vì `kb.chunks.embedding` là chỗ số chiều thật sự cắn.
