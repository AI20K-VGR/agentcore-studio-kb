---
id: studio.de.day-02-plan
type: day-plan
status: draft
author: DE — Nguyễn Đông Anh
date: 2026-07-21
sprint: s1
day: 2
week_calendar: 1
title: "Kế hoạch Ngày 2 (T3 21/07) — DE: scaffold + 2 interface v0 + question-batch"
---

# KẾ HOẠCH NGÀY 2 — DE (KB pipeline + obs/eval data)
### Thứ Ba 21/07 · Sprint 1 · macro-goal **G1→G2** · luật ngày: **hỏi rõ trước khi code (clarify-first)**

> Đây là **plan thi công**, chưa phải sản phẩm.
> Nguồn chuẩn: `docs/requirements/week-1/days/day-02.md` · `../../docs/requirements/00-orientation/umbrella-contract.md` §2/§3/§4/§7 · `week-1/README.md` §5/§6 · `GITFLOWS.md` §4.

---

## 0. Ranh giới hôm nay (đọc trước khi mở editor)

| Việc | Trong scope DE? | Ghi chú |
|---|---|---|
| Bút v0 **trace-event** (§3.2) | ✅ | day-02 §Giao việc: "DE giữ 2" |
| Bút v0 **`kb.search(query, tenant, top_k)`** (§3.3) | ✅ | chữ ký v0 ghi thẳng trong brief |
| Phác **schema doc Callisto** + bảng chunk/index | ✅ | brief giao đích danh |
| Chốt shape **5 smoke-case** cùng AIE-2 | ✅ | DE là người **cấp `expected`** (nhãn tay) |
| recipe v0 (§3.1) | ❌ | SWE giữ bút |
| scorecard v0 (§3.4) | ❌ | AIE-2 giữ bút |
| interpreter loop / node-executor / fixture VCR | ❌ | AIE-1 |
| Sửa `packages/contracts/**` | ❌ | mentor-approval, PR ở repo `agentcore-studio-contracts` (GITFLOWS §5) |
| Sửa `packages/{engine,workbench,evalhub}/**`, `apps/**` | ❌ | fence-lane người khác |

**Kho ghi được hôm nay: chỉ `packages/kb/**`** (submodule `agentcore-studio-kb`). `agentcore-studio-kit` = READ.

> ⚠️ DoD ghi "**4** interface v0" và "scaffold **4** quadrant" — đó là **DoD cấp team** (4 bút, 4 người, xác nhận ở day-02 §Output chung/riêng). Phần DE chịu trách nhiệm là **2/4**. Không viết hộ recipe/scorecard.

---

## 1. Deliverable hôm nay (6 mục)

### D2-0 · Đọc đề "paved-path trọn vòng đời" (30')
Đọc lại 3 chặng theo đúng thứ tự nhân-quả, viết **3 câu** vào daily-note bằng lời của mình:
`authoring (form→recipe)` → `fence (chặn rò rỉ TẠI TẦNG TRUY XUẤT)` → `eval-gate (cổng kiểm định CHẶN publish)`.
Mục đích: hiểu **vì sao 2 interface của DE nằm ở đúng 2 điểm gãy** — `kb.search` là nơi fence sống, `trace-event` là nơi cost/citation chảy ra eval-gate. Đây cũng là bài teach-back cuối tuần.

---

### D2-1 · Scaffold `packages/kb` cho phần DE
**Làm gì:** dựng khung thư mục cho 3 lát việc tuần 1 của DE (doc-factory · kb.search · trace sink) — **khung + docstring + TODO, chưa code logic**.

```
packages/kb/
├── day02_plan.md                    # file này
├── DESCOPE.md                       # D2-2 (phần KB của DE + link bản team)
├── docs/
│   ├── contracts/
│   │   ├── trace-event.v0.md        # D2-3a  ← bút DE
│   │   └── kb-search.v0.md          # D2-3b  ← bút DE
│   ├── callisto-doc-schema.md       # D2-4
│   ├── format.md                    # D2-5 (định dạng golden-set + điều chốt với AIE-2)
│   └── question-batch-d02.md        # D2-6
└── src/studio_kb/                   # ĐÃ CÓ SẴN (seam P5) — hôm nay KHÔNG đụng
```

