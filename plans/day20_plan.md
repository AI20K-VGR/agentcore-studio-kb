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

**2 DEPENDENCY THẬT — nhìn thẳng, verify SÁNG D20 trước khi dám ghi "xanh" (đừng fake-green gate):**

1. **T6 label-spoof "xanh" thật ⇐ inject `section_roles` = #111 (engine, AIE-1).** VERIFY code hôm nay:
   `interpreter.py:291` **mới inject `tenant_id`**, **CHƯA** `section_roles`; con trỏ `packages/engine`
   đang ở **D15** (`86b88ed`). Nghĩa là **#111 chưa land vào pointer kit thấy** → T6 hiện chỉ **mức-đầu
   kb-acceptance** (D17 ③c: mô phỏng override + `kb.search` thật + no-bypass teeth), **chưa** integration
   thật qua interpreter. **DoD #125 "T6 xanh" chỉ trọn khi engine bump có dòng inject.** Nếu D19 chưa kéo
   engine tới #111 → sáng D20 **hỏi AIE-1 #126** đã inject chưa; chưa thì T6 ở gate = mức-đầu + honest-TODO,
   **không** ghi "đóng thật".
2. **"cost cùng-1-số" ⇐ cost-lineage = D19 (#120), chưa land.** VERIFY code: `interpreter.py:389`
   `cost=_NO_COST` (0.0 cố định); docstring `:221` tự khai *"no real cost model exists yet, `obs.costs` is
   a schema-shell"*. **Không có hàm tokens→cost nào trong repo.** Cost-lineage invariant (§3.2: `cost` ở
   UI-test == trace == dashboard) **chưa chứng minh được** cho tới khi D19 land nguồn-1-số. D20 gate item
   này **kế thừa D19** — plan này giả định D19 (13/08) land đúng hẹn; nếu trượt → mang sang D20 (xem §1④).

