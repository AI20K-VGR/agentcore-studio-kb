---
id: studio.de.day-07-plan
type: day-plan
status: draft
author: DE — Nguyễn Đông Anh
date: 2026-07-28
sprint: s1
day: 7
week_calendar: 2
title: "Kế hoạch Ngày 7 (T3 28/07) — DE: fixtures embed/chunk cho Callisto + một nguồn sự thật duy nhất"
---

# KẾ HOẠCH NGÀY 7 — DE (KB pipeline + obs/eval data)
### Thứ Ba 28/07 · **Seam Protocol 2-impl, hôm nay chỉ bật stub** · luật ngày: **deterministic trước, thật sau**

> Nguồn chuẩn: `docs/requirements/week-1/days/day-07.md` · bút DE (`docs/contracts/kb-search.v0.md`) ·
> `plans/day06_plan.md` · `src/studio_kb/schema.py` (EMBEDDING_DIM) · `GITFLOWS.md` §4.
>
> `day-07.md:37` giao DE: *"Cấp **fixtures embed/chunk** cho stub (recorded vector Callisto); đảm bảo
> `kb.search` dùng **cùng** fixtures"*.
>
> `day-07.md:25` ghi luật vàng của ngày: *"**AC không phụ thuộc IQ của LLM** — chấm pipeline/trace,
> không chấm chất lượng câu trả lời"*. D6 đã học bài này bằng 4 case đỏ; D7 không lặp lại.

---

## 0. Ranh giới — 4/5 gạch đầu dòng DoD không phải của DE

