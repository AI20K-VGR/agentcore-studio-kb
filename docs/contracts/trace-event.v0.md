---
id: studio.contract.trace-event.v0
type: interface-draft
status: freeze-ready
freeze: FREEZE-READY   # chờ Q-1 (nơi freeze) + 4/4 chữ ký — workshop #84, D11
freeze_target: D11
contract_ref: umbrella-contract §3.2
pen: DE — Nguyễn Đông Anh
date: 2026-07-21
updated: 2026-08-03
---

# 🖊️ trace-event — INTERFACE (FREEZE-READY D11)

> ## 🧊 FREEZE-READY (03/08, D11) — nội dung câu-chữ đã khoá; còn chờ **người**.
> Tên + nghĩa mọi khoá khớp `studio_contracts.trace.TraceEvent` **sau khi sửa drift D-13**
> (`tenant: str` → `tenant_id: UUID`) trong bản 03/08 — xem §7. *(Trước bản này doc còn `tenant: str`,
> **mâu thuẫn** với runtime; AIE-2 review bắt, đã sửa.)* Ngày freeze này **không** thêm field — chỉ
> **chốt câu chữ + căn lại theo runtime** và đóng/hoãn-có-ghi các câu mở. **Hai cổng còn lại là việc người** (xem §0.1):
> **Q-1** (bản `FROZEN` nằm ở draft kb hay PR bump `SCHEMA_VERSION` ở `contracts`) + **4/4 chữ ký**.
> Đổi sau khi freeze = mini-RFC + 4/4 chữ ký + decision-log; đổi bản freeze-ready này = nhắn DE.

## 0.1 Trạng thái freeze — đã khoá vs còn chờ người

**✅ Đã khoá bằng câu chữ (D11, DE):**
- **§4.2a `ts`** — ties hợp lệ; sắp ổn định `(ts, event_id)`; `ts` là cột `TEXT` → parse rồi mới sắp,
  raise khi hỏng; **KHÔNG** assert tăng-nghiêm-ngặt. Reader-test `test_trace_reader.py`
  (`test_ts_trung_nhau...`, `test_ts_sai_dinh_dang...`) đã khớp đúng câu này.
- **§4.1 `cost` một-nguồn** — mặc định DE: **sink tính từ `tokens` + bảng đơn giá**, executor chỉ cấp
  `tokens`. Cấm hai chỗ tính (kể cả ra cùng số). *(chờ AIE-1 xác nhận — Q-3)*
- **§5 `node_type`** — enum đóng 6 giá trị, **nguồn duy nhất** `studio_contracts.nodes.NodeType`, cấm
  khai lại phía kb; chuỗi walk hiện là **4** (`_WALK_ORDER`), không phải 6. *(phải trùng tập node
  `recipe.dag` của SWE — Q-4)*
- **§7 carrier** — `inputs_hash` (không DB default) + `outputs` **bắt buộc AIE-1 truyền** từ tuần 1.
  Đây là **thông báo ràng buộc bảng đã tồn tại**, không phải đàm phán.

