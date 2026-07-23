---
id: studio.de.day-04-plan
type: day-plan
status: draft
author: DE — Nguyễn Đông Anh
date: 2026-07-23
sprint: s1
day: 4
week_calendar: 1
title: "Kế hoạch Ngày 4 (T5 23/07) — DE: doc-factory chunk hoá + kb.search thô + golden 5 case nhãn tay"
---

# KẾ HOẠCH NGÀY 4 — DE (KB pipeline + obs/eval data)
### Thứ Năm 23/07 · Sprint 1 · macro-goal **G2** · luật ngày: **xâu kim trước, siết sau**

> Đây là **plan thi công**, chưa phải sản phẩm.
> Nguồn chuẩn: `docs/requirements/week-1/days/day-04.md` · bút DE ngày 2–3
> (`docs/contracts/kb-search.v0.md` v0.1, `docs/callisto-doc-schema.md`, `docs/format.md`) ·
> `GITFLOWS.md` §4.

---

## 0. Ranh giới hôm nay (đọc trước khi mở editor)

Brief giao DE **1 script, 2 deliverable** (`day-04.md:37`):

| Việc | Trong scope DE? | Ghi chú |
|---|---|---|
| **doc-factory** chunk hoá 5 doc (frontmatter `tenant`/`section`) | ✅ | Nội dung doc **đã xong D3** — hôm nay là *máy cắt*, không phải viết nội dung |
| **`kb.search` thô** — cited chunks, filter tenant naive | ✅ | **CHƯA fence** (`day-04.md:22`) — xem D4-2, và xem cảnh báo "đừng đụng `KbSearchService`" |
| **golden 5 case** sinh từ doc-factory + **nhãn tay** | ✅ | `packages/kb/golden/smoke-5.yaml` — `format.md` §1 |
| Daily-note D4 | ✅ | `docs/reports/daily-notes/2026-07-23-DongAnh2704.md` |
| smoke-eval runner / bảng điểm / `compute_scorecard` | ❌ | AIE-2 giữ bút (`day-04.md:38`) |
| `kb-retrieve` nối thật · `llm-step` trích `chunk_id` | ❌ | AIE-1 giữ bút (`day-04.md:39`) |
| `recipe.kb_binding.{kb_id,scope}` | ❌ | SWE giữ bút (`day-04.md:40`) |
| Loader YAML → `GoldenSet` | ❌ *(nhưng chưa ai làm — xem Q-A)* | `format.md` §10: "DE sinh + gán nhãn · **AIE-2 chỉ đọc**" |
| Permission fence chunk-level · leak-test T1/T6 | ❌ | **Sprint 3** — `day-04.md:46` cấm làm sớm |
| Điền thân `KbSearchService.search` | ❌ | Xem D4-2b — làm là **đỏ CI**, và sai contract |

**Kho ghi được hôm nay: chỉ `packages/kb/**` + `docs/reports/**`.** `agentcore-studio-kit` = READ.

> ⚠️ Khác D3: hôm nay DE **có DoD sản phẩm thật**. `day-04.md:53` — *"`kb.search` trả `chunk_id`
> (citation chấm được)"* và `:54` — *"5 case có nhãn tay"* đều là của DE. Nhưng DoD `:55`
> (*"bảng điểm 5 dòng in ra CLI"*) là của AIE-2 và **nó chỉ chạy được nếu cả chuỗi thông**:
> YAML của tôi → loader → interpreter (AIE-1 tiêm search của tôi) → `score_case` → in bảng.
> Tôi nắm 2 mắt xích (search + YAML); 3 mắt xích còn lại là của người khác và **2 trong số đó
> hiện đang hỏng/thiếu** — xem §7. Báo sớm, đừng đợi 4h chiều.

---

## 1. Deliverable hôm nay (5 mục)

### D4-1 · doc-factory: máy cắt chunk từ 5 doc — **làm đầu tiên, mọi thứ khác phụ thuộc**