**Vì sao không đụng `src/`:** `schema.py` / `search.py` / `pipeline.py` **đã có seam sẵn** — `KbSearchService.search` và `KbPipeline.{chunker,embed_invoke,index,consent_purge,re_index}` đều `NotImplementedError` **có chủ đích**, kèm docstring ghi rõ contract phải thoả. Hôm nay việc của DE là **đọc seam đó để 2 bản v0 khớp với nó**, không viết đè. Điền thân hàm là việc Day 4 trở đi.

**Xong là:** cây thư mục tồn tại; `uv run pytest packages/kb/tests -q` (chạy **từ repo cha**) không đổi trạng thái so với đầu ngày.

---

### D2-2 · `DESCOPE.md` — 4 nấc cắt giảm
**Làm gì:** viết 4 nấc theo **umbrella §7 INV-7** (không tự chế nấc mới), mỗi nấc kèm 1 dòng "walking-skeleton vẫn sống vì…".

| Nấc | Cắt gì | Skeleton còn sống nhờ | Neo | Chủ nấc |
|---|---|---|---|---|
| 1 | KB thật → **KB stub tĩnh 5 doc** | `kb.search` vẫn trả `chunk_id` → citation vẫn chấm được | §4 nấc **L0** | **DE** |
| 2 | canvas React Flow → **form + Mermaid** | recipe vẫn sinh ra được → interpreter vẫn đọc được | §7 INV-7 | SWE |
| 3 | LLM-judge → **exact-match scorer** | scorecard vẫn ra PASS/FAIL bằng success + citation | §3.4 descope-guard | AIE-2 |
| 4 | cost dashboard → **bảng CLI** | cost-lineage 3-surface vẫn cùng 1 số, chỉ đổi cách hiển thị | §3.2 | DE |

**Phần DE phải viết kỹ (nấc 1 + nấc 4 là của mình):**
- **Nấc 1** — đường lui trên **storage ladder §4**: `L1 (Postgres/SQLite + index per-tenant)` → tụt về `L0 (in-memory + trace JSONL/SQLite, KB stub tĩnh 5 doc)`.
  **Điều kiện kích hoạt:** hết Day 4 mà `kb.search` chưa trả được cited chunks → tụt nấc, không cố.
- **Nấc 4** — dashboard → bảng CLI: **cost-lineage invariant không được cắt theo**. Cắt cách *hiển thị*, không cắt *nguồn số*.

> ⚠️ **Điểm cần hỏi (→ Q1):** day-02 xếp `DESCOPE.md` vào **Output chung** của team, nhưng DE chỉ có WRITE ở `packages/kb`. Kế hoạch tạm: DE viết bản **đầy đủ 4 nấc** trong `packages/kb/DESCOPE.md`, đánh dấu rõ nấc nào DE own, và đề xuất team gộp về 1 bản ở repo cha.

**Xong là:** 4 nấc × (cắt gì · skeleton sống vì · điều kiện kích hoạt · chủ nấc), + câu "8 bước demo VẪN SỐNG" cho từng nấc.

---

### D2-3 · Hai interface v0 (bút DE)

Tên file/interface **khớp umbrella §3**: `trace-event` (§3.2) · `kb.search` (§3.3). Cả hai đóng dấu **"v0 — CHƯA FREEZE (freeze D11)"**.

#### a) `docs/contracts/trace-event.v0.md`
- Lấy **hình dạng tối thiểu** §3.2 làm gốc, chia field thành 2 nhóm:

