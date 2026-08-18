# Kế hoạch: Harness đánh giá embedding (300 test, test-first) cho KB Callisto 2.0

## Context — vì sao làm cái này

Thực nghiệm 2026-08-17 (nhánh kb `experiment`) đã chứng minh: wire corpus Callisto 2.0 (800 chunk) qua đường sống `KbIngest → kb.chunks → PgKbSearch` **chạy trọn về mặt cơ học** (ingest 800, RLS cô lập tenant tuyệt đối), **nhưng embedding placeholder dim-8 `derive_vector` không kham nổi 800 chunk**: top-1 cho query "quyền truy cập production database" lại là `public-dress-code` (sai chủ đề), điểm cosine dồn cụm 0.87–0.93, khoảng cách rank1→rank10 nén ~2× so với 1.0. Kết luận: cần **embedding ngữ nghĩa thật**.

**Nhiệm vụ lần này KHÔNG phải chọn/hiện thực model.** Theo yêu cầu: viết trước bộ **300 test** (đúng tinh thần test-first) làm **dụng cụ đo** để *sau đó* dùng chính nó chọn phương thức embedding. Vậy sản phẩm là một **harness đánh giá embedding model-agnostic** + tập 300 case có nhãn (DE sở hữu giá trị) + baseline dim-8 đóng băng. Model (Gemini / ONNX e5 / sentence-transformers / lexical) sẽ cắm vào **cùng harness** này để so và quyết định — không chọn bây giờ.

## Quyết định đã chốt với DE

| Trục | Chốt |
|---|---|
| Phương thức embedding | **Hoãn** — test quyết định sau; harness model-agnostic |
| Nguồn 300 case | **LLM-draft theo tầng + DE verify** (DE sở hữu nhãn cuối) |
| Pass bar | **Tương đối: vượt baseline dim-8 ≥ margin, theo từng tầng** (baseline check-in, không lách được) |
| Đổi `EMBEDDING_DIM` | **Hoãn** → khi chọn model, đi qua **mini-RFC** tới apps/studio (`FakeEmbedding.dim`) + AIE-1 (tiền lệ `day18/de-mini-rfc-schema-drift`, marker `[PRIOR]` ở `schema.py:32`) |

## Ràng buộc sở hữu (đọc kỹ, không lấn lane)

- `EmbeddingService` protocol **owner = AIE-1** (`packages/contracts/.../protocols.py:17`). DE sở hữu **fixture vector đã-ghi + công thức + corpus + nhãn eval**. Ràng buộc cross-quadrant duy nhất = **số chiều** (`EMBEDDING_DIM`).
- `.importlinter`: `studio_kb` **cấm** import `studio_app`/engine/workbench/evalhub → harness chỉ được phụ thuộc `studio_contracts` + lib ngoài. **Không** import `FakeEmbedding`.
- Harness **model-agnostic**: chấp nhận bất kỳ object shape `EmbeddingService` (`async embed(texts)->list[list[float]]`) và **KHÔNG** ghim `EMBEDDING_DIM=8` — chấm được model bất kỳ số chiều.

## Thiết kế harness

Thư mục mới: `packages/kb/tests/embedding-tests/` (đã nằm dưới `testpaths=packages/kb/tests`, pytest đệ quy collect; **basename duy nhất** kiểu `test_embedding_*.py` để không đụng import-mode `prepend`; helper/fixture đặt trong `conftest.py` của thư mục này để né vấn đề import ở thư mục có dấu `-`).

**1. Tập case có nhãn** — `cases/` (**JSON**, không YAML: kb cố tình không kéo `pyyaml` — xem `embeddings.py`/`golden_set.py`; JSON stdlib vẫn review + diff được). Tách theo tầng cho dễ review, mỗi case:
```
id, query, tenant (ankor|borea), section_roles, expected_citation (list[str]),
stratum (S1..S5), decoy_hint (chunk gây nhiễu, để review near-miss), notes
```
5 tầng × ~60 case = **300**, rải đều ankor/borea + 4 role:
- **S1 lexical-easy** — sàn tỉnh táo (query trùng từ khoá đáp án).
- **S2 paraphrase/synonym** — query cùng nghĩa, **ít trùng token** với chunk đúng.
- **S3 near-miss decoy** — cùng role, chủ đề kề; **decoy nhiều trùng token** hơn đáp án.
- **S4 cross-role confusion** — đáp án đúng role, decoy ở role khác trùng từ.
- **S5 negative/no-answer** — **không** nên trả gì trên ngưỡng (đo false-positive).

Chống vòng-lặp (bẫy lexical): luật dựng case S2–S4 = *chunk đúng ít trùng token với query, decoy nhiều trùng* — nếu không, lexical baseline cũng thắng và test không phân biệt được ngữ nghĩa. Đây là điều `test_embedding_dataset_integrity` cưỡng chế (xem dưới).

**2. Retrieval in-memory** (`conftest.py`): cosine trên {chunk_id→vector} của 800 chunk (`load_corpus_v2`), **lọc TRƯỚC rồi xếp hạng** đúng ngữ nghĩa `PgKbSearch` (tenant + section_role → cosine desc → top-k). Không đụng Postgres cho 300 case (nhanh, deterministic). Dành **vài test pg-parity** riêng: cùng query, khẳng định thứ hạng pgvector khớp in-memory (chứng minh fixture ↔ DB đồng ý) — chạy trên `docker-compose.test.yml` (5433, cô lập).

