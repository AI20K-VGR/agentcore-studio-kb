# Plan D12 (DE) — doc-factory Callisto Handbook (~40–60 doc · 2 tenant) + ground-truth annotation skeleton

> **Ngày:** 2026-08-04 (D12, Thứ Ba · Chặng 2 / Sprint 2 · Tuần 3) · **Bút:** DE (Nguyễn Đông Anh)
> **Anchor:** issue kit **#85** (con của **#89** "Canvas 6-node + recipe validator/graph-lint"). Anh em:
> SWE **#87** (canvas React Flow 6-node, fallback form+Mermaid) · AIE-1 **#86** (refactor interpreter đọc
> recipe) · AIE-2 **#88** (scorecard skeleton + playground-trace wireframe).
> **Repo WRITE: `agentcore-studio-kb`** · kit READ. **Milestone:** Sprint 2 — Gate Day 20.
>
> Việc DE (#85, dòng tiêu đề): *"Khởi động **doc-factory Callisto Handbook** (~40–60 doc, 2 tenant
> `ankor`/`borea`) + **ground-truth annotation skeleton** — nuôi cả KB (D13) lẫn golden-set (D16)."*
>
> **Về DoD của #85:** 4 ô (canvas sinh recipe · graph-lint fail-closed · pytest happy+negative · decision-log
> nếu tụt nấc) là **DoD chung của issue cha #89, kế thừa nguyên văn** — đúng convention repo (D11: #80 kế
> thừa y hệt #84). Không đọc là "dán nhầm"; đọc là **"phần DE của 4 ô đó"** + các việc DE-riêng từ dòng tiêu
> đề #85. Map ở §5, đúng cách `day11_plan.md:183-191` đã làm.

---

## 0. Đọc cho đúng trước khi cắt — D12 là NUÔI DỮ LIỆU, không phải viết pipeline; và "thêm" chứ không "sửa"

Ba điều đặt ra lằn ranh của ngày:

