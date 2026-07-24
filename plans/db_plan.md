---
id: studio.de.db-standalone-plan
type: goal-plan
status: draft
author: DE — Nguyễn Đông Anh
date: 2026-07-23
sprint: s1
title: "Postgres độc lập đạt chuẩn đề bài — hàng rào tenant toàn cơ sở dữ liệu"
scope: standalone
wired: false
pushed: false
---

# KẾ HOẠCH — POSTGRES ĐỘC LẬP ĐẠT CHUẨN ĐỀ BÀI
### Không gắn ngày · chạy song song · **KHÔNG nối vào hệ thống · KHÔNG push**

> Plan này **không theo nhịp ngày**. Nó có đúng một mục tiêu: dựng một Postgres mà **hàng rào
> tenant đứng vững ở mọi bảng**, đo được bằng test, không phải bằng lời.
>
> Đây là **sân tập song song**. Không sửa đường chạy nào đang sống, không đụng composition, không
> push. Khi nào có thứ đáng đưa vào hệ thật thì tách ra thành PR riêng — đó là quyết định sau, không
> phải hệ quả của plan này.

---

## 0. Mục tiêu và ranh giới

### 0.1 Mục tiêu đo được

Đề bài có **một luật cứng** xuyên suốt, không phải "tính năng thêm" — `decisions-locked.md` D-11 và
`umbrella-contract.md` §INV-1/DEC-E9:

> Permission filter nằm **TẠI RETRIEVAL** (chunk-level, cột `tenant_id`/`section_role` NOT NULL +
> mandatory filter fail-closed). Leak-test **T1 IDOR** + **T6 label-spoof** xanh CI; **leakage = 0**
> là AC cứng.

→ **Mục tiêu:** mọi bảng mang dữ liệu của tenant đều **chặn được T1 và T6**, chứng minh bằng test
**XANH THẬT** (không `xfail`), chạy qua kết nối **non-owner**, trên **một** instance Postgres dựng
bằng một lệnh.

### 0.2 Ranh giới sở hữu — **quan trọng nhất, đọc trước khi gõ dòng nào**

DDL của **4 trong 5 schema nằm ở repo người khác**. Không phân biệt được ba nhóm dưới đây thì plan
này biến thành "DE âm thầm viết lại schema của cả đội":

| nhóm | phạm vi | cách làm |
|---|---|---|
| **A. Lắp, KHÔNG viết lại** | `core` · `obs` (mentor) · `wb` (SWE) · `eval` (AIE-2) | Gọi **`ddl()` có sẵn** của từng quadrant qua `ensure_all_schemas()`. **Tuyệt đối không** chép tay DDL song song — sandbox lệch cột với thật thì còn tệ hơn không có sandbox |
| **B. Tự viết, chất lượng đầy đủ** | `kb.*` + phần **obs/eval-data** DE sở hữu (week-1 §5) | Đây là lane của tôi: ingest thật, truy xuất có hàng rào, leak-test có răng |
| **C. Nguyên mẫu + báo, KHÔNG phải deliverable** | RLS còn thiếu ở bảng của người khác | Dựng thử **trong sandbox** để chứng minh nó chạy, rồi đưa chủ sở hữu bản diff. **Không bao giờ** trình bày là "DE đã làm RLS cho wb/obs" |

> ⚠️ **Ràng buộc import.** Script dựng toàn bộ DB cần `ensure_all_schemas()` từ `studio_app`, mà
> `.importlinter` **cấm `studio_kb` import `studio_app`**. Nên script bring-up **không được nằm
> trong `src/studio_kb/`** — đặt ở tầng script/test (giống cách `tests/test_leak.py` đang dùng
> fixture của `conftest.py` gốc). Plan nằm trong `packages/kb/` nhưng code thì không phải chỗ nào
> cũng đặt được.

### 0.3 Ngoài phạm vi — cố ý

