# Plan D8 (DE) — INV-1 Tenant-Wall: data-plane áp tenant filter server-side

> **Ngày:** 2026-07-29 (D8, G2) · **Bút:** DE (Nguyễn Đông Anh) · **Repo WRITE:** kb · **READ:** kit
>
> Issue: `docs/requirements/week-1/days/day-08.md`. Việc DE (`:37`): *"`kb.search` + trace store **áp
> tenant filter server-side** (client khai tenant bị bỏ qua); chuẩn bị `section_role` field (chưa
> filter — để Sprint 3)"*. DoD chung `:52-56`.

---

## 0. Đánh giá khối lượng — NHẸ, vì fence đã front-load ở D4–D5

Nói thẳng để không thổi phồng: **pattern INV-1 (resolve server-side + mandatory filter fail-closed) đã
nằm trong code data-plane của DE từ D4–D5.** Day 8 với DE **phần lớn là verify + ghi chú + phối hợp**,
không phải viết fence mới. Kiểm bằng đọc code, không tự khai:

| Mảnh INV-1 mà Day 8 đòi | Đã có ở đâu | Trạng thái |
|---|---|---|
| `kb.chunks.tenant_id UUID **NOT NULL**` | `schema.py:40` | ✅ |
| RLS fail-closed trên `kb.chunks` (`ENABLE`+`FORCE`+policy `app.tenant_id`) | `schema.py:52-58` | ✅ — unset session ⇒ 0 dòng |
| `StaticKbSearch` lọc tenant (nhận **UUID resolved**, so `==`) | `static_search.py:63,92` | ✅ đang chạy |
| `PgKbSearch` `WHERE tenant_id` + `_bind_tenant` (`set_config app.tenant_id`, is_local) kích RLS | `postgres.py:68-70,88-96` | ✅ viết rồi (cần DB) |
| Trace reader lọc tenant (`WHERE run_id AND tenant_id`) | `trace_reader.py:67-70` | ✅ |
| `section_role` field trên `kb.chunks` | `schema.py:41` | ✅ đã có |

→ **Cả 6 mảnh DE cần cho INV-1 đều đã tồn tại.** Chữ ký `search(query, tenant_id: UUID, section_roles,
top_k)` chỉ nhận **UUID đã phân giải**, **không có đường nào nhận tenant slug do client khai** — tức
"client khai tenant bị bỏ qua" đã đúng ở tầng chữ ký (`static_search.py:63`, `postgres.py`, `trace_reader.py:289`).

