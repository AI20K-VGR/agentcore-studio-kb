# Bằng chứng D20 — phần DE (kb) · GATE-2 + plan-vs-actual

> **Mục đích:** phần DE trong evidence-pack GATE-2 (issue **#125**, con của gate **#129**). Chuẩn *"đủ để
> chấm không cần hỏi"* — mọi con số §2 **tái lập được** bằng khối lệnh §1, không tin lời khai. §3 là
> **plan-vs-actual** đối chiếu [design-note D11](design-notes/de-day11.md) §6 (DoD #129). §4 là 2 lỗ upstream
> đã biết (T6-integration, cost-lineage) — nêu thẳng, không giấu.
>
> **Bối cảnh trung thực:** báo cáo chạy **12/08 (D18)** như một **gate dry-run** — sớm 2 ngày so với D20
> (14/08). Vì thế 2 dependency upstream (**#111** engine inject · **D19** cost-lineage) **chưa land**; các item
> phụ thuộc chúng ghi ⏳ + honest-TODO, đúng như plan D20 §0 đã gate. Chạy lại đúng ngày gate khi upstream vào.

---

## 1. Chạy lại — khối lệnh dán-là-chạy

Từ **thư mục gốc của kit** (`agentcore-studio-kit/`):

```bash
docker compose -f docker-compose.test.yml up -d --wait

export STUDIO_DATABASE_URL_ADMIN=postgresql://studio_owner:changeme@localhost:5433/studio_test
export STUDIO_DATABASE_URL=postgresql://studio_app:changeme@localhost:5433/studio_test

uv run --python 3.14 pytest packages/kb -q                       # 225 passed, 1 xfailed, 0 skipped
uv run --python 3.14 python packages/kb/scripts/ingest_callisto.py   # ankor 71 · borea 69 · 140 chunk / 2 tenant
```

⚠️ **Hai dòng `export` là bắt buộc** (bài học O3.2): thiếu → test tầng DB **skip lặng lẽ**, `skip ≠ pass`,
và người đọc kết luận số 225 khai láo. Interpreter **pin 3.14** (`uv run --python 3.14`), không `python3`
trần (bẫy 3.11 → SyntaxError giả PEP 695/701/758).

---

## 2. Số đo — DoD #125 từng item

| Item #125 | Bằng chứng (test / lệnh) | Kết |
|---|---|---|
| **KB thật ingest→embed→index per-tenant** | `ingest_callisto.py`: **140 chunk / 2 tenant** (ankor 71 · borea 69), clone-tươi 1 lệnh · `test_pg_kb::test_ingest_idempotent_chay_lai_khong_nhan_doi` + `test_ingest_hai_tenant_moi_ben_chi_thay_phan_minh` | ✅ |
| **`kb.search` cited** (§3.3 shape) | `test_spine_live::test_citations_are_grounded` + `test_trace_la_nguon_citation_dung_duoc_cho_bo_cham` (chunk-id có thật kho Callisto) | ✅ |
| **tenant filter + T1 IDOR xanh** | `test_leak::test_t1_idor` **PASSED** (gỡ xfail D17, RLS + `WHERE tenant_id`) + `test_pg_kb::test_t1_khong_ro_ri_cheo_tenant` | ✅ |
| **T6 label-spoof** | **kb-mức-đầu:** `test_pg_kb::test_t6_khong_ro_ri_cheo_vai` + `test_no_bypass` (5/5: empty-roles→no-grant · không wildcard · public không thấy finance) **PASSED** · **integration:** `test_leak::test_t6_label_spoof` **XFAIL** (chờ #111) | ✅ mức-đầu / ⏳ integration |
| **trace viewer** | `test_trace_reader::test_render_timeline_*` (4 test: tokens · monotonic · tự-sắp-xếp · đủ/thiếu node) **PASSED** | ✅ |
| **cost-lineage cùng-1-số** (§3.2) | `interpreter.py:389` `cost=_NO_COST` (0.0) — **nguồn tokens→cost chưa tồn tại (D19)** | ⏳ (xem §4.2) |
| **golden-set 30** | `callisto-golden-30-v1.yaml`: **30 case · 10 `manual_label`** (D16 + nhãn tay D18) · `test_golden_set` **PASSED** | ✅ |
| **spine 4 bước chạy thật** (DoD #129) | `test_spine_live` **10/10 PASSED** (emit→sink→reader; INV-1 recipe-spoof-tenant→session thắng; refusal-from-grounding) | ✅ |

**Tổng suite kb:** `225 passed, 1 xfailed, 0 skipped`. Xfailed duy nhất = `test_t6_label_spoof`
(integration-close, retire khi #111 land).

---

## 3. Plan-vs-actual — đối chiếu design-note D11 §6 "Điểm S2 đã biết"

Design-note D11 (03/08) **nêu trước 4 điểm** sẽ lộ ở S2. D20 đối chiếu từng điểm — cả chỗ **khớp** lẫn chỗ
**còn treo**:

| # | Dự đoán D11 (§6) | Actual D20 | Kết |
|---|---|---|---|
| 1 | *"Fence mới ở tầng retrieval của KB stub… cần một điểm chặn dùng chung, không rải rác."* | D17 lật `KbSearchService`→`PgKbSearch`: fence tại retrieval **một seam** chính thức, fail-closed (§3.3). `test_no_bypass` chứng minh 1 chỗ chặn. | ✅ **đúng hướng, đã làm** |
| 2 | *"INV-1 mới chặn `tenant`, chưa chặn `roles`… `section_roles` nhận-rồi-bỏ."* | **kb-lane đã chặn roles** tại `PgKbSearch` (`test_t6_khong_ro_ri_cheo_vai` + no-bypass PASSED). **Nhưng** integration-close (interpreter đè recipe-khai) = **#111 engine chưa land** — `interpreter.py:291` mới inject `tenant_id`, chưa `section_roles`; con trỏ `packages/engine`@**D15** (`86b88ed`). | ⏳ **dự đoán đúng — vẫn là gap**, đóng kb-mức-đầu, chờ #111 |
| 3 | *"`obs.costs` ngoài fence-lane DE — DE điền ở D19 (cost-lineage)."* | Đúng: `cost=_NO_COST` (0.0), chưa có nguồn tokens→cost. **Cập nhật:** mini-RFC schema-drift (amendment **D18** 12/08) phân loại lại `obs.costs`→**CẦN RLS** (chi phí per-tenant lên UI), build kèm `tenant_id`+RLS ngay ở D19, không để cột trần vá sau. | ⏳ **dự đoán đúng — chờ D19** |
| 4 | *"`obs.golden_sets` nghi bảng-chết trùng `eval.golden_sets` → đề xuất DROP (mini-RFC)."* | mini-RFC amendment D18 **giữ đề xuất DROP** `obs.golden_sets` (0 runtime reader); nguồn sự thật = `eval.golden_sets`. **Chưa DROP thật** (chờ phê). Cùng amendment: bỏ nhóm "3 bảng HOÃN", chốt nhị phân cần/không-cần RLS; `eval.*`→KHÔNG-CẦN (đề chung, observe-only) *đề xuất chờ AIE-2 phê*. | 🔵 **đúng nghi vấn — mini-RFC mở, chưa thực thi DROP** |

**Chỗ lệch dự đoán (trung thực):** không có mục nào D11 hứa mà D20 làm thiếu; ngược lại D20 **làm dày hơn**
dự đoán ở điểm 2 (đã chặn roles ở kb-lane, không chỉ "nhận-rồi-bỏ" như D11 mô tả). Điểm treo còn lại đều là
**cross-lane/upstream** (engine #111, cost D19), không phải nợ trong lane kb.

---

## 4. Hai lỗ upstream đã biết — honest-TODO (không giấu, không fake-green)

### 4.1 T6 integration-close ⇐ #111 (engine, AIE-1)
- **Trạng thái:** `test_t6_label_spoof` giữ **XFAIL**; đóng thật cần dòng inject `section_roles` từ
  `session_context.roles` vào `node.params` ở `interpreter.py:291` (cạnh `tenant_id`). Con trỏ engine@D15
  chưa có dòng này.
- **DE đã cấp sẵn:** no-bypass teeth (5/5) + acceptance mô phỏng override — là **spec** cho #111. Khi #111
  land → gỡ xfail, thêm assert integration trong spine-live, sửa `test_leak_meta.py` cùng commit.
- **DE không WRITE engine** (lane AIE-1).

### 4.2 Cost-lineage cùng-1-số ⇐ D19 (#120)
- **Trạng thái:** `interpreter.py:389` `cost=_NO_COST` (0.0); docstring `:221` tự khai *"no real cost model
  exists yet"*. Không có hàm tokens→cost trong repo. Invariant §3.2 (`cost` UI-test == trace == dashboard)
  **chưa chứng minh được** — hiện "khớp" một cách rỗng nghĩa (0.0 khắp nơi).
- **Seam cần chốt (coordinate leader):** nguồn-1-số emit ở **engine** hay derive ở **apps/`obs.costs`**? DE
  trace-viewer phải **đọc, không tính lại** (design-note §6: `obs.costs` ngoài fence-lane DE). mini-RFC D18:
  `obs.costs` build kèm `tenant_id`+RLS từ đầu.
- **Không WRITE apps/engine trong lane DE.**

---

## 5. Bàn giao / mốc retire

- **#111 land** → gỡ xfail `test_t6_label_spoof` + assert integration + `test_leak_meta.py` (commit riêng).
- **D19 land** → thêm test cost-lineage đọc-cùng-số (reader vs UI-test), tái lập được.
- **mini-RFC schema-drift** (`docs/mini-rfc-tenant-schema-unify.md`, amendment D18 đang WIP chưa commit) →
  chờ AIE-2 phê phần `eval.*`; `obs.costs` (lane DE) chốt CẦN-RLS build ở D19; DROP `obs.golden_sets` khi phê.
- **CI 5 bước** (gate-ready, code src không đổi — chỉ thêm docs): `pytest · ruff check · ruff format --check ·
  mypy · lint-imports`.
