# Plan D16 (DE) — Golden-set 30 case nhãn TỪ CHÍNH doc-factory (1 script 2 deliverable: KB + golden-set) + phủ biên · promote `draft`→`v1` (AIE-2 đã gỡ blocker; rename KÈM sửa `test_golden_set.py:29` cùng commit)

> **Ngày:** 2026-08-10 (D16, Thứ Hai · Chặng 2 / Sprint 2 · Tuần 4) · **Bút:** DE (Nguyễn Đông Anh)
> **Anchor:** issue kit **#105** (con của **#109** "Eval harness v1 + golden-set 30 + scorecard chấm
> điểm"). Anh em: AIE-1 **#106** (interpreter chạy 30 case deterministic qua fixtures để scorecard ổn
> định qua replay) · SWE **#107** (`golden_set_ref` + `scorecard_threshold` trong recipe trỏ đúng
> golden-set) · AIE-2 **#108** (**chủ công**: eval harness v1 field-match/exact scorer + scorecard
> render + verdict PASS/FAIL vs threshold).
> **Repo WRITE: `agentcore-studio-kb`** · kit READ. **Milestone:** Sprint 2 — Gate Day 20.
>
> Việc DE (#105, dòng tiêu đề): *"**Cấp golden-set 30 case có nhãn** từ chính doc-factory (1 script 2
> deliverable: KB + golden-set); expected + expected-citations **phủ biên**."* DoD 4 ô (eval harness v1
> chạy 30 · scorecard render success+citation+verdict · golden-set 30 có nhãn · đổi threshold → verdict
> đổi) là **DoD chung kế thừa từ cha #109** — đọc là **"phần DE của 4 ô đó"**: DE cấp **golden-set 30
> có nhãn (ô 3)**; harness v1 + scorecard render + verdict + threshold-flip là **#108** (evalhub);
> replay deterministic là **#106** (engine); `golden_set_ref`/`threshold` trong recipe là **#107**
> (workbench). DE **không** viết harness/scorecard/recipe.

---

## 0. Đọc cho đúng trước khi cắt — D16 KHÔNG phải build lại 30; là NÂNG golden-set lên "recorded từ doc-factory" + GỘP 1 lệnh + audit phủ biên + promote `draft`→`v1`

Năm điều đặt lằn ranh của ngày:

**(a) Nền phải là main MỚI — D15 đã đóng.** PR kb **#16** (`D15 — trace viewer tokens + ordering
monotonic`) và **#17** (`D15 — mutation into evalhub`) **đã MERGED** (`1e8774f`); `kit#142` bump 6 con
trỏ submodule sau D15 đã merged. Local kb có thể còn đứng nhánh D15. → **`git fetch` + cắt
`day16/de-golden-set-recorded` trên `origin/main` MỚI** (`1e8774f`), KHÔNG xây tiếp trên nhánh D15
(refresh local mỗi ngày — đừng coi nhánh checkout là bất khả xâm phạm).

**(b) 30 case ĐÃ tồn tại và ĐÃ có răng — D16 là DỜI vào khuôn recorded, không viết lại nhãn.**
`golden/callisto-handbook-30-draft.yaml` (build D14, `d6a5dc9`) đã đủ **30 case = 22 dương + 8 âm**,
nhãn annotate-verified qua `scripts/annotate_golden.py`, và `tests/test_golden_set.py` **đã canh 5 trục**:
đủ-30 · citation truy-xuất-được · `expected` grounded trong chunk trích · `expected` **DUY NHẤT** trong
(tenant, roles) (chống PASS oan) · case âm fence kín · teeth ≥2 ứng viên cùng vai · refusal-semantics khớp
scope · citation khớp `expected_tenant/section_role`. **Khe hở thật của D16 nằm ở CHỮ "từ chính
doc-factory (1 script 2 deliverable)"**, không ở nội dung 30 case: hiện golden-set là **yaml gõ tay**
(annotate-verified nhưng vẫn tay), CHƯA phải **recorded artifact** như `embeddings-callisto-v0.json`
(`record_embeddings.py`) và `callisto-grid-queries-v0.yaml` (`grid_queries.py`→`emit_grid_queries.py`,
byte-identical, guard `test_grid_inputs.py`). D16 = **đưa golden-set vào đúng khuôn đó**.

