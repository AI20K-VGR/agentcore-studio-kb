# Plan D17 (DE) — Fence TẠI RETRIEVAL fail-closed: lật `KbSearchService`→`PgKbSearch` + đóng T1 IDOR + T6 label-spoof test (mức đầu)

> **Ngày:** 2026-08-11 (D17, Thứ Ba · Chặng 2 / Sprint 2 · Tuần 4) · **Bút:** DE (Nguyễn Đông Anh)
> **Anchor:** issue kit **#110** (con của **#114**). Anh em: AIE-1 **#111** (executor tenant-scoped +
> refusal) · SWE **#112** (Own INV-1 + Tenant-Wall + viết **T1** test playground) · AIE-2 **#113**
> (golden case cross-tenant → refusal). **Repo WRITE: `agentcore-studio-kb`** · kit READ. **Milestone:**
> Sprint 2 — Gate Day 20.
>
> Việc DE (#110): *"**Áp mandatory filter tại retrieval** trên `kb.search` (chunk-level `tenant_id`/
> `section_role` NOT NULL, fail-closed); **viết T6 label-spoof test** (client tự khai bị bỏ qua)."*

---

## 0. Bức tranh đã VERIFY code (đọc 3 phút rồi vào §1)

**T6 đóng thế nào — đơn giản hơn tưởng, KHÔNG cần resolver.** Trace code (đã verify):
- **Lỗ T6 ở `engine/executors.py:139`:** executor đọc `node.params.get("section_roles", [])` (từ **recipe**,
  client khai được) → `:155` truyền vào `kb.search`. `tenant_id` thì đã an toàn — `interpreter.py:291`
  **inject `session_context.tenant_id`** đè node.params; `section_roles` thì **chưa được inject**.
- **section_roles ĐÃ CÓ SẴN trong session (identity, không map):** `eval_adapter.py:104` dựng session
  `resolve_session({"tenant_id":…, "user":"eval-harness", "roles": section_roles})` — `SessionContext.roles`
  = section_roles **truyền thẳng** (cùng list nhét vào cả `scope` recipe lẫn `roles` session). Không có
  tầng vai-org, không cần `resolve_section_roles` mapping.