**Nội dung doc đã có sẵn từ D3** (`docs/callisto/`, 5 doc × 5 chunk = 25 chunk). Brief nói
*"doc-factory KB stub 5 doc"* — phần còn thiếu là **hàm biến file `.md` thành chunk có `chunk_id`**,
không phải viết thêm doc.

**"1 script, 2 deliverable"** (`day-04.md:37`) đọc như sau: cùng một máy cắt sinh ra **cả** dữ liệu
KB (để `kb.search` trả về) **lẫn** khung golden-case (để tôi gán nhãn tay). Nếu tách hai máy, hai
bên sẽ lệch `chunk_id` — và `format.md` §2 đã cảnh báo: *"lệch định dạng thì mọi case ra 0 mà không
có lỗi nào nổi lên"*.

Đặt ở `src/studio_kb/doc_factory.py`. Ba luật phải bám, đều đã chốt ở D2, **không chọn lại**:

| Luật | Neo | Cụ thể |
|---|---|---|
| cắt theo heading `##` | `callisto-doc-schema.md` §5 | 1 chunk = 1 heading `##` + thân bên dưới |
| `chunk_id = {doc_id}#c{n}`, n từ 1, **đếm theo doc** | §6 | không UUID — golden-set chết nếu id không tái tạo được |
| **1 chunk = đúng 1 `section_role`** | §5 | mặc định = `section` ở front-matter; **override tại chỗ** khi heading có `{section: X}` |

Ca kiểm chứng luật override là `ankor-expense-001`: front-matter `section: public`, nhưng heading
`## Hạn mức phê duyệt   {section: finance}` → **`#c2` phải ra `finance`**, 4 chunk còn lại `public`.
Đây là doc nhiều section **duy nhất** trong bộ — nó hỏng thì luật §5 không có gì kiểm.

**Bảng chunk_id kỳ vọng** (tôi đã đối chiếu tay với file thật, dùng làm oracle cho test):

| doc | c1 | c2 | c3 | c4 | c5 |
|---|---|---|---|---|---|
| `ankor-leave-001` (public) | Thời hạn báo trước | Cách nộp đơn | Nghỉ đột xuất | Ngày phép năm | Liên hệ hỗ trợ |
| `ankor-expense-001` (public) | Nguyên tắc chung | **Hạn mức phê duyệt → `finance`** | Hồ sơ cần nộp | Thời gian hoàn ứng | Liên hệ hỗ trợ |
| `ankor-salary-001` (hr) | Cấu trúc thang lương | Xét tăng bậc | Phụ cấp | Kỳ trả lương | Bảo mật thông tin lương |
| `borea-leave-001` (public) | Thời hạn báo trước | Quy trình duyệt hai cấp | Nghỉ đột xuất | Ngày phép năm | Nghỉ không lương |
| `borea-expense-001` (finance) | Hạn mức phê duyệt | Quy trình đề nghị | Chứng từ | Hoàn ứng | Kiểm soát nội bộ |

> ⚠️ **KHÔNG đụng `src/studio_kb/pipeline.py`.** `KbPipeline.chunker/embed_invoke/index` đều raise
> `NotImplementedError` **có chủ đích** (spec DE, gắn với Postgres + pgvector). doc-factory hôm nay
> là **máy cắt tĩnh đọc file**, không phải `KbPipeline.chunker` chạy thật. Hai thứ khác tầng: cái
> này ăn `.md` trên đĩa, cái kia ăn document đã vào DB. Nhập chúng lại = tự đặt bom cho S2.

**Xong là:** gọi factory ra đúng 25 chunk, `ankor-expense-001#c2` mang `section_role='finance'`,
và mọi `chunk_id` khớp bảng trên.

---

### D4-2 · `kb.search` thô — **class MỚI, không phải điền `KbSearchService`**

#### a) Vì sao là class mới (đây là quyết định kỹ thuật quan trọng nhất của ngày)