**Việc phân giải session → tenant là bút SWE** (middleware, `day-08.md:36`), không phải DE. DE **consume**:
nhận UUID đã resolve rồi lọc bắt buộc. Nên DoD `:52` ("client gửi tenant=borea khi session=ankor →
kb.search chỉ trả ankor") **chủ yếu là việc SWE**; DE chỉ đảm bảo data-plane không có kẽ hở nhận tenant client.

---

## 1. Hai điều chốt trước để plan không trôi

**① INV-1 hôm nay là về TENANT, không phải ROLE.** `tenant_id` được truyền **resolved** → DE lọc bắt
buộc, đúng bài. `section_roles` thì `StaticKbSearch` hiện **tin giá trị client khai** (`static_search.py:24`
docstring) — nhưng đó là **đúng scope**: issue `:37` ghi *"section_role chưa filter — để Sprint 3"*, và
việc hoãn là **phân giải server-side + fail-closed cho role**, tới S3. Đừng kéo role-resolution vào D8.

**② `obs.trace_events` KHÔNG có RLS, và đó KHÔNG phải việc DE sửa.** DDL bảng này thuộc **`apps/studio`**
(`apps/studio/src/studio_app/obs/schema.py`), DE chỉ **đọc** qua `trace_reader.py`. Bảng cố ý không RLS
(trace là hành động composition-root, không phải của tenant — `trace_reader.py:281-283`), nên mệnh đề
`WHERE ... AND tenant_id` trong reader là **hàng rào duy nhất** ở đó. Hàng rào DE cần cấp = mệnh đề WHERE
đó — **đã có**. Thêm RLS vào `obs.trace_events` là lane của chủ DDL (apps/studio/mentor), ghi rõ để khỏi
lấn.

---

## 2. Việc DE thật sự còn — 4 mục, đều nhẹ

### D8-1 · Test/demo "client-khai-tenant bị bỏ qua" ở data-plane

Đã đo trong phiên review golden-set: `StaticKbSearch.search(q, TENANT_IDS["ankor"], ["public"], k)` với
query *"Hạn mức chi của **Borea**"* → **5/5 chunk toàn ankor, leak borea = False** (chạy lại được). Đây
là bằng chứng data-plane: kể cả query nhắc "Borea", chỉ tenant được truyền (ankor) quyết định kết quả.

Việc: viết **một test DE** khoá tính chất này — `search` với `tenant_id=ankor` **không bao giờ** trả chunk
tenant khác, **bất kể nội dung query**. Không phải test của mentor; là test canh chính data-plane của DE
(cùng khuôn `test_pg_kb.py`). Nếu là StaticKbSearch (in-memory) thì test thuần; nếu muốn khoá cả tầng
Postgres thì dùng `PgKbSearch` + RLS (cần DB — có thể để marker skip khi không có DB, đúng vết #11).

**Ranh giới:** DE **không** dựng middleware session. Test này chứng minh *"cho UUID nào, lọc đúng UUID đó"*
— nửa còn lại *"UUID đến từ session không từ client"* là DoD của SWE.

### D8-2 · Ghi chú tag-vs-isolation (1 đoạn) + vì sao "nhờ LLM đừng nói" là fake fence

DoD `:54,:55`. Bản nháp (đưa vào daily-note):

> **Tag ≠ isolation.** *Tag* là nhãn mềm đi kèm dữ liệu (vd nhét "chỉ ankor" vào prompt rồi mong model
> tôn trọng) — nó **khuyên**, không **chặn**; một prompt-injection hoặc model kém là rò. *Isolation* là
> **fail-closed filter** dựa trên danh tính **resolve server-side**: `kb.chunks` bật `FORCE ROW LEVEL
> SECURITY` khoá theo `current_setting('app.tenant_id')` (`schema.py:52-58`) — session chưa set thì thấy
> **0 dòng**, không phải "thấy hết rồi nhờ đừng đọc". "Nhờ LLM đừng nói" là fake fence vì nó đặt biên
> giới bảo mật **sau** khi dữ liệu đã rời kho, ở một lớp (LLM) vốn không đảm bảo — dữ liệu nhạy cảm đã
> nằm trong context thì coi như đã rò. Isolation thật đặt biên **trước** truy xuất: chunk sai tenant
> **không bao giờ** ra khỏi Postgres.

### D8-3 · Hoà giải `section_role`: field đã có VÀ đã lọc — nói rõ quyết định

Issue `:37` viết *"chuẩn bị section_role field (chưa filter — để S3)"*. Thực tế: field **đã có**
(`schema.py:41`) VÀ `StaticKbSearch` **đã lọc** nó (`static_search.py:92`, cho SC-05). Không mâu thuẫn —
docstring `static_search.py:27-29` chốt sẵn: *v0 vẫn lọc mệnh đề `section_roles` (không thì SC-05 xanh vì
lý do sai); thứ hoãn tới S3 là **phân giải server-side + fail-closed**, không phải bản thân mệnh đề lọc.*
Việc D8: **ghi một dòng trong daily-note** xác nhận đọc đúng ý issue — "field sẵn, mệnh đề lọc sẵn cho
role; role-resolution server-side để S3" — để mentor/AIE không đọc lệch "DE làm sớm".

### D8-4 · Daily-note D8

DoD `:56`. Gói D8-1..D8-3 + trạng thái "fence đã front-load, D8 chủ yếu verify/consume".

---

## 3. Phụ thuộc & câu hỏi chặn (gửi đầu giờ)

| # | Cho ai | Câu hỏi | Vì sao chặn |
|---|---|---|---|
| **Q-A** | **SWE** | Middleware resolve `{tenant,user,roles}` từ `session_id` truyền `tenant_id` **UUID** xuống seam `kb.search`/`trace_reader` qua đường nào (composition root ở `apps/studio`)? DE nhận UUID ở tham số — cần biết ai set, set ở đâu, để test D8-1 khớp luồng thật | DoD `:52` là **của SWE**; DE chỉ verify được nửa data-plane nếu chưa biết middleware bơm UUID vào đâu |
| **Q-B** | **SWE / chủ obs DDL** | `obs.trace_events` có định thêm RLS ở D8 không, hay giữ WHERE-only (reader là hàng rào duy nhất)? | Nếu có → không phải lane DE nhưng ảnh hưởng lý lẽ "isolation" trong ghi chú D8-2; nếu không → ghi rõ là nợ có chủ đích |
| Q-C | AIE-1 | Interpreter truyền `session` context (không truyền tenant client) — executor có tự set tenant không? | Nếu executor tự set tenant từ recipe/client thì fence data-plane của DE bị bypass phía trên |

---

## 4. Lịch (đầu giờ / trong ngày)

| Mốc | Việc | ⬜ |
|---|---|---|
| Đầu giờ | Nhắn **Q-A** (SWE, chặn D8-1) + **Q-B** (obs RLS) | ⬜ |
| Sáng | D8-1: viết test data-plane "client-tenant-ignored" (StaticKbSearch; PgKbSearch nếu có DB) | ⬜ |
| Sáng | D8-3: dòng hoà giải section_role | ⬜ |
| Chiều | D8-2: chốt ghi chú tag-vs-isolation (khớp câu trả lời Q-B) | ⬜ |
| Chiều | D8-4: daily-note D8, mở PR nhánh `day8/...` submodule kb | ⬜ |

---

## 5. DoD D8 — phần DE

- [ ] (chung, dẫn SWE) client gửi `tenant=borea` khi session `ankor` → `kb.search` chỉ trả ankor.
      **DE:** test data-plane chứng minh "cho UUID ankor → chỉ ankor, bất kể query" (D8-1).
- [ ] `tenant_id NOT NULL` + mandatory filter fail-closed — **đã có** (`schema.py:40,52-58`); D8 chỉ verify.
- [ ] Giải thích "nhờ LLM đừng nói" = fake fence — ghi chú D8-2.
- [ ] Ghi chú tag-vs-isolation (1 đoạn) — D8-2.
- [ ] Daily-note D8 — D8-4.

**Tóm tắt khối lượng:** ~nửa ngày. Không fence mới; một test data-plane + hai đoạn ghi chú + hoà giải
section_role + daily-note. Việc nặng của INV-1 (middleware session→tenant) nằm ở **SWE**, DE consume.