| DoD `day-07.md` | Ai chịu | DE làm được gì |
|---|---|---|
| `:52` Đổi `StubEmbedding`→`GatewayEmbedding` không phải sửa interpreter | **AIE-1** (bút Protocol, R-SPEC A1#5) | Không. DE chỉ cấp **dữ liệu** cho stub, không cầm bút Protocol |
| `:53` CI không gọi network/model thật | **chung** | ✅ Phần DE: fixture là **file đã ghi sẵn**, không tính toán lúc chạy, không đọc mạng |
| `:54` Interpreter đọc `agent_config` đủ 3 field | **AIE-1** (đọc) + **SWE** (form → recipe) | Không. `packages/engine` + `packages/workbench` đều ngoài quyền ghi của DE |
| `:55` smoke-eval chạy lại ra **cùng** bảng điểm | **AIE-2** | ⚠️ Một nửa: fixture của DE làm **truy xuất** deterministic. Bảng điểm còn phụ thuộc `_NaiveExtractiveLLM` đứng yên — file đó ở `scripts/`, không phải của DE |
| `:56` Daily-note D7 | **DE** | ✅ |

**Kho ghi được: chỉ `packages/kb/**` + `docs/reports/**`.**

Deliverable thật của DE hôm nay gói gọn trong một câu: **một file vector đã ghi sẵn cho 25 chunk
Callisto, và không chỗ nào khác trong workspace tự tính vector riêng.**

### 0.1 Hai quyết định chốt trước, để plan không trôi

**① "`kb.search` dùng cùng fixtures" = CHUNG MỘT FILE ÁNH XẠ `chunk_id → vector`, KHÔNG phải đổi
`kb.search` sang xếp hạng cosine.**

Đây là chỗ duy nhất trong bảng giao việc đọc được hai kiểu, nên chốt ngay:

- **Nghĩa hẹp (chọn):** một file fixture là nguồn duy nhất cho vector của 25 chunk. `StubEmbedding`
  (AIE-1) và `kb.search` (DE) nhìn cùng file đó, đồng ý với nhau **vector nào thuộc `chunk_id` nào**.
- **Nghĩa rộng (loại):** `StaticKbSearch` bỏ trùng-token, chuyển sang cosine trên vector.

Loại nghĩa rộng vì chính bảng nâng cấp trong `static_search.py` (bút DE, D4) đã xếp *"xếp hạng:
cosine trên vector"* vào cột **S2–S3**, cùng ô với `KbSearchService` + pgvector. Kéo cosine vào D7 là
plan tự nói ngược tài liệu của chính mình — và nó kéo theo cả chuỗi `db_plan.md` y như §0.1① của D6
đã từ chối kéo `PgKbSearch` vào D6.

**Phép thử phân biệt hai nghĩa** (dùng để nghiệm thu, không phải để tranh luận): file fixture có làm
`StubEmbedding` và `kb.search` thống nhất **vector nào ứng với `chunk_id` nào** không? Có → đạt
"cùng fixtures". Chỉ thống nhất **số chiều** thôi → chưa đạt.

**② Vector phải được GHI RA FILE, không phải tính lúc import — và công thức là bag-of-words.**

`day-07.md:37` viết "**recorded** vector Callisto". `FakeEmbedding._vector`
(`apps/studio/.../fakes.py:38`) tính ngay lúc gọi — nếu fixture của DE cũng làm vậy thì nó không
phải fixture đã ghi, và chữ "recorded" thành nhãn sai. Đúng bài học tự rút cuối daily-note D6:
*"một dòng ghi trong tài liệu không phải bằng chứng"*.

Nên: **file JSON check-in** + **script sinh ra nó** + **test canh file vẫn khớp corpus**, kèm đường
re-record khi gateway thật về.

**Công thức lấy từ `BagOfWordsEmbedding`, KHÔNG chép sha256 của `FakeEmbedding`.** Bản đầu của plan
này chọn sha256 với lý do "cả workspace ra cùng số" — sai, và đo được là sai:

    sha256         cosine cùng doc 0.754 · khác doc 0.752 → chênh +0.002   (nhiễu)
    bag-of-words   cosine cùng doc 0.885 · khác doc 0.867 → chênh +0.018

`kb.chunks.embedding` có index HNSW `vector_cosine_ops` và `kb.search` bản S2–S3 xếp hạng bằng
cosine. Vector không có cấu trúc cosine nạp vào index cosine thì mọi phép kiểm ranking sau này vẫn
"chạy" mà không chứng minh gì. `BagOfWordsEmbedding` (`tests/test_pg_kb.py`, D4) là bản kb **đã tự
chọn** cho chính test ingest pgvector của mình, và docstring nó ghi rõ không lấy `FakeEmbedding` làm
chuẩn vì `.importlinter` cấm `studio_kb` chạm `studio_app` — tức kb quyết chuyện này một lần rồi.

Từ D7 công thức sống ở `src/studio_kb/embeddings.py`, `test_pg_kb.py` import lại — một nguồn, không
hai bản. Hệ quả: fixture **không còn khớp** `FakeEmbedding`; ràng buộc còn lại giữa hai bên chỉ là
**số chiều**, và đó là Q-B.

---

## 1. Trạng thái trước D7 — schema đã sẵn, không ai sinh nổi một vector Callisto

Kiểm bằng đọc code, không phải tự khai:

| Mảnh | Ở đâu | Trạng thái |
|---|---|---|
| `EMBEDDING_DIM = 8` | `schema.py:33` | ✅ đã ghim |
| `kb.chunks.embedding vector(8)` + index HNSW `vector_cosine_ops` | `schema.py:43,47` | ✅ DDL sẵn |
| `KbPipeline.embed_invoke` / `index` / `chunker` | `pipeline.py:26,31,21` | ❌ `NotImplementedError` cả ba |
| `StaticKbSearch` xếp hạng | `static_search.py` | trùng token thô — **không đụng vector** |
| `FakeEmbedding` (sha256, `dim=8`) | `apps/studio/.../fakes.py:29` | có, nhưng docstring ghi rõ *"CI fixture — KHÔNG phải deliverable AIE-1"*; và `apps/studio` DE chỉ READ |
| `EmptyEmbedding` | `engine/demo_stubs.py` | trả `[]` |
| `_UnusedEmbedding` | `scripts/smoke_eval_d6.py` | trả `[]` |

→ Cột `vector(8)` tồn tại, ba đường sinh vector tồn tại, **nhưng không đường nào sinh ra vector cho
một chunk Callisto cụ thể.** Đó đúng là lỗ D7 giao cho DE.

### 1.1 Ràng buộc chặn thiết kế: engine KHÔNG import được `studio_kb`

`.importlinter:20` xếp `studio_kb | studio_engine | studio_workbench | studio_evalhub` **cùng một
tầng** — anh em, cấm import chéo. `StubEmbedding` là file của AIE-1 trong `packages/engine`, nên nó
**không thể** `from studio_kb... import` fixture của DE.

Đây y hệt tình huống `KbSearch` ở D4: lời giải khi đó là **Protocol + tiêm vào từ ngoài**, không phải
import. Nhưng vector là **dữ liệu**, không phải hành vi, nên có thêm hai đường và cả hai đều có giá:
đọc file theo đường dẫn chéo package (phụ thuộc layout, import-linter không bắt nhưng vẫn là coupling
ngầm), hoặc chép file sang `packages/engine` (**hai nguồn sự thật** — đúng vết `smoke-5.yaml` ↔
`cli._demo_golden_set` đã ghi ở điểm gãy #8). Xem **Q-A**.

### 1.2 Nợ mang từ D6 sang, phải xử trước khi nói tới `:55`

Refactor workbench `2cea2db` (28/07) xoá `builder_d3/d4/d6.py`, gộp vào `builder.py`. Hệ quả **đã đo**:

```
scripts/smoke_eval_d6.py:69   ModuleNotFoundError: studio_workbench.builder_d6
packages/kb/tests/test_spine_live.py:40  ModuleNotFoundError: studio_workbench.builder_d4
```

→ **smoke-eval hôm nay không chạy được một dòng nào.** DoD `:55` đòi "chạy lại ra cùng bảng điểm" mà
hiện tại còn chưa chạy lại được lần đầu. Đây là việc đầu tiên trong ngày, xem D7-0.

---

## 2. Deliverable

### D7-0 · Sửa 2 import gãy — **chặn DoD `:55`**

`create_recipe_d4`/`create_recipe_d6` vẫn còn, chỉ dời sang `studio_workbench.builder` và được
re-export ở `studio_workbench/__init__.py`. Sửa mỗi file một dòng, dùng đường re-export (bền hơn
đường module, vì SWE vừa chứng minh họ sẽ còn dời file):

```python
from studio_workbench import create_recipe_d6   # scripts/smoke_eval_d6.py
from studio_workbench import create_recipe_d4   # packages/kb/tests/test_spine_live.py
```

**Xong là:** `uv run python scripts/smoke_eval_d6.py` in lại bảng 10 case. Ghi lại bảng đó làm mốc —
`:55` chấm bằng cách so hai lần chạy, không có mốc thì không có gì để so.

---

### D7-1 · Fixture vector Callisto — **deliverable chính**

**File:** `packages/kb/golden/embeddings-callisto-v0.json`

```json
{
  "fixture_ref": "callisto-embeddings-v0",
  "dim": 8,
  "derivation": "sha256(text)[i % 32] / 255.0 — tổng hợp deterministic, KHÔNG phải output model",
  "corpus_ref": "docs/callisto/ — 5 doc × 5 chunk",
  "vectors": { "ankor-leave-001#c1": [0.42, ...], "...": [] }
}
```

Bốn ràng buộc, mỗi cái có lý do riêng:

1. **Khoá là `chunk_id`, không phải text.** Đây chính là thứ phép thử §0.1① đòi: hai bên phải đồng ý
   vector nào thuộc chunk nào. Khoá theo text thì `StubEmbedding` nhận `texts: list[str]` vẫn tra
   được, nhưng `kb.search` không kiểm chéo được với `chunk_id` nó trả về.
2. **`dim` ghi trong file, không suy từ độ dài mảng.** Lệch số chiều phải đỏ ở một dòng assert, không
   phải vỡ sâu trong pgvector.
3. **Ghi rõ `derivation` là tổng hợp.** Ai đọc file cũng phải biết ngay đây không phải vector model
   thật, khỏi ai đó dựng kết luận về chất lượng retrieval trên nó.
4. **Đủ 25 chunk, không phải chỉ chunk mà smoke-case chạm tới.** Fixture thiếu chunk thì ngày mai
   thêm một golden case là fixture đỏ vì lý do không liên quan.

**Script sinh:** `packages/kb/scripts/record_embeddings.py` — đọc `load_callisto()`, sinh vector,
ghi file. Chạy lại phải ra **byte-identical**; đó là điều kiện để `:53` (CI không gọi model) có nghĩa.

---

### D7-2 · Test canh trôi — **thứ giữ "cùng fixtures" không thành khẩu hiệu**

Ba nguồn có thể sinh vector: fixture của DE · `FakeEmbedding` (studio) · `StubEmbedding` (AIE-1).
Comment ở `schema.py:29-32` đã dặn phải re-pin `EMBEDDING_DIM` và `FakeEmbedding.dim` **cùng lúc** —
tức rủi ro trôi đã được nhận diện từ trước, chỉ chưa có test nào canh.

`packages/kb/tests/test_embedding_fixture.py` — 4 assert, mỗi cái bắt một kiểu trôi:

| # | Assert | Bắt được gì |
|---|---|---|
| 1 | key của fixture == đúng tập `chunk_id` của `load_callisto()` | corpus thêm/bớt/đổi tên chunk mà quên re-record |
| 2 | mọi vector dài đúng `schema.EMBEDDING_DIM` | ai đó đổi `EMBEDDING_DIM` mà quên file |
| 3 | `fixture["dim"] == schema.EMBEDDING_DIM` | file tự mâu thuẫn |
| 4 | chạy lại script sinh ra **đúng** nội dung file đang có | fixture bị sửa tay, hoặc công thức đổi mà file không đổi |

Assert #4 là cái đắt nhất và cũng là cái duy nhất chứng minh chữ "recorded": nó so **file đã ghi** với
**thứ script sinh ra bây giờ**, thay vì tin rằng hai thứ đó bằng nhau.

Không assert `FakeEmbedding.dim` ở đây — `apps/studio` ngoài tầng, và kb test import `studio_app` sẽ
làm đỏ `lint-imports`. Chỗ đó là **Q-B**.

---

### D7-3 · Đường cho `kb.search` dùng fixture

Theo §0.1①, D7 **không** đổi cách xếp hạng. Việc thật là mở một đường đọc để `StaticKbSearch` (và
`KbSearchService` sau này) lấy vector từ **đúng file đó**, không tự tính:

`load_callisto_embeddings() -> dict[str, list[float]]` trong `studio_kb`, đọc file, cache. `KbSearch`
chưa gọi nó ở D7 — nhưng nó là điểm nối để `db_plan.md` (ingest → `kb.chunks.embedding`) và bản cosine
S2–S3 cắm vào mà không phải quyết lại nguồn vector.

Ghi thẳng trong docstring: **hàm này là nguồn duy nhất**; ai cần vector Callisto thì gọi nó, cấm
sha256 tại chỗ.

---

## 3. Thứ tự (timebox)

| Slot | Việc | TT |
|---|---|---|
| **Đầu giờ** | Nhắn **Q-A** (AIE-1: `StubEmbedding` lấy fixture qua đường nào) — chặn thiết kế D7-1 | ⬜ |
| **Đầu giờ** | Nhắn **Q-C** (AIE-2: mốc bảng điểm lấy từ đâu khi smoke-eval đang gãy) | ⬜ |
| Sáng 1 | **D7-0** sửa 2 import, chạy smoke-eval, **ghi lại bảng điểm làm mốc** | ⬜ |
| Sáng 2 | **D7-1** script record + sinh file 25 chunk | ⬜ |
| Sáng 3 | **D7-2** 4 test canh trôi | ⬜ |
| Chiều 1 | Trực để AIE-1 cắm `StubEmbedding` vào fixture — **để trống có chủ ý** | ⬜ |
| Chiều 2 | **D7-3** `load_callisto_embeddings()` + docstring nguồn-duy-nhất | ⬜ |
| Cuối ngày | Chạy smoke-eval **lần hai**, so với mốc sáng · daily-note D7 · PR | ⬜ |

> Chiều 1 để trống theo đúng bài học D6: ngày có seam mới cắm thì người giữ dữ liệu phải rảnh đúng
> lúc người cắm cần, không phải đang bận deliverable của mình.

---

## 4. Câu hỏi phải hỏi TRƯỚC khi code

| # | hỏi ai | nội dung | nghiêng về |
|---|---|---|---|
| **Q-A** *(chặn D7-1)* | **AIE-1** | `.importlinter:20` cấm `studio_engine` import `studio_kb`, nên `StubEmbedding` không import được fixture của DE. Ba đường: (a) đọc file theo đường dẫn chéo package, (b) chép file sang `packages/engine`, (c) composition root nạp rồi tiêm vào. Chọn đường nào? | **(c)**, cùng khuôn `KbSearch` đã dùng từ D4 — dữ liệu đi qua chỗ tiêm, không qua import. (b) đẻ nguồn sự thật thứ hai, đúng vết điểm gãy #8. Nếu composition root vẫn chưa tồn tại (Q-A của D6 **vẫn chưa có trả lời**) thì lui về (a) và **ghi rõ là nợ**, đừng lặng lẽ chọn (b) |
| **Q-B** | **mentor** | Ai canh `FakeEmbedding.dim` (`apps/studio`) khớp `EMBEDDING_DIM` (`packages/kb`)? Comment `schema.py:29-32` bảo re-pin cùng lúc nhưng không test nào canh, và DE không ghi được `apps/studio`, cũng không import được nó từ kb test | test đặt ở `apps/studio/tests` (vùng mentor) hoặc `tests/` repo cha — chỗ duy nhất nhìn được cả hai |
| **Q-C** *(chặn DoD `:55`)* | **AIE-2** | `:55` đòi "chạy lại ra **cùng** bảng điểm", nhưng smoke-eval đang `ModuleNotFoundError` sau refactor workbench `2cea2db`. Mốc để so lấy từ đâu — bảng 6/10 ghi trong daily-note D6, hay chạy lại sau khi sửa import rồi lấy làm mốc mới? | chạy lại sau D7-0 rồi lấy làm mốc mới. Bảng D6 sinh ra ở con trỏ submodule khác, so với nó là so hai thứ khác nhau |
| **Q-D** | **SWE** | Refactor `2cea2db` xoá `builder_d3/d4/d6.py` không báo trước, làm gãy 2 file ngoài workbench. Lần sau đổi API công khai có báo trước không, hay bên dùng tự dò? | báo trước ở kênh chung; hoặc giữ module cũ re-export một sprint |

---

## 5. Tự kiểm trước khi push

- [ ] Nhánh tách từ kb `main`, **không** commit thẳng `main` (guard chặn).
- [ ] `packages/kb/golden/embeddings-callisto-v0.json` có **đủ 25** khoá, mỗi vector **đúng 8** số.
- [ ] Chạy lại `record_embeddings.py` → file **không đổi một byte** (`git diff` rỗng).
- [ ] 4 test `test_embedding_fixture.py` xanh, **0 skip**.
- [ ] `search.py` + `pipeline.py` vẫn nguyên `NotImplementedError`; `test_search_contract.py` xanh.
- [ ] `StaticKbSearch` **không đổi cách xếp hạng** (§0.1① — cosine là S2–S3).
- [ ] `apps/studio/**` và `packages/engine/**` không đổi một dòng.
- [ ] `lint-imports` xanh — `studio_kb` không import `studio_app`/`studio_engine`.
- [ ] smoke-eval chạy **hai lần** ra **cùng** bảng; dán cả hai vào daily-note.
- [ ] Daily-note D7, có mục "điểm gãy còn lại".

---

## 6. Ngoài phạm vi

`kb.search` xếp hạng cosine (§0.1①, để S2–S3 + `db_plan.md`) · điền thân `KbPipeline.embed_invoke`/
`index` (ingest thật vào `kb.chunks`) · nối `KbSearchService` + gỡ `xfail` `test_leak.py` · gateway
embedding thật (`day-07.md:45` — Phase-2, sau flag) · `StubEmbedding` và Protocol (**bút AIE-1**) ·
`agent_config` 3 field (**AIE-1 + SWE**) · sửa 7 lỗi ruff `packages/workbench` (**SWE**).

---

*Plan D7 — DE, 28/07/2026. Q-A chặn thiết kế D7-1 và phải hỏi trước khi viết dòng code đầu tiên:
chọn sai đường cấp fixture thì hôm sau phải gỡ, và đường sai rẻ nhất (chép file) lại chính là đường
đẻ ra nguồn sự thật thứ hai.*