Cost-lineage 3-surface (**S3**) · LLM-judge (**S3**) · composition production trong `apps/studio`
(**Day 6+, mentor**) · UI trace viewer (**S2**) · nối `PgKbSearch` vào `KbSearchService` (quyết định
un-ratchet riêng) · tối ưu hiệu năng / sharding / vector-DB production-scale.

`umbrella-contract.md` §4 đã ghi thẳng: *"**Postgres + fence tại retrieval là điểm gãy demo**, không
phải vector-DB production-scale."* Plan này bám đúng câu đó.

---

## 1. Hiện trạng — kiểm kê thật, không phải ấn tượng

Quét toàn bộ 5 file DDL trong workspace:

| bảng | cột tenant | RLS | chủ |
|---|---|---|---|
| **`kb.chunks`** | `tenant_id TEXT NOT NULL` | ✅ **ENABLE + FORCE + policy** | DE |
| `obs.trace_events` | `tenant TEXT NOT NULL` | ❌ | mentor |
| `core.jobs` | `tenant_id UUID NOT NULL` | ❌ | mentor |
| `core.outbox` | `tenant_id UUID NOT NULL` | ❌ | mentor |
| `wb.recipes` | `tenant TEXT NOT NULL` | ❌ | SWE |
| `wb.recipe_versions` | `tenant TEXT NOT NULL` | ❌ | SWE |
| `core.tenants` | *(chính là sổ đăng ký tenant)* | ❌ | mentor |
| `obs.costs` | **không có** — vỏ rỗng (`id`, `created_at`) | ❌ | mentor → DE điền |
| `obs.golden_sets` | **không có** — vỏ rỗng | ❌ | mentor → DE điền |
| `eval.golden_sets` | **không có** | ❌ | AIE-2 |
| `eval.scorecards` | **không có** (chỉ `agent_id`) | ❌ | AIE-2 |

---

## 2. Ba phát hiện — đây là lý do plan này tồn tại

### F-1 · Hàng rào chỉ đứng ở **đúng một bảng trên mười một**

`kb.chunks` là bảng **duy nhất** có RLS. Năm bảng khác mang `tenant`/`tenant_id` **NOT NULL** nhưng
**không có policy nào** — cột tenant ở đó chỉ là một cột dữ liệu, không phải một hàng rào.

Hệ quả cụ thể: một truy vấn quên mệnh đề `WHERE tenant = ...` trên `obs.trace_events` hay
`wb.recipes` sẽ **trả về dữ liệu của mọi tenant, im lặng, không lỗi**. Ở `kb.chunks` thì RLS chặn
lại. Cùng một lỗi lập trình, hai kết cục trái ngược.

> Đây **chưa chắc là bug**. Có lý do chính đáng để `obs`/`core` không fence: ghi trace và chạy job là
> chức năng của composition-root đã được tin cậy, không phải hành động của tenant. Nhưng `wb.recipes`
> thì khác — recipe **là** tài sản của tenant, và `INV-1 Tenant-Wall` được giao đích danh cho SWE
> (`week-1/README.md` §5). Cần chốt từng bảng, đừng gom một cục.

### F-2 · Cột tenant có **ba kiểu đặt tên/kiểu dữ liệu khác nhau** — không join được

| cách viết | ở đâu |
|---|---|
| `tenant_id TEXT` | `kb.chunks` |
| `tenant_id UUID` | `core.jobs`, `core.outbox` |
| `tenant TEXT` | `obs.trace_events`, `wb.recipes`, `wb.recipe_versions` |

Và `core.tenants.id` là **UUID**.

Nghĩa là `kb.chunks.tenant_id = 'ankor'` (chuỗi) **không nối được** với `core.tenants.id` (UUID).
Không có khoá ngoại nào giữa dữ liệu tenant và sổ đăng ký tenant. Muốn trả lời *"tenant `ankor`
đang giữ những gì"* thì phải nối tay bằng ba quy ước khác nhau.

Nghiêm trọng hơn ở tầng RLS: policy của `kb.chunks` so
`tenant_id = current_setting('app.tenant_id', true)` — **so chuỗi**. Nếu policy cho `core.jobs` viết
y hệt thì so `UUID` với `TEXT` → lỗi kiểu, hoặc tệ hơn là cast ngầm rồi khớp sai.

