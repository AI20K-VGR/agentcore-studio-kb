# Plan D11 (DE) — Contract-freeze: đóng băng trace-event + kb.search + design-note + 4/4 chữ ký

> **Ngày:** 2026-08-03 (D11, Thứ Hai · Chặng 2 / Sprint 2 · Tuần 3) · **Bút:** DE (Nguyễn Đông Anh)
> **Anchor:** issue kit **#80** (con của **#84** "Đàm phán & đóng băng 4 hợp đồng"). Anh em: SWE **#82**
> (recipe schema) · AIE-1 **#81** (tiêu thụ EmbeddingService Protocol) · AIE-2 **#83** (scorecard).
> **Repo WRITE: `agentcore-studio-kb`** · kit READ. **Milestone:** Sprint 2 — Gate Day 20.
>
> Việc DE (#80): *"**Bút trace-event** (`run_id·tenant NOT NULL·node_type∈6·tokens·cost·citations`)
> + **`kb.search`** (`kb.search(query, tenant, section_roles, top_k)`). Design-note: doc-factory +
> chunk/embed/index per-tenant + fence-tại-retrieval."* **DoD #80 (4 ô):** 4/4 contract commit + freeze ·
> 4/4 design-note approved · decision-log ghi · 4/4 chữ ký.
>
> Luật freeze (không phải tuỳ chọn): umbrella §3 `:92-93` *"integration CHỈ qua 4 contract; freeze cuối
> S1 (workshop D11 → freeze); đổi = **mini-RFC + 4/4 chữ ký + decision-log**"* · **D-12** · **INV-5** ·
> umbrella `:17` *"writer role-track **chi tiết hoá** field, KHÔNG đổi tên/nghĩa khoá đã freeze"*.

---

## 0. Hôm nay freeze là chốt NGHĨA, không phải viết feature — và lằn WRITE của DE có thể không với tới nơi chứa bản freeze

Hai điều đọc cho đúng trước khi bắt tay:

**(a) "Freeze" = khoá tên + nghĩa khoá, không phải viết thêm code.** Cả hai contract DE cầm đã ở trạng
thái `freeze: NOT-FROZEN / freeze_target: D11`. Bản kb là **role-track chi tiết hoá** (umbrella `:17`);
tên + nghĩa khoá thật đã sống ở `agentcore-studio-contracts` (`studio_contracts.trace.TraceEvent`,
`studio_contracts.kb.KbSearch`) và **đã khớp** — delta §7 (trace) / §8 (kb.search) ghi rõ *"v0 chỉ
THIẾU, không MÂU THUẪN"*. Nên việc hôm nay **không** phải điền thân hàm mới; là **chốt câu chữ đang đọc
được hai kiểu**, đóng/hoãn-có-chủ-đích các câu hỏi mở, lấy 4 chữ ký, ghi decision-log.

**(b) DE chỉ WRITE `kb` — bản freeze "thật" nằm ở repo của mentor.** GITFLOWS §5 + D-12:
CODEOWNERS của `agentcore-studio-contracts` = **mentor** (seam chung); rename/required-add = **bump
`SCHEMA_VERSION` + mini-RFC 4 chữ ký**. Vậy **câu chặn số một** của ngày: *"contract commit + freeze"
cho DE nghĩa là (1) lật `freeze: FROZEN` trên 2 file draft trong `kb/docs/contracts/` + ký + ghi
decision-log, HAY (2) còn cần PR bump `SCHEMA_VERSION` vào repo `contracts` mà DE **không** WRITE?"* —
xem **Q-1**, phải hỏi mentor/leader **đầu giờ**, đúng cách D10-7 xử con-trỏ. Nếu là (2): DoD "commit +
freeze" **không đóng được trong lằn DE hôm nay** nếu không có đường cross-repo — nêu thẳng, đừng để 17:00
mới lộ.

Lằn giữ nguyên: **không sửa test để pass**; **không đụng quadrant khác** (`apps/studio`, engine,
workbench, evalhub) — chỉ báo/coordinate; **không sửa `packages/contracts/**`** (repo mentor).

---

## 1. Trạng thái chốt trước (sáng 03/08)

| Mục | Trạng thái |
|---|---|
| `trace-event.v0.md` | `NOT-FROZEN`, `freeze_target: D11`. 9 field lõi khớp `contracts`; 3 field hoãn (`inputs_hash`/`outputs`/`citations`) **có trong schema, chưa điền** (§3). Mở: **Q-A** (bút v0 = draft kb hay delta lên contracts?), **Q-C** (AIE-2 còn đọc field nào?), **Q-D** (`obs.costs`/`obs.golden_sets` là bảng rỗng ở `apps/studio` — ngoài lằn DE) |
| `kb-search.v0.md` | `NOT-FROZEN`, `freeze_target: D11`. Chữ ký **đã 4 tham số** (`query, tenant_id: UUID, section_roles, top_k`) trùng bản freeze từ D3/D5 (D-13). Nâng freeze = **chỉ siết HÀNH VI** (§4), không đổi chữ ký. Mở: **Q-B** (draft vs PR), **Q-D** (AIE-1 tự dựng stub vs DE ship `StubKbSearch`), **Q-G** (đường slug→UUID thật) |
| `ts` monotonic (điểm D10-5 lo) | **Đã chốt** ở §4.2a: ties hợp lệ, sắp ổn định, `ORDER BY ts, event_id`, `ts` là cột `TEXT` → parse rồi mới sắp, **không** assert tăng-nghiêm-ngặt. Reader-test (`test_trace_reader.py`) **đã khớp** đúng câu này (`test_ts_trung_nhau...`, `test_ts_sai_dinh_dang...`). → hôm nay là **freeze nguyên văn §4.2a**, không mở lại |
| Bản freeze end-S1 (4 contract) | chưa file nào `FROZEN`; workshop #84 hôm nay mới chạy |
| decision-log | **chưa có file** trong repo — DoD "decision-log ghi" đòi tạo/định vị (xem Q-2) |

---

## 2. Việc DE hôm nay — chốt nghĩa, ký, ghi

### D11-1 · CHẶN ⭐ — chốt **nơi + cơ chế** freeze với mentor/leader (đầu giờ, trước mọi thứ)
Đây là tiền đề của cả 4 ô DoD, không riêng DE. Cần 3 câu trả lời (xem §3 Q-1/Q-2):
1. Bản `FROZEN` **nằm ở đâu** — file draft `kb/docs/contracts/*.v0.md` lật cờ, hay PR bump
   `SCHEMA_VERSION` ở `contracts` (mentor CODEOWNERS)? Nếu là contracts → DE cần đường merge cross-repo.
2. **decision-log ghi ở đâu** (chưa có file) — kit? contracts? một `kb/docs/decisions/`?
3. "4/4 chữ ký" **hình thức gì** — approve PR, comment ký tên ở #84, hay bảng ký trong file contract?

Không chốt được 3 câu này thì "commit + freeze" là ô **mở** — báo leader ngay, đừng ôm.

### D11-2 · trace-event → FREEZE (nâng `v0` → `FROZEN`, chốt câu chữ)
Bản kb đã khớp `contracts` về tên/nghĩa; freeze = **chốt các invariant đang đọc-hai-kiểu + đóng/hoãn câu
mở**, rồi lật cờ + thêm bảng chữ ký + §Lịch-sử `v1.0 FROZEN`:
- **§4.2a `ts`** — freeze **nguyên văn**: ties hợp lệ, sắp ổn định `(ts, event_id)`, `ts` là `TEXT` →
  parse rồi sắp, raise khi hỏng, **không** tăng-nghiêm-ngặt. (Reader-test đã khớp; nếu chạm test
  spine/writer bên `apps/studio` giả định ngược → **coordinate**, không tự sửa.)
- **§4.1 cost — MỘT nguồn** (chốt với AIE-1, xem Q-3): mặc định DE = **sink tính từ `tokens` + bảng
  đơn giá**, executor chỉ cấp `tokens`. Freeze câu "ai tính `cost`" — cấm hai chỗ tính (kể cả ra đúng
  số).
- **§5 `node_type`** — enum đóng 6 giá trị, **nguồn duy nhất** `studio_contracts.nodes.NodeType`, cấm
  khai lại phía kb. **Phải trùng tập node SWE validate trong `recipe.dag`** (Q-4). Chốt luôn: chuỗi
  kỳ-vọng-walk hiện là **4** (`_WALK_ORDER`), không phải 6 — freeze bằng chữ để reader không báo thiếu oan.
- **§7 carrier** — `inputs_hash` (không có DB default) + `outputs` **AIE-1 bắt buộc truyền** từ tuần 1;
  đây là **thông báo ràng buộc bảng đã tồn tại**, không phải điều đàm phán — xác nhận với AIE-1 khi ký.
- **Đóng/hoãn câu mở:** Q-A→ theo D11-1; Q-C→ hỏi AIE-2 chốt danh sách field eval đọc (xem Q-5); **Q-D
  (`obs.costs`/`obs.golden_sets`)** → **ghi hoãn có chủ đích**: bảng ở `apps/studio`, **ngoài fence-lane
  DE**; ai điền/bằng cách nào = coordinate leader, **không chặn freeze schema** hôm nay.

### D11-3 · kb.search → FREEZE (chữ ký đã khoá, freeze HÀNH VI + hoãn có ghi)
Chữ ký 4 tham số + `tenant_id: UUID` đã trùng `contracts` từ D3/D5 (D-13) — freeze = khoá **hành vi** §4/§5:
- **Lọc TẠI RETRIEVAL, fail-closed** (§5.1); **`section_roles` do SERVER quyết** (§5.2, client gửi là
  *yêu cầu* không phải *quyền*); **cấm trả hết nhờ LLM lọc** (§5.3). Ba câu này là AC S2/S3 — freeze bằng
  chữ để không ai "làm sớm/làm sai" rồi đập.
- **`chunk_id` ổn định** cho citation-accuracy của AIE-2 — freeze rằng `chunk_id` bền (prefix slug +
  `#cN`), vì scorecard so khớp citation **bằng `chunk_id`** (Q-5).
- **Hoãn có ghi:** **Q-D** (stub) → mặc định AIE-1 tự dựng; nếu cần chung đặt `src/studio_kb/stubs.py`
  class riêng, **không đụng** `KbSearchService` — chốt với AIE-1 (Q-3). **Q-G** (slug→UUID thật) →
  **D-13 đã trả**: producer/middleware resolve header slug→UUID qua `core.tenants`; kb khoá theo UUID.
  Ghi decision-log "Q-G đóng theo D-13, đường resolve = middleware, ngoài lằn kb" — **không chặn freeze**.

### D11-4 · Design-note DE ≤2 trang — tự viết, mentor duyệt (ô DoD 2)
Nội dung theo #80: **doc-factory + chunk/embed/index per-tenant + fence-tại-retrieval**. Không phải
tóm tắt contract — là **thiết kế + đánh đổi**: (1) doc-factory sinh KB per-tenant thế nào (frontmatter
tenant/section, tiền lệ D4 stub 5 doc → hướng S2); (2) chunk/embed/index **per-tenant** — vì sao tách
theo tenant ở tầng index chứ không lọc sau; (3) **fence-tại-retrieval là LUẬT** — loại **trước** ranking,
fail-closed, vì "đừng tiết lộ" là chỉ dẫn mềm, dữ liệu sai tenant/vai vào context là rò qua
suy-luận/citation/tool-output. Nêu **1 phương án đã bỏ** (vd: fence sau ranking / lọc ở LLM) và vì sao.

### D11-5 · decision-log — ghi (ô DoD 3)
Sau khi D11-1 chốt nơi ghi: mỗi quyết chốt hôm nay 1 dòng — cost-single-source, `ts`-không-nghiêm-ngặt,
`node_type` 6-enum/4-walk, Q-G đóng theo D-13, Q-D(costs) hoãn cross-lane. Format tối thiểu:
`ID · ngày · quyết · lý do · người ký`.

### D11-6 · Ceremony 4/4 chữ ký (ô DoD 4)
Workshop #84: mỗi contract cần 4 chữ ký (DE·SWE·AIE-1·AIE-2). DE **ký 4 bản** (recipe/trace/kb.search/
scorecard) sau khi đọc; **đòi 3 người kia ký 2 bản DE cầm**. Đừng ký khống — đọc delta trước khi ký.

