---
id: studio.de.callisto-doc-schema
type: data-design-draft
status: v0-draft
author: DE — Nguyễn Đông Anh
date: 2026-07-21
---

# Sơ đồ tài liệu Callisto + bảng chunk / index

> **Câu hỏi file này trả lời:** *chữ `tenant` viết ở đầu một file markdown, bằng cách nào mà cuối
> cùng nó chặn được rò rỉ dữ liệu ở `kb.search`?*
>
> Đây là **thiết kế hình dạng dữ liệu**, chưa sinh tài liệu. Nội dung 40–60 doc viết từ S2;
> tuần 1 chỉ cần **5 doc stub** (§8).
> **Neo:** `src/studio_kb/schema.py` (DDL đã có) · `pipeline.py::chunker` (luật cắt) · umbrella §1 fence · §6 NDA.

---

## 1. Callisto là gì

**Callisto Handbook** — bộ tài liệu nội bộ **tự viết 100%** (INV-3), đóng vai kho tri thức cho agent.
Hai tổ chức khách hàng giả lập dùng chung hình dạng tài liệu nhưng **nội dung tách biệt hoàn toàn**:

| | |
|---|---|
| Tenant | `ankor` · `borea` — **chỉ hai giá trị này** |
| User | `alice` · `bob` · `carol` — định danh sinh mới |
| Quy mô | ~40–60 doc `.md` (S2) · **5 doc (tuần 1)** |
| Ràng buộc | 0 PII · 0 tên thật · 0 dữ liệu sản xuất |

Cùng một câu hỏi hỏi ở `ankor` và ở `borea` phải ra **hai đáp án khác nhau**. Đó là điều kiện để
leak-test có ý nghĩa — nếu hai tenant trả lời giống nhau thì rò rỉ cũng không ai phát hiện được.

---

## 2. Front-matter — đầu mỗi file `.md`

```yaml
---
doc_id:  str           # ổn định — nguồn của chunk_id, xem §6
tenant:  ankor|borea   # → cột tenant_id (NOT NULL)
section: str           # → cột section_role (NOT NULL), từ vựng đóng §3
---
```

**Ba field, không hơn.** Mỗi field phải neo được vào một dòng umbrella hoặc một lỗ rò rỉ cụ thể:

| Field | Neo | Thiếu thì sao |
|---|---|---|
| `tenant` | **§3.3** — item trả về có `tenant`; filter theo `{tenant, section_role}` | fence không có gì để lọc → **rò rỉ chéo tenant** |
| `section` | **§3.3** — item trả về có `section_role` | fence chỉ chặn tới mức tenant, **không chặn được theo vai** (T6) |
| `doc_id` | **§3.3** *"mọi chunk trả về mang `chunk_id`"* + `re_index` phải **giữ nguyên `chunk_id`** | `chunk_id` không tái tạo được sau re-index → golden-set chết (§6) |

**Đã cân nhắc rồi bỏ:** `title` (§3.3 item trả về không có field này — hiển thị nguồn là việc của
UI, tra ngược từ `doc_id`), `author`, `created_at`, `tags`. Không neo được vào contract, cũng không
bịt lỗ rò rỉ nào.

---

## 3. Từ vựng `section_role` — đề xuất đóng, v0

Fence theo vai chỉ chạy được khi tập giá trị **đóng và biết trước**. Đề xuất 4 giá trị:

| `section_role` | Ai đọc được | Nội dung mẫu |
|---|---|---|
| `public` | mọi user trong tenant | quy trình chung, lịch nghỉ, giới thiệu |
| `hr` | alice | thang lương, hồ sơ nhân sự, đánh giá |
| `finance` | bob | hạn mức chi, ngân sách, hợp đồng |
| `engineering` | carol | runbook, cấu hình hệ thống, sự cố |

Ánh xạ user → role này do **SWE resolve server-side** (INV-1 middleware), DE chỉ **nhận** kết quả.
DE không tự suy ra role từ tên user.

> ❓ Từ vựng này là **đề xuất của DE**, chưa chốt với team → §10 Q1. Chốt sớm vì nó ăn vào cả
> golden-set lẫn leak-test.

---

## 4. Bảng chunk / index

Bám **đúng** DDL đã có trong `src/studio_kb/schema.py` — **không thêm cột mới**:

