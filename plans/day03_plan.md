---
id: studio.de.day-03-plan
type: day-plan
status: draft
author: DE — Nguyễn Đông Anh
date: 2026-07-22
sprint: s1
day: 3
week_calendar: 1
title: "Kế hoạch Ngày 3 (T4 22/07) — DE: chốt signature kb.search cho AIE-1 + khởi động doc-factory"
---

# KẾ HOẠCH NGÀY 3 — DE (KB pipeline + obs/eval data)
### Thứ Tư 22/07 · Sprint 1 · macro-goal **G2** · luật ngày: **không generalize quá đà**

> Đây là **plan thi công**, chưa phải sản phẩm.
> Nguồn chuẩn: `docs/requirements/week-1/days/day-03.md` · bút DE ngày 2 (`docs/contracts/kb-search.v0.md`, `docs/callisto-doc-schema.md`) · `GITFLOWS.md` §4.

---

## 0. Ranh giới hôm nay (đọc trước khi mở editor)

Brief giao DE **đúng 2 việc** (`day-03.md:39`):

| Việc | Trong scope DE? | Ghi chú |
|---|---|---|
| Cấp **`kb.search` stub signature** để AIE-1 wiring | ✅ | **việc chặn người khác** — ưu tiên tuyệt đối |
| **Bắt đầu** doc-factory 5 doc Callisto (`ankor`/`borea`) | ✅ | "bắt đầu", không phải "xong" — xem D3-2 |
| Interpreter 3-node / node-executor / LLM fixture | ❌ | AIE-1 giữ bút |
| Form tạo agent → `recipe.agent_config` | ❌ | SWE giữ bút |
| Smoke-eval runner skeleton | ❌ | AIE-2 giữ bút |
| **Mở PR #1** | ❌ | DoD của **AIE-1** (`day-03.md:23`), không phải DE |
| Điền thân `KbSearchService.search` | ❌ | Day 4+, và hôm nay làm là **đỏ CI** — xem D3-1 |
| Sửa `packages/contracts/**`, `packages/{engine,workbench,evalhub}/**`, `apps/**` | ❌ | fence-lane người khác |

**Kho ghi được hôm nay: chỉ `packages/kb/**` + `docs/reports/**`** (daily-note). `agentcore-studio-kit` = READ.

> ⚠️ **DE không có DoD "sản phẩm" riêng hôm nay.** Cả 4 mục DoD đầu của `day-03.md:53-56` đều là của SWE/AIE-1. Giá trị của DE ngày 3 đo bằng **AIE-1 có bị chặn hay không**, không phải bằng số file viết ra. `day-03.md:43` ghi thẳng: *"AIE-1 **chờ** signature `kb.search` của DE để wiring"* — và AIE-2 chờ interpreter của AIE-1. Chậm 1 giờ ở DE = chậm dây chuyền 3 người.

---

## 1. Deliverable hôm nay (5 mục)

### D3-1 · Chốt + phát signature `kb.search` cho AIE-1 — **LÀM ĐẦU TIÊN, xong trước 10h**

> **TT:** ✅ **XONG (22/07)** — AIE-1 đã **chốt nhận 4 tham số**. Chữ ký nằm ở `docs/contracts/kb-search.v0.md` (bản **v0.1**). DoD "AIE-1 xác nhận bằng chữ" đã đạt.

#### a) Ranh giới: DE cấp **signature**, AIE-1 tự dựng **vật trả rỗng**

Đọc kỹ hai dòng trong cùng một bảng giao việc:

| Vai | Chữ trong brief |
|---|---|
| **DE** (`day-03.md:39`) | "Cấp `kb.search` **stub signature** (chưa có doc) để AIE-1 wiring" |
| **AIE-1** (`day-03.md:38`) | "`kb-retrieve` (gọi `kb.search` **stub tạm** trả rỗng)" |

→ Cái *trả rỗng* nằm ở **cột AIE-1**. DE giao **hình dạng**, không giao **vật**.