Cám dỗ hiển nhiên: `KbSearchService.search` đang `raise NotImplementedError`, brief bảo "làm
`kb.search` thô" → điền vào đó. **Sai, vì ba lý do độc lập, mỗi lý do đủ để chặn:**

1. **Sai contract.** Docstring của `search.py:1-17` ràng buộc bản thật phải: filter **fail-closed**
   tại truy xuất, `section_roles` phân giải **server-side**, chạy qua `get_pool()` để RLS có hiệu
   lực. Brief hôm nay nói ngược lại: *"**CHƯA fence** — filter tenant **naive** để xâu kim"*
   (`day-04.md:22`), fence để **Sprint 3** (`:46`). Nhét hành vi naive vào cái seam đã ghi rõ là
   fenced = nói dối bằng code.
2. **Đỏ CI ngay.** `tests/test_search_contract.py` là một test **XANH** khẳng định method đó raise.
   Điền thân → test đỏ. Đúng cái bẫy `day03_plan.md:94` đã cảnh báo.
3. **Không có gì để tìm.** `KbSearchService` nhận `pool` Postgres và tìm trên bảng `kb.chunks` —
   bảng đó **rỗng**, vì `KbPipeline.index` chưa chạy được (D4-1). Điền thân xong nó vẫn trả `[]`.

→ **Chốt: viết `StaticKbSearch` mới ở `src/studio_kb/static_search.py`.**

Cái mở khoá là **`KbRetrieveExecutor.__init__(self, kb_search: KbSearch)`**
(`packages/engine/src/studio_engine/executors.py:50`) — AIE-1 nhận qua **Protocol, tiêm vào**, không
nhận class cụ thể. Nên một class tĩnh thoả `KbSearch` **chính là** "kb.search thật" theo nghĩa AIE-1
cần: đủ để bỏ `EmptyKbSearch`, đủ để `llm-step` có `chunk_id` mà trích. Không vector, không DB.

`KbSearchService` giữ nguyên `NotImplementedError`, `test_search_contract.py` giữ nguyên xanh. Bản
Postgres fenced vẫn là deliverable của tôi ở S2–S3 — hôm nay không tiêu nó.

#### b) Hành vi v0 (thô — cố ý)

Chữ ký **bắt buộc y hệt** Protocol 4 tham số đã chốt D3 (`kb-search.v0.md` v0.1 §1):

```python
async def search(
    self, query: str, tenant: str, section_roles: list[str], top_k: int
) -> list[KbSearchResultItem]: ...
```

| Khía cạnh | v0 hôm nay | Về sau |
|---|---|---|
| nguồn | 25 chunk tĩnh từ D4-1, nạp sẵn trong bộ nhớ | `kb.chunks` + pgvector (S2) |
| filter `tenant` | so chuỗi thẳng, **naive** | RLS + `WHERE` tại truy xuất (S3) |
| filter `section_roles` | so `section_role ∈ section_roles` | phân giải **server-side** (S3, chặn T6) |
| xếp hạng `score` | trùng token thô (không embedding) | cosine trên vector |
| trả rỗng | `[]` là **hợp lệ**, không raise | giữ nguyên — đây đã là hình dạng fail-closed |

> Dù "chưa fence", vẫn lọc `section_roles` ở v0. Không phải làm sớm: **SC-05 (chéo vai) không có
> nghĩa gì nếu không lọc vai** — case sẽ xanh vì lý do sai. Cái để S3 là *phân giải server-side* và
> *fail-closed*, không phải bản thân mệnh đề lọc.

**Xong là:** `search("báo trước", "ankor", ["public"], 5)` trả item có
`chunk_id="ankor-leave-001#c1"`; đổi `tenant="borea"` trả `borea-leave-001#c1` với **nội dung khác
hẳn** (3 ngày vs 7 ngày) — đây là phép thử fence rẻ nhất (`callisto-doc-schema.md:276`).

---

### D4-3 · `golden/smoke-5.yaml` — 5 case nhãn tay — ✅ **XONG (23/07)**