**Lằn giữ nguyên (bám contract, INV-5 freeze):** chỉ WRITE `packages/kb`; **KHÔNG đổi** chữ ký `kb.search`
(§3.3 FROZEN: `(query, tenant_id, section_roles, top_k)`) và **KHÔNG đổi** tên/nghĩa khoá trace-event §3.2
(`tokens{prompt,completion}` · `cost` · `citations[]`); giữ `EMBEDDING_DIM=8` + schema/RLS; **KHÔNG WRITE**
engine (inject #111 là AIE-1 lane) hay apps (`obs.costs` là apps/studio); **KHÔNG fake-green** T6/cost ở gate.

---

## 1. Việc D20 — làm theo THỨ TỰ (chứng minh > viết mới)

### ⓪ SÁNG (≤15 phút): refresh + Docker + verify 2 upstream
- `git fetch` (đừng dùng fetch cũ trong phiên — remote đổi do người khác). Refresh local sang `origin/main`
  mới nhất; cập nhật con trỏ submodule (`git submodule update`), **verify pointer `packages/engine`** đã
  qua #111 chưa (`git -C packages/engine log --oneline | grep -i 'inject\|section_roles\|#111'`).
- Docker: `docker compose -f docker-compose.test.yml up -d --wait` + export 2 DSN (`studio_owner` 5433 /
  `studio_app`) **TRƯỚC** khi chạy bất kỳ test/ghi báo cáo (skip ≠ pass — O3.2). T1/T6/spine-live **cần DB**.
- **2 câu coordinate (comment issue, KHÔNG WRITE lane khác):**
  - **AIE-1 #126:** *"Con trỏ engine đã có dòng inject `section_roles` ở interpreter.py:291 (đóng T6 thật)
    chưa? Nếu rồi, mình bật assert integration T6 trong spine-live; chưa thì gate ghi T6 = mức-đầu kb."*
  - **Leader (cost-lineage seam):** *"D19 land nguồn tokens→cost một-số ở đâu — engine emit `cost` thật, hay
    reader/apps derive? DE cần biết để trace-viewer đọc CÙNG số với UI-test, không tính lại (§3.2 invariant)."*

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
- **T6 label-spoof:** chạy theo kết quả ⓪.
  - **Nếu #111 đã land** (engine inject `section_roles`): bật **assert integration** trong spine-live —
    recipe khai `section_roles=["finance"]` nhưng session `roles=["public"]` → interpreter đè → `kb.search`
    nhận `["public"]` → không rò finance-chunk. Đây là T6 **đóng thật** (§3.3: client tự khai bị bỏ qua).
  - **Nếu chưa:** giữ D17 mức-đầu (`test_no_bypass` teeth + acceptance mô phỏng override), gate ghi *"T6
    kb-acceptance xanh; integration-close chờ engine #111"* — honest-TODO, **không** ghi "đóng thật".
- **KHÔNG** vocab-guard / răng-giả để ép xanh; assert tại **giá trị `section_roles` thực vào `kb.search`**.

### ④ Trace viewer + cost cùng-1-số (§3.2 cost-lineage invariant)
- **Trace viewer:** `render_timeline` in timeline từng node của run thật ở ② (`tok=prompt/completion cost=…
  citations=[…]`), monotonic `ts` (`check_ts_monotonic`). Đã có — chứng minh render đúng run live.
- **Cost cùng-1-số:** **kế thừa D19.**
  - **Nếu D19 land:** thêm test khẳng định `cost` reader-đọc-từ-trace == số UI-test đọc (cùng nguồn, §3.2).
    DE **KHÔNG tính lại** cost trong `kb.search`/reader — chỉ **đọc** `cost` đã emit; nguồn-1-số ở
    engine/leader-seam (design-note §6: `obs.costs` ngoài fence-lane DE). Assert tái lập được (chạy 2 lần
    cùng số).
  - **Nếu D19 chưa land:** `cost=0.0` khắp nơi → invariant "khớp" một cách rỗng nghĩa. Ghi honest-TODO:
    *"cost-lineage nguồn-1-số = D19 chưa land; hiện `_NO_COST=0.0`, chưa chứng minh được lệch/khớp thật."*
    **Không** ghi "cost cùng-1-số ✅".

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
| INV-1 chặn `tenant`, **chưa** chặn `roles` (`section_roles` nhận-rồi-bỏ) | `section_roles` inject #111 (engine) — ⓪ verify | ✅/⏳ theo ⓪ |
| `obs.costs` ngoài fence-lane DE, DE điền D19 | cost-lineage D19 — ④ verify | ✅/⏳ theo ④ |
| `obs.golden_sets` nghi bảng-chết trùng `eval.golden_sets` → đề xuất DROP (mini-RFC schema-drift) | trạng thái mini-RFC `docs/mini-rfc-tenant-schema-unify.md` (đang M) | ghi trạng thái |
- Trung thực cả chỗ **lệch dự đoán** (mentor S1: giữ nhịp làm sạch, không giấu). Đây là input quyết scope tuần 5.

---

## 2. DoD #125 (phần DE) — đối chiếu

- [ ] **KB thật ingest→embed→index per-tenant** — ①: 1 lệnh dựng lại, 2 tenant, NOT NULL, idempotent.
- [ ] **`kb.search` cited** — ②③: spine-live citations grounded + shape §3.3.
- [ ] **tenant filter + T1 xanh** — ③: `test_t1_idor` xanh thật (RLS).
- [ ] **T6 label-spoof xanh** — ③: integration nếu #111 land, else kb-acceptance mức-đầu + honest-TODO.
- [ ] **trace viewer** — ④: `render_timeline` trên run live.
- [ ] **cost-lineage cùng-1-số** — ④: kế thừa D19; đọc-không-tính-lại; honest-TODO nếu D19 chưa land.
- [ ] **golden-set 30** — ⑤: 30 case + 10 nhãn tay, byte-identical.
- [ ] **plan-vs-actual** — ⑥: đối chiếu §6 design-note D11.
- [ ] **Demo spine 4 bước chạy thật** (DoD #129) — ② là xương sống demo.

---

## 3. Coordinate (comment issue, KHÔNG WRITE lane khác)

- **AIE-1 #126 — CHÍNH:** (a) xác nhận inject `section_roles` interpreter.py:291 (#111) đã vào pointer engine
  → mở khoá T6 integration ③; (b) 6 node-type executor chạy DAG thật qua EmbeddingService + bảng
  chunking×embedding trade-off (số) — DE cấp KB/golden làm nguồn, **không** viết executor.
- **SWE #127:** canvas 6-node + validator/graph-lint + INV-1 Tenant-Wall + T1 test playground. DE đảm bảo
  `kb.search` shape §3.3 để playground gọi được; **không** WRITE workbench.
- **AIE-2 #128:** eval harness v1 + scorecard verdict PASS/FAIL — tiêu thụ golden-30 + 10 nhãn tay (⑤) qua
  `golden_set_ref`/`scorecard_threshold` (§3.1/§3.4). DE không viết harness.
- **Leader (cost-lineage seam):** chốt nguồn tokens→cost một-số (engine emit vs apps derive) để trace-viewer
  DE đọc **cùng số** UI-test, không tính lại (§3.2). Liên quan `obs.costs` (apps, ngoài lane DE — design-note §6).

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

- **T6 integration-close** (assert đè `section_roles` thật qua interpreter) **phụ thuộc #111 (engine, AIE-1)**
  đã bump vào pointer kit. Nếu D20 sáng chưa land → T6 gate = kb-acceptance mức-đầu (D17) + honest-TODO, retire
  khi engine inject xanh. **DE không WRITE engine.**
- **cost-lineage nguồn-1-số** = **D19 (#120)**; nếu D19 trượt sang D20, đây là việc D20 nhưng cross-lane seam
  (engine emit / `obs.costs` apps) — coordinate leader, **không** DE tự tính lại cost trong `kb.search`/reader.
- **Auth thật (JWT nuôi `session.roles`)** = production T6 kín, ngoài S2 (hiện eval-fed + header stub) — INV-1 phần SWE.
- **`obs.golden_sets` DROP** (schema-drift) = mini-RFC `docs/mini-rfc-tenant-schema-unify.md` (đang M) → ghi
  trạng thái ở ⑥, không tự DROP một mình.
- **L2 gateway embed thật** (fixtures→gateway qua flag, INV-4) = stretch S3, không đổi storage (vẫn pgvector §4).
- **Trạng thái:** plan gate-ready. Nhịp: refresh → verify 2 upstream (⓪) → ①②③④⑤ chứng minh ghép → ⑥
  plan-vs-actual → PR → review ≤2 vòng. **Không fake-green T6/cost; skip ≠ pass; đọc trạng thái pointer engine
  trước khi khẳng định.**
