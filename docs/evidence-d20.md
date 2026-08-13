# Bằng chứng D20 — phần DE (kb) · GATE-2 + plan-vs-actual

> **Mục đích:** phần DE trong evidence-pack GATE-2 (issue **#125**, con của gate **#129**). Chuẩn *"đủ để
> chấm không cần hỏi"* — mọi con số §2 **tái lập được** bằng khối lệnh §1, không tin lời khai. §3 là
> **plan-vs-actual** đối chiếu [design-note D11](design-notes/de-day11.md) §6 (DoD #129). §4 còn **1 điểm
> treo** (cost-lineage — chờ AIE-1 **#121**) — nêu thẳng, không giấu. T6-integration đã **đóng thật, và
> kb tự chứng minh trong kho của mình** (xem §4.1).
>
> **Bối cảnh trung thực:** báo cáo gốc chạy **12/08 (D18)** như một **gate dry-run** — sớm 2 ngày so với D20
> (14/08). **Sửa sau review AIE-2 (kb#25, F1 — blocker):** bản gốc khai sai trạng thái con trỏ
> `packages/engine` — **#111 đã land từ 11/08** (kit#113, `a4e59ed`), một ngày TRƯỚC dry-run, không phải
> "chưa land" như bản gốc ghi. `kb#26` sau đó retire xfail T6 nhưng **dựa vào bằng chứng của repo engine**;
> rà lại thấy đó là lỗ trong evidence-pack (kb đi mượn bằng chứng cho một dòng DoD của chính mình), nên
> kb nay có **bài integration của riêng nó** chạy `interpreter.run()` thật — §4.1. Riêng **D19 cost-lineage**
> (kb#22) và **mini-RFC amendment D18** (kb#24) đúng là chưa land lúc dry-run — cả hai đã **merge 13/08**
> (sau dry-run, trước gate 14/08); bản này cập nhật theo trạng thái mới nhất tính tới 13/08.

---

## 1. Chạy lại — khối lệnh dán-là-chạy

Từ **thư mục gốc của kit** (`agentcore-studio-kit/`):

```bash
docker compose -f docker-compose.test.yml up -d --wait

export STUDIO_DATABASE_URL_ADMIN=postgresql://studio_owner:changeme@localhost:5433/studio_test
export STUDIO_DATABASE_URL=postgresql://studio_app:changeme@localhost:5433/studio_test

uv run --python 3.14 pytest packages/kb -q                       # 239 passed, 0 xfailed, 0 skipped
uv run --python 3.14 python packages/kb/scripts/ingest_callisto.py   # ankor 71 · borea 69 · 140 chunk / 2 tenant
```

⚠️ **Hai dòng `export` là bắt buộc** (bài học O3.2): thiếu → test tầng DB **skip lặng lẽ**, `skip ≠ pass`,
và người đọc kết luận số 239 khai láo. Interpreter **pin 3.14** (`uv run --python 3.14`), không `python3`
trần (bẫy 3.11 → SyntaxError giả PEP 695/701/758).

---

## 2. Số đo — DoD #125 từng item

| Item #125 | Bằng chứng (test / lệnh) | Kết |
|---|---|---|
| **KB thật ingest→embed→index per-tenant** | `ingest_callisto.py`: **140 chunk / 2 tenant** (ankor 71 · borea 69), clone-tươi 1 lệnh · `test_pg_kb::test_ingest_idempotent_chay_lai_khong_nhan_doi` + `test_ingest_hai_tenant_moi_ben_chi_thay_phan_minh` | ✅ |
| **`kb.search` cited** (§3.3 shape) | `test_spine_live::test_citations_are_grounded` + `test_trace_la_nguon_citation_dung_duoc_cho_bo_cham` (chunk-id có thật kho Callisto) | ✅ |
| **tenant filter + T1 IDOR xanh** | `test_leak::test_t1_idor` **PASSED** (gỡ xfail D17, RLS + `WHERE tenant_id`) + `test_pg_kb::test_t1_khong_ro_ri_cheo_tenant` | ✅ |
| **T6 label-spoof** | **kb-mức-đầu:** `test_pg_kb::test_t6_khong_ro_ri_cheo_vai` + `test_no_bypass` (5/5) **PASSED** · **integration TRONG KB:** `test_spine_live::test_t6_recipe_khai_section_roles_rong_hon_thi_phien_thang` **PASSED** — recipe khai `scope="ankor/finance"`, phiên `roles=["public"]`, chạy `interpreter.run()` thật trên kho Callisto thật; assert **cả** giá trị thực vào `kb.search` (`["public"]`) **lẫn** trace đọc lại từ Postgres (0 chunk finance) · engine-lane có bài độc lập riêng (`test_section_roles_server_resolve.py`, #111) | ✅ đóng thật — **kb tự chứng minh, không mượn bằng chứng repo khác** |
| **trace viewer** | `test_trace_reader::test_render_timeline_*` (4 test: tokens · monotonic · tự-sắp-xếp · đủ/thiếu node) **PASSED** | ✅ |
| **cost-lineage cùng-1-số** (§3.2) | kb#22 (D19, merge 13/08) land cỗ máy cộng dồn (`aggregate_run_cost`/`cost_of`/`PgCostReader` + cost-table CLI), đọc on-read từ `obs.trace_events` — nhưng `interpreter.py:438` (con trỏ engine hiện tại) vẫn `cost=_NO_COST` (0.0): chưa wire `cost_of` tại emit (chờ AIE-1 **#121**, còn mở) | ⏳ (xem §4.2) |
| **golden-set 30** | `callisto-golden-30-v1.yaml`: **30 case · 10 `manual_label`** (D16 + nhãn tay D18) · `test_golden_set` **PASSED** | ✅ |
| **spine 4 bước chạy thật** (DoD #129) | `test_spine_live` **11/11 PASSED** (emit→sink→reader; INV-1 recipe-spoof-tenant→session thắng; **T6 recipe-spoof-roles→session thắng**; refusal-from-grounding) | ✅ |

**Tổng suite kb:** `239 passed, 0 xfailed, 0 skipped` — 225 passed cũ (D18) + 13 test mới trong
`test_cost.py` (kb#22, D19) + 1 bài T6 integration mới trong `test_spine_live.py` (§4.1). Xfail T6 duy
nhất trước đó (`test_t6_label_spoof`) không chuyển thành passed — hàm test đó bị **xoá hẳn** khi retire
(kb#26): kb-side placeholder gọi thẳng `KbSearchService` nên không bao giờ chứng minh được override ở
tầng interpreter; bài thay thế nó chạy `interpreter.run()` thật.

---

## 3. Plan-vs-actual — đối chiếu design-note D11 §6 "Điểm S2 đã biết"

Design-note D11 (03/08) **nêu trước 4 điểm** sẽ lộ ở S2. D20 đối chiếu từng điểm — cả chỗ **khớp** lẫn chỗ
**còn treo**:

| # | Dự đoán D11 (§6) | Actual D20 | Kết |
|---|---|---|---|
| 1 | *"Fence mới ở tầng retrieval của KB stub… cần một điểm chặn dùng chung, không rải rác."* | D17 lật `KbSearchService`→`PgKbSearch`: fence tại retrieval **một seam** chính thức, fail-closed (§3.3). `test_no_bypass` chứng minh 1 chỗ chặn. | ✅ **đúng hướng, đã làm** |
| 2 | *"INV-1 mới chặn `tenant`, chưa chặn `roles`… `section_roles` nhận-rồi-bỏ."* | **kb-lane đã chặn roles** tại `PgKbSearch` (`test_t6_khong_ro_ri_cheo_vai` + no-bypass PASSED). **Sửa sau review kb#25 F1:** #111 **đã land** 11/08 (kit#113, một ngày TRƯỚC dry-run) — con trỏ `packages/engine` hiện ở `62773ba` (D17), và `interpreter.py:324-325` inject **cả** `tenant_id` **lẫn** `section_roles` từ `session_context.roles` vào `node.params`. Bài test tích hợp ở tầng interpreter nay có **trong chính kb** (`test_spine_live::test_t6_recipe_khai_section_roles_rong_hon_thi_phien_thang`) — T6 **đóng thật**, không còn "nhận-rồi-bỏ" (§4.1). | ✅ **đóng thật — kb có bài integration của riêng mình** |
| 3 | *"`obs.costs` ngoài fence-lane DE — DE điền ở D19 (cost-lineage)."* | **Sửa sau review kb#25 F2:** D19 (kb#22, merge 13/08) **KHÔNG build `obs.costs`** — cost-lineage đọc **on-read** từ `obs.trace_events` (một-nơi-tính, §4.1 mini-RFC); dựng bảng tổng hợp riêng sẽ là nơi tính thứ hai. Lỗ per-tenant thật vẫn nằm ở `obs.trace_events` (cột `cost`+`tenant_id`, chưa RLS) = **hạng mục B** trong mini-RFC (kb#24), không phải `obs.costs`. mini-RFC amendment D18 (kb#24, **APPROVED** 13/08) chốt `obs.costs`→**CẦN RLS *nếu/khi được build*** — chưa build hôm nay. | ⏳ **dự đoán đúng hướng — RLS vẫn treo, nhưng ở `obs.trace_events`, không phải `obs.costs`** |
| 4 | *"`obs.golden_sets` nghi bảng-chết trùng `eval.golden_sets` → đề xuất DROP (mini-RFC)."* | mini-RFC amendment D18 (kb#24, **APPROVED** 13/08) **giữ đề xuất DROP** `obs.golden_sets` (0 runtime reader); nguồn sự thật = `eval.golden_sets`. **Chưa DROP thật** (chờ xác nhận AIE-1, gate thay mentor). **Sửa sau review kb#25 F2:** `eval.*` không còn "chờ phê" — AIE-2 đã **chốt trực tiếp ở review kb#24**: `eval.golden_sets`→**KHÔNG CẦN** (đề dùng chung, ref-keyed) · `eval.scorecards`→**CẦN RLS** (`results` lưu answer-text per-tenant, `evalhub:harness.py:530`+`:540`). | 🔵 **đúng nghi vấn — DROP còn treo (AIE-1); nhánh `eval.*` đã chốt, không còn mở** |

**Chỗ lệch dự đoán (trung thực):** không có mục nào D11 hứa mà D20 làm thiếu; ngược lại D20 **làm dày hơn**
dự đoán ở điểm 2 (đã chặn roles ở kb-lane **và** đóng thật integration, không chỉ "nhận-rồi-bỏ" như D11
mô tả). **Sửa sau review kb#25:** điểm 2 (T6) đã **đóng hẳn**, không còn treo. Điểm treo thật sự chỉ còn
điểm 3 (cost số thật, chờ #121 AIE-1) và phần DROP của điểm 4 (chờ AIE-1 xác nhận) — cả hai cross-lane.

---

## 4. Một điểm còn treo đã biết — honest-TODO (không giấu, không fake-green)

### 4.1 T6 integration-close — ĐÃ ĐÓNG, và kb tự chứng minh (không mượn bằng chứng repo khác)

> **Lịch sử sửa — hai vòng, và vòng hai mới là vòng đóng thật:**
>
> 1. **kb#25 (review AIE-2, F1 — blocker):** mục này ban đầu khai #111 "chưa land" và gán việc còn thiếu
>    sang lane AIE-1. Đính chính: #111 land 11/08, `interpreter.py:324-325` tại pointer `62773ba` đã
>    inject cả `tenant_id` lẫn `section_roles`.
> 2. **kb#26 retire xfail — nhưng dựa vào bằng chứng repo engine.** Rà lại thấy đó vẫn là lỗ: kb tuyên bố
>    T6 đóng mà bằng chứng nằm ở `packages/engine`. Đo được mức nghiêm trọng — gỡ hẳn dòng inject khỏi
>    interpreter thì **cả 238 test kb vẫn xanh**, tức kb có **0 coverage** cho chính bất biến nó đang
>    tuyên bố. Nay kb có bài của riêng mình (dưới), và mục này mới thật sự hết là honest-TODO.

- **Trạng thái cuối:** `test_leak.py::test_t6_label_spoof` (kb-side placeholder, luôn xfail by design vì
  gọi thẳng `KbSearchService` bỏ qua interpreter) đã **xoá hẳn** — không còn lý do tồn tại.
- **kb tự chứng minh T6 trong kho của mình** (bổ sung sau khi rà lại kb#26):
  `test_spine_live::test_t6_recipe_khai_section_roles_rong_hon_thi_phien_thang` — bài anh em của
  `test_inv1_recipe_tu_khai_tenant_khac_thi_phien_thang`, trục thứ hai (INV-1 tách *bạn là ai*, T6 tách
  *bạn đọc được mục nào*). Recipe khai `kb_binding.scope="ankor/finance"`, phiên server-resolve
  `roles=["public"]`, chạy chuỗi thật `resolve_session`(SWE) → `interpreter.run()`(AIE-1) →
  `kb.search`(DE) → Postgres → đọc lại. Ba cầu chì chống xanh-giả (đòn tấn công phải ăn được nếu không
  chặn · recipe phải thật sự khai finance · `kb.search` phải thật sự được gọi), rồi hai vế: **cơ chế**
  (`kb.search` nhận `["public"]`) và **hệ quả** (trace 0 chunk finance).
- **Vì sao phải viết dù engine đã có bài:** đo được — gỡ hẳn dòng inject `section_roles` khỏi
  `interpreter.py` (đúng trạng thái lỗ hổng trước #111) thì **cả 238 test kb cũ vẫn XANH**; chỉ bài mới
  đỏ. Trước bài này, evidence-pack kb phải mượn bằng chứng ở repo khác cho một dòng DoD của chính mình —
  người chấm chỉ đọc kb không kiểm lại được, trái chuẩn *"đủ để chấm không cần hỏi"*. Engine-lane
  `test_section_roles_server_resolve.py` (#111) vẫn giữ, hai lane hai bằng chứng độc lập.
- **Self-mutation đã chạy (xanh ≠ đúng):** M-1 *bỏ hẳn dòng inject* → đỏ ở vế cơ chế
  (`kb.search nhận ['finance']`); M-2 *đè bằng chính giá trị recipe khai* → đỏ; tạm vô hiệu vế cơ chế →
  vế hệ quả vẫn tự bắt được. Cả hai vế có răng độc lập.
- **`test_leak_meta.py` đã repoint:** anti-tamper không còn canh chuỗi assert của hàm đã xoá, mà canh các
  răng loại-trừ vai trò (`ankor-salary-001#c1` in / `ankor-budget-001#c1` not in / `section_role == "hr"`)
  trong `test_no_bypass.py` — vẫn chống ai đó âm thầm làm rỗng phép chứng minh no-bypass.

### 4.2 Cost-lineage cùng-1-số ⇐ D19 (#120) — landed 13/08, seam wire còn mở (#121)

> **Cập nhật (không phải khai sai — D19 hợp lệ "chưa land" lúc dry-run 12/08, đã merge sau đó):** kb#22
> merge 13/08. Cập nhật §2/§3/§5 theo trạng thái mới.

- **Đã có (kb#22):** `src/studio_kb/cost.py` — bảng đơn giá + `cost_of(tokens)` (dùng để KIỂM, không tính
  cost thật), `aggregate_run_cost` (cộng `event.cost` đã lưu, fail-closed khi trộn `run_id`/`tenant_id`),
  `PgCostReader`, cost-table CLI (`scripts/cost_table.py`). Đọc **on-read** từ `obs.trace_events`, không
  materialize `obs.costs` (§4.1 mini-RFC: một-nơi-tính).
- **Vẫn 0:** `interpreter.py:438` (con trỏ engine hiện tại) còn `cost=_NO_COST` (0.0) — `cost_of` chưa
  được wire tại điểm emit. Invariant §3.2 (`cost` UI-test == trace == cost-table) **vẫn chưa chứng minh
  được** bằng số thật — "khớp" hiện vẫn rỗng nghĩa (0.0 khắp nơi), chỉ khác là giờ có sẵn cỗ máy cộng dồn
  + lưới kiểm (`price_mismatches`) chờ số thật chảy vào.
- **Seam còn mở:** `cost_of` phải land ở `contracts` để interpreter import (Q-A, DE không sửa `contracts`
  — GITFLOWS §5, cần mentor/CODEOWNERS PR) rồi **AIE-1 (#121, còn mở)** wire lúc emit. Cho tới đó,
  cost-table CLI/trace-viewer đọc đúng nhưng ra toàn 0 — honest-TODO, không tô hồng.
- **Không WRITE apps/engine/contracts trong lane DE.**

---

## 5. Bàn giao / mốc retire

- **T6 integration-close: HOÀN TẤT.** #111 đã land (11/08); bài test tích hợp lane DE viết xong ở kb#26,
  đã gộp vào branch này (§4.1). `xfail` đã retire, `test_leak_meta.py` đã repoint. Không còn việc mở.
- **D19 (kb#22) đã land** (13/08) → cỗ máy cộng dồn cost sẵn sàng; còn chờ **#121 (AIE-1, mở)** wire
  `cost_of` tại emit + `cost_of` land ở `contracts` (Q-A) trước khi có số thật để đối chiếu UI-test.
- **mini-RFC schema-drift** (`docs/mini-rfc-tenant-schema-unify.md`, amendment D18 = **kb#24, APPROVED**
  13/08) → `eval.golden_sets` KHÔNG CẦN / `eval.scorecards` CẦN RLS đã chốt (AIE-2); `obs.costs` CẦN-RLS
  *nếu/khi build* (lane DE, chưa build — D19 đọc on-read từ `obs.trace_events`); DROP `obs.golden_sets`
  còn chờ xác nhận AIE-1 (gate thay mentor). B (RLS `wb.recipes`/`wb.recipe_versions`) đã đủ 4/4 chữ ký.
- **CI 5 bước xanh** trên `day20/de-gate-evidence` sau khi gộp kb#26 (T6 retire) + đã có kb#22 (cost) qua
  `main`: `pytest` **239 passed, 0 xfailed** · `ruff check` · `ruff format --check` · `mypy` ·
  `lint-imports`.
