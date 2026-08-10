# Plan D17 (DE) — Fence TẠI RETRIEVAL fail-closed (lật `KbSearchService`→`PgKbSearch`) + T1 IDOR đóng + T6 label-spoof (mức ĐẦU) · KHÔNG còn blocker quyết-design (B2 hướng A chốt bởi SWE #112 + verify code); build song song qua mock, giữ xfail T6

> **Ngày:** 2026-08-11 (D17, Thứ Ba · Chặng 2 / Sprint 2 · Tuần 4) · **Bút:** DE (Nguyễn Đông Anh)
> **Anchor:** issue kit **#110** (con của **#114** "Fence tại retrieval fail-closed + T1 IDOR + T6
> label-spoof xanh"). Anh em: AIE-1 **#111** (xác nhận kb-retrieve executor chạy trong context
> tenant-scoped) · SWE **#112** (**own INV-1**: `session_id` resolve `{tenant,user,roles}` server-side) ·
> AIE-2 **#113** (thêm 1 golden case cross-tenant "câu chỉ có ở tenant-Y" → scorecard).
> **Repo WRITE: `agentcore-studio-kb`** · kit READ. **Milestone:** Sprint 2 — Gate Day 20.
>
> Việc DE (#110, dòng tiêu đề): *"**Áp mandatory filter tại retrieval** trên `kb.search` (chunk-level
> `tenant_id`/`section_role` NOT NULL, fail-closed); viết **T6 label-spoof** test (client tự khai bị bỏ
> qua)."* DoD 3 ô (filter fail-closed tại retrieval · T1 IDOR + T6 label-spoof pytest xanh (đầu) ·
> refusal+audit cho câu cross-tenant) là **DoD chung kế thừa từ cha #114** — đọc là **"phần DE của 3 ô
> đó"**: DE lật seam + đóng T1 + T6-đầu; **INV-1 server-side là #112**, executor tenant-scoped là #111.

---

## 0. Đọc cho đúng trước khi cắt — D17 là UN-RATCHET đã dựng scaffold, NHƯNG "T6 đầy đủ" vượt lằn kb

Bốn điều đặt lằn ranh của ngày:

**(a) Nền phải là main MỚI — SAU khi D16 (#105) merge.** D16 golden-set-recorded (nhánh
`day16/de-golden-set-recorded`, PR chưa mở) phải **merged** trước; 8 case âm của
`callisto-golden-30-v1.yaml` (T1 hai chiều + T6 hai tenant) là **fixture nghiệm thu** của D17. →
`git fetch` + cắt `day17/de-fence-at-retrieval` trên `origin/main` MỚI sau D16.

**(b) Cơ chế fail-closed ĐÃ có trong `PgKbSearch` từ D13 — D17 KHÔNG viết lại logic lọc.** `postgres.py::
PgKbSearch.search` đã: RLS `FORCE` khoá `app.tenant_id` (trục tenant) + `WHERE section_role = ANY(%s)`
(trục vai) + `section_roles` rỗng → `[]` (không hiểu là "bỏ lọc") + lọc **trong SQL** (không trả-hết-rồi-
lọc). `schema.py` đã `tenant_id UUID NOT NULL` + `section_role TEXT NOT NULL`. → Phần "chunk-level NOT
NULL + fail-closed tại retrieval" của #110 phần lớn **đã tồn tại**; việc D17 là **lật seam chính thức**
`KbSearchService` sang dùng cơ chế đó + đóng leak-test, KHÔNG dựng fence mới.

