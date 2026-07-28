---
id: studio.de.day-06-plan
type: day-plan
status: draft
author: DE — Nguyễn Đông Anh
date: 2026-07-27
sprint: s1
day: 6
week_calendar: 2
title: "Kế hoạch Ngày 6 (T2 27/07) — DE: trace sink nhận call thật + reader chứng minh 0-gap"
---

# KẾ HOẠCH NGÀY 6 — DE (KB pipeline + obs/eval data)
### Thứ Hai 27/07 · **Xâu-kim lần 1** · luật ngày: **thông trước, đẹp sau**

> Nguồn chuẩn: `docs/requirements/week-1/days/day-06.md` · bút DE
> (`docs/contracts/trace-event.v0.md`, `kb-search.v0.md`) · `plans/day05_plan.md` · `GITFLOWS.md` §4.
>
> `day-06.md:26` gọi đây là **ngày quan trọng nhất của tuần**: chứng minh spine tồn tại. Bẫy phải
> diệt cũng ghi sẵn — *"các mảnh vẫn **mock lẫn nhau** để né tích hợp"*.

---

## 0. Ranh giới — hẹp hơn bảng giao việc trông có vẻ

`day-06.md:39` giao DE: *"`kb.search` + **trace sink nhận call thật** từ interpreter (không stub
rỗng); kiểm citation ra `chunk_id`"*.

