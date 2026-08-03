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
  (recipe = IP tenant, playground liệt kê), `obs.trace_events` (trace/cost/citations).
- **2 bảng KHÔNG bật read-RLS** (hàng đợi infra drain cross-tenant, RLS sẽ phá): `core.jobs`, `core.outbox`.
- **4 bảng HOÃN** (chưa có cột tenant — quyết cột trước): `obs.costs`, `obs.golden_sets`,
  `eval.golden_sets`, `eval.scorecards`.
- **1 registry** `core.tenants` — n/a (key = `id`).
- **1 đã có** `kb.chunks`.

→ **3 + 2 + 4 + 1 + 1 = 11.**

## Đề xuất
- **A — cột workbench** `tenant TEXT`→`tenant_id UUID` (`workbench/schema.py:31,43`, `publish.py:47`).
  Workbench-internal (không lane khác đọc, không FK; `resolve_tenant()` đã trả UUID). → **SWE tự sửa, KHÔNG cần ký.**
- **B — bật RLS cho 3 bảng** theo mẫu `kb_chunks_tenant_isolation`
  (`ENABLE`+`FORCE` + `USING (tenant_id = current_setting('app.tenant_id')::uuid)`):
  - `wb.recipes`, `wb.recipe_versions` — **phải làm SAU A** (policy cần cột `tenant_id UUID`).
  - `obs.trace_events` — reader hiện tại `PgTraceReader.read_run` đã lọc `tenant_id` (an toàn ngay);
    **cost aggregator D19 (#120, việc DE) phải tenant-aware** hoặc đi đường admin có chủ đích.
- **B-excl — `core.jobs`/`core.outbox`: KHÔNG read-RLS** (xem "Loại trừ"). Cùng lắm enforce phía **ghi**.
- **B2 — 4 bảng chưa có cột tenant:** quyết *"có cần tenant-scope không?"* → nếu có, thêm `tenant_id UUID`
  rồi mới RLS (gắn với DE điền `obs.costs`/`obs.golden_sets` + AIE-2 `eval.*`). Không RLS mù khi chưa có cột.
- **C — invariant từ nay:** bảng tenant-scoped **có đường user đọc** ⇒ `tenant_id UUID` + RLS theo mẫu
  + 1 leak-test có răng (T1/T6: inclusion dương trước, rồi loại trừ). Chống tái drift khi S2 thêm bảng.

## Loại trừ có chủ đích — `core.jobs` / `core.outbox` (KHÔNG read-RLS)
Đây là hàng đợi hạ tầng **drain cross-tenant**, không có đường user đọc:
- `core/queue.py:68` — worker claim job bằng `SELECT ... FOR UPDATE SKIP LOCKED WHERE status='pending'`,
  **không** predicate tenant (cố ý lấy job mọi tenant).
- `core/schema.py` docstring — dùng **`FORCE ROW LEVEL SECURITY`** "bite cả owner".
→ Bật read-RLS theo `app.tenant_id` sẽ khiến worker/dispatcher **chỉ thấy 1 tenant → hàng đợi tắc**,
kể cả chạy `studio_owner`. Lợi ích security ≈ 0 (không có đường user đọc). Kết: **không read-RLS**;
nếu cần thì chỉ enforce phía ghi. (Ghi DL-11.8.)

## Ai thực thi + thứ tự
| Bảng | Việc | Lane | Cần ký? |
|---|---|---|---|
| `wb.recipes`,`wb.recipe_versions` | A đổi cột **→ rồi** B RLS | SWE | A:❌ · B:✅ |
| `obs.trace_events` | B RLS (+ D19 aggregator tenant-aware) | mentor (apps/studio) + DE | ✅ |
| `core.jobs`,`core.outbox` | **loại trừ** read-RLS | mentor | — (ghi DL) |
| `obs.costs`,`obs.golden_sets` | B2 thêm cột→RLS | DE điền / mentor | ✅ |
| `eval.golden_sets`,`eval.scorecards` | B2 quyết tenant-scope | AIE-2 | ✅ |
| `kb.chunks` | mẫu tham chiếu | DE | ✅ (đã có) |

## Vì sao cần ký (B · B2 · C — không phải A)
Bật RLS **đổi runtime lane khác** (query phải `SET app.tenant_id`, không thì gãy) + là quyết định INV-1.
→ Ký chuẩn **1 lần**, rồi mỗi chủ lane tự thực thi phần mình.

## Chữ ký (B · B2 · C)
| Vai | Người | Ký |
|---|---|---|
| DE (bút + mẫu kb) | Nguyễn Đông Anh | ✅ |
| SWE | Thiệu Quang Minh | ⬜ |
| AIE-1 | Trần Bá Đạt | ⬜ |
| AIE-2 | Lưu Tiến Duy | ⬜ |
| mentor (obs·core) | | ⬜ |

*Chốt xong ghi decision-log. Non-goal: INV-1 roles (đó là #110/#112, D17).*

---
<details><summary>Phụ lục — inventory bằng chứng (kiểm 03/08)</summary>

| Bảng | Lane | Cột tenant | RLS hiện | Quyết |
|---|---|---|---|---|
| `kb.chunks` | kb | `tenant_id UUID` | ✅ | mẫu |
| `wb.recipes` | workbench | `tenant TEXT` ⚠️ | ❌ | A→B RLS |
| `wb.recipe_versions` | workbench | `tenant TEXT` ⚠️ | ❌ | A→B RLS |
| `obs.trace_events` | apps/studio | `tenant_id UUID` | ❌ | B RLS |
| `core.jobs` | apps/studio | `tenant_id UUID` | ❌ | **loại** (queue drain) |
| `core.outbox` | apps/studio | `tenant_id UUID` | ❌ | **loại** (outbox drain) |
| `obs.costs` | apps/studio | — (shell) | ❌ | B2 |
| `obs.golden_sets` | apps/studio | — (shell) | ❌ | B2 |
| `eval.golden_sets` | evalhub | — | ❌ | B2 |
| `eval.scorecards` | evalhub | — (chỉ `agent_id`) | ❌ | B2 |
| `core.tenants` | apps/studio | — (registry) | n/a | n/a |

RLS duy nhất: `kb_chunks_tenant_isolation` (`ENABLE`+`FORCE`). Mâu thuẫn nội bộ workbench:
`tenant_wall.py:70 resolve_tenant()->UUID` nhưng storage vẫn `str`.
Reader `obs.trace_events`: `PgTraceReader.read_run` lọc `WHERE run_id AND tenant_id` (trace_reader.py:70).
</details>