> **TT:** file đã tạo, 5 case × 7 field, nạp được vào `GoldenSet` của AIE-2. Một điều chỉnh so với
> thiết kế §8: `expected` của 3 case dương viết **dạng ngắn** (`"3 ngày làm việc"`) vì `harness.py:69`
> so khớp **tuyệt đối** và `scorecard-v0.md:166` chốt bộ này ở nấc exact-match. Sửa bên mình rẻ hơn
> bắt AIE-2 đổi luật chấm — nên **Q-F (dự định hỏi về exact-match) đã tự đóng, không cần hỏi.**

Đường dẫn theo **bút của chính tôi** `format.md` §1: `packages/kb/golden/smoke-5.yaml`.
*(Brief `day-04.md:32` viết `golden/smoke_5.yaml` — gạch dưới. Giữ `smoke-5.yaml` cho khớp file
spec đã phát cho AIE-2 từ D2; ghi chú lệch tên vào daily-note.)*

Bộ 5 case đã phác ở `format.md` §8 và **nội dung 5 doc D3 đã viết bám đúng các con số đó**, nên hôm
nay là **xác nhận + gán nhãn**, không phải nghĩ lại đề. Tôi đã đối chiếu từng nhãn với file thật:

| case | loại | tenant / roles | chunk thật | nhãn `expected` |
|---|---|---|---|---|
| **SC-01** | ✅ dương | ankor / `[public]` | `ankor-leave-001#c1` — "tối thiểu **3 ngày** làm việc" | ✔ khớp |
| **SC-02** | ✅ dương, **cặp với SC-01** | borea / `[public]` | `borea-leave-001#c1` — "tối thiểu **7 ngày** làm việc" | ✔ khớp |
| **SC-03** | ✅ dương, đúng vai | ankor / `[finance]` | `ankor-expense-001#c2` — "**20 triệu** đồng" | ✔ khớp (chunk override) |
| **SC-04** | ❌ âm — **chéo tenant** (mầm T1) | ankor / `[public]` | mồi: `borea-expense-001#c1` = **77 triệu** | `refusal`, citation `[]` |
| **SC-05** | ❌ âm — **chéo vai** (mầm T6) | ankor / `[engineering]` | mồi: `ankor-salary-001#c1` = 6 bậc B1–B6 (`hr`) | `refusal`, citation `[]` |

Luật gán nhãn (`format.md` §10): **nhãn viết tay, không nhờ model**. Dùng model sinh `expected` rồi
lại dùng model chấm là để model tự chấm mình — phép đo mất sạch ý nghĩa.

Mọi field bắt buộc, rỗng viết `[]`, **không bỏ khuyết** (`format.md` §2) — bỏ khuyết là mập mờ giữa
*cố ý rỗng* và *quên điền*.

> ⚠️ **SC-05 sẽ bị AIE-2 chấm SAI như hiện trạng code.** Không phải lỗi nhãn của tôi — xem D4-4 và
> Q-B. Vẫn viết SC-05 đúng theo spec của mình, không bẻ nhãn cho vừa bug bên kia.

---

### D4-4 · Phát bảng `chunk_id` + báo 2 lỗi seam (30' — **làm buổi sáng, đừng để cuối ngày**)

Ba thứ tôi phát hiện khi quét code đồng đội sáng nay. Cả ba đều **chặn DoD `day-04.md:55`** (bảng
điểm 5 dòng), và **không cái nào tôi tự sửa được** — đều nằm trong lane người khác.

**(1) SC-05 bị chấm ngược — nghiêm trọng nhất.**
`GoldenCase.expects_refusal` của AIE-2 suy ra kiểu case bằng `expected_tenant != tenant`
(`golden_case.py:91`). SC-05 có `expected_tenant: ankor` **==** `tenant: ankor` (cùng tenant, lệch
**vai**) → trả `False` → `score_case` (`harness.py:68`) rẽ vào nhánh *trả-lời-được*:

```python
success = (answer.refused is False) and (answer.answer == case.expected)
```

