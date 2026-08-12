---
id: studio.mini-rfc.tenant-schema-unify
type: mini-rfc
status: DRAFT — gate 4 thành viên; B đủ 4/4, B2·C·D còn hở SWE/AIE-1
author: DE — Nguyễn Đông Anh
date: 2026-08-03
neo: D-13 · umbrella §3 (INV-1/INV-5) · GITFLOWS §5
addresses: "Still open #5 — schema drift (Anh, needs a mini-RFC)"
---

# Mini-RFC — Chuẩn tenant + RLS cho bảng tenant-scoped

## Vấn đề (kiểm từng bảng — 03/08; phân loại lại nhị phân 12/08 · D18)
11 bảng, RLS mới bật **1** (`kb.chunks`). Rà theo threat-model, mỗi bảng về **đúng một** trong hai
nhóm — **bỏ nhóm "HOÃN" cũ** (xem [Amendment D18](#amendment-2026-08-12--d18) bên dưới):

- **5 CẦN RLS** (tenant-scoped + có đường user đọc + payload nhạy cảm):
  `kb.chunks` (✅ đã có, mẫu) · `wb.recipes` · `wb.recipe_versions` (recipe = IP tenant) ·
  `obs.trace_events` (trace/cost/citations) · `obs.costs` (chi phí per-tenant, "đồng hồ điện" hiện trên UI).
- **5 KHÔNG CẦN RLS**:
  `core.jobs` · `core.outbox` (hàng đợi infra drain cross-tenant — RLS sẽ phá) ·
  `core.tenants` (registry định danh — RLS là vòng tròn logic) ·
  `eval.golden_sets` (bộ đề **CHUNG**, ref-keyed) ·
  `eval.scorecards` (kết quả chấm **nội bộ**, observe-only — *đề xuất, chờ AIE-2 phê*).
- **1 XOÁ:** `obs.golden_sets` (0 reader; trùng `eval.golden_sets`).

→ **5 + 5 + 1 = 11.**

> ### Amendment 2026-08-12 · D18
> **Đổi:** gỡ hẳn nhóm "3 bảng HOÃN" (`obs.costs`, `eval.golden_sets`, `eval.scorecards`) — mỗi bảng
> về cần/không-cần RLS. **Lý do:** câu *"có cần RLS không"* phụ thuộc **bản chất data** (data khách hàng
> nhạy cảm + có đường đọc?), **không** phụ thuộc bảng đã xây hay chưa — nên quyết được ngay, không cần
> hoãn tới ngày build. `obs.costs`→**CẦN** (chi phí per-tenant lên UI); `eval.*`→**KHÔNG CẦN** (đề chung
> + kết quả chấm nội bộ, observe-only, khớp DEC-07). ⚠️ Amendment này **sau** chữ ký AIE-2 (ký trên bản
> B2-hoãn cũ) — phần `eval.*` **giữ mức đề xuất, chờ AIE-2 phê** vì là lane của họ; phần `obs.costs` là
> lane DE.

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
- **B2 — 3 bảng "hoãn" cũ, nay chốt nhị phân (amendment D18):** trả lời *"có cần RLS không?"* ngay từ
  bản chất data, không chờ bảng xây xong:
  - `obs.costs` → **CẦN RLS.** Chi phí per-tenant; đích D19 là "đồng hồ điện" hiện trên UI. DE build ở
    D19 thì thêm `tenant_id UUID` + RLS theo mẫu **ngay từ đầu**, không để cột trần rồi vá sau. (Lane DE.)
  - `eval.golden_sets` → **KHÔNG CẦN.** `golden_set_ref` là bộ đề **dùng chung** (ref-keyed), không phải
    data khách hàng per-tenant. Fence tenant thật nằm ở `kb.chunks` (retrieval) + trace `tenant_id`.
  - `eval.scorecards` → **KHÔNG CẦN** (đề xuất). Kết quả chấm nội bộ; `gate` do pipeline publish/rollback
    đọc (INV-6, hệ thống — không phải tenant đọc chéo); observe-only theo DEC-07. **Lật sang CẦN** nếu về
    sau có màn hình cho tenant xem scorecard agent mình **và** `results` lưu answer-text của tenant.
    → **Chủ lane AIE-2 chốt**, không quyết hộ.
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
| `core.jobs`,`core.outbox` | **KHÔNG CẦN** read-RLS | mentor | — (DL-11.8) |
| `core.tenants` | **KHÔNG CẦN** (registry định danh) | — | — n/a |
| `obs.costs` | **CẦN RLS** — thêm `tenant_id`+RLS khi build (D19) | DE | cần ký |
| `eval.golden_sets`,`eval.scorecards` | **KHÔNG CẦN** (eval observe-only, D18) | AIE-2 | đề xuất → AIE-2 phê |
| `obs.golden_sets` | D DROP (xác nhận mentor) | mentor | cần ký |
| `kb.chunks` | mẫu tham chiếu | DE | ✅ đã có |

## Vì sao cần ký (B · B2 · C · D — không phải A)
Bật RLS / DROP bảng **đổi runtime lane khác** + là quyết định INV-1. → Ký chuẩn **1 lần**, rồi mỗi chủ lane tự thực thi.

## Chữ ký (B · B2 · C · D) — gate 4 thành viên (DE · SWE · AIE-1 · AIE-2)
| Vai | Người | Ký |
|---|---|---|
| DE (bút + mẫu kb) | Nguyễn Đông Anh | ✅ — B·B2·C·D |
| SWE | Thiệu Quang Minh | ✅ 2026-08-12 — **phần B** (RLS `wb.recipes`/`wb.recipe_versions`), PR kb#23 · RLS ở workbench#22. B2/C/D chưa nhận. |
| AIE-1 | Trần Bá Đạt | ✅ 2026-08-12 — **phần B** (`obs.trace_events`). Điều kiện A1-8 (writer bind `app.tenant_id`) **tự đóng** bằng PR `apps/studio#4` do chính AIE-1 mở; DE review+verify (45 passed) → rút objection. *(PR#4 tự giới hạn: chỉ đóng đk kỹ thuật, bật RLS production là mentor+DE.)* B2/C/D: không phản đối (B2=eval/wb ngoài lane AIE-1). |
| AIE-2 | Lưu Tiến Duy | ✅ 2026-08-03 — B·B2·C·D (comment PR kb#10, ghi `evalhub:decisions/scorecard.md`) |

**Trạng thái chữ ký:** **B** — đủ 4/4 thành viên (DE·SWE·AIE-1·AIE-2). **B2·C·D** — mới DE + AIE-2; còn chờ SWE/AIE-1 nhận (B2 phần eval là AIE-2 đã ký; wb/costs/invariant/drop còn hở).

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
| `obs.costs` | apps/studio | — (shell) | ❌ | **CẦN** — thêm `tenant_id`+RLS @D19 |
| `eval.golden_sets` | evalhub | — | ❌ | **KHÔNG CẦN** (đề chung) |
| `eval.scorecards` | evalhub | — (chỉ `agent_id`) | ❌ | **KHÔNG CẦN*** (observe-only · AIE-2 phê) |
| `obs.golden_sets` | apps/studio | — (shell, 0 ref) | ❌ | **D — DROP?** |
| `core.tenants` | apps/studio | — (registry) | n/a | **KHÔNG CẦN** (registry định danh) |

RLS duy nhất: `kb_chunks_tenant_isolation`. Reader `obs.trace_events`: `read_run` lọc `WHERE run_id AND tenant_id`
(trace_reader.py:70). wb tables write-free (`publish()`/`rollback()` stub). `obs.golden_sets` **và**
`eval.golden_sets` đều 0 runtime reader; chọn `eval.golden_sets` làm nguồn sự thật theo **quyền ghi**
(evalhub/AIE-2 ghi được; `obs.golden_sets` ở `apps/studio` không ai điền) — DEC-Q5.
</details>