```sql
CREATE TABLE kb.chunks (
    chunk_id     TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    tenant_id    TEXT NOT NULL,        -- ← từ front-matter tenant
    section_role TEXT NOT NULL,        -- ← từ front-matter section
    text         TEXT NOT NULL,
    embedding    vector(8),            -- EMBEDDING_DIM, khớp FakeEmbedding.dim
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**Ba lớp phòng vệ đã dựng sẵn trong DDL** — DE chỉ cần không phá:

| Cơ chế | Tác dụng |
|---|---|
| `tenant_id` / `section_role` **NOT NULL** | không tồn tại dòng "không thuộc về ai" |
| `ENABLE` + **`FORCE` ROW LEVEL SECURITY** | `FORCE` khiến chính chủ bảng cũng bị chặn, không được miễn trừ |
| policy `USING` + `WITH CHECK` theo `current_setting('app.tenant_id', true)` | chặn cả **đọc** lẫn **ghi**; phiên chưa set tenant → so sánh với NULL → **0 dòng** (fail-closed, không phải "thấy hết") |

### ⚠️ Hai loại rò rỉ được bảo vệ ở mức KHÁC NHAU

Đọc kỹ policy trong `schema.py`: nó **chỉ khoá theo `tenant_id`**. `section_role` **không có RLS
đứng sau**.

| Loại rò rỉ | Ai chặn | Độ chắc |
|---|---|---|
| **Chéo tenant** (ankor thấy borea) | RLS **+** mệnh đề `WHERE` trong `kb.search` | **hai lớp** — quên `WHERE` thì RLS vẫn đỡ |
| **Chéo vai** (carol thấy `hr`) | **chỉ** mệnh đề `WHERE` ở tầng ứng dụng | **một lớp** — quên là rò thẳng |

Đây là **cạnh yếu nhất của cả thiết kế**, và đúng là chỗ leak-test **T6** nhắm vào. Ghi ra đây để
không ai nhầm rằng "đã có RLS thì role cũng an toàn". Khi viết `kb.search` thật (Day 4+), mệnh đề
lọc `section_role` phải được test riêng, không dựa vào RLS đỡ hộ.

**Index:**

| Index | Cột | Dùng khi |
|---|---|---|
| `kb_chunks_embedding_hnsw_idx` | `embedding` (cosine) | xếp hạng độ tương đồng |
| `kb_chunks_tenant_id_idx` | `tenant_id` | lọc tenant trước khi xếp hạng |

Hai index này phản ánh đúng thứ tự truy vấn bắt buộc: **lọc trước, xếp hạng và cắt `top_k` sau** —
cả hai trong **cùng một câu SQL**.

---

## 5. Luật cắt đoạn: **1 chunk = đúng 1 `section_role`**

Docstring `KbPipeline.chunker` đã khoá luật này. Ranh giới chunk **không được bắc qua hai section**.

**Vì sao là luật cứng, không phải khuyến nghị:** giả sử một chunk chứa cả nội dung `public` lẫn
`finance`. Khi lọc theo role, bạn chỉ có hai lựa chọn, **cả hai đều sai**:

- trả cả chunk → lộ phần `finance` cho người chỉ được đọc `public`;
- bỏ cả chunk → mất phần `public` mà người ta hoàn toàn có quyền đọc.

Không có lựa chọn đúng. Nên fence phải được bảo vệ **từ lúc cắt**, không phải lúc truy vấn. Cắt sai
là hỏng vĩnh viễn — truy vấn không cứu được.

**Chiến lược cắt v0:** cắt theo **heading cấp 2 (`##`)**, mỗi heading khai `section` của nó. Đơn
giản, kiểm tra bằng mắt được, và bảo đảm luật trên theo cấu trúc chứ không nhờ may mắn.

### Ví dụ: 1 doc → 3 chunk

```markdown
---
doc_id: ankor-expense-001
tenant: ankor
section: public          ← mặc định của doc
---

# Quy trình chi tiêu Ankor

## Nguyên tắc chung                    → chunk 1 · section_role = public
Mọi khoản chi cần có phiếu đề nghị...

## Hạn mức phê duyệt   {section: finance}   → chunk 2 · section_role = finance
Trưởng nhóm duyệt tối đa 20 triệu...

## Liên hệ hỗ trợ                      → chunk 3 · section_role = public
Thắc mắc gửi về kênh nội bộ...
```

