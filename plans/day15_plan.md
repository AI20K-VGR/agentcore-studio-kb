# Plan D15 (DE) — Trace viewer đủ `timeline+tokens+cost+citations` (ordering monotonic) + tenant filter tại retrieve (đầu, CHUẨN BỊ fence D17)

> **Ngày:** 2026-08-07 (D15, Thứ Sáu · Chặng 2 / Sprint 2 · Tuần 3) · **Bút:** DE (Nguyễn Đông Anh)
> **Anchor:** issue kit **#100** (con của **#104** "Trace viewer + tenant filter tại retrieve ·
> Integration Friday"). Anh em: AIE-1 **#101** (6 executor chạy trong batch ghép thật; xác nhận
> emit trace đúng schema) · SWE **#102** (Playground: bấm Test 1 recipe → interpreter chạy → trace
> viewer hiện) · AIE-2 **#103** (Scorecard skeleton đọc trace của run thật; playground-trace UX ghép).
> **Repo WRITE: `agentcore-studio-kb`** · kit READ. **Milestone:** Sprint 2 — Gate Day 20.
>
> Việc DE (#100, dòng tiêu đề): *"**Chủ công**: trace viewer (timeline từng node, tokens/cost/
> citations, ordering monotonic) + tenant filter tại retrieve (chuẩn bị fence D17)."* DoD 3 ô (trace
> viewer render timeline+tokens+cost+citations · tenant filter tại retrieve 0-leak (đầu) · Integration
> Friday 4-mảng recording) là **DoD chung kế thừa từ cha #104** — đọc là **"phần DE của 3 ô đó"**: ô
> Integration Friday là buổi ghép cả nhóm (#101/#102/#103 nối vào), DE cấp **phía trace-viewer đọc**;
> DE không viết playground (#102) hay scorecard (#103).

---

## 0. Đọc cho đúng trước khi cắt — D15 là VIẾT DÀY cái đã có + DỌN GROUND cho D17, KHÔNG lật fence hôm nay

Bốn điều đặt lằn ranh của ngày:

**(a) Nền phải là main MỚI — D14 đã đóng.** PR kb **#15** (`feat D14 — golden query grid inputs +
golden-set 30`) **đã MERGED** (06/08, `b57ba78`); `kit#140` merged; `kit` đang ở nhánh
`chore/bump-submodules-d14` (`eb8138a`) đã bump pointer. Local kb có thể còn đứng nhánh D14. →
**`git fetch` + cắt `day15/de-trace-viewer-tokens-tenant-prep` trên `origin/main` MỚI**, KHÔNG xây
tiếp trên nhánh D14 (refresh local mỗi ngày — đừng coi nhánh checkout là bất khả xâm phạm).

**(b) Trace-reader ĐÃ tồn tại gần đủ — D15 là BỔ `tokens`, không viết lại.** `trace_reader.py`
(bút DE, D5/D9) đã có `sort_events` · `check_walk` (0-gap) · `render_timeline` · `PgTraceReader.
read_run` · `walk_from_dag`. **Khe hở thật của D15:** `render_timeline` (dòng 259-264) in
`node_type · node_id · cost · citations` **nhưng KHÔNG in `tokens`** — mà DoD ghi rõ
"timeline+**tokens**+cost+citations". `TraceEvent.tokens` (`Tokens{prompt,completion}`) đã có sẵn
trong event (`_row_to_event` dòng 325 dựng đủ, `PgTraceReader` đọc đủ) — chỉ **chưa phơi ra dòng
render**. Đây là sửa nhỏ + có răng, không phải tính năng mới.

**(c) "tenant filter tại retrieve" D15 là ĐẦU (chuẩn bị fence D17), KHÔNG un-ratchet `KbSearchService`.**
`search.py::KbSearchService.search` còn `NotImplementedError` **cố ý** — un-ratchet (flip → delegate
+ gỡ `test_leak` xfail T1/T6) là **D17 (#110)**, mentor chốt (README P5/P9, xfail strict=False). D15
**giữ nguyên** `NotImplementedError` + **giữ nguyên 2 xfail** (không sửa test để pass). Phần "đầu" của
D15 = **củng cố + phơi bằng chứng** đường filter tại retrieve đã đúng ở tầng `PgKbSearch`/RLS (fence
2 trục: RLS `tenant_id` + `WHERE section_role`), và **dựng scaffold** để D17 chỉ việc lật — không
đụng seam chính thức hôm nay.

**(d) Integration Friday là buổi GHÉP CẢ NHÓM, "recording" nằm NGOÀI kb.** 4 mảng ghép thật
(interpreter #101 → KB retrieve → trace viewer DE → scorecard #103, canvas #102). DE cấp **phía
trace-viewer đọc-lại** để buổi ghép có cái nhìn; bản ghi (daily-note/evidence) sống ở `docs/reports`
(submodule ngoài kb) — **chỉ làm khi được yêu cầu**, không WRITE vào lane khác.

Lằn giữ nguyên: **chỉ WRITE trong `packages/kb`**; **không đụng** engine (#101), workbench/playground
(#102), evalhub/scorecard (#103), `apps/studio` obs-writer (DE chỉ READ phía ghi trace). Bàn giao
bằng **hàm + tài liệu trong kb**, không viết sang repo khác. **KHÔNG lật `KbSearchService`, KHÔNG gỡ
xfail** (để D17). Giữ `EMBEDDING_DIM=8`, không đụng schema (chống schema-drift — dặn mentor S1).

---

## 1. Việc sẽ làm (nhánh `day15/de-trace-viewer-tokens-tenant-prep`, nền `origin/main` MỚI · test-first)

### ① `render_timeline` — phơi `tokens` ra dòng timeline (DoD ô 1: "…+tokens+…")
Thêm `tokens` (prompt/completion) vào mỗi dòng render, cạnh `cost`/`citations` đã có. Nguồn =
`event.tokens: Tokens{prompt,completion}` (đã có trong event, không tính lại). Hình dạng đề xuất
(giữ 1 dòng/node, dễ đọc lúc gỡ lỗi):
```
  {i}. {ts}  {node_type:<12} node={node_id:<6} tok={prompt}/{completion:<6} cost={cost:<8} citations=[…]
```
Lưu ý trung thực: `llm-step` hiện `tokens=Tokens(0,0)` (LLM là fixture replay, `executors.py`) — viewer
in `0/0` là **đúng sự thật hiện trạng**, không được bịa số. "Cost cùng-1-số từ tokens" là **D19 (#120)**;
D15 chỉ **phơi** tokens/cost đã ghi trong trace, không dựng lineage `tokens→cost`.

### ② Ordering monotonic — phơi tường minh trong viewer (DoD ô 1: "ordering monotonic")
Hiện `sort_events` **âm thầm** xếp lại theo `ts`; `check_walk` chỉ kiểm 0-gap (thiếu/trùng `node_type`),
**không** kiểm thứ tự phát ra có đơn điệu không. Thêm một phép **kiểm monotonic** (mỗi `ts` ≥ `ts`
trước, đọc theo thứ tự event **gốc** trước khi sort) và cho `render_timeline` **nói ra**: `✓ ordering
monotonic` hoặc `⚠ có đảo thứ tự tại event k` — thay vì lặng lẽ sửa. Lý do: một viewer chỉ biết sort
rồi in thì luôn trông đẹp; DoD đòi *bằng chứng* thứ tự phát đúng, không phải viewer tự vá.
> **Điểm cần chốt với cha #104 / hợp đồng `trace-event.v0.md`:** "monotonic" đo trên `ts` (TEXT, đang
> dùng) hay trên cột `seq/ordering` (12-cột sink, `_READ_RUN` **chưa** select `seq`). Mặc định D15:
> đo trên `ts` (dữ liệu reader đang có), và ghi honest-TODO nếu cần đọc thêm `seq` — không tự mở rộng
> `_READ_RUN` nếu chưa cần. Xác nhận trước khi khoá.

### ③ tenant filter tại retrieve — 0-leak (ĐẦU) · chuẩn bị fence D17 (KHÔNG lật `KbSearchService`)
- **Giữ nguyên** `KbSearchService.search = NotImplementedError` + `test_leak` T1/T6 `xfail` (un-ratchet
  = D17). **Không sửa test để pass.**
- **Củng cố + phơi bằng chứng** đường filter đã đúng ở tầng thật `PgKbSearch` (`postgres.py`): RLS
  `FORCE` khoá `app.tenant_id` (trục tenant) + `WHERE section_role = ANY(%s)` (trục section) + pool
  **non-owner** để RLS cắn. D15 rà lại `test_pg_kb`/`test_leak_meta`/`test_rls_framework` phủ đủ ca
  "đầu": T1 IDOR (đọc chéo tenant) trả `[]`/0-leak trên đường `PgKbSearch`; unset-tenant thấy 0 dòng.
- **Dựng scaffold cho D17** (không thực thi fence hôm nay): đánh dấu rõ trong `search.py` docstring +
  `test_leak.py` chỗ D17 sẽ lật (delegate `KbSearchService`→`PgKbSearch` + gỡ xfail), để D17 là thao
  tác cơ học có chủ đích, không phải khảo cổ. Nếu cần một test mới cho "đầu", đặt tên tách (không đụng
  `test_search_contract` XANH đang khẳng định `NotImplementedError`).

### ④ Tests — test cho glue mới (không đụng test cũ đang XANH)
- `test_trace_reader.py`: thêm ca **render có `tokens`** (event `tokens=137/42` phải hiện đúng trên
  dòng, không phải `0/0` cứng) + ca **monotonic** (chuỗi đảo `ts` → viewer báo `⚠`, chuỗi đúng →
  `✓`). Giữ nguyên mọi test cũ (`test_du_4_node_thi_0_gap`, `test_ts_sai_dinh_dang_thi_raise`, …).
- Phần ③: chỉ **thêm** ca phủ nếu cần; **không** gỡ xfail, **không** sửa `test_search_contract`.

---

## 2. DoD #100 (phần DE) — đối chiếu

- [ ] **Trace viewer render timeline+tokens+cost+citations** — ①: `render_timeline` phơi thêm
  `tokens` (đã có `cost`/`citations`); ②: nói rõ `ordering monotonic ✓/⚠`. Chạy được không cần DB
  (nhóm thuần) + `PgTraceReader` đọc thật khi có DB.
- [ ] **tenant filter tại retrieve 0-leak (đầu)** — ③: giữ fence 2 trục ở `PgKbSearch`/RLS, phủ T1
  0-leak trên đường thật; **chuẩn bị** D17, **không** lật `KbSearchService` (giữ `NotImplementedError`
  + 2 xfail). "0-leak (đầu)" = đường `PgKbSearch` đã kín; seam chính thức đóng hoàn toàn là D17.
- [~] **Integration Friday 4-mảng recording** — DE cấp **phía trace-viewer đọc-lại** cho buổi ghép
  (#101 interpreter → retrieve → trace viewer → #103 scorecard, canvas #102). **Recording** (evidence/
  daily-note) sống ở `docs/reports` — **ngoài kb**, coordinate; không DE-gated, không WRITE lane khác.

---

## 3. Bàn giao / ghép Integration Friday — bằng hàm + tài liệu TRONG kb

- `render_timeline(events, expected=walk_from_dag(recipe.dag))` là đường buổi-ghép in timeline một run
  thật; truyền `expected` từ recipe (không dựa hằng `EXPECTED_WALK` — nó chỉ đúng cho chuỗi thẳng 4 node).
- `PgTraceReader.read_run(run_id, tenant_id: UUID)` cho #102/#103 đọc-lại trace của run thật (tenant là
  **UUID**, không slug — D-13). Bảng `obs.trace_events` **không RLS** → mệnh đề `tenant_id` trong SQL là
  hàng rào **duy nhất**; đã có `test_db_khong_doc_cheo_tenant` canh.
- `tokens`/`cost` hiện là số **đã ghi trong trace** (llm-step `0/0` do fixture) — viewer **đọc**, không
  tính lại; "cùng-1-số tokens→cost" là D19. Ghi rõ để #103 không tự cộng lại lệch nguồn.
- Ghi ở docstring `trace_reader.py` + design-note trong kb; **không post sang engine/workbench/evalhub**.

---

## 4. Bằng chứng (env pinned 3.14 · Postgres sống port 5433 · skip ≠ pass)

- **`git fetch` trước** — D14 PR#15 đã merged; cắt `day15/de-trace-viewer-tokens-tenant-prep` trên
  `origin/main` mới (không nền nhánh D14).
- `docker compose -f docker-compose.test.yml up -d --wait` + 2 DSN (`studio_app`/`studio_owner`)
  **TRƯỚC** khi chạy test/viết báo cáo (SOP; skip ≠ pass — O3.2). Nhóm thuần trace-reader chạy
  không-DB; nhóm DB (`test_pg_kb`/`PgTraceReader`) cần Docker sống.
- `test_trace_reader.py` xanh: ca `tokens` hiện đúng + ca monotonic `✓/⚠` + **mọi test cũ giữ xanh**.
- `test_leak.py` T1/T6 **vẫn `xfail`** (cố ý, un-ratchet = D17); `test_search_contract` **vẫn XANH**
  (`KbSearchService.search` còn `NotImplementedError`). Không sửa test để pass.
- **Toàn suite kb xanh** (cần Docker cho `test_pg_kb`) · `ruff` sạch · `mypy` sạch · `lint-imports` KEPT.
- Interpreter **3.14** (`.venv/bin/python` hoặc `uv run --python 3.14`), **không `python3` trần**
  (local 3.11 — bẫy quen; check lại interpreter trước khi báo mọi SyntaxError).
- Mutation sweep cho glue mới (`render_timeline` nhánh tokens/monotonic); code mới không phát sinh lỗ.

---

## 5. Còn treo / ngoài phạm vi hôm nay

- **Un-ratchet `KbSearchService` (flip → `PgKbSearch`) + gỡ `test_leak` xfail T1/T6 = D17 (#110)** —
  KHÔNG làm ở D15. D15 chỉ "đầu" + scaffold. T6 đóng hoàn toàn còn cần INV-1 server-side (SWE #112, D17).
- **golden-set 30 case ĐẦY ĐỦ final = D16 (#105)** — hiện `callisto-handbook-30-draft.yaml` là draft.
- **Cost-lineage `tokens→cost` một-nguồn = D19 (#120)** — D15 chỉ **phơi** tokens/cost đã ghi, không
  dựng lineage; llm-step `0/0` là hiện trạng thật, không bịa.
- **Nhãn tay ground-truth (agreement) = D18 (#115)** — không D15.
- **Chốt "monotonic đo trên `ts` hay `seq`"** — xác nhận với cha #104 / `trace-event.v0.md` trước khi
  khoá; mặc định `ts`, honest-TODO nếu cần select thêm `seq` trong `_READ_RUN`.
- **Integration Friday recording / daily-note `docs/reports`** nằm **ngoài** submodule kb — chỉ làm
  khi được yêu cầu (chỉ đạo: WRITE trong kb).
- **Chưa commit/push, chưa mở PR** — chờ review (đúng nhịp D12/D13/D14).