### F-3 · Bốn bảng **không có cột tenant** — có đúng không?

`eval.golden_sets`, `eval.scorecards`, `obs.costs`, `obs.golden_sets`.

Với `obs.costs`/`obs.golden_sets` thì dễ hiểu — chúng là **vỏ rỗng**, chỉ có `id` + `created_at`,
chờ DE điền cột thật (`scorecard-v0.md:157` ghi rõ vậy). Cột tenant sẽ vào lúc điền.

Nhưng `eval.scorecards` thì **đã có cột thật** (`agent_id`, `results`, `aggregate`, `gate`) mà
**không có tenant**. Bảng điểm của một agent thuộc tenant nào? Nếu hai tenant cùng chạy một
`golden_set_ref` thì hai bảng điểm phân biệt bằng gì ngoài `agent_id`?

Đây là **câu hỏi yêu cầu**, không phải lỗi kỹ thuật — trả lời được thì mới biết có cần fence hay
không.

---

## 3. Các chặng (theo mục tiêu, không theo ngày)

### P0 · Dựng được — **chặn mọi thứ phía sau**

Tầng Postgres viết ở D4 (`postgres.py` + 10 test) **chưa từng chạy một câu SQL nào**. Không có bước
này thì mọi chặng sau đều là code chưa ai bước lên.

```bash
docker compose -f docker-compose.test.yml up -d      # pgvector/pgvector:pg17, cổng 5433
export STUDIO_DATABASE_URL_ADMIN='postgresql://postgres:postgres@localhost:5433/studio_test'
export STUDIO_DATABASE_URL='postgresql://studio_app:...@localhost:5433/studio_test'
uv run pytest packages/kb/tests/test_pg_kb.py -q     # 10 test D4 phải XANH
```

Rồi dựng **cả 5 schema** bằng đúng `ddl()` của từng quadrant — `ensure_all_schemas()` +
`grant_app_privileges()` đã làm sẵn việc gom. **Không chép DDL ra chỗ khác.**

**Xong là:** một lệnh dựng xong toàn bộ; 10 test D4 xanh thật.

---

### P1 · `kb` đạt chuẩn — lane của tôi, làm cho hết

| việc | trạng thái hiện tại |
|---|---|
| Ingest **25 chunk Callisto thật** qua `doc_factory` → `kb.chunks` | viết rồi, **chưa chạy** |
| Truy xuất vector có hàng rào (`PgKbSearch`) | viết rồi, **chưa chạy** |
| Leak-test **T1 + T6 XANH THẬT** trên `kb.chunks` | viết rồi, **chưa chạy** |
| Embedding | **chưa có bản thật nào trong workspace** — chỉ fake |

> Về embedding: đây là **2 impl được chấm của AIE-1** (D-6), không phải việc DE. Sandbox dùng fake
> tất định là đủ — nhưng **`EMBEDDING_DIM = 8` là chiều của fixture**. Khi bản thật về (768/1536
> chiều) thì phải `ALTER TABLE` đổi kiểu cột + **dựng lại index HNSW** + **re-embed toàn bộ**; vector
> 8 chiều cũ không convert được. Ghi vào plan từ bây giờ, đừng để hôm đó mới phát hiện.

**Xong là:** `kb.chunks` có 25 dòng thật, `PgKbSearch` trả `chunk_id` đúng, T1/T6 xanh không `xfail`.

---

### P2 · Mở leak-test ra **toàn bộ** cơ sở dữ liệu — trọng tâm của plan

Đây là phần biến "một sandbox nữa" thành "cơ sở dữ liệu đạt chuẩn". Với **mỗi** bảng mang tenant,
viết đúng một cặp:

| phép thử | nội dung |
|---|---|
| **có mặt** | tenant A ghi 1 dòng → A đọc lại **thấy** |
| **vắng mặt** | tenant B ghi 1 dòng → A đọc **không thấy** |