**⏳ Còn chờ người (không đóng được trong lằn DE một mình):**
- **Q-1** — nơi chứa bản `FROZEN` (draft kb vs PR `contracts`/mentor CODEOWNERS) → hỏi mentor/leader.
- **Q-3 / Q-4 / Q-5** — cost-source (AIE-1) · node_type-set (SWE) · field-eval-đọc + `chunk_id` (AIE-2).
- **4/4 chữ ký** — bảng §10 (để trống, chờ ceremony #84).

## 0.2 Chữ ký freeze (D11) — chờ workshop #84

| Vai | Người | Ký | Ngày |
|---|---|---|---|
| DE (bút) | Nguyễn Đông Anh | ⬜ | |
| SWE | Thiệu Quang Minh | ⬜ | |
| AIE-1 | Trần Bá Đạt | ⬜ | |
| AIE-2 | Lưu Tiến Duy | ⬜ | |

*Không ký khống: ký sau khi đọc delta §7 + chốt Q-3/Q-4/Q-5.*

---

**Bút:** DE · **Neo:** umbrella §3.2 · **Người dùng:** AIE-1 (emit), AIE-2 (đọc `cost`/`citations`), SWE (hiển thị trace ở playground).

---

## 1. Bản ghi này để làm gì

Mỗi bước chạy của interpreter đẻ ra **đúng một** trace-event. Ba thứ khác nhau đọc lại cùng bộ event đó:

| Ai đọc | Đọc để làm gì |
|---|---|
| Trace viewer (SWE) | in timeline từng node của 1 lần chạy |
| Cost dashboard (DE) | cộng `cost` theo agent / tenant |
| Eval harness (AIE-2) | lấy `citations` chấm citation-accuracy, lấy `cost` báo cáo |

Vì **ba mặt đọc chung một nguồn**, mọi con số chỉ được tính **một lần** — tại điểm emit. Ai tính lại ở phía mình là sai kiến trúc, kể cả khi công thức giống nhau (xem §4).

---

## 2. Schema v0

```yaml
trace_event:
  event_id:    str        # khoá chính, duy nhất toàn hệ
  run_id:      str        # gom mọi event của 1 lần chạy
  agent_id:    str
  tenant_id:   uuid       # NOT NULL — INV-1 · UUID (D-13, đổi từ `tenant: str`)
  node_id:     str        # id node trong DAG của recipe
  node_type:   str        # ∈ 6 loại đóng (§5)
  ts:          iso8601    # monotonic trong 1 run_id
  tokens:                 # nguồn của cost-lineage
    prompt:     int
    completion: int
  cost:        float      # MỘT số duy nhất, chảy ra 3 mặt

  # ── để trống tới S2, xem §3 ──
  inputs_hash: str?
  outputs:     obj?
  citations:   [chunk_id]?
```

---

## 3. Field nào dùng ngay, field nào hoãn

Tiêu chí cắt: **"Day 5 (trace sink + reader timeline) có cần field này để chạy không?"**

| Field | v0 tuần 1 | Vì sao |
|---|---|---|
| `event_id` | ✅ bắt buộc | không có thì không dedupe được |
| `run_id` | ✅ bắt buộc | không có thì không gom được 1 lần chạy |
| `agent_id` | ✅ bắt buộc | dashboard cộng theo agent |
| `tenant_id` (UUID) | ✅ **NOT NULL** | ràng buộc dữ liệu, không phải field tuỳ chọn — xem §4.3 (D-13: UUID, không phải slug) |
| `node_id` | ✅ bắt buộc | timeline phải chỉ được node nào |
| `node_type` | ✅ bắt buộc | enum đóng, xem §5 |
| `ts` | ✅ bắt buộc | thứ tự timeline |
| `tokens` | ✅ bắt buộc | nguồn tính `cost` |
| `cost` | ✅ bắt buộc | invariant chính của tuần |
| `inputs_hash` | ⏸ hoãn S2 | dùng để replay/dedupe — tuần 1 chưa có nhu cầu replay |
| `outputs` | ⏸ hoãn S2 | tuần 1 chỉ cần biết node **đã chạy**, chưa cần nội dung |
| `citations` | ⏸ hoãn **Day 4** | chỉ có nghĩa khi `kb-retrieve` chạy thật; hôm nay KB còn là stub |

> **Hoãn ≠ bỏ.** 3 field cuối vẫn nằm nguyên trong schema và trong `studio_contracts.trace.TraceEvent`.
> v0 chỉ **chưa điền**, không đề xuất xoá.

---

## 4. Invariant — phần ràng buộc thật của bản giao kèo

Schema nói *có field gì*. Mục này nói *cái gì đúng, cái gì sai*. Đây mới là chỗ bản giao kèo cắn.

### 4.1 cost-lineage — một số, ba mặt

`cost` xuất hiện ở 3 nơi: bảng kết quả UI test · trace viewer · cost dashboard.
**Cả ba phải đọc cùng một giá trị từ cùng một event.**

- ✅ Đúng: tính `cost` **một lần tại điểm emit**, ba mặt kia chỉ đọc lại.
- ❌ Sai: mỗi mặt tự nhân `tokens × đơn giá` — **kể cả khi ra đúng cùng con số**. Sai vì hôm sau đơn giá đổi ở một chỗ là ba mặt lệch nhau, mà không ai biết mặt nào đúng.

Lệch giữa ba mặt = **fail**, không phải cảnh báo.

### 4.2 ordering — monotonic, 0-gap

Trong cùng một `run_id`:
- `ts` **không được giảm** giữa hai event liên tiếp;
- reader in ra timeline phải **0-gap** — mọi node đã chạy đều có mặt, không thiếu ở giữa.

Thiếu một event ở giữa nguy hiểm hơn hỏng hẳn: timeline vẫn **trông** liền mạch, người đọc không biết mình đang thiếu.

#### 4.2a "0-gap" nghĩa là gì — chốt bằng chữ *(bổ sung 24/07, D5)*

Câu "0-gap" đọc được theo **hai** cách, và hai cách cho ra hai reader khác hẳn nhau. Ghi ra đây vì
đây là loại câu hỏi mà mỗi người tự suy một kiểu rồi không ai phát hiện lệch:

| cách hiểu | nghĩa | chọn? |
|---|---|---|
| **thời gian liên tục** | không có khoảng trống giữa các `ts` | ❌ **vô nghĩa** — node chạy nhanh chậm khác nhau là bình thường, mọi run đều sẽ "có gap" |
| **không sót node** | mỗi node trong chuỗi kỳ vọng có **đúng một** event | ✅ **chọn** — đúng chữ DoD *"Mọi node của 1 run emit event (không sót node)"* |

Ba hệ quả ràng buộc reader, không phải gợi ý:

1. **So theo `node_type`, không theo `node_id`.** `node_id` do người viết recipe đặt (`"n1"`, `"n2"`…),
   không đoán trước được; `node_type` thuộc tập đóng 6 giá trị và là thứ "chuỗi kỳ vọng" nói tới.
2. **Chuỗi kỳ vọng hiện tại là 4 node, không phải 6.** `studio_engine.interpreter._WALK_ORDER`
   hardcode `kb-retrieve → llm-step → tool-call → end`; `condition` và `hitl-pause` **không bao giờ
   được dispatch** ở phase này (đọc `recipe.dag.edges` để đi động là Day-6 scope). So với 6 là báo
   thiếu oan. Khi vòng đi thành động, truyền chuỗi thật của recipe vào thay vì sửa hằng số.
3. **Trùng cũng là sai, không chỉ thiếu.** Luật viết là *"mọi node emit event"* — số ít. Hai event
   cho cùng một node nghĩa là emit-hook chạy hai lần; reader phải kêu, không được im.

**`ts` dùng để SẮP, tập node dùng để KIỂM — đừng trộn hai việc.** Dùng khoảng cách thời gian để suy
ra thiếu node sẽ báo động giả mỗi khi một node chạy lâu.

> ⚠️ **`ts` là cột `TEXT`.** `ORDER BY ts` là **so chuỗi**, chỉ trùng với thứ tự thời gian khi mọi
> timestamp cùng định dạng và cùng độ dài — có/không `Z`, có/không micro-giây, lệch múi giờ đều làm
> thứ tự sai, và sai **im lặng**. Reader phải parse ra `datetime` rồi mới sắp, và **raise** khi parse
> hỏng thay vì lặng lẽ giữ thứ tự DB trả về.
>
> Ngược lại, **không** assert `ts` tăng nghiêm ngặt: hai node chạy cùng mili-giây trùng `ts` là
> chuyện bình thường. Trùng thì giữ thứ tự đầu vào (sắp ổn định), và đầu vào đã `ORDER BY ts,
> event_id` nên kết quả tất định.

Bản hiện thực: `studio_kb.trace_reader` — `check_walk()` / `sort_events()` / `render_timeline()`.

### 4.3 tenant_id NOT NULL

`tenant_id` (**UUID**, D-13 — danh tính tenant là `core.tenants.id` bất biến, không phải slug) là
**ràng buộc dữ liệu**, không phải field tuỳ chọn. Một event `tenant_id = NULL` là một event không thuộc về ai, và mọi phép lọc theo tenant đều trượt qua nó — vừa hỏng dashboard, vừa hở INV-1. Sink phải **từ chối ghi**, không được ghi rồi sửa sau.

---

## 5. `node_type` — enum đóng 6 giá trị

```
kb-retrieve · llm-step · condition · tool-call · hitl-pause · end
```

Nguồn duy nhất: `studio_contracts.nodes.NodeType`. **Không tự khai lại enum này ở phía KB** — import về dùng, để 6 giá trị không bao giờ trôi lệch giữa các package.

Thêm giá trị thứ 7 = **breaking change**, cần mini-RFC + 4/4 chữ ký. Sink gặp `node_type` lạ → **từ chối event**, không ghi "cho an toàn".

---

## 6. Ai emit, emit lúc nào (seam với AIE-1)

AIE-1 đang phác node-executor dạng `execute(node, ctx) -> ctx'`.

**Luật:** mỗi lần `execute` trả về `ctx'` → emit **đúng 1** trace-event. Không gộp 2 node vào 1 event; không emit 2 event cho 1 node.

Để DE điền được event mà không phải đoán, `ctx'` cần mang sẵn:

| DE cần | Ai đặt vào | Khi nào cần |
|---|---|---|
| `tokens {prompt, completion}` | AIE-1, sau khi gọi EmbeddingService / gateway | ngay tuần 1 |
| `cost` | AIE-1 (hoặc thống nhất DE tính từ `tokens`) — **chốt một chỗ duy nhất** | ngay tuần 1 |
| `citations: [chunk_id]` | AIE-1, lấy từ kết quả `kb.search` | từ Day 4 |
| `node_id`, `node_type` | AIE-1, từ node đang chạy | ngay tuần 1 |

> **Mặc định của DE:** `cost` do **sink tính** từ `tokens` + bảng đơn giá, executor chỉ cấp `tokens`
> — đơn giá đổi thì sửa một chỗ. §4.1 cấm tính hai lần nên phải có đúng một nơi tính; chốt lại với
> AIE-1 khi vào việc thật (Day 3–5).

---

## 7. Delta: v0 ↔ bản freeze §3.2 / `studio_contracts.trace.TraceEvent`

| Field | v0 (file này) | freeze §3.2 + `trace.py` | Ghi chú |
|---|---|---|---|
| 8 field lõi khác | ✅ có, dùng thật | ✅ có | khớp hoàn toàn |
| **`tenant` → `tenant_id`** | trước 03/08: `tenant: str` ❌ | `tenant_id: UUID` | **🔴 D-13 breaking rename+retype.** Doc này **đã drift sau D-13** (contract runtime đổi, doc quên đổi); **sửa 03/08** cho khớp `trace.py:30`. Trước bản sửa đây LÀ mâu thuẫn thật. |
| `inputs_hash` | có trong schema, **chưa điền** | bắt buộc | hoãn S2 |
| `outputs` | có trong schema, **chưa điền** | bắt buộc | hoãn S2 |
| `citations` | có trong schema, **chưa điền** | optional (`list[str] \| None`) | hoãn Day 4 |
| Kiểu `node_type` | `str` mô tả trong tài liệu | `NodeType` (StrEnum) | code phải dùng enum, không dùng `str` trần |

**Đính chính (03/08, review AIE-2):** câu cũ *"v0 chỉ THIẾU, không MÂU THUẪN"* **đúng ở D2, sai sau D-13.**
D-13 đổi danh tính tenant `str`→`UUID` và tên field `tenant`→`tenant_id` ở contract runtime, nhưng doc
này **chưa được cập nhật** nên §2/§3/§4.3 vẫn ghi `tenant: str` — **một mâu thuẫn thật**, không phải chỉ
thiếu. Người mới đọc bản cũ sẽ wire `tenant: "ankor"` và **fail runtime validation**. Bản 03/08 sửa mọi
chỗ `tenant`→`tenant_id: UUID`. **Chỉ sau khi sửa** thì "mọi khoá khớp `TraceEvent`" mới đúng — và giờ
thì đúng: 3 field còn lại (`inputs_hash`/`outputs`/`citations`) là THIẾU thật (điền nốt), không mâu thuẫn.

### ⚠️ "Hoãn" KHÔNG có nghĩa là bỏ trống — sink đã tồn tại và bắt buộc

Sink **đã được cài sẵn trong kit**, không phải thứ sẽ dựng ở Day 5:

| Thành phần | Ở đâu | Trạng thái |
|---|---|---|
| `TraceWriter` Protocol — `write(event) -> None` | `studio_contracts/protocols.py` | ghi rõ *"owner DE (trace_sink)"* |
| `PgTraceWriter.write()` | `apps/studio/src/studio_app/obs/trace_writer.py` | **đã chạy** — 1 câu INSERT trần |
| Bảng `obs.trace_events` | `apps/studio/src/studio_app/obs/schema.py` | **đã có đủ 12 cột** |
| Test cổng | `apps/studio/tests/test_trace_writer.py` | 2 event → **2 dòng riêng**, cấm gộp |

Vì thế **không có chuyện "ghi dict tập con"**. Ràng buộc thật:

```sql
inputs_hash  TEXT NOT NULL          -- ⚠️ KHÔNG có DEFAULT
outputs      JSONB NOT NULL DEFAULT '{}'
tokens       JSONB NOT NULL DEFAULT '{}'
cost         NUMERIC NOT NULL DEFAULT 0
citations    JSONB                   -- nullable, field DUY NHẤT được bỏ trống
```

Cộng với `TraceEvent` (pydantic) cũng bắt buộc `inputs_hash` + `outputs`, kết luận cho **tuần 1**:

| Field | Thực tế phải làm gì |
|---|---|
| `inputs_hash` | **AIE-1 BẮT BUỘC truyền**, kể cả giá trị tạm (`""` hoặc hash rỗng). Không có default để dựa. |
| `outputs` | phải truyền, dùng `{}` khi chưa có nội dung |
| `citations` | **thật sự** bỏ trống được (`None`) tới Day 4 |

→ Phải báo AIE-1 **trước Day 3**. Đây không phải lựa chọn, là ràng buộc của bảng đã tồn tại.

### Ranh giới `write()` — luật F15

`write()` là **một câu INSERT trần**: không cộng dồn cost, không dedup, không upsert. Cộng dồn là
việc phía sau của DE (bảng `obs.costs`), không bao giờ thuộc seam ghi.

Lý do: **đường ghi không được hỏng vì logic tính toán.** Một lỗi trong phép cộng mà làm mất event
gốc là mất bằng chứng — không dựng lại được. Event thô là nguồn duy nhất; mọi số tổng hợp suy ra
từ đó. Đây cũng chính là cơ chế đỡ cho invariant cost-lineage ở §4.1.

**Không sửa `packages/contracts/**`.** File đó là reference do mentor cấp, DE chỉ đọc; muốn đổi phải mở PR ở repo `agentcore-studio-contracts` (GITFLOWS §5).

---

## 8. Câu hỏi còn mở

| # | Hỏi ai | Nội dung | Trạng thái |
|---|---|---|---|
| **Q-A** | mentor | `packages/contracts/trace.py` đã có bản đầy đủ — "bút v0 của DE" nghĩa là file nháp này, hay là đề xuất delta lên bản reference? | 🔴 **CHẶN FREEZE (D11 = Q-1)** — quyết nơi bản `FROZEN` đổ vào (draft kb vs PR `contracts`/mentor CODEOWNERS). Đến 03/08 chưa có câu trả lời → hỏi mentor/leader đầu giờ workshop #84 |
| ~~Q-B~~ | ~~mentor~~ | ~~SQLite hay Postgres?~~ → **đã tự trả lời: Postgres**, bảng `obs.trace_events` + `PgTraceWriter` đã có trong kit. "SQLite" ở week-1 §6 chỉ là cách nói giản lược | ✅ đóng |
| Q-C | AIE-2 | Ngoài `cost` + `citations`, eval harness còn cần đọc field nào từ trace? | 🟠 **chặn chữ ký AIE-2** — chốt danh sách field eval đọc trước khi ký (D11 Q-5) |
| **Q-D** | mentor | `obs.costs` + `obs.golden_sets` đang là **bảng rỗng chờ DE điền**, nhưng chúng nằm trong `apps/studio/` — **không phải fence-lane của DE**. DE điền bằng cách nào? | 🟡 **hoãn-có-ghi (D11)** — bảng ở `apps/studio`, **ngoài fence-lane DE**; ai/điền-sao = coordinate leader. **KHÔNG chặn freeze schema** — đã vào decision-log |

---

## 9. Lịch sử

| Bản | Ngày | Đổi gì |
|---|---|---|
| v0 | 2026-07-21 (D2) | Bản nháp đầu — cắt 9/12 field cho tuần 1, chốt 3 invariant, mở seam `ctx'` với AIE-1 |
| v0.1 | 2026-07-24 (D5) | Thêm **§4.2a — "0-gap" nghĩa là gì**, chốt bằng chữ trước khi code. Không đổi schema, không đổi invariant; chỉ **nói rõ một câu vốn đọc được hai kiểu**: chọn *"không sót node"*, bác *"thời gian liên tục"*. Kèm 3 hệ quả ràng buộc reader (so theo `node_type`; chuỗi kỳ vọng là **4** node theo `_WALK_ORDER` chứ không phải 6; trùng cũng là sai) và bẫy `ts` là cột `TEXT` (so chuỗi → phải parse rồi mới sắp, raise khi hỏng; nhưng **không** assert tăng nghiêm ngặt vì trùng `ts` là hợp lệ). Sinh ra cùng lúc với bản hiện thực `studio_kb.trace_reader` (#21) |
| **freeze-ready** | 2026-08-03 (D11, #80) | **Đưa về trạng thái freeze-ready** cho workshop #84. Khoá câu chữ: §4.2a `ts` (ties hợp lệ, không tăng-nghiêm-ngặt), §4.1 `cost` một-nguồn (sink-từ-`tokens`, mặc định DE), §5 `node_type` một-nguồn `studio_contracts.nodes.NodeType` (walk 4≠6), §7 carrier `inputs_hash`/`outputs` bắt buộc. Thêm §0.1 (đã-khoá vs chờ-người) + §0.2 (bảng chữ ký để trống). Đóng/hoãn câu mở: **Q-A→Q-1 (CHẶN, hỏi mentor nơi freeze)**, Q-C→Q-5 (chốt với AIE-2), **Q-D→hoãn-có-ghi cross-lane**. `FROZEN` + 4/4 chữ ký **chưa đóng**. *(Lưu ý: bản này còn sót `tenant: str` — sửa ở bản kế.)* |
| **d13-align** | 2026-08-03 (D11, review AIE-2) | **Sửa drift D-13 mà freeze-ready bỏ sót.** Đổi `tenant: str` → **`tenant_id: UUID`** ở §2 (schema), §3 (bảng field), §4.3 (tên mục + thân) cho khớp `studio_contracts.trace.TraceEvent` (`trace.py:30`). §7: bỏ câu *"v0 chỉ THIẾU, không MÂU THUẪN"* (đúng D2, sai sau D-13) — thêm đính chính + hàng delta `tenant→tenant_id`. §0.1 sửa claim "mọi khoá khớp" cho đúng (chỉ đúng SAU khi align). Không đổi field khác. Đây là drift **doc-đi-sau-runtime**, cùng loại với `wb.recipes` (workbench PR#13) nhưng ở lane DE — bắt bởi review AIE-2 trên PR#10. |