- **→ Fix T6 = MỘT dòng ở `interpreter.py:291` (ENGINE, #111):** inject thêm `section_roles` từ
  `session_context.roles` cạnh `tenant_id`, đè recipe khai. Executor đọc giá trị đã-đè → lỗ đóng, **cùng
  cơ chế `tenant_id`**. **DE không viết dòng này** (engine lane); DE cấp **test acceptance**.

**Caveat trung thực — server-side đang là STUB, nên "đóng T6" ở D17 chỉ MỨC ĐẦU:**
- Nguồn danh tính chưa thật: eval path dựng session tay (`user="eval-harness"`); HTTP middleware
  (`apps/studio/middleware.py`) là `!!! DEV-TIME STUB` tin header `x-tenant-id` (giả được), **không JWT**.
  Code tự ghi *"AUTHENTICATION gap... MUST be replaced before production"*.
- → Fix inject đóng đường **recipe-spoof** (recipe khai bị đè). Nhưng **T6 kín production** còn cần **auth
  thật** nuôi `session.roles` — **ngoài D17**. D17 đóng mức đầu bằng session eval-fed.

**Đã settle:**
1. **B1 embedding** — `KbSearchService.__init__(self, pool, embedding=None)`, self-provision stub
   `derive_vector` khi None (giữ QĐ-U1: `KbSearchService(pool)` T3 apps dựng được, AIE-1 không sửa).
2. **T1** đóng được **một mình** ở kb (RLS + `WHERE tenant_id`).
3. **T6 test là deliverable RIÊNG của DE, không dự phòng** (đọc kỹ 5 issue: chỉ #110 có "viết T6 test").
4. **Audit** vừa carrier trace-event `§7` (`tenant_id`+`inputs_hash`+`citations:[]`+`outputs`) — không event mới.
5. **KHÔNG cần `resolve_section_roles` / Protocol / signature** (section_roles đã ở session, identity) —
   cả cuộc bàn primitive-vs-ResolvedContext thành **moot cho D17**.

**Về cú LẬT `KbSearchService` (①②) — DE-elective, KHÔNG phải yêu cầu #110.** Đọc kỹ #110: chỉ đòi *"áp
mandatory filter tại retrieval + viết T6 test"* — **không có chữ "lật"**. Mandatory filter **đã chạy** trên
`PgKbSearch` (spine từ D13) + schema NOT NULL, nên #110 thoả được **không cần lật**. Cú lật (un-ratchet
seam chính thức) là **roadmap DE tự hẹn** (`postgres.py` scaffold, D15 plan). **Quyết định (10/08): GIỮ lật**
vì (i) **lật một lần → sau khỏi lật lại**, (ii) **DoD-compatible** — làm thừa yêu cầu #110 (filter vẫn chạy)
+ dọn un-ratchet, không bỏ sót gì. Điều kiện-gate: xem note sau §1①.

**Lằn giữ nguyên:** chỉ WRITE `packages/kb`; **không đổi** chữ ký `kb.search` (FROZEN); giữ `EMBEDDING_DIM=8`
+ schema/RLS; **không fake-green** T6 (mentor S1: *"vá RĂNG T6"*); **không WRITE** engine (inject là #111).

---

## 1. Việc D17 — làm theo THỨ TỰ (test-first)

### ⓪ SÁNG (≤10 phút): 2 câu coordinate + Docker + nhánh
- **Với AIE-1 #111:** *"Đóng T6 = thêm inject `section_roles` từ `session_context.roles` vào `node.params`
  ở `interpreter.py:291`, cạnh `tenant_id` (identity, khỏi resolver). Bạn thêm ở D17 được không? Mình cấp
  test acceptance từ kb."*
- **Với SWE #112:** *"section_roles đã ở `session.roles` (eval_adapter:104, identity) → resolver/Protocol
  CHƯA cần cho D17. Chỉ 1 policy cần chốt: `roles` RỖNG thì thấy gì — `[]` (fail-closed, không cả public)
  hay resolve thành `["public"]`?"*
- `git fetch`; cắt `day17/de-fence-at-retrieval` trên `origin/main` **sau khi D16 (kb#18) merge**.
- Docker: `docker compose -f docker-compose.test.yml up -d --wait` + 2 DSN (`studio_owner`/`studio_app`).
> ①②④⑤ + ③a/③b chạy được **ngay**, không chờ 2 câu trên. Chỉ ③c (acceptance) muốn khớp câu chữ #111.

### ① Lật `KbSearchService.search` → cơ chế `PgKbSearch` — `src/studio_kb/search.py`
- `__init__(self, pool, embedding: EmbeddingService | None = None)`; `self._pg = PgKbSearch(pool, embedding
  or _default_stub())`; `search(...)` → `return await self._pg.search(...)` (chữ ký 4 tham số frozen).
- `_default_stub()` = adapter bọc `derive_vector` **dim-8** (SSOT `embeddings.py`/`ingest_callisto`). **Bắt
  buộc cùng không gian** vector đã seed `kb.chunks`, nếu không `KbSearchService(pool)` (T3 apps) truy vấn
  lệch → rỗng → T3 vỡ. Không hardcode gateway (owner AIE-1). Cập nhật docstring (bỏ "spec DE — NotImplemented").

> ⚠️ **ĐIỀU KIỆN-GATE cho cú lật (①②) — nếu KHÔNG đủ điều kiện thì HỎI Ý bạn TRƯỚC KHI bỏ lật, không tự
> quyết.** Lật chỉ giữ trong D17 nếu land SẠCH; các điều kiện phải đúng HẾT:
> 1. **Stub SSOT khớp T3:** `_default_stub()` cùng không gian `derive_vector` dim-8 với vector T3 apps seed →
>    `KbSearchService(pool)` tự XPASS (QĐ-U1). Nếu T3 vẫn rỗng/vỡ mà không sửa được **trong lane kb** → thiếu điều kiện.
> 2. **Wrinkle seed T1 khép được:** `_seed_chunk` seed kèm embedding dim-8 → `test_t1_idor` xanh, KHÔNG cascade
>    vỡ test khác. Nếu cascade rộng → thiếu điều kiện.
> 3. **Anti-tamper hoà giải được:** `test_leak_meta.py` khớp sau khi đổi. Nếu xoá `test_search_contract` / gỡ
>    xfail T1 làm anti-tamper mâu thuẫn không vá gọn → thiếu điều kiện.
> 4. **`apps/studio` không cần DE sửa** (QĐ-U1: AIE-1 không đụng call-site). Nếu land buộc phải WRITE apps →
>    **vượt lane**, thiếu điều kiện.
>
> **Nếu bất kỳ điều nào thiếu / "thiếu quá nhiều" → DỪNG, HỎI Ý bạn** (bỏ lật, lùi về #110-tối-thiểu:
> no-bypass teeth + T6 test + NOT NULL, T1 xanh qua `test_pg_kb`). **Không tự bỏ lật, không để suite đỏ.**

### ② Un-ratchet T1 + xoá contract test — `tests/test_leak.py`, `tests/test_search_contract.py`
- **Xoá `tests/test_search_contract.py`** (assert `NotImplementedError`, giờ sai).
- **Gỡ `@xfail` khỏi `test_t1_idor`** → RLS + `WHERE tenant_id` đóng → xanh thật.
- ⚠️ **Wrinkle seed:** `_seed_chunk` INSERT thiếu `embedding`; `PgKbSearch._SEARCH` có `AND embedding IS NOT
  NULL` → positive-inclusion trượt. **Sửa `_seed_chunk` seed kèm embedding dim-8** (`derive_vector(text)`) —
  hoàn thiện fixture placeholder, KHÔNG nới assert loại-trừ.
- `tests/test_leak_meta.py` (anti-tamper): sửa **cùng commit** nếu tên/shape đổi (khuôn D-13).

### ③ T6 — 3 mảnh, KHÔNG fake-green — `tests/test_leak.py` + file mới
**(a) GIỮ `test_t6_label_spoof` xfail — không gỡ, không xoá.** Đổi *reason string* cho rõ:
> `reason="T6 enforce bằng inject section_roles ở interpreter.py:291 (engine #111); kb-by-design trust
> input nên test gọi service trực tiếp này không đóng được ở kb — retire khi test T6-interpreter xanh."`

**(b) VIẾT no-bypass teeth (kb-lane, xanh, DE đóng một mình)** — `tests/test_no_bypass.py`:
- `section_roles=[]` → `[]` · `["hr"]` → không lọt finance/eng/public · không wildcard/`"*"`/None-là-tất-cả.
Chạy trên `PgKbSearch`/RLS (DB) + mirror `StaticKbSearch` (không DB) nếu rẻ.

**(c) VIẾT T6 label-spoof test = deliverable #110 (mức đầu, xanh).** Chứng minh **override → an toàn** — recipe
khai roles thừa **bị đè** bằng session-resolved trước khi tới `kb.search`:
```python
session_roles = ["public"]            # server-side đã-resolve (user chỉ public)
recipe_declared = ["finance"]         # client/recipe cố khai (spoof)
effective = session_roles             # cơ chế override (interpreter.py:291 sẽ làm) — ở test mô phỏng
hits = await kb_search.search(q, ANKOR, effective, k)
assert effective == ["public"] and no_finance_chunk(hits)   # client-khai bị bỏ qua + không rò
```
- Xanh **ngay** (mô phỏng override + `kb.search` thật). Đây là **acceptance spec** cho dòng inject #111 —
  khi #111 land, có test integration thật (engine/app, #111 lane) chứng minh interpreter đè thật.
- **KHÔNG vocab-guard** để ép `test_t6(a)` xanh (`confidential`∉vocab drop được, nhưng `public`-khai-`hr` vẫn
  lọt → răng giả). ⚠️ assert tại **giá trị `effective` vào `kb.search`**, không kiểu "service không raise".

### ④ NOT NULL — 1 test cho vế 2 airtight — `tests/test_pg_kb.py`
`schema.py:40-41` đã NOT NULL. Thêm test khẳng định: insert `section_role=NULL` → DB từ chối · search không
trả chunk role-null.

### ⑤ refusal cho câu cross-tenant · audit vừa carrier §7
`kb.search` trả `[]` ngoài scope = refusal (đã có). **Audit** = `kb-retrieve` event hiện hữu (tenant
người-hỏi + `citations:[]`, #111 phát) — không schema mới. DE không tự emit trace trong `kb.search`.

---

## 2. DoD #110 (phần DE) — đối chiếu

- [ ] **Áp mandatory filter tại retrieval** — ①: seam chính thức chạy cơ chế `PgKbSearch` + ③b no-bypass.
- [ ] **chunk-level tenant_id/section_role NOT NULL, fail-closed** — ④: DDL + test khẳng định.
- [ ] **viết T6 label-spoof test (client tự khai bị bỏ qua)** — ③c: acceptance test (override→safe, xanh) +
  ③a marker + ③b teeth. **Đóng thật ở interpreter** = inject #111 (engine, ngoài kb).
- [ ] **T1 IDOR pytest xanh** — ②: gỡ xfail `test_t1_idor` (RLS) + seed embedding.

---

## 3. Coordinate (bằng comment issue, KHÔNG WRITE lane khác)

- **AIE-1 #111 — CHÍNH:** thêm **inject `section_roles`** từ `session_context.roles` vào `node.params` ở
  `interpreter.py:291`, cạnh `tenant_id` (đè recipe khai — đóng `executors.py:139`). + test integration
  T6-interpreter thật. DE cấp ③c làm acceptance. Đây là **cách đóng T6 gọn nhất, không cần resolver**.
- **SWE #112:** `resolve_section_roles`/Protocol **CHƯA cần** (section_roles đã ở session, identity). Chỉ
  chốt **1 policy:** `roles` rỗng → `[]` (fail-closed) hay `["public"]`. INV-1 auth thật (JWT nuôi session)
  = việc lớn hơn, ngoài D17. SWE vẫn viết T1 test playground (#112).
- **AIE-2 #113:** golden case cross-tenant → dùng 8 case âm `callisto-golden-30-v1.yaml` (D16) làm nguồn.
- **`apps/studio` T3/T4:** DE land ① sao cho `KbSearchService(pool)` tự XPASS (QĐ-U1) — **không** WRITE apps.

---

## 4. Bằng chứng (env pinned 3.14 · Postgres 5433 sống · skip ≠ pass)

- `git fetch` sau D16 merge; Docker up + 2 DSN **TRƯỚC** khi test (skip ≠ pass — O3.2). T1/no-bypass **cần DB**.
- `test_leak.py`: **T1 xanh thật** (gỡ xfail + seed embedding); **T6(a) giữ xfail** (reason mới).
  `test_search_contract.py` **đã xoá**; `test_leak_meta.py` khớp (cùng commit).
- **Mới xanh:** ③b no-bypass · ③c T6-override · ④ NOT NULL.
- **Toàn suite kb xanh** (cần Docker) · `ruff`/`ruff format`/`mypy` sạch · **`lint-imports` KEPT** (③c
  **không** import engine/workbench). Golden-set D16 byte-identical không đụng.
- Interpreter **3.14** (`.venv/bin/python` / `uv run --python 3.14`), **không `python3` trần**.
- Mutation sweep glue mới. Canh riêng: mutant "bỏ `WHERE section_role`" phải bị bắt (hở T6 im lặng).

---

## 5. Còn treo / ngoài phạm vi hôm nay

- **Inject `section_roles` ở `interpreter.py:291` (đóng T6 thật) = #111 (engine)** — DE cấp acceptance, không WRITE engine.
- **`resolve_section_roles` / Protocol / mapping vai-org→section = HOÃN** — chưa cần (section_roles đã ở
  session, identity). Chỉ dựng nếu sau này có tầng vai-org thật ≠ section labels (mini-RFC).
- **Auth thật (JWT nuôi session) — production T6 kín = ngoài D17** (hiện stub: eval tay + header giả). D17
  chỉ mức đầu (session eval-fed).
- **Policy roles-rỗng** (`[]` vs `["public"]`) = chốt với #112, không chặn code DE.
- **Retire xfail `test_t6(a)`** = sau khi #111 inject + test T6-interpreter xanh, commit riêng + sửa
  `test_leak_meta.py`. KHÔNG D17.
- **Audit-event mới** = mini-RFC (trace-event §5 khoá 6 node_type) → out-of-scope.
- **Trạng thái:** plan execute-ready. Chưa cắt nhánh. Mai: ⓪ 2 câu coordinate + Docker → **①②④⑤ + ③a/③b +
  T1** chạy ngay (không chờ ai) → ③c khớp câu chữ #111. Nhịp D14/D15: code → PR → review.
