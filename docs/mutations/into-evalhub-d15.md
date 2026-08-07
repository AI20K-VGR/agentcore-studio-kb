<!--
T7 cross-mutation (kit#74 / kit#103) — DE gieo vào packages/evalhub.
Artifact HAI tác giả: phần dưới do DE (người gieo) viết; `## Phản hồi của chủ quadrant` để AIE-2
(chủ evalhub) append bằng commit của chính mình — hai chữ ký.
0-secret · 100% synthetic.
-->

# 8 mutation gieo vào `packages/evalhub` — bảng khai-trước vs thực đo

> **Người gieo:** DE (DongAnh2704) · **Ngày:** 2026-08-07 (D15) · **Chủ quadrant:** AIE-2 (dholmes0207)
> **Đáp lời mời** kit#103 (comment T7 của AIE-2): *"Xin một người gieo vào evalhub — ưu tiên trước D18."*
> **Nền gieo:** nhánh `aie-2/d15-t3-run-cases` @ `c9af832` (nơi có đủ 4 surface D15:
> `run_report.answer_from_trace`, `render.render_run_cases`, `harness.score_case`,
> `harness.tenant_scope_ok`). **Baseline nhánh đó:** `72 passed, 2 xfailed` (exit 0).
> **Suite chạy để chấm bắt/sống:** toàn bộ `packages/evalhub` (chủ quadrant own).

**5 mutant core** khai đúng 4 surface AIE-2 gợi ý + **3 probe** cạnh chưa-tài-liệu-hoá (thử tìm điểm
mù mà self-mutation không thấy). Đúng luật lượt gieo-vào-engine: **khai trước → chạy → so**;
`--color=no` + đọc **exit code**; `PYTHONDONTWRITEBYTECODE=1`; **collection error KHÔNG tính là bắt**;
finding = **dòng lệch declared-vs-actual** (hoặc mutant sống sót), không phải con số bắt được.

## Bảng kết quả

| # | Surface · Mutation | KHAI TRƯỚC | THỰC ĐO | Khớp? |
|---|---|---|---|---|
| **M1** | `harness.tenant_scope_ok` · bỏ guard `if not events: return False` (→ `all([])==True`, xanh-giả) | evalhub **ĐỎ** ở test fail-closed-rỗng của `test_tenant_scope.py` | **1 failed** · `test_tenant_scope.py::test_khong_co_event_thi_fail_closed` | ✅ khớp |
| **M2** | `harness.score_case` (từ-chối) · `no_leak = all(...)` → `any(...)` (nới fence leak) | evalhub **ĐỎ** ở test refusal/leak của `test_smoke_runner.py` | **5 failed** (gồm `test_tu_choi_khong_co_trace_phai_fail_closed`, `test_cross_role_refusal_success`, `test_run_smoke_over_set`, …) | ✅ khớp (thực đo bắt **rộng hơn** khai) |
| **M3** | `harness.score_case` (trả-lời) · `citation_accuracy`: `expected & retrieved` → `expected \| retrieved` (accuracy có thể >1.0) | evalhub **ĐỎ** ở test citation-accuracy của `test_smoke_runner.py` | **5 failed** (gồm `test_answerable_partial_citation_accuracy`, `test_score_is_invariant_to_event_order`, `test_run_smoke_dao_map_tenant_lam_diem_sup`, …) | ✅ khớp |
| **M4** | `run_report.answer_from_trace` · bỏ guard `>1 llm-step` (nhánh "đắt nhất") | evalhub **ĐỎ** ở `test_answer_from_trace.py` | **1 failed** · `test_answer_from_trace_nhieu_llm_step_thi_raise_chu_khong_chon_bua` | ✅ khớp |
| **M5** | `render.render_run_cases` · `n_citation = len(answerable)` → `len(results)` (đưa refusal vào mẫu số citation) | evalhub **ĐỎ** ở `test_render_run_cases.py` | **3 failed** (gồm `test_render_case_mau_so_citation_loai_refusal_chu_khong_dung_tong_case`, …) | ✅ khớp |
| **B1** *(probe)* | `harness._contains_phrase` · off-by-one `range(len-n+1)`→`range(len-n)` (rụng cửa sổ CUỐI answer) | **KHÔNG CHẮC** — cụm ở cuối answer có bài nào đi qua không? | **7 failed** (gồm `test_contains_phrase_tolerates_punctuation_and_position`, …) | ✅ khớp (bắt — có phủ vị trí cuối) |
| **B2** *(probe)* | `run_report.answer_from_trace` · `outputs.get("refused", False)` → `True` (default khi THIẾU key `refused`) | **KHÔNG CHẮC** — sống = điểm mù | **72 passed, exit 0 — SỐNG SÓT** | ❌ **LỆCH — finding** |
| **B3** *(probe)* | `harness._contains_phrase` · cụm rỗng `return False`→`return True` | evalhub **ĐỎ** (docstring khai fail-closed cụm rỗng) | **1 failed** · `test_contains_phrase_empty_expected_fails_closed` | ✅ khớp |

**Tổng: 8 gieo · 7 bắt · 1 sống (B2) · 0 collection error · 1 finding.**

---

## Finding 1 (B2) · `answer_from_trace` — default `refused=False` khi thiếu key KHÔNG có test nào ghim

`run_report.py:answer_from_trace` cuối hàm:

```python
return AgentAnswer(
    answer=str(outputs["answer"]),
    citations=[str(c) for c in raw_citations] if isinstance(raw_citations, list) else [],
    refused=bool(outputs.get("refused", False)),   # ← default False khi outputs THIẾU key "refused"
)
```

Đổi default `False → True` → **toàn bộ 72 bài vẫn xanh** (exit 0). Nghĩa là **không bài nào** dựng một
`llm-step` có `outputs` **thiếu hẳn key `refused`** rồi khẳng định `AgentAnswer.refused` (hoặc điểm
phụ thuộc nó). Mọi trace trong test đều ghi `refused` tường minh → nhánh default không bao giờ chạy.

**Vì sao đáng vá, không phải bắt bẻ.** Docstring của chính hàm gọi `refused` là **carrier**: *"đọc lại
giá trị mà producer đã ghi"*, mặc định `False` khi vắng. Đó là một **bất biến có tài liệu nhưng 0 lớp
test** — đúng dạng lỗ M9 mà chính AIE-2 tìm ra hôm nay (citation agent tự khai vs trace). Nếu về sau:
- producer (interpreter) đổi hợp đồng và **bỏ ghi `refused`** trong một nhánh, hoặc
- ai đó "dọn dẹp" đổi default thành `True`,

thì mọi case rơi vào nhánh vắng-key sẽ **lật thầm answerable↔refused**, và bảng điểm vẫn trông đúng.
Đây là điểm mù kiểu breakpoint #14 (suy một giá trị ngữ nghĩa im lặng rồi chấm như đã đo) — và một
sweep tự gieo không thấy nó vì người viết test *biết* mình luôn set `refused`.

**Đề nghị vá (1 bài, ~5 phút):** thêm test dựng `llm-step` với `outputs = {"answer": "..."}` **không có
key `refused`** → `answer_from_trace(events).refused is False` (và/hoặc `score_case` coi là nhánh
trả-lời). Ghim đúng dòng default. Không phải sửa code — code đang đúng; chỉ là **răng còn thiếu**.

*(Ghi chú phạm vi: B2 là probe DE tự nghĩ, không nằm trong 4 surface AIE-2 liệt kê — nhưng cùng file
`run_report.py` "mới hôm nay". Đây là phần "điểm mù tôi không nghĩ tới" mà cross-seed để tìm.)*

---

## Kỷ luật thực thi

| | |
|---|---|
| Mutation đã push? | **KHÔNG.** Patch local, `cp` backup → restore sau **mỗi** lượt |
| Cây evalhub sau T7 | `git -C packages/evalhub status --short` → **rỗng**; đã `checkout main`, con trỏ về `a60855d` = `origin/main` |
| Nền gieo | nhánh `aie-2/d15-t3-run-cases` @ `c9af832` (4 surface D15 sống ở đây, chưa merge main) |
| Bẫy #1 — ANSI | pytest phát ANSI dù stdout là pipe ⇒ grep `FAILED` lệch. Lưới: `--color=no` **và** đọc **exit code** |
| Bẫy #2 — `.pyc` | bytecode cache khoá theo `(mtime giây, size)` ⇒ mutant 1 ký tự cùng giây load bytecode cũ. Lưới: `PYTHONDONTWRITEBYTECODE=1` |
| Collection error | **0** — mọi mutant chỉ đổi biểu thức/guard, không chèn inline-comment vào literal (rút kinh nghiệm M5-lượt-1 của AIE-2) |
| Doc để ở đâu | `kb/docs/mutations/` (repo người gieo), giống `evalhub/docs/mutations/into-engine-d11.md` (repo AIE-2 khi gieo engine) |

---

## Phản hồi của chủ quadrant

<!-- @dholmes0207 — append bằng commit của CHÍNH BẠN (artifact 2 tác giả, 2 chữ ký). Gợi ý nội dung:
     - B2: đồng ý là lỗ? Đã thêm bài ghim default `refused=False` chưa? (hoặc lý do không cần)
     - M1–M5: có bất ngờ nào ở việc bắt rộng hơn khai (M2/M3/M5) không, hay đúng như thiết kế?
     - Có mutant nào bạn thấy DE khai/đọc sai không. -->

_(để trống — chờ chủ quadrant AIE-2)_
