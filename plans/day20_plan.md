# Plan D20 (DE) — GATE-2: spine 4 quadrant ghép THẬT lần đầu qua 2 contract DE + plan-vs-actual vs design-note D11

> **Ngày:** 2026-08-14 (D20, Thứ Sáu · Chặng 2 / Sprint 2 · Tuần 4) · **Bút:** DE (Nguyễn Đông Anh)
> **Anchor:** issue **#125** (con của gate **#129**). Anh em: AIE-1 **#126** (6 node-type executor chạy DAG
> thật qua ES + bảng chunking×embedding) · SWE **#127** (canvas 6-node + validator/graph-lint + INV-1) ·
> AIE-2 **#128** (eval harness v1 + scorecard verdict PASS/FAIL). **Repo WRITE: `agentcore-studio-kb`** ·
> kit READ. **Milestone:** Sprint 2 — Gate Day 20.
>
> Việc DE (#125): *"KB thật ingest→embed→index per-tenant + `kb.search` cited + **tenant filter + T6
> label-spoof xanh** + trace viewer + cost-lineage cùng-1-số + golden-set 30."*
>
> DoD ngày (chung #129): Demo spine 4 bước chạy thật · AC executable xanh (canvas · KB thật retrieve +
> T1/T6 · trace viewer + cost cùng-1-số · eval v1 verdict · 6 node-type + trade-off số) · **plan-vs-actual
> đối chiếu** · review ≤2 vòng.

---

## 0. Bức tranh — D20 là GATE, không phải feature-day (đọc 3 phút rồi vào §1)

**D20 = money-shot §5.3 umbrella:** *"S2: … Happy-path spine chạy lần đầu (G4/D20)."* Gate giữa kỳ, quyết
scope tuần tới. Việc DE hôm nay **không phải viết tính năng mới** — là **CHỨNG MINH 4 quadrant ghép thật
qua 2 contract DE bút** ([§3.2 trace-event](../docs/contracts/trace-event.v0.md) · [§3.3 kb.search](../docs/contracts/kb-search.v0.md))
end-to-end, rồi **đối chiếu plan-vs-actual** với [design-note D11](../docs/design-notes/de-day11.md) §6.

**Cái gì ĐÃ có sẵn (land rải S2, D20 chỉ chứng minh ghép — không viết lại):**
| Deliverable #125 | Đã land ở | Bằng chứng hiện hữu |
|---|---|---|
| KB thật ingest→embed→index per-tenant | D12–D13 | `pipeline.py` · `scripts/ingest_callisto` · `kb.chunks` pgvector + RLS |
| `kb.search` cited | D13–D17 | `PgKbSearch.search()` trả `chunk_id` (§3.3 shape) |
| tenant filter + **T1 IDOR xanh** | **D17** | RLS + `WHERE tenant_id`; `test_t1_idor` đã gỡ xfail (kb#19/#20) |
| trace viewer | D14–D16 | `trace_reader.render_timeline` + `PgTraceReader.read_run` |
| golden-set 30 (+10 nhãn tay) | D16 + **D18** | `golden/callisto-golden-30-v1.yaml` (30 case · 10 `manual_label`) |

**1 DEPENDENCY còn treo (T6 đã đóng xong) — trạng thái tính tới 13/08 (sửa sau review AIE-2, kb#25 F1/F2 —
bản trước khai #111 sai "chưa land"; RE-VERIFY sáng D20 vẫn bắt buộc, remote đổi được qua đêm — đừng tin
bản ghi này thay `git fetch`):**

1. **T6 label-spoof "xanh" thật — ĐÃ ĐÓNG XONG.** #111 (engine, AIE-1) land 11/08 (kit#113, `a4e59ed`),
   một ngày TRƯỚC dry-run 12/08. Con trỏ `packages/engine` hiện ở `62773ba` (D17); `interpreter.py:324-325`
   inject **cả** `tenant_id` **lẫn** `section_roles` từ `session_context.roles`. Bài test tích hợp ở tầng
   interpreter (lane DE) đã **viết xong trong `kb#26`** và **gộp vào branch này** (`git merge`,
   commit `ce0276f`) — DoD #125 "T6 xanh" **đã trọn**. Không còn việc gì để làm ở ③ cho T6 nữa; mục ③
   dưới đây giữ nguyên phần mô tả kỹ thuật để tham chiếu, nhưng bản thân bài test đã xanh sẵn.
2. **"cost cùng-1-số" ⇐ cost-lineage — D19 (kb#22) ĐÃ LAND 13/08.** `src/studio_kb/cost.py` +
   `scripts/cost_table.py` đọc on-read từ `obs.trace_events`, cộng dồn `event.cost` đã lưu (không tính
   lại). **Nhưng `interpreter.py:438`** (con trỏ engine hiện tại) **vẫn `cost=_NO_COST`** (0.0) —
   `cost_of` chưa land ở `contracts` (Q-A, ngoài lane DE) và chưa được **AIE-1 (#121, còn mở)** wire tại
   emit. Cost-lineage invariant (§3.2: `cost` ở UI-test == trace == cost-table) **vẫn chưa chứng minh
   được bằng số thật** — "khớp" hiện vẫn rỗng nghĩa (0.0 khắp nơi). D20 gate item này giờ **kế thừa #121**,
   không còn kế thừa D19.

**Lằn giữ nguyên (bám contract, INV-5 freeze):** chỉ WRITE `packages/kb`; **KHÔNG đổi** chữ ký `kb.search`
(§3.3 FROZEN: `(query, tenant_id, section_roles, top_k)`) và **KHÔNG đổi** tên/nghĩa khoá trace-event §3.2
(`tokens{prompt,completion}` · `cost` · `citations[]`); giữ `EMBEDDING_DIM=8` + schema/RLS; **KHÔNG WRITE**
engine (T6-integration-test đã viết ở kb, KHÔNG sửa `interpreter.py`; cost `_NO_COST`→`cost_of` wire là
AIE-1 lane #121) hay apps (`obs.costs` là apps/studio); **KHÔNG fake-green** cost ở gate (T6 đã xanh thật).

---

## 1. Việc D20 — làm theo THỨ TỰ (chứng minh > viết mới)

### ⓪ SÁNG (≤15 phút): refresh + Docker + re-verify pointer (đừng tin bản ghi hôm qua)
- `git fetch` (đừng dùng fetch cũ trong phiên — remote đổi do người khác). Refresh local sang `origin/main`
  mới nhất; cập nhật con trỏ submodule (`git submodule update`), **verify lại** pointer `packages/engine`
  (tính tới 13/08 đã ở `62773ba`/D17, #111 land) và `packages/kb`-lane self chưa lệch gì thêm qua đêm.
- Docker: `docker compose -f docker-compose.test.yml up -d --wait` + export 2 DSN (`studio_owner` 5433 /
  `studio_app`) **TRƯỚC** khi chạy bất kỳ test/ghi báo cáo (skip ≠ pass — O3.2). T1/T6/spine-live **cần DB**.
- **1 câu coordinate còn lại (comment issue, KHÔNG WRITE lane khác) — AIE-1 #121, không còn #126:**
  - **AIE-1 #121 (cost seam):** *"`cost_of` cần land ở `contracts` trước khi engine wire tại emit (Q-A,
    DE không sửa `contracts`) — bạn định wire lúc nào? DE cần biết để cost-table/trace-viewer đọc CÙNG số
    với UI-test khi số thật chảy vào (§3.2 invariant)."* (Không còn câu hỏi #111/T6 — đã land VÀ bài test
    tích hợp DE-viết đã merge ở kb#26, không còn gì phải hỏi ai về T6.)

### ① KB thật per-tenant — chứng minh 1 lệnh dựng lại (clone-tươi-chạy-nguyên-lệnh)
- Chạy `scripts/ingest_callisto` (hoặc lệnh ingest chuẩn) trên DB tươi → `kb.chunks` có 2 tenant
  (`ankor`/`borea`), mỗi chunk `tenant_id`/`section_role` NOT NULL + `embedding` dim-8 (§4 ladder L1 pgvector).
- **AC:** đếm chunk per-tenant > 0; không chunk `section_role IS NULL` (fail-closed §3.3). Đây là "ingest→
  embed→index per-tenant **THẬT**" của #125 — bằng chứng = **re-index idempotent** (cùng seed → cùng KB,
  design-note §2), không phải file chép tay.

### ② Spine-live xanh — 4-node emit→sink→reader chạy THẬT (bằng chứng ghép §5/§6)
- `tests/test_spine_live.py`: `studio_engine.run()` thật trên recipe SWE + `StaticKbSearch`/`PgKbSearch` DE
  + `PgTraceWriter` → **đọc lại từ Postgres** bằng `PgTraceReader` DE. Không dựng `TraceEvent` tay (nếu
  emit-hook mất → bảng rỗng → đỏ dòng assert đầu, đúng ý).
- **AC:** `walk_from_dag` khớp `check_walk`; `citations` grounded (`test_citations_are_grounded` — chunk-id
  có thật trong kho Callisto, không bịa). Đây là "spine 4 bước chạy thật" của DoD #129 — **ghép qua contract,
  không mock lẫn quadrant** (§6 ranh giới vàng).

### ③ kb.search cited + T1/T6 — leakage=0 là AC CỨNG (§3.3 / INV-1)
- **T1 IDOR:** `test_t1_idor` xanh thật (RLS + `WHERE tenant_id`, đã gỡ xfail D17). Câu cross-tenant → `[]`
  (refusal + audit), không hallucinate.
- **T6 label-spoof: ĐÃ ĐÓNG XONG, bằng bài test CỦA CHÍNH KB.**
  `test_spine_live::test_t6_recipe_khai_section_roles_rong_hon_thi_phien_thang` đi qua `interpreter.run()`
  thật trên kho Callisto thật: recipe khai `kb_binding.scope="ankor/finance"` nhưng session
  `roles=["public"]` → interpreter đè (`interpreter.py:324-325`) → `kb.search` nhận `["public"]` → không
  rò finance-chunk. T6 **đóng thật** (§3.3: client tự khai bị bỏ qua).
  - **Vì sao không dừng ở bằng chứng engine** (`test_section_roles_server_resolve.py`, #111 — vẫn giữ,
    hai lane hai bằng chứng độc lập): kb#26 retire xfail dựa vào bài của engine, tức kb đi mượn bằng
    chứng cho một dòng DoD của chính mình. Đo được — gỡ hẳn dòng inject khỏi interpreter thì **cả 238
    test kb vẫn xanh**: kb có **0 coverage** cho bất biến nó đang tuyên bố.
  - Kb-side placeholder `test_leak.py::test_t6_label_spoof` đã **xoá** (không còn `xfail`),
    `test_leak_meta.py` repoint anti-tamper sang răng loại-trừ trong `test_no_bypass.py`.
- **KHÔNG** vocab-guard / răng-giả để ép xanh; assert tại **giá trị `section_roles` thực vào `kb.search`**
  — bài trên làm đúng vậy qua `_RolesCapturingKbSearch` (ghi lại input thật), **cộng** vế hệ quả đọc lại
  từ Postgres. Self-mutation đã chạy: M-1 (bỏ dòng inject) và M-2 (đè bằng chính giá trị recipe khai) đều
  bị bắt đỏ; hai vế có răng độc lập.

### ④ Trace viewer + cost cùng-1-số (§3.2 cost-lineage invariant)
- **Trace viewer:** `render_timeline` in timeline từng node của run thật ở ② (`tok=prompt/completion cost=…
  citations=[…]`), monotonic `ts` (`check_ts_monotonic`). Đã có — chứng minh render đúng run live.
- **Cost cùng-1-số:** **D19 (kb#22) đã land** — `aggregate_run_cost`/`PgCostReader`/cost-table CLI sẵn
  sàng, đọc on-read từ `obs.trace_events`, không materialize `obs.costs`. **Còn treo #121 (AIE-1):**
  `interpreter.py:438` vẫn `cost=_NO_COST` (0.0) — `cost_of` chưa land ở `contracts` (Q-A) + chưa được
  wire tại emit. Cho tới đó invariant "khớp" vẫn rỗng nghĩa (0.0 khắp nơi). Ghi honest-TODO: *"cost-lineage
  cỗ máy đã có (kb#22); nguồn số thật chờ #121 (AIE-1) wire `cost_of` tại emit — chưa chứng minh được
  lệch/khớp thật."* **Không** ghi "cost cùng-1-số ✅" cho tới khi #121 land và có test đối chiếu reader
  vs UI-test ra số khác 0.

### ⑤ Golden-set 30 — nguồn eval AIE-2 (#128)
- `golden/callisto-golden-30-v1.yaml`: 30 case, byte-identical không đụng (giữ nguyên D16). 10 `manual_label`
  (D18) là nguồn agreement-check cho LLM-judge #128. DE **không sửa** golden ở D20 (nhãn đã cấp D18) — chỉ
  xác nhận AIE-2 tiêu thụ được qua `golden_set_ref` (§3.1/§3.4).

### ⑥ plan-vs-actual — đối chiếu design-note D11 §6 (deliverable RIÊNG của gate)
Viết `docs/reports/de-d20-plan-vs-actual.md` (hoặc mục trong report gate), đối chiếu **từng điểm §6 "Điểm S2
đã biết"** của [de-day11.md](../docs/design-notes/de-day11.md):
| Dự đoán D11 (§6) | Actual D20 | Kết |
|---|---|---|
| Fence mới ở tầng retrieval, cần 1 điểm chặn dùng chung | Lật `KbSearchService`→`PgKbSearch` (D17): fence tại retrieval, 1 seam | ✅ đúng hướng |
| INV-1 chặn `tenant`, **chưa** chặn `roles` (`section_roles` nhận-rồi-bỏ) | `section_roles` inject #111 (engine) đã land 11/08; bài test tích hợp DE đã viết + gộp (kb#26) | ✅ đóng thật, không còn treo |
| `obs.costs` ngoài fence-lane DE, DE điền D19 | D19 (kb#22) land 13/08 nhưng KHÔNG build `obs.costs` — on-read từ `obs.trace_events`; số thật chờ #121 | ⏳ theo #121 (AIE-1) |
| `obs.golden_sets` nghi bảng-chết trùng `eval.golden_sets` → đề xuất DROP (mini-RFC schema-drift) | mini-RFC amendment D18 = kb#24, **APPROVED** 13/08; DROP còn chờ xác nhận AIE-1 (gate thay mentor); `eval.*` đã chốt (golden_sets KHÔNG CẦN, scorecards CẦN) | ghi trạng thái mới |
- Trung thực cả chỗ **lệch dự đoán** (mentor S1: giữ nhịp làm sạch, không giấu). Đây là input quyết scope tuần 5.

---

## 2. DoD #125 (phần DE) — đối chiếu

- [ ] **KB thật ingest→embed→index per-tenant** — ①: 1 lệnh dựng lại, 2 tenant, NOT NULL, idempotent.
- [ ] **`kb.search` cited** — ②③: spine-live citations grounded + shape §3.3.
- [ ] **tenant filter + T1 xanh** — ③: `test_t1_idor` xanh thật (RLS).
- [x] **T6 label-spoof xanh** — ③: ĐÃ XONG — #111 land + **kb có bài integration của riêng mình** (`test_spine_live::test_t6_recipe_khai_section_roles_rong_hon_thi_phien_thang`) + xfail đã retire.
- [ ] **trace viewer** — ④: `render_timeline` trên run live.
- [ ] **cost-lineage cùng-1-số** — ④: kb#22 (D19) đã land, đọc-không-tính-lại; honest-TODO chờ #121 (AIE-1) wire số thật.
- [ ] **golden-set 30** — ⑤: 30 case + 10 nhãn tay, byte-identical.
- [ ] **plan-vs-actual** — ⑥: đối chiếu §6 design-note D11.
- [ ] **Demo spine 4 bước chạy thật** (DoD #129) — ② là xương sống demo.

---

## 3. Coordinate (comment issue, KHÔNG WRITE lane khác)

- **AIE-1 #126:** 6 node-type executor chạy DAG thật qua EmbeddingService + bảng chunking×embedding
  trade-off (số) — DE cấp KB/golden làm nguồn, **không** viết executor. (T6 integration **đã đóng xong**
  ở kb#26, không còn gì để coordinate.)
- **AIE-1 #121 — cost seam:** khi nào wire `cost_of` tại emit (`interpreter.py:438`, thay `_NO_COST`)?
  Cần `cost_of` land ở `contracts` trước (Q-A, DE không sửa `contracts`). DE cần biết để trace-viewer đọc
  **cùng số** UI-test, không tính lại (§3.2).
- **SWE #127:** canvas 6-node + validator/graph-lint + INV-1 Tenant-Wall + T1 test playground. DE đảm bảo
  `kb.search` shape §3.3 để playground gọi được; **không** WRITE workbench.
- **AIE-2 #128:** eval harness v1 + scorecard verdict PASS/FAIL — tiêu thụ golden-30 + 10 nhãn tay (⑤) qua
  `golden_set_ref`/`scorecard_threshold` (§3.1/§3.4). DE không viết harness.

---

## 4. Bằng chứng (env pinned 3.14 · Postgres 5433 sống · skip ≠ pass)

- `git fetch` + refresh local + `git submodule update` **TRƯỚC** khi phát biểu trạng thái pointer engine.
- Docker up + 2 DSN **TRƯỚC** khi test (skip ≠ pass — O3.2). Spine-live/T1/T6 **cần DB**.
- Interpreter **3.14** (`.venv/bin/python` / `uv run --python 3.14`), **KHÔNG `python3` trần** (bẫy 3.11
  khi chỉ review — SyntaxError giả PEP 695/701/758).
- **5 bước CI đủ, không chỉ mypy:** `pytest` (toàn suite kb xanh, cần Docker) · `ruff check` · `ruff format
  --check` · `mypy` · `lint-imports` (`test_spine_live` import `studio_engine/app/workbench` chỉ TRONG test,
  không trong `src/` — `.importlinter` chỉ quét `studio_kb`).
- **Self-mutate trước review:** đột biến ĐÚNG dòng vừa đổi — vd mutant "bỏ inject `section_roles`" (nếu bật
  ③ integration) hoặc "reader tự tính lại cost thay vì đọc" (④) phải bị test bắt đỏ; `strict=True` kẻo XPASS
  nuốt câm. Xanh ≠ đúng.
- Golden-30 byte-identical (`git diff --stat golden/` rỗng). Mutation sweep glue mới nếu thêm test.

---

## 5. Còn treo / ngoài phạm vi hôm nay

- ~~T6 integration-close~~ — **KHÔNG còn treo.** #111 (engine, AIE-1) land 11/08; bài test tích hợp DE
  viết xong + gộp ở kb#26; `xfail` đã retire. Giữ dòng này để lịch sử review (F1) không mất dấu.
- **cost-lineage nguồn-1-số** = **D19 (kb#22) đã land** 13/08 (cỗ máy cộng dồn); số thật còn treo ở **#121
  (AIE-1, còn mở)** wire `cost_of` tại emit + `cost_of` land ở `contracts` (Q-A) — cross-lane seam, **không**
  DE tự tính lại cost trong `kb.search`/reader.
- **Auth thật (JWT nuôi `session.roles`)** = production T6 kín, ngoài S2 (hiện eval-fed + header stub) — INV-1 phần SWE.
- **`obs.golden_sets` DROP** (schema-drift) = mini-RFC amendment D18 (kb#24, **APPROVED** 13/08) giữ đề
  xuất DROP; còn chờ xác nhận AIE-1 (gate thay mentor) → ghi trạng thái ở ⑥, không tự DROP một mình.
- **L2 gateway embed thật** (fixtures→gateway qua flag, INV-4) = stretch S3, không đổi storage (vẫn pgvector §4).
- **Trạng thái:** plan gate-ready. Nhịp: refresh + re-verify pointer (⓪) → ①②③④⑤ chứng minh ghép (T6 đã
  xong từ kb#26, chỉ cần xác nhận lại ở ③; cost chờ #121 ở ④) → ⑥ plan-vs-actual → PR → review ≤2 vòng.
  **Không fake-green cost; skip ≠ pass; đọc trạng thái pointer engine trước khi khẳng định — kể cả bản
  ghi trong chính plan này.**
