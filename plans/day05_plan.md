---
id: studio.de.day-05-plan
type: day-plan
status: draft
author: DE — Nguyễn Đông Anh
date: 2026-07-24
sprint: s1
day: 5
week_calendar: 1
revision: r2 — viết lại 24/07 sáng, sau khi mentor chốt ranh giới trace + sau khi pull `0920307`
title: "Kế hoạch Ngày 5 (T6 24/07) — DE: adopt D-13 → trace reader #21 (timeline in-order, 0-gap) + review chéo"
---

# KẾ HOẠCH NGÀY 5 — DE (KB pipeline + obs/eval data)
### Thứ Sáu 24/07 · Sprint 1 · **Integration/review day** · luật ngày: **ít build, nhiều ghép**

> Đây là **plan thi công**, chưa phải sản phẩm.
> Nguồn chuẩn: `docs/requirements/week-1/days/day-05.md` · bút DE
> (`docs/contracts/trace-event.v0.md`) · `umbrella-contract.md` §4 · `decisions-locked.md` D-13 ·
> `GITFLOWS.md` §2/§4 (bản 24/07).

---

## ⚠️ Đổi gì so với bản nháp r1 (viết tối 23/07)

Bản r1 viết trước khi mentor sửa code và trước khi chốt ranh giới. Ba thứ đã đổi:

| # | r1 nói | Hôm nay |
|---|---|---|
| 1 | Cảnh báo brief ghi *"sink **SQLite**"* → phải bám Postgres | ✅ **Hết hạn** — brief hiện hành đã ghi `obs.trace_events` Postgres. **Q-F đóng.** |
| 2 | Q-A *"việc của em là reader chứ không phải sink, đúng không?"* — tự quyết, không chờ | ✅ **Mentor chốt: đúng.** Reader = **#21**, sink không đụng. **Q-A đóng.** |
| 3 | Q-E xin `pyyaml` vào `[dependency-groups].dev` **repo cha** | ⚠️ **Sai chỗ.** Khai vào `pyproject.toml` **của package** trong PR; mentor regen `uv.lock` lúc merge. **Không phải blocker.** **Q-E đóng.** |
| 4 | Q-D kèm *"`_CITATION_RE` (`executors.py:20`) không đọc được `#` trong `chunk_id`"* | ✅ **Đã được sửa** — `executors.py:24` giờ là `re.compile(r"\[([\w#-]+)\]")`, **có `#`**. Bỏ khỏi Q-D, đừng báo lại |

Và một thứ r1 **không biết**, phát hiện sáng nay khi đối chiếu code sau pull:

> ## 🔴 `packages/kb` chưa adopt D-13 — **8 test đang đỏ ngay lúc này**
>
> ```
> $ uv run pytest packages/kb/tests -q
> 8 failed, 10 passed, 16 skipped
>
> ValidationError: 1 validation error for KbSearchResultItem
> tenant_id
>   Field required [type=missing, input_value={'chunk_id': 'ankor-expen...}]
> packages/kb/src/studio_kb/static_search.py:100
> ```
>
> Không cần Docker để tái hiện. Contracts đã bump `0.1.0 → 0.2.0-draft` theo **D-13**
> (`decisions-locked.md:27`): `tenant: str` → **`tenant_id: UUID`**. Contracts, workbench,
> `apps/studio` **đã adopt hết**; `kb` là quadrant **cuối cùng còn lại**. Đây chính là chữ
> *"forces adoption"* trong commit `ab1d306` pull về sáng nay.
>
> → Thành **D5-0**, làm đầu tiên. Chi tiết §1.

---

## 0. Ranh giới hôm nay — **mentor đã chốt, không còn phải đoán**

Brief vẫn ghi *"**Bút** trace sink Postgres (mọi node emit) + trace reader"*. Mentor 24/07:
chữ "sink" trong tiêu đề **#21 là dư — bỏ qua, tập trung reader**. Sink đã tồn tại và hoàn chỉnh
ở `apps/studio`, nơi DE chỉ READ.

| Mảnh | Chủ | Ở đâu | Issue |
|---|---|---|---|
| sink-writer (ghi `obs.trace_events`) | **đã có sẵn** | `apps/studio/src/studio_app/obs/trace_writer.py` | — **không đụng** |
| emit-hook (mỗi node → 1 event) | SWE | `packages/engine` / interpreter loop | **#23** |
| node populate `tokens`/`node_type`/`outputs` | AIE-1 | node executors | **#22** |
| **trace reader** (timeline in-order, 0-gap) | **DE — tôi** | `packages/kb` | **#21** |
| scorecard đọc trace lấy `citations` | AIE-2 | `packages/evalhub` | **#24** |

Trạng thái tầng trace (đã tra lại sau pull, đường dẫn r1 ghi thiếu `src/studio_app/`):

| thành phần | ở đâu | tình trạng |
|---|---|---|
| `TraceEvent` contract (12 field, `tenant_id: UUID`) | `studio_contracts/trace.py` | ✅ **bút DE, đã land** |
| Bảng `obs.trace_events` (12 cột, `tenant_id UUID NOT NULL`) | `apps/studio/src/studio_app/obs/schema.py:23` | ✅ mentor ship P4 |
| `PgTraceWriter.write()` — 1 câu INSERT | `apps/studio/src/studio_app/obs/trace_writer.py` | ✅ thân đầy đủ |
| `TraceWriter` Protocol | `studio_contracts/protocols.py` | ✅ |
| **reader — đọc lại timeline** | **không ở đâu cả** | ❌ **← #21, việc của tôi** |