Precedent trong kit ủng hộ cách đọc này: `FakeEmbedding` — double dùng cho CI — sống ở `apps/studio/src/studio_app/providers/fakes.py`, tức **tầng composition**, không nằm trong seam domain (`src/studio_kb/schema.py:21` dẫn thẳng tới đó). P5 chỉ ship **WIRE**, không ship fake.

#### b) Quyết định kỹ thuật phải chốt hôm nay: **3 hay 4 tham số?**

Trong repo đang tồn tại song song hai chữ ký:

| Nơi | Nguồn | Tham số |
|---|---|---|
| `docs/contracts/kb-search.v0.md` §1 | bút DE, D2 | **3** — `query, tenant, top_k` |
| `studio_contracts.kb.KbSearch` (Protocol) | reference mentor | **4** — thêm `section_roles` |
| `studio_kb.search.KbSearchService.search` | seam P5 | **4** |

→ **Chốt: wiring dùng 4 tham số.** Đây là ràng buộc kỹ thuật, không phải sở thích:

`KbSearch` là Protocol 4 tham số (`packages/contracts/src/studio_contracts/kb.py:31-41`), và seam `KbSearchService.search` cũng 4. Một stub 3 tham số hỏng ở **cả hai tầng**:

1. **Lúc chạy (ồn, thấy ngay):** node `kb-retrieve` gọi `search(query, tenant, section_roles, top_k)` — 4 đối số. Stub 3 tham số → **`TypeError` tại call-site**.
2. **Lúc type-check:** `mypy` **có** kiểm chữ ký khi xét Protocol conformance → `x: KbSearch = stub_3_tham_số` báo lỗi.

Wiring 3 tham số hôm nay = **chắc chắn phải sửa call-site lần hai** ở S2.

> ⚠️ **Đừng dùng `isinstance(stub, KbSearch)` làm bằng chứng.** `KbSearch` có `@runtime_checkable`, nhưng `isinstance` với Protocol **chỉ kiểm tên method có tồn tại, KHÔNG kiểm chữ ký**. Một stub 3 tham số vẫn có method tên `search` → `isinstance` trả **`True`**. Đây là bẫy đã biết của Python: dùng nó làm cổng kiểm sẽ **xanh đúng ở trường hợp cần chặn**.

> ✅ **Việc này đóng Q-A** của `kb-search.v0.md` ("có nên nhận `section_roles` ngay từ v0?"). Câu trả lời do thực tế wiring quyết, không cần chờ mentor: **có** — nhận rồi **bỏ qua**.

#### c) Ghi chú wiring gửi AIE-1 — ✅ **đã viết, nằm trong `kb-search.v0.md` §6**

**Quyết định về chỗ đặt:** ban đầu định làm file riêng `kb-search-wiring-d03.md`. Đã **bỏ** cách đó và gộp thẳng vào `kb-search.v0.md` — hai file cùng nói về một chữ ký thì sớm muộn lệch nhau, và AIE-1 sẽ không biết đọc bản nào. Một nguồn duy nhất.

Ba điều đã nói rõ với AIE-1 (v0.1 §6.1–6.3), nếu không họ sẽ thiết kế ngược:

1. **`[]` là kết quả hợp lệ, không phải lỗi.** Node `kb-retrieve` phải đi tiếp sang `llm-step`, không được raise. Đây cũng đúng là hình dạng của **fail-closed** sau này (§5.1: không xác định được phạm vi → trả 0 kết quả) — quen từ bây giờ thì S2 không phải sửa luồng.
2. **`citations` trong trace-event tuần này sẽ rỗng theo.** Báo AIE-2 để runner skeleton không chấm `citation_accuracy` ngày 3 rồi tưởng hỏng.
3. **KHÔNG gọi `KbSearchService`.** Nó raise `NotImplementedError` **có chủ đích**, và `tests/test_search_contract.py:11-14` là một test **XANH** khẳng định đúng điều đó. Cần thứ chạy được thì dùng double phía engine, nhận qua **dependency injection**.