**(c) "1 script 2 deliverable" = MỘT lệnh, clone-tươi, ra CẢ KB manifest LẪN golden-set — cùng
`load_callisto()`, cùng `chunk_id`.** Đây là yêu cầu clone-tươi-chạy-nguyên-lệnh của rubric S2. Hiện
đường KB (`ingest_callisto.py`→DB, `record_embeddings.py`→fixture) và đường golden (yaml tay) **rời
nhau**; không có gì buộc `expected_citation` trong golden phải là `chunk_id` doc-factory **thật** ngoài
kỷ luật tay + test guard. D16 gộp: **một entrypoint** chạy doc-factory **một lần** rồi phát **hai
deliverable** từ **cùng một nguồn** — nên `chunk_id` trong golden-set là thật **do kiến tạo**, không phải
do người gõ đúng. Đây là điều "từ CHÍNH doc-factory" đòi, và là cái D14 chưa đóng.

**(d) "phủ biên" (expected + expected-citations) là AUDIT có bằng chứng, không phải thêm case bừa.**
Biên đã phủ trong 30 hiện tại: cặp chéo-tenant cùng-query-khác-số (leak-mimic) HB-01/02·03/04·05/06·
10/22·11/12·15/16 · T1 **cả hai chiều** (ankor→borea HB-23/24; borea→ankor HB-28/29) · T6 **cả hai
tenant** (ankor HB-24/26/27; borea HB-30) · đáp-án-KHÔNG-ở-`#c1` (HB-20 `#c3`, HB-21 `#c3`, HB-05/06
`#c2`) · cặp CỐ Ý không ghép HB-08/09 (cả hai tenant '6 bậc' → vô hiệu phép thử fence). D16 **biến audit
tay đó thành một bảng phủ-biên tường minh trong module typed** + test khẳng định mỗi trục biên có ≥1 case,
để "phủ biên" **đọc được**, không phải lời khai. **Không** phình bộ quá 30 nếu không cần (30 là số cha
#109 chốt); nếu audit lộ 1 trục biên trống → thêm case **thay** case trùng, giữ 30.

**(e) Promote `draft`→`v1` LÀM Ở D16 — AIE-2 đã gỡ blocker; ràng buộc DUY NHẤT là sửa kèm
`test_golden_set.py:29` cùng commit.** Hôm qua treo vì chưa rõ #108 có hardcode path không; **AIE-2 đã
xác nhận** (10/08): *"đổi tên tuỳ DE, không chặn AIE-2, không cần gấp — chỉ nhớ sửa kèm
`packages/kb/tests/test_golden_set.py:29` trong cùng commit vì đó là hardcode path trong guard test của
chính kb, đỏ nếu đổi tên mà bỏ quên."* → harness #108 KHÔNG trỏ bằng path (đọc bằng `golden_set_ref`);
chỗ hardcode **duy nhất** là guard của chính kb (`_GOLDEN`, dòng 29). D16 là ngày *finalize* golden-set,
`golden_set_ref` **trong** file đã final `callisto-golden-30-v1` từ D14 — để tên FILE mãi `-draft` cho
artifact sẽ chấm verdict tại **gate D20** là sai và đẻ chore rename lơ lửng. → **D16 `git mv`
`callisto-handbook-30-draft.yaml`→`callisto-golden-30-v1.yaml`**, cập nhật `test_golden_set.py:29` +
`emit_golden_set.py` output path **trong CÙNG commit** (rename tự-chứa trong lane kb). Sửa dòng 29 là
**refactor artifact-được-canh** (đổi path, giữ nguyên MỌI assert ngữ nghĩa) — **KHÔNG** phải
sửa-test-để-pass; ngược lại thêm guard byte-identical để rename mà quên re-emit là ĐỎ ngay.

Lằn giữ nguyên: **chỉ WRITE trong `packages/kb`**; **không đụng** evalhub/harness/scorecard (#108),
engine/interpreter (#106), workbench/recipe (#107), `apps/studio`. Bàn giao AIE-2 bằng **artifact +
tài liệu trong kb**, không viết sang repo khác. **Giữ `EMBEDDING_DIM=8`, không đụng schema** (chống
schema-drift — dặn mentor S1). **KHÔNG lật `KbSearchService`, KHÔNG gỡ `test_leak` xfail** (un-ratchet =
D17 #110). **Không sửa test để pass** — mọi guard `test_golden_set.py` giữ nguyên độ chặt hoặc chặt hơn;
đổi dòng 29 chỉ là đổi path deliverable (đã coordinate với #108), không nới assert nào.

---

## 1. Việc sẽ làm (nhánh `day16/de-golden-set-recorded`, nền `origin/main` MỚI · test-first)

### ① `src/studio_kb/golden_set.py` — nguồn sự thật TYPED cho 30 case (mirror `grid_queries.py`)
Dời 30 case từ yaml tay vào module typed `GOLDEN_CASES: list[GoldenCase]` + `GOLDEN_SET_REF =
"callisto-golden-30-v1"` + `render_yaml()`. Cùng khuôn `grid_queries.py`:
- `GoldenCase` dataclass 8-field (`docs/format.md` §2): `case_id · query · tenant · section_roles ·
  expected_tenant · expected_section_role · expected · expected_citation`. Thêm `is_refusal` property
  (`not expected_citation`) như `_Case` trong test.
- **Query là authored (người viết), NHÃN là derived (máy).** Nói thẳng ranh này trong docstring: câu hỏi
  tự nhiên không sinh được bằng máy (như `grid_queries.py`); cái "từ doc-factory" là **`expected_citation`
  = `chunk_id` thật do `load_callisto()` cắt ra**, kiểm annotate-verified. Không tô hồng.
- `render_yaml()` sinh **byte-identical** yaml (giữ header comment giải thích cặp chéo/HB-08-09/22+8),
  không kéo `pyyaml` (kb cố ý chưa khai — `doc_factory.parse_front_matter` docstring).

### ② `git mv` → `golden/callisto-golden-30-v1.yaml` — promote `draft`→final, RECORDED (§0e)
`git mv callisto-handbook-30-draft.yaml callisto-golden-30-v1.yaml` (giữ lịch sử). File này từ nay **sinh
ra** bởi ③ (không gõ tay), nội dung phải `==` `render_yaml()`. Tên file khớp `golden_set_ref` đã final.
**Trong CÙNG commit** (AIE-2 dặn): cập nhật `test_golden_set.py:29` (`_GOLDEN`) + output path của
`emit_golden_set.py` → tên mới. Đây là 3 điểm chạm path duy nhất trong kb (đã grep xác nhận: chỉ
`test_golden_set.py:29` hardcode; harness #108 đọc qua `golden_set_ref`, không path).

### ③ `scripts/emit_golden_set.py` + gộp `scripts/build_callisto.py` — "1 script 2 deliverable"
- `emit_golden_set.py`: ghi/ghi-đè `callisto-golden-30-v1.yaml` từ `golden_set.render_yaml()` (mirror
  `emit_grid_queries.py`). Chạy lại phải byte-identical; `git diff` khác rỗng = quên re-emit.
- `build_callisto.py` (**entrypoint "1 lệnh 2 deliverable"**): chạy `load_callisto()` **một lần**, rồi
  gọi lần lượt (a) đường KB — re-emit `embeddings-callisto-v0.json` (qua `record_embeddings`) + in
  manifest 42 doc / 140 chunk / per-tenant count (đường ingest ăn cùng corpus); (b) đường golden —
  `emit_golden_set`. Cùng một `load_callisto()` → cùng `chunk_id` **do kiến tạo**. In một dòng tổng
  ("KB: 140 chunk/2 tenant · golden: 22 dương + 8 âm, tất cả `expected_citation` ∈ corpus"). **Không**
  tự dựng schema / không tự ghi DB ở đây (DDL = composition-root; ingest DB là `ingest_callisto.py` khi
  có Docker — giữ ranh cũ).

### ④ Phủ biên tường minh — bảng trục + guard (DoD "expected + expected-citations phủ biên")
Trong `golden_set.py`, khai `EDGE_AXES: dict[str, list[case_id]]` liệt kê mỗi trục biên → các case phủ
nó: `cross_tenant_pair` · `t1_ankor_to_borea` · `t1_borea_to_ankor` · `t6_role_ankor` · `t6_role_borea`
· `answer_not_c1` · `deliberately_unpaired` (HB-08/09). Test ④ khẳng định **mỗi trục có ≥1 case tồn tại
trong bộ** — biến audit §0(d) thành CI gate, "phủ biên" đọc-được, không khai suông.

### ⑤ Tests — mở rộng guard + đổi path deliverable, KHÔNG nới lỏng (test-first)
- `tests/test_golden_set.py`: **đổi `_GOLDEN` (dòng 29) sang `callisto-golden-30-v1.yaml`** (theo ②/§0e,
  cùng commit — AIE-2 dặn; là đổi path deliverable đã coordinate, **KHÔNG** sửa-test-để-pass: mọi assert
  ngữ nghĩa giữ nguyên). **Thêm** ca **byte-identical** (`callisto-golden-30-v1.yaml` trên đĩa `==`
  `golden_set.render_yaml()` — bắt drift gõ tay + bắt rename-mà-quên-re-emit, như `test_grid_inputs`) +
  ca **phủ-biên** (mỗi trục `EDGE_AXES` có ≥1 case). Giữ nguyên 5 trục cũ (đủ-30, grounded, duy-nhất,
  fence, teeth≥2, refusal-semantics, citation-tenant-role).
- Có thể để test import `GOLDEN_CASES` typed thay parser tay — nhưng **giữ parser yaml hiện có** cho ca
  byte-identical (đọc file thật, so với render) để không mất lớp bắt drift file↔module.

---

## 2. DoD #105 (phần DE) — đối chiếu

- [ ] **golden-set 30 có nhãn** — ①②: 30 case (22 dương + 8 âm) dời vào `golden_set.py` typed, phát
  `callisto-golden-30-v1.yaml` recorded (promote từ `-draft`, §0e); nhãn annotate-verified (không gõ
  tay), guard `test_golden_set` giữ nguyên 5 trục + thêm byte-identical.
- [ ] **từ chính doc-factory (1 script 2 deliverable: KB + golden-set)** — ③: `build_callisto.py` chạy
  `load_callisto()` một lần → phát **KB manifest/embeddings + golden-set**, cùng `chunk_id`; clone-tươi
  một lệnh ra cả hai. `expected_citation` là `chunk_id` thật **do kiến tạo**, test canh ∈ corpus.
- [ ] **expected + expected-citations phủ biên** — ④: `EDGE_AXES` + guard mỗi trục biên có case
  (cross-tenant pair · T1 hai chiều · T6 hai tenant · answer≠#c1 · unpaired HB-08/09).
- [~] **Eval harness v1 chạy 30 · scorecard render success+citation+verdict · đổi threshold→verdict** —
  DoD chung, việc **#108** (evalhub, chủ công) + **#106** (replay deterministic) + **#107** (recipe
  `golden_set_ref`/`threshold`). DE **cấp bộ + coordinate**, không viết harness/scorecard/recipe.

---

## 3. Bàn giao AIE-2 (#108) + đọc cả tuần D16→D20 — bằng artifact + tài liệu TRONG kb

- **AIE-2 (#108) hôm nay:** harness v1 đọc bộ **qua `golden_set_ref=callisto-golden-30-v1`** (AIE-2 xác
  nhận không hardcode path → rename file không đụng họ, §0e); DE cấp `golden_set.py` typed để #108
  **import trực tiếp** nếu muốn (khỏi parse yaml). `_contains_phrase` của harness = `re.findall(r"\w+",
  lower)` + so token liên tiếp — golden-set đã mirror đúng luật đó trong test (chống PASS oan cụm-chung);
  ghi rõ để #108 không đổi tokenizer lệch.
- **D17 (#110, DE chủ):** 8 case âm của bộ này **chính là fixture fence** — T1 hai chiều + T6 hai
  tenant. Khi D17 lật `KbSearchService`→`PgKbSearch` + gỡ `test_leak` xfail, chúng là ground-truth
  "câu cross-tenant phải refusal". **Giữ 8 case âm ổn định** từ D16 để D17 chỉ việc nối, không đụng bộ.
- **D18 (#115, DE cấp nhãn tay):** subset golden-set nhận **nhãn tay** để đo agreement vs LLM-judge.
  Thiết kế `golden_set.py` để **thêm được cột `manual_label` cho subset** ở D18 mà không vỡ shape D16 —
  hôm nay **chưa** thêm (không làm sớm), chỉ chừa chỗ (honest-TODO trong docstring).
- **D20 (#125, GATE-2):** bộ này là eval v1 chấm verdict tại gate. **Determinism** (query/nhãn/thứ tự
  case bền, `render_yaml` byte-identical) là điều kiện để replay tại gate cho **cùng verdict** — đó là
  lý do dời vào typed + byte-identical guard ngay D16, không để D20 mới lo. Tên file final `-v1` từ D16
  để gate không phải xử một artifact còn mang nhãn `draft`.
- Ghi ở docstring `golden_set.py` + design-note `docs/design-notes/de-day16.md` trong kb; **không post
  sang evalhub/engine/workbench**.

---

## 4. Bằng chứng (env pinned 3.14 · Postgres sống port 5433 · skip ≠ pass)

- **`git fetch` trước** — D15 PR#16/#17 đã merged (`1e8774f`); cắt `day16/de-golden-set-recorded` trên
  `origin/main` mới (không nền nhánh D15).
- `emit_golden_set.py` chạy → `callisto-golden-30-v1.yaml` **byte-identical** (`git diff` rỗng sau
  re-emit); `build_callisto.py` in manifest 140 chunk/2 tenant + 22+8. Nhóm golden/annotate chạy
  **không-DB** (`StaticKbSearch`, `load_callisto`); nhóm DB (`test_pg_kb`/ingest) cần Docker sống.
- **`git mv` + sửa `test_golden_set.py:29` + emit-path đi CÙNG commit** (AIE-2 dặn) — sau rename, `grep
  -rn 'callisto-handbook-30-draft' packages/kb` phải **rỗng** (không sót tham chiếu tên cũ).
- `docker compose -f docker-compose.test.yml up -d --wait` + 2 DSN (`studio_app`/`studio_owner`)
  **TRƯỚC** khi chạy test/viết báo cáo (SOP; skip ≠ pass — O3.2).
- `test_golden_set.py` xanh: 5 trục cũ giữ nguyên + byte-identical + phủ-biên; **mọi test cũ giữ xanh**.
- `test_leak.py` T1/T6 **vẫn `xfail`** (un-ratchet = D17); `test_search_contract` **vẫn XANH**. Không
  sửa test để pass. `test_grid_inputs.py` (D14) không đụng — vẫn xanh.
- **Toàn suite kb xanh** (cần Docker cho `test_pg_kb`) · `ruff` sạch · `mypy` sạch · `lint-imports` KEPT
  (`golden_set.py` không import chéo tầng; **không** import `studio_evalhub`).
- Interpreter **3.14** (`.venv/bin/python` hoặc `uv run --python 3.14`), **không `python3` trần**
  (local 3.11 — bẫy quen; check lại interpreter trước khi báo mọi SyntaxError).
- Mutation sweep cho glue mới (`golden_set.render_yaml` + guard phủ-biên/byte-identical); code mới không
  phát sinh lỗ.

---

## 5. Còn treo / ngoài phạm vi hôm nay

- **Eval harness v1 + scorecard render + verdict + threshold-flip = #108 (AIE-2, chủ công, evalhub)** —
  KHÔNG làm ở kb. DE cấp bộ + coordinate luật tokenizer/`golden_set_ref`.
- **Replay deterministic 30 case qua interpreter = #106 (AIE-1, engine)** — DE cấp bộ; không viết fixtures engine.
- **`golden_set_ref` + `scorecard_threshold` trong recipe = #107 (SWE, workbench)** — không đụng recipe.
- **Mandatory filter tại retrieval + un-ratchet `KbSearchService` + gỡ `test_leak` xfail + T6 label-spoof
  = D17 (#110)** — KHÔNG làm ở D16. D16 giữ 8 case âm ổn định làm fixture cho D17.
- **Nhãn tay ground-truth subset (agreement) = D18 (#115)** — hôm nay chỉ chừa chỗ shape, không thêm cột.
- **Cost-lineage `tokens→cost` = D19 (#120)** · **spine ghép thật + plan-vs-actual = D20 (#125)**.
- **Rename đã QUYẾT làm ở D16** (§0e) — AIE-2 gỡ blocker, tự-chứa trong lane kb (chỉ `test_golden_set.py:29`
  + emit-path, cùng commit). Không còn treo.
- **Daily-note / evidence `docs/reports`** nằm **ngoài** submodule kb — chỉ làm khi được yêu cầu (chỉ
  đạo: WRITE trong kb).
- **Trạng thái (cập nhật 10/08):** ĐÃ code trên nhánh `day16/de-golden-set-recorded`. ①→⑤ xong:
  `golden_set.py` (typed, render byte-identical) · `git mv` draft→v1 (pure-rename R100) · `emit_golden_set.py`
  + `build_callisto.py` · `EDGE_AXES` + guard · `test_golden_set.py` (+3 guard, dòng 29 đổi path cùng chỗ) ·
  design-note `de-day16.md` + DL-16.1. Bằng chứng: **toàn suite kb 199 passed, 2 xfailed** (T1/T6 giữ cho
  D17), ruff/mypy/lint-imports sạch, mutation `is_refusal` đã bịt. **Chưa commit/push** — chờ review (đúng
  nhịp D14/D15).
