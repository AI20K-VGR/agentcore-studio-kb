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

**AIE-2 (dholmes0207) · 2026-08-07 · chữ ký thứ hai của artifact này.**

**Không nhận nguyên văn — kiểm lại trước rồi mới trả lời.** Mọi số dưới đây đo trên
`aie-2/d15-t3-run-cases` @ `7745bd5`, không phải trên nền `c9af832` mà DE gieo (lý do ở §4).

---

### 1 · B2 — đồng ý là lỗ. Không đồng ý câu *"code đang đúng; chỉ là răng còn thiếu"*

Vế *"đây là lỗ"*: **đúng, và đã xác minh chứ không tin theo.** Gieo lại B2 trên head `7745bd5` →
`76 passed`, exit 0. Sống thật, không phải hiện vật của SHA cũ.

Vế *"code đang đúng"*: **không đồng ý.** `answer_from_trace` **raise** ở 4 nhánh không chứng minh
được — `events` rỗng · không có `llm-step` · thiếu key `answer` · nhiều `llm-step`. Riêng `refused`
thì **đoán im lặng**. Đó không phải một nhánh thiếu test, đó là một nhánh **lệch với doctrine của
chính hàm**, và B2 chạm đúng vào chỗ lệch.

Và mặc định `False` không phải lựa chọn an toàn — nó là lựa chọn **ĐO SAI**:

> một ca đáng là *từ-chối* nhưng thiếu key sẽ bị đẩy sang nhánh trả-lời rồi báo **FAIL** ⇒ bảng điểm
> nói *"agent trả lời sai"*, trong khi sự thật là *"trace không đọc được"*.

Ghim `refused is False` bằng test — như đề nghị — sẽ **ghim cứng đúng phép đo sai đó**, và biến một
lỗ thành một bất biến được bảo vệ. Nên vá theo hướng **raise**, cho đối xứng với 4 nhánh kia.

Cơ sở để chọn raise chứ không phải khẩu vị: producer thật **luôn** ghi key này —
`engine:executors.py:265`, `"refused": not citations`. Thiếu nó nghĩa là trace dị dạng hoặc đến từ
producer lạ, không phải một ca vận hành bình thường.

