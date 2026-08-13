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

- **6 CẦN RLS** (tenant-scoped + có đường user đọc + payload nhạy cảm):
  `kb.chunks` (✅ đã có, mẫu) · `wb.recipes` · `wb.recipe_versions` (recipe = IP tenant) ·
  `obs.trace_events` (trace/cost/citations) · `obs.costs` (chi phí per-tenant, "đồng hồ điện" hiện trên UI) ·
  `eval.scorecards` (`results` lưu answer-text per-tenant — chốt CẦN bởi lane AIE-2, review kb#24).
- **4 KHÔNG CẦN RLS**:
  `core.jobs` · `core.outbox` (hàng đợi infra drain cross-tenant — RLS sẽ phá) ·
  `core.tenants` (registry định danh — RLS là vòng tròn logic) ·
  `eval.golden_sets` (bộ đề **CHUNG**, ref-keyed).
- **1 XOÁ:** `obs.golden_sets` (0 reader; trùng `eval.golden_sets`).

→ **6 + 4 + 1 = 11.**

> ### Amendment 2026-08-12 · D18
> **Đổi:** gỡ hẳn nhóm "3 bảng HOÃN" (`obs.costs`, `eval.golden_sets`, `eval.scorecards`) — mỗi bảng
> về cần/không-cần RLS. **Lý do:** câu *"có cần RLS không"* phụ thuộc **bản chất data** (data khách hàng
> nhạy cảm + có đường đọc?), **không** phụ thuộc bảng đã xây hay chưa — nên quyết được ngay, không cần
> hoãn tới ngày build. `obs.costs`→**CẦN** (chi phí per-tenant lên UI); `eval.golden_sets`→**KHÔNG CẦN**
> (đề dùng chung, ref-keyed); `eval.scorecards`→**CẦN** (`results` lưu answer-text per-tenant — điều kiện
> lật đã thoả, xem B2). ⚠️ Amendment này **sau** chữ ký AIE-2 03/08 (ký trên bản B2-hoãn cũ, nghĩa khác:
> *"quyết sau, không RLS mù"* ≠ *"không cần"*) — nên chữ ký cũ **KHÔNG** tính là phê amendment D18. Lane
> AIE-2 đã chốt trực tiếp ở review kb#24: `eval.golden_sets` phê KHÔNG CẦN, `eval.scorecards` về CẦN.

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
  - `obs.costs` → **CẦN RLS** *nếu/khi được build.* Chi phí per-tenant là "đồng hồ điện" nhạy cảm. **Nhưng
    D19 (kb#22) KHÔNG build `obs.costs`:** cost-lineage đọc **on-read** từ `obs.trace_events` (§4.1 "một nơi
    tính" — dựng bảng tổng hợp = nơi thứ hai chứa cost), nên lỗ per-tenant thật **đang nằm ở
    `obs.trace_events`** (cột `cost`+`tenant_id`, chưa RLS) — đó là **hạng mục B**, không phải `obs.costs`.
    Nếu sau này có ai build `obs.costs` thì thêm `tenant_id UUID`+RLS ngay từ đầu. (Lane DE.)
  - `eval.golden_sets` → **KHÔNG CẦN.** `golden_set_ref` là bộ đề **dùng chung** (ref-keyed), không phải
    data khách hàng per-tenant. Fence tenant thật nằm ở `kb.chunks` (retrieval) + trace `tenant_id`.
  - `eval.scorecards` → **CẦN RLS** (chốt bởi chủ lane AIE-2, review kb#24). Điều kiện lật *"`results`
    lưu answer-text của tenant"* **đã thoả HÔM NAY**, không phải "về sau": `EvalHarness.run()`
    (`evalhub:harness.py:463`, đã hiện thực trên `origin/main` — hết `NotImplementedError`) chạy từng case
    `tenant_id=tenant_ids[case.tenant]` (`:530`) rồi đổ `CaseResult(expected, actual=scored.actual)` (`:540`) — answer-text dẫn xuất từ
    kho tenant — vào `eval.scorecards.results JSONB` (`evalhub:schema.py:31`). Tiêu chí RFC là **bản chất
    data**, không phải "ai đọc" (`gate`): bản chất `results` là nội dung per-tenant ⇒ CẦN. Chưa hở thật
    (0 writer, bảng mới có DDL) nhưng RFC này quyết theo bản-chất-data *"không phụ thuộc bảng đã xây hay
    chưa"* — nên áp nhất quán = CẦN. (Lane AIE-2.)
- **D — `obs.golden_sets`:** **nghi bảng chết trùng lặp** — cả `obs.golden_sets` lẫn `eval.golden_sets`
  đều **0 runtime reader**: mọi ref tới `eval.golden_sets` là docstring/DDL; `EvalHarness.run()` **nay đã
  hiện thực** (`evalhub:harness.py:463`, hết `NotImplementedError`) nhưng nạp golden từ **file path** chứ
  không từ bảng `eval.golden_sets` — nên "0 runtime reader" của bảng vẫn đúng. Chọn `eval.golden_sets` làm
  nguồn sự thật vì **quyền ghi**, không phải "đang được đọc": `obs.golden_sets` nằm `apps/studio/` — ngoài
  fence-lane DE nên bên giữ nhãn không điền được; `eval.golden_sets` ở evalhub, bút AIE-2 — có người ghi
  được. Chốt cùng AIE-2: DEC-Q5 (`evalhub:docs/decisions/scorecard.md`). **Xác nhận với AIE-1 (gate thay
  mentor) rồi DROP** — "chưa dùng" chưa chắc "không định dùng".
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
| `obs.trace_events` | B RLS (+ D19 aggregator tenant-aware ✅ kb#22) | AIE-1 + DE | cần ký |
| `core.jobs`,`core.outbox` | **KHÔNG CẦN** read-RLS | AIE-1 (gate thay mentor) | — (DL-11.8) |
| `core.tenants` | **KHÔNG CẦN** (registry định danh) | — | — n/a |
| `obs.costs` | **CẦN RLS** khi/nếu build (D19 kb#22 **KHÔNG** build — đọc on-read từ `trace_events`) | DE | — chưa build |
| `eval.golden_sets` | **KHÔNG CẦN** (đề chung, ref-keyed, D18) | AIE-2 | ✅ AIE-2 phê (kb#24) |
| `eval.scorecards` | **CẦN RLS** (`results` = answer-text per-tenant, D18) | AIE-2 | ✅ AIE-2 chốt CẦN (kb#24) |
| `obs.golden_sets` | D DROP (xác nhận AIE-1 gate thay mentor) | AIE-1 | cần ký |
| `kb.chunks` | mẫu tham chiếu | DE | ✅ đã có |

## Vì sao cần ký (B · B2 · C · D — không phải A)
Bật RLS / DROP bảng **đổi runtime lane khác** + là quyết định INV-1. → Ký chuẩn **1 lần**, rồi mỗi chủ lane tự thực thi.

## Chữ ký (B · B2 · C · D) — gate 4 thành viên (DE · SWE · AIE-1 · AIE-2)
| Vai | Người | Ký |
|---|---|---|
| DE (bút + mẫu kb) | Nguyễn Đông Anh | ✅ — B·B2·C·D |
| SWE | Thiệu Quang Minh | ✅ 2026-08-12 — **phần B** (RLS `wb.recipes`/`wb.recipe_versions`), PR kb#23 · RLS ở workbench#22. B2/C/D chưa nhận. |
| AIE-1 | Trần Bá Đạt | ✅ 2026-08-12 — **phần B** (`obs.trace_events`). Điều kiện A1-8 (writer bind `app.tenant_id`) **tự đóng** bằng PR `apps/studio#4` do chính AIE-1 mở; DE review+verify (45 passed) → rút objection. *(PR#4 tự giới hạn: chỉ đóng đk kỹ thuật, bật RLS production là AIE-1+DE — gate thay mentor.)* B2/C/D: không phản đối (B2=eval/wb ngoài lane AIE-1). |
| AIE-2 | Lưu Tiến Duy | ✅ 2026-08-03 — **B·C·D** (comment PR kb#10). **✅ B2 (phê ở review kb#24, commit 0ef2728):** chữ ký 03/08 là trên **bản "hoãn" cũ** (*"quyết tenant-scope sau, không RLS mù"*) — **KHÔNG** tính là phê amendment D18 (*"KHÔNG CẦN"* là nghĩa khác). Lập trường D18 do chính AIE-2 chốt ở review kb#24: `eval.golden_sets` **KHÔNG CẦN ✅**, `eval.scorecards` **→ CẦN** (`results` = answer-text per-tenant). Doc đã khớp (bản này) → **đã phê B2 chính thức**. |

**Trạng thái chữ ký:** **B** — đủ 4/4 thành viên (DE·SWE·AIE-1·AIE-2). **B2·C·D** — mới DE ký đủ; AIE-2 đã chốt phần eval của B2 ở kb#24 (golden_sets KHÔNG CẦN, scorecards CẦN) và **đã phê chính thức** amendment (review kb#24); `obs.costs` (B2, lane DE) chưa build; SWE/AIE-1 còn hở wb/invariant/drop. Chữ ký 03/08 của AIE-2 **không** tính vào B2-amendment.

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
| `obs.costs` | apps/studio | — (shell) | ❌ | **CẦN** khi/nếu build (D19 kb#22 KHÔNG build — on-read `trace_events`) |
| `eval.golden_sets` | evalhub | — | ❌ | **KHÔNG CẦN** (đề chung) · AIE-2 phê kb#24 |
| `eval.scorecards` | evalhub | — (chỉ `agent_id`) | ❌ | **CẦN** — `results` = answer-text per-tenant (`harness.py:530`+`:540`); AIE-2 chốt kb#24 |
| `obs.golden_sets` | apps/studio | — (shell, 0 ref) | ❌ | **D — DROP?** |
| `core.tenants` | apps/studio | — (registry) | n/a | **KHÔNG CẦN** (registry định danh) |

RLS duy nhất: `kb_chunks_tenant_isolation`. Reader `obs.trace_events`: `read_run` lọc `WHERE run_id AND tenant_id`
(trace_reader.py:70). wb tables write-free (`publish()`/`rollback()` stub). `obs.golden_sets` **và**
`eval.golden_sets` đều 0 runtime reader; chọn `eval.golden_sets` làm nguồn sự thật theo **quyền ghi**
(evalhub/AIE-2 ghi được; `obs.golden_sets` ở `apps/studio` không ai điền) — DEC-Q5.
</details>
