---
id: studio.decision-log.trace-event
type: decision-log
owner: DE — Nguyễn Đông Anh
scope: contract `trace-event.v0` (1 trong 2 contract DE cầm)
sibling: decision-log-kb-search.md
started: 2026-08-03
canonical_location: PENDING (Q-2)
---

# Decision-log — trace-event (DE)

> **⚠️ Vị trí canon chưa chốt (Q-2).** DoD #80 đòi *"decision-log ghi"* nhưng repo chưa có file
> decision-log dùng chung. File này là **bản ghi kb-local của DE** cho các quyết chốt ở D11 **thuộc
> contract `trace-event.v0`**; nếu mentor/leader chỉ định một decision-log chung (kit? contracts?),
> **di về đó** và để lại con trỏ. Không tự quyết vị trí canon thay leader.
>
> Nguồn luật freeze: umbrella §3 (`:92-93`) · **D-12** · **INV-5** · GITFLOWS §5. Đổi contract sau
> freeze = **mini-RFC + 4/4 chữ ký + decision-log**.
>
> **Tách file (D11):** decision-log gốc chia đôi theo 2 contract DE cầm — nửa `kb.search` ở
> [`decision-log-kb-search.md`](decision-log-kb-search.md). Hai quyết **schema-drift** (DL-11.8
> `core.jobs`/`core.outbox` không read-RLS · DL-11.9 `wb` `tenant_id`/`obs.golden_sets` DROP) **không
> thuộc riêng contract nào** → canon ở [`../mini-rfc-tenant-schema-unify.md`](../mini-rfc-tenant-schema-unify.md)
> (DL-11.8: §"Loại trừ" `:64`,`:72`; DL-11.9: phần A PR#13 `:25-26` + phần D DROP `:50-53`).

## D11 · 2026-08-03 · Contract-freeze workshop (#84)

| # | Quyết | Lý do | Trạng thái / người ký |
|---|---|---|---|
| **DL-11.1** | **`ts` không assert tăng-nghiêm-ngặt.** Ties hợp lệ; sắp ổn định `(ts, event_id)`; `ts` là cột `TEXT` → parse rồi mới sắp, raise khi hỏng. | Hai node cùng mili-giây trùng `ts` là bình thường; so-chuỗi trên `TEXT` sai im lặng nếu format lệch. Reader-test `test_trace_reader.py` đã khớp. Khoá nguyên văn trace-event §4.2a. | ✅ chốt (DE, đã có test) — freeze nguyên văn |
| **DL-11.2** | **`cost` một-nguồn: sink tính từ `tokens` + bảng đơn giá; executor chỉ cấp `tokens`.** Cấm hai chỗ tính (kể cả ra cùng số). | Đơn giá đổi một chỗ → ba mặt (UI test · trace viewer · cost dashboard) lệch nhau mà không ai biết mặt nào đúng. trace-event §4.1. | ✅ **AIE-1 xác nhận (Q-3, engine#15)** — executor chỉ cấp `tokens` (`executors.py:262`), interpreter `cost=_NO_COST` (`interpreter.py:300`); sink là nơi tính duy nhất, code engine đã đúng sẵn |
| **DL-11.3** | **`node_type` = enum đóng 6, nguồn duy nhất `studio_contracts.nodes.NodeType`;** cấm khai lại phía kb. Chuỗi walk hiện là **4**, không phải 6 (nguồn: `recipe.dag.edges`; hằng số `interpreter._WALK_ORDER` đã bỏ ở D6/#27, walk đi động theo edge). | 6 giá trị không được trôi lệch giữa các package; reader so theo `node_type` nên phải cùng một enum với `recipe.dag` của SWE. trace-event §5. | ⏳ **chờ SWE xác nhận tập node recipe (Q-4)** |
| **DL-11.4** | **`inputs_hash` + `outputs` bắt buộc AIE-1 truyền từ tuần 1** (`inputs_hash` không có DB default; `outputs` dùng `{}` khi chưa có). `citations` mới thật sự nullable. | Ràng buộc **bảng `obs.trace_events` đã tồn tại** + `TraceEvent` pydantic — là thông báo, không đàm phán. trace-event §7. | ✅ ràng buộc cứng — **đã điền thật D11** (`interpreter.py:297/298` mọi event; `citations` grounded từ D6 `executors.py:259`) |
| **DL-11.7** | **`obs.costs` hoãn-có-ghi (cross-lane):** bảng ở `apps/studio`, **ngoài fence-lane DE**; ai điền/bằng cách nào = coordinate leader. *(Cập nhật: `obs.golden_sets` **KHÔNG** còn gộp ở đây — chuyển sang DROP, xem DL-11.9 @ mini-rfc. `obs.costs` gỡ hoãn ở D19; nhóm hoãn ≠ phần A wb.\*, PR #13 không đụng.)* | Không phải WRITE-lane của DE (kb). Không chặn freeze schema. trace-event §8 Q-D. | ⏳ coordinate leader / D19 |

> **Schema-drift (DL-11.8 · DL-11.9)** không thuộc contract này — canon ở
> [`../mini-rfc-tenant-schema-unify.md`](../mini-rfc-tenant-schema-unify.md). Liên quan trace-event ở
> chỗ **`obs.trace_events` NẰM trong tập bật RLS** (DL-11.8): RLS đáng cho `wb.*` + `obs.trace_events`;
> hoãn `obs.costs` + `eval.*`; `core.jobs`/`core.outbox` **loại trừ** (queue drain cross-tenant).

## Câu CHẶN chưa đóng — trace-event (không đóng được trong lằn kb — cần người)

| # | Hỏi ai | Nội dung | Ảnh hưởng |
|---|---|---|---|
| **Q-1** | mentor / leader | Bản `FROZEN` nằm ở draft kb (lật cờ) hay PR bump `SCHEMA_VERSION` ở `contracts` (mentor CODEOWNERS)? | **CHẶN DoD ô 1** (contract commit + freeze). Nếu là contracts → DE cần đường cross-repo, không đóng solo |
| **Q-2** | mentor / leader | decision-log canon ở đâu (chưa có file chung)? + hình thức "4 chữ ký"? | **CHẶN DoD ô 3 & 4** — file này chỉ là bản kb-local tạm |
| **Q-3** | AIE-1 | cost-source (DL-11.2) + xác nhận carrier (DL-11.4) | chặn ký trace-event *(phần stub DL-11.6 → xem decision-log-kb-search)* |
| **Q-4** | SWE | tập `node_type` recipe.dag = đúng 6 enum (DL-11.3) | chặn ký trace-event |
| **Q-5** | AIE-2 | field eval đọc từ trace (Q-C) | chặn ký trace-event *(vế `expected_citation`↔`chunk_id` → xem decision-log-kb-search)* |

> **Chưa có chữ ký nào (0/4).** Bảng chữ ký sống trong contract (`trace-event.v0.md` §0.2). Không ký
> khống — ký sau khi đóng Q-3/Q-4/Q-5 và đọc delta §7.