Doc khai `section` mặc định ở front-matter; heading nào cần khác thì **ghi đè tại chỗ**. Chunk 2 mang
`finance` — carol hỏi trúng phần này sẽ **không thấy gì**, dù đang đứng đúng tenant `ankor`.

### 5b. Seam `KbPipeline` quy định luôn cách thực thi luật này

Đọc chữ ký đã có trong `src/studio_kb/pipeline.py`:

```python
async def chunker(self, document: str, *, tenant: str) -> list[str]
async def index(self, tenant: str, section_role: str, chunks, embeddings) -> None
#                                   ^^^^^^^^^^^^^^^^ MỘT role cho CẢ mẻ
```

Hai điều seam nói ra:
- `chunker` trả **chuỗi trần**, không mang role → nó không được thiết kế để phân biệt section;
- `index` đóng dấu **một `section_role` duy nhất lên toàn bộ mẻ** truyền vào.

→ Suy ra thứ tự bắt buộc: **tách theo section TRƯỚC, cắt chunk SAU.**

```
doc.md
  └─ tách theo section  →  nhóm 'public'    ─┐
                        →  nhóm 'finance'   ─┤
                                             │  với MỖI nhóm:
                                             ├─ chunker(text_nhóm, tenant) -> [str]
                                             ├─ embed_invoke(chunks)
                                             └─ index(tenant, section_role, chunks, embeddings)
```

**Một doc n section = n lời gọi `index()`**, không phải một.

Điều hay: luật "1 chunk = 1 `section_role`" (§5) khi đó **được bảo đảm theo cấu trúc**, không phải
nhờ cẩn thận — vì `chunker` không bao giờ nhìn thấy nhiều hơn một section. Muốn cắt sai cũng không
cắt sai được.

---

## 6. Quyết định: `chunk_id` phải **tự sinh có quy luật**, không dùng UUID

DDL đặt `DEFAULT gen_random_uuid()::text`. Default đó **chỉ chạy khi không truyền giá trị** — và DE
**nên truyền**. Đề xuất quy ước:

```
chunk_id = "{doc_id}#c{số thứ tự bắt đầu từ 1}"

ví dụ:  ankor-expense-001#c1
        ankor-expense-001#c2
```

**Ba lý do, đều là ràng buộc thật trong đồ án:**

1. **Gán nhãn tay khả thi.** Golden-set cần `expected_citation` do người điền. Chép tay UUID
   `f47ac10b-58cc-...` là bất khả thi; `ankor-expense-001#c2` thì nhìn là biết.
2. **Re-index idempotent (S3).** Docstring `re_index` bắt **giữ nguyên `chunk_id`**. Với UUID ngẫu
   nhiên, re-index sinh id mới → mọi `expected_citation` trong golden-set chết theo, phải gán nhãn
   lại toàn bộ. Với id suy ra từ `(doc_id, thứ tự)`, re-index tái tạo đúng id cũ **miễn phí**.
3. **Đọc trace hiểu ngay.** `citations` trong trace-event là danh sách `chunk_id`. Một mảng UUID
   không nói lên điều gì khi debug.

> ⚠️ Hệ quả phải chấp nhận: chèn thêm một section vào **giữa** tài liệu sẽ đánh số lại các chunk phía
> sau. Ở quy mô 40–60 doc và tài liệu tự viết, đây là cái giá rẻ hơn nhiều so với gán nhãn lại
> golden-set. → §10 Q2.

---

## 7. Đường đi của metadata

```
  doc.md
  front-matter { tenant: ankor, section: public }
        │
        │  ingest → chunker (cắt theo ##, giữ 1 chunk = 1 role)
        ▼
  kb.chunks row { tenant_id: 'ankor', section_role: 'finance', chunk_id: 'ankor-expense-001#c2' }
        │
        │  RLS policy + WHERE tenant_id = ? AND section_role = ANY(?)
        ▼
  kb.search → chỉ chunk khớp scope rời khỏi hàm
        │
        ▼
  citations: [chunk_id] → trace-event → citation_accuracy (AIE-2)
```

**Câu chốt:** *hai cột `NOT NULL` kia **chính là** fence. Một dòng `tenant_id` NULL là dòng không
thuộc về ai, và mọi phép lọc đều trượt qua nó. NULL = fence hở.* Vì thế ràng buộc phải nằm **ở lúc
ghi vào**, không phải kiểm lúc đọc ra.

---

## 8. Bộ 5 doc stub tuần 1 — thiết kế có chủ đích

