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

## Vấn đề (số thật, 03/08 — kiểm từng bảng)
11 bảng, chỉ **`kb.chunks`** có RLS. Chia đúng thực trạng:
- **5 bảng có cột tenant nhưng THIẾU RLS** → hở INV-1 (đang dựa lọc-tầng-app, fail-open):
  `obs.trace_events`, `core.jobs`, `core.outbox`, `wb.recipes`, `wb.recipe_versions`.
- **4 bảng CHƯA có cột tenant** (không thể RLS per-tenant tới khi thêm cột): `obs.costs`,
  `obs.golden_sets` (shell rỗng), `eval.golden_sets`, `eval.scorecards`.
- **1 registry** `core.tenants` — không RLS per-tenant (key = `id`, là danh bạ tenant).
- Cột tenant còn **lệch tên/kiểu** ở workbench: `wb.recipes`/`wb.recipe_versions` = `tenant TEXT`
  (còn lại `tenant_id UUID` theo D-13).

## Đề xuất
- **A — cột workbench** `tenant TEXT`→`tenant_id UUID` (`workbench/schema.py:31,43`, `publish.py:47`).
  Workbench-internal (không lane khác đọc, không FK; `resolve_tenant()` đã trả UUID). → **SWE tự sửa, KHÔNG cần ký.**
- **B — bật RLS ngay cho 5 bảng có sẵn cột tenant** theo **đúng mẫu** `kb_chunks_tenant_isolation`
  (`ENABLE`+`FORCE` + `USING (tenant_id = current_setting('app.tenant_id')::uuid)`).
- **B2 — 4 bảng chưa có cột tenant:** quyết trước *"có cần tenant-scope không?"* → nếu có thì thêm
  `tenant_id UUID` rồi mới RLS (gắn với việc DE điền `obs.costs`/`obs.golden_sets` + AIE-2 `eval.*`).
  Không bật RLS mù khi chưa có cột.
- **C — invariant từ nay:** bảng tenant-scoped ⇒ **`tenant_id UUID` + RLS theo mẫu + 1 leak-test có răng**
  (T1/T6: inclusion dương trước, rồi loại trừ). Chống tái drift khi S2 thêm bảng.

## Vì sao cần ký (B · B2 · C — không phải A)
Bật RLS **đổi runtime lane khác** (query phải `SET app.tenant_id`, không thì gãy) + là quyết định INV-1.
→ Ký chuẩn **1 lần**, rồi **mỗi chủ lane tự thực thi phần mình** (DE đã làm mẫu `kb.chunks`).

## Ai thực thi phần nào
| Bảng | Việc | Lane | Cần ký? |
|---|---|---|---|
| `wb.recipes`,`wb.recipe_versions` | A đổi cột + B RLS | SWE | A:❌ · B:✅ |
| `obs.trace_events` | B RLS | mentor (apps/studio) | ✅ |
| `core.jobs`,`core.outbox` | B RLS | mentor | ✅ |
| `obs.costs`,`obs.golden_sets` | B2 thêm cột→RLS | DE điền / mentor | ✅ |
| `eval.golden_sets`,`eval.scorecards` | B2 quyết tenant-scope | AIE-2 | ✅ |
| `kb.chunks` | mẫu tham chiếu | DE | ✅ (đã có) |

## Chữ ký (B · B2 · C)
| Vai | Người | Ký |
|---|---|---|
| DE (bút + mẫu kb) | Nguyễn Đông Anh | ✅ |
| SWE | Thiệu Quang Minh | ⬜ |
| AIE-1 | Trần Bá Đạt | ⬜ |
| AIE-2 | Lưu Tiến Duy | ⬜ |
| mentor (obs·core) | | ⬜ |

*Chốt xong ghi decision-log (DL-11.x). Non-goal: INV-1 roles (đó là #110/#112, D17).*

---
<details><summary>Phụ lục — inventory bằng chứng (kiểm 03/08)</summary>

**11 bảng / cột tenant / RLS:**
| Bảng | Lane | Cột tenant | RLS |
|---|---|---|---|
| `kb.chunks` | kb | `tenant_id UUID` | ✅ |
| `obs.trace_events` | apps/studio | `tenant_id UUID` | ❌ |
| `core.jobs` | apps/studio | `tenant_id UUID` | ❌ |
| `core.outbox` | apps/studio | `tenant_id UUID` | ❌ |
| `wb.recipes` | workbench | `tenant TEXT` ⚠️ | ❌ |
| `wb.recipe_versions` | workbench | `tenant TEXT` ⚠️ | ❌ |
| `obs.costs` | apps/studio | — (shell) | ❌ |
| `obs.golden_sets` | apps/studio | — (shell) | ❌ |
| `eval.golden_sets` | evalhub | — | ❌ |
| `eval.scorecards` | evalhub | — (chỉ `agent_id`) | ❌ |
| `core.tenants` | apps/studio | — (registry, key=`id`) | n/a |

RLS duy nhất: `kb_chunks_tenant_isolation` (`ENABLE`+`FORCE`). Mâu thuẫn nội bộ workbench:
`tenant_wall.py:70 resolve_tenant()->UUID` nhưng storage vẫn `str`.
</details>