**Khẳng định có mặt phải đứng trước.** Một bảng trả rỗng vì lý do sai sẽ pass vế loại trừ một cách
vô nghĩa — tập rỗng loại trừ mọi thứ. Bài học đã dùng ở `test_pg_kb.py`, áp lại nguyên vẹn.

Phạm vi: `obs.trace_events` · `core.jobs` · `core.outbox` · `wb.recipes` · `wb.recipe_versions`.

**Kết quả kỳ vọng là ĐỎ.** Năm bảng đó chưa có RLS, nên vế "vắng mặt" sẽ trượt. **Đó chính là sản
phẩm của P2** — biến một nhận xét ("thiếu RLS") thành một lệnh chạy được, có tên bảng, có dòng dữ
liệu, ai cũng tái hiện được. Không có nó thì F-1 chỉ là ý kiến.

---

### P3 · Nguyên mẫu RLS cho các bảng còn thiếu — **sandbox, không phải PR**

Cho từng bảng ở P2, viết policy theo đúng khuôn `kb.chunks` (`ENABLE` + `FORCE` + `USING` +
`WITH CHECK`, khoá theo `current_setting('app.tenant_id', true)`), áp trong sandbox, chạy lại P2.

Hai việc phải làm cùng lúc, không tách:

1. **`FORCE` là bắt buộc, không phải tuỳ chọn.** Thiếu nó thì chủ bảng bỏ qua policy — và trong kit
   này `studio_owner` chính là chủ. Fence trông như có mà không có.
2. **Xử lý F-2 trước khi viết policy cho `core.*`**: cột là `UUID` chứ không phải `TEXT`, nên
   `current_setting()` (trả `text`) phải cast tường minh. Chép nguyên policy của `kb.chunks` sang là
   sai kiểu.

> **Đây KHÔNG phải deliverable của DE.** Sản phẩm là **bản diff + test tái hiện được** đưa cho chủ
> sở hữu: `obs`/`core` → mentor, `wb` → SWE. Nói rõ "đây là nguyên mẫu, mời anh/bạn xem", không phải
> "em làm xong RLS cho phần của anh".

---

### P4 · Thống nhất cột tenant (F-2) — **đề xuất, tuyệt đối không tự sửa**

Ba cách viết cho cùng một khái niệm là nợ kỹ thuật sẽ đắt dần. Nhưng đổi tên cột là **thay đổi phá
vỡ** chạm cả 4 quadrant — đúng thứ `GITFLOWS.md` §6 bắt phải qua quy trình, và `decisions-locked.md`
D-12 xếp vào loại cần **mini-RFC 4 chữ ký**.

Việc của plan này: **chứng minh nó gây hại thật** (một truy vấn nối `kb.chunks` với `core.tenants`
không viết nổi nếu không cast tay), rồi đưa ra một đề xuất có số liệu. Không tự đổi.

---

### P5 · Dữ liệu obs/eval DE sở hữu

`obs.costs` và `obs.golden_sets` là **vỏ rỗng chờ DE điền** (`scorecard-v0.md:157`). Khi điền:

- Có cột tenant ngay từ đầu, **cùng tên cùng kiểu** với quyết định ở P4 — đừng đẻ thêm cách viết thứ tư.
- Có RLS ngay từ đầu, không "thêm sau" — thêm sau nghĩa là có một quãng thời gian dữ liệu nằm trần.
- Cost-lineage 3-surface vẫn để **S3**. Điền cột không có nghĩa là làm luôn tính năng.

---

## 4. Xong là gì — DoD đo được

