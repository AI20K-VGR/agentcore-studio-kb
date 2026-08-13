---
id: studio.de.cost-lineage.d19
type: design-note + honest-TODO
status: wip
author: DE — Nguyễn Đông Anh
date: 2026-08-13
issue: kit#120 (Day 19)
contract_ref: trace-event.v0.md §4.1 · §7/F15 · §8 Q-A/Q-D
---

# Cost-lineage (D19, DE) — cộng dồn per-run + failure-mode

## 1. Kiến trúc (đã chốt trong DESCOPE.md + trace-event.v0.md)

```
executor(AIE-1) → tokens ──emit(interpreter)──▶ obs.trace_events (event thô, cost/1 event)
                                                        │  ← nguồn số DUY NHẤT
                                        DE: cộng dồn (studio_kb/cost.py)
                                                        ▼
                                          RunCost per-run ──▶ 3 mặt ĐỌC LẠI
                                          (UI-test AIE-2 · trace viewer · cost table CLI)
```

- **§4.1 (FROZEN):** `cost` tính **một lần tại emit**; mọi mặt **đọc lại**. `aggregate_run_cost` **CỘNG
  `event.cost` đã lưu**, KHÔNG tính lại từ tokens — recompute ở mặt đọc = vi phạm *kể cả ra cùng số*.
- **§7/F15:** `write()` INSERT trần; cộng dồn là downstream của DE — làm ở kb, không đụng đường ghi.
- **Đọc on-read từ `obs.trace_events`**, KHÔNG materialize `obs.costs` hôm nay: `obs.costs` ở
  `apps/studio` (ngoài fence-lane DE, Q-D hoãn-có-ghi) + schema-change cần ký (mini-rfc-tenant). Né
  blocker: bảng CLI suy trực tiếp từ event thô; materialize vào `obs.costs` để sau, khi có ceremony.

## 2. Đã giao hôm nay (kb)

| Deliverable | File |
|---|---|
| Bảng đơn giá + `cost_of(tokens)` (nguồn giá, để KIỂM) | `src/studio_kb/cost.py` |
| `aggregate_run_cost` (cộng `event.cost`, tenant-aware) + `RunCost` | `src/studio_kb/cost.py` |
| `price_mismatches` (lưới §4.1: `event.cost == cost_of(tokens)`) | `src/studio_kb/cost.py` |
| `PgCostReader` (tái dùng `PgTraceReader.read_run`) | `src/studio_kb/cost.py` |
| Cost table CLI (dashboard→CLI, DESCOPE NẤC 4) | `scripts/cost_table.py` |
| Test pure + DB + quét-AST "không mặt nào tự tính" (F-7) + self-mutation | `tests/test_cost.py` |

## 3. Điểm ghép (chưa đóng — KHÔNG tự vượt lane)

- **`cost_of` → phải land ở `contracts`** để interpreter (engine) áp tại emit (§4.1 "một nơi tính").
  DE **không sửa `contracts`** (GITFLOWS §5) → đây là **Q-A**, cần mentor/CODEOWNERS PR. Bản kb hiện là
  **đề xuất-tham chiếu + lưới kiểm**; tới khi land + AIE-1 nối, `event.cost=0` → cost table trả **0**
  (honest-TODO, không tô hồng).
- **AIE-1 (#121):** emit `tokens` thật + wire `cost_of` thay `_NO_COST` (`interpreter.py:300`); xác nhận
  **idempotent replay** (chống double-count — xem F-3 dưới).
- **AIE-2 (#123) / SWE (#122):** ĐỌC `RunCost`/`event.cost`, **không tự tính**.

## 4. Failure-mode nhìn đầu (honest-TODO, DoD)

| # | Failure-mode | Hiện trạng / vá |
|---|---|---|
| **F-1** | `cost=0` toàn bộ (emit chưa nối `cost_of`) → cost table ra 0 | **biết & ghi**; số thật khi Q-A land + AIE-1 nối. `price_mismatches` sẽ đỏ nếu tokens thật mà cost quên nối |
| **F-2** | Đơn giá theo model — `TraceEvent` chưa mang `model`, đang một mức phẳng | honest-TODO: thêm `model` vào carrier (mini-RFC contract) rồi bảng đơn giá theo model |
| **F-3** | **Replay double-count** — chạy lại một run tạo event `event_id` mới cùng `run_id` → cộng dồn gấp đôi | ghép AIE-1 idempotent (#121); cân nhắc dedup theo `(run_id, node_id)` hoặc run_id mới mỗi replay |
| **F-4** | Trộn tenant khi cộng dồn (obs.trace_events **không RLS**) → hở INV-1 | **đã vá**: `aggregate_run_cost` raise khi trộn `tenant_id`; mọi query mang `tenant_id` (hàng rào duy nhất) |
| **F-5** | Float drift khi cộng nhiều event | làm tròn 6 chữ số ở `cost_of` + tổng; nếu tiền-chính-xác cần thì đổi `Decimal` (honest-TODO) |
| **F-6** | Event thiếu ở giữa run → tổng thiếu mà timeline trông liền | dùng `trace_reader.check_walk` (0-gap) cạnh cost table trước khi tin số |
| **F-7** | Mặt đọc (UI-test/playground) tự nhân `tokens×đơn giá` cho tiện → phá §4.1 | contract cấm; lưới ở `test_khong_mat_doc_nao_ngoai_cost_py_goi_cost_of` (quét AST đệ quy **lane kb**, canh cả hằng đơn giá + alias) + `price_mismatches`. **Cross-repo (sửa lượt 3):** 4 quadrant cùng 1 layer import-linter (`studio_kb\|engine\|workbench\|evalhub`) ⇒ AIE-2/SWE **không import được** `studio_kb.cost` (`make lint` đỏ) — nên "gọi reader của DE" bất khả thi. Thực tế: mỗi mặt đọc tự **cộng `cost` đã lưu** (phép đọc trên nhiều dòng, KHÔNG suy giá từ `tokens` → vẫn đúng §4.1). Nửa cross-repo này **không có lưới ở lane kb**; đóng khi `cost_of` land ở `contracts` (Q-A §3), luật giá đi cùng nó |

## 5. Bất biến sống-còn
Cost-lineage nằm nhóm **KHÔNG được cắt** (DESCOPE §0): dù tụt nấc (dashboard→CLI), 3 mặt vẫn đọc **một**
số từ **một** nguồn. Tự tính lại mỗi mặt = phá bất biến, không phải descope.