5 doc này **không phải chọn ngẫu nhiên**. Chúng phải đủ để dựng cả case dương lẫn hai loại case âm
cho smoke-case (và dùng lại nguyên si ở leak-test T1/T6 tại S3):

| # | `doc_id` | tenant | section | Chủ đề | TT |
|---|---|---|---|---|---|
| 1 | `ankor-leave-001` | ankor | public | Quy trình nghỉ phép | ✅ D3 · 5 chunk |
| 2 | `ankor-expense-001` | ankor | public + **finance** | Chi tiêu — doc nhiều section (§5), ingest thành **2 lời gọi `index()`** | ✅ D3 · 5 chunk (`#c2` = finance) |
| 3 | `ankor-salary-001` | ankor | **hr** | Thang lương | ✅ D3 · 5 chunk |
| 4 | `borea-leave-001` | borea | public | Quy trình nghỉ phép — **nội dung khác hẳn** | ✅ D3 · 5 chunk |
| 5 | `borea-expense-001` | borea | **finance** | Hạn mức chi — **con số khác hẳn** | ✅ D3 · 5 chunk |

> **Viết ở D3 (22/07) — đủ cả 5 doc**, nằm ở `docs/callisto/`, tổng 25 chunk.
> Nội dung **bám đúng đáp án placeholder** của `format.md` §8: `ankor-leave-001#c1` = 3 ngày,
> `borea-leave-001#c1` = 7 ngày, `ankor-expense-001#c2` = 20 triệu. Hai doc phục vụ case âm cũng đã
> có nguồn thật: `ankor-salary-001` (vai `hr`, mồi SC-05 chéo vai) và `borea-expense-001`
> (**77 triệu** — lệch hẳn 20 triệu của Ankor đúng như §9 yêu cầu, mồi SC-04 chéo tenant).
> Day 4 vì thế chỉ còn **gán nhãn `expected`**, không phải viết nội dung.

**Ba tình huống bộ này dựng được:**

| Loại | Câu hỏi | Kết quả đúng |
|---|---|---|
| ✅ dương | scope `ankor`, hỏi quy trình nghỉ phép | trả lời + trích `ankor-leave-001#c1` |
| ❌ âm — **chéo tenant** | scope `ankor`, hỏi hạn mức chi của Borea | **từ chối** — không được lấy từ doc #5 |
| ❌ âm — **chéo vai** | scope `ankor`, role `engineering`, hỏi thang lương | **từ chối** — doc #3 là `hr` |

Doc #1 và #4 **cùng chủ đề, khác nội dung** là chủ ý: nếu fence hở, câu trả lời sẽ lẫn nội dung của
tenant kia — và vì hai bản khác nhau nên phát hiện được ngay. Nếu hai bản giống nhau, rò rỉ xảy ra
mà test vẫn xanh.

---

## 9. Ràng buộc NDA

| Luật | Áp dụng |
|---|---|
| 100% synthetic | tự viết, không lấy từ tài liệu thật của bất kỳ tổ chức nào |
| 0 PII | không tên thật, không email, không số điện thoại |
| Định danh sinh mới | chỉ `ankor`/`borea`, `alice`/`bob`/`carol` |
| Secret-scan | pre-commit `nda-denylist` chặn khi commit |

Số liệu trong doc (lương, hạn mức) là số **bịa có chủ đích** — chọn số dễ nhận ra khi bị rò
(ví dụ 20 triệu vs 77 triệu), không chọn số tròn giống nhau giữa hai tenant.

---

## 10. Câu hỏi còn mở

| # | Hỏi ai | Nội dung | Nghiêng về |
|---|---|---|---|
| **Q1** | SWE + mentor | Từ vựng `section_role` 4 giá trị (`public/hr/finance/engineering`) — chốt được không? SWE là người resolve role server-side nên phải khớp | dùng 4 giá trị này |
| **Q2** | mentor | `chunk_id` theo quy ước `{doc_id}#c{n}` thay vì UUID mặc định — có vi phạm gì không? | có, vì re-index idempotent + gán nhãn tay |
| **Q3** | AIE-2 | Bộ 5 doc §8 có đủ dựng 5 smoke-case không, hay cần thêm chủ đề? | đủ |

---

*Draft D2 — 2026-07-21. Nội dung 5 doc viết ở Day 4; 40–60 doc đầy đủ ở S2.*