**(a) D12 là content + annotation, KHÔNG phải `KbPipeline` thật.** `doc_factory.py` đã ghi rõ ranh giới:
nó là **máy cắt tĩnh đọc `.md` trên đĩa** cho S1; `KbPipeline.chunker` (`pipeline.py`) — ingest→chunk→
embed→index thật — là **spec-DE của S2, giữ nguyên `NotImplementedError`**, và đó chính là **việc D13
(#90)**. Nhập hai thứ là tự đặt bom cho S2. Nên hôm nay: **mở rộng corpus + annotation** đổ vào máy cắt
tĩnh đang có; **không** động vào `KbPipeline`.

**(b) "1 script, 2 deliverable" (umbrella `:81`) đã là kiến trúc sống, không phải mục tiêu mới.**
`doc_factory.py` docstring: cùng một máy cắt nuôi **cả** dữ liệu KB (`StaticKbSearch` tìm trên nó) **lẫn**
golden-set (`golden/smoke-5.yaml` trích `chunk_id` từ đây). Tách hai máy → lệch `chunk_id` → mọi case ra
0 điểm **không lỗi nào nổi lên** (`docs/format.md §2`). D12 chỉ **mở rộng** đường này, giữ nguyên bất biến.

**(c) Corpus hiện có là ADDITIVE-ONLY — 5 doc cũ đóng-băng-tham-chiếu.** Cắt lại / đổi heading
`ankor-salary-001` v.v. sẽ **dịch số `#cN`** và **âm thầm zero** `golden/smoke-5.yaml` + `smoke-10.yaml`
(chúng pin `ankor-leave-001#c1`, `borea-leave-001#c1`, `ankor-expense-001#c2`, `borea-expense-001#c1`…).
Luật D12: **chỉ THÊM doc mới**; 5 doc gốc không đụng một ký tự. Giữ đặc biệt `ankor-expense-001#c2` — chunk
**duy nhất** trong bộ chạy luật heading-override `{section: finance}`; mất nó là mất chỗ kiểm luật override.

Lằn giữ nguyên: **không sửa test để pass**; **không đụng quadrant khác** (`apps/studio`, engine, workbench,
evalhub) — chỉ báo/coordinate; **không sửa `packages/contracts/**`** (repo mentor); **Python 3.14** — chạy
test bằng `.venv/bin/python` hoặc `uv run --python 3.14`, cấm `python3` trần.

---

## 1. Trạng thái chốt trước (sáng 04/08)

| Mục | Trạng thái |
|---|---|
| Corpus Callisto | **5 doc** (`docs/callisto/`): ankor {salary, expense, leave}, borea {expense, leave}. Frontmatter `tenant/section`. Cần lên **~40–60 doc / 2 tenant** (#85). |
| `doc_factory.py` | Máy cắt tĩnh ổn định: `chunk_id = "{doc_id}#c{n}"` (n từ 1/doc, §6 schema), 1 chunk = 1 heading `##` (§5), 1 chunk = 1 `section_role`, heading `{section:X}` override riêng chunk. `resolve_tenant_id` slug→UUID (fixture S1, xoá khi Q-G chốt). |
| `SECTION_VOCAB` | `frozenset({public, hr, finance, engineering})`, **raise** khi gặp giá trị lạ. Vocab đóng ở `callisto-doc-schema.md §3`, **vẫn mang dấu "đề xuất DE, §10 Q1 chưa chốt team"**. Handbook 40–60 doc dễ "thèm" `legal/it/sales` → **xem Q-A (gating)**. |
| `kb-search.v0.md` | **FREEZE-READY D11** (chờ Q-1 nơi-freeze + 4/4 chữ ký). Return mang `section_role: **str**` — **KHÔNG enum-hoá vocab trong contract**. Nghĩa: mở rộng vocab **không** đổi chữ ký kb.search; nhưng ăn vào fence/golden/leak → vẫn là quyết cần team, không đơn phương. |
| golden-set | `golden/smoke-5.yaml`, `smoke-10.yaml` (trích `chunk_id` + `expected_citation`), `embeddings-callisto-v0.json` (chỉ phủ **5 doc hiện tại**). D16 (#105) cần golden-set 30 case có nhãn **từ chính doc-factory**. |
| ground-truth annotation | **chưa có skeleton** — #85 đòi "annotation skeleton" nuôi golden-set (D16) + expected-chunks cho AIE-1 đo chunking×embedding (D14 #95). |
| Nudge #85 (overdue #84) | **stale** — #84 đã CLOSED 06:49 hôm nay. Bỏ qua, không tốn item. |

---

## 2. Việc DE hôm nay — corpus + annotation, giữ bất biến chunk_id

### D12-1 · CHẶN ⭐ — chốt **từ vựng `section_role`** với team (đầu giờ, trước khi viết doc mới)
Đây là **Q-4 của D12**: viết 40–60 doc handbook rất dễ đẻ ra section mới (`legal`, `it`, `sales`, `sales-ops`…).
`SECTION_VOCAB` đóng ở 4 giá trị và **raise** khi lạ — thêm bừa là vỡ cắt. Hai đường, phải chốt trước:
1. **Giữ 4 vai** (`public/hr/finance/engineering`) → **không** đụng vocab, **không** cần mini-RFC, corpus vẫn
   giàu (một tenant nhiều doc/vai). **Mặc định DE nghiêng đường này** — rẻ nhất, giữ fence/golden ổn định.
2. **Mở vocab** → vì `section_role` ăn vào **fence + leak-test + golden-set** (schema §3 ghi rõ "chốt sớm vì
   ăn cả golden lẫn leak-test") và có thể **SWE validate/hardcode** 4 vai → cần: cập nhật `SECTION_VOCAB` +
   `callisto-doc-schema.md §3` + **hỏi SWE (recipe/graph-lint có ràng vai?)** + decision-log. `kb-search.v0.md`
   **không** phải đổi (chỉ `str`), nhưng vẫn là quyết chạm nhiều lane → xem Q-A.

Không chốt Q-A thì **không viết doc mới** — nếu không, cuối ngày phát hiện phải sửa hàng chục frontmatter.

### D12-2 · Doc-factory: viết ~40–60 doc handbook (ADDITIVE, 2 tenant)
- **Chỉ thêm file mới** vào `docs/callisto/`; **không đụng 5 doc gốc** (§0c). Đặt tên theo tiền lệ
  `{tenant}-{topic}-{NNN}.md`, frontmatter `tenant: ankor|borea` + `section: <vai đã chốt Q-A>`.
- **Cân đối 2 tenant + phủ đủ 4 vai** để fence/leak-test có chỗ bấu: mỗi tenant có doc `public/hr/finance/
  engineering`; cố ý gài vài cặp **cùng-chủ-đề-khác-số** giữa ankor↔borea (tiền lệ `borea-expense-001#c1`
  = 77tr vs ankor 20tr — mồi phát hiện fence hở). Giữ ≥1 doc dùng **heading-override** để luật §5 còn được
  kiểm ở quy mô mới (ngoài `ankor-expense-001#c2`).
- **Cách sinh (commit tĩnh, không generate-lúc-test):** doc là `.md` **commit sẵn trên đĩa**, KHÔNG sinh
  runtime — nếu không, `chunk_id` mất tính deterministic và D14 không pin được expected-chunks. Dùng
  **template frontmatter + nội dung soạn/review tay** (Sprint 2 rubric: *artifact-người-khác-dùng-được* >
  số lượng; nội dung đọc-được-thật hơn là bulk sinh máy). Ghi 1 dòng phương án đã chọn vào decision-log.
- Chạy `doc_factory` trên corpus mới, xác nhận: mọi `chunk_id` **duy nhất & ổn định**, mọi `section_role`
  ∈ vocab, không doc nào làm `resolve_tenant_id` raise.

### D12-3 · Ground-truth annotation skeleton (nuôi D16 golden-set + D14 expected-chunks)
- **Skeleton = khung + quy ước, chưa cần đủ 30 case** (30 case là DoD **D16 #105**; D12 chỉ "khởi động").
  Định dạng thống nhất với golden hiện có (`smoke-5.yaml`): mỗi case `{query, tenant, section_roles,
  expected_citation: [chunk_id...]}` + (cho D14) `expected_chunks`.
- **Nguồn nhãn = chính doc-factory** (#85/#105 "1 script 2 deliverable"): annotation trích `chunk_id`
  **từ output máy cắt**, không gõ tay — gõ tay là mầm lệch `chunk_id` → 0 điểm câm.
- Ship **script/khung annotation** (vd mở rộng đường đang nuôi `golden/`) + **vài case mẫu** trên corpus
  mới để chứng minh khung chạy; ghi rõ "đủ 30 case = D16". Giữ nguyên `smoke-5/10.yaml` (§0c).

### D12-4 · Embeddings fixture — quyết re-record hay hoãn (đừng để lộ 17:00)
`golden/embeddings-callisto-v0.json` chỉ phủ **5 doc cũ**. D13 (#90) DoD đòi "fixtures deterministic".
Chốt **ngay trong D12** một trong hai, ghi decision-log:
- **(a) Re-record** corpus mới qua `scripts/record_embeddings.py` → embeddings fixture phủ đủ 40–60 doc,
  D13 dùng liền; hoặc
- **(b) Hoãn có chủ đích sang D13** (D13 là ngày dựng pipeline embed thật) → ghi rõ "embeddings mới record
  ở D13 cùng ingest", **không** để fixture nửa vời. Mặc định nghiêng (b) vì embed là việc lõi D13; nhưng
  nếu D14 (#95) cần vector cho expected-chunks trước → cân (a). **Hỏi AIE-1 (#86)** đầu giờ (Q-B).

### D12-5 · decision-log — ghi (ô DoD 4, "nếu tụt nấc")
Ghi vào `docs/decisions/decision-log.md` (đã tồn tại): quyết vocab (Q-A: giữ-4 hay mở), phương án sinh doc
(template+tay, commit tĩnh), embeddings (re-record vs hoãn D13), corpus additive-only. Format tối thiểu:
`ID · ngày · quyết · lý do · người ký`.

### D12-6 · Daily-note D12 — viết trong ngày (kỷ luật ngược backfill)
Mạch: bối cảnh khởi-động-doc-factory → corpus mở bao nhiêu doc/vai + giữ bất biến gì → annotation skeleton
nuôi D13/D16/D14 → câu chặn (Q-A vocab) + cách giải → 4 ô DoD (phần DE). Ghi **hôm nay** để liền mạch.

---

## 3. Phụ thuộc & câu hỏi chặn — ai chặn DE, DE chặn ai

**Câu CHẶN (phải trả lời đầu giờ):**

| # | Hỏi ai | Câu hỏi | Vì sao chặn |
|---|---|---|---|
| **Q-A** ⭐ | **SWE (#87) + team** | Từ vựng `section_role`: **giữ 4 vai** hay **mở** (`legal/it/…`)? recipe/graph-lint của SWE có ràng/hardcode tập vai không? | Quyết trước khi viết doc; mở vocab = sửa `SECTION_VOCAB` + schema §3 + đụng fence/golden/leak (D12-1) |
| **Q-B** | **AIE-1 (#86)** | D14 cần vector cho expected-chunks **trước D13** không → embeddings re-record ở D12 (a) hay hoãn D13 (b)? | Quyết D12-4; tránh lộ thiếu fixture ở 17:00 |
| **Q-C** | **AIE-2 (#88)** | Golden-set/annotation: ngoài `expected_citation` (so bằng `chunk_id`), scorecard skeleton đọc field nào? | Khoá **định dạng annotation** (D12-3) để D16 không phải làm lại |

**Ai đang CHẶN DE (blocked-by):**
- **SWE** — Q-A: chưa chốt vocab thì viết 40–60 doc là đánh bạc (có thể phải sửa hàng loạt frontmatter).
- (nhẹ) **AIE-1/AIE-2** — Q-B/Q-C: chỉ chặn phần embeddings + định dạng annotation, không chặn viết corpus.

**DE đang CHẶN ai (blocking):**
- **AIE-1 (#90, D13)** — **nặng nhất**: KB pipeline D13 `ingest→chunk→embed→index` **ăn corpus + chunk_id**
  của doc-factory D12. Corpus/annotation D12 không ổn định thì D13 không có gì để ingest.
- **AIE-1 (#95, D14)** — expected-chunks (đo chunking×embedding) đến **từ annotation D12**.
- **AIE-2 (#105, D16)** — golden-set 30 case lấy nhãn **từ doc-factory** qua khung annotation D12.
- **SWE (#87)** — `kb_binding.scope` trong recipe phải trỏ đúng `{tenant, section}` mà corpus D12 phát ra
  (nếu corpus đẻ vai mới mà chưa chốt Q-A → recipe trỏ trượt).

**Đóng băng KÈM ghi (không chặn, nhưng vào decision-log):**
1. **Corpus additive-only** — 5 doc gốc + `smoke-5/10.yaml` + `embeddings-v0.json` bất khả xâm phạm (§0c).
2. **slug→UUID (Q-G)** — đã đóng theo D-13 (middleware resolve, ngoài lằn kb); `resolve_tenant_id` vẫn là
   fixture S1, xoá khi composition-root truyền UUID xuống ingest (D13+).
3. **`KbPipeline` giữ `NotImplementedError`** — việc D13, **không** đụng ở D12.

---

## 4. Lịch

| Mốc | Việc | ⬜ |
|---|---|---|
| **Đầu giờ — trước hết** | **D12-1** hỏi Q-A (SWE/team, vocab section_role) · gửi Q-B (AIE-1) · Q-C (AIE-2) | ⬜ |
| Sáng | **D12-2** viết corpus handbook (additive, 2 tenant, phủ 4 vai, giữ override) → chạy `doc_factory` xác nhận chunk_id | ⬜ |
| Trưa | **D12-3** khung ground-truth annotation + vài case mẫu (nhãn trích từ doc-factory) | ⬜ |
| Chiều | **D12-4** chốt embeddings (re-record/hoãn) · mở rộng `test_doc_factory.py` happy+negative (40–60 doc) | ⬜ |
| Cuối ngày | **D12-5** decision-log · **D12-6** daily-note D12 · self-check pytest xanh | ⬜ |

---

## 5. DoD #85 — phần DE (map lên 4 ô kế thừa từ #89 + việc DE-riêng)

- [ ] **Canvas/Mermaid sinh recipe đúng schema** — SWE chủ công (#87). **Phần DE:** seam — `kb_binding.scope`
      trong recipe phải trỏ `{tenant, section}` **corpus D12 thật sự phát ra**. Nếu vocab đổi (Q-A) mà không
      báo SWE → recipe trỏ trượt câm. 1 câu coordinate, không DE-gated.
- [ ] **graph-lint fail-closed** — coordinate only; `node_type` enum đã FROZEN D11 (day11_plan §5). Không DE-gated.
- [ ] **pytest happy+negative xanh** — **DE trực tiếp:** mở rộng `test_doc_factory.py` phủ corpus 40–60 doc;
      **negative**: frontmatter hỏng / `section_role` lạ / `tenant` lạ → **raise** (không im lặng). Chạy
      `.venv/bin/python -m pytest` (3.14), **không** sửa test để pass.
- [ ] **decision-log ghi (nếu tụt nấc)** — **D12-5**: vocab Q-A, phương án sinh doc, embeddings, additive-only.
- [ ] **[DE-riêng] Corpus ~40–60 doc / 2 tenant** — D12-2, additive, chunk_id ổn định & duy nhất.
- [ ] **[DE-riêng] Ground-truth annotation skeleton** — D12-3, khung + case mẫu, nhãn trích từ doc-factory.
- [ ] **[DE-riêng] Daily-note D12** — D12-6, viết trong ngày.

**Rủi ro lớn nhất:** (1) **Q-A không chốt** → viết doc với vai mới rồi phải sửa hàng loạt / `doc_factory`
raise; (2) **lỡ tay re-cut 5 doc gốc** → `smoke-5/10.yaml` zero câm (không test nào đỏ); (3) **gõ tay
`chunk_id`** vào annotation thay vì trích từ máy cắt → golden-set lệch, 0 điểm không lỗi nổi; (4) embeddings
fixture bỏ lửng → lộ ở D13. Khối lượng nặng **content + annotation kỷ luật**, nhẹ code — giá trị nằm ở
corpus D13/D16 **dùng lại được ngay** và chunk_id **không bao giờ drift**.
