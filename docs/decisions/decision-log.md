---
id: studio.decision-log.kb
type: decision-log
owner: DE — Nguyễn Đông Anh
scope: agentcore-studio-kb (2 contract DE cầm: trace-event · kb.search)
started: 2026-08-03
canonical_location: PENDING (Q-2)
---

# Decision-log — kb (DE)

> **⚠️ Vị trí canon chưa chốt (Q-2).** DoD #80 đòi *"decision-log ghi"* nhưng repo chưa có file
> decision-log dùng chung. File này là **bản ghi kb-local của DE** cho các quyết chốt ở D11; nếu
> mentor/leader chỉ định một decision-log chung (kit? contracts?), **di về đó** và để lại con trỏ.
> Không tự quyết vị trí canon thay leader.
>
> Nguồn luật freeze: umbrella §3 (`:92-93`) · **D-12** · **INV-5** · GITFLOWS §5. Đổi contract sau
> freeze = **mini-RFC + 4/4 chữ ký + decision-log**.

## D11 · 2026-08-03 · Contract-freeze workshop (#84)

| # | Quyết | Lý do | Trạng thái / người ký |
|---|---|---|---|
| **DL-11.1** | **`ts` không assert tăng-nghiêm-ngặt.** Ties hợp lệ; sắp ổn định `(ts, event_id)`; `ts` là cột `TEXT` → parse rồi mới sắp, raise khi hỏng. | Hai node cùng mili-giây trùng `ts` là bình thường; so-chuỗi trên `TEXT` sai im lặng nếu format lệch. Reader-test `test_trace_reader.py` đã khớp. Khoá nguyên văn trace-event §4.2a. | ✅ chốt (DE, đã có test) — freeze nguyên văn |
| **DL-11.2** | **`cost` một-nguồn: sink tính từ `tokens` + bảng đơn giá; executor chỉ cấp `tokens`.** Cấm hai chỗ tính (kể cả ra cùng số). | Đơn giá đổi một chỗ → ba mặt (UI test · trace viewer · cost dashboard) lệch nhau mà không ai biết mặt nào đúng. trace-event §4.1. | ⏳ **chờ AIE-1 xác nhận (Q-3)** trước khi ký |
| **DL-11.3** | **`node_type` = enum đóng 6, nguồn duy nhất `studio_contracts.nodes.NodeType`;** cấm khai lại phía kb. Chuỗi walk hiện là **4** (`_WALK_ORDER`), không phải 6. | 6 giá trị không được trôi lệch giữa các package; reader so theo `node_type` nên phải cùng một enum với `recipe.dag` của SWE. trace-event §5. | ⏳ **chờ SWE xác nhận tập node recipe (Q-4)** |
| **DL-11.4** | **`inputs_hash` + `outputs` bắt buộc AIE-1 truyền từ tuần 1** (`inputs_hash` không có DB default; `outputs` dùng `{}` khi chưa có). `citations` mới thật sự nullable. | Ràng buộc **bảng `obs.trace_events` đã tồn tại** + `TraceEvent` pydantic — là thông báo, không đàm phán. trace-event §7. | ✅ ràng buộc cứng — thông báo AIE-1 khi ký |
| **DL-11.5** | **Q-G (slug→UUID thật) ĐÓNG theo D-13:** producer/middleware resolve header slug→UUID qua `core.tenants`; kb khoá theo UUID. | Đường resolve **ngoài lằn kb**; kb chỉ nhận UUID. Không chặn freeze kb.search. | ✅ đóng theo D-13 |
| **DL-11.6** | **Q-D stub (`kb.search`) hoãn-có-ghi:** mặc định AIE-1 tự dựng double; bản chung nếu cần đặt `src/studio_kb/stubs.py` class riêng, **không đụng** `KbSearchService`. | `day-03.md:38` + tiền lệ `FakeEmbedding`. Không chặn freeze. | ⏳ chốt với AIE-1 (Q-3) |
| **DL-11.7** | **`obs.costs` hoãn-có-ghi (cross-lane):** bảng ở `apps/studio`, **ngoài fence-lane DE**; ai điền/bằng cách nào = coordinate leader. *(Cập nhật: `obs.golden_sets` **KHÔNG** còn gộp ở đây — chuyển sang DROP, xem DL-11.9. `obs.costs` gỡ hoãn ở D19; nhóm hoãn ≠ phần A wb.\*, PR #13 không đụng.)* | Không phải WRITE-lane của DE (kb). Không chặn freeze schema. trace-event §8 Q-D. | ⏳ coordinate leader / D19 |
| **DL-11.8** | **`core.jobs` / `core.outbox`: KHÔNG read-RLS** (loại trừ có chủ đích trong mini-RFC schema-drift). Cùng lắm enforce phía ghi. | Hàng đợi infra **drain cross-tenant**: `core/queue.py:68` claim job `FOR UPDATE SKIP LOCKED` không predicate tenant; `core/schema.py` docstring dùng `FORCE ROW LEVEL SECURITY` bite cả owner → read-RLS theo `app.tenant_id` làm **worker/dispatcher tắc hàng đợi**, mà không có đường user đọc nên security ≈ 0. RLS đáng: `wb.*` + `obs.trace_events`; hoãn: `obs.costs` + `eval.*`; registry `core.tenants` n/a. | ✅ chốt (advisor xác nhận) — xem `docs/mini-rfc-tenant-schema-unify.md` |
| **DL-11.9** | **Phần A (cột `wb` `tenant`→`tenant_id UUID`) đã có SWE làm — PR workbench #13** (chờ merge). `wb.*` RLS (phần B) **chờ #13 merge**. **`obs.golden_sets` nghi bảng chết trùng lặp → đề xuất DROP, xác nhận mentor trước.** | Kiểm 03/08: wb tables write-free (`publish()`/`rollback()` stub, 0 INSERT) nên #13 không cần ALTER. `obs.golden_sets` 0 reference; golden-set thật = `eval.golden_sets` (`harness.py:187`) — "chưa dùng" ≠ "không định dùng" nên hỏi mentor. | 🟡 A: chờ #13 merge · DROP: chờ mentor |

## Câu CHẶN chưa đóng (không đóng được trong lằn kb — cần người)

| # | Hỏi ai | Nội dung | Ảnh hưởng |
|---|---|---|---|
| **Q-1** | mentor / leader | Bản `FROZEN` nằm ở draft kb (lật cờ) hay PR bump `SCHEMA_VERSION` ở `contracts` (mentor CODEOWNERS)? | **CHẶN DoD ô 1** (contract commit + freeze). Nếu là contracts → DE cần đường cross-repo, không đóng solo |
| **Q-2** | mentor / leader | decision-log canon ở đâu (chưa có file chung)? + hình thức "4 chữ ký"? | **CHẶN DoD ô 3 & 4** — file này chỉ là bản kb-local tạm |
| **Q-3** | AIE-1 | cost-source (DL-11.2) + xác nhận carrier (DL-11.4) + stub (DL-11.6) | chặn ký trace-event + kb.search |
| **Q-4** | SWE | tập `node_type` recipe.dag = đúng 6 enum (DL-11.3) | chặn ký trace-event |
| **Q-5** | AIE-2 | field eval đọc từ trace (Q-C) + `expected_citation` khớp `chunk_id` | chặn ký cả hai |

> **Chưa có chữ ký nào (0/4).** Bảng chữ ký sống trong từng contract (§0.2). Không ký khống —
> ký sau khi đóng Q-3/Q-4/Q-5 và đọc delta.