> ⚠️ **Cạm bẫy lớn nhất của ngày:** điền thân `KbSearchService.search` để "giúp AIE-1 chạy được". Làm vậy `test_search_contract.py` **đỏ ngay**, và bạn vừa tiêu mất graded deliverable của chính mình (Day 4+). Nếu thấy mình đang mở `src/studio_kb/search.py` — dừng lại.

**Xong là:** AIE-1 **xác nhận bằng chữ** đã đủ để wiring. Không phải "đã gửi" — mà "đã được xác nhận".

---

### D3-2 · doc-factory Callisto — ✅ **XONG, đủ 5 doc**

**Phạm vi:** `day-03.md:39` giao *"bắt đầu doc-factory **5 doc** Callisto (2 tenant `ankor`/`borea`)"* — con số 5 nằm ngay trong dòng giao việc, nên làm đủ. *(Kế hoạch ban đầu của tôi cắt còn 2–3 doc dựa trên `callisto-doc-schema.md:306` "Nội dung 5 doc viết ở Day 4" — đọc sai trọng tâm; brief mới là nguồn chuẩn.)*

Bộ 5 doc theo đúng thiết kế `callisto-doc-schema.md` §8 — **không chọn lại**:

```
packages/kb/docs/callisto/          25 chunk tổng
├── ankor-leave-001.md      ✅ 5 chunk · public          (cặp phát hiện rò rỉ)
├── borea-leave-001.md      ✅ 5 chunk · public          (cặp phát hiện rò rỉ)
├── ankor-expense-001.md    ✅ 5 chunk · public+finance  (doc nhiều section)
├── ankor-salary-001.md     ✅ 5 chunk · hr              (mồi SC-05 chéo vai)
└── borea-expense-001.md    ✅ 5 chunk · finance         (mồi SC-04 chéo tenant)
```

**Thứ tự ưu tiên có lý do, không phải theo số:**

- **#1 + #4 trước** vì đó là **cặp phát hiện rò rỉ** (`callisto-doc-schema.md:276-278`): cùng chủ đề nghỉ phép, **nội dung khác hẳn**. Không có cặp này thì fence hở mà test vẫn xanh — tức là cả bộ test mất răng.
- **#2 tiếp** vì nó là doc **nhiều section** duy nhất trong bộ. Nó là thứ duy nhất kiểm chứng được luật "1 chunk = đúng 1 `section_role`" (§5) và hệ quả "**1 doc n section = n lời gọi `index()`**" (§5b).

Mỗi doc bám đúng thiết kế D2, **không tự chế**:

| Luật | Neo |
|---|---|
| front-matter **đúng 3 field** `doc_id/tenant/section` | §2 — đã cân nhắc rồi bỏ `title`/`author`/`tags` |
| cắt theo heading `##`, override `section` tại chỗ khi cần | §5 |
| `chunk_id = {doc_id}#c{n}` (không dùng UUID) | §6 |
| `section` ∈ `{public, hr, finance, engineering}` | §3 — **từ vựng đóng** |
| 100% tự viết · 0 PII · chỉ `ankor`/`borea` + `alice`/`bob`/`carol` | §9 |
| số liệu **bịa có chủ đích**, dễ nhận ra khi rò (20 triệu vs 77 triệu) | §9 |

**Xong là:** thư mục tồn tại + ≥2 doc viết xong + tự đọc lại xác nhận được `ankor-leave-001` và `borea-leave-001` trả lời **khác nhau thật**, không phải cùng nội dung đổi mỗi tên tenant.

---

### D3-3 · Cập nhật `docs/contracts/kb-search.v0.md` — ✅ **XONG (v0.1)**

Làm cùng lúc với D3-1 thay vì để cuối ngày, vì AIE-1 cần đọc bản đã cập nhật chứ không phải bản D2.