- [ ] **Một lệnh** dựng xong Postgres + cả 5 schema, bằng `ddl()` có sẵn (không có DDL chép tay song song).
- [ ] 25 chunk Callisto thật nằm trong `kb.chunks`, ingest qua doc-factory.
- [ ] `PgKbSearch` trả `chunk_id` đúng định dạng `{doc_id}#c{n}`, lọc đủ **hai** trục.
- [ ] Leak-test T1 + T6 trên `kb.chunks` **XANH THẬT**, không `xfail`, chạy qua **non-owner pool**.
- [ ] Có test **có mặt/vắng mặt** cho **mọi** bảng mang tenant — kể cả những bài đang đỏ.
- [ ] Danh sách bảng thiếu RLS là **output của một lệnh chạy được**, không phải một đoạn văn.
- [ ] Nguyên mẫu policy chạy được cho từng bảng đó, **kèm chủ sở hữu tương ứng**.
- [ ] F-2 (ba kiểu cột tenant) có bằng chứng gây hại cụ thể + một đề xuất.
- [ ] **Không một dòng nào** ở `apps/studio`, `packages/workbench`, `packages/evalhub` bị sửa.
- [ ] **Không push.**

---

## 5. Nguyên tắc giữ suốt plan

1. **Lắp, đừng viết lại.** DDL của người khác thì gọi `ddl()` của họ. Sandbox lệch cột với thật là
   thứ tệ hơn không có sandbox — nó cho cảm giác an toàn sai.
2. **Đỏ có chủ đích là sản phẩm.** P2 sinh ra test đỏ, và đó là điểm mạnh nhất của plan: nó biến
   nhận xét thành bằng chứng.
3. **Có mặt trước, vắng mặt sau.** Mọi cặp test fence.
4. **`FORCE` cùng với `ENABLE`.** Thiếu `FORCE` thì owner bỏ qua policy — fence hình nộm.
5. **Chưa chạy thì chưa xong.** Đây là SQL. "Đọc thấy đúng" và "chạy đúng" cách nhau rất xa — D4 đã
   commit một tầng Postgres mang nhãn "CHƯA VERIFY", đừng thêm cái thứ hai.
6. **Không nối, không push.** Đụng tới hai điều đó là một quyết định riêng, không phải bước tiếp theo
   của plan này.

---

## 6. Câu cần chốt (không chặn P0–P2)

| # | hỏi ai | nội dung | nghiêng về |
|---|---|---|---|
| **Q1** | mentor | `obs.trace_events` không RLS là **chủ ý** (ghi trace là chức năng tin cậy của composition-root) hay là sót? | chủ ý — nhưng cần xác nhận bằng chữ |
| **Q2** | **SWE** | `wb.recipes` mang `tenant NOT NULL` nhưng không RLS, trong khi **INV-1 Tenant-Wall** được giao đích danh cho bạn. Recipe là tài sản của tenant — fence ở tầng ứng dụng hay tầng DB? | **tầng DB** — cùng khuôn `kb.chunks`; tầng ứng dụng quên một mệnh đề `WHERE` là hở im lặng |
| **Q3** | **AIE-2** | `eval.scorecards` có `agent_id` mà **không có tenant**. Hai tenant cùng chạy một `golden_set_ref` thì phân biệt bằng gì? | thêm cột tenant; nếu không thì phải nói rõ scorecard là **system-scope** |
| **Q4** | mentor + cả nhóm | F-2 — ba kiểu cột tenant (`tenant_id TEXT` / `tenant_id UUID` / `tenant TEXT`). Thống nhất được không, và có đáng làm ở S1 không? | thống nhất **`tenant_id TEXT`** (khớp `kb.chunks` — bảng duy nhất đã có RLS chạy được, đổi nó là đắt nhất). Cần **mini-RFC 4 chữ ký** theo D-12 |
| **Q5** | mentor | `EMBEDDING_DIM = 8` là chiều fixture. Khi embedding thật về thì đổi cột + dựng lại HNSW + re-embed — có nên ghim sẵn 768/1536 ngay bây giờ để tránh migration? | giữ 8 cho S1 (fixtures-first, D-5), nhưng **ghi migration vào plan S2** thay vì để phát hiện lúc chuyển |

---

*Plan mục tiêu — DE, 23/07/2026. Sân tập song song: không nối vào hệ thống, không push. Sửa khi
Q1–Q5 có trả lời.*