Agent **từ chối đúng** → `refused=True` → `success=False`. **Hành vi đúng bị chấm FAIL.**

Gốc rễ không phải shape lệch — 7 field của tôi ánh xạ 1:1 vào `GoldenCase`. Gốc rễ là phép suy diễn
của AIE-2 chỉ có **hai trục** (chéo tenant, và `None`) nên **không biểu diễn được refusal chéo vai**,
trong khi `format.md` §5 dùng sentinel `expected: "refusal"` — mà `score_case` không đọc.
`GoldenCase` là của AIE-2, tôi không sửa. → **Q-B**.

**(2) Không ai có loader YAML.** `format.md` §1 nói tôi sinh `golden/smoke-5.yaml`; `run_smoke()`
nhận `GoldenSet` **in-memory**; `cli.py:22` đang dùng `_demo_golden_set()` hard-code. Giữa file YAML
và runner **không có gì**. `format.md` §10 chia việc "DE giữ file · AIE-2 chỉ đọc" → loader thuộc
phía đọc, nhưng nó chưa tồn tại. → **Q-A**.

**(3) AIE-1 tiêm search ở đâu?** `demo_stubs.py:26` ghi *"Day 6 replaces with real composition in
`apps/studio`"*, còn `day-04.md:39` bảo AIE-1 nối thật **hôm nay**. Hai mốc khác tầng (`apps/studio`
là composition root production, còn hôm nay chỉ cần đường demo) — cần hỏi cho rõ, không tự suy.
→ **Q-C**.

Cùng lúc đó, **phát bảng `chunk_id` ở D4-1 cho cả AIE-1 lẫn AIE-2** — nó là từ vựng chung để chấm
citation. Ghi vào `docs/format.md` (§8, cạnh bộ case) chứ không mở file mới: hai file cùng nói về
một thứ thì sớm muộn lệch nhau — đúng bài học D3-3.

---

### D4-5 · Daily-note D4

`docs/reports/daily-notes/2026-07-23-DongAnh2704.md` — submodule `docs/reports`, **không** để trong
`packages/kb` (`day02_plan.md:199`).

Giữ nguyên heading `## ` (pipeline đọc theo heading):
- **Bối cảnh & câu hỏi** ← Q-A…Q-D §7.
- **Việc đã làm** ← doc-factory · `StaticKbSearch` · `smoke-5.yaml`.
- **Contract / integration** ← 3 phát hiện D4-4, đặc biệt SC-05.
- **Quyết định kỹ thuật** ← vì sao class mới thay vì điền `KbSearchService`; vì sao vẫn lọc
  `section_roles` dù "chưa fence".
- **Blocker / escalate** ← kỷ luật 2-4-8h.

> Còn nợ từ hôm qua: `2026-07-21-DongAnh2704.md` đang có sửa **chưa commit** trong `docs/reports`.
> Dọn cùng lúc, đừng để treo sang D5.

---

## 2. Thứ tự thực thi (timebox)

