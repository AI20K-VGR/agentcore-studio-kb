---
id: studio.decision-log.kb
type: decision-log-index
owner: DE — Nguyễn Đông Anh
scope: agentcore-studio-kb (2 contract DE cầm: trace-event · kb.search)
started: 2026-08-03
split: 2026-08-04 (D12)
canonical_location: PENDING (Q-2)
---

# Decision-log — kb (DE) · INDEX

> **⚠️ Vị trí canon chưa chốt (Q-2).** DoD #80 đòi *"decision-log ghi"* nhưng repo chưa có file
> decision-log dùng chung. Nếu mentor/leader chỉ định một decision-log chung (kit? contracts?),
> **di 2 file dưới về đó** và để lại con trỏ. Không tự quyết vị trí canon thay leader.

**Đã tách theo 2 contract DE cầm (D12).** File monolithic gốc chia đôi để mỗi contract có decision-log
riêng, khớp bảng chữ ký sống trong từng contract (`§0.2`):

| Decision-log | Contract | Quyết |
|---|---|---|
| [`decision-log-trace-event.md`](decision-log-trace-event.md) | `trace-event.v0` | DL-11.1 (`ts`) · DL-11.2 (`cost` một-nguồn) · DL-11.3 (`node_type` enum) · DL-11.4 (carrier) · DL-11.7 (`obs.costs` hoãn) |
| [`decision-log-kb-search.md`](decision-log-kb-search.md) | `kb.search.v0` | DL-11.5 (Q-G slug→UUID) · DL-11.6 (stub) |
| [`decision-log-doc-factory.md`](decision-log-doc-factory.md) | doc-factory / corpus (không phải contract) | DL-12.1 (corpus mọc tại chỗ 5→42 doc) · DL-12.2 (vocab giữ 4 vai) · DL-12.3 (embeddings re-record) · DL-12.4 (SC-05 loại-trừ) · DL-12.5 (golden Handbook tách file) |

**Hai quyết schema-drift KHÔNG thuộc riêng contract nào** → canon ở
[`../mini-rfc-tenant-schema-unify.md`](../mini-rfc-tenant-schema-unify.md):

- **DL-11.8** — `core.jobs`/`core.outbox` **loại trừ** read-RLS (queue/outbox drain cross-tenant); RLS
  đáng cho `wb.*` + `obs.trace_events`, hoãn `obs.costs` + `eval.*`. *(mini-rfc §"Loại trừ" `:64`,`:72`)*
- **DL-11.9** — phần A `wb` `tenant`→`tenant_id UUID` (SWE, PR#13, chờ merge) · `obs.golden_sets` nghi
  bảng chết trùng lặp → đề xuất DROP (xác nhận mentor). *(mini-rfc phần A `:25-26` + phần D `:50-53`)*

> **Chưa có chữ ký nào (0/4).** Bảng chữ ký sống trong từng contract (`§0.2`), không ở đây. Blocker
> chung Q-1/Q-2 (nơi freeze · decision-log canon) lặp trong cả hai file vì chặn ký cả hai.
