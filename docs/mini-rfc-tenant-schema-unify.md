---
id: studio.mini-rfc.tenant-schema-unify
type: mini-rfc
status: DRAFT — chờ 4/4 chữ ký
author: DE — Nguyễn Đông Anh
date: 2026-08-03
neo: D-13 · umbrella §3 (INV-1/INV-5) · GITFLOWS §5
addresses: "Still open #5 — schema drift (Anh, needs a mini-RFC)"
---

# Mini-RFC — Chuẩn tenant + RLS cho bảng tenant-scoped

## Vấn đề (kiểm từng bảng, 03/08)
11 bảng, RLS mới bật **1** (`kb.chunks`). Rà theo threat-model — **không** RLS đồng loạt:
- **3 bảng ĐÁNG bật RLS** (có đường user đọc + payload nhạy cảm): `wb.recipes`, `wb.recipe_versions`
  (recipe = IP tenant), `obs.trace_events` (trace/cost/citations).
- **2 bảng KHÔNG bật read-RLS** (hàng đợi infra drain cross-tenant, RLS sẽ phá): `core.jobs`, `core.outbox`.
- **3 bảng HOÃN** (chưa có cột tenant — quyết cột trước): `obs.costs`, `eval.golden_sets`, `eval.scorecards`.
- **1 bảng nghi CHẾT trùng lặp → đề xuất DROP:** `obs.golden_sets` (0 chỗ dùng; golden-set thật là `eval.golden_sets`).
- **1 registry** `core.tenants` — n/a (key = `id`). **1 đã có** `kb.chunks`.

→ **3 + 2 + 3 + 1 + 1 + 1 = 11.**

## Đề xuất
- **A — cột workbench** `tenant TEXT`→`tenant_id UUID` (`schema.py:31,43` + `UNIQUE`, `publish.py:47`).
  **✅ SWE ĐÃ LÀM — PR workbench #13** (MERGEABLE, chờ review). Workbench-internal, không cần ký RFC.
  Không cần ALTER: bảng **write-free** (đã kiểm — `publish()`/`rollback()` còn `raise NotImplementedError`,
  0 INSERT ngoài DDL), nên `CREATE TABLE IF NOT EXISTS` DDL mới trên DB tươi là đủ.