**3. Metric** — tái dùng công thức `citation_accuracy = |expected ∩ retrieved_topk| / |expected|` (`packages/evalhub/.../harness.py:349`); tổng hợp **recall@k + MRR theo từng tầng**. S5 đảo chiều: đo tỷ lệ trả nhầm (thấp = tốt).

**4. Embedding-under-test** — provider tiêm qua fixture, **mặc định = baseline dim-8** (`derive_vector`, tính live, tức thì). Model ứng viên sau này cắm cùng seam (tính live hoặc đọc fixture vector đã-ghi của nó, giữ kỷ luật single-read-path như `embeddings.py`).

**5. Baseline đóng băng** — `baseline-dim8.json` (check-in): recall@k + MRR **của dim-8 trên chính 300 case**, đo **ngay bây giờ** (không cần model mới). Đây là mốc so tương đối; nằm trong git diff nên không hạ lén được.

**6. Cơ chế 300 test + pass bar (tương đối):**
- **300 item parametrize** (mỗi case 1 item — "300 test" = 300 case qua `@pytest.mark.parametrize`): mỗi item chạy embedding-under-test, **ghi hit@k vào collector theo tầng**, và **assert tính toàn vẹn case** (expected_citation phân giải ra chunk thật; tenant/role hợp lệ; bất biến tầng — vd S3 decoy trùng-token > đáp án). Phần integrity **xanh với mọi model** → 300 test là artifact test-first bảo vệ ground-truth.
- **Gate hiệu quả** = nhóm test **per-stratum** riêng: `recall@k(under_test) ≥ recall@k(baseline) + margin[stratum]`. Với under_test=baseline → bằng nhau → **CI xanh**; cắm model ứng viên → gate cưỡng chế "phải hơn dim-8 mỗi tầng". `margin` nhỏ, nằm trong `baseline-dim8.json`.
- Case kỳ vọng-đỏ ở baseline (nếu dùng biến thể xfail) phải `strict=True` (bài học kb#19 F1) — nhưng thiết kế chính là collector+gate ở trên, không cần xfail hàng loạt.

**7. Property/guard band** (đếm RIÊNG, ngoài 300 — tránh thổi phồng): determinism (cùng text→cùng vector), số chiều nhất quán, text rỗng không NaN, cô lập tenant/role do fence quyết (đánh dấu là guard, **không** tính vào "300 chứng minh embedding" vì chúng pass bất kể embedding).

## Tái dùng (không viết mới)

- `load_corpus_v2` (`studio_kb.doc_factory_v2`) · `resolve_tenant_id`/`SECTION_VOCAB`/`TENANT_IDS` (`doc_factory`) · `derive_vector` (baseline, `studio_kb.embeddings`) · công thức `citation_accuracy` (evalhub harness) · pattern verify nhãn của `scripts/annotate_golden.py` (thích ứng cho corpus 2.0 in-memory).

## Kỷ luật thực thi

Test-first (viết case + harness + baseline TRƯỚC mọi model); **không sửa test cho pass**; tự gieo mutation đúng seam trước review; chạy đủ 5 bước CI trước push (pytest·ruff check·ruff format·mypy·lint-imports); pin 3.14 (`.venv/bin/python` hoặc `uv run --python 3.14`). Làm trên nhánh sandbox `experiment` (kb) — không lên main; PR #29 đã đóng.

## Các file dự kiến

- `packages/kb/tests/embedding-tests/conftest.py` — fixtures: corpus 800 chunk, retriever cosine in-memory, embedding-under-test provider, collector theo tầng.
- `packages/kb/tests/embedding-tests/cases/s1..s5.json` — 300 case có nhãn (DE verify).
- `packages/kb/tests/embedding-tests/test_embedding_cases.py` — 300 item parametrize (integrity + ghi metric).
- `packages/kb/tests/embedding-tests/test_embedding_gate.py` — gate per-stratum vs baseline.
- `packages/kb/tests/embedding-tests/test_embedding_properties.py` — property/guard band.
- `packages/kb/tests/embedding-tests/baseline-dim8.json` — baseline đóng băng + margin.
- (pg-parity) 1 file test nhỏ dùng stack test 5433.

## Verification

1. `uv run --python 3.14 pytest packages/kb/tests/embedding-tests -q` → **300 case + gate + property xanh với baseline** (gate bằng nhau, integrity pass).
2. Tự gieo mutation: sửa retriever bỏ lọc role → S4 gate/integrity phải đỏ; hoàn tác.
3. Đo baseline: sinh `baseline-dim8.json`, `git diff` cho thấy con số dim-8 theo tầng (thấp ở S2–S5 — đúng kỳ vọng).
4. pg-parity: `docker compose -f docker-compose.test.yml up -d` → test khớp thứ hạng in-memory ↔ pgvector.
5. Đủ 5 bước CI trước khi push nhánh `experiment`.

## Ngoài phạm vi (bước sau)

- Chọn/hiện thực model embedding thật (dùng harness này để quyết).
- Đổi `EMBEDDING_DIM` + re-ingest + rebuild HNSW → **mini-RFC** tới apps/studio (`FakeEmbedding.dim`) + AIE-1.
- Di dời golden-30/grid/embeddings 1.0 sang 2.0 (khi 2.0 chính thức thay 1.0).
