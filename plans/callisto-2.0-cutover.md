---
id: studio.de.callisto-2.0-cutover
type: cutover-plan
status: draft
author: DE — Nguyễn Đông Anh
supersedes-when-done: callisto-doc-schema.md + corpus 1.0 (docs/callisto/) + đường 1.0
---

# Callisto 2.0 — kế hoạch gỡ 1.0 & chuyển sang 2.0

> **Câu hỏi file này trả lời:** *tôi (DE) cần làm gì và mỗi lane cần làm gì để tháo hẳn
> Callisto 1.0 và cho spine chạy trên 2.0 — theo thứ tự nào để không gãy giữa chừng?*

## 0. Nguyên tắc chốt (đã quyết trong repo, KHÔNG mở lại thiết kế)

- **Thứ tự bất di:** `wire → parity → cutover → delete`. Nguồn: `docs/callisto-2.0-schema.md`
  frontmatter `supersedes-when-wired` + thân "khi nào 2.0 được duyệt để thay 1.0 mới tính chuyện
  di dời golden-set/test". **Xoá 1.0 trước là sai** — mất mất baseline để chứng minh cutover.
- **Không sửa lịch sử.** `docs/reports/**` (nhật ký, gate) và `docs/requirements/**` (charter/NDA
  INV-3) chứa citation 1.0 (`ankor-leave-001#c1`…) như **bằng chứng đã xảy ra**. Cấm rewrite.
- **`doc_factory.py` KHÔNG bị xoá nguyên khối** — `doc_factory_v2` đang mượn `Chunk`,
  `SECTION_VOCAB`, `resolve_tenant_id` từ nó. Phải tách primitive dùng chung ra module trung tính
  TRƯỚC, rồi 1.0-riêng mới xoá được.
- **SOP Docker (O3.2):** mọi phát biểu "ingest chạy" phải có daemon bật + DSN export + chạy thật.
  `skip ≠ pass`. Đụng code người khác → pin `.venv/bin/python` hoặc `uv run --python 3.14`.

> **PARK (18/08, theo yêu cầu):** cổng embedding (§2, Phase P/D) tạm gác — DE đang viết test chứng
> minh embedding tốt hơn, KHÔNG bump dim-8. Phase **A** ✅ và **B** ✅ (không đụng embedding) đã xong;
> còn lại C (ingest script) trở đi cần EmbeddingService thắng cuộc từ P.

## 1. Hiện trạng (18/08/2026)

| Mảnh | 1.0 (đang chạy spine) | 2.0 (đã dựng, CHƯA wire) |
|---|---|---|
| Corpus | `docs/callisto/` — 42 doc / 140 chunk | `docs/callisto-2.0/` — 80 doc / ~800 chunk ✅ có |
| Cutter | `doc_factory.chunk_document` (front-matter) | `doc_factory_v2._cut_document` (thư mục/tên file) ✅ |
| Loader/pipeline | `doc_factory.load_callisto` + `scripts/ingest_callisto.py` | `pipeline.KbPipeline` (cut v2 + write reuse) ✅ có, `test_pipeline.py` ✅ |
| Embedding | `embeddings.derive_vector` **dim-8** (bag-of-words) | `KbPipeline` nhận `EmbeddingService` tiêm vào (agnostic) |
| Vector space | `schema.EMBEDDING_DIM = 8`, DDL `vector(8)` | **DÙNG CHUNG** cột `vector(EMBEDDING_DIM)` |
| Golden | `golden/callisto-golden-30-v1.yaml`, `embeddings-callisto-v0.json`, `callisto-grid-queries-v0.yaml`, `smoke-5/10.yaml` | **chưa có** golden 2.0 |
| Search runtime | `static_search.StaticKbSearch` → `load_callisto()`; `search.KbSearchService` → `derive_vector` | (chưa trỏ sang 2.0) |

**Cái CÒN THIẾU để cutover:** (a) script ingest lái `KbPipeline` trên `docs/callisto-2.0/`;
(b) golden-set 2.0 để đo parity; (c) quyết cổng embedding (§3).

## 2. Embedding — hướng đã chốt (KHÔNG bump dim)

`KbPipeline` đã embedding-agnostic ⇒ **plumbing không nghẽn**: nó nhận `EmbeddingService` tiêm vào.

**Quyết định DE (18/08):** *không* bump `EMBEDDING_DIM`, *không* đo dim-bump. Dim-8 bag-of-words
coi như **known-bad** cho 800 chunk (đụng độ băm, xếp hạng rác) — không cần chứng minh lại. Thay
vào đó DE đang **viết test chứng minh một EmbeddingService khác tốt hơn**; embedding mới thắng qua
test đó thì mới là ứng viên wire vào 2.0.

- Đường embedding = **thay `derive_vector` bằng EmbeddingService tốt hơn** (được test bảo chứng),
  KHÔNG phải nong dim-8.
- Việc này chạy **song song** và **không chặn** Phase A/B (tách primitive + golden 2.0).
- Cột `kb.chunks.embedding` có phải đổi `vector(N)` hay không → phụ thuộc embedding thắng cuộc,
  quyết sau khi test xong; nếu đổi thì kèm migration + reindex ~800 chunk qua fence RLS.

## 3. Các pha & chủ trì

