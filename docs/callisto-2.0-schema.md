---
id: studio.de.callisto-2.0-schema
type: data-design-draft
status: v0-experiment
author: DE — Nguyễn Đông Anh
supersedes-when-wired: callisto-doc-schema.md (v0-draft, corpus 1.0)
---

# Callisto 2.0 — schema corpus (thử nghiệm, SONG SONG với 1.0)

> **Trạng thái:** thử nghiệm, **chưa wire** vào spine. Corpus 1.0 (`docs/callisto/`) + loader
> `doc_factory.load_callisto` + toàn bộ test 1.0 **giữ nguyên, không đụng tới**. 2.0 là cutter riêng
> (`doc_factory_v2`) đọc thư mục riêng (`docs/callisto-2.0/`). Khi nào 2.0 được duyệt để thay 1.0
> mới tính chuyện di dời golden-set/test — không phải bây giờ.

> **Câu hỏi file này trả lời:** *một chunk biết nó thuộc tenant nào và role nào — bằng cách nào, và
> nguồn nào là DUY NHẤT?*

## 0. Mục tiêu 2.0 khác 1.0 chỗ nào

| | 1.0 (`callisto-doc-schema.md`) | 2.0 (file này) |
|---|---|---|
| Nguồn `tenant` | front-matter `tenant:` (tài liệu tự khai) | **tên thư mục cha** (`ankor/`, `borea/`) |
| Nguồn `section_role` | front-matter `section:` + override per-chunk | **token đầu của tên file** (`hr-…md` → `hr`) |
| Override per-chunk | **có** (`## Tiêu đề {section: X}`) | **BỎ** — có invariant raise nếu gặp |
| Front-matter | 3 field bắt buộc | **không có** — doc là markdown thuần |
| `doc_id` | field front-matter | **= `{tenant}-{stem}`** (tenant từ thư mục + stem tên file) |
| Quy mô | 43 doc / ~140 chunk | 80 doc / ~800 chunk (40 ankor + 40 borea) |

**Giữ nguyên (đã thống nhất mentor/SWE ở 1.0, KHÔNG chốt lại):**
- Từ vựng đóng `SECTION_VOCAB = {public, hr, finance, engineering}` (Q1 · SWE resolve role server-side phải khớp).
- `chunk_id = "{doc_id}#c{n}"`, n đếm từ 1 theo từng doc, **không UUID** (Q2 · re-index idempotent).
- `tenant_id` là **UUID** (D-13), phân giải qua `resolve_tenant_id` — 2.0 phân giải **tên thư mục** thay vì slug front-matter.

## 1. Bố cục thư mục — tenant là THƯ MỤC, không phải tên file

```
docs/callisto-2.0/
  ankor/
    hr-onboarding.md          # role=hr,     doc_id=hr-onboarding
    finance-budget.md         # role=finance, doc_id=finance-budget
    engineering-oncall.md
    public-holidays.md
    ...                       # 10 doc / role × 4 role = 40 doc
  borea/
    hr-onboarding.md          # nội dung KHÁC ankor (leak-test có nghĩa)
    ...                       # 40 doc
```

**Vì sao tenant = thư mục:** danh tính tenant về lâu dài đến từ **ngữ cảnh ingest** (composition-root
truyền `tenant_id` xuống — Q-G, chưa chốt), KHÔNG từ tài liệu tự khai. Thư mục-per-tenant khớp sẵn
hướng đó: ingest thư mục `ankor/` *dưới danh nghĩa* ankor. Khắc tenant vào tên file = đóng đinh một
fixture đã đánh dấu để xoá.

## 2. Tên file — `{role}-{name}.md`

- **`role`** = token trước dấu `-` đầu tiên. PHẢI ∈ `SECTION_VOCAB`, sai → **raise**.
- **`name`** = phần còn lại (được có dấu `-`: `hr-code-of-conduct.md` → role=`hr`, name=`code-of-conduct`).
- **`doc_id` = `{tenant}-{stem}`** (tenant từ thư mục cha + stem tên file → `ankor-hr-code-of-conduct`).
  → **citation = tên file**: `chunk_id` = `{tenant}-{role}-{name}#c{n}` (`ankor-hr-code-of-conduct#c1`),
  tra ngược ra đúng file `docs/callisto-2.0/{tenant}/{role}-{name}.md`. Có tenant trong `doc_id` để hai
  tenant dùng **cùng tên file** (nội dung song song, tiền đề leak-test) **không đụng `chunk_id`**.
- Tên file **không có** đủ `role-name` (thiếu `-`, hoặc rỗng) → **raise**. Không đoán, không mặc định.
- **KHÔNG front-matter.** File mở đầu bằng nội dung (hoặc `#` tiêu đề), không có khối `---`.

## 3. Luật cắt (thừa kế 1.0, bỏ override)

1. **Cắt theo heading `##`** — 1 chunk = 1 heading + thân dưới nó; text **gồm cả dòng heading**.
2. **`chunk_id = "{doc_id}#c{n}"`**, n từ 1 theo từng doc.
3. **Mọi chunk trong 1 doc mang CÙNG `section_role`** = role từ tên file. Không ngoại lệ.
4. **CẤM override.** Heading chứa `{section: …}` → **raise** (`override bị bỏ ở 2.0`). Đây là invariant
   biến "không override" từ *trí nhớ* thành *luật cưỡng chế* — cùng kỷ luật `SECTION_VOCAB` raise.
5. **Thân heading rỗng → raise.** 1.0 âm thầm bỏ chunk rỗng; 2.0 raise để "10 chunk/doc" là thật, không
   âm thầm thành 9. Mỗi `##` phải có nội dung.

## 4. Mỗi doc = 10 chunk, dài ngắn khác nhau

- 10 heading `##`/doc → 10 chunk. Độ dài thân tự do (câu ngắn tới nhiều đoạn) — cạnh tranh near-miss
  thật là mục tiêu, KHÔNG phải filler (số lượng không tự dời điểm — rubric S2).

## 5. Bất biến 2.0 (được test cưỡng chế — xem `tests/test_doc_factory_v2.py`)

| # | Bất biến | Sai thì |
|---|---|---|
| I1 | thư mục cha ∈ {ankor, borea} | raise (qua `resolve_tenant_id`) |
| I2 | role (token đầu tên file) ∈ `SECTION_VOCAB` | raise |
| I3 | tên file đúng dạng `role-name.md` | raise |
| I4 | `doc_id == {tenant}-{stem}`, `chunk_id == {doc_id}#c{n}` | test đỏ |
| I5 | không heading nào mang `{section:…}` | raise (cấm override) |
| I6 | mọi chunk 1 doc cùng role = role tên file | test đỏ |
| I7 | thân `##` rỗng | raise |
| I8 | ankor vs borea cùng tên file → `tenant_id` khác nhau | test đỏ (tiền đề leak-test) |
| I9 | `chunk_id` duy nhất toàn corpus (kể cả 2 tenant cùng tên file) | test đỏ |

## 6. Điều KHÔNG làm ở 2.0 (nói rõ)

- **Không wire** vào `StaticKbSearch`/spine/golden-set. `emit_golden_set`, grid-queries, embeddings
  fixture, 15 file test 1.0 — **không đụng**.
- **Không di dời** con trỏ hay corpus 1.0.
- Nếu sau này 2.0 thay 1.0: lúc đó mới regen golden-30/smoke/grid + embeddings v1 + cập nhật test —
  và nếu cần override lại thì thêm có chủ đích + test, không để luật biến mất một mình.