| Nhóm | Field | Lý do |
|---|---|---|
| **Dùng thật tuần 1** | `event_id · run_id · agent_id · tenant · node_id · node_type · ts · tokens{prompt,completion} · cost` | đủ để trace sink SQLite + reader timeline chạy (week-1 §6) |
| **Để trống tới S2** | `inputs_hash · outputs · citations[]` | `citations` chỉ có nghĩa khi `kb-retrieve` chạy thật (Day 4) |

- Viết **2 invariant** bằng lời của mình:
  - **cost-lineage:** `cost` ở UI test **==** trace **==** dashboard — **cùng 1 nguồn, cùng 1 số**. Lệch = fail (không phải warning).
  - **ordering:** `ts` monotonic trong 1 `run_id`; reader in timeline **0-gap**.
- `node_type` ∈ **6 loại đóng** (`kb-retrieve · llm-step · condition · tool-call · hitl-pause · end`) — ghi thẳng enum; **CẤM** loại thứ 7.
- `tenant` **NOT NULL** (INV-1) — ghi rõ đây là ràng buộc dữ liệu, không phải field tuỳ chọn.
- **Seam với AIE-1:** AIE-1 hôm nay phác `execute(node, ctx) -> ctx'`. Ghi 1 mục **"ai emit, emit lúc nào"**: mỗi lần `execute` trả `ctx'` → emit đúng **1** trace-event. Nói rõ những gì DE cần AIE-1 đặt vào `ctx'` (`tokens`, `cost`, `citations`) để không phải sửa chữ ký giữa tuần.
- **Bảng delta v0 ↔ reference:** `packages/contracts/src/studio_contracts/trace.py` đã có bản đầy đủ (`TraceEvent`, `Tokens`, `node_type: NodeType`). Ghi delta — **không sửa file đó**.

#### b) `docs/contracts/kb-search.v0.md`
- **Chữ ký v0 tuần 1** (đúng như brief giao):
  ```
  kb.search(query, tenant, top_k) -> [{chunk_id, text, score, tenant}]     # CHƯA fence
  ```
- **Forward-compat note** (bắt buộc): bản freeze §3.3 là
  ```
  kb.search(query, tenant, section_roles, top_k) -> [{chunk_id, text, score, tenant, section_role}]
  ```
  Nêu đường nâng: **thêm** `section_roles` (resolve server-side) + **thêm** `section_role` vào item → v0 là **tập con hợp lệ** của bản freeze, không phải chữ ký mâu thuẫn. Chỉ thêm, không đổi tên/nghĩa khoá đã có.
- Ghi trước **3 luật sẽ ràng buộc từ S2/S3** (để AIE-1 không thiết kế ngược ngay từ Day 3):
  1. filter **TẠI RETRIEVAL**, fail-closed — chunk ngoài scope **không bao giờ** rời khỏi hàm;
  2. `section_roles` resolve **server-side** — client tự khai là *yêu cầu*, không phải *quyền*; đây chính là thứ chặn **T6 label-spoof**;
  3. **CẤM** trả hết rồi nhờ LLM lọc — anti-pattern bị cấm bằng chữ.
- **Delta so với seam đã có:** `studio_contracts.kb.KbSearchResultItem` (đã có `section_role`) + `KbSearchService.search` (đã có `section_roles` trong chữ ký). Ghi rõ: v0 **không xoá** field khỏi reference, chỉ **chưa dùng** — tránh hiểu nhầm là DE đề xuất bỏ fence.

**Xong là:** mỗi file có: chữ ký/schema · bảng field (v0 vs sau) · invariant · delta vs reference · dấu v0-chưa-freeze · mục "ai consume" (AIE-1 cho cả hai, AIE-2 cho `citations`).

---

### D2-4 · Sơ đồ tài liệu Callisto + bảng chunk/index
**Làm gì:** phác **hình dạng dữ liệu**, chưa sinh doc.