| Pha | Việc | Chủ trì | Chặn bởi |
|---|---|---|---|
| **A. Tách primitive** ✅ DONE (18/08) | `doc_factory_core.py` giữ `Chunk`/`SECTION_VOCAB`/`TENANT_IDS`/`resolve_tenant_id` (SSOT); `doc_factory` re-export (mọi import cũ khắp workspace không đổi); `doc_factory_v2` cắt import khỏi 1.0. Guard `test_doc_factory_core.py` canh seam (đỏ-được khi v2 phụ thuộc lại 1.0). CI 5 bước xanh; 373 test collect sạch. | DE | — |
| **P. EmbeddingService tốt hơn** | Test chứng minh embedding khác > dim-8 (§2). Không bump dim-8. Song song, không chặn A/B. | DE | — |
| **B. Golden 2.0** ✅ DONE (18/08) | `golden_set_v2.GOLDEN_CASES_V2` (typed, 22 dương + 8 âm) → `emit_golden_set_v2.py` → `golden/callisto-2.0-golden-30-v1.yaml`; `test_golden_set_v2.py` canh 5 trục trên corpus 2.0 + byte-identical + phủ biên + 12 nhãn tay. Nhãn trace qua `annotate_golden_v2.py` (StaticKbSearch + `_contains_phrase` thật, máy-kiểm uniqueness — corpus gương). `GoldenCase` tách sang `golden_set_core` (1.0 xoá được). Rank-verify hoãn sang parity gate. | DE | A |
| **C. Script ingest 2.0** ✅ DONE (18/08) | `scripts/ingest_callisto_v2.py` lái `KbPipeline` (`load_corpus_v2` → embed_invoke → index) + `_FixtureEmbedding` dim-8 tạm (đổi chỗ tiêm khi có bản AIE-1). Test `test_ingest_script_v2.py`. **Chạy LIVE trên test-stack** (docker-compose.test.yml:5433): 800 chunk (ankor 400+borea 400) vào `kb.chunks`, RLS kín (app.tenant_id=ankor→400), idempotent, pipeline DB tests 13/13 xanh. | DE | (P cho chất lượng), B |
| **D. Migration cột** *(chỉ nếu embedding thắng đổi dim)* | Đổi `EMBEDDING_DIM`, migration cột `vector(N)` + reindex; ghi lại vector fixture mới. | DE | P |
| **E. Wire search sang 2.0** | Trỏ `StaticKbSearch`/`KbSearchService` sang corpus+vector 2.0; giữ contract `kb-search.v0` bất biến (chunk_id/score/tenant). | DE | C, D |
| **F. Parity gate** | Chạy golden 2.0 qua luồng thật, so với baseline 1.0 đã freeze. Đạt ngưỡng → được cutover. | AIE-2 + DE | E, B |
| **G. Đồng bộ lane phụ thuộc** | AIE-1 (retrieve), SWE (recipe), AIE-2 (scorecard) đổi expected citation 1.0 → 2.0 nếu có. Mỗi lane tự grep tree mình. | AIE-1 / SWE / AIE-2 | F |
| **H. Cập nhật README kit** | `README.md` §5 (dòng ~233–242): đổi `ingest_callisto.py`/"42 doc / 140 chunk" → script + số 2.0. | DE (owner kit) | E |
| **I. DELETE 1.0** | Chỉ sau F+G+H xanh. Xoá: `docs/callisto/`, phần 1.0-riêng trong `doc_factory.py` (front-matter/override/`load_callisto`), `scripts/ingest_callisto.py`, `scripts/build_callisto.py`, test 1.0-riêng, `docs/callisto-doc-schema.md`. | DE | F, G, H |

## 4. Mỗi lane cần làm gì (tóm tắt cho team)

- **DE (tôi):** A→P→B→C→(D)→E→H→I. Chủ trì toàn bộ đường dữ liệu. Phép đo embedding (P) là việc
  đầu tiên có giá trị nhất — nó mở khoá phần còn lại và quyết có kéo AIE-1 vào không.
- **AIE-1 (retrieve/EmbeddingService):** *chưa cần làm gì cho tới sau P.* Nếu P = "recall rớt" →
  ship `EmbeddingService` ngữ nghĩa (đúng interface `KbPipeline` đã chờ). Ở G: đổi expected citation.
- **AIE-2 (golden/scorecard):** đồng dựng golden 2.0 (B), chủ trì parity gate (F), cập nhật
  scorecard nếu citation đổi (G).
- **SWE (recipe/engine):** ở G, grep tree engine/workbench tìm citation 1.0 hard-code (grep repo
  cho thấy **hiện không có** — vẫn tự xác nhận lại), đổi nếu có. Không cần làm sớm.
- **Contract owner (`kb-search.v0`):** xác nhận đổi `doc_id` (`ankor-leave-001` → `{tenant}-{stem}`)
  có phá contract citation không; nếu có, cần bản contract mới trước G.

## 5. CẤM ĐỘNG cho tới pha tương ứng

- **Cho tới sau F (parity đạt):** không xoá/ghi đè
  `golden/callisto-golden-30-v1.yaml`, `golden/embeddings-callisto-v0.json`,
  `golden/callisto-grid-queries-v0.yaml`, `golden/smoke-5.yaml`, `golden/smoke-10.yaml`.
  Đây là **baseline duy nhất** để biện minh cutover — freeze/archive, xoá cuối cùng (pha I).
- **Không bao giờ:** sửa `docs/reports/**` và `docs/requirements/**` (charter/NDA INV-3) — lịch sử
  bất biến, citation 1.0 trong đó là bằng chứng, không phải nợ kỹ thuật.
- **Không sửa test để pass** (luật test-first). Test 1.0 chỉ *xoá* ở pha I khi đã hết ai dùng.

## 6. Định nghĩa "xong" (được xoá 1.0)

1. Golden 2.0 qua luồng thật đạt ngưỡng parity so baseline 1.0 (F).
2. Không lane nào còn tham chiếu citation/loader 1.0 (G — mỗi lane tự xác nhận).
3. README kit + overview/detail_overview đã tả 2.0 (H).
4. `docs/callisto-2.0-schema.md` đổi `status: v0-experiment` → `active`, gỡ chữ "SONG SONG/chưa wire".
