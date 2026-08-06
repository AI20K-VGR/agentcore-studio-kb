# HANDOFF — Golden-set `callisto-golden-30-v1` + D14 grid (DE)

> Dừng vì hết quota, 2026-08-06 (D14). Note này để tiếp tục sau. Tất cả **chưa commit**.

## 1. TRẠNG THÁI — đã xong & đã verify

### Golden-set cho AIE-2 (#105, đáng ra D16 — làm sớm để gỡ chặn)
- **`golden/callisto-handbook-30-draft.yaml`** — đã **GHI ĐÈ** file 9-case cũ thành **30 case**
  (`golden_set_ref: callisto-golden-30-v1`), **22 dương + 8 âm**.
  - Tên file giữ `-draft` cố ý (không mồ côi doc trỏ tới + đúng DL-12.5 "-draft tới khi AIE-2 nghiệm thu").
  - Đã verify: mọi `expected_citation` truy-xuất-được trong scope · `expected` **grounded** trong chunk trích
    · `expected` **DUY NHẤT** trong (tenant, roles) · case âm fence chặn · load được qua
    `studio_evalhub.GoldenCase` (`expects_refusal=8`).
- **`tests/test_golden_set.py`** — guard mới (kb-native, không import evalhub, không pyyaml): parser 8-field +
  mirror `_contains_phrase`. **31 test PASS** lần chạy cuối. Canh nhãn không trôi khi corpus đổi.
- **`docs/callisto-doc-schema.md`** — cập nhật mô tả "9 skeleton" → "30 case, ref v1".

### Grid queries cho AIE-1 (#95/#96, D14) — TÁCH RIÊNG với golden (KHÔNG gộp)
- `src/studio_kb/grid_queries.py` (20 case typed) · `golden/callisto-grid-queries-v0.yaml` (sinh ra) ·
  `scripts/emit_grid_queries.py` · `tests/test_grid_inputs.py` (12 test) · `docs/design-notes/de-day14.md` ·
  `plans/day14_plan.md`.
- `src/studio_kb/embeddings.py` **KHÔNG đụng** (đã revert ý tưởng dim-32 sai — xem plan §0 đuôi).

### Vá chất lượng theo advisor QA (verdict: GIAO ĐƯỢC KÈM SỬA NHỎ) — ĐÃ áp
- 7 nhãn `expected` không-duy-nhất → đã làm dài/đặc trưng (HB-01,02,06,15,16,17,18).
- HB-08/09 (salary) **gỡ ghép cặp** (cả 2 tenant đều "6 bậc" → vô hiệu làm leak-mimic; header đã ghi rõ).
- **Rebalance borea:** HB-19 (was ankor facilities) → **borea-procurement finance dương**; HB-30 (was ankor T6)
  → **borea T6 âm**. Nay: dương ankor 14/borea 8 · T6 có cả ankor lẫn borea · borea có dương finance.
- **KHÔNG thêm case `expected_tenant: null`** (advisor gợi ý, đã BỎ): null làm `no_leak=all(t!=null)` luôn True
  → rụng răng leak-test (xem `harness.py:170` + format.md §8). Giữ nguyên tắc cũ của DE.

## 2. BƯỚC ĐANG DỞ (bị ngắt) — chạy lại để xác nhận xanh
Docker Postgres cần bật cho `test_pg_kb`. Lệnh:
```
docker compose -f docker-compose.test.yml up -d --wait
export STUDIO_DATABASE_URL="postgresql://studio_app:changeme@localhost:5433/studio_test"
export STUDIO_DATABASE_URL_ADMIN="postgresql://studio_owner:changeme@localhost:5433/studio_test"
uv run --python 3.14 --package agentcore-studio-kb python -m pytest packages/kb -q      # kỳ vọng: all pass, 2 xfailed
uv run --python 3.14 mypy packages/kb/tests/test_golden_set.py                          # đã sửa by_id: dict[str,Chunk]
uv run --python 3.14 ruff check packages/kb && uv run --python 3.14 lint-imports        # ruff sạch, layering KEPT
```
- `test_golden_set.py` chạy riêng đã 31 pass + ruff sạch + lint KEPT; chỉ còn xác nhận **mypy** + **full suite**
  không hồi quy sau 2 edit type annotation cuối (`by_id: dict[str, Chunk]`).

## 3. CÒN PHẢI LÀM
1. **QUYẾT: 1 PR hay 2 PR?** Nhánh hiện tại `day14/de-golden-grid-inputs` đang ôm **cả grid (AIE-1) lẫn
   golden-30 (AIE-2)**. Hai deliverable khác consumer/khác issue — cân nhắc **tách 2 PR** (grid #96 · golden #105)
   cho sạch, hoặc 1 PR nếu muốn nhanh. Commit: danh tính `lvtanhpro`, **không** Co-Authored-By.
2. **Báo AIE-2** (#105/#108): `callisto-golden-30-v1` đủ 30 sẵn ở `kb/golden/callisto-handbook-30-draft.yaml`,
   load được qua `GoldenCase`, mời nghiệm thu (đổi tên file bỏ `-draft` sau khi nghiệm thu).
3. **Báo AIE-1** (#96): grid queries `callisto-grid-queries-v0` sẵn để đo chunking×embedding.
4. **Daily note** `docs/reports` (ngoài submodule kb) — nếu muốn.

## 4. NẾU CẦN SỬA GOLDEN — cách regenerate (chống drift)
Nguồn dựng + verify nằm ở **scratchpad** (không phải file kb):
`/private/tmp/claude-501/-Users-nguyendonganh-agentcore-studio-kit/dfed0245-5cb4-41cf-bb1d-087cce9c87e3/scratchpad/`
- `build_golden30.py` — sửa list `C` (30 tuple) → chạy:
  `uv run --python 3.14 --package agentcore-studio-evalhub python <scratchpad>/build_golden30.py`
  → tự verify (citation+grounded+unique+teeth+fence) rồi ghi `callisto-golden-30-v1.yaml`; copy đè vào
  `packages/kb/golden/callisto-handbook-30-draft.yaml`.
- `validate_evalhub.py` — kiểm load qua pydantic `GoldenCase`.
- Nhãn phải annotate-verify (không gõ tay): `packages/kb/scripts/annotate_golden.py --tenant .. --roles .. --query ".." --expect <chunk_id>`.
- **Scratchpad có thể bị dọn** — nếu mất, `C` tái dựng được từ chính yaml; logic verify đã port vào
  `tests/test_golden_set.py` rồi.

## 5. RỦI RO advisor nêu (đã xử) & còn treo
- ✅ PASS-oan do nhãn chung → đã vá + guard test chặn tái diễn.
- ✅ Phân bố lệch ankor/borea → đã rebalance.
- ⚠️ (cosmetic, chưa làm) HB-20 citation `invoicing#c3` không phải top-hit (nhạy `top_k` nhỏ) — chỉ lưu ý
  AIE-2 khi chỉnh `top_k`, không phải lỗi.
