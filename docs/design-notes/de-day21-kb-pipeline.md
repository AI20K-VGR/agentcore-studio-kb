# Note DE → AIE-1: điền `KbPipeline` (lệch scope #30 có chủ ý — chuyển 2.0, sắp gỡ 1.0)

**Ngày:** 2026-08-17 (Day 21) · **Người viết:** DE (Nguyễn Đông Anh) · **Gửi:** AIE-1 (Trần Bá Đạt, author #30)
· **Liên quan:** issue #30, PR điền `KbPipeline`.

## TL;DR

Mình điền `KbPipeline` nhưng **lệch scope frozen của #30 có chủ ý**, vì mình **đang chuyển KB sang corpus
2.0 và sắp gỡ 1.0**. PR này **chưa gỡ gì** — đường ghi/đọc production (`KbIngest`/`PgKbSearch`/
`ingest_callisto` v1) **giữ nguyên 100%**, chỉ thêm `pipeline.py`. Ghi lại đây để AIE-1 khỏi review theo
bản #30 cũ và nắm hướng sắp tới.

## 3 điểm lệch so với #30 + lý do

| #30 chốt | Mình làm | Vì sao |
|---|---|---|
| `chunker` → `doc_factory.chunk_document` (**1.0**, front-matter) | `chunker` → `doc_factory_v2._cut_document` (**2.0**, role theo tên file) | 1.0 sắp bị gỡ; xây pipeline trên bản sắp chết là nợ ngay khi merge |
| Chỉ 3 hàm; `consent_purge`/`re_index` **giữ `NotImplementedError`** | Điền **cả 5** | 2.0 lên spine thì vòng đời dữ liệu (purge/re-index) cần luôn; `re_index` cũng chính là đường migrate khi đổi `EMBEDDING_DIM` |
| `index` → gọi `KbIngest.ingest` | `index` tái dùng `_UPSERT`+`_bind_tenant`, **nhận embeddings tính sẵn** | Bản #30 bị **double-embed**: `embed_invoke` embed, rồi `KbIngest.ingest` embed lần nữa. Tách `embed_invoke`↔`index` gỡ mâu thuẫn đó |

Giữ nguyên theo #30: không gộp `search`, không đổi call-site `KbIngest`/`PgKbSearch` ở `apps/studio`,
không sửa `chunk_document`/`derive_vector`/`KbIngest`/`PgKbSearch`.

## Điều AIE-1 cần biết (touch points khi 2.0 lên)

1. **Nội dung `kb.chunks` sẽ đổi:** 140 chunk (v1) → **800 chunk (2.0)** khi migrate. Retrieval mà AIE-1
   tiêm (`PgKbSearch`) sẽ đọc corpus khác.
2. **`chunk_id` đổi scheme:** v1 `ankor-leave-001#c1` → 2.0 `ankor-hr-leave#c1` (`{tenant}-{role}-{name}#c{n}`,
   citation = tên file). Mọi `expected_citation` trong golden-set sẽ phải re-annotate — đây là việc DE, báo trước.
3. **`EMBEDDING_DIM` vẫn = 8** trong PR này (chưa đổi). Khi cắm EmbeddingService thật của AIE-1 cho 800 chunk
   + đổi dim (768/1536) = **mini-RFC riêng** (đổi cột `vector(N)` + dựng lại HNSW + `re_index`), mình sẽ mở
   trước, không tự đổi.
4. **Chưa gỡ 1.0 trong PR này.** Gỡ `doc_factory.chunk_document` / `load_callisto` / `docs/callisto/` (1.0) là
   **bước sau, PR/issue riêng**, sẽ ping AIE-1 vì nó chạm đường AIE-1 tiêm + fixture embedding v0.

## Nhờ AIE-1

- Xác nhận shape 5-hàm 2.0 (`chunker→embed_invoke→index`, `Chunk`-based) **ăn khớp** cách AIE-1 tiêm
  `PgKbSearch`/`EmbeddingService` — có gì lệch nói sớm.
- Chốt **thời điểm** cần EmbeddingService thật cho 800 chunk (để mình xếp lịch migrate + mini-RFC dim).
- #30: mình sẽ **cập nhật scope** (comment) thay vì close nguyên văn, vì đã deviate — nhờ AIE-1 duyệt hướng.
