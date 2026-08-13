# Bằng chứng D20 — phần DE (kb) · GATE-2 + plan-vs-actual

> **Mục đích:** phần DE trong evidence-pack GATE-2 (issue **#125**, con của gate **#129**). Chuẩn *"đủ để
> chấm không cần hỏi"* — mọi con số §2 **tái lập được** bằng khối lệnh §1, không tin lời khai. §3 là
> **plan-vs-actual** đối chiếu [design-note D11](design-notes/de-day11.md) §6 (DoD #129). §4 là 2 điểm còn
> treo đã biết (T6-integration — **lane DE** · cost-lineage — chờ AIE-1 **#121**) — nêu thẳng, không giấu.
>
> **Bối cảnh trung thực:** báo cáo gốc chạy **12/08 (D18)** như một **gate dry-run** — sớm 2 ngày so với D20
> (14/08). **Sửa sau review AIE-2 (kb#25, F1 — blocker):** bản gốc khai sai trạng thái con trỏ
> `packages/engine` — **#111 đã land từ 11/08** (kit#113, `a4e59ed`), một ngày TRƯỚC dry-run, không phải
> "chưa land" như bản gốc ghi; việc còn thiếu ở T6 là một bài test tích hợp tầng interpreter (**lane DE**,
> không phải chờ AIE-1) — xem §4.1. Riêng **D19 cost-lineage** (kb#22) và **mini-RFC amendment D18** (kb#24)
> đúng là chưa land lúc dry-run — cả hai đã **merge 13/08** (sau dry-run, trước gate 14/08); bản này cập
> nhật theo trạng thái mới nhất tính tới 13/08.

---

## 1. Chạy lại — khối lệnh dán-là-chạy

Từ **thư mục gốc của kit** (`agentcore-studio-kit/`):

```bash
docker compose -f docker-compose.test.yml up -d --wait

export STUDIO_DATABASE_URL_ADMIN=postgresql://studio_owner:changeme@localhost:5433/studio_test
export STUDIO_DATABASE_URL=postgresql://studio_app:changeme@localhost:5433/studio_test

uv run --python 3.14 pytest packages/kb -q                       # 225 passed, 1 xfailed, 0 skipped
uv run --python 3.14 python packages/kb/scripts/ingest_callisto.py   # ankor 71 · borea 69 · 140 chunk / 2 tenant
```

⚠️ **Hai dòng `export` là bắt buộc** (bài học O3.2): thiếu → test tầng DB **skip lặng lẽ**, `skip ≠ pass`,
và người đọc kết luận số 225 khai láo. Interpreter **pin 3.14** (`uv run --python 3.14`), không `python3`
trần (bẫy 3.11 → SyntaxError giả PEP 695/701/758).

---

## 2. Số đo — DoD #125 từng item

| Item #125 | Bằng chứng (test / lệnh) | Kết |
|---|---|---|
| **KB thật ingest→embed→index per-tenant** | `ingest_callisto.py`: **140 chunk / 2 tenant** (ankor 71 · borea 69), clone-tươi 1 lệnh · `test_pg_kb::test_ingest_idempotent_chay_lai_khong_nhan_doi` + `test_ingest_hai_tenant_moi_ben_chi_thay_phan_minh` | ✅ |
| **`kb.search` cited** (§3.3 shape) | `test_spine_live::test_citations_are_grounded` + `test_trace_la_nguon_citation_dung_duoc_cho_bo_cham` (chunk-id có thật kho Callisto) | ✅ |
| **tenant filter + T1 IDOR xanh** | `test_leak::test_t1_idor` **PASSED** (gỡ xfail D17, RLS + `WHERE tenant_id`) + `test_pg_kb::test_t1_khong_ro_ri_cheo_tenant` | ✅ |
| **T6 label-spoof** | **kb-mức-đầu:** `test_pg_kb::test_t6_khong_ro_ri_cheo_vai` + `test_no_bypass` (5/5: empty-roles→no-grant · không wildcard · public không thấy finance) **PASSED** · **integration:** `test_leak::test_t6_label_spoof` **XFAIL** (đúng thiết kế — gọi thẳng `KbSearchService`, không qua interpreter; #111 đã land 11/08, retire cần bài test tích hợp mới ở tầng interpreter — **lane DE**, xem §4.1) | ✅ mức-đầu / ⏳ integration test (DE, không phải upstream) |
| **trace viewer** | `test_trace_reader::test_render_timeline_*` (4 test: tokens · monotonic · tự-sắp-xếp · đủ/thiếu node) **PASSED** | ✅ |
| **cost-lineage cùng-1-số** (§3.2) | kb#22 (D19, merge 13/08) land cỗ máy cộng dồn (`aggregate_run_cost`/`cost_of`/`PgCostReader` + cost-table CLI), đọc on-read từ `obs.trace_events` — nhưng `interpreter.py:438` (con trỏ engine hiện tại) vẫn `cost=_NO_COST` (0.0): chưa wire `cost_of` tại emit (chờ AIE-1 **#121**, còn mở) | ⏳ (xem §4.2) |
| **golden-set 30** | `callisto-golden-30-v1.yaml`: **30 case · 10 `manual_label`** (D16 + nhãn tay D18) · `test_golden_set` **PASSED** | ✅ |
| **spine 4 bước chạy thật** (DoD #129) | `test_spine_live` **10/10 PASSED** (emit→sink→reader; INV-1 recipe-spoof-tenant→session thắng; refusal-from-grounding) | ✅ |

**Tổng suite kb:** `225 passed, 1 xfailed, 0 skipped`. Xfailed duy nhất = `test_t6_label_spoof`
(integration-close, retire khi bài test tích hợp DE-viết mới lên xanh — xem §4.1; #111 đã land).

---

## 3. Plan-vs-actual — đối chiếu design-note D11 §6 "Điểm S2 đã biết"

Design-note D11 (03/08) **nêu trước 4 điểm** sẽ lộ ở S2. D20 đối chiếu từng điểm — cả chỗ **khớp** lẫn chỗ
**còn treo**:

| # | Dự đoán D11 (§6) | Actual D20 | Kết |
|---|---|---|---|
| 1 | *"Fence mới ở tầng retrieval của KB stub… cần một điểm chặn dùng chung, không rải rác."* | D17 lật `KbSearchService`→`PgKbSearch`: fence tại retrieval **một seam** chính thức, fail-closed (§3.3). `test_no_bypass` chứng minh 1 chỗ chặn. | ✅ **đúng hướng, đã làm** |
| 2 | *"INV-1 mới chặn `tenant`, chưa chặn `roles`… `section_roles` nhận-rồi-bỏ."* | **kb-lane đã chặn roles** tại `PgKbSearch` (`test_t6_khong_ro_ri_cheo_vai` + no-bypass PASSED). **Sửa sau review kb#25 F1:** #111 **đã land** 11/08 (kit#113, một ngày TRƯỚC dry-run) — con trỏ `packages/engine` hiện ở `62773ba` (D17), và `interpreter.py:324-325` inject **cả** `tenant_id` **lẫn** `section_roles` từ `session_context.roles` vào `node.params`. Cái còn thiếu **không phải upstream** mà là bài test tích hợp ở tầng interpreter — lane DE — retire khi test đó lên xanh (§4.1). | ⏳ **dự đoán đúng — vẫn là gap, nhưng gap nằm trong lane DE, không phải chờ #111** |
| 3 | *"`obs.costs` ngoài fence-lane DE — DE điền ở D19 (cost-lineage)."* | **Sửa sau review kb#25 F2:** D19 (kb#22, merge 13/08) **KHÔNG build `obs.costs`** — cost-lineage đọc **on-read** từ `obs.trace_events` (một-nơi-tính, §4.1 mini-RFC); dựng bảng tổng hợp riêng sẽ là nơi tính thứ hai. Lỗ per-tenant thật vẫn nằm ở `obs.trace_events` (cột `cost`+`tenant_id`, chưa RLS) = **hạng mục B** trong mini-RFC (kb#24), không phải `obs.costs`. mini-RFC amendment D18 (kb#24, **APPROVED** 13/08) chốt `obs.costs`→**CẦN RLS *nếu/khi được build*** — chưa build hôm nay. | ⏳ **dự đoán đúng hướng — RLS vẫn treo, nhưng ở `obs.trace_events`, không phải `obs.costs`** |
| 4 | *"`obs.golden_sets` nghi bảng-chết trùng `eval.golden_sets` → đề xuất DROP (mini-RFC)."* | mini-RFC amendment D18 (kb#24, **APPROVED** 13/08) **giữ đề xuất DROP** `obs.golden_sets` (0 runtime reader); nguồn sự thật = `eval.golden_sets`. **Chưa DROP thật** (chờ xác nhận AIE-1, gate thay mentor). **Sửa sau review kb#25 F2:** `eval.*` không còn "chờ phê" — AIE-2 đã **chốt trực tiếp ở review kb#24**: `eval.golden_sets`→**KHÔNG CẦN** (đề dùng chung, ref-keyed) · `eval.scorecards`→**CẦN RLS** (`results` lưu answer-text per-tenant, `evalhub:harness.py:530`+`:540`). | 🔵 **đúng nghi vấn — DROP còn treo (AIE-1); nhánh `eval.*` đã chốt, không còn mở** |

**Chỗ lệch dự đoán (trung thực):** không có mục nào D11 hứa mà D20 làm thiếu; ngược lại D20 **làm dày hơn**
dự đoán ở điểm 2 (đã chặn roles ở kb-lane, không chỉ "nhận-rồi-bỏ" như D11 mô tả). **Sửa sau review kb#25:**
điểm treo còn lại **không đều là cross-lane/upstream** như bản gốc khai — điểm 2 (T6 integration-close) là
nợ **trong lane kb** (bài test tích hợp DE tự viết, §4.1); chỉ điểm 3 (cost số thật, chờ #121 AIE-1) và
phần DROP của điểm 4 (chờ AIE-1 xác nhận) còn thật sự cross-lane.

---

## 4. Hai lỗ upstream đã biết — honest-TODO (không giấu, không fake-green)

### 4.1 T6 integration-close — việc còn lại nằm trong lane DE (không phải chờ #111)

> **Sửa sau review AIE-2 (kb#25, F1 — blocker):** mục này viết sai lúc đầu — khai #111 "chưa land" và gán
> việc còn thiếu sang lane AIE-1. Thực tế **#111 đã land 11/08** (kit#113, `a4e59ed`), một ngày TRƯỚC
> dry-run 12/08; con trỏ `packages/engine` hiện ở `62773ba` (D17) và `interpreter.py:324-325` đã inject
> **cả** `tenant_id` **lẫn** `section_roles`. Việc còn thiếu **không phải upstream** mà là bài test tích
> hợp — **lane DE**.

- **Trạng thái:** `test_t6_label_spoof` giữ **XFAIL** — đúng thiết kế, không phải do thiếu upstream: bài
  này gọi thẳng `KbSearchService` với `section_roles` khai giả, cố tình **bỏ qua** interpreter (kb nhận gì
  thì TRUST đó, theo chữ ký 4-tham-số frozen `kb-search.v0.md §5.2`). Đóng thật cần một bài test MỚI đi qua
  `interpreter.run()` thật (kiểu `test_spine_live`), khai `section_roles=["finance"]` ở recipe nhưng session
  `roles=["public"]`, rồi assert `kb.search` chỉ nhận `["public"]` — chứng minh interpreter **đè** giá trị
  client khai, không phải "nhận-rồi-bỏ" như D11 §6 lo.
- **DE đã cấp sẵn:** no-bypass teeth (5/5) + acceptance mô phỏng override — giờ dùng làm **acceptance
  layer** cho bài test tích hợp mới, không còn là "spec chờ #111" nữa.
- **Việc còn lại (DE, D20 §③):** viết bài test tích hợp trên, gỡ `xfail` ở `test_t6_label_spoof` nếu bài
  mới thay được vai trò của nó, sửa `test_leak_meta.py` cùng commit (anti-tamper string). Không WRITE
  engine — chỉ thêm test trong lane kb.

### 4.2 Cost-lineage cùng-1-số ⇐ D19 (#120) — landed 13/08, seam wire còn mở (#121)

> **Cập nhật (không phải khai sai — D19 hợp lệ "chưa land" lúc dry-run 12/08, đã merge sau đó):** kb#22
> merge 13/08. Cập nhật §2/§3/§5 theo trạng thái mới.

- **Đã có (kb#22):** `src/studio_kb/cost.py` — bảng đơn giá + `cost_of(tokens)` (dùng để KIỂM, không tính
  cost thật), `aggregate_run_cost` (cộng `event.cost` đã lưu, fail-closed khi trộn `run_id`/`tenant_id`),
  `PgCostReader`, cost-table CLI (`scripts/cost_table.py`). Đọc **on-read** từ `obs.trace_events`, không
  materialize `obs.costs` (§4.1 mini-RFC: một-nơi-tính).
- **Vẫn 0:** `interpreter.py:438` (con trỏ engine hiện tại) còn `cost=_NO_COST` (0.0) — `cost_of` chưa
  được wire tại điểm emit. Invariant §3.2 (`cost` UI-test == trace == cost-table) **vẫn chưa chứng minh
  được** bằng số thật — "khớp" hiện vẫn rỗng nghĩa (0.0 khắp nơi), chỉ khác là giờ có sẵn cỗ máy cộng dồn
  + lưới kiểm (`price_mismatches`) chờ số thật chảy vào.
- **Seam còn mở:** `cost_of` phải land ở `contracts` để interpreter import (Q-A, DE không sửa `contracts`
  — GITFLOWS §5, cần mentor/CODEOWNERS PR) rồi **AIE-1 (#121, còn mở)** wire lúc emit. Cho tới đó,
  cost-table CLI/trace-viewer đọc đúng nhưng ra toàn 0 — honest-TODO, không tô hồng.
- **Không WRITE apps/engine/contracts trong lane DE.**

---

## 5. Bàn giao / mốc retire

- **#111 đã land** (11/08) → việc còn lại là bài test tích hợp ở tầng interpreter (lane DE, §4.1),
  **không** phải chờ engine — retire `xfail` khi bài test đó lên xanh + `test_leak_meta.py` cùng commit.
- **D19 (kb#22) đã land** (13/08) → cỗ máy cộng dồn cost sẵn sàng; còn chờ **#121 (AIE-1, mở)** wire
  `cost_of` tại emit + `cost_of` land ở `contracts` (Q-A) trước khi có số thật để đối chiếu UI-test.
- **mini-RFC schema-drift** (`docs/mini-rfc-tenant-schema-unify.md`, amendment D18 = **kb#24, APPROVED**
  13/08) → `eval.golden_sets` KHÔNG CẦN / `eval.scorecards` CẦN RLS đã chốt (AIE-2); `obs.costs` CẦN-RLS
  *nếu/khi build* (lane DE, chưa build — D19 đọc on-read từ `obs.trace_events`); DROP `obs.golden_sets`
  còn chờ xác nhận AIE-1 (gate thay mentor). B (RLS `wb.recipes`/`wb.recipe_versions`) đã đủ 4/4 chữ ký.
- **CI 5 bước** (gate-ready, code src không đổi — chỉ thêm docs): `pytest · ruff check · ruff format --check ·
  mypy · lint-imports`.