**Kho ghi được hôm nay: chỉ `packages/kb/**` + `docs/reports/**`.**

| Việc | Trong scope DE? | Ghi chú |
|---|---|---|
| **Adopt D-13 ở `kb`** (**#25**) | ✅ | **deliverable**, mentor nói rõ "không phải bug" |
| **`trace` reader** (#21) | ✅ | deliverable chính |
| Review PR SWE (recipe shape), bắt ≥1 vấn đề thật | ✅ | **là DoD**, không phải việc phụ |
| Teach-back KB pipeline (weekly demo #1) | ✅ | DoD |
| Daily-note D5 | ✅ | DoD |
| Viết lại `PgTraceWriter` / sửa `obs/schema.py` | ❌ | `apps/studio` = mentor, DE chỉ READ |
| Gắn emit-trace hook vào interpreter | ❌ | SWE **#23** |
| Node-executor populate `tokens`/`outputs` | ❌ | AIE-1 **#22** |
| Scorecard đọc trace chấm citation | ❌ | AIE-2 **#24** |
| Cost-lineage 3-surface · `obs.costs` điền thật | ❌ | **S3** — cấm làm sớm |

> ⚠️ **Hôm nay là ngày review** (*"≥50% review, không cấp goal build mới"*). Reader cố ý nhỏ.
> D5-0 là **trả nợ**, không phải goal build mới — nó đưa `kb` về đúng contract mà cả đội đã chuyển.

---

## 1. Deliverable hôm nay

### D5-0 · Adopt D-13 — **issue #25**, deliverable chính thức (không phải "dọn dẹp")

> **Mentor 24/07:** *"Build kb D4 của bạn sẽ đỏ với contract mới — **đây là deliverable, không phải
> bug**."* Full mô tả ở **#25**.

**Vì sao gấp:** teach-back (DoD) của tôi đứng trên 5 bài `test_sc01..sc05` — **cả 5 đang đỏ**.
Không sửa thì không có gì để demo.

**Điều D-13 chốt** (`decisions-locked.md:27`): danh tính tenant là `core.tenants.id` **UUID bất
biến**, tên field trên dây = `tenant_id`, kiểu **UUID strict**. Cột DB (`kb.chunks` / `wb.recipes` /
`obs.trace_events`) + biến RLS `app.tenant_id` đều UUID; RLS cast `::uuid` bọc `NULLIF(...,'')`.

**🚦 Gate của #25 (mentor chốt):** `leak-test T1/T6` **+ empty-string** xanh ⇒ `leakage = 0`.
Đây là thước đo xong-hay-chưa, không phải "pytest không đỏ". Xem D5-0c.

**6 chỗ phải sửa trong `packages/kb`:**

| # | file | đang là | phải thành |
|---|---|---|---|
| 1 | `schema.py:31` | `tenant_id TEXT NOT NULL` | `tenant_id UUID NOT NULL` |
| 2 | `schema.py:46-48` policy | `tenant_id = current_setting('app.tenant_id', true)` | `tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid` |
| 3 | `static_search.py:100` | `tenant=chunk.tenant` | `tenant_id=...` |
| 4 | `postgres.py:188` | `tenant=row[3]` | `tenant_id=...` |
| 5 | `search.py:41` · `postgres.py:157` · `static_search.py` | `tenant: str` | `tenant_id: UUID` |
| 6 | `postgres.py:95` `_bind_tenant` | truyền slug vào `set_config` | truyền UUID (str của UUID) |

> **Fail-closed vẫn giữ nguyên sau khi cast** — kiểm lại lập luận, đừng tin suông:
> `current_setting(..., true)` chưa set → `NULL`; `NULLIF(NULL,'')` → `NULL`; `NULL::uuid` → `NULL`;
> `tenant_id = NULL` không bao giờ đúng → phiên chưa set vẫn thấy **0 dòng**. Docstring đầu
> `schema.py` giải thích cơ chế này — **sửa docstring theo**, đừng để nó mô tả bản cũ.
>
> `NULLIF` có mặt vì lý do riêng: `current_setting` trả **chuỗi rỗng** (không phải NULL) trong vài
> đường đặt biến; `''::uuid` thì **raise**, không fail-closed. Bọc `NULLIF` biến nó về `NULL`.
> Mentor gọi đây là **"fail-closed edge"** và đặt nó thành một phần của gate — xem D5-0c.

✅ **Câu SQL trên là mentor phát nguyên văn trong #25** — không phải tôi tự suy, cứ copy thẳng:

```sql
USING      (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
```

**Quyết định cần chốt — `Chunk.tenant` (`doc_factory.py:52`):** đây là kiểu **nội bộ kb**, D-13 không
bắt. Nhưng để `Chunk.tenant` là slug cạnh `KbSearchResultItem.tenant_id` là UUID thì `postgres.py:123`
(`by_tenant[chunk.tenant]`) thành chỗ trộn hai vũ trụ. **Nghiêng về: đổi luôn thành `tenant_id: UUID`.**

> ⚠️ **Đây là chỗ dễ sa lầy nhất buổi sáng — giới hạn phạm vi trước khi bắt đầu.** `doc_factory` dựng
> `Chunk` từ markdown, nơi tenant là **slug** ("ankor"); mà `kb` **không được import `core.tenants`**
> để resolve (`.importlinter` chặn, và đó là bảng của `apps/studio`). Nên:
> - **Hôm nay:** dùng UUID **fixture** (`ANKOR_ID`/`BOREA_ID`) ở tầng test + ingest. Đủ để suite xanh.
> - **Không phải hôm nay:** resolve slug→UUID thật lúc ingest. Đó là câu hỏi thiết kế riêng (ai gọi
>   `core.tenants`? middleware đã làm cho request-path, còn ingest-path thì chưa ai) — **mở thành
>   Q-G, đừng giải trong PR này.**
>
> Mentor #25 nói *"`doc_factory.py` … **key theo UUID (không so slug thẳng)**"* → xác nhận hướng đổi
> kiểu, nhưng **không nói UUID từ đâu ra lúc ingest**. Nên Q-G vẫn mở; hôm nay dùng fixture.

**Test:** copy hằng số của SWE để cả repo cùng một giá trị —
`ANKOR_ID = UUID("a0000000-0000-0000-0000-000000000001")` (`workbench/src/studio_workbench/builder_d4.py:22`).
Cần thêm `BOREA_ID` cho ca chéo tenant.

> ✅ **D-13 GIỮ NGUYÊN slug làm nhãn hiển thị** — `expected_tenant` trong golden-set và prefix
> `chunk_id` **không đổi**. Slug-check bên evalhub là sanity thứ cấp. **Không viết lại
> `golden/smoke-5.yaml`.** Đây là chỗ dễ dọn quá tay nhất.

---

#### D5-0b · Migration DB — **phải xoá volume, không migrate tại chỗ được**

Mentor cảnh báo đích danh: DDL là `CREATE TABLE IF NOT EXISTS` + volume Docker **bền**, nên đổi cột
`TEXT → UUID` trên DB cũ sẽ lỗi:

```
operator does not exist: text = uuid
```

Bảng cũ vẫn còn nguyên `tenant_id TEXT`, DDL mới **không chạy lại** (đã tồn tại), policy mới cast
`::uuid` đem so với cột TEXT → nổ. Cách xử lý mentor chốt:

```bash
docker compose -f docker-compose.test.yml down -v     # -v = xoá volume, đây mới là chỗ quan trọng
make dev
```

> **An toàn vì dữ liệu KB là synthetic, tái tạo được** (5 file `.md` ở `docs/callisto/` → 25 chunk).
> Không có gì để mất. Nhưng nhớ `-v` — `down` không có `-v` là volume còn nguyên, và triệu chứng sẽ
> là "sửa đúng hết rồi mà vẫn lỗi y như cũ".

---

#### D5-0c · Gate `leakage = 0` — **chỗ có 2 cái bẫy, đọc kỹ**

Mentor chốt gate: **`leak-test T1/T6` + `empty-string` xanh**. Nhưng `tests/test_leak.py` hiện tại
**không chạy nổi** dưới D-13, và đường tới "xanh" có hai chỗ vướng không hiển nhiên.

**Bẫy 1 — `test_leak.py` đang dùng slug, mà slug không phải UUID hợp lệ.**

```python
await _seed_chunk(admin_pool, "tenant-a", ...)          # INSERT vào cột UUID → invalid input syntax
SET LOCAL app.tenant_id = 'tenant-a'                     # policy cast ::uuid → nổ
service.search(..., tenant="tenant-a", ...)              # kwarg cũ
assert all(item.tenant == "tenant-a" for item in results)  # field cũ
```

`"tenant-a"` / `"tenant-b"` **không parse được thành UUID** (khác `ANKOR_ID`). Phải đổi hết sang
UUID fixture, kể cả `_seed_chunk(tenant_id: str)`.

**Bẫy 2 — `test_leak_meta.py` là anti-tamper, nó SẼ nổ khi tôi sửa đúng.**

Meta-test grep **nguyên văn chuỗi** trong source của `test_leak.py`:

```python
assert 'assert all(item.tenant == "tenant-a" for item in results)' in source
```

Sửa `item.tenant` → `item.tenant_id` là dòng này **không còn khớp** → meta-test đỏ. Đây là hàng rào
chống *"lặng lẽ rút ruột leak-test để giả xanh"* — và nó không phân biệt được tôi với người rút ruột.

> ⚠️ **Phải sửa `test_leak_meta.py` cùng commit với `test_leak.py`, và GIẢI THÍCH RÕ TRONG PR.**
> Nếu không, người review (mentor) nhìn thấy đúng cái hình dạng mà meta-test sinh ra để bắt: sửa
> leak-test rồi sửa luôn cái đang canh leak-test. Viết thẳng trong mô tả PR: *"đổi theo D-13 #25,
> assertion giữ nguyên **răng**, chỉ đổi tên field + kiểu giá trị"* — và giữ đúng số lượng assertion.

**Bẫy 3 — bài `empty-string` chưa tồn tại, phải viết mới.**

Đây là bài chứng minh `NULLIF(...,'')` làm đúng việc:

| đặt `app.tenant_id` | kỳ vọng |
|---|---|
| `''` (chuỗi rỗng) | **0 dòng**, KHÔNG raise ← bài mới, chính là "empty-string" mentor nhắc |
| chưa set | 0 dòng (`current_setting(...,true)` → NULL) |
| UUID khác | 0 dòng |
| UUID đúng | ra chunk của mình |

Không có `NULLIF` thì ô đầu **raise** `invalid input syntax for type uuid: ""` — vỡ to tiếng, nhưng
vỡ **sai kiểu**: fence phải trả rỗng, không phải ném lỗi 500 vào mặt người dùng.

**Xong là:** `uv run pytest packages/kb/tests -q` → **0 failed**, và T1/T6 + empty-string xanh thật
(xem Q-H về chuyện "xanh thật" nghĩa là gì).

---

### D5-1 · Dựng Postgres chạy được — nền cho cả `kb.chunks` lẫn `obs.trace_events`

Tầng Postgres viết ở D4 (`postgres.py`, 10 test) **chưa từng chạy một câu SQL nào** — Docker tắt,
test skip. Cùng một hạ tầng đỡ cả hai bảng; hỏng ở đâu thì hỏng cả hai.

```bash
docker compose -f docker-compose.test.yml up -d        # pgvector/pgvector:pg17, cổng 5433
export STUDIO_DATABASE_URL_ADMIN='postgresql://postgres:postgres@localhost:5433/studio_test'
export STUDIO_DATABASE_URL='postgresql://studio_app:...@localhost:5433/studio_test'
uv run pytest packages/kb/tests -q                     # 16 skipped phải chuyển thành xanh
```

> ⚠️ **Dự đoán, chưa kiểm chứng được:** `postgres.py:188` mang **đúng lỗi** đã làm đỏ
> `static_search.py:100`. Nên 16 bài skipped nhiều khả năng đỏ khi Docker bật lên — trừ phi D5-0 đã
> sửa. Đó là lý do D5-0 đứng **trước** mục này, không phải sau.
>
> Chuyện volume/`down -v` đã chuyển lên **D5-0b** — làm ở đó, không phải ở đây.

**Xong là:** toàn bộ suite `kb` xanh thật, không còn skip.

> `studio_app` có SELECT trên `obs.*` (`core/schema.py` `ALL_SCHEMAS` gồm `obs`, `grant_app_privileges`
> cấp đủ 5 schema). Reader đọc qua **app-pool**, không cần admin-pool.

---

### D5-2 · `trace` reader (#21) — deliverable chính

Đặt ở `src/studio_kb/trace_reader.py`. Đọc `obs.trace_events` bằng SQL thô, chỉ import `TraceEvent`
(contracts) + pool — **không** import `studio_app`, y hệt cách `PgKbSearch` đọc `kb.chunks`.
`.importlinter` cho phép; không phải lách luật.

> **Chỗ đặt file:** mentor đã xác nhận reader là việc DE (#21) và kho ghi được của DE là
> `packages/kb`. Q-A đóng.

Ba việc:

| # | việc | neo DoD |
|---|---|---|
| 1 | `read_run(run_id, tenant_id: UUID) -> list[TraceEvent]`, xếp theo `ts` tăng dần | "đúng thứ tự" |
| 2 | `render_timeline(events) -> str` — in ra người đọc được | "reader in timeline" |
| 3 | **phát hiện gap** — thiếu node so với chuỗi kỳ vọng | "0-gap" |

**`tenant_id` là UUID, không phải slug** *(mentor nhắc riêng 24/07)*. Cột là `UUID NOT NULL`
(`obs/schema.py:23`). Truyền `"ankor"` vào → psycopg raise `invalid input syntax for type uuid`.
May là **vỡ to tiếng**, không âm thầm — nhưng vẫn phải nhận UUID ở chữ ký, không phải `str`.
Nguồn UUID: `core.tenants` (`id UUID PK`, `name TEXT UNIQUE`), middleware resolve slug→UUID.

**"0-gap" nghĩa là gì phải chốt bằng chữ trước khi code.** Hai cách hiểu:

- **thời gian liên tục** — không khoảng trống giữa các `ts`. Vô nghĩa: node chạy nhanh chậm khác nhau.
- **không sót node** — mỗi node trong DAG của run phải có đúng 1 event.

Chọn cách hai; DoD nói thẳng *"**Mọi node** của 1 run emit event (**không sót node**)"*. Reader so
**tập node đã emit** với **chuỗi node kỳ vọng**, báo cái thiếu. Ghi định nghĩa này vào
`trace-event.v0.md` — không chốt miệng, đúng bài học D4.

**Về `ts`:** cột là `TEXT` chứa ISO-8601 (`obs/schema.py`). `ORDER BY ts` là **so chuỗi**, chỉ đúng
khi mọi timestamp cùng định dạng và cùng độ dài (có `Z`, có micro-giây). Lệch định dạng giữa các node
là thứ tự sai **im lặng**. Reader phải parse ra `datetime` rồi mới sắp, và **raise khi parse hỏng**
thay vì lặng lẽ giữ nguyên thứ tự đọc từ DB.

> ⚠️ **Không assert `ts` tăng nghiêm ngặt.** Hai node chạy cùng mili-giây có thể trùng `ts`. Dùng
> `ts` để **sắp**, dùng **tập node** để kiểm **0-gap** — đừng trộn hai việc.

**Xong là:** cho một `run_id` + `tenant_id`, in ra timeline có thứ tự và nói được "đủ node" hay
"thiếu node nào".

---

### D5-3 · Test reader — **không chờ #22/#23**

Chỗ gỡ rủi ro lớn nhất của ngày: reader **không phụ thuộc** emit-hook (SWE #23) hay populate
(AIE-1 #22). Tự ghi event bằng `PgTraceWriter` đã có sẵn, rồi đọc lại.

| test | chứng minh |
|---|---|
| ghi 4 event xáo trộn thứ tự → đọc ra **đúng thứ tự `ts`** | in-order |
| cố ý bỏ 1 node → reader **báo thiếu**, không im lặng | 0-gap — bài có răng |
| hai `run_id` xen kẽ → đọc run A **không lẫn** event của run B | cách ly run |
| `ts` sai định dạng → **raise**, không sắp bừa | bẫy so chuỗi ở trên |
| `run_id` không tồn tại → trả `[]`, không raise | rỗng là hợp lệ |
| truyền slug thay UUID → **vỡ rõ ràng**, không trả nhầm | D-13 |

Bài thứ hai quan trọng nhất: một reader chỉ biết in ra thì **luôn trông như thành công**. Phải có
bài mà nó bắt buộc phải kêu.

---

### D5-4 · Review PR của SWE (recipe shape) — **DoD, không phải việc phụ**

Yêu cầu là **bắt ≥1 vấn đề thật** — không phải "LGTM".

Chỗ đáng soi nhất, dựa trên thứ đã đụng ở D4:

- `recipe.kb_binding.{kb_id, scope}` — `scope` có mang **cả `tenant_id` lẫn `section_roles`** không?
  Thiếu vế vai thì T6 không có đường đi từ recipe xuống `kb.search`.
- **`scope.tenant_id` đã là UUID chưa** hay còn slug? SWE đã adopt D-13 ở `builder_d4.py` — nhưng
  `kb_binding.scope` là chỗ dễ sót nhất vì nó nằm trong `dict`, pydantic không gác.
- Từ vựng `section_role` bên SWE có khớp `{public, hr, finance, engineering}` không — họ là bên
  phân giải role server-side (câu hỏi này **vẫn chưa ai trả lời**).
- `public` có được cấp **ngầm** không? Nếu không, mọi request phải tự nhớ kèm `public`, quên là người
  dùng mất quyền đọc tài liệu chung — triệu chứng là "tìm không ra", không phải báo lỗi.
- 🎯 **Vấn đề thật đã tìm được, đủ tiêu chuẩn DoD — recipe mang HAI danh tính tenant.**
  `builder_d4.py` tách `kb_binding.scope` (`"ankor/public"`) ra rồi nạp **slug** `"ankor"` vào
  `node.params["tenant"]`, trong khi `recipe.tenant_id` là **UUID** và **không ai luồn nó xuống
  node**. Hàng rào `kb.search` dùng cái slug — đúng thứ D-13 sinh ra để loại bỏ (*"slug/tên trùng
  được"*). Không có chỗ nào kiểm hai giá trị này khớp nhau. Kèm: `section_roles` tách bằng `,` bên
  trong chuỗi phân cách bằng `/` → role chứa `/` hoặc `,` hỏng im lặng.
  **Kèm hệ quả phải báo:** #25 của tôi sẽ **làm gãy `builder_d4.py`** (`WHERE tenant_id = %s` nhận
  slug → `invalid input syntax for type uuid`). Báo SWE **trước** khi merge #25.
- ~~`golden_set_ref` trỏ `"golden-set-d4-callisto"`~~ — **hết đúng**, SWE đã sửa thành
  `"callisto-smoke-5-v0"`. Bỏ khỏi danh sách review.

---

### D5-5 · Teach-back weekly demo #1 — KB pipeline (ingest→chunk→embed→index + fence-data)

Slot demo của DE là **teach-back KB pipeline**, không phải demo chung. Đây là phần dễ bị bỏ tới phút
chót nhất, mà lại là ô DoD.

**Trạng thái thật hôm nay — nói đúng cái đang có, đừng nói cái đáng lẽ có:**

| bước | thực tế | bằng chứng chạy được |
|---|---|---|
| **ingest** | `doc_factory` đọc 5 `.md` ở `docs/callisto/` | ✅ chạy thật |
| **chunk** | cắt theo heading `##` · `chunk_id = {doc_id}#c{n}` · 25 chunk | ✅ 7 test xanh |
| **embed** | **chưa có embedding thật ở bất kỳ đâu trong workspace** — chỉ `FakeEmbedding` (SHA256, 8 chiều) | ⚠️ **phải nói thẳng** |
| **index** | `KbIngest` → `kb.chunks`, `ON CONFLICT DO UPDATE` giữ `chunk_id` | ⚠️ viết rồi, chưa chạy → **D5-1** |
| **fence-data** | `StaticKbSearch` lọc 2 trục; `PgKbSearch` lọc trong SQL + RLS | 🔴 **đang đỏ → D5-0** |

> **Ba trong năm bước hiện chưa chứng minh được, và một bước đang ĐỎ.** Đó là lý do D5-0 + D5-1
> không phải việc dọn dẹp tuỳ chọn — chúng quyết định teach-back là *"đây, chạy đây"* hay *"em viết
> rồi nhưng chưa chạy"*. **Làm buổi sáng.**

**Ba điểm nên nói, vì chúng là *quyết định* chứ không phải *tính năng*** — teach-back chấm ở chỗ hiểu
vì sao, không phải liệt kê được gì:

1. **Vì sao `chunk_id` là chữ có quy luật, không phải UUID.** `re_index` ở S3 bắt giữ nguyên
   `chunk_id`; UUID ngẫu nhiên thì mỗi lần index lại là golden-set chết sạch. Kèm cái giá: chèn
   heading vào **giữa** doc là đánh số lại phía sau.
   *(Đối chiếu thú vị với D-13: `chunk_id` cố ý **không** UUID, `tenant_id` cố ý **phải** UUID —
   hai quyết định ngược nhau, cùng một lý do: cái nào cần bền qua re-index thì không được ngẫu nhiên,
   cái nào cần không trùng được thì không được để người đặt tên.)*
2. **Vì sao fence phải ở tầng truy xuất.** Hàng rào có **hai trục**, chỉ một trục có lưới: RLS khoá
   `tenant_id`, còn `section_role` **không có policy nào** — chặn hoàn toàn bằng `WHERE`. Mất mệnh
   đề đó là hở T6, im lặng.
3. **Vì sao `StaticKbSearch` không phải hình nộm.** Phân biệt với `EmptyKbSearch` (luôn trả `[]`):
   bản của tôi tìm thật, lọc thật — hỏi từ Ankor ra "3 ngày", từ Borea ra "7 ngày", hỏi thang lương
   bằng vai `engineering` ra **rỗng**. ← **cần D5-0 xong mới demo được.**

**Xong là:** chạy được một mạch trước mặt người khác, và trả lời được "vì sao" cho cả ba, không đọc slide.

---

### D5-6 · Daily-note D5 + trả nợ D4

`docs/reports/daily-notes/2026-07-24-DongAnh2704.md`.

**Nợ mang sang, dọn buổi sáng:**
- **daily-note D4 chưa viết** — viết bù cùng lúc, đừng gộp vào note D5.
- `2026-07-21-DongAnh2704.md` **vẫn sửa dở chưa commit** trong `docs/reports` — treo từ D3.
- `2026-07-23-DongAnh2704.md` untracked — chưa vào git.
- **Pre-commit NDA-denylist chưa cài ở `kb`** (GITFLOWS §9.3 bắt mọi repo). Thư mục hook rỗng.
  Script ở `docs/requirements/nda-denylist.sh`. 5 phút. **Giờ càng gấp: repo đã PUBLIC từ 24/07.**
- `plans/day02_plan.md` còn mô tả **SQLite** như lựa chọn mở. `umbrella-contract.md` §4 đã chốt
  "Postgres-everything từ S1". Đánh dấu Q5 đã đóng.
- `docs/contracts/kb-search.v0.md` — bảng chữ ký §3.1 ghi `tenant`, phải đổi theo D-13. Đi cùng PR D5-0.

---

## 2. Thứ tự thực thi (timebox)

| Slot | Việc | Ra cái gì | TT |
|---|---|---|---|
| **Sáng 0 (10', ngay khi mở máy)** | **Ping AIE-1 về Q-D** (`execute()` chưa nhận state → chưa node nào emit được, DoD #1 chết) **+ hỏi mentor Q-H** (gate #25 có gồm un-ratchet không) | hai người kia không bị chặn; tôi biết D5-0 to hay nhỏ | ⬜ |
| **Sáng 1 (90–120')** | **D5-0** adopt D-13 **#25** — 6 chỗ + `down -v` + `test_leak.py`/`test_leak_meta.py` + bài empty-string | `pytest kb` **0 failed**, gate `leakage=0` | ⬜ |
| Sáng 2 (30') | **D5-1** dựng Docker, 16 bài skipped chuyển xanh | nền Postgres xanh thật | ⬜ |
| Sáng 3 (20') | **D5-6** trả nợ: note D4, note D2, pre-commit NDA, Q5 | hết treo artifact | ⬜ |
| Trưa | **D5-2** reader + chốt "0-gap" bằng chữ | `trace_reader.py` | ⬜ |
| Chiều 1 | **D5-3** test reader (6 bài) | DoD in-order + 0-gap | ⬜ |
| **Chiều 2 (lịch cứng)** | **D5-4** review PR SWE | comment bắt ≥1 vấn đề thật (**DoD**) | ⬜ |
| Chiều 3 (30' tập trước) | **D5-5** teach-back — chạy thử một mạch, không đọc slide | recording (**DoD**) | ⬜ |
| Cuối ngày | **D5-6** daily-note D5, push | DoD | ⬜ |

> **Sáng 0 đứng trước cả D5-0** vì nó không tốn thời gian của tôi mà lại mở khoá cho người khác.
> DoD #1 (*"mọi node emit event"*) **không nằm trong tay tôi** — nó phụ thuộc #22/#23, mà cả hai đang
> chặn ở Q-D. Reader của tôi có hoàn hảo thì DoD đó vẫn trượt nếu AIE-1 chưa đổi `execute()`. Báo
> lúc 9h thì còn cứu được; báo lúc 3h chiều thì không.
>
> **D5-0 lên đầu** trong phần việc của tôi vì nó gate teach-back (D5-5) — mà teach-back có recording,
> không dời được sang mai.
> Nó cũng là việc **cơ học**: SWE đã đi đúng con đường này ở D4, copy pattern của họ, đừng thiết kế lại.
>
> D5-1 ngay sau vì mọi thứ còn lại là Postgres. Phát hiện hạ tầng hỏng lúc 3h chiều thì mất cả ngày.
>
> D5-4 **lịch cứng**, không để "làm nốt nếu còn giờ": review là DoD, và PR của SWE có sớm thì họ cũng
> cần thời gian sửa theo comment trước demo.

---

## 3. Luồng git — **mô hình mới từ 24/07 (repo đã PUBLIC)**

`GITFLOWS.md` đã đổi: 8 repo studio **public**, org `AI20K-VGR`. Mọi TTS có **write ở mọi repo**;
`main` được **GitHub bảo vệ server-side** (PR + ≥1 review + CODEOWNERS). Ownership giờ ở tầng
**review**, không phải tầng push.

**Ảnh hưởng trực tiếp tới tôi:**
- `CODEOWNERS` của `kb` = `@DongAnh2704 @hieubui2409` → **tôi là người gác cổng `kb`**, phải theo
  dõi tab Pull requests.
- **PR của chính tôi vào `kb` cần mentor duyệt** — không tự-approve được. Mở PR sớm, ping mentor sớm.
- D4 tôi push thẳng `main`, `kb` có **0 PR** trong khi `engine` đã 3 PR merged. Hôm nay bắt đầu đi PR.

```bash
cd packages/kb
git checkout main && git pull
git checkout -b day5/d13-adopt-and-trace-reader
# ... D5-0 → D5-3 ...
git push -u origin day5/d13-adopt-and-trace-reader
gh pr create --fill --base main
```

> ⚠️ **`gh` chưa cài trên máy này** (`command -v gh` → không có). Cài trước khi tới bước PR:
> `brew install gh && gh auth login`. Hoặc dùng link PR mà `git push` in ra.

**Cân nhắc tách 2 PR?** D5-0 (adopt D-13) và #21 (reader) là hai việc độc lập. Tách ra thì mentor
review nhanh hơn và D5-0 merge sớm để không chặn ai. **Nghiêng về tách**, trừ phi muốn giảm số lần
chờ duyệt.

`pyyaml` (nếu chạm loader hôm nay): khai vào `packages/kb/pyproject.toml` **ngay trong PR** — mentor
regen `uv.lock` lúc merge. **Không phải blocker, cứ mở PR bình thường.**

Test chạy **từ repo cha**:
```bash
cd /Users/nguyendonganh/agentcore-studio-kit
uv run pytest packages/kb/tests -q
make lint
```

---

## 4. Tự kiểm trước khi push

- [ ] Đang trên **nhánh** `day5/...`, không phải `main`, không detached.
- [ ] `uv run pytest packages/kb/tests -q` → **0 failed, 0 skipped** (Docker đang chạy).
- [ ] `kb.chunks.tenant_id` là **UUID**; policy có `::uuid` bọc `NULLIF(...,'')`; docstring `schema.py` đã sửa theo.
- [ ] Đã `docker compose ... down -v` (**có `-v`**) rồi `make dev` — không migrate tại chỗ.
- [ ] `test_leak.py` dùng **UUID fixture**, không còn `"tenant-a"`/`"tenant-b"`.
- [ ] `test_leak_meta.py` đã sửa **cùng commit**, và **PR có giải thích vì sao** (anti-tamper sẽ trông như bị rút ruột).
- [ ] Số lượng assertion trong `test_leak.py` **không giảm** — đổi tên field, không bớt răng.
- [ ] Bài **empty-string** (`app.tenant_id = ''`) → trả **0 dòng**, KHÔNG raise.
- [ ] Gate `leakage = 0`: T1 + T6 + empty-string xanh (theo nghĩa Q-H đã chốt).
- [ ] **Không** đụng `golden/smoke-5.yaml` — `expected_tenant` slug là nhãn hiển thị, D-13 giữ nguyên.
- [ ] `apps/studio/**` **không đổi 1 dòng** — `git -C apps/studio status` sạch.
- [ ] `trace_reader.py` **không import `studio_app`** — `uv run lint-imports` xanh.
- [ ] Reader nhận `tenant_id: UUID` ở chữ ký, không phải `str`.
- [ ] Reader **báo thiếu node**, chứng minh bằng test cố ý bỏ 1 node (không chỉ test đường thuận).
- [ ] `ts` parse ra `datetime` rồi mới sắp; định dạng hỏng thì **raise**.
- [ ] Định nghĩa "0-gap" đã ghi vào `trace-event.v0.md`, không chốt miệng.
- [ ] `kb-search.v0.md` §3.1 đã đổi `tenant` → `tenant_id: UUID`.
- [ ] Đã comment review PR SWE, **bắt ≥1 vấn đề thật**.
- [ ] Daily-note **D4** (nợ) + **D5** đều đã push; note D2/D3 hết treo.
- [ ] Pre-commit `nda-denylist` đã cài ở `kb` (repo public rồi).

---

## 5. Ngoài phạm vi hôm nay

Emit-trace hook (SWE **#23**) · populate `tokens`/`outputs` (AIE-1 **#22**) · scorecard đọc trace
(AIE-2 **#24**) · cost-lineage 3-surface + `obs.costs` điền thật (**S3**) · RLS cho
`obs.trace_events` (Q-B — không phải việc DE, và không sửa được) · trace viewer UI (S2).

> ⚠️ **Nối `PgKbSearch` vào `KbSearchService` + gỡ `xfail` (un-ratchet F5)** — trước đây nằm chắc ở
> đây. Gate #25 (*"leak-test T1/T6 xanh"*) **có thể kéo nó vào scope**. **Q-H phải trả lời trước khi
> tôi bắt đầu code**, vì nó quyết định D5-0 là 90 phút hay cả buổi sáng.

---

## 6. Đối chiếu DoD của brief

| DoD | Ai gánh | DE liên quan thế nào |
|---|---|---|
| **Mọi node** của 1 run emit event (không sót node) | SWE **#23** + AIE-1 **#22** | **gián tiếp** — reader của tôi là thứ *kiểm chứng* điều đó; xem Q-D, hiện chuỗi đang đứt |
| Timeline đọc lại **đúng thứ tự + 0-gap** | **DE #21** | ✅ **D5-2 + D5-3** |
| Mỗi người review PR người khác, bắt ≥1 vấn đề thật | mọi vai | ✅ **D5-4** |
| Weekly demo #1 chạy thật (recording) | cả team | ✅ **D5-5** — slot DE là **teach-back KB pipeline**; 🔴 **gate bởi D5-0** |
| **Daily-note D5** | mọi vai | ✅ **D5-6** (+ trả nợ note D4) |

---

## 7. Câu hỏi còn mở

| # | Hỏi ai | Nội dung | Trạng thái |
|---|---|---|---|
| **Q-A** | mentor | Việc DE là **reader** chứ không phải viết sink? | ✅ **ĐÓNG 24/07** — mentor chốt: reader (**#21**), sink không đụng. Chữ "sink" ở tiêu đề #21 là dư |
| **Q-E** | mentor | `pyyaml` khai ở đâu | ✅ **ĐÓNG 24/07** — vào `pyproject.toml` **của package**, trong PR; mentor regen `uv.lock` lúc merge. Không phải blocker |
| **Q-F** | mentor | Brief lưu hành ghi "sink SQLite" trong khi repo ghi Postgres | ✅ **ĐÓNG** — brief hiện hành đã ghi `obs.trace_events` Postgres |
| **Q-B** | mentor | `obs.trace_events` có `tenant_id UUID NOT NULL` nhưng **không RLS, không policy** — khác hẳn `kb.chunks` (ENABLE + FORCE + policy). `PgTraceWriter.write()` cũng không đặt `app.tenant_id`. Chủ ý hay sót? *(r1 ghi cột là `tenant TEXT` — sai, đã sửa)* | 🟡 **mở** — nghiêng **chủ ý**: trace là chức năng tin cậy của composition-root, không phải hành động của tenant. Reader đọc theo `run_id`, một run thuộc đúng một tenant → không lọt chéo **theo cấu trúc**. Chỉ cần xác nhận |
| **Q-C** | AIE-2 | Golden-set sống ở **file** `golden/smoke-5.yaml` hay **hàng** `eval.golden_sets`? | 🟡 **mở** *(chuyển tiếp từ D4)* — nghiêng: YAML là **nguồn gán nhãn** (DE giữ, review qua PR), bảng là **bản nạp vào** (AIE-2 seed từ YAML). Một chiều, không hai nguồn sự thật |
| **Q-H** *(mới — CHẶN, hỏi cùng lúc với Sáng 0)* | **mentor** | Gate #25 là *"leak-test T1/T6 xanh"*. Nhưng T1/T6 gọi `KbSearchService.search`, mà hàm đó vẫn `raise NotImplementedError` (`search.py:48`), và cả hai bài đang `@pytest.mark.xfail(strict=False)` — **suite xanh dù test đỏ hay xanh**, đúng cái "xanh giả" mà docstring `test_leak.py` cảnh báo. Nên gate chỉ có nghĩa nếu **gỡ `xfail` (un-ratchet F5) + hiện thực `KbSearchService.search`**. #25 có bao gồm việc đó không, hay chỉ cần đổi kiểu và để ratchet nguyên? | 🔴 **mở — quyết định độ lớn của ngày.** Nghiêng: **#25 chỉ là đổi kiểu**; un-ratchet là việc riêng vì nó đòi nối `PgKbSearch` vào `KbSearchService` (quyết định kiến trúc, không phải migration). Nhưng nếu mentor muốn gate theo nghĩa đen thì D5-0 phình gấp đôi — **phải hỏi trước khi code, không đoán** |
| **Q-G** *(mới, sinh ra từ D5-0)* | mentor / AIE-1 | Ingest-path resolve slug→UUID ở đâu? `middleware._resolve_tenant_id` lo request-path qua `core.tenants`, nhưng `doc_factory` dựng `Chunk` từ markdown mang slug, mà `kb` **không được import `core.tenants`**. Hôm nay dùng UUID fixture; đường thật chưa có ai | 🟡 **mở** — nghiêng: ingest nhận `tenant_id: UUID` **từ caller** (composition-root resolve sẵn), `kb` không tự tra bảng. Giữ `kb` không biết gì về `core.*` |
| **Q-D** | AIE-1 | `NodeExecutor.execute(self, node: Node)` (`engine/executors.py:32`) **không nhận state**, và `interpreter.py:82` có `del trace_writer` — nên hiện **chưa node nào emit được event**. Sửa signature Protocol (ảnh hưởng 6 executor) hay có đường khác? | 🔴 **mở — chặn DoD #1** (#22/#23). Nghiêng: đổi Protocol cho `execute` nhận state. **Protocol này nằm trong `packages/engine`, KHÔNG phải `studio_contracts`** → là quyết định nội bộ của AIE-1, không cần mentor duyệt theo D-12, không bump `SCHEMA_VERSION`. Rào cản thấp hơn tôi tưởng ở r1 |

---

*Plan D5 **r2** — DE, 24/07/2026 sáng. Viết lại sau khi mentor chốt ranh giới trace (#21–#24) và sau
khi phát hiện `kb` chưa adopt D-13. Bản r1 giữ ở `plans/day05_plan.r1.md` (chưa từng commit, nên
không có trong git history — đó là lý do phải lưu thành file riêng).*
