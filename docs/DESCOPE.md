---
id: studio.de.descope-ladder
type: descope-ladder
status: draft
author: DE — Nguyễn Đông Anh
date: 2026-07-21
scope: 4 nấc (INV-7) — chi tiết 2 nấc DE own
---

# DESCOPE-LADDER — danh sách được phép cắt khi kẹt

> **Luật:** khi kẹt thì cắt **theo danh sách này**, **không cắt tuỳ hứng**. Viết sẵn từ Day 2 để lúc
> hoảng không phải nghĩ.
> **Ràng buộc cứng:** mỗi nấc tụt xuống, **demo 8 bước vẫn phải sống** (INV-7).
> **Neo:** umbrella §7 INV-7 · §4 storage ladder · `brief-overview.md` §5 (8 bước demo).

---

## 0. Cái KHÔNG BAO GIỜ được cắt

Descope-ladder cắt **độ giàu của cách làm**, không cắt **bất biến**. Bốn thứ dưới đây là AC
executable — tụt nấc nào cũng phải còn:

| Bất biến | Nghĩa |
|---|---|
| **`leakage = 0`** | chunk ngoài phạm vi không bao giờ rời khỏi `kb.search` (bước 5) |
| **eval-gate CHẶN + rollback** | verdict FAIL là cổng cứng, không phải cảnh báo (bước 7) |
| **cost-lineage khớp 3 mặt** | UI test == trace == dashboard, cùng một số |
| **hitl-pause dừng thật** | bước 8 |

Cắt trúng một trong bốn thứ này thì **không phải descope, là bỏ bài**.

---

## 1. Bốn nấc — tổng quan

| Nấc | Cắt gì | Chủ | Neo |
|---|---|---|---|
| **1** | KB thật → **stub tĩnh 5 doc** | **DE** | §7 INV-7 · §4 |
| 2 | Canvas React Flow → **form + Mermaid** | SWE | §7 INV-7 |
| 3 | LLM-judge → **exact-match scorer** | AIE-2 | §3.4 descope-guard |
| **4** | Cost dashboard → **bảng CLI** | **DE** | §3.2 |

Hai nấc **1** và **4** là của DE — chi tiết ở §2, §3. Hai nấc kia tóm tắt ở §4.

---

## 2. NẤC 1 (DE) — KB thật → stub tĩnh 5 doc

### 2.1 Cắt gì / giữ gì

| Cắt | Giữ nguyên |
|---|---|
| ingest tài liệu thật (40–60 doc) | **5 doc Callisto nạp sẵn**, 2 tenant |
| `chunker` chạy động | chunk **cắt sẵn tay**, mỗi chunk vẫn đúng 1 `section_role` |
| `embed_invoke` qua EmbeddingService | vector **fixture ghi sẵn** (chiều 8) |
| xếp hạng theo độ tương đồng thật | so khớp từ khoá / thứ tự cố định |
| `re_index`, `consent_purge` | — (S3, chưa có ở nấc này) |

### 2.2 ⚠️ Cắt ĐƯỜNG ỐNG, không cắt HÀNG RÀO

Đây là điểm dễ hiểu sai nhất của nấc này.

**Vẫn phải giữ, kể cả khi tụt nấc:**
- bảng `kb.chunks` với `tenant_id` / `section_role` **NOT NULL**;
- lọc **tại retrieval**, fail-closed — trong câu truy vấn, không lọc sau;
- mỗi kết quả mang `chunk_id` → citation vẫn chấm được.

§4 nói thẳng: *money-shot fence-proof (bước 5) phải đứng vững ở **L1***. Nên nấc 1 tụt về **cách nạp
dữ liệu**, không tụt xuống mức mất fence. 5 doc tĩnh vẫn đủ dựng cả case chéo tenant lẫn chéo vai.

> Nói gọn: **KB stub ≠ KB không rào.** Cắt phần "làm ra chunk", giữ nguyên phần "canh chunk".

### 2.3 Đối chiếu 8 bước demo

| Bước | Sống? | Vì sao |
|---|---|---|
| 1–3 tạo agent / gắn KB / vẽ flow | ✅ | `kb_binding` vẫn trỏ được vào KB stub |
| 4 Test → trace + cost live | ✅ | không liên quan nấc này |
| **5 money-shot fence** | ✅ | fence giữ nguyên (§2.2) — 5 doc đủ dựng case chéo tenant |
| 6 Eval → scorecard → PASS | ✅ | golden-set trỏ vào `chunk_id` của 5 doc |
| 7 gate CHẶN + rollback | ✅ | không liên quan |
| 8 hitl-pause | ✅ | không liên quan |

**8/8 sống.**

### 2.4 Điều kiện kích hoạt

| Kích hoạt khi | Hành động |
|---|---|
| Hết **Day 4** mà `kb.search` chưa trả được cited chunks | tụt nấc, **không cố** |
| Hết **S2** mà ingest→embed→index chưa chạy ổn định | giữ stub qua S3, dồn sức cho fence |
| `EmbeddingService` (AIE-1) chưa có ở mốc cần | dùng vector fixture, không chờ |

