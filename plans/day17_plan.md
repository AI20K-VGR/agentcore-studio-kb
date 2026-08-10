# Plan D17 (DE) — Fence TẠI RETRIEVAL fail-closed: lật `KbSearchService`→`PgKbSearch` + đóng T1 IDOR + viết T6 label-spoof test (mức đầu, mock resolver)

> **Ngày:** 2026-08-11 (D17, Thứ Ba · Chặng 2 / Sprint 2 · Tuần 4) · **Bút:** DE (Nguyễn Đông Anh)
> **Anchor:** issue kit **#110** (con của **#114** "Fence tại retrieval fail-closed + T1 IDOR + T6
> label-spoof xanh"). Anh em: AIE-1 **#111** (executor tenant-scoped + refusal path) · SWE **#112**
> (**Own INV-1**: `session_id`→`{tenant,user,roles}` server-side + Tenant-Wall wiring + viết **T1** test
> qua playground) · AIE-2 **#113** (thêm golden case cross-tenant → scorecard chấm refusal).
> **Repo WRITE: `agentcore-studio-kb`** · kit READ. **Milestone:** Sprint 2 — Gate Day 20.
>
> Việc DE (#110): *"**Áp mandatory filter tại retrieval** trên `kb.search` (chunk-level `tenant_id`/
> `section_role` NOT NULL, fail-closed); **viết T6 label-spoof test** (client tự khai bị bỏ qua)."*

---

## 0. Bức tranh đã CHỐT (đọc 2 phút rồi vào §1)

