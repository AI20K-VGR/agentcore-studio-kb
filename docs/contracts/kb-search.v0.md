---
id: studio.contract.kb-search.v0
type: interface-draft
status: v0-draft
freeze: NOT-FROZEN
freeze_target: D11
contract_ref: umbrella-contract §3.3
pen: DE — Nguyễn Đông Anh
date: 2026-07-21
---

# 🖊️ kb.search — INTERFACE v0 (NHÁP)

> ## ⚠️ v0 — CHƯA FREEZE. Dự kiến freeze **D11**.
> Bản v0 tuần 1 **CHƯA CÓ FENCE** — đây là chủ ý, không phải thiếu sót. Đọc §4 trước khi code:
> ba luật fence sẽ có hiệu lực từ S2/S3, viết sẵn để không ai thiết kế theo hướng phải đập đi.

**Bút:** DE · **Neo:** umbrella §3.3 · **Người dùng:** AIE-1 (node `kb-retrieve`), AIE-2 (citation-accuracy).

---

## 1. Chữ ký v0 — tuần 1

```
kb.search(query: str, tenant: str, top_k: int)
    -> [ { chunk_id: str, text: str, score: float, tenant: str } ]
```

Đủ để walking-skeleton chạy: AIE-1 gọi được từ node `kb-retrieve`, kết quả có `chunk_id` nên
AIE-2 chấm được citation-accuracy ngay từ tuần 1.

**`chunk_id` là field quan trọng nhất ở v0.** Không có nó thì "câu trả lời có trích dẫn"
(cited answer) không kiểm chứng được, và citation-accuracy chỉ còn là cảm tính.

---

## 2. Chữ ký đích — bản freeze §3.3

```
kb.search(query: str, tenant: str, section_roles: [str], top_k: int)
    -> [ { chunk_id: str, text: str, score: float, tenant: str, section_role: str } ]
```

---

## 3. Đường nâng v0 → freeze: **chỉ THÊM, không ĐỔI**

| | v0 (tuần 1) | freeze (§3.3) | Loại thay đổi |
|---|---|---|---|
| tham số `query`, `tenant`, `top_k` | ✅ | ✅ | *giữ nguyên* |
| tham số `section_roles` | ❌ chưa có | ✅ | **thêm** |
| item `chunk_id`, `text`, `score`, `tenant` | ✅ | ✅ | *giữ nguyên* |
| item `section_role` | ❌ chưa có | ✅ | **thêm** |
| hành vi lọc | chưa fence | fence tại retrieval | **siết** |

**v0 chỉ THIẾU, không MÂU THUẪN với bản freeze.** Không có tham số nào bị đổi tên, không có
field nào đổi nghĩa. Nâng lên freeze = thêm 1 tham số + thêm 1 field + siết hành vi lọc.

> ⚠️ **Nhưng "thêm tham số" vẫn là đổi call-site.** AIE-1 nối `kb-retrieve` từ Day 3–4; nếu
> `section_roles` xuất hiện ở S2 thì mọi chỗ gọi phải sửa lần hai → xem **§7 Q-A**.

---

## 4. Ba luật SẼ ràng buộc từ S2/S3 — đọc trước khi thiết kế

v0 chưa fence, nhưng ba luật dưới đây là **đích không đổi**. Ghi ở đây để không ai xây theo hướng
sau này phải đập đi. Nguồn: umbrella §3.3 + docstring `src/studio_kb/search.py`.

### 4.1 Lọc TẠI RETRIEVAL, fail-closed

Chunk nằm ngoài phạm vi người gọi được phép đọc **không bao giờ được rời khỏi hàm này**. Lọc phải
nằm trong câu truy vấn, không phải lọc sau khi đã lấy ra.

Fail-closed nghĩa là: khi không xác định được phạm vi → trả **0 kết quả**, không trả tất cả. Mặc
định lúc hỏng phải là *không cho gì*, chứ không phải *cho hết*.

### 4.2 `section_roles` do SERVER quyết

Giá trị `section_roles` client gửi lên là một **yêu cầu**, không phải một **quyền**. Server tự
resolve phạm vi thật từ phiên làm việc; danh sách client tự khai bị bỏ qua.

Đây chính là thứ chặn **T6 label-spoof**: nếu tin danh sách client gửi lên, kẻ tấn công chỉ cần
khai thêm một `section_role` là đọc được phần không thuộc về mình — không cần khai thác lỗ hổng gì.

### 4.3 CẤM trả hết rồi nhờ LLM lọc

Anti-pattern bị cấm bằng chữ: lấy toàn bộ chunk rồi dặn model *"chỉ dùng phần thuộc tenant X"*.

Sai vì hai lẽ. Một: dữ liệu **đã rời khỏi** vùng an toàn — nó nằm trong prompt, trong log, trong
trace. Hai: nó biến một ràng buộc dữ liệu (luôn đúng) thành một lời đề nghị với model (thường
đúng). Fence phải là cơ chế, không phải lời nhờ vả.

---

## 5. Quan hệ với dữ liệu bên dưới

Fence ở §4 chỉ bám được vào hai cột đã có trong `src/studio_kb/schema.py`:

```
kb.chunks( chunk_id, tenant_id NOT NULL, section_role NOT NULL, text, embedding, created_at )
```

Hai cột `NOT NULL` đó **là** fence. Một dòng có `tenant_id` NULL là dòng không thuộc về ai, và mọi
phép lọc đều trượt qua nó. Vì thế ràng buộc `NOT NULL` phải được giữ **từ lúc ghi vào**, không phải
kiểm lúc đọc ra. Chi tiết đường đi từ front-matter tài liệu xuống chunk: `../callisto-doc-schema.md`.

---

## 6. Delta so với code đã có trong repo

| Nơi | Trạng thái hiện tại | v0 nói gì |
|---|---|---|
| `studio_contracts.kb.KbSearch` (Protocol) | đã có **4 tham số**, gồm `section_roles` | v0 dùng 3 — **thiếu**, không phải đề xuất bỏ |
| `studio_contracts.kb.KbSearchResultItem` | đã có `section_role` | v0 chưa dùng — **chưa điền**, không xoá |
| `studio_kb.search.KbSearchService.search` | seam, thân hàm `NotImplementedError` | DE điền từ Day 4 |

**Nói rõ để tránh hiểu nhầm:** v0 bỏ `section_roles` **không phải** vì DE đề xuất bỏ fence. Fence là
AC cứng (leakage = 0). v0 mỏng vì tuần 1 KB còn là stub 5 doc, chưa có `section_role` thật để lọc.

**Không sửa `packages/contracts/**`** — reference do mentor cấp, DE chỉ đọc (GITFLOWS §5).

---

## 7. Câu hỏi còn mở

| # | Hỏi ai | Nội dung | Nghiêng về |
|---|---|---|---|
| **Q-A** | mentor | Có nên nhận `section_roles` **ngay từ v0** (nhận rồi bỏ qua) để khỏi đổi call-site hai lần? | giữ v0 thin đúng brief |
| Q-B | mentor | File nháp này là "bút v0", hay phải đề xuất delta lên `contracts` qua PR? | file nháp trong `packages/kb` |
| Q-C | AIE-2 | citation-accuracy so khớp bằng `chunk_id` — có cần `expected_citation` trong golden-set không? | có, xem `../format.md` |

---

## 8. Lịch sử

| Bản | Ngày | Đổi gì |
|---|---|---|
| v0 | 2026-07-21 (D2) | Bản nháp đầu — chữ ký 3 tham số theo brief tuần 1, ghi sẵn 3 luật fence S2/S3, nêu rõ v0 là tập con của bản freeze |
