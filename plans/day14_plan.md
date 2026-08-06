# Plan D14 (DE) — Cấp golden query + expected chunks (nhãn) + trục embedding thứ 2 cho grid `chunking×embedding` của AIE-1

> **Ngày:** 2026-08-06 (D14, Thứ Năm · Chặng 2 / Sprint 2 · Tuần 3) · **Bút:** DE (Nguyễn Đông Anh)
> **Anchor:** issue kit **#95** (con của **#99** "Interpreter đủ 6 node-type + `chunking×embedding`
> trade-off ĐO SỐ"). Anh em: AIE-1 **#96** (chủ công: 6 node-type executor đóng + đo grid qua ES 2-impl
> trên golden query của DE) · SWE **#97** (condition/tool-call seam trong canvas) · AIE-2 **#98** (eval
> harness reader: đọc outputs + citations từ trace).
> **Repo WRITE: `agentcore-studio-kb`** · kit READ. **Milestone:** Sprint 2 — Gate Day 20.
>
> Việc DE (#95, dòng tiêu đề): *"Cấp **golden query + expected chunks** (từ doc-factory) để AIE-1 đo
> recall/precision **có nhãn**; đảm bảo **2 embedding-impl** khả dụng qua ES."* DoD 3 ô (6 node-type chạy ·
> DAG 4-node emit event · bảng `chunking×embedding` ≥2×2 có số + kết luận) là **DoD chung kế thừa từ cha
> #99** — đọc là **"phần DE của 3 ô đó"**: DE cấp **nhãn + trục embedding**; đóng 6-node/DAG là #96, seam
> canvas là #97, đo-và-kết-luận grid là #96.

---

## 0. Đọc cho đúng trước khi cắt — D14 là CẤP NHÃN + TRỤC ĐO, không phải viết executor hay tự đo grid

Bốn điều đặt lằn ranh của ngày:

**(a) Nền phải là main MỚI — D13 đã đóng.** PR kb **#13** (`feat D13 — KB pipeline thật`) và **#14**
(`docs DL-13.1`) **đã MERGED** (05/08); `kit#139` pointer-bump CI 10/10 pass; `agentcore-report#53`
merged. Local đang đứng nhánh `day13/de-kb-pipeline-live` (`b977bd1`, **đã merged**) và `origin/main`
local còn cũ (`51df3a4` = D12). → **`git fetch` + cắt nhánh D14 trên `origin/main` mới**, KHÔNG xây tiếp
trên nhánh D13 ([đừng coi nhánh checkout là bất khả xâm phạm — refresh mỗi ngày]).