**Kiến trúc T6 — hướng A (SWE #112 chốt, verify code khớp):**
```
session → resolve_session → ResolvedContext{tenant_id, user, roles}      [SWE, tenant_wall.py — ĐÃ CÓ]
             → resolve_section_roles(...) → section_roles                 [SWE #112 — CHƯA CÓ, mai làm]
                  → (đè client-khai) → kb.search(query, tenant_id, section_roles, top_k)   [DE]
```
- **Lỗ T6 nằm ở `engine/executors.py:139`** (`node.params.get("section_roles", [])` → `:155` truyền
  thẳng vào `kb.search` — TIN client/recipe khai). `tenant_id` được `interpreter.py:291` bơm server-side,
  `section_roles` thì **chưa**. Sửa lỗ = resolve server-side ở **executor** (engine #111) dùng resolver
  của #112.
- **`KbSearchService` (kb) CHỈ trust list nhận được** — không tự hỏi session (chữ ký FROZEN 4 tham số,
  không mang danh tính; `contracts/kb.py:4` + `kb-search.v0.md §5.2` nói rõ). **kb KHÔNG phải chỗ chặn
  T6**, mà là chỗ *tin* danh sách đã-resolve.

**4 điều đã settle (không cần bàn lại):**
1. **B1 embedding** — `KbSearchService.__init__(self, pool, embedding=None)`, self-provision stub
   `derive_vector` khi None (giữ QĐ-U1: `KbSearchService(pool)` của T3 apps dựng được, AIE-1 không sửa).
2. **T1** đóng được **một mình** ở kb (RLS + `WHERE tenant_id`).
3. **T6 test là deliverable RIÊNG của DE, KHÔNG có người dự phòng** — đọc kỹ 5 issue: chỉ #110 có "viết
   T6 test"; #112 viết **T1** test, #111 lo tenant-scope+refusal, #113 golden cross-tenant (T1). Bỏ = dòng
   DoD nhóm "T6 xanh (đầu)" hụt, truy về DE. → **BẮT BUỘC viết.** Nó là **acceptance test** cho resolver
   #112 (test-first).
4. **Audit** vừa carrier trace-event có sẵn (`§7`: `tenant_id`+`inputs_hash`+`citations:[]`+`outputs`) —
   KHÔNG cần node_type mới.

**1 điều CHƯA chốt — phải handshake SÁNG mai trước khi viết test (③c):**
> **Signature `resolve_section_roles`** — SWE mới **ĐỀ XUẤT** trong tin nhắn (`(ctx: ResolvedContext)->
> list[str]`), **chưa ghi ở đâu bền**, `contracts/` chưa có Protocol nào cho nó (đã grep). Cần chốt công
> khai ở issue #112/#110. **Đề xuất DE: dùng primitive** `resolve_section_roles(tenant_id: UUID, roles:
> list[str]) -> list[str]` thay vì nhận `ResolvedContext` — vì `ResolvedContext` sống ở `studio_workbench`,
> nếu Protocol đặt ở `contracts` mà tham chiếu nó thì phải move nó sang contracts (ngược tầng import-linter);
> primitive tránh được. Chốt cái này = mock của DE (③c) đúng ngay, khỏi rework.

**Lằn giữ nguyên:** chỉ WRITE trong `packages/kb`; **không** đổi chữ ký `kb.search` (FROZEN); giữ
`EMBEDDING_DIM=8` + schema/RLS; **không fake-green** T6 (mentor S1 dặn *"vá RĂNG T6"* = răng thật).

---

## 1. Việc D17 — làm theo THỨ TỰ này (test-first)

### ⓪ SÁNG (≤10 phút, trước khi code): 1 handshake + cắt nhánh
- **Chốt signature `resolve_section_roles` với SWE** ở comment issue #112 (đề xuất primitive — §0). Lấy 👍
  công khai. Đây là **thứ duy nhất** cần chốt; ①②④⑤ chạy được ngay cả khi chưa có, chỉ ③c cần nó.
- `git fetch`; cắt `day17/de-fence-at-retrieval` trên `origin/main` **sau khi D16 (kb#18) merge**.
- Docker: `docker compose -f docker-compose.test.yml up -d --wait` + 2 DSN (`studio_owner`/`studio_app`).

### ① Lật `KbSearchService.search` → cơ chế `PgKbSearch` (kb lane, làm ngay) — `src/studio_kb/search.py`
- `__init__(self, pool, embedding: EmbeddingService | None = None)`; body:
  `self._pg = PgKbSearch(pool, embedding or _default_stub())`.
- `search(query, tenant_id, section_roles, top_k)` → `return await self._pg.search(...)` (uỷ quyền 1 dòng,
  chữ ký giống hệt 4 tham số frozen).
- `_default_stub()` = adapter bọc `derive_vector` **dim-8** (cùng SSOT `embeddings.py`/`ingest_callisto._FixtureEmbedding`).
  **Bắt buộc cùng không gian** vector đã seed vào `kb.chunks`, nếu không `KbSearchService(pool)` (T3 apps)
  truy vấn lệch không gian → rỗng → T3 vỡ. Không hardcode gateway (owner AIE-1).
- Cập nhật docstring `search.py` (bỏ "spec DE — NotImplementedError").

### ② Un-ratchet T1 + xoá contract test — `tests/test_leak.py`, `tests/test_search_contract.py`
- **Xoá `tests/test_search_contract.py`** (assert `NotImplementedError`, giờ sai → đỏ nếu giữ).
- **Gỡ `@pytest.mark.xfail` khỏi `test_t1_idor`** → RLS + `WHERE tenant_id` đóng → xanh THẬT.
- ⚠️ **Wrinkle seed:** `_seed_chunk` hiện INSERT `(chunk_id,tenant_id,section_role,text)` — **thiếu
  embedding**; mà `PgKbSearch._SEARCH` có `AND embedding IS NOT NULL`. → **sửa `_seed_chunk` seed kèm
  embedding dim-8** (`derive_vector(text)`), nếu không positive-inclusion `"chunk-a-1" in results` TRƯỢT.
  Đây là **hoàn thiện fixture cho test placeholder**, KHÔNG nới assert loại-trừ.
- `tests/test_leak_meta.py` (anti-tamper): sửa **cùng commit** nếu tên/shape leak-test đổi (khuôn D-13).

### ③ T6 — 3 mảnh, KHÔNG fake-green — `tests/test_leak.py` + file test mới
**(a) GIỮ `test_t6_label_spoof` xfail — KHÔNG gỡ, KHÔNG xoá.** Chỉ **đổi reason string**:
> `reason="T6 enforce ở resolver (executor, #112 INV-1); kb-by-design trust input nên test gọi service
> trực tiếp này KHÔNG đóng được ở kb — retire khi test T6-executor xanh (#111/#112)."`

Lý do: test này gọi `KbSearchService` **trực tiếp** với `["confidential"]`, kb trust input → không bao giờ
pass ở tầng kb. Là **marker un-ratchet**; xoá = mất phiếu-ghi-nợ + đụng anti-tamper. **Retire về sau**, có
phối hợp (sau khi executor đóng T6 thật + sửa `test_leak_meta.py`).

**(b) VIẾT no-bypass teeth (kb-lane, xanh, DE đóng một mình)** — file `tests/test_no_bypass.py` (hoặc thêm
vào `test_pg_kb.py`):
- `section_roles=[]` → `[]` (không hiểu là "bỏ lọc"/trả hết).
- `section_roles=["hr"]` → **không** lọt chunk `finance`/`engineering`/`public` (chỉ `hr`).
- không nhánh wildcard/`"*"`/None-là-tất-cả.
Chạy trên `PgKbSearch`/RLS (Docker) + mirror `StaticKbSearch` (không DB) nếu rẻ.

**(c) VIẾT T6 label-spoof test = ACCEPTANCE cho resolver #112 (deliverable #110, mock resolver, xanh đầu)**
— file `tests/test_t6_label_spoof.py`, **kb-lane, KHÔNG import engine**:
```python
def fake_resolve(tenant_id, user_roles):   # signature ĐÃ CHỐT ở ⓪; mock cục bộ
    return ["public"]                       # user này chỉ được đọc public
client_declared = ["finance"]               # client/recipe cố khai finance (spoof)
resolved = fake_resolve(ANKOR, ["employee"])          # đè: bỏ qua client_declared
assert resolved == ["public"]                          # client-khai bị bỏ qua
hits = await kb_search.search(q, ANKOR, resolved, k)   # search bằng resolved, KHÔNG client_declared
assert no finance chunk in hits                        # → không rò
```
- Xanh **ngay với mock** (mock + `kb.search` thật). Chứng minh contract: *resolve-rồi-search thì client
  khai bị bỏ qua + kb an toàn* → đây là **spec mà resolver #112 phải thoả**. Khi #112 giao resolver thật +
  #111 wiring executor → thay mock bằng thật (hoặc test integration ở engine/apps do #111).
- ⚠️ Cảnh báo SWE: **assert tại giá trị vào `kb.search`** (là `resolved`), KHÔNG kiểu "service không raise"
  — assert sai chỗ thì mutation fail-OPEN `executors.py` không bị bắt.
- **KHÔNG vocab-guard** để ép `test_t6(a)` xanh (`confidential`∉vocab drop được, nhưng `public`-khai-`hr`
  vẫn lọt → răng giả).

### ④ NOT NULL — 1 test cho vế 2 airtight — `tests/test_pg_kb.py` (hoặc test_rls_framework)
`schema.py:40-41` đã `tenant_id/section_role NOT NULL` (DDL). Thêm 1 test khẳng định tường minh: insert
chunk `section_role=NULL` → DB **từ chối** (IntegrityError) · `kb.search` không trả chunk role-null.

### ⑤ refusal cho câu cross-tenant (đã có, chỉ xác nhận)
`kb.search` trả `[]` cho câu ngoài scope = refusal (§5.1/§6.1a, đã canh). **Audit** = `kb-retrieve` event
hiện hữu (tenant người-hỏi + `citations:[]`, do #111 phát) — carrier §7 đủ, **không** thêm event mới. DE
không tự emit trace trong `kb.search`. Enrich `outputs.fenced` = nicety #111 (coordinate, không chặn).

---

## 2. DoD #110 (phần DE) — đối chiếu

- [ ] **Áp mandatory filter tại retrieval trên `kb.search`** — ①: seam chính thức chạy cơ chế `PgKbSearch`
  (RLS tenant + `WHERE section_role` + rỗng→[] + lọc-trong-SQL) + ③b no-bypass (không cửa hậu).
- [ ] **chunk-level tenant_id/section_role NOT NULL, fail-closed** — ④: DDL đã có + test khẳng định.
- [ ] **viết T6 label-spoof test (client tự khai bị bỏ qua)** — ③c: acceptance test (mock resolver, xanh
  đầu) chứng minh client-khai bị bỏ qua + kb an toàn. ③a giữ marker, ③b răng kb. **Full closure** (executor
  gọi resolver thật) = #111/#112 (out-of-scope kb; coordinate).
- [ ] **T1 IDOR pytest xanh** — ②: gỡ xfail `test_t1_idor` (RLS đóng thật) + seed embedding.

---

## 3. Coordinate (bằng comment issue, KHÔNG WRITE lane khác)

- **SWE #112 — SÁNG (chặn ③c):** chốt signature `resolve_section_roles` (đề xuất primitive `(tenant_id,
  roles)->list[str]`, §0). Đây là điều DUY NHẤT chặn 1 phần việc — chốt xong ③c mock đúng ngay.
- **SWE #112 — cả ngày (song song):** SWE code resolver + mapping thật; DE mock ③c theo signature. Ráp ở
  composition root `apps/studio` sau. **Thứ chờ #112 xong hẳn = được retire xfail `test_t6(a)`** (không
  chặn code DE).
- **AIE-1 #111:** executor fix (`executors.py:139` gọi resolver) + test T6-executor thật (assert tại input
  `kb.search`) = **engine lane, DE không WRITE**. DE cấp ③c làm spec/acceptance. Nhắc `outputs.fenced` (⑤).
- **AIE-2 #113:** golden case cross-tenant → dùng 8 case âm `callisto-golden-30-v1.yaml` (D16) làm nguồn.
- **`apps/studio` T3/T4** (`test_kb_search_live_readiness`): DE land ① sao cho `KbSearchService(pool)` tự
  XPASS (QĐ-U1) — **không** WRITE apps.

---

## 4. Bằng chứng (env pinned 3.14 · Postgres 5433 sống · skip ≠ pass)

- `git fetch` sau D16 merge; nhánh trên `origin/main` mới.
- Docker up + 2 DSN **TRƯỚC** khi test (SOP; skip ≠ pass — O3.2). T1/no-bypass/T6-mock **cần DB** (RLS chỉ
  cắn qua non-owner pool).
- `test_leak.py`: **T1 xanh thật** (gỡ xfail + seed embedding); **T6(a) giữ xfail** (reason mới).
  `test_search_contract.py` **đã xoá**; `test_leak_meta.py` khớp (cùng commit).
- **Mới xanh:** ③b no-bypass · ③c T6-mock · ④ NOT NULL.
- **Toàn suite kb xanh** (cần Docker) · `ruff`/`ruff format --check`/`mypy` sạch · **`lint-imports` KEPT**
  (test ③c **không** import engine). Golden-set D16 byte-identical không đụng.
- Interpreter **3.14** (`.venv/bin/python` / `uv run --python 3.14`), **không `python3` trần** (local 3.11).
- Mutation sweep glue mới (lật seam + no-bypass + ③c). **Canh riêng:** mutant "bỏ `WHERE section_role`"
  phải bị bắt (hở T6 im lặng).

---

## 5. Còn treo / ngoài phạm vi hôm nay

- **Resolver `resolve_section_roles` + mapping role→section thật = #112 (SWE)** — DE mock, không viết thật.
- **Executor gọi resolver (`executors.py:139` fix) + test T6-executor thật = #111 (AIE-1, engine)** — DE cấp
  ③c làm acceptance; không WRITE engine.
- **Retire xfail `test_t6(a)`** = sau khi test T6-executor xanh (đóng lỗ thật) + sửa `test_leak_meta.py`,
  commit RIÊNG có phối hợp. **KHÔNG làm D17.**
- **Audit-event mới** = mini-RFC (trace-event §5 khoá 6 node_type) → out-of-scope; D17 chỉ refusal (⑤).
- **`ResolvedContext` move sang contracts** (nếu chốt signature nhận object thay primitive) = việc #112, coordinate.
- **Trạng thái:** plan sạch, execute-ready. Chưa cắt nhánh. Mai: ⓪ handshake signature + Docker → ①②④⑤ +
  ③a/③b chạy ngay (không chờ ai) → ③c sau khi chốt signature (mock). Nhịp D14/D15: code → PR → review.