| Đã làm | Chi tiết |
|---|---|
| **§1 viết lại** | chữ ký v0 nâng **3 → 4 tham số**, thêm shape `KbSearchResultItem` + quy ước trả `[]` |
| **§2** | chữ ký đích giờ **giống hệt §1** — v0 và freeze chung một chữ ký, chỉ khác hành vi |
| **§3 mới** | vì sao 4 chứ không 3 (`TypeError` tại call-site + mypy fail + seam đã 4 sẵn) và cảnh báo bẫy `isinstance` |
| **§4** | bảng đường nâng viết lại: **chỉ siết hành vi, không đổi chữ ký** |
| **§6 mới** | ghi chú wiring cho AIE-1, gộp từ file riêng đã bỏ |
| **§9** | Q-A đánh ✅ ĐÓNG; thêm **Q-D** hỏi AIE-1 về double |
| **§10** | thêm dòng v0.1, **giữ nguyên dòng v0** ghi rõ bản cũ là 3 tham số |

Giữ nguyên ba luật fence (§5) và phần dữ liệu bên dưới (§7) — phần mạnh nhất của bản D2, không đụng.

> ⚠️ **Đây là sửa một deliverable D2 đã push** (`d5c335d` lên remote với bản 3 tham số). Hợp lệ: file đóng dấu `NOT-FROZEN`, và bảng Lịch sử sinh ra để ghi đúng loại thay đổi này. Nhưng khi báo mentor phải nói rõ **đổi có chủ đích để đóng Q-A**, không phải viết lại cho khớp thực tế sau khi lỡ tay.

---

### D3-4 · Daily-note D3 — ⚠️ **đang có nợ, xem D3-5 trước**

Đặt đúng chỗ: submodule `docs/reports` (repo `agentcore-report`), **KHÔNG** phải trong `packages/kb` — `day02_plan.md:199-208`.

Quy ước tên file lấy theo đồng đội đã push: `daily-notes/YYYY-MM-DD-<github-username>.md` → của DE là **`2026-07-22-DongAnh2704.md`** (username lấy từ `GITFLOWS.md:78`).

```bash
cd docs/reports
git checkout main && git pull        # ⚠️ submodule này đang DETACHED + behind 7
cp templates/daily-note.md daily-notes/2026-07-22-DongAnh2704.md
```

Giữ nguyên các heading `## ` (pipeline đọc theo heading):
- **Bối cảnh & câu hỏi** ← Q1–Q4 §7 dưới.
- **Việc đã làm** ← commit doc-factory + ghi chú wiring.
- **Contract / integration** ← chốt 4 tham số với AIE-1, thông báo `citations` rỗng cho AIE-2.
- **Quyết định kỹ thuật** ← vì sao **không** ship `StubKbSearch`, vì sao 4 tham số.
- **Blocker / escalate** ← kỷ luật 2-4-8h.

---

### D3-5 · Trả 3 món nợ từ D2 (30') — **làm buổi sáng**

Ba thứ lệch giữa plan D2 và thực tế repo. Gate D10 chấm theo **artifact có thật**, nên đừng để plan nói một đằng repo một nẻo.

| # | Nợ | Bằng chứng | Xử lý | TT |
|---|---|---|---|---|
| 1 | **Daily-note D2 chưa push** | `docs/reports` origin/main chỉ có `2026-07-20-TranBaDat2607`, `2026-07-21-TranBaDat2607`, `2026-07-21-dholmes0207` — **không có file nào của DE** | Đây là **DoD của day-02**. Chuyển `packages/kb/daily_note.md` → `docs/reports/daily-notes/2026-07-21-DongAnh2704.md`, push. | ✅ commit `96ccc84` |
| 2 | **`daily_note.md` nằm sai chỗ** | untracked ở gốc `packages/kb/` | Đã `mv` sang `docs/reports` cùng lúc với (1) — không còn bản trùng. | ✅ |
| 3 | **`docs/question-batch-d02.md` không tồn tại** | `day02_plan.md:182` đặt đích danh tên file này, nhưng `git ls-files` không có | **Không tạo file mới.** Q1–Q6 đã có ở 2 nơi (bảng `day02_plan.md` §D2-6 + daily-note D2 đã push); thêm bản thứ ba là ba nguồn sẽ lệch nhau. Đã sửa `day02_plan.md` ghi rõ nơi ở thật. | ✅ |
| 4 | `.gitignore` của kb **chưa có `.DS_Store`** | `git status` ở kb luôn bẩn; §3 có bước `git add -A` nên dễ lỡ tay commit rác macOS lên repo chung. *(Không nguồn nào yêu cầu — tự thêm.)* | Thêm 1 dòng vào `.gitignore`. | ✅ |

