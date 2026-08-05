# Plan D13 (DE) — KB pipeline THẬT `ingest→embed→index` per-tenant + `kb.search` trả cited chunks

> **Ngày:** 2026-08-05 (D13, Thứ Tư · Chặng 2 / Sprint 2 · Tuần 3) · **Bút:** DE (Nguyễn Đông Anh)
> **Anchor:** issue kit **#90** (con của **#94** "KB thật ingest→embed→index per-tenant + retrieve —
> ghép DE×AIE-1"). Anh em: AIE-1 **#91** (ghép `kb-retrieve` executor thật qua `kb.search` + ES.embed) ·
> SWE **#92** (`kb_binding.scope` trỏ đúng tenant/section) · AIE-2 **#93** (golden-set input draft).
> **Repo WRITE: `agentcore-studio-kb`** · kit READ. **Milestone:** Sprint 2 — Gate Day 20.
>
> Việc DE (#90, dòng tiêu đề): *"Chủ công: KB pipeline `ingest→chunk→embed→index` per-tenant (Callisto 2
> tenant) + `kb.search` trả cited chunks."* DoD 4 ô (ingest→embed→index chạy · kb.search cited · AIE-1
> kb-retrieve tiêu thụ ES stub · fixtures deterministic) là **DoD chung kế thừa từ cha #94** — đọc là
> **"phần DE của 4 ô đó"**, ô "AIE-1 tiêu thụ" là việc #91.

---

## 0. Đọc cho đúng trước khi cắt — D13 là NỐI DÂY + CHỨNG MINH, không phải viết engine từ đầu

Ba điều đặt lằn ranh của ngày:

**(a) Tầng Postgres thật ĐÃ tồn tại từ trước D13.** `postgres.py` (commit `2de0c1a` "tầng Postgres thật
… CHƯA nối vào") có sẵn `KbIngest` (ghi: `Chunk` → embed → `kb.chunks`, idempotent `ON CONFLICT`, gom
theo tenant, non-owner pool) và `PgKbSearch` (đọc: cosine trên pgvector, lọc fail-closed
`tenant_id`+`section_role`). `schema.py` có sẵn DDL `kb.chunks` + HNSW `vector_cosine_ops` + RLS
`ENABLE/FORCE` + policy `USING/WITH CHECK`. `test_pg_kb.py` là **bộ test-first hoàn chỉnh** (ingest
idempotent · 2-tenant · sai-chiều · T1 · T6 · section_roles rỗng · top_k biên gồm `=1` · 140-chunk thật
· RLS unset-tenant). → D13 **không viết pgvector từ đầu**; việc là **bật hạ tầng cho test xanh THẬT +
đóng gói thành lệnh chạy được + mở seam cho AIE-1**.