| Slot | Việc | Ra cái gì | TT |
|---|---|---|---|
| **Sáng 1 (30') — sớm nhất** | **D4-4**: báo Q-A/Q-B/Q-C cho AIE-1 + AIE-2 | người khác không kẹt vì chờ tôi | ⬜ |
| Sáng 2 | **D4-1** doc-factory + test bảng chunk_id | 25 chunk, `#c2` = finance | ⬜ |
| Sáng 3 | **D4-2** `StaticKbSearch` + test cặp SC-01/SC-02 | `kb.search` trả `chunk_id` (**DoD `:53`**) | ⬜ |
| Chiều 1 | **D4-3** `golden/smoke-5.yaml` nhãn tay | 5 case (**DoD `:54`**) | ✅ |
| Chiều 2 | Phát bảng `chunk_id` vào `format.md` §8 | AIE-2 chấm citation được | ✅ |
| Chiều 3 | **D4-5** daily-note D4 + dọn nợ note D2 | DoD `:57` | ⬜ |
| Cuối ngày | commit + push `packages/kb`, rồi `docs/reports` | | ⬜ |

> D4-4 kéo lên **đầu tiên** dù nó không phải deliverable: 2 trong 3 phát hiện chặn DoD của AIE-2, và
> AIE-2 chỉ có 1 ngày. Báo lúc 16h thì báo làm gì.

---

## 3. Luồng git (GITFLOWS §4)

`packages/kb` đang ở nhánh `main` tại `a9f0e4d`, khớp `origin/main`.

```bash
cd packages/kb
git status -sb               # kỳ vọng: "## main...origin/main", KHÔNG [behind N]

# ... D4-1 .. D4-5 ...

git add -A
git commit -m "feat(kb): D4 — doc-factory chunk hoá + kb.search tĩnh (cited chunks) + golden 5 case nhãn tay"
git push
```

Test chạy **từ repo cha** (kb không test độc lập được):

```bash
cd /Users/nguyendonganh/agentcore-studio-kit
uv run pytest packages/kb/tests -q
```

**Bump con trỏ ở repo cha:** không phải việc của DE (GITFLOWS §5 — mentor).

---

## 4. Tự kiểm trước khi push

- [ ] `git status -sb` ở kb ra `## main...origin/main` — trên **branch**, không detached.
- [ ] **`src/studio_kb/search.py` không đổi 1 dòng** — `git diff --stat src/studio_kb/search.py` rỗng.
- [ ] **`src/studio_kb/pipeline.py` không đổi 1 dòng.**
- [ ] `test_search_contract.py` vẫn **XANH**.
- [ ] `StaticKbSearch.search` đúng **4 tham số**, đúng thứ tự Protocol — kiểm bằng gọi thật đủ 4
      keyword-arg, **không** dùng `isinstance` (bẫy đã biết, `day03_plan.md:80`).
- [ ] doc-factory ra đúng **25 chunk**; `ankor-expense-001#c2` = `finance`, 4 chunk kia = `public`.
- [ ] `chunk_id` đúng dạng `{doc_id}#c{n}` — **không UUID**.
- [ ] SC-01 vs SC-02 trả **nội dung khác nhau thật** (3 ngày vs 7 ngày), không phải cùng chunk.
- [ ] `smoke-5.yaml`: đủ 5 case × **7 field**, không field khuyết, `[]` viết tường minh.
- [ ] Mọi `expected_citation` khớp `chunk_id` factory sinh ra — **copy từ output, không gõ tay**.
- [ ] `section` chỉ thuộc `{public, hr, finance, engineering}`.
- [ ] 0 PII · chỉ `ankor`/`borea` + `alice`/`bob`/`carol` · NDA sạch (`day-04.md:56`).
- [ ] Daily-note D4 đã push; nợ note D2 đã dọn.

---

## 5. Ngoài phạm vi hôm nay (làm sớm = **bị chặn**)

Smoke-eval runner / bảng điểm / `compute_scorecard` (AIE-2) · `kb-retrieve` nối thật + `llm-step`
trích citation (AIE-1) · `recipe.kb_binding` (SWE) · **điền thân `KbSearchService.search`** ·
`KbPipeline.chunker/embed_invoke/index` chạy thật · embedding/vector · fence chunk-level +
`section_roles` server-side + leak-test T1/T6 (**S3**) · bộ golden 30 case (S2) · trace sink ·
cost dashboard.

---

## 6. Đối chiếu DoD của brief (`day-04.md:52-57`)

| DoD | Ai gánh | DE liên quan thế nào |
|---|---|---|
| `kb.search` trả `chunk_id` (citation chấm được) | **DE** | ✅ **D4-2** |
| 5 case **có nhãn tay** | **DE** | ✅ **D4-3** |
| Bảng điểm 5 dòng in ra CLI | AIE-2 | **gián tiếp — và đang có 2 mắt xích hỏng**: Q-A (loader), Q-B (SC-05). D4-4 báo sớm |
| Tên Callisto synthetic mới, NDA sạch | mọi vai | ✅ §4 — bộ định danh `ankor`/`borea` giữ nguyên theo `format.md` §9, "mới" = sinh mới/sạch NDA, không phải đổi tenant |
| **Daily-note D4** | mọi vai | ✅ **D4-5** |

---

## 7. Câu hỏi còn mở

| # | Hỏi ai | Nội dung | Nghiêng về |
|---|---|---|---|
| **Q-A** *(chặn DoD `:55`)* | **AIE-2** | `format.md` §1 chốt golden-set là **YAML ở `packages/kb/golden/`**, nhưng `run_smoke()` nhận `GoldenSet` in-memory và `cli.py` đang hard-code `_demo_golden_set()`. **Ai viết loader YAML → `GoldenSet`?** | **AIE-2** — §10 chia "DE giữ file · AIE-2 chỉ đọc", loader thuộc phía đọc. *Nếu AIE-2 không kịp:* tôi ship hàm đọc trong `packages/kb` trả `list[dict]` đúng 7 field, AIE-2 tự dựng `GoldenCase` — **không** để `packages/kb` import `studio_evalhub` (ngược chiều phụ thuộc, `make lint` chặn) |
| **Q-B** *(chặn DoD `:55` — **đã có repro**)* | **AIE-2** | Nạp `golden/smoke-5.yaml` vào `GoldenSet` rồi chấm bằng một agent **hành xử đúng tuyệt đối** (trả đúng đáp án, từ chối đúng chỗ, không rò chunk nào) → **4/5 PASS**, SC-05 là case duy nhất đỏ. `expects_refusal = expected_tenant != tenant` **không biểu diễn được refusal chéo vai**. SC-05 (`ankor`/`[engineering]` hỏi thang lương `hr`) có `expected_tenant == tenant` → rơi vào nhánh trả-lời-được → agent **từ chối đúng** bị chấm **FAIL**. Sửa thế nào? | thêm trục thứ ba, **không** bắt tôi bẻ nhãn. Rẻ nhất: đọc sentinel `expected == "refusal"` (`format.md` §5) như một điều kiện `or`. Hoặc so `section_roles` với `section_role` của chunk đáp án — nhưng cái đó cần dữ liệu KB, đắt hơn |
| **Q-C** | **AIE-1** | Hôm nay bạn tiêm `kb.search` thật ở **đâu**? `demo_stubs.py:26` ghi "Day 6 · `apps/studio`" nhưng `day-04.md:39` giao nối thật hôm nay. Tôi sẽ export `StaticKbSearch` từ `studio_kb` — bạn import thẳng, hay cần tôi để ở chỗ khác? | import thẳng `from studio_kb.static_search import StaticKbSearch` cho đường **demo D4**; đường `apps/studio` vẫn để D6 |
| **Q-D** *(chuyển tiếp, chưa có trả lời)* | SWE + mentor | Từ vựng `section_role` 4 giá trị `{public, hr, finance, engineering}` chốt chưa? SWE resolve role server-side nên phải khớp. *Ghi chú: demo của AIE-2 (`cli.py:31`) đang dùng `section_roles=["employee"]` — **ngoài từ vựng**. Case đó synthetic nên sẽ biến mất khi YAML thật land, nhưng nếu `"employee"` là ý định thật thì phải chốt lại từ vựng.* | giữ 4 giá trị |
| **Q-E** | mentor | Tên file: `format.md` §1 dùng `smoke-5.yaml`, `day-04.md:32` dùng `smoke_5.yaml`. Giữ bản nào? | **`smoke-5.yaml`** — đã phát cho AIE-2 từ D2, đổi bây giờ tốn hơn |

---

*Plan D4 — DE, 23/07/2026. Sửa lại khi AIE-2 trả lời Q-A/Q-B (ảnh hưởng trực tiếp việc bảng điểm có
chạy được trong ngày hay không).*