> **Nguyên tắc rút ra từ (3)** — dùng lại cho mọi artifact sau: question-batch không phải deliverable độc lập, nó là *bằng chứng đã hỏi trước khi code*. Bằng chứng mạnh nhất là **bản ghi đã push có timestamp** (daily-note), không phải file `.md` rời có thể viết bổ sung sau. Khi plan và thực tế lệch nhau, **sửa plan cho khớp thực tế** rẻ hơn là đẻ thêm file cho khớp plan.

---

## 2. Thứ tự thực thi (timebox)

| Slot | Việc | Ra cái gì | TT |
|---|---|---|---|
| **Sáng 1 (30') — sớm nhất** | **D3-1** chốt 4 tham số + **D3-3** viết vào `kb-search.v0.md` | chữ ký chốt bằng văn bản | ✅ |
| Sáng 2 | Gửi `kb-search.v0.md` cho AIE-1 | **AIE-1 đã chốt nhận 4 tham số** | ✅ |
| Sáng 3 (30') | **D3-5** trả nợ D2 (daily-note D2 + question-batch + `.gitignore`) | hết treo artifact | ✅ |
| Chiều 1–2 | **D3-2**: đủ **5 doc** Callisto, 25 chunk | KB stub tuần 1 xong | ✅ |
| Chiều 3 | **D3-4** daily-note D3 | `2026-07-22-DongAnh2704.md` | ✅ đã viết, **chưa push** |
| Cuối ngày | commit + push `packages/kb`, rồi push daily-note | DoD | ⬜ **còn lại** |
| *(không hạn)* | Báo AIE-2 chuyện `citations` rỗng · chờ AIE-1 trả lời **Q-D** | seam sạch | 🔶 |

> D3-3 kéo lên làm cùng D3-1 (kế hoạch ban đầu để cuối ngày) vì AIE-1 phải đọc bản v0.1, không phải bản D2.

---

## 3. Luồng git (GITFLOWS §4)

**Nền đã sạch, bắt tay làm được ngay.** `packages/kb` đang ở nhánh `main` tại `acf9d05`, khớp `origin/main` và khớp con trỏ submodule của repo cha — đã fast-forward từ `d5c335d` sáng 22/07.

```bash
cd packages/kb
git status -sb               # kỳ vọng: "## main...origin/main", KHÔNG có [behind N]

# ... làm D3-1 .. D3-5 ...

git add -A
git commit -m "docs(kb): D3 — chốt chữ ký wiring kb.search (4 tham số) + khởi động doc-factory Callisto"
git push
```

Test chạy **từ repo cha** (kb không test độc lập được):

```bash
cd /Users/nguyendonganh/agentcore-studio-kit
uv run pytest packages/kb/tests -q
```

**Trạng thái test phải KHÔNG ĐỔI so với đầu ngày** — đặc biệt `test_search_contract.py` vẫn xanh. Hôm nay DE không đụng `src/`.

**Bump con trỏ ở repo cha:** không phải việc của DE (GITFLOWS §5 — mentor). Chỉ push ở kb là đồng đội `git submodule update --remote packages/kb` thấy được.

---

## 4. Tự kiểm trước khi push

- [ ] `git status -sb` ở kb ra đúng `## main...origin/main` — trên **branch**, không detached, không `[behind N]`.
- [ ] **`src/studio_kb/search.py` không đổi 1 dòng nào** — kiểm bằng `git diff --stat src/`.
- [ ] `test_search_contract.py` vẫn **xanh**.
- [ ] Chỉ file trong `packages/kb/**` bị đổi; `packages/contracts/**` không đụng.
- [ ] Doc Callisto: front-matter **đúng 3 field**, không phát sinh field thứ 4.
- [ ] `section` chỉ thuộc `{public, hr, finance, engineering}`.
- [ ] 0 PII · chỉ `ankor`/`borea` + `alice`/`bob`/`carol` · số liệu bịa dễ nhận ra khi rò.
- [ ] `ankor-leave-001` vs `borea-leave-001` **khác nội dung thật**, không phải copy đổi tên tenant.
- [ ] **AIE-1 đã xác nhận** nhận đủ signature (đây là DoD thật của DE hôm nay).
- [ ] Daily-note **D2** đã push lên `docs/reports` (nợ D3-5).
- [ ] Không copy nguyên văn tài liệu mentor/rubric — pre-commit `nda-denylist` sẽ chặn.

---

## 5. Ngoài phạm vi hôm nay (làm sớm = **bị chặn**, không phải được cộng điểm)

Interpreter / node-executor · form→recipe · smoke-eval runner · **điền thân `KbSearchService.search`** · `chunker`/`embed_invoke`/`index` chạy thật · nội dung đủ 5 doc (Day 4) · fence chunk-level + leak-test T1/T6 (S3) · trace sink · cost dashboard · PR #1 (của AIE-1).

---

## 6. Đối chiếu DoD của brief (`day-03.md:52-57`)

| DoD | Ai gánh | DE liên quan thế nào |
|---|---|---|
| Form xuất `agent_config` đúng shape recipe v0 | SWE | ❌ |
| 3 node chạy đúng thứ tự `kb-retrieve→llm-step→tool-call` | AIE-1 | **gián tiếp** — node đầu tiên cần signature từ D3-1 |
| Node-executor có docstring input/output | AIE-1 | ❌ |
| PR #1 mở | AIE-1 | ❌ |
| **Daily-note D3** | **mọi vai, gồm DE** | ✅ D3-4 |

---

## 7. Câu hỏi còn mở

| # | Hỏi ai | Nội dung | Nghiêng về |
|---|---|---|---|
| **Q-D** *(đã gửi trong `kb-search.v0.md` §9)* | **AIE-1** | Bạn cần một **object import được** (`StubKbSearch` ship trong `packages/kb`) hay chỉ cần **signature** để tự dựng double bên engine? | **chỉ signature** — đúng cột brief `day-03.md:38-39` + precedent `FakeEmbedding` nằm ở tầng composition. *Nếu AIE-1 cần thật:* đặt ở `src/studio_kb/stubs.py`, **class riêng**, tuyệt đối không đụng `KbSearchService`. Test kèm phải **gọi thật đủ 4 keyword-arg và assert trả `[]`** (hoặc so `inspect.signature`) — **không** dùng `isinstance` (xem cảnh báo ở D3-1b: nó xanh cả với stub sai). |
| **Q2** | SWE + mentor | *(chuyển tiếp từ `callisto-doc-schema.md` §10 Q1)* Từ vựng `section_role` 4 giá trị chốt được chưa? **Hôm nay bắt đầu viết doc là bắt đầu đóng đinh giá trị này** — trả lời muộn thì phải sửa lại doc. | dùng 4 giá trị `public/hr/finance/engineering` |
| **Q3** | AIE-2 | Tuần này `kb.search` trả `[]` nên `citations` rỗng. Runner skeleton có nhánh xử lý "0 citation" chưa, hay sẽ coi là fail? | coi `[]` là **hợp lệ**, chưa chấm `citation_accuracy` tới Day 4 |
| **Q4** | mentor | *(chuyển tiếp Q1/Q2 của D2 — chưa có trả lời)* `DESCOPE.md` đặt ở đâu cho bản team; và "bút v0" là file nháp trong `packages/kb` hay delta PR lên `contracts`? | giữ nguyên phương án mặc định đã ghi ở `day02_plan.md` |

> ✅ **Q3 của D2 (Python 3.12 hay 3.14) coi như đã đóng:** `pyproject.toml:5` yêu cầu `>=3.14`, và repo requirements vừa có 2 commit "Python 3.14 unify". Không cần hỏi lại.

---

*Plan D3 — DE, 22/07/2026. Sửa lại khi AIE-1 trả lời Q1 (ảnh hưởng trực tiếp D3-1) và khi mentor trả lời Q2.*