1. **Front-matter doc** (mỗi file `.md` trong doc-factory):
   ```yaml
   doc_id: str
   tenant: ankor | borea        # NOT NULL — nguồn của cột tenant_id
   section: str                 # → section_role
   title: str
   ```
2. **Bảng chunk/index** — bám đúng `kb.chunks` đã có trong `src/studio_kb/schema.py`, **không tự chế cột mới**:
   `chunk_id · tenant_id (NOT NULL) · section_role (NOT NULL) · text · embedding vector(EMBEDDING_DIM=8) · created_at`.
3. **Luật cắt đoạn** (đã ghi ở docstring `KbPipeline.chunker`): **1 chunk = đúng 1 `section_role`** — ranh giới chunk **không** được bắc qua 2 section. Vẽ ví dụ 1 doc → 3 chunk để chốt hiểu.
4. **Sơ đồ đường đi** (mermaid hoặc ASCII) — đây là phần quan trọng nhất của mục này:
   ```
   front-matter (tenant/section)  →  chunk row (tenant_id/section_role NOT NULL)
                                  →  kb.search filter  →  fence-data (leakage=0)
   ```
   Viết 1 câu: *"2 cột kia NOT NULL vì đó là thứ duy nhất fence bám vào — NULL = fence hở."*

**Xong là:** 1 file có 1 doc mẫu + bảng cột + sơ đồ đường đi + luật chunk-không-bắc-cầu.

---

### D2-5 · Chốt shape 5 smoke-case cùng AIE-2 (DE cấp `expected`)
**Làm gì:** ngồi cùng AIE-2 chốt **hình dạng**, chưa cần nội dung.

- Đề xuất shape:
  ```yaml
  - case_id: str
    query: str
    tenant: ankor | borea        # ← hứng từ UI
    section_roles: [str]         # ← hứng từ UI, khớp tham số kb.search §3.3
    expected_tenant: str         # ← nguồn KB của câu hỏi; lệch `tenant` ⟹ phải refusal
    expected: str                # ← NHÃN TAY của DE (ground-truth)
    expected_citation: [str]     # ← để AIE-2 tính citation_accuracy, không phải đoán
  ```
  Khớp ngược với scorecard v0 của AIE-2 (`{case_id, expected, actual, success, citation_accuracy}`) — `expected` là khớp nối giữa 2 bút.
- **Chốt quyền sở hữu:** DE **sinh + gán nhãn**, AIE-2 **đọc** (một doc-factory nuôi cả KB lẫn golden-set — umbrella §2).
- **Chốt trước 1 case "âm":** query có đáp án **chỉ ở tenant kia** → `expected` = **refusal**, không hallucinate. Case này là mầm INV-1, dùng lại được nguyên si ở leak-test T1/T6 (S3).
- Ghi kết quả vào `docs/format.md` + daily-note mục *Contract / integration*.

**Xong là:** shape đã thống nhất **bằng văn bản** với AIE-2 (không phải "nói miệng"). Nội dung 5 case viết Day 4.

---

### D2-6 · Question-batch ≥3 câu — **gửi TRƯỚC khi code** (DoD)

File: `docs/question-batch-d02.md`. Mẫu mỗi câu: **hỏi · vì sao chặn · phương án mặc định nếu không kịp có trả lời**.

