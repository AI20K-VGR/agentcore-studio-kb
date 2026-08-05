---
id: studio.decision-log.kb-search
type: decision-log
owner: DE — Nguyễn Đông Anh
scope: contract `kb.search.v0` (1 trong 2 contract DE cầm)
sibling: decision-log-trace-event.md
started: 2026-08-03
canonical_location: PENDING (Q-2)
---

# Decision-log — kb.search (DE)

> **⚠️ Vị trí canon chưa chốt (Q-2).** DoD #80 đòi *"decision-log ghi"* nhưng repo chưa có file
> decision-log dùng chung. File này là **bản ghi kb-local của DE** cho các quyết chốt ở D11 **thuộc
> contract `kb.search.v0`**; nếu mentor/leader chỉ định một decision-log chung (kit? contracts?),
> **di về đó** và để lại con trỏ. Không tự quyết vị trí canon thay leader.
>
> Nguồn luật freeze: umbrella §3 (`:92-93`) · **D-12** · **INV-5** · GITFLOWS §5. Đổi contract sau
> freeze = **mini-RFC + 4/4 chữ ký + decision-log**.
>
> **Tách file (D11):** decision-log gốc chia đôi theo 2 contract DE cầm — nửa `trace-event` ở
> [`decision-log-trace-event.md`](decision-log-trace-event.md). Hai quyết **schema-drift** (DL-11.8
> `core.jobs`/`core.outbox` không read-RLS · DL-11.9 `wb` `tenant_id`/`obs.golden_sets` DROP) **không
> thuộc riêng contract nào** → canon ở [`../mini-rfc-tenant-schema-unify.md`](../mini-rfc-tenant-schema-unify.md).

## D11 · 2026-08-03 · Contract-freeze workshop (#84)

| # | Quyết | Lý do | Trạng thái / người ký |
|---|---|---|---|
| **DL-11.5** | **Q-G (slug→UUID thật) ĐÓNG theo D-13:** producer/middleware resolve header slug→UUID qua `core.tenants`; kb khoá theo UUID. | Đường resolve **ngoài lằn kb**; kb chỉ nhận UUID. Không chặn freeze kb.search. | ✅ đóng theo D-13 |
| **DL-11.6** | **Q-D stub (`kb.search`) hoãn-có-ghi:** mặc định AIE-1 tự dựng double; bản chung nếu cần đặt `src/studio_kb/stubs.py` class riêng, **không đụng** `KbSearchService`. | `day-03.md:38` + tiền lệ `FakeEmbedding`. Không chặn freeze. | ✅ **AIE-1 xác nhận (engine#15):** tự dựng double **bên engine** — stub sống trong kb thì engine-test không gọi tới được, `.importlinter:20` cấm `studio_engine → studio_kb` (4 quadrant sibling độc lập). Ràng buộc cứng, không phải khẩu vị |

> **Schema-drift (DL-11.8 · DL-11.9)** không thuộc contract này — canon ở
> [`../mini-rfc-tenant-schema-unify.md`](../mini-rfc-tenant-schema-unify.md). Liên quan kb.search ở
> chỗ **`kb.chunks` là mẫu RLS tham chiếu** (`kb_chunks_tenant_isolation`) mà DL-11.8 dựa theo để chốt
> phạm vi bật/loại-trừ; `obs.golden_sets` DROP (DL-11.9) không đụng golden-set thật của kb (`kb/golden/`).

## D13 · 2026-08-05 · Chữ ký ctor `KbSearchService` khi un-ratchet (seam DE×AIE-1, #91/PR-app#3)

| # | Quyết | Lý do | Trạng thái / người ký |
|---|---|---|---|
| **DL-13.1** | **`KbSearchService.__init__` khi un-ratchet (D17) = `(pool, embedding)`, KHÔNG giữ `(pool)`.** `pool` = **non-owner `get_pool()`** — đường dữ liệu kích RLS (`_bind_tenant` đặt `app.tenant_id`, policy `kb_chunks_tenant_isolation` cắn). `embedding` = `EmbeddingService` vector-hoá `query` để cosine với `kb.chunks.embedding`, **cùng không gian với vector seed** (`derive_vector`). `search()` **giữ frozen** (`kb-search.v0.md §0.2`) — `embedding` là collaborator lúc-dựng, không phải tham số mỗi-lần-gọi. | (1) **`.importlinter` cấm `studio_kb → studio_app`/engine** → không import được `EmbeddingService` graded của AIE-1; DI qua ctor là đường DUY NHẤT sạch để nhận đúng embedding, tránh hard-code bag-of-words D13 vào service chính thức (S3 đổi embedding không phải sửa `KbSearchService`). (2) **Đồng dạng `PgKbSearch(pool, embedding)`** — un-ratchet là ủy nhiệm/thay bằng `PgKbSearch`, vốn đã cần `embedding`. (3) Tiêm **một** `EmbeddingService` cho cả `KbIngest` (seed) lẫn search ở composition-root → chống drift seed-space ≠ query-space. (4) Đổi stub↔gateway không sửa class. | 🟡 **Quyết DE — chờ AIE-1 ack.** Đổi `__init__` được phép (chỉ `search()` đóng băng). **Việc D17** (`__init__.py`: un-ratchet sang `PgKbSearch` là RIÊNG của D17); hôm nay `KbSearchService` giữ `NotImplementedError` là **đúng lịch**. **Coordinate PR-app#3:** T3 phải đổi `KbSearchService(pool)` → `KbSearchService(pool, embedding)` tại/sau flip — nếu quên, guard `raises=NotImplementedError` biến `KbSearchService(pool)` thành `TypeError` = FAIL thật lúc land. |

## Câu CHẶN chưa đóng — kb.search (không đóng được trong lằn kb — cần người)

| # | Hỏi ai | Nội dung | Ảnh hưởng |
|---|---|---|---|
| **Q-1** | mentor / leader | Bản `FROZEN` nằm ở draft kb (lật cờ) hay PR bump `SCHEMA_VERSION` ở `contracts` (mentor CODEOWNERS)? | **CHẶN DoD ô 1** (contract commit + freeze). Nếu là contracts → DE cần đường cross-repo, không đóng solo |
| **Q-2** | mentor / leader | decision-log canon ở đâu (chưa có file chung)? + hình thức "4 chữ ký"? | **CHẶN DoD ô 3 & 4** — file này chỉ là bản kb-local tạm |
| **Q-3** | AIE-1 | stub `kb.search` (DL-11.6) | chặn ký kb.search *(vế cost-source/carrier → xem decision-log-trace-event)* |
| **Q-5** | AIE-2 | `expected_citation` khớp `chunk_id` | chặn ký kb.search *(vế field eval đọc trace → xem decision-log-trace-event)* |

> **Chưa có chữ ký nào (0/4).** Bảng chữ ký sống trong contract (`kb-search.v0.md` §0.2). Không ký
> khống — ký sau khi đóng Q-3/Q-5 và đọc delta.
