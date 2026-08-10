---
id: studio.design-note.de.day-16
type: design-note
role: DE — Nguyễn Đông Anh
day: 16
date: 2026-08-10
status: draft (chờ review — bàn giao #108)
scope: golden-set 30 recorded từ doc-factory · 1 script 2 deliverable · phủ biên · promote draft→v1
length_target: ≤2 trang
---

# Design-note DE (D16) — Golden-set 30 recorded + "1 script 2 deliverable" (KB + golden-set)

> Neo: issue **#105** (*"Cấp golden-set 30 case có nhãn từ chính doc-factory (1 script 2 deliverable:
> KB + golden-set); expected + expected-citations phủ biên"*), tiêu thụ bởi **#108** (AIE-2, chủ công
> eval harness v1 + scorecard). Đây là **thiết kế + đánh đổi + ràng buộc bàn giao**, không tóm tắt yaml.

## 1. DE giao gì

- **`golden/callisto-golden-30-v1.yaml`** — 30 case (22 dương + 8 âm T1/T6), `golden_set_ref:
  callisto-golden-30-v1`, shape 8-field `docs/format.md` §2 (đọc y hệt `smoke-5.yaml`).
- **Nguồn sự thật là `src/studio_kb/golden_set.py`** (typed `GOLDEN_CASES`); yaml **sinh ra** bằng
  `scripts/emit_golden_set.py`, byte-identical (kb không kéo `pyyaml`). #108 có thể **import thẳng
  `golden_set.GOLDEN_CASES`** khỏi parse yaml, hoặc đọc yaml — cùng một dữ liệu.
- **`scripts/build_callisto.py`** — entrypoint "1 lệnh 2 deliverable": một lệnh phát **KB** (re-record
  `embeddings-callisto-v0.json` + manifest 42 doc/140 chunk/2 tenant) **và** golden-set, từ **cùng**
  `load_callisto()`.

## 2. Vì sao "recorded" (không để yaml gõ tay) — #105 "từ CHÍNH doc-factory"

Bộ 30 đã annotate-verified + xanh từ **D14**. D16 **không viết lại nhãn** — chỉ **dời** y nguyên vào
module typed rồi phát lại. Giá trị: `render_yaml()` ghim **đúng-từng-byte** bộ đã xanh, nên
`test_golden_set.py::test_yaml_byte_identical_voi_module_typed` biến kỷ luật tay D6 thành **CI gate** —
sửa một `query`/`expected`/`chunk_id` mà quên re-emit là ĐỎ ngay (không còn cửa lệch âm thầm). Cùng khuôn
`grid_queries.py` (D14) / `embeddings.py`. **Promote** `git mv` `-draft`→`-v1` là **pure-rename
zero-content-diff** (R100) — bằng chứng 30 case không bị đụng.

**Ranh authored ↔ derived (không tô hồng):** `query` là **người viết** (câu hỏi tự nhiên, không sinh bằng
máy — như `grid_queries`); NHÃN (`expected_citation`, `expected_tenant/section_role`) là **derived** từ
retrieval thật (`annotate_golden.py`, `StaticKbSearch`). "1 lệnh 2 deliverable" bảo đảm mọi
`expected_citation` là `chunk_id` doc-factory **thật do kiến tạo** (`build_callisto` kiểm ∈ corpus cuối
lệnh), không phải do gõ đúng.

## 3. Phủ biên — audit thành gate (`EDGE_AXES`)

`golden_set.EDGE_AXES` khai tường minh 7 trục biên → case phủ; `test_phu_bien_moi_truc_co_case` canh mỗi
trục có ≥1 case tồn tại. "Phủ biên" đọc-được, không khai suông:

| trục | case | ý đồ |
|---|---|---|
| `cross_tenant_pair` | HB-01/02·03/04·05/06·10/22·11/12·15/16 | cùng query khác tenant → đáp án PHẢI khác số (leak-mimic) |
| `t1_ankor_to_borea` / `t1_borea_to_ankor` | HB-23,25 / HB-28,29 | T1 IDOR **hai chiều** → refusal |
| `t6_role_ankor` / `t6_role_borea` | HB-24,26,27 / HB-30 | T6 chéo-vai **hai tenant** → refusal |
| `answer_not_c1` | HB-05,06,17,20,21 | đáp án KHÔNG ở #c1 → chống bug "luôn trả top-1" |
| `deliberately_unpaired` | HB-08,09 | cả 2 tenant '6 bậc' → CỐ Ý không làm leak-mimic (ghi để không ai "sửa") |

## 4. Ràng buộc bàn giao #108 (eval harness v1)

- **Tokenizer phải khớp:** golden mirror đúng `harness._contains_phrase` = `re.findall(r"\w+", lower)` +
  so token liên tiếp. Nhãn `expected` kiểm **DUY NHẤT** trong (tenant, roles) theo luật đó (chống PASS oan
  khi câu trả lời sai chủ đề vẫn chứa cụm chung). **Đừng đổi tokenizer lệch** — golden sẽ hết răng.
- **Rename an toàn:** AIE-2 xác nhận harness đọc bằng `golden_set_ref` (không path). Chỗ hardcode duy nhất
  là `test_golden_set.py:29` (guard của chính kb) — đã sửa kèm trong cùng commit.
- **8 case âm là hợp đồng fence:** #108 chấm chúng ra **refusal** (rỗng citation); đừng "chữa" thành có
  đáp án.

## 5. Đọc cả tuần (D16 là substrate, dựng một lần)

- **D17 (#110, DE chủ):** 8 case âm = fixture cho fence tại retrieval + T6 label-spoof. Giữ ổn định.
- **D18 (#115):** subset nhận **nhãn tay** đo agreement vs LLM-judge → sẽ thêm field `manual_label` cho
  subset. **Chưa thêm hôm nay** (giữ shape 8-field); chỗ mở rộng đã chừa (docstring `golden_set.py`).
- **D20 (#125, GATE-2):** bộ này là eval v1 chấm verdict tại gate. `render_yaml` byte-identical +
  determinism là điều kiện replay cho **cùng verdict**; tên `-v1` để gate không xử artifact mang nhãn
  `draft`.

## 6. Bằng chứng (D16)

Toàn suite kb **199 passed, 2 xfailed** (2 xfail = T1/T6 `KbSearchService`, cố ý giữ cho D17 — không
đụng). `test_golden_set.py` +3 guard (byte-identical · phủ-biên · khoá 22/8 + refusal module↔yaml).
`ruff`/`mypy`/`lint-imports` sạch. `build_callisto.py` phát 2 deliverable, mọi `expected_citation` ∈
corpus. Mutation sweep: mutant `is_refusal` bỏ `not` đã bịt (thêm test khoá 22/8); còn lại `frozen/slots`
by-design (cùng chính sách `grid_queries`/`Chunk`, cố ý không test).
