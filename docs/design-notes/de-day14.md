---
id: studio.design-note.de.day-14
type: design-note
role: DE — Nguyễn Đông Anh
day: 14
date: 2026-08-06
status: draft (chờ review — bàn giao #96)
scope: golden query + expected chunks cho grid chunking×embedding · teeth · ràng buộc dim-8
length_target: ≤2 trang
---

# Design-note DE (D14) — Golden query + expected chunks cho grid `chunking×embedding`

> Neo: issue **#95** (*"Cấp golden query + expected chunks để AIE-1 đo recall/precision có nhãn; đảm bảo
> 2 embedding-impl khả dụng qua ES"*), tiêu thụ bởi **#96** (AIE-1, chủ công grid). Đây là **thiết kế +
> đánh đổi + ràng buộc bàn giao**, không tóm tắt lại yaml.

## 1. DE giao gì

- **`golden/callisto-grid-queries-v0.yaml`** — 20 case (`GQ-01..14` dương, `GQ-15..20` âm T1/T6), shape
  8-field `docs/format.md` §2 (đọc y hệt `smoke-5.yaml`).
- **Nguồn sự thật là `src/studio_kb/grid_queries.py`** (typed `GRID_CASES`); yaml **sinh ra** bằng
  `scripts/emit_grid_queries.py`, byte-identical (kb không kéo `pyyaml`, nên nguồn phải typed). #96 có thể
  **import thẳng `grid_queries.GRID_CASES`** khỏi parse yaml, hoặc đọc yaml — cùng một dữ liệu.

## 2. Đánh đổi cốt lõi: teeth (finding D11) — vì sao mọi case dương có ≥2 ứng viên cùng scope

`citation_accuracy` **không có răng** khi fence lọc còn đúng 1 ứng viên hợp lệ: case xanh vì lý do sai,
embedding tốt/xấu không phân biệt được. Nên bộ này chọn câu hỏi mà **≥2 chunk cùng `tenant`+`section_role`**
cùng token-khớp → thứ hạng THẬT SỰ phụ thuộc embedding. `tests/test_grid_inputs.py` khoá tính chất này
(không khai suông): mỗi case dương phải có `≥2` ứng viên cùng vai + `expected_citation ⊆` ứng viên.

Phổ độ khó có chủ đích, để grid thấy được cả hai đầu:

| case | ứng viên đầu bảng (điểm token `StaticKbSearch`) | biên | ý đồ |
|---|---|---|---|
| `GQ-01` | `ankor-remote-001#c1` 0.846 vs `#c2` 0.769 | **0.077** (hẹp) | ca nặng F-8 — dim-8 gần như hoà |
| `GQ-05` | `ankor-oncall-001#c2` 0.69 vs `#c1` 0.31 | 0.38 (rộng) | đối chứng — embedding dở vẫn nên đúng |

## 3. Ràng buộc BẮT BUỘC cho #96: mọi embedding đo qua ES phải **dim-8**

`kb.chunks.embedding` là `vector(8)` (`schema.py`), HNSW cosine trên đúng width đó. `KbIngest`
(`postgres.py:137-140`) **raise ngay** nếu `len(vector) != EMBEDDING_DIM`; `PgKbSearch` embed query rồi so
cột `vector(8)` → vector chiều khác là lỗi pgvector. Và **`PgKbSearch` là nơi DUY NHẤT embedding ảnh hưởng
ranking** (`StaticKbSearch` xếp bằng token-overlap, không đụng vector). ⇒ Trục "embedding" của grid phải
đo **qua `PgKbSearch`/pgvector với vector 8 chiều**; đừng thử nới `EMBEDDING_DIM` để "tăng headroom" — sẽ
vỡ ingest + là schema-drift. *(DE đã cân nhắc dim-32 và loại vì lý do này.)*

## 4. "2 embedding-impl khả dụng qua ES" = stub↔gateway, KHÔNG phải DE cấp 2 embedding

**D-6** (`decisions-locked.md`): `EmbeddingService` Protocol **2-impl = StubEmbedding (fixtures, CI) +
GatewayEmbedding (Phase-2/S3)** — một interface, đổi impl không sửa interpreter (`day-07.md:25`). Đây là
**seam của AIE-1**. Phần DE chỉ là **fixture vector dim-8** cho impl stub, **đã có sẵn**
(`golden/embeddings-callisto-v0.json`, 140 chunk, `test_embedding_fixture.py` canh). D14 **không có
deliverable code embedding mới** phía DE.

## 5. Kỷ luật threshold (đồng thuận #93)

**KHÔNG** chốt ngưỡng `citation_accuracy` trên đường PG **trước khi** #96 có baseline embedding từ grid
này. Grid D14 chính là để tìm baseline đó — chốt ngưỡng trước là chốt trên số chưa có nghĩa.

## 6. Ngoài phạm vi D14

- Trục **chunk-size** của grid: chunking là `doc_factory` (heading-based, không có tham số size). Nếu #96
  cần corpus ở chunk-size thứ 2, **coordinate** — DE phơi tham số re-chunk, không tự mở rộng.
- **golden-set 30 case đầy đủ = D16 (#105)**. Bộ GQ này là *đầu vào đo cho grid*, không phải bộ 30.
- **Số 20 case là chọn của DE, KHÔNG có quy định.** #95/#99/roadmap D14 không nêu số golden query (chỉ
  nêu grid "≥2×2" = kích thước bảng). Chọn 20 để mỗi ô grid là `x/14` (mịn hơn `x/7`). **#96 nên xác nhận
  20 có đủ** cho recall/precision có nghĩa, hay cần thêm — DE mở rộng theo cùng khung `grid_queries.py`.