### 2.5 Mất gì

Mất phần trình diễn "pipeline dữ liệu thật" — tức mất **chiều rộng**, không mất **chiều sâu**. Fence,
citation, trace vẫn chấm được đủ. Với DE đây là nấc **rẻ nhất** trong 4 nấc.

---

## 3. NẤC 4 (DE) — cost dashboard → bảng CLI

### 3.1 Cắt gì / giữ gì

| Cắt | Giữ nguyên |
|---|---|
| dashboard đồ thị | **bảng in ra CLI** |
| lọc / group theo nhiều chiều | tổng theo agent + theo tenant |
| cập nhật thời gian thực | chạy lệnh là in |

### 3.2 ⚠️ Cắt CÁCH HIỆN, không cắt NGUỒN SỐ

**cost-lineage nằm ở nhóm không được cắt (§0).** Ba mặt (UI test · trace · dashboard) vẫn phải đọc
**cùng một số từ cùng một nguồn** — nấc này chỉ đổi mặt thứ ba từ đồ thị thành bảng chữ.

Nếu tụt nấc mà mỗi mặt tự tính lại `cost` cho tiện thì **đã phá bất biến**, không còn là descope.

Nguồn số không đổi: bảng `obs.trace_events` (event thô) → cộng dồn → `obs.costs`.

### 3.3 Đối chiếu 8 bước demo

| Bước | Sống? | Vì sao |
|---|---|---|
| **4 Test → token/chi phí live** | ✅ | số vẫn hiện ở UI test, chỉ mặt dashboard đổi dạng |
| 1–3, 5–8 | ✅ | không chạm |

**8/8 sống.**

### 3.4 Điều kiện kích hoạt

| Kích hoạt khi | Hành động |
|---|---|
| Vào S3 mà fence / gate chưa xanh | cắt dashboard ngay, dồn sức cho AC cứng |
| Còn < 3 ngày tới Day 30 mà dashboard chưa xong | in bảng CLI, không cố dựng đồ thị |

### 3.5 Mất gì

Mất tính "nhìn đẹp". Không mất điểm nào về bất biến — cost-lineage vẫn chứng minh được bằng cách in
ba mặt ra và so số.

---

## 4. Hai nấc của người khác (ghi cho đủ 4 — DE không quyết)

| Nấc | Chủ | Cắt gì | Skeleton sống vì | Ảnh hưởng DE |
|---|---|---|---|---|
| **2** | SWE | Canvas React Flow → **form + Mermaid** | recipe vẫn sinh ra được → interpreter vẫn đọc được `kb_binding` | không — DE chỉ đọc `kb_binding`, không quan tâm nó được vẽ bằng gì |
| **3** | AIE-2 | LLM-judge → **exact-match scorer** | scorecard vẫn ra PASS/FAIL bằng `success` + `citation_accuracy` | **có** — chấm exact-match thì `expected` phải khớp chặt hơn; xem `docs/format.md` §7 (đã cân nhắc `expected_contains` rồi bỏ) |

---

## 5. Thứ tự tụt nấc

Bốn nấc **độc lập**, không phải bậc thang phải đi tuần tự. Nhưng khi phải chọn cắt cái nào trước,
thứ tự ưu tiên của DE:

```
Nấc 4 (dashboard→CLI)     ← cắt trước, rẻ nhất, chỉ mất thẩm mỹ
Nấc 1 (KB thật→stub)      ← cắt sau, mất chiều rộng nhưng giữ đủ bất biến
```

Không có nấc nào cho phép cắt fence, cắt trace sink, hay cắt golden-set — vì cả ba đều nuôi trực
tiếp một bất biến ở §0.

---

## 6. Ai quyết, ghi ở đâu

| Việc | Ai |
|---|---|
| Kích hoạt nấc 1 / nấc 4 | **DE**, báo team trong daily-note |
| Kích hoạt nấc 2 / nấc 3 | SWE / AIE-2 |
| Tụt nấc chạm bất biến §0 | **không ai** — phải escalate mentor |

Mỗi lần tụt nấc: ghi vào daily-note mục *Quyết định kỹ thuật* — **nấc nào · vì điều kiện gì · mất
gì**. Tụt nấc là quyết định kỹ thuật có bằng chứng, không phải bỏ cuộc.

---

## 7. Ghi chú vị trí file

`day-02.md` xếp `DESCOPE.md` vào **Output chung** của team, nhưng DE chỉ có WRITE ở `packages/kb`.
Bản này viết đủ 4 nấc, chi tiết 2 nấc DE own — nếu team gộp về một bản ở repo cha thì bản này thành
phần KB của bản đó. Đang chờ mentor trả lời (question-batch Q1).

---

*Draft D2 — 2026-07-21.*