- **B — bật RLS cho 3 bảng** theo mẫu `kb_chunks_tenant_isolation`
  (`ENABLE`+`FORCE` + `USING (tenant_id = current_setting('app.tenant_id')::uuid)`):
  - `wb.recipes`, `wb.recipe_versions` — **chờ PR #13 merge trước** (policy cần cột `tenant_id UUID`).
  - `obs.trace_events` — reader `PgTraceReader.read_run` đã lọc `tenant_id` (an toàn ngay);
    **cost aggregator D19 (#120, việc DE) phải tenant-aware** hoặc đi đường admin có chủ đích.
    > ⏳ **Điều kiện ký AIE-1 (03/08):** KHÔNG ký B cho `obs.trace_events` tới khi đường **ghi** bind
    > `app.tenant_id` trên chính connection của nó. Nay `PgTraceWriter.write()` mở connection riêng từ
    > pool (`trace_writer.py:26`) rồi INSERT thẳng, **không** `set_config('app.tenant_id')` (đã kiểm phía
    > writer); middleware chỉ `SET LOCAL` — phạm vi giao dịch khác. Với `FORCE` + `WITH CHECK` mặc định
    > theo `USING`, INSERT của writer bị từ chối ⇒ mọi `interpreter.run()` gãy ở emit. **Phần A
    > (`tenant_id UUID`) AIE-1 ký được ngay.**
- **B-excl — `core.jobs`/`core.outbox`: KHÔNG read-RLS** (xem "Loại trừ"). Cùng lắm enforce phía ghi.
- **B2 — 3 bảng chưa có cột tenant:** quyết *"có cần tenant-scope không?"* → nếu có, thêm `tenant_id UUID`
  rồi mới RLS. `obs.costs` gắn D19 (DE); `eval.*` gắn D16 (#108, AIE-2). Không RLS mù khi chưa có cột.
  > ⚠️ **Đây là NHÓM KHÁC với phần A.** Phần A (PR #13) chỉ sửa `wb.recipes`/`wb.recipe_versions` —
  > 2 bảng này đã có tenant từ trước, không thuộc nhóm hoãn. Ba bảng B2 nằm ở **lane khác**
  > (`apps/studio`, `evalhub`); **PR #13 không chạm dòng nào** của chúng. Vì thế đánh-giá-lại sau #13
  > **vẫn hoãn** — không phải né, mà vì #13 (workbench-only) không liên quan tới chúng. Lý do hoãn
  > **không** phải "chờ ai sửa tenant" mà là **bảng chưa được xây** → chưa quyết được tenant-scope.
  > Mốc gỡ hoãn = ngày chủ lane xây thật (`obs.costs`→D19 DE · `eval.*`→D16 AIE-2), cộng invariant C
  > ép RLS khi có dữ liệu. Không mở vô hạn.
- **D — `obs.golden_sets`:** **nghi bảng chết trùng lặp** — cả `obs.golden_sets` lẫn `eval.golden_sets`
  đều **0 runtime reader** (mọi ref tới `eval.golden_sets` là docstring/DDL; `EvalHarness.run()` vẫn
  `NotImplementedError`). Chọn `eval.golden_sets` làm nguồn sự thật vì **quyền ghi**, không phải "đang
  được đọc": `obs.golden_sets` nằm `apps/studio/` — ngoài fence-lane DE nên bên giữ nhãn không điền
  được; `eval.golden_sets` ở evalhub, bút AIE-2 — có người ghi được. Chốt cùng AIE-2: DEC-Q5
  (`evalhub:docs/decisions/scorecard.md`). **Xác nhận với mentor rồi DROP** — "chưa dùng" chưa chắc
  "không định dùng".
- **C — invariant từ nay:** bảng tenant-scoped **có đường user đọc** ⇒ `tenant_id UUID` + RLS theo mẫu
  + 1 leak-test có răng (T1/T6: inclusion dương trước, rồi loại trừ). Chống tái drift khi S2 thêm bảng.

## Loại trừ có chủ đích — `core.jobs` / `core.outbox` (KHÔNG read-RLS)
Hàng đợi hạ tầng **drain cross-tenant**, không có đường user đọc:
- `core/queue.py:68` — claim job `SELECT ... FOR UPDATE SKIP LOCKED WHERE status='pending'`, **không** predicate tenant.
- `core/schema.py` docstring — dùng **`FORCE ROW LEVEL SECURITY`** "bite cả owner".
→ Read-RLS theo `app.tenant_id` làm worker/dispatcher **chỉ thấy 1 tenant → tắc hàng đợi**, security ≈ 0. (DL-11.8.)

## Ai thực thi + thứ tự
| Bảng | Việc | Lane | Trạng thái |
|---|---|---|---|
| `wb.recipes`,`wb.recipe_versions` | A đổi cột | SWE | ✅ **PR #13, chờ merge** |
| `wb.recipes`,`wb.recipe_versions` | B RLS | SWE | ⏳ chờ #13 merge → cần ký |
| `obs.trace_events` | B RLS (+ D19 aggregator tenant-aware) | mentor + DE | cần ký |
| `core.jobs`,`core.outbox` | **loại trừ** read-RLS | mentor | — (DL-11.8) |
| `obs.costs` | B2 thêm cột→RLS (D19) | DE điền | cần ký |
| `eval.golden_sets`,`eval.scorecards` | B2 quyết tenant-scope (D16) | AIE-2 | cần ký |
| `obs.golden_sets` | D DROP (xác nhận mentor) | mentor | cần ký |
| `kb.chunks` | mẫu tham chiếu | DE | ✅ đã có |

## Vì sao cần ký (B · B2 · C · D — không phải A)
Bật RLS / DROP bảng **đổi runtime lane khác** + là quyết định INV-1. → Ký chuẩn **1 lần**, rồi mỗi chủ lane tự thực thi.

## Chữ ký (B · B2 · C · D)
| Vai | Người | Ký |
|---|---|---|
| DE (bút + mẫu kb) | Nguyễn Đông Anh | ✅	|
| SWE | Thiệu Quang Minh | ⬜ |
| AIE-1 | Trần Bá Đạt | ⬜ |
| AIE-2 | Lưu Tiến Duy | ⬜ |
| mentor (obs·core) | | ⬜ |

*Chốt xong ghi decision-log. Non-goal: INV-1 roles (đó là #110/#112, D17).*

---
<details><summary>Phụ lục — inventory bằng chứng (kiểm 03/08)</summary>

| Bảng | Lane | Cột tenant | RLS | Quyết |
|---|---|---|---|---|
| `kb.chunks` | kb | `tenant_id UUID` | ✅ | mẫu |
| `wb.recipes` | workbench | `tenant TEXT`→UUID (PR#13) | ❌ | A(#13)→B RLS |
| `wb.recipe_versions` | workbench | `tenant TEXT`→UUID (PR#13) | ❌ | A(#13)→B RLS |
| `obs.trace_events` | apps/studio | `tenant_id UUID` | ❌ | B RLS |
| `core.jobs` | apps/studio | `tenant_id UUID` | ❌ | **loại** (queue drain) |
| `core.outbox` | apps/studio | `tenant_id UUID` | ❌ | **loại** (outbox drain) |
| `obs.costs` | apps/studio | — (shell) | ❌ | B2 (D19) |
| `eval.golden_sets` | evalhub | — | ❌ | B2 (D16) |
| `eval.scorecards` | evalhub | — (chỉ `agent_id`) | ❌ | B2 (D16) |
| `obs.golden_sets` | apps/studio | — (shell, 0 ref) | ❌ | **D — DROP?** |
| `core.tenants` | apps/studio | — (registry) | n/a | n/a |

RLS duy nhất: `kb_chunks_tenant_isolation`. Reader `obs.trace_events`: `read_run` lọc `WHERE run_id AND tenant_id`
(trace_reader.py:70). wb tables write-free (`publish()`/`rollback()` stub). `obs.golden_sets` **và**
`eval.golden_sets` đều 0 runtime reader; chọn `eval.golden_sets` làm nguồn sự thật theo **quyền ghi**
(evalhub/AIE-2 ghi được; `obs.golden_sets` ở `apps/studio` không ai điền) — DEC-Q5.
</details>