| # | Câu hỏi | Vì sao chặn | Mặc định nếu chưa có trả lời |
|---|---|---|---|
| **Q1** | `DESCOPE.md` là **Output chung** (day-02) nhưng DE chỉ WRITE ở `packages/kb` — bản team đặt ở repo cha (ai commit?) hay mỗi owner giữ 1 bản trong quadrant mình? | Sai chỗ → gate Day 10 không tìm thấy artifact chung | Viết đủ 4 nấc trong `packages/kb/DESCOPE.md`, đánh dấu nấc DE own |
| **Q2** | `packages/contracts` **đã có sẵn** `trace.py` + `kb.py` bản đầy đủ. Vậy "bút v0 của DE" = viết **draft mới** trong `packages/kb/docs/contracts/`, hay đề xuất **delta** lên bản reference qua PR repo contracts? | Sai chỗ đặt → D11 freeze ceremony không có artifact để ký | Draft mới trong `packages/kb/docs/contracts/` + bảng delta |
| **Q3** | Python **3.12** (day-01 + week-1 §7) vs **3.14** (`.venv` hiện tại + `packages/kb/README.md` + `pyproject` `requires-python >=3.12`) — bản nào là chuẩn để chấm? | Env lệch → CI/pytest evidence không dùng được | Theo `.venv` 3.14 đang chạy được |
| **Q4** | `kb.search` v0 bỏ `section_roles`, nhưng seam `KbSearchService.search` **đã có sẵn** tham số đó và AIE-1 nối `kb-retrieve` từ Day 3–4. Có nên nhận `section_roles` ngay ở v0 (nhận và **bỏ qua**) để khỏi đổi call-site 2 lần? | Đổi chữ ký sau khi AIE-1 đã nối = phá integration giữa tuần | Giữ v0 thin đúng brief + forward-compat note |
| **Q5** | Trace sink tuần 1: **SQLite** (§4 L1 + week-1 §5) hay **Postgres** (kit đang dựng pgvector + RLS + `docker/postgres-init`)? | Chọn sai → viết lại sink ở Day 5 | Bám Postgres đang có sẵn trong kit (RLS S3 sẽ cần) |
| **Q6** | `packages/kb/tests/test_leak.py` là **red-by-design**. Trong DoD "CI xanh 100% fixtures", test này tính là `xfail`/`skip`, hay CI được phép đỏ đúng ở test đó? | Ảnh hưởng cách đọc CI evidence cả tuần | Hỏi trước, không tự đổi trạng thái test |

**Xong là:** ≥3 câu (đang có 6) đã **GỬI** — không phải chỉ viết ra file. Gửi buổi sáng để kịp nhận trả lời trong ngày.

---

## 2. Daily-note D2

**Đặt đúng chỗ:** daily-note **KHÔNG** nằm trong `packages/kb`. Nó thuộc submodule `docs/reports`
(repo `agentcore-report` — write-surface của TTS):

```bash
cd docs/reports
git checkout main            # ⚠️ submodule này cũng đang DETACHED HEAD
cp templates/daily-note.md daily-notes/2026-07-21-de.md
# ... điền ...
git add -A && git commit -m "docs(daily-note): D2 — DE" && git push
```

Copy `templates/daily-note.md` → điền, **giữ nguyên các heading `## `** (pipeline đọc theo heading):
- **Bối cảnh & câu hỏi** ← Q1–Q6 (đây là evidence proactive-communication, phần chấm thật).
- **Việc đã làm** ← link commit/PR scaffold + CI run.
- **Contract / integration** ← 2 interface v0 + shape 5 case đã chốt với AIE-2 + seam `ctx'` với AIE-1.
- **Quyết định kỹ thuật** ← vì sao chọn v0 thin + forward-compat thay vì bê nguyên §3.3 vào tuần 1.
- **Blocker / escalate** ← áp kỷ luật 2-4-8h.

---

## 3. Thứ tự thực thi (timebox)