**(b) Seam `KbSearchService`/`KbPipeline` cố ý KHÔNG lật ở D13.** `test_search_contract.py` (XANH) khẳng
định `KbSearchService.search` phải `NotImplementedError`; `test_leak.py` T1/T6 `xfail(strict=False)` qua
`KbSearchService`; README ghi un-ratchet là việc RIÊNG (P5/P9). Fence qua **seam chính thức** là **D17
(#110)**. Nên hôm nay giữ cả hai test nguyên trạng (**không sửa test để pass**); AIE-1 tiêu thụ bằng cách
**tiêm thẳng `PgKbSearch`** — nó đã thoả `studio_contracts.KbSearch`.

**(c) Data đã đủ, không cần "thêm chunk".** Corpus 42 doc / 140 chunk (D12, đã merge `origin/main` =
`51df3a4`) là đầu vào; `chunk_id` bền; fixture `embeddings-callisto-v0.json` phủ 140 vector deterministic.
D13 **bơm** data sẵn-có vào Postgres, không mở rộng corpus.

Lằn giữ nguyên: **chỉ WRITE trong `packages/kb`**; **không đụng** `apps/studio` composition, engine
(#91), workbench, contracts. Bàn giao AIE-1 bằng **seam + tài liệu trong kb**, không viết sang repo khác.

---

## 1. Việc đã làm (nhánh `day13/de-kb-pipeline-live`, nền `origin/main` = 51df3a4 · **chưa commit — chờ review**)

### ① `scripts/ingest_callisto.py` — biến `KbIngest` thành LỆNH CHẠY ĐƯỢC (DoD "ingest…chạy")
`load_callisto()` (140 chunk) → embed → `kb.chunks` qua **pool non-owner** (`studio_app`, để `WITH CHECK`
cắn), gom theo tenant, idempotent. Tách `ingest_all(pool)` khỏi `main()` để test gọi được; `main()` thiếu
`STUDIO_DATABASE_URL` **báo lỗi to** kèm hướng dẫn, không chạy câm. **Không tự dựng schema** (việc
composition-root) — chỉ ghi dữ liệu. Embedding dùng adapter **cục bộ** `_FixtureEmbedding` bọc
`derive_vector` (cùng công thức fixture), **không** export EmbeddingService cạnh tranh (protocol ghi
"Owner: AIE-1") — đúng mẫu `test_pg_kb.py::BagOfWordsEmbedding`.

### ② Export seam pg trong `src/studio_kb/__init__.py`
Thêm `KbIngest`, `PgKbSearch` vào `__all__` → AIE-1 `from studio_kb import PgKbSearch` được. Vá drift
docstring "25 chunk" → "140" (D12). Ghi rõ trong docstring: `PgKbSearch` là seam AIE-1 tiêm thay
`StaticKbSearch`/`EmptyKbSearch`; `KbSearchService` giữ `NotImplementedError` (un-ratchet = D17).

### ③ `tests/test_ingest_script.py` — test cho glue của script (file mới, không đụng test cũ)
3 test: `ingest_all` nạp đúng 140 · idempotent chạy-lại vẫn 140 · `main()` thiếu DSN → `SystemExit`.

---

## 2. DoD #90 (phần DE) — đối chiếu

- [x] **KB ingest→embed→index per-tenant chạy** — `test_pg_kb` 10/10 xanh THẬT + `scripts/ingest_callisto.py`
  chạy: `ankor 71 · borea 69 = 140`, idempotent (lần 2 vẫn 140).
- [x] **`kb.search` trả cited chunks** — `PgKbSearch` trả `KbSearchResultItem` mức `chunk_id` (cited),
  cosine pgvector, T1/T6/real-corpus xanh.
- [~] **AIE-1 kb-retrieve tiêu thụ ES stub** — DE cung: `PgKbSearch` exported + nhận `EmbeddingService`
  tiêm + fixture chung. Code wiring là #91 (engine) — **coordinate, không DE-gated / không đụng repo engine**.
- [x] **fixtures deterministic** — `record_embeddings.py` re-record byte-identical (`git diff` rỗng),
  140 chunk / 8 chiều; `test_embedding_fixture` xanh.

---

## 3. Bàn giao AIE-1 (#91) — bằng seam + tài liệu TRONG kb

- `PgKbSearch(pool, embedding)` là `kb.search` thật để **tiêm thay `EmptyKbSearch`** ở `KbRetrieveExecutor`.
- **Cùng một `EmbeddingService` deterministic** ở cả ingest lẫn search (nếu không, vector truy vấn khác
  không gian vector chunk → ranking vô nghĩa). Fixture `golden/embeddings-callisto-v0.json` là nguồn chung;
  công thức `derive_vector` (`embeddings.py`) là đường tính khớp fixture.
- Ràng buộc còn lại giữa hai bên chỉ là **số chiều** `EMBEDDING_DIM=8` (`schema.py`, khớp `FakeEmbedding.dim`).
- Ghi ở docstring `__init__.py` + `postgres.py`; **không post lên #91**, không WRITE sang engine (kb-only).

---

## 4. Bằng chứng (env pinned 3.14 · Postgres sống port 5433 · skip ≠ pass)

- `docker compose -f docker-compose.test.yml up -d --wait` + 2 DSN (`studio_app`/`studio_owner`).
- **Toàn suite kb: 80 passed, 2 xfailed** (2 xfail = leak qua `KbSearchService` còn `NotImplementedError`,
  cố ý). Trước khi bật DB là skip — nay xanh thật.
- **Toàn workspace: 355 passed, 8 skipped, 4 xfailed** — không vỡ consumer (engine/apps import `studio_kb`
  sạch dù `__init__` giờ kéo `postgres`; `psycopg[binary,pool]` đã là dep runtime của kb).
- **Lệnh ingest thật:** `ankor 71 · borea 69 = 140`, chạy lại idempotent; đếm rows DB per-tenant khớp.
- **Lint:** `ruff` sạch · `mypy` sạch · `lint-imports` "quadrant layering KEPT".
- **Mutation sweep:** 93 mutant / 9 sống sót — **đều là các sống sót có sẵn đã triage "tương đương"**
  (30/07); code mới không phát sinh lỗ (`postgres.py` 184/144 nằm trong nhóm đã ghi).
- Interpreter **3.14** (`.venv/bin/python`), không `python3` trần (local 3.11 — bẫy quen).

---

## 5. Còn treo / ngoài phạm vi hôm nay

- **KbSearchService flip + un-ratchet `test_leak` xfail → D17 (#110)**, không làm ở D13.
- **Daily-note `docs/reports`** (convention hằng ngày) nằm **ngoài submodule kb** — giữ lại, chỉ làm khi
  được yêu cầu (chỉ đạo: chỉ WRITE trong kb).
- **Chưa commit/push, chưa mở PR** — chờ review (đúng nhịp D12).
