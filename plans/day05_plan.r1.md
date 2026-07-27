---
id: studio.de.day-05-plan
type: day-plan
status: superseded
superseded_by: day05_plan.md (r2, 24/07 sáng)
author: DE — Nguyễn Đông Anh
date: 2026-07-24
sprint: s1
day: 5
week_calendar: 1
title: "Kế hoạch Ngày 5 (T6 24/07) — DE: trace reader (timeline in-order, 0-gap) + review chéo"
---

> ⚠️ **BẢN r1 — ĐÃ THAY THẾ.** Viết tối 23/07, trước khi mentor chốt ranh giới trace (#21–#24) và
> trước khi phát hiện `kb` chưa adopt D-13. Giữ lại để đối chiếu. Bản đang dùng: `day05_plan.md`.

# KẾ HOẠCH NGÀY 5 — DE (KB pipeline + obs/eval data)
### Thứ Sáu 24/07 · Sprint 1 · **Integration/review day** · luật ngày: **ít build, nhiều ghép**

> Đây là **plan thi công**, chưa phải sản phẩm.
> Nguồn chuẩn: `docs/requirements/week-1/days/day-05.md` · bút DE
> (`docs/contracts/trace-event.v0.md`) · `umbrella-contract.md` §4 · `GITFLOWS.md` §4.

> ## ⚠️ Bản brief đang lưu hành có chỗ LỖI THỜI — đọc trước khi làm
>
> Bản giao việc tôi nhận được ghi *"Bút trace sink **SQLite** (mọi node emit)"*. **Sai, và sai theo
> hướng nguy hiểm** — làm theo là viết nhầm cả một tầng lưu trữ.
>
> | nguồn | nói gì |
> |---|---|
> | `day-05.md:15,18,22,37,46` (repo) | **Postgres**, năm chỗ, kể cả tiêu đề |
> | `week-1/README.md:141` | *"Trace vào **Postgres** `obs.trace_events`"* |
> | `umbrella-contract.md` §4 | *"**Postgres-everything từ S1**… không có nấc 'đổi DB' — Postgres từ L0"* (commit `56da923`) |
> | thực tế kit | bảng `obs.trace_events` + `PgTraceWriter` đã tồn tại; **0 dòng SQLite** trong toàn bộ code |
>
> `week-1/README.md:17` đã viết sẵn luật cho tình huống này: *"Mọi con số/quy ước bám 4 file gốc —
> nếu thấy lệch, **file gốc thắng, báo mentor**."*
>
> → **Làm theo Postgres.** Báo mentor bản đang lưu hành còn sót (§7 Q-F) — không phải để bắt lỗi,
> mà vì ba người còn lại có thể đang đọc cùng bản đó.

---

## 0. Ranh giới hôm nay — **sink đã có sẵn, đừng dựng lại**

`day-05.md:37` giao DE *"**Bút** trace sink Postgres (mọi node emit) + `trace` reader"*. Đọc chữ
"bút trace sink" mà chưa tra repo thì sẽ ngồi viết lại một thứ **đã tồn tại và đã hoàn chỉnh**:

| thành phần | ở đâu | tình trạng |
|---|---|---|
| `TraceEvent` contract (12 field) | `studio_contracts/trace.py` | ✅ **bút DE, đã land** |
| Bảng `obs.trace_events` (đủ 12 cột) | `apps/studio/obs/schema.py:19` | ✅ mentor ship ở P4 |
| `PgTraceWriter.write()` — 1 câu INSERT | `apps/studio/obs/trace_writer.py:24` | ✅ **đã có thân đầy đủ** |
| `TraceWriter` Protocol | `studio_contracts/protocols.py:37` | ✅ |
| **reader — đọc lại timeline** | **không ở đâu cả** | ❌ **← đây mới là việc của tôi** |

Quét cả workspace: **không có một dòng nào đọc `obs.trace_events`** ngoài test của mentor. Nên
deliverable dựng được của DE hôm nay là **reader**, hết. Sink thì tiêu thụ cái đã có.

| Việc | Trong scope DE? | Ghi chú |
|---|---|---|
| **`trace` reader** — cho `run_id`, in timeline đúng thứ tự, phát hiện gap | ✅ | **deliverable duy nhất phải dựng** |
| Review PR SWE (recipe shape), bắt ≥1 vấn đề thật | ✅ | **là DoD `:55`**, không phải việc phụ |
| Daily-note D5 | ✅ | DoD `:57` |
| Viết lại `PgTraceWriter` / sửa `obs/schema.py` | ❌ | `apps/studio` = mentor, DE chỉ READ |
| Gắn emit-trace hook vào interpreter loop | ❌ | SWE (`day-05.md:38`) |
| Node-executor populate `tokens`/`node_type`/`outputs` | ❌ | AIE-1 (`:39`) |
| Scorecard đọc trace chấm citation · nạp smoke-5 vào demo | ❌ | AIE-2 (`:40`) |
| Cost-lineage 3-surface · `obs.costs` điền thật | ❌ | **S3** — `:46` cấm làm sớm |

**Kho ghi được hôm nay: chỉ `packages/kb/**` + `docs/reports/**`.**

> ⚠️ **Hôm nay là ngày review** (`:19` — *"≥50% review, không cấp goal build mới"*). Reader cố ý
> nhỏ. Nếu thấy mình đang dựng thêm thứ gì ngoài nó, đó là dấu hiệu đi lệch — thời gian còn lại
> thuộc về đọc code người khác, và **bắt ≥1 vấn đề thật là một ô DoD**, ngang hàng với build.

---

## 1. Deliverable hôm nay (4 mục)

### D5-0 · Dựng Postgres chạy được — **làm trước tiên, chặn mọi thứ còn lại**

Hôm nay **toàn bộ** là Postgres. Mà tầng Postgres viết ở D4 (`postgres.py`, 10 test) **chưa từng
chạy một câu SQL nào** — Docker tắt, test skip hết. Cùng một hạ tầng (DSN, pool, giao dịch, grant)
đỡ cả `kb.chunks` lẫn `obs.trace_events`; hỏng ở đâu thì hỏng cả hai.

```bash
docker compose -f docker-compose.test.yml up -d        # pgvector/pgvector:pg17, cổng 5433
export STUDIO_DATABASE_URL_ADMIN='postgresql://postgres:postgres@localhost:5433/studio_test'
export STUDIO_DATABASE_URL='postgresql://studio_app:...@localhost:5433/studio_test'
uv run pytest packages/kb/tests/test_pg_kb.py -q       # 10 test D4 phải XANH trước đã
```

**Xong là:** 10 test D4 xanh thật. Đỏ thì sửa **trước khi** viết reader — đừng chồng code mới lên
nền chưa ai bước lên.

> `studio_app` có SELECT trên `obs.*`: `ALL_SCHEMAS` ở `core/schema.py:81` gồm `obs`, và
> `grant_app_privileges` cấp `SELECT/INSERT/UPDATE/DELETE` cho cả 5 schema. Reader đọc qua app-pool
> được, không cần admin-pool.

---

### D5-1 · `trace` reader — deliverable chính

Đặt ở `src/studio_kb/trace_reader.py`. Đọc `obs.trace_events` bằng SQL thô, chỉ import `TraceEvent`
(contracts) + pool — **không** import `studio_app`, y hệt cách `PgKbSearch` đọc `kb.chunks`.
`.importlinter` cho phép; đây không phải lách luật.

> **Giả định đang chạy dưới:** reader thuộc `packages/kb` vì week-1 §5 giao DE *"KB pipeline **+
> obs/eval data**"*, và đây là phía **đọc** dữ liệu quan trắc. Đã hỏi mentor (§7 Q-A) nhưng **không
> chờ trả lời** — code không đụng gì của `apps/studio`, sai chỗ thì chuyển file, không phải viết lại.

Ba việc, đúng chữ DoD `:53-54`:

| # | việc | neo |
|---|---|---|
| 1 | `read_run(run_id) -> list[TraceEvent]`, xếp theo `ts` tăng dần | `:54` "đúng thứ tự" |
| 2 | `render_timeline(events) -> str` — in ra người đọc được | `:32` "reader in timeline" |
| 3 | **phát hiện gap** — thiếu node so với chuỗi kỳ vọng | `:54` "0-gap" |

**Về (3) — "0-gap" nghĩa là gì phải chốt bằng chữ trước khi code.** Hai cách hiểu:

- **thời gian liên tục** — không khoảng trống giữa các `ts`. Vô nghĩa: node chạy nhanh chậm khác nhau.
- **không sót node** — mỗi node trong DAG của run phải có đúng 1 event.

Chọn cách hai, và `:53` nói thẳng: *"**Mọi node** của 1 run emit event (**không sót node**)"*. Nên
reader so **tập node đã emit** với **chuỗi node kỳ vọng**, báo cái thiếu. Ghi định nghĩa này vào
`trace-event.v0.md` — không chốt miệng, đúng bài học D4.

**Về `ts`:** cột là `TEXT` (`obs/schema.py:26`), chứa ISO-8601. Sắp bằng `ORDER BY ts` là **so
chuỗi**, chỉ đúng khi mọi timestamp cùng định dạng và cùng độ dài (có `Z`, có micro-giây). Lệch định
dạng giữa các node là thứ tự sai **im lặng**. Reader phải parse ra `datetime` rồi mới sắp, và
**raise khi parse hỏng** thay vì lặng lẽ giữ nguyên thứ tự đọc từ DB.

> ⚠️ **Không assert `ts` tăng nghiêm ngặt.** Hai node chạy trong cùng một mili-giây có thể trùng
> `ts`. Dùng `ts` để sắp, dùng **tập node** để kiểm 0-gap — đừng trộn hai việc.

**Xong là:** cho một `run_id`, in ra được timeline có thứ tự và nói được "đủ node" hay "thiếu node
nào".

---

### D5-2 · Test reader — **không chờ SWE/AIE-1**

Đây là chỗ gỡ rủi ro lớn nhất của ngày: reader **không phụ thuộc** emit-hook (SWE) hay populate
(AIE-1). Tự ghi event bằng `PgTraceWriter` đã có sẵn, rồi đọc lại.

| test | chứng minh |
|---|---|
| ghi 4 event xáo trộn thứ tự → đọc ra **đúng thứ tự `ts`** | `:54` |
| cố ý bỏ 1 node → reader **báo thiếu**, không im lặng | `:53` — và đây là test có răng |
| hai `run_id` xen kẽ → đọc run A **không lẫn** event của run B | cách ly run |
| `ts` sai định dạng → **raise**, không sắp bừa | bẫy so chuỗi ở trên |
| `run_id` không tồn tại → trả `[]`, không raise | rỗng là hợp lệ |

Bài thứ hai quan trọng nhất: một reader chỉ biết in ra thì **luôn trông như thành công**. Phải có
bài mà nó bắt buộc phải kêu.

---

### D5-3 · Review PR của SWE — **DoD `:55`, không phải việc phụ**

`day-05.md:37` giao DE review **PR SWE (recipe shape)**. Yêu cầu là **bắt ≥1 vấn đề thật** — không
phải "LGTM".

Chỗ đáng soi nhất, dựa trên thứ đã đụng ở D4:

- `recipe.kb_binding.{kb_id, scope}` (SWE làm ở D4) — `scope` có mang **cả `tenant` lẫn
  `section_roles`** không? Thiếu vế vai thì T6 không có đường đi từ recipe xuống `kb.search`.
- Từ vựng `section_role` bên SWE có khớp `{public, hr, finance, engineering}` không — họ là bên
  phân giải role server-side (`callisto-doc-schema.md` §10 Q1, tới giờ **vẫn chưa ai trả lời**).
- `public` có được cấp **ngầm** không? Nếu không, mọi request phải tự nhớ kèm `public`, quên là
  người dùng mất quyền đọc tài liệu chung — và triệu chứng là "tìm không ra", không phải báo lỗi.
- `golden_set_ref` trong recipe trỏ tới **file** `golden/smoke-5.yaml` hay **hàng** `eval.golden_sets`?
  Hai bên đang hình dung hai vật khác nhau (xem Q-C).

---

### D5-4 · Teach-back weekly demo — **KB pipeline: ingest→chunk→embed→index + fence-data**

Bản giao việc chỉ đích danh slot demo của DE là **teach-back KB pipeline**, không phải "demo chung
chung". Đây là phần dễ bị bỏ tới phút chót nhất, mà lại là ô DoD.

**Xương sống 5 bước — nói đúng cái đang có, đừng nói cái đáng lẽ có.** Trạng thái thật hôm nay:

| bước | thực tế | bằng chứng chạy được |
|---|---|---|
| **ingest** | `doc_factory` đọc 5 `.md` ở `docs/callisto/` | ✅ chạy thật |
| **chunk** | cắt theo heading `##` · `chunk_id = {doc_id}#c{n}` · 25 chunk | ✅ 7 test xanh |
| **embed** | **chưa có embedding thật ở bất kỳ đâu trong workspace** — chỉ `FakeEmbedding` (SHA256, 8 chiều) và fake băm-túi-từ của tôi | ⚠️ **phải nói thẳng** |
| **index** | `KbIngest` → `kb.chunks`, `ON CONFLICT DO UPDATE` giữ nguyên `chunk_id` | ⚠️ **viết rồi, chưa chạy** → D5-0 |
| **fence-data** | `StaticKbSearch` lọc 2 trục, có test; `PgKbSearch` lọc trong SQL + RLS | ✅ / ⚠️ bản Pg chưa chạy |

> **Hai trong năm bước hiện chưa chứng minh được.** Đó là lý do D5-0 (dựng Docker) không phải việc
> dọn dẹp tuỳ chọn — nó quyết định teach-back của bạn là *"đây, chạy đây"* hay *"em viết rồi nhưng
> chưa chạy"*. Làm buổi sáng.

**Ba điểm nên nói, vì chúng là *quyết định* chứ không phải *tính năng*** — teach-back chấm ở chỗ
hiểu vì sao, không phải liệt kê được gì:

1. **Vì sao `chunk_id` là chữ có quy luật, không phải UUID.** `re_index` ở S3 bắt giữ nguyên
   `chunk_id`; UUID ngẫu nhiên thì mỗi lần index lại là golden-set chết sạch. Kèm cái giá phải
   chấp nhận: chèn heading vào **giữa** doc là đánh số lại phía sau.
2. **Vì sao fence phải ở tầng truy xuất.** Hàng rào có **hai trục**, và chỉ một trục có lưới: RLS
   khoá `tenant_id`, còn `section_role` **không có policy nào** — chặn hoàn toàn bằng `WHERE`. Mất
   mệnh đề đó là hở T6, im lặng. Đây cũng là câu week-1 §4 đòi trả lời ở Gate D10 (*"vì sao
   fence-tại-retrieval là LUẬT"*), nên tập trước từ hôm nay là lãi.
3. **Vì sao `StaticKbSearch` không phải hình nộm.** Phân biệt với `EmptyKbSearch` (luôn trả `[]`):
   bản của tôi tìm thật, lọc thật — hỏi từ Ankor ra "3 ngày", từ Borea ra "7 ngày", hỏi thang lương
   bằng vai `engineering` ra **rỗng**. Hình nộm không chứng minh được điều nào trong ba.

**Xong là:** chạy được một mạch trước mặt người khác, và trả lời được "vì sao" cho cả ba, không đọc
slide.

---

### D5-5 · Daily-note D5 + trả nợ D4

`docs/reports/daily-notes/2026-07-24-DongAnh2704.md`.

**Nợ mang sang từ D4, dọn buổi sáng:**
- **daily-note D4 chưa viết** (DoD D4 `:57` còn treo) — viết bù cùng lúc, đừng gộp vào note D5.
- `2026-07-21-DongAnh2704.md` **vẫn đang sửa dở chưa commit** trong `docs/reports` — treo từ D3.
- **Pre-commit NDA-denylist chưa cài ở `kb`** (GITFLOWS §9.3 bắt mọi repo). Thư mục hook rỗng.
  Script có sẵn ở `docs/requirements/nda-denylist.sh`. 5 phút.
- `day02_plan.md:84,103,196` còn mô tả **SQLite** như lựa chọn mở. `umbrella-contract.md` §4 đã chốt
  *"Postgres-everything từ S1... không có nấc đổi DB"* (commit `56da923`). Hôm nay đúng là ngày
  trace-vào-Postgres — để câu hỏi đã đóng nằm đó là mời người khác hỏi lại. Đánh dấu Q5 đã đóng.

---

## 2. Thứ tự thực thi (timebox)

| Slot | Việc | Ra cái gì | TT |
|---|---|---|---|
| **Sáng 1 (30')** | **D5-0** dựng Docker, chạy 10 test D4 | nền Postgres xanh thật | ⬜ |
| Sáng 2 (20') | **D5-5** trả nợ D4: note D4, note D2, pre-commit, Q5 | hết treo artifact | ⬜ |
| Sáng 3 | **D5-1** reader + chốt định nghĩa "0-gap" bằng chữ | `trace_reader.py` | ⬜ |
| Chiều 1 | **D5-2** test reader (5 bài) | DoD `:53-54` chứng minh được | ⬜ |
| **Chiều 2 (đặt lịch cứng)** | **D5-3** review PR SWE | comment bắt ≥1 vấn đề thật (**DoD `:55`**) | ⬜ |
| Chiều 3 (30' tập trước) | **D5-4** teach-back KB pipeline — chạy thử một mạch, không đọc slide | recording (**DoD `:56`**) | ⬜ |
| Cuối ngày | **D5-5** daily-note D5, push | DoD `:57` | ⬜ |

> D5-0 lên đầu vì mọi thứ sau nó đều là Postgres. Phát hiện hạ tầng hỏng lúc 3h chiều thì mất cả
> ngày.
>
> D5-3 **đặt lịch cứng**, không để "làm nốt nếu còn giờ": review là DoD, và PR của SWE có sớm thì
> họ cũng cần thời gian sửa theo comment trước demo.

---

## 3. Luồng git — **đổi cách làm từ hôm nay: nhánh + PR**

D4 tôi push thẳng `main`. Đúng theo `GITFLOWS.md` §4, nhưng **lệch nhịp với đội và với gate**:

| | |
|---|---|
| `packages/engine` (AIE-1) | 3 PR đã merge (#1, #2, #3) |
| `packages/kb` (tôi) | **0 PR** |

`day-05.md:39` xếp lịch **AIE-1 review "PR DE (`kb.search`)"** — hôm nay họ mở ra sẽ không thấy PR
nào. Và week-1 §4 (điều kiện qua Gate D10) đòi *"một luồng đi hết 4 quadrant, chạy thật, **PR đã
merge qua review**"*.

```bash
cd packages/kb
git checkout main && git pull
git checkout -b day5/trace-reader        # ← từ hôm nay
# ... D5-1, D5-2 ...
git push -u origin day5/trace-reader
gh pr create --fill
```

Phần `kb.search` của D4 đã nằm trên `main` nên không PR ngược được. Gửi AIE-1 **link compare
`a9f0e4d..2de0c1a`** để họ review theo dải commit — nội dung vẫn review được, chỉ là không có chỗ
comment inline. Nói rõ lý do, đừng để họ tưởng bị bỏ qua.

Test chạy **từ repo cha**:

```bash
cd /Users/nguyendonganh/agentcore-studio-kit
uv run pytest packages/kb/tests -q
make lint
```

---

## 4. Tự kiểm trước khi push

- [ ] Đang trên **nhánh** `day5/trace-reader`, không phải `main`, không detached.
- [ ] **10 test `test_pg_kb.py` của D4 đã xanh thật** (không còn skip) — nền đã được kiểm.
- [ ] `apps/studio/**` **không đổi 1 dòng nào** — `git -C apps/studio status` sạch.
- [ ] `src/studio_kb/search.py` + `pipeline.py` vẫn nguyên; `test_search_contract.py` xanh.
- [ ] `trace_reader.py` **không import `studio_app`** — `uv run lint-imports` xanh.
- [ ] Reader **báo thiếu node**, chứng minh bằng test cố ý bỏ 1 node (không chỉ test đường thuận).
- [ ] `ts` parse ra `datetime` rồi mới sắp; định dạng hỏng thì **raise**.
- [ ] Định nghĩa "0-gap" đã ghi vào `trace-event.v0.md`, không chốt miệng.
- [ ] Đã comment review PR SWE, **bắt ≥1 vấn đề thật** (DoD `:55`).
- [ ] Daily-note **D4** (nợ) + **D5** đều đã push; note D2 hết treo.
- [ ] Pre-commit `nda-denylist` đã cài ở `kb`.

---

## 5. Ngoài phạm vi hôm nay

Emit-trace hook (SWE) · populate `tokens`/`outputs` (AIE-1) · scorecard đọc trace (AIE-2) ·
cost-lineage 3-surface + `obs.costs` điền thật (**S3**) · RLS cho `obs.trace_events` (xem Q-B —
không phải việc DE, và không sửa được) · nối `PgKbSearch` vào `KbSearchService` (còn chờ quyết định
un-ratchet) · trace viewer UI (S2).

---

## 6. Đối chiếu DoD của brief (`day-05.md:52-57`)

| DoD | Ai gánh | DE liên quan thế nào |
|---|---|---|
| **Mọi node** của 1 run emit event | SWE + AIE-1 | **gián tiếp** — reader của tôi là thứ *kiểm chứng* điều đó; xem Q-D, hiện chuỗi đang đứt |
| Timeline đọc lại **đúng thứ tự + 0-gap** | **DE** | ✅ **D5-1 + D5-2** |
| Mỗi người review PR người khác, bắt ≥1 vấn đề thật | mọi vai | ✅ **D5-3** |
| Weekly demo #1 chạy thật (recording) | cả team | ✅ **D5-4** — slot DE là **teach-back KB pipeline** (ingest→chunk→embed→index + fence-data), không phải demo chung |
| **Daily-note D5** | mọi vai | ✅ **D5-5** (+ trả nợ note D4) |

---

## 7. Câu hỏi còn mở

| # | Hỏi ai | Nội dung | Nghiêng về |
|---|---|---|---|
| **Q-A** *(hỏi tối 23/07, không chờ để bắt đầu)* | **mentor** | `day-05.md:37` giao DE "bút trace **sink**", nhưng sink đã hoàn chỉnh ở `apps/studio` (`PgTraceWriter` + bảng 12 cột) mà DE chỉ READ. Phần dựng được của DE là **reader** — đúng không? | **đúng**: sink tiêu thụ cái đã có, DE bút **reader** đặt trong `packages/kb`. Làm theo hướng này luôn; sai thì **chuyển file**, không phải viết lại |
| **Q-B** | **mentor** | `obs.trace_events` có `tenant TEXT NOT NULL` (INV-1) nhưng **không có RLS, không có policy** — khác hẳn `kb.chunks` (ENABLE + FORCE + policy). `PgTraceWriter.write()` cũng không đặt `app.tenant_id`. Là **chủ ý** (trace là chức năng tin cậy của composition-root, không phải hành động của tenant) hay là sót? | **chủ ý** — nên chỉ cần xác nhận. Reader vẫn đọc theo `run_id`, mà một run thuộc đúng một tenant, nên không lọt chéo tenant **theo cấu trúc**. Không dựng máy móc phân quyền cho trace ở S1 |
| **Q-C** | **AIE-2** *(chuyển tiếp Q-A của D4, chưa đóng)* | Golden-set sống ở **file** `golden/smoke-5.yaml` hay **hàng** `eval.golden_sets`? Hôm nay `day-05.md:40` giao bạn "nạp smoke-5 vào demo" mà vẫn chưa có gì đọc file YAML | YAML là **nguồn gán nhãn** (DE giữ, review qua PR), bảng là **bản nạp vào** (AIE-2 seed từ YAML). Một chiều, không hai nguồn sự thật |
| **Q-D** *(chặn DoD `:53`)* | **AIE-1** | `NodeExecutor.execute(self, node)` **không nhận state**, và `interpreter.py:82` có `del trace_writer` — nên hiện chưa node nào emit được event, và `llm-step` cũng không thấy chunk mà `kb-retrieve` lấy về. Sửa signature Protocol (ảnh hưởng cả 6 executor) hay có đường khác? | đổi Protocol cho `execute` nhận state. Kèm luôn: `_CITATION_RE` ở `executors.py:20` không đọc được `#` trong `chunk_id` |
| **Q-F** *(báo, không phải hỏi)* | **mentor** | Bản brief D5 đang lưu hành ghi *"trace sink **SQLite**"*, trong khi `day-05.md` trong repo ghi **Postgres** ở 5 chỗ và `umbrella-contract` §4 đã chốt "Postgres-everything" từ `56da923`. Em bám file gốc theo `week-1/README.md:17`. Báo vì **3 bạn còn lại có thể đang đọc cùng bản cũ** — SWE gắn emit-hook và AIE-1 populate mà tưởng đích là SQLite thì mất cả ngày | file gốc thắng; nhờ mentor phát lại bản đã sửa cho cả nhóm |
| **Q-E** | **mentor** | Xin thêm `pyyaml` vào dev-group repo cha — chưa khai ở đâu, chỉ tình cờ có trong venv. Chặn loader (evalhub) + test kiểm hợp lệ golden-set (kb). Thêm dependency thì đụng `uv.lock` repo cha | thêm vào `[dependency-groups].dev` |

---

*Plan D5 — DE, 24/07/2026. Sửa lại khi mentor trả lời Q-A (chỗ đặt reader) và Q-B (RLS cho trace).*