**Đã vá:** commit `9505c8d` trên `aie-2/d15-t3-run-cases` (PR
[evalhub#15](https://github.com/AI20K-VGR/agentcore-studio-evalhub/pull/15)), bài
`test_answer_from_trace_thieu_key_refused_thi_raise_chu_khong_doan_False`. Viết **đỏ trước** — fail
bằng `DID NOT RAISE`, không phải `ImportError`. Suite `76 → 77`.

**Gieo lại CẢ HAI chiều sau khi vá**, vì chỉ gieo chiều `True` thì bài mới có thể đang ghim *"phải
bằng `False`"* thay vì *"phải raise"*, và lỗ còn nguyên dưới một cái tên khác:

| gieo lại | exit | |
|---|---|---|
| hoàn nguyên bản cũ `get("refused", False)` | 1 | **BẮT** |
| B2 nguyên bản của DE `get("refused", True)` | 1 | **BẮT** |

### 2 · M1–M5 bắt rộng hơn khai — không bất ngờ, và lý do nên ghi

Đúng như thiết kế, nhưng cơ chế khác nhau ở hai nhóm:

- **M2/M3** (`score_case`) rộng vì `score_case` là **tim** — `run_smoke` và bài over-set đều đi qua
  nó, nên đổi một vị từ là vỡ dây chuyền. Số `5 failed` đo **độ tập trung của kiến trúc**, không đo
  độ mạnh của suite. Cùng lớp với `M8` ở sweep tự gieo của tôi: khai 1, thực 11, nhưng cơ chế bắt
  thật là *"nó raise"* chứ không phải *"suite phát hiện"*.
- **M5** rộng vì bài `toan_refusal` hoá ra là bài **đa mục đích** — nó khoá cả nhánh `n = 0` lẫn tính
  đúng của hai mẫu số. Tôi đã gặp đúng hiện tượng này (`self-render-d15.md` §2.3) và ghi rằng đó là
  chỗ mạnh nhất của suite, không phải bài phụ như tên gọi gợi ý.

⇒ Một dòng *"bắt rộng hơn khai"* nên đọc là **câu hỏi**, không phải điểm cộng: rộng vì suite khoẻ,
hay rộng vì một hàm đứng ở chỗ ai cũng phải đi qua? Hai lượt này là vế thứ hai.

### 3 · Hai mutant TRÙNG với sweep tự gieo — và lỗi thuộc về tôi

| DE | ≡ của tôi | mutation | kết quả hai lượt |
|---|---|---|---|
| **M4** | `M6` (`self-render-d15.md` §1) | `answer_from_trace` bỏ guard `>1 llm-step` | y hệt, 1 bài đỏ |
| **M5** | `M3` (§1) | `render_run_cases` `n_citation = len(results)` | y hệt, 3 bài đỏ |

Hai lượt gieo độc lập cách nhau 5 tiếng, cùng mutation, cùng tập bài đỏ. **Nguyên nhân là bảng gợi ý
T7 của tôi.** Nó liệt kê `run_report.answer_from_trace` và `render.render_run_cases` là *"mới hôm
nay"* mà **không nói** rằng M1–M8 đã gieo vào đúng hai chỗ đó vài giờ trước. DE không có cách nào
biết, nên 2/8 lượt gieo rơi vào đất đã cày.

Tệ hơn: đúng lúc DE nhận việc, chỗ **thật sự** chưa có lưới là `_row_to_event` — cả tầng đọc DB của
`run_report.py`, **0 test** — và nó **không** nằm trong bảng gợi ý. Tôi vá nó lúc `08:20`, ba phút
trước comment nhận việc của DE.

⇒ **Bài học cho lần xin gieo sau, và nó ngược với trực giác:** một bảng *"gợi ý bề mặt"* do chủ
quadrant viết sẽ **lái người gieo về chỗ chủ quadrant đã nghĩ tới** — tức đúng chỗ ít điểm mù nhất.
Giá trị của lượt này nằm trọn ở **B2**, là **probe DE tự nghĩ, ngoài danh sách tôi đưa**. Lần sau xin
gieo thì đưa *"file nào mới"* + *"lần cuối tôi gieo vào đâu và khi nào"*, rồi để người gieo tự chọn.

### 4 · Hai chỗ số lệch giữa hai doc — không ai sai, nhưng phải ghi

| | doc này (DE) | đo ở evalhub |
|---|---|---|
| nền gieo | `c9af832` | head đã là `7745bd5` khi DE giao lúc `08:31` |
| baseline | `72 passed, 2 xfailed` | `71 passed, 1 skipped, 2 xfailed` |

**SHA.** DE nhận việc `08:23`, giữa hai commit của tôi (`08:20` và `08:26`), và cả hai push lên
origin sau đó — nên lúc DE đọc branch thì origin vẫn ở `c9af832`. **Không kết luận nào bị ảnh hưởng:**
`git diff c9af832..7745bd5` trên `harness.py` và `render.py` là **rỗng**, `run_report.py` chỉ `+9/-3`
và **toàn docstring**; `answer_from_trace` byte-identical. Đó là lý do B2 được gieo lại trên head để
xác nhận thay vì suy luận. Chỉ cần một dòng ghi base SHA trong doc là ai chạy lại cũng khớp.

**Baseline.** Chênh đúng 1 bài: `test_scorecard_roundtrip.py:61` **skip** khi thiếu
`STUDIO_DATABASE_URL_ADMIN`. DE có DSN nên chạy đủ **72 bài thật** ⇒ sweep của DE **mạnh hơn** baseline
local của tôi một bài, và mạnh đúng ở nhánh DB. Ghi lại để không ai đọc chênh lệch này thành mâu thuẫn.

### 5 · Chốt

`kit#74` đòi hai chiều: *"you seed bugs in their code, the owner has to show their tests catch them.
Both of you write down what happened."* Với quadrant **evalhub** thì từ hôm nay đủ cả hai — DE gieo,
chủ quadrant đã cho thấy bài bắt được (B2 bắt cả hai chiều sau khi vá), và cả hai đã viết lại.

Vế còn thiếu của cơ chế bây giờ nằm ở quadrant **engine**: mục `## Phản hồi của chủ quadrant` trong
`evalhub/docs/mutations/into-engine-d11.md` vẫn trống sang ngày thứ tư. Đó là việc của
@TranBaDat2607, không phải của DE — nêu ở đây để bảng theo dõi không trông như đã đủ.

Kết quả lượt này đã chép sang `evalhub/docs/mutations/self-render-d15.md` §6, có trỏ ngược về đây.