| Việc | DE? | Trạng thái vào D6 |
|---|---|---|
| **trace reader** — timeline in-order, phát hiện thiếu node | ✅ | **xong ở D5** (`trace_reader.py` + `test_trace_reader.py`) — không mang sang |
| **trace sink nhận call thật** — chứng minh event vào `obs.trace_events` rồi đọc lại được | ✅ | **deliverable chính** |
| `kb.search` nhận call thật | ✅ | **API xong** (D-13: `tenant_id: UUID`, #25) — xem §1 |
| citation ra `chunk_id` | ⚠️ | kb trả `chunk_id` thật, nhưng **đường end-to-end đang tắc slug→UUID** — §1 + §D6-3 |
| Interpreter đọc `dag` từ recipe (bỏ hardcode) | ❌ | AIE-1 (`:38`) |
| Emit-trace hook (mỗi node → 1 event) | ❌ | SWE (`day-05.md:38`) — xem §4 Q-B |
| Recipe feed vào interpreter entry đầy đủ | ❌ | SWE (`:37`) |
| smoke-eval chạy trên luồng thật | ❌ | AIE-2 (`:40`) |

**Kho ghi được: chỉ `packages/kb/**` + `docs/reports/**`.**

### 0.1 Hai quyết định chốt trước, để plan không trôi

**① D6 xâu kim bằng `StaticKbSearch`, KHÔNG đổi sang `PgKbSearch`.**

`:39` nói *"không stub rỗng"* — `StaticKbSearch` **không phải stub**: nó tìm thật trên 25 chunk thật,
lọc thật hai trục, và đã chạy end-to-end với recipe của SWE. DoD D6 không nhắc Postgres cho KB.

Đổi sang `PgKbSearch` ở D6 sẽ kéo theo một chuỗi: dựng Docker → chạy ingest thật → **xoá một test
đang xanh** (`test_search_contract.py`) → gỡ `xfail` ở `test_leak.py` → cộng phần wiring. Dồn ngần
đó thay đổi trạng thái vào đúng ngày cần một lần chạy sạch là tự chuốc rủi ro.

Hai bản dùng chung Protocol `KbSearch` nên hoán đổi là **một dòng**, làm riêng theo lịch của nó
(`plans/db_plan.md`). **Nâng KB lên Postgres = ngoài phạm vi D6.**

**② `StaticKbSearch` KHÔNG vi phạm DoD `:54` ("không còn mảnh nào mock lẫn nhau").**

Ghi rõ ra đây để không ai đọc "in-memory" thành "vẫn đang mock". Luật `:46` cấm **mock lẫn nhau** —
tức quadrant này dựng giả quadrant kia để né tích hợp. `StaticKbSearch` là **impl thật của DE trên dữ
liệu thật**, được AIE-1 tiêm vào qua Protocol. Thứ phải gỡ là `EmptyKbSearch` (engine) và
`_DemoRunner` (evalhub) — đều không phải của DE.

---

## 1. Trạng thái trước D6 — `kb.search` xong (API), đường citation vướng D-13

Kiểm bằng chạy thật, không phải tự khai. Lần chạy 23/07 (**TRƯỚC #25**):

```
recipe SWE (create_recipe_d4)  →  interpreter  →  StaticKbSearch
  scope 'ankor/public' → node.params{tenant(slug), section_roles}
  kb-retrieve  → ['ankor-leave-001#c1', '#c3', '#c2']
  citations    → ['ankor-leave-001#c1']
```

→ **`kb.search` (API) đã đạt** và giờ đã lên D-13: `search(tenant_id: UUID)`, DE cấp sẵn
`resolve_tenant_id` (slug→UUID). **NHƯNG** sau #25 đường end-to-end **hồi quy**: `executors.py:77`
vẫn truyền `node.params["tenant"]` (slug `"ankor"`) vào arg UUID → `chunk.tenant_id (UUID) != "ankor"
(str)` → lọc rỗng → **không ra citation**. Nên vế citation của `:39`/`:55` **chưa với tới đầu-cuối**
cho tới khi có bước resolve ở biên (§D6-3, vai AIE-1/SWE). Vế còn lại thuộc DE: **trace**.

---

## 2. Deliverable

### D6-0 · Dựng Postgres chạy được — **chặn mọi thứ**

Nợ mang sang từ D4: `postgres.py` + 10 test **chưa từng chạy một câu SQL nào**. Mà D6 là ngày trace
vào Postgres.

```bash
docker compose -f docker-compose.test.yml up -d
export STUDIO_DATABASE_URL_ADMIN='postgresql://postgres:postgres@localhost:5433/studio_test'
export STUDIO_DATABASE_URL='postgresql://studio_app:...@localhost:5433/studio_test'
uv run pytest packages/kb/tests -q          # 10 test D4 phải XANH trước đã
```

**Xong là:** nền Postgres đã có người bước lên. Nếu D5 đã làm thì bỏ qua.

---

### D6-1 · Trace reader — **xong ở D5** (không mang sang)

`trace_reader.py` + `test_trace_reader.py` đã land trên nhánh này (D5), **không còn là việc D6**. Giữ
mục này để đối chiếu; thiết kế đầy đủ ở `plans/day05_plan.md` §D5-1/D5-2. Ba tính chất phải bảo toàn:

1. `read_run(run_id)` xếp theo `ts` — **parse ra `datetime` rồi mới sắp**, không `ORDER BY ts` (cột
   là `TEXT`, so chuỗi sai lặng lẽ khi định dạng lệch). Parse hỏng thì **raise**.
2. "0-gap" = **không sót node**, không phải "thời gian liên tục" (`day-05.md:53` — *"Mọi node… không
   sót node"*).
3. Test có răng: cố ý **bỏ 1 node** → reader phải kêu. Reader chỉ biết in ra thì luôn trông như thành
   công.

---

### D6-2 · **Trace sink nhận call thật** — deliverable chính, và tách làm hai phần

Đây là chỗ dễ kẹt nhất của ngày, vì nó đụng ranh giới quyền. Tách rõ:

#### a) Phần DE tự chứng minh được — **không phụ thuộc ai**

`.importlinter` cấm `studio_kb` import `studio_app`, nhưng **thư mục `tests/` không nằm trong
namespace `studio_kb`** nên không bị quét — `conftest.py` gốc đã import `studio_app` sẵn, và
`test_leak.py` đang dùng đúng đường đó.

→ Viết một test tích hợp trong `packages/kb/tests/`: dựng `PgTraceWriter` thật → ghi một chuỗi
`TraceEvent` → **reader đọc lại**, đúng thứ tự, phát hiện được node thiếu.

Đây là bằng chứng *"sink + reader chạy thật trên Postgres"*, làm được ngay, **không chờ ai**.

#### b) Phần KHÔNG thuộc DE — luồng demo chạy thật

DoD `:53` đòi **1 luồng chạy hết 4 quadrant**, tức phải có một chỗ dựng đồng thời `PgTraceWriter` +
`StaticKbSearch` + LLM + interpreter. Chỗ đó **chỉ có thể là `apps/studio`**:

| | |
|---|---|
| `PgTraceWriter` sống ở | `apps/studio` |
| Quadrant được import `studio_app` không | **KHÔNG** — `.importlinter` layers |
| `engine/__main__.py` hiện dùng | `_NoOpTraceWriter`, docstring ghi thẳng *"without pulling in `PgTraceWriter`/`studio_app`"* |
| `create_app()` có wire quadrant không | **KHÔNG** — có "Deviation note" giải thích P1 chỉ ship `__init__.py` rỗng |

→ Không ai trong nhóm dựng được composition đó: `apps/studio` là **mentor**, cả 4 kỹ sư chỉ có READ.

**Hỏi mentor TRƯỚC thứ Hai** (§4 Q-A). Phát hiện chuyện này lúc 9h sáng D6 là mất ngày quan trọng
nhất tuần.

---

### D6-3 · Gỡ mock phía DE + ghi điểm gãy còn lại

DoD `:54` bắt gỡ mock lẫn nhau. **Phía DE không có gì để gỡ** — `StaticKbSearch` là impl thật (§0.1②),
và `postgres.py` không nằm trên đường chạy nào.

Việc thật của DE ở đây là **`:56` — ghi điểm gãy còn lại**. Tính tới 23/07:

| điểm gãy | ai | |
|---|---|---|
| **`kb-retrieve` truyền slug vào arg UUID** (`executors.py:77`) → lọc rỗng, mất citation | **AIE-1 (#22)** | kb.search cần `tenant_id: UUID` (D-13); executor đọc `node.params["tenant"]`=slug, chưa resolve. DE đã cấp `resolve_tenant_id`. **Chặn `:55`** |
| **Recipe mang 2 danh tính tenant** | SWE/AIE-1 | `builder_d4` đặt `node.params["tenant"]`=slug **và** `recipe.tenant_id`=UUID; node mang slug còn seam cần UUID → nên đưa `tenant_id` UUID vào `node.params` |
| **#25 (UUID) chưa merge lên kb `main`** → workspace/demo kéo kb=str | DE + mentor | `feat/day5-reader-d13` chưa vào `main`; con trỏ cha + PR #60 trỏ kb `main` (str) ⟂ `contracts@UUID`. **Chặn `:53`** — việc: merge #25 → kb main rồi bump con trỏ (§3) |
| Đường đưa `query` vào lúc chạy | SWE + AIE-1 | `create_recipe_d4` không có tham số `query`; `interpreter.run()` cũng không → chạy 5 case thì 3 case sai đề |
| `refused = not retrieved_chunks` (SC-04) | AIE-1 | đã có đề xuất kiểm chứng, chưa gửi |
| Citation không đối chiếu khi truy xuất rỗng | AIE-1 | `citations = extracted` — dấu ngoặc nào cũng lọt |
| Adapter `engine → AgentAnswer` (#29) · merge nhánh D4 | AIE-2 | |
| Emit-trace hook | SWE ↔ AIE-1 | xem Q-B |

Ghi vào daily-note D6 — đó là artifact `:56` đòi.

---

## 3. Thứ tự (timebox)

| Slot | Việc | TT |
|---|---|---|
| **Trước T2** | **Merge `feat/day5-reader-d13` → kb `main`** (#25 UUID) để demo kéo kb khớp `contracts@UUID` — chặn `:53` | ⬜ |
| **Trước T2** | Nhắn mentor **Q-A** (composition), nhắn SWE+AIE-1 **Q-B** (emit hook) | ⬜ |
| Sáng 1 | **D6-0** Docker + 10 test D4 xanh | ⬜ |
| Sáng 2 | **D6-1** reader (nếu D5 chưa xong) | ⬜ |
| Sáng 3 | **D6-2a** test tích hợp `PgTraceWriter` → reader | ⬜ |
| Chiều 1 | Ghép cùng cả nhóm — DE trực để `kb.search`/trace nhận call thật | ⬜ |
| Chiều 2 | **D6-3** ghi điểm gãy còn lại | ⬜ |
| Cuối ngày | Daily-note D6, PR | ⬜ |

> Hai câu hỏi đặt **trước thứ Hai**, không phải sáng thứ Hai. Cả hai đều là chuyện quyền ghi — không
> ai giải quyết được trong lúc đang ghép.
>
> Chiều 1 để trống có chủ ý: `:43` nói *"hôm nay **tất cả ghép vào nhau cùng lúc**"*. Nhét deliverable
> vào slot đó là tự đảm bảo không có mặt lúc người khác cần.

---

## 4. Câu hỏi phải hỏi TRƯỚC thứ Hai

| # | hỏi ai | nội dung | nghiêng về |
|---|---|---|---|
| **Q-A** *(chặn DoD `:53`)* | **mentor** | Luồng demo cần một chỗ dựng đồng thời `PgTraceWriter` (ở `apps/studio`) + interpreter + `kb.search`. `.importlinter` cấm quadrant import `studio_app`, mà `apps/studio` thì cả 4 kỹ sư chỉ READ, và `create_app()` hiện không wire quadrant nào. Ai dựng composition đó, và đặt ở đâu? | mentor dựng trong `apps/studio` (đúng vai composition root, đúng mốc "Day 6" mà `demo_stubs.py:26` đã ghi). *Nếu không kịp:* chấp nhận D6 chứng minh bằng **script/test ngoài tầng package** (tests không bị import-linter quét), ghi rõ đó là dàn dựng để chạy thử, chưa phải composition thật |
| **Q-B** *(chặn DoD `:53`)* | **SWE + AIE-1** | Emit-trace hook giao **SWE** (`day-05.md:38`) nhưng phải sửa `interpreter.run()` — file trong `packages/engine`, **SWE không có quyền ghi**. Cùng kiểu vướng đã gặp ở `kb_binding` và test wiring. Ai làm, ở repo nào? | AIE-1 làm trong engine theo thiết kế SWE chốt. Không có nó thì `del trace_writer` vẫn còn, `events=[]`, và reader của DE không có gì thật để đọc |
| **Q-C** | AIE-1 | `refused = not retrieved_chunks` làm SC-04 sai. Đề xuất: đọc dấu hiệu khai báo + lui về cách cũ — đã chạy thử 5/5 và vẫn bắt được agent bịa. Neo: `kb-search.v0.md` §6.1a (*"khác rỗng ≠ có đáp án"*) | như đề xuất |
| **Q-D** | mentor | `pyyaml` chưa khai báo ở đâu — chặn loader (evalhub) + test canh golden-set (kb). Đụng `uv.lock` repo cha nên DE không tự làm được | thêm vào `[dependency-groups].dev` |

---

## 5. Tự kiểm trước khi push

- [ ] **#25 (UUID) đã merge lên kb `main`** trước khi demo kéo submodule (chưa thì demo lấy kb=str → vỡ).
- [ ] Trên **nhánh** `day6/trace-sink-live` tách từ **kb `main` đã có #25**, không phải `main` (guard chặn push thẳng).
- [ ] 10 test D4 (`test_pg_kb.py`) **xanh thật**, không còn skip.
- [x] Reader đọc đúng thứ tự **và** báo được node thiếu — **xong ở D5** (`test_trace_reader.py`, có test cố ý bỏ node).
- [ ] `apps/studio/**` không đổi một dòng.
- [ ] `search.py` + `pipeline.py` vẫn nguyên; `test_search_contract.py` xanh.
- [ ] `lint-imports` xanh — reader **không** import `studio_app` trong `src/`.
- [ ] Điểm gãy còn lại đã ghi vào daily-note (DoD `:56`).
- [ ] Daily-note D6.

---

## 6. Ngoài phạm vi

Nâng KB lên Postgres / `PgKbSearch` vào đường chạy (§0.1①, để `db_plan.md`) · nối
`KbSearchService` + gỡ `xfail` `test_leak.py` · cost-lineage 3-surface (**S3**) · RLS cho
`obs.trace_events` (không sửa được, `apps/studio`) · thêm node thứ 4+ (`:46` — vẫn 3-node) ·
trace viewer UI (S2).

---

*Plan D6 — DE, 27/07/2026. Q-A và Q-B phải có câu trả lời trước sáng thứ Hai; cả hai đều chặn DoD
`:53` và cả hai đều là chuyện quyền ghi, không phải chuyện kỹ thuật.*