### D11-7 · Daily-note D11 — viết trong ngày (kỷ luật ngược backfill)
Mạch: bối cảnh freeze-day → 2 contract DE chốt gì (đối chiếu §/issue) → design-note → câu chặn + cách
giải → 4 ô DoD. Ghi **hôm nay** để liền mạch.

---

## 3. Phụ thuộc & câu hỏi chặn — ai chặn DE, DE chặn ai

**Câu CHẶN chữ ký (phải trả lời trước khi ký được):**

| # | Hỏi ai | Câu hỏi | Vì sao chặn |
|---|---|---|---|
| **Q-1** | **mentor / leader** | Bản `FROZEN` nằm ở draft kb (lật cờ) hay PR bump `SCHEMA_VERSION` ở `contracts` (DE không WRITE)? | Quyết "commit + freeze" đóng được trong lằn DE hay cần cross-repo (D11-1) |
| **Q-2** | **mentor / leader** | decision-log ghi ở file/repo nào (chưa tồn tại)? + hình thức "4 chữ ký"? | DoD ô 3 & 4 không có địa chỉ để đóng |
| **Q-3** | **AIE-1 (#81)** | Ai tính `cost` — sink-từ-`tokens` (mặc định DE) hay executor cấp? + xác nhận truyền `inputs_hash`+`outputs` từ tuần 1 | §4.1 cấm tính hai chỗ; freeze cần chốt **một** nguồn |
| **Q-4** | **SWE (#82)** | Tập `node_type` trong `recipe.dag{nodes,edges}` = đúng 6 enum `studio_contracts.nodes.NodeType`? | node_type lệch giữa recipe ↔ trace = vỡ seam; cùng import một enum |
| **Q-5** | **AIE-2 (#83)** | Ngoài `cost`+`citations`, scorecard đọc field nào từ trace? + citation-accuracy so bằng `chunk_id` → cần `expected_citation` trong golden-set? | Đóng Q-C(trace)+Q-C(kb.search); DE khoá `chunk_id` bền cho AIE-2 |

**Ai đang CHẶN DE (blocked-by):**
- **mentor** — Q-1/Q-2: **chặn cứng nhất**. Không biết freeze đổ vào đâu + ký/ghi kiểu gì thì 3/4 ô DoD
  treo, dù nội dung schema đã sẵn.
- **AIE-1** — Q-3: chưa chốt "ai tính cost" thì §4.1 của trace-event chưa freeze sạch.
- **SWE** — Q-4: `node_type` enum của DE phải trùng tập node recipe của SWE.
- **AIE-2** — Q-5: cần biết eval đọc field nào để đóng Q-C trước khi ký trace-event.

**DE đang CHẶN ai (blocking) — DE chặn AIE-2 nặng nhất:**
- **AIE-2 (#83)** — **nặng nhất**: `citation_accuracy` + `cost` của scorecard **đọc từ trace-event của
  DE**; `citation_accuracy` so bằng `chunk_id` của `kb.search` (DE). Scorecard **không freeze trước**
  trace-event + `chunk_id` được → DE phải chốt hình dạng `citations`/`chunk_id` để AIE-2 ký.
- **AIE-1 (#81)** — node-executor emit đúng 1 trace-event/node (§6) + lấy `citations` từ `kb.search`
  (DE); "tiêu thụ EmbeddingService" đổ `tokens` vào trace của DE. AIE-1 chốt tiêu thụ **sau khi** hình
  dạng trace + quyết-định-stub (Q-D) của DE rõ.
- **SWE (#82)** — recipe có `kb_binding` trỏ tới `kb.search` (chữ ký + `tenant_id` UUID + `section_roles`
  của DE) và `dag` phải dùng đúng enum `node_type` của DE.

**Cần thống nhất cả team — tách "chặn-ký" vs "hoãn-có-ghi":**

*Phải chốt trước khi ký (gating):*
1. **Nơi + cơ chế freeze** (Q-1/Q-2) — gate cả **4** contract, không riêng DE.
2. **cost một-nguồn** (Q-3, DE↔AIE-1) — sink-từ-tokens vs executor.
3. **`node_type` 6-enum một-nguồn** (Q-4, DE↔SWE) — trace ↔ recipe cùng `studio_contracts.nodes`.
4. **hình dạng `citations`/`chunk_id`** (Q-5, DE↔AIE-2) — downstream của scorecard.

*Đóng băng KÈM ghi hoãn (không chặn ký, nhưng phải vào decision-log):*
5. **`inputs_hash`/`outputs` bắt buộc-kèm-placeholder** — ràng buộc bảng đã có (§7), là **thông báo**,
   không đàm phán.
6. **stub `kb.search`** (Q-D) — mặc định AIE-1 tự dựng; bản chung `stubs.py` class riêng nếu cần.
7. **slug→UUID** (Q-G) — **đóng theo D-13** (middleware resolve, ngoài lằn kb).
8. **`obs.costs`/`obs.golden_sets`** (trace Q-D) — bảng ở `apps/studio`, **ngoài fence-lane DE**;
   ai/điền-sao = coordinate leader.
9. **fence chỉ ở tầng retrieval KB** + **INV-1 mới chặn `tenant`, chưa chặn `roles`** — ghi là điểm S2
   đã biết, không chặn freeze S1.

---

## 4. Lịch

| Mốc | Việc | ⬜ |
|---|---|---|
| **Đầu giờ — trước hết** | **D11-1** hỏi mentor/leader Q-1/Q-2 (nơi freeze · decision-log · hình thức ký) | ⬜ |
| Đầu giờ | Gửi Q-3 (AIE-1) · Q-4 (SWE) · Q-5 (AIE-2) — 3 câu chặn-ký | ⬜ |
| Sáng | **D11-2** trace-event: chốt §4.2a/§4.1/§5/§7 + đóng-hoãn câu mở → lật `FROZEN` | ⬜ |
| Sáng | **D11-3** kb.search: freeze hành vi §4/§5 + `chunk_id` bền + hoãn Q-D/Q-G có ghi → lật `FROZEN` | ⬜ |
| Trưa | **D11-4** viết design-note ≤2 trang (doc-factory · per-tenant index · fence-tại-retrieval) | ⬜ |
| Chiều | **workshop #84**: đàm phán → **D11-6** ký 4/4 · **D11-5** ghi decision-log | ⬜ |
| Cuối ngày | mentor duyệt design-note · **D11-7** daily-note D11 | ⬜ |

---

## 5. DoD #80 — phần DE

- [ ] **4/4 contract commit + freeze** — D11-2 (trace-event) + D11-3 (kb.search) lật `FROZEN`; **điều
      kiện: Q-1 chốt nơi freeze**. Nếu freeze đổ vào repo `contracts` (mentor) → nêu chặn cross-repo, không tự đóng.
- [ ] **4/4 design-note approved** — D11-4 (DE tự viết) + mentor duyệt. DE ký/đọc 3 note còn lại.
- [ ] **decision-log ghi** — D11-5, sau khi Q-2 chốt địa chỉ; ghi cost-single-source, ts-không-nghiêm-ngặt,
      node_type 6-enum/4-walk, Q-G đóng theo D-13, Q-D(costs) hoãn cross-lane.
- [ ] **4/4 chữ ký** — D11-6, ký sau khi đọc delta; đòi đủ 4 chữ ký trên 2 bản DE cầm.
- [ ] **Daily-note D11** — D11-7, viết trong ngày.

**Rủi ro lớn nhất:** (1) **Q-1 không chốt** → "freeze" thành nghi thức treo, hoặc DE bị kẹt ngoài repo
`contracts`; (2) ký khống trước khi chốt cost-source/node_type/citations → freeze vỡ ở Gate Day 20;
(3) decision-log không có địa chỉ → ô DoD 3 mở âm thầm. Khối lượng không nặng code — nặng **đàm phán +
chốt nghĩa**; giá trị nằm ở câu chữ không đọc-hai-kiểu.