| Slot | Việc | Ra cái gì |
|---|---|---|
| Sáng 1 (30') | Đọc paved-path + đọc seam `src/studio_kb/*.py` | D2-0, hiểu delta v0 ↔ reference |
| **Sáng 2 (45')** | **Viết + GỬI question-batch Q1–Q6** | D2-6 — **làm sớm nhất**, để có thời gian nhận trả lời |
| Sáng 3 | Scaffold thư mục + `DESCOPE.md` | D2-1, D2-2 |
| Chiều 1 | `trace-event.v0.md` | D2-3a |
| Chiều 2 | `kb-search.v0.md` | D2-3b |
| Chiều 3 | `callisto-doc-schema.md` | D2-4 |
| Chiều 4 | Sync AIE-2 chốt shape 5 case | D2-5 |
| Cuối ngày | Commit + push + daily-note D2 | DoD |

---

## 4. Luồng git (GITFLOWS §4) — ⚠️ có bẫy

`packages/kb` hiện đang ở **DETACHED HEAD** (mặc định của submodule). **Commit ở trạng thái này sẽ mất.** Bắt buộc về nhánh trước:

```bash
cd packages/kb
git checkout main            # ⚠️ BẮT BUỘC — đang detached
git pull

# ... tạo các file D2-1..D2-6 ...

git add -A
git commit -m "docs(kb): D2 — plan + DESCOPE 4 nấc + trace-event/kb.search v0 + question-batch"
git push                     # push vào repo agentcore-studio-kb
gh pr create                 # (tuỳ chọn) PR để mentor review
```

Test phải chạy **từ repo cha** (kb không test độc lập được — cần `studio_contracts` + `apps/studio` + Postgres):

```bash
cd /Users/nguyendonganh/agentcore-studio-kit
uv run pytest packages/kb/tests -q
```

**Bump submodule ở repo cha:** chỉ làm **sau khi** đã push ở kb, và chỉ khi cần đồng đội thấy ngay —
`git add packages/kb && git commit && git push` ở repo cha.

---

## 5. Tự kiểm trước khi mở PR

- [ ] `packages/kb` đang ở **branch `main`**, không phải detached HEAD.
- [ ] Chỉ file trong `packages/kb/**` bị đổi — `git status` ở repo cha sạch (trừ dòng bump submodule).
- [ ] `src/studio_kb/*.py` **không đổi** — hôm nay là ngày viết giao kèo, không phải ngày code.
- [ ] Không có `node_type` thứ 7 ở bất kỳ đâu.
- [ ] Mọi file giao kèo có nhãn **"v0 — CHƯA FREEZE (freeze D11)"**.
- [ ] 4 nấc DESCOPE, nấc nào cũng có câu "skeleton vẫn sống vì…" + điều kiện kích hoạt.
- [ ] Question-batch đã **gửi**, không chỉ viết.
- [ ] 100% synthetic: chỉ `ankor`/`borea`, `alice`/`bob`/`carol`; 0 PII; `nda-denylist` + secret-scan pre-commit xanh.
- [ ] **Không copy nguyên văn** tài liệu mentor/rubric/answer-key vào file commit — viết bằng lời của mình (pre-commit `nda-denylist` sẽ chặn).

---

## 6. Ngoài phạm vi hôm nay (làm sớm = **bị chặn**, không phải được cộng điểm)
Ingest→chunk→embed→index chạy thật · fence chunk-level + leak-test · code trace sink · **nội dung** 5 golden-case · vector store L2 · cost dashboard · eval-gate · LLM-judge.

---

## 7. Đối chiếu DoD của brief

| DoD (day-02) | Mục trong plan | Cấp |
|---|---|---|
| Scaffold 4 quadrant push, tách đúng owner | D2-1 (phần kb) | team — DE lo `packages/kb` |
| `DESCOPE.md` 4 nấc viết sẵn | D2-2 (+Q1) | chung |
| 4 interface v0 tên khớp umbrella §3 | D2-3 (2/4 của DE) | team — DE lo trace-event + kb.search |
| Question-batch ≥3 câu gửi mentor **trước khi** code | D2-6 (6 câu) | brief xếp *chung* — DE vẫn nộp batch riêng của mình |
| Daily-note D2 | §2 → `docs/reports/daily-notes/` | riêng |
| *(brief §Cách cộng tác)* chốt shape 5 smoke-case với AIE-2 | D2-5 | riêng (DE cấp `expected`) |

---

*Plan v2 — DE, 21/07/2026. Cập nhật sau khi `day-02.md` chính thức publish. Sửa lại khi mentor trả lời Q1–Q6.*