**(b) DE cấp NHÃN. "2 embedding-impl" KHÔNG phải việc DE cấp 2 embedding.** #96 (AIE-1, chủ công) đóng 6
node-type + chạy grid — đó là repo **engine**, lane AIE-1. Việc DE (#95) chỉ gọn trong kb: **golden query +
expected chunks có nhãn** để AIE-1 tính recall/precision. Về *"đảm bảo 2 embedding-impl khả dụng qua ES"*:
**D-6** (`decisions-locked.md:20`) khoá *"`EmbeddingService` Protocol **2-impl** (stub local + gateway)"* —
tức **1 interface, 2 backend: StubEmbedding (fixtures, CI) ↔ GatewayEmbedding (Phase-2/S3)**, để *đổi impl
không sửa interpreter* (`day-07.md:25`). Đây là **seam kiến trúc của AIE-1**, KHÔNG phải hai embedding khác
nhau để so chất lượng. Phần DE: **fixture vector dim-8 đã có** (`embeddings-callisto-v0.json`) là dữ liệu
cho impl stub chạy — **đã tồn tại, không thêm fixture nào**. DE **không** export EmbeddingService (protocol
"Owner: AIE-1", `embeddings.py:46-53`).

**(c) F-8 là ĐẦU VÀO của grid D14, không phải bug phải vá hôm nay.** Carry-over từ comment đóng #93:
*"nhãn chưa sống qua đường KB thật — 2/7 giữ rank 1; `EMBEDDING_DIM=8` thiếu headroom, median pairwise
cosine 0.8571"* (tracking ở **#96**). Đây chính là **con số grid D14 phải giải thích**, không phải hồi
quy. Kỷ luật đồng thuận (#93): **KHÔNG chốt threshold `citation_accuracy` trên đường PG trước khi có
baseline embedding**. Việc DE: cấp **các case teeth (≥2 ứng viên cùng scope)** để #96 CÓ dữ liệu đo
headroom — không tự đo, không tự kết luận. **Không nới dim** (xem §1②).

**(d) Teeth-fix (finding D11) là hình dạng nhãn D14.** `citation_accuracy` "không có răng" khi mỗi case
chỉ có 1 ứng viên hợp lệ sau fence (hiện 2/6 trong HB draft có ≥2 ứng viên cùng scope). Golden query cấp
cho grid **phải phủ ca có ≥2 chunk cạnh tranh cùng `tenant`+`section_role`**, nếu không recall/precision
không phân biệt được embedding tốt/xấu. Đây là phần D14 của yêu cầu `callisto-golden-30-v1` (đủ 30 = D16
#105), tách riêng "query-có-nhãn-cho-grid".

Lằn giữ nguyên: **chỉ WRITE trong `packages/kb`**; **không đụng** engine (#96), canvas/workbench (#97),
evalhub reader (#98), `apps/studio`. Bàn giao AIE-1 bằng **fixture + tài liệu trong kb**, không viết sang
repo khác. **Schema production giữ `vector(8)`, KHÔNG đổi `EMBEDDING_DIM`, KHÔNG thêm fixture chiều khác**
(giữ O3.2 / schema-drift không tái phát — dặn của mentor S1).

> **Ghi lại lỗi đã suýt phạm (06/08):** bản nháp §1② đầu tiên đề xuất cấp fixture **dim-32** làm "trục
> embedding thứ 2". SAI: `kb.chunks` là `vector(8)`, `postgres.py:137-140` (`KbIngest`) raise ngay nếu
> `len(vector) != EMBEDDING_DIM`, và `PgKbSearch` là **nơi duy nhất** embedding ảnh hưởng ranking
> (`StaticKbSearch` xếp bằng token-overlap) — nên vector 32 chiều không đo được bằng chính đường nó phục
> vụ. Đã revert sạch (`embeddings.py` git diff rỗng). Bài học: "2-impl" là stub↔gateway (b), không phải
> nới chiều.

---

## 1. Việc sẽ làm (nhánh `day14/de-golden-grid-inputs`, nền `origin/main` MỚI · test-first)

### ① `golden/callisto-grid-queries-v0.yaml` — bộ golden query + expected chunks CHO GRID  ✅ ĐÃ LÀM
**Nguồn sự thật = `src/studio_kb/grid_queries.py`** (typed), yaml **sinh ra** bằng
`scripts/emit_grid_queries.py` (byte-identical) — cùng kỷ luật "recorded" của `embeddings.py`; kb cố ý
**không kéo `pyyaml`** nên không đọc-lại yaml trong test, phải để module typed làm nguồn. **20 case**: 14
dương (`GQ-01..GQ-14`) + 6 âm T1/T6 (`GQ-15..GQ-20`). Tiền tố `GQ-` để không đụng `SC-` (smoke) / `HB-`
(draft). Shape 8-field `docs/format.md` §2 (đúng như smoke-5). **Số 20 là DE tự chọn — #95/#99/roadmap D14
KHÔNG quy định số** (chỉ grid "≥2×2"); chọn 20 cho mỗi ô grid `x/14` mịn hơn; bộ đủ 30 là D16 (#105). Nên
xác nhận số với #96.

Điểm cốt: **mọi case dương để lại ≥2 ứng viên cùng `tenant`+`section_role`** (teeth, finding D11) —
annotate-verified qua `scripts/annotate_golden.py` (`StaticKbSearch`, không cần DB). Ca nặng nhất `GQ-01`:
`ankor-remote-001#c1` (0.846) chỉ hơn `#c2` (0.769) **0.077** ở điểm token — đúng "thiếu headroom" F-8;
`GQ-05` biên rộng (oncall #c2 0.69 vs #c1 0.31) làm đối chứng. Đây là dữ liệu để #96 đo embedding phân
biệt được hay không — DE **không** đo.

### ② "2 embedding-impl" — KHÔNG có việc code cho DE (đã hiểu lại đúng)
"2-impl" = **stub↔gateway** (D-6, §0b), seam của AIE-1. Phần DE là **fixture vector dim-8** cho impl stub
— **đã có** `golden/embeddings-callisto-v0.json` (140 chunk, `EMBEDDING_DIM=8`), `test_embedding_fixture.py`
canh byte-identical. **Không thêm fixture, không đổi `embeddings.py`, không nới dim** (lý do ở §0 đuôi).
Nếu #96 muốn DE tinh chỉnh fixture stub → coordinate, nhưng mặc định D14 **không có deliverable code ở ô này**.

### ③ Trục `chunk-size` — coordinate với #96 (chunking là doc-factory = DE)
Grid `chunking×embedding ≥2×2` cần **2 độ hạt chunk**. Chunking thuộc `doc_factory.py` (DE). Sáng D14 hỏi
#96: AIE-1 muốn DE **cấp corpus ở chunk-size thứ 2** (phơi tham số re-chunk trong `doc_factory`, recorded)
hay AIE-1 tự vary? Mặc định đề xuất: DE phơi `chunk_size` param + xuất 1 biến thể thứ 2 recorded (chunk_id
bền, deterministic) để **trục chunk-size là data DE thật**, không phải AIE-1 đoán. Deliverable ③ **có điều
kiện** theo chốt coordinate — không tự ý mở rộng nếu #96 tự vary.

### ④ `tests/test_grid_inputs.py` — test cho glue (file MỚI, không đụng test cũ)
Chạy lại phép kiểm annotate trong CI (`StaticKbSearch`, không DB):
- **dương:** mỗi `GQ-01..14` — `expected_citation ⊆` ứng viên trả về **và** `len(ứng viên) ≥ 2` cùng
  `tenant`+`section_role` (teeth thật, không khai suông).
- **âm:** mỗi `GQ-15..20` — `expected_citation == []` **và** fence chặn: không ứng viên nào thuộc
  `expected_tenant`/`expected_section_role` bị hỏi chéo (T1/T6 không rò).
- **byte-identical:** `callisto-grid-queries-v0.yaml` trên đĩa `==` `render_yaml()` (bắt drift gõ tay).

**Không** đụng `test_embedding_fixture.py` (dim-8) — nó vẫn 5 passed, không liên quan.

---

## 2. DoD #95 (phần DE) — đối chiếu

- [x] **golden query + expected chunks có nhãn** — `callisto-grid-queries-v0.yaml` (20 case: 14 dương teeth
  ≥2 ứng viên cùng scope + 6 âm T1/T6), nhãn **annotate-verified** trên corpus 140-chunk (không gõ tay).
- [x] **2 embedding-impl khả dụng qua ES** — "2-impl" = stub↔gateway (D-6), seam AIE-1; phần DE là fixture
  dim-8 cho stub **đã có sẵn** (`embeddings-callisto-v0.json`). **Không có việc code mới cho DE** ở ô này.
- [~] **6 node-type executor chạy · DAG 4-node emit event** — DoD chung, việc **#96/#97** (engine/canvas).
  DE **coordinate, không DE-gated / không đụng repo engine**.
- [~] **bảng `chunking×embedding` ≥2×2 có số + kết luận** — DE cấp **nhãn (grid queries)** làm ground-truth
  (+ trục chunk-size theo ③ nếu chốt). **Đo và kết luận là #96**; DE cấp INPUT, không tự đo trên engine.

---

## 3. Bàn giao AIE-1 (#96) — bằng fixture + tài liệu TRONG kb

- `callisto-grid-queries-v0.yaml` là **ground-truth** để #96 tính recall@k / precision có nhãn; nguồn
  typed `grid_queries.py` để #96 import trực tiếp nếu muốn (khỏi parse yaml).
- **Teeth:** mọi case dương có ≥2 ứng viên cùng scope → thứ hạng phụ thuộc THẬT vào embedding; đây là dữ
  liệu để #96 đo headroom F-8 (dim=8 median cosine 0.857), **qua `PgKbSearch`/pgvector** (nơi duy nhất
  embedding ảnh hưởng ranking — `StaticKbSearch` chỉ token-overlap).
- **Kỷ luật (đồng thuận #93):** KHÔNG chốt threshold `citation_accuracy` trên đường PG **trước** baseline
  embedding. Grid D14 là để tìm baseline đó.
- **Ràng buộc chống schema-drift:** `kb.chunks` là `vector(8)`; **mọi embedding đo qua ES đều phải dim-8**
  (nếu không `KbIngest` raise / pgvector từ chối). Không có fixture chiều khác.
- "2-impl" (stub↔gateway) là lane AIE-1 — DE chỉ cấp fixture dim-8 stub (đã có). Ghi ở design-note trong
  kb; **không post lên #96**, không WRITE sang engine.

---

## 4. Bằng chứng (env pinned 3.14 · Postgres sống port 5433 · skip ≠ pass)

- **`git fetch` trước** — D13 PR#13/#14 đã merged; cắt `day14/de-golden-grid-inputs` trên `origin/main`
  mới (không nền nhánh D13).
- `docker compose -f docker-compose.test.yml up -d --wait` + 2 DSN (`studio_app`/`studio_owner`) **TRƯỚC**
  khi chạy test/viết báo cáo (SOP; skip ≠ pass — O3.2).
- `test_grid_inputs.py` xanh: 20 case annotate-verified (`StaticKbSearch`, không DB) + yaml byte-identical.
- `embeddings.py` **git diff rỗng** (đã revert dim-32) · `test_embedding_fixture.py` vẫn 5 passed.
- **Toàn suite kb xanh** (cần Docker cho `test_pg_kb`) · `ruff` sạch · `mypy` sạch · `lint-imports` KEPT.
- Interpreter **3.14** (`.venv/bin/python` hoặc `uv run --python 3.14`), **không `python3` trần** (local
  3.11 — bẫy quen; check lại interpreter trước khi báo mọi SyntaxError).
- Mutation sweep cho glue mới (`grid_queries.py` render + `test_grid_inputs.py`); code mới không phát sinh lỗ.

---

## 5. Còn treo / ngoài phạm vi hôm nay

- **golden-set 30 case ĐẦY ĐỦ = D16 (#105)**. D14 chỉ cấp **query-có-nhãn-cho-grid** (subset + ca teeth),
  KHÔNG phải bộ 30.
- **Kết luận trade-off + chọn chunk-size (và embedding impl) = #96 (AIE-1)**. DE cấp input, không kết luận.
- **Threshold `citation_accuracy`** chốt **sau** baseline embedding — không D14.
- **KbSearchService flip + un-ratchet `test_leak` xfail → D17 (#110)** — không D14.
- **Carry-over NON-kb** (ghi để không rơi, nhưng ngoài lane DE): F-4 `e2e_smoke_eval.py:274` heuristic T6
  (chưa owner) · version-drift `apps/studio` `test_eval_adapter` (lane AIE-1/SWE). Chỉ nêu, không WRITE.
- **Daily-note `docs/reports`** nằm **ngoài** submodule kb — chỉ làm khi được yêu cầu (chỉ đạo: WRITE trong kb).
- **Chưa commit/push, chưa mở PR** — chờ review (đúng nhịp D12/D13).