**(c) Un-ratchet đã dựng scaffold 3 bước (postgres.py) — bước 1 CẦN embedding, đã CHỐT cách cấp.**
Scaffold: ① `KbSearchService.search` uỷ quyền `PgKbSearch.search`; ② xoá `test_search_contract.py`;
③ gỡ `xfail` `test_leak.py` T1/T6. `KbSearchService.__init__(self, pool)` **không có embedding**, còn
`PgKbSearch(pool, embedding)` **cần embedding** để embed query. **B1 ĐÃ CHỐT (11/08, team):** cấp
embedding theo đường **optional + factory, GIỮ QĐ-U1** — `__init__(self, pool, embedding=None)`,
production dùng factory tiêm embedding thật; `KbSearchService(pool)` (T3) self-provision stub
`derive_vector` khi `None` → T3 **tự XPASS, AIE-1 KHÔNG sửa call-site**. → B1 hết chặn (xem §3). Còn
**B2/B3/B4** vẫn cần chốt.

**(d) "T6 client tự khai bị bỏ qua" ĐẦY ĐỦ vượt lằn kb — chữ ký frozen không mang danh tính.**
`kb-search.v0.md` §5.2 + `postgres.py` đuôi module nói thẳng: chữ ký `search(query, tenant_id,
section_roles, top_k)` **FROZEN 4 tham số, KHÔNG mang danh tính người gọi**, nên kb **không thể** phân
giải role server-side từ trong hàm. `PgKbSearch` **tin** `section_roles` truyền xuống (`WHERE section_role
= ANY`). "Client tự khai bị bỏ qua" = **INV-1** (resolve `session_id`→roles server-side, **#112 own**);
kb chỉ đảm bảo **fail-closed trên roles ĐƯỢC GIAO**. → **Blocker B2** (xem §3). Vì vậy #114 ghi rõ T6
"mức **đầu**".

Lằn giữ nguyên: **chỉ WRITE trong `packages/kb`**; **không đụng** `apps/studio` (composition/T3/T4 —
lane AIE-1/SWE), engine executor (#111), workbench, INV-1 (#112). **Không đổi chữ ký `kb.search`** (FROZEN
`kb-search.v0.md`). **Giữ `EMBEDDING_DIM=8`, không đụng schema/RLS** (chống schema-drift). Un-ratchet là
**gỡ xfail vì impl đã thật**, KHÔNG phải sửa test để pass (mentor P5/P9 sanction).

---

## 1. Việc sẽ làm (nhánh `day17/de-fence-at-retrieval`, nền `origin/main` sau D16 · test-first)

> ⚠️ **KHÔNG còn blocker quyết-design.** B1 chốt (embedding); **B2 hướng A chốt** (SWE #112 + verify: lỗ ở
> `executors.py:139`, resolve ở executor, kb trust); B4 theo B2; B3 gỡ (carrier §7). Khởi công NGAY sau D16
> merge: **①②④⑤ + T1 + no-bypass teeth** — build song song qua **mock** `resolve_section_roles`. **Giữ `test_t6`
> xfail** (đúng lộ trình un-ratchet, tách khỏi gate D17); chỉ **gỡ xfail T6** mới chờ #112 xong. T6-full assert
> (mock resolver, tại input `kb.search`) sống ở **executor** — coordinate #111/#112, DE không WRITE engine.

### ① Lật `KbSearchService.search` → dùng cơ chế `PgKbSearch` (fail-closed tại retrieval) · B1 đã chốt
Uỷ quyền logic sang `PgKbSearch.search` (RLS tenant + `WHERE section_role` + rỗng→`[]` + lọc-trong-SQL).
**B1 chốt (optional + factory, giữ QĐ-U1):**
- `__init__(self, pool, embedding=None)`; body dựng `self._pg = PgKbSearch(pool, embedding or
  _default_stub())`, `search()` uỷ quyền thẳng `self._pg.search(...)` (chữ ký giống hệt, 4 tham số frozen).
- `_default_stub()` = adapter bọc `derive_vector` — **cùng không gian SSOT** `embeddings.py` /
  `ingest_callisto._FixtureEmbedding` / `test_pg_kb` (dim-8). **Bắt buộc cùng không gian** với vector đã
  seed vào `kb.chunks`, nếu không `KbSearchService(pool)` (T3) truy vấn lệch không gian → trả rỗng → T3 vỡ
  ở khẳng định positive-inclusion. Không hardcode gateway (EmbeddingService owner = AIE-1); stub chỉ phục
  vụ đường dev/test dựng-1-tham-số.
- Production tiêm embedding thật qua factory (không phải stub). DE **không** WRITE factory ở `apps/studio`
  — chỉ cấp `KbSearchService` nhận được embedding; ai gọi factory là composition (lane AIE-1/SWE).

### ② T1 IDOR — đóng ĐẦY ĐỦ (trục tenant, RLS đỡ) · gỡ xfail `test_t1_idor`
`test_leak.py::test_t1_idor` (seed tenant-A + tenant-B, search as A, đòi chỉ A trả về). Lật ① xong, RLS +
`WHERE tenant_id` khoá → T1 xanh THẬT. **Gỡ `@pytest.mark.xfail`** khỏi `test_t1_idor` (un-ratchet). Đây
là phần DE đóng trọn được **một mình**, không chờ #112.
> ⚠️ **Wrinkle seed (verify 10/08):** `_seed_chunk` (test_leak.py) INSERT `(chunk_id,tenant_id,section_role,
> text)` — **không embedding**; mà `PgKbSearch._SEARCH` có `AND embedding IS NOT NULL`. Uỷ quyền thẳng →
> chunk seed (embedding NULL) bị lọc → khẳng định positive-inclusion `"chunk-a-1" in results` **TRƯỢT**. Nên
> un-ratchet T1 phải **sửa `_seed_chunk` seed kèm embedding** (dim-8 `derive_vector`) để đường PgKbSearch trả
> được — đây là **hoàn thiện fixture cho test placeholder**, không phải nới assert (assert loại-trừ giữ nguyên).

### ③ T6 label-spoof — hướng A CHỐT (SWE #112, verified code) · DE GIỮ xfail T6 ở D17
**SWE #112 trả lời + verify code (10/08):** lỗ T6 nằm ở **`engine/executors.py:139`** (`node.params.get(
"section_roles", [])` → `:155` truyền vào `kb.search` — TIN thẳng client/recipe khai). `tenant_id` thì
`interpreter.py:291` bơm server-side, `section_roles` thì **chưa**. `contracts/kb.py:4` + `kb-search.v0.md
§5.2` + docstring `executors.py:92-102` đều nói section_roles **phải resolve server-side, truyền UNCHANGED**.
→ **Hướng A CHỐT:** resolve ở **executor / Tenant-Wall** (dùng `resolve_section_roles(ResolvedContext)` — #112
**tạo mới**, chưa tồn tại; đặt cạnh `resolve_session` ở `tenant_wall.py`, expose qua `packages/contracts`).
**KbSearchService CHỈ trust list nhận được**, không tự hỏi session. Phần kb DE:
- **kb đảm bảo no-bypass trên roles ĐƯỢC GIAO:** rỗng→`[]`, không wildcard, không nhánh "bỏ lọc" — viết
  **teeth kb-lane** cho bất biến này (DE đóng một mình).
- **GIỮ `test_leak.py::test_t6_label_spoof` xfail — KHÔNG gỡ ở D17** (SWE khuyến nghị + nhất quán: test này
  gọi `KbSearchService` trực tiếp với roles spoof, mà kb **theo thiết kế trust input** → không bao giờ pass ở
  tầng kb). Nó là **marker un-ratchet** cho tới khi closure thật (resolver upstream) được verify.
- **Full label-spoof (assert đúng chỗ)** = test tại **input của `kb.search` ở executor**: mock
  `resolve_section_roles`→`["public"]`, recipe khai `["finance"]`, assert giá trị THẬT vào `kb.search` là
  `["public"]`. Đây là **engine lane (executors.py) + #112 resolver** — DE **coordinate #111/#112**, không WRITE
  engine. (Cảnh báo SWE: assert sai chỗ — kiểu "service không raise" — thì mutation fail-OPEN `executors.py`
  default-4-role KHÔNG bị bắt, kb vẫn "71 passed". Phải assert tại input kb.search.)
- **Build song song (không chờ #112 chạy):** DE viết seam + no-bypass teeth dùng **mock** `resolve_section_roles`
  (theo hành vi kỳ vọng, đúng tinh thần contract-first + `.importlinter`); SWE viết resolver + mapping thật song
  song; ráp ở composition root `apps/studio`. **Thứ duy nhất chờ #112 xong hẳn = được phép GỠ xfail T6.**

### ④ Xoá `tests/test_search_contract.py` (scaffold bước ②)
Nó khẳng định `KbSearchService.search` raise `NotImplementedError` — lật ① xong là mâu thuẫn, phải xoá
(đã ghi ở postgres.py). Cập nhật `__init__.py`/docstring nhắc "spec DE chưa xong" cho khớp trạng thái mới.

### ⑤ refusal + audit cho câu cross-tenant — CẢ HAI trong schema frozen (B3 gỡ)
- **Refusal** = `kb.search` trả `[]` cho câu ngoài scope — phần kb DE, **đã có** (§5.1/§6.1a, fail-closed).
- **Audit** = **KHÔNG cần node_type thứ 7** (mis-frame ban đầu). `trace-event.v0.md` schema/§7: mỗi event đã
  có `tenant_id` NOT NULL + `inputs_hash` (sha256 params — **hash, không rò nội dung**) + `citations:[]` +
  `outputs: obj` (NOT NULL, default `{}`). Một câu cross-tenant để lại **một `kb-retrieve` event mang tenant
  người-hỏi + `citations:[]`** = **bản ghi audit đã tồn tại sẵn** trong carrier frozen. Event này do executor
  (#111) phát — **DE không tự emit trace trong `kb.search`** (giữ hàm truy xuất thuần).
- **Enrich tuỳ chọn (không chặn):** coordinate #111 ghi `outputs.fenced=true` + scope-requested vào event
  `kb-retrieve` khi kết quả rỗng-do-fence, để audit **phân biệt** "fenced" với "in-scope-no-answer" (§6.1a).
  Nicety nhỏ trong carrier có sẵn, KHÔNG schema-change. Nếu #111 chưa kịp → audit cơ bản (tenant+citations:[])
  vẫn đủ cho DoD.

### ⑥ Tests — teeth mới, KHÔNG nới cũ
- Gỡ xfail T1 (②) + T6 theo B2. `test_pg_kb.py` (đã canh PgKbSearch fence) giữ nguyên xanh.
- `test_leak_meta.py` (anti-tamper) sửa **cùng commit** nếu tên/shape leak-test đổi (như D-13 đã làm).
- Thêm ca no-bypass nếu B2-b; ca vocab-drop nếu B2-a. Byte-identical golden-set (D16) không đụng.

---

## 2. DoD #110 (phần DE) — đối chiếu

- [ ] **Filter fail-closed tại retrieval** — ①: seam chính thức `KbSearchService` chạy cơ chế `PgKbSearch`
  (RLS tenant + `WHERE section_role` + rỗng→`[]` + lọc-trong-SQL); NOT NULL đã ở `schema.py`.
- [ ] **T1 IDOR pytest xanh** — ②: đóng đầy đủ (RLS), gỡ xfail `test_t1_idor`.
- [~] **T6 label-spoof pytest xanh (ĐẦU)** — ③: kb đảm bảo **no-bypass trên roles được giao**; `test_t6`
  re-scope no-bypass (design chốt bởi contract §5.2 = B2-b, **không** vocab-guard). **"Client tự khai bị bỏ
  qua" đầy đủ = #112 INV-1** (chữ ký frozen không mang danh tính) — joint test, chờ #112 timing.
- [ ] **refusal + audit cho câu cross-tenant** — ⑤: **refusal** = `kb.search []` (DE, đã có + canh);
  **audit** = `kb-retrieve` event hiện hữu (tenant người-hỏi + `citations:[]`) trong carrier frozen §7, do
  #111 phát — **không cần schema mới**. Enrich `outputs.fenced` = nicety #111 (không chặn).

---

## 3. ⚠️ BLOCKER — viết rõ (cần chốt ở huddle sáng D17 TRƯỚC khi code)

| # | Trạng thái | Blocker | Vì sao chặn | Ai chốt | Kết / đề xuất |
|---|---|---|---|---|---|
| **B1** | ✅ **CHỐT 11/08** | `KbSearchService(pool)` **thiếu embedding** để uỷ quyền `PgKbSearch(pool, embedding)`; QĐ-U1 cấm AIE-1 sửa call-site (T3). | Uỷ quyền cần embedding; bắt buộc thêm tham số `__init__` → `KbSearchService(pool)` vỡ T3. | DE + AIE-1 + mentor. | **Optional + factory, giữ QĐ-U1:** `__init__(self, pool, embedding=None)` — production factory tiêm embedding thật, `KbSearchService(pool)` self-provision stub `derive_vector` (SSOT dim-8) → T3 tự XPASS, AIE-1 không sửa. Xem §1①. |
| **B2** | ✅ **CHỐT (SWE #112 + verify code)** | Lỗ T6 nằm ở **`engine/executors.py:139`** (`node.params.get("section_roles",[])`→`:155` truyền vào `kb.search`); kb theo thiết kế **trust input**. | `contracts/kb.py:4` + `kb-search.v0.md §5.2` + `executors.py:92-102`: section_roles resolve server-side, truyền UNCHANGED → **hướng A**: resolve ở executor/Tenant-Wall (#112 tạo `resolve_section_roles`, chưa tồn tại), kb chỉ trust. | SWE #112 (chốt) + AIE-1 #111 (executor). | **kb:** no-bypass teeth (DE, một mình) + **GIỮ `test_t6` xfail ở D17** (kb-by-design không pass được). **Full label-spoof** = assert tại input `kb.search` ở executor (mock resolver → assert `["public"]` không `["finance"]`) = engine lane. **Build song song qua mock**; chỉ GỠ xfail T6 mới chờ #112 xong. |
| **B3** | ✅ **GỠ (mis-frame ban đầu)** | "Audit" cho câu cross-tenant tưởng cần trace-event mới. | **Không cần node_type thứ 7.** `trace-event.v0.md` schema/§7: mỗi event đã có `tenant_id` NOT NULL + `inputs_hash` + `citations:[]` + `outputs` obj → **carrier frozen chở được audit**. | DE (refusal) + **#111** (event đã emit). | **refusal** = `kb.search []` (DE, đã có); **audit** = `kb-retrieve` event hiện hữu (tenant người-hỏi + `citations:[]`) do #111 phát — **trong schema frozen, không mini-RFC**. Enrich `outputs.fenced` = nicety #111, không chặn. |
| **B4** | ✅ **chốt (B1+§5.2)** | Design "factory tiêm resolver" (R1b, T3:203) kỳ vọng resolver. | Embedding theo B1; **resolver = session-side per §5.2 = #112**. | — | kb **không dựng resolver**; D17 land seam KHÔNG buộc resolver, #112 cấp sau. Hết là câu hỏi mở riêng. |

**Sau B1 + contract + SWE #112 trả lời, KHÔNG còn blocker quyết-design:** hướng A đã chốt (executor resolve,
kb trust) — verify code khớp 100%. **DE build song song ngay qua mock `resolve_section_roles`** (contract-first
+ `.importlinter` cho phép); `un-ratchet` (detail_overview.md:166-168) **tách khỏi gate D17** nên D17 KHÔNG buộc
xanh-100% — **giữ `test_t6` xfail là đúng lộ trình**. Thứ duy nhất chờ #112 xong hẳn = **được phép gỡ xfail T6**
(tuyên bố lỗ đã đóng thật) — không chặn code D17 của DE. **①②④⑤ + T1 + no-bypass teeth** khởi công ngay sau D16
merge; T6-full assert (executor) coordinate #111/#112 song song.

---

## 4. Bằng chứng (env pinned 3.14 · Postgres sống port 5433 · skip ≠ pass)

- **`git fetch` sau khi D16 merge** — cắt `day17/de-fence-at-retrieval` trên `origin/main` mới.
- `docker compose -f docker-compose.test.yml up -d --wait` + 2 DSN (`studio_owner`/`studio_app`) **TRƯỚC**
  khi chạy test/viết báo cáo (SOP; skip ≠ pass — O3.2). T1/T6 leak-test **cần DB** (RLS chỉ cắn qua
  non-owner pool).
- `test_leak.py`: T1 xanh THẬT sau gỡ xfail; T6 xanh theo B2 (đầu). `test_search_contract.py` **đã xoá**.
  `test_leak_meta.py` khớp tên mới (cùng commit). `test_pg_kb.py` giữ xanh.
- **Toàn suite kb xanh** (cần Docker) · `ruff`/`mypy`/`lint-imports` KEPT. Golden-set D16 byte-identical
  không đụng.
- Interpreter **3.14** (`.venv/bin/python` / `uv run --python 3.14`), **không `python3` trần** (local 3.11).
- Mutation sweep cho glue mới (nhánh lật seam + vocab-guard nếu B2-a); không phát sinh lỗ. Đặc biệt canh
  mutant "bỏ mệnh đề `WHERE section_role`" phải bị bắt (đó là hở T6 im lặng).

---

## 5. Còn treo / ngoài phạm vi hôm nay

- **INV-1 server-side `session_id`→`{tenant,user,roles}` = #112 (SWE)** — DE **không** viết INV-1; DE cấp
  seam fail-closed nhận roles-đã-resolve. T6 đầy-đủ là joint DE×#112.
- **kb-retrieve executor tenant-scoped = #111 (AIE-1, engine)** — DE coordinate, không đụng engine.
- **Golden case cross-tenant "chỉ có ở tenant-Y" cho scorecard = #113 (AIE-2)** — DE cấp 8 case âm golden-set
  (D16) làm nguồn; không viết scorecard.
- **Audit emission** (nếu chốt ngoài lằn kb ở B3) — honest-TODO, không tự mở scope.
- **Nhãn tay ground-truth (agreement) = D18 (#115)** · **cost-lineage = D19 (#120)** · **gate spine = D20 (#125)**.
- **`apps/studio` T3/T4** (`test_kb_search_live_readiness`) là lane AIE-1/SWE — DE land sao cho **tự XPASS**
  (QĐ-U1), **không** WRITE vào `apps/studio`.
- **Trạng thái:** plan viết xong; **chưa** cắt nhánh / chưa code. **KHÔNG còn blocker quyết-design:** B1 chốt
  (embedding optional+factory) · **B2 chốt hướng A** (SWE #112 + verify code: lỗ ở `executors.py:139`, resolve ở
  executor, kb trust; #112 tạo `resolve_section_roles`) · B4 theo B2 · B3 gỡ (audit vừa carrier §7). Sau D16
  merge: **①②④⑤ + T1 + no-bypass teeth** khởi công ngay (build song song qua **mock** `resolve_section_roles`).
  **Giữ `test_t6` xfail ở D17** (đúng lộ trình un-ratchet, tách khỏi gate). Thứ duy nhất chờ #112 xong = **gỡ
  xfail T6** — không chặn code DE. Coordinate còn lại: T6-full assert ở executor (#111/#112) + `outputs.fenced` (#111).
