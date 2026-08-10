---
id: studio.decision-log.doc-factory
type: decision-log
owner: DE — Nguyễn Đông Anh
scope: doc-factory + corpus Callisto (docs/callisto/, golden/) — data-design, KHÔNG phải contract
started: 2026-08-04 (D12)
canonical_location: PENDING (Q-2 — cùng blocker với 2 log contract)
---

# Decision-log — doc-factory / corpus Callisto (DE)

> Ghi quyết ngày D12 khi **khởi động Callisto Handbook** (`#85`). Không thuộc 2 contract DE cầm
> (trace-event · kb.search) nên tách log riêng, cùng nằm dưới blocker Q-2 (vị trí canon chưa chốt).
> Format: `ID · ngày · quyết · lý do · đánh đổi`.

| ID | Ngày | Quyết | Lý do | Đánh đổi / ghi chú |
|---|---|---|---|---|
| **DL-12.1** | 04/08 | Corpus **mọc tại chỗ** trong `docs/callisto/` (không tách dir riêng), 5→**42 doc / 140 chunk**, **additive** (5 doc gốc nguyên byte). | `callisto-doc-schema.md` §1/§8 khung corpus mọc chính trong `docs/callisto/`; giữ **một** `load_callisto()` cho D13 ingest, không chẻ hai nguồn `chunk_id`. | Vỡ 3 test coupling vào số 25 → sửa có chủ đích: DL-12.3 (embeddings), DL-12.4 (SC-05), `test_pg_kb` ingest 25→140. Canary `test_doc_factory` 25→140. |
| **DL-12.2** | 04/08 | `section_role` **giữ 4 vai** (`public/hr/finance/engineering`), **không mở** (legal/it/sales…). | Đóng **Q-A** theo mặc định plan D12-1. Contract `kb.search` FROZEN chỉ mang `section_role: str` (không enum vocab) → giữ 4 vai **không** cần mini-RFC; mở vocab mới ăn vào fence/golden/leak + hardcode SWE. | Handbook vẫn giàu (mỗi tenant đủ 4 vai). Muốn mở sau = mini-RFC. |
| **DL-12.3** | 04/08 | **Re-record ngay** `golden/embeddings-callisto-v0.json` phủ đủ 140 chunk — **không hoãn D13**. | `test_embedding_fixture` assert fixture == tập chunk corpus; grow-in-place (DL-12.1) buộc phủ lại. Vector deterministic (bag-of-words blake2b) nên re-record rẻ, không cần model/gateway. | Đảo mặc định plan D12-4 (vốn nghiêng "hoãn D13"): grow-in-place ép làm luôn. `corpus_ref` trong fixture cập nhật "42 doc / 140 chunk". |
| **DL-12.4** | 04/08 | **Leak-test SC-05** (`test_static_search`) đổi oracle `== []` → **loại-trừ** (mọi hit đúng vai `engineering`, KHÔNG rò `hr`/lương), theo khuôn SC-04. `test_pg_kb` SC-05 cùng hướng. | Corpus mới có nội dung `engineering` thật cho ankor → scope không còn rỗng, câu hỏi token-khớp vài chunk engineering hợp lệ. `== []` khoá cứng giả định "engineering rỗng" — đúng lý do SC-04 vốn tránh `== []`. | **Chạm test an ninh** — ghi rõ ở đây. Ý nghĩa fence **giữ nguyên/mạnh hơn** (không nới lỏng): chứng minh không rò chéo-vai thay vì "không có gì". |
| **DL-12.5** | 04/08 | Golden Handbook **tách file** `golden/callisto-handbook-30-draft.yaml` (skeleton 9 case) + harness `scripts/annotate_golden.py`; **không đụng** smoke-5/10. | smoke-5/10 đang được `builder_d4/d6` + evalhub tham chiếu (`smoke-10` header) — đổi = sửa lane SWE/AIE-2. Nhãn trích từ retrieval thật (kỷ luật D6), `--expect` chặn `chunk_id` gõ sai. | Đủ 30 case = DoD **D16 (#105)**, điền tiếp theo khung. `-draft` cho tới khi AIE-2 nghiệm thu. |
| **DL-16.1** | 10/08 | Golden-set lên **recorded**: nguồn typed `src/studio_kb/golden_set.py` (`GOLDEN_CASES`), yaml sinh byte-identical qua `scripts/emit_golden_set.py` (khuôn `grid_queries`/`embeddings`). **Gộp "1 lệnh 2 deliverable"** `scripts/build_callisto.py` (KB embeddings + golden từ **cùng** `load_callisto()`). **Promote** `git mv callisto-handbook-30-draft.yaml → callisto-golden-30-v1.yaml`. | #105 đòi "từ chính doc-factory (1 script 2 deliverable)"; recorded biến kỷ luật tay D6 thành gate byte-identical → sửa case mà quên re-emit là ĐỎ. Rename: AIE-2 xác nhận (10/08) harness đọc bằng `golden_set_ref`, **không** hardcode path — chỉ `test_golden_set.py:29` cần sửa kèm. | **Zero content diff**: `render_yaml()` tái tạo đúng-từng-byte bộ D14 (rename thuần R100), nhãn 30 case **không đổi**. Sửa `test_golden_set.py:29` (path) trong CÙNG commit + thêm guard byte-identical/phủ-biên(`EDGE_AXES`)/khoá-22-8 — **không** nới assert cũ. `manual_label` (D18/#115) chừa chỗ, chưa thêm. |
