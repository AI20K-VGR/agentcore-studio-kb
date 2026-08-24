# Plan Sprint 3 (DE) — hàng rào phòng ban + doc_id/kb.documents + tiền xử lý + chunker tổng quát + crawler

> **Ngày lập:** 2026-08-23 · **Bút:** DE (Nguyễn Đông Anh) · **Ngân sách đề bài:** 10 pd, 8 việc.
> **File này KHÔNG phải chép lại bảng đề bài** — nó ghi nhận định (đã verify code, không đoán) +
> thứ tự thực thi đề xuất + câu hỏi mở cần chốt trước khi bắt tay.

---

## 0. Nhận định tổng quan — bảng CÓ hợp lý cho DE không?

**Chốt: hợp lý, giữ nguyên phạm vi 8 việc.** Cả 8 đều nằm trong lane kb (schema/RLS/pipeline/eval),
không lấn SWE/AIE-1/AIE-2 (chỉ việc 1 *đọc* qua route chat của SWE để đo, không viết). Điểm mạnh nhất:
việc 1 và việc 5 không phải hạng mục mới bịa ra — chúng đóng đúng khoản nợ mà **chính code kb đã tự
ghi lại** là "để S3":

> `postgres.py:36-41` (nguyên văn, viết từ D17): *"Còn thiếu so với contract đầy đủ — để S3:
> `section_roles` ở đây dùng đúng giá trị bên gọi đưa xuống, chưa phân giải server-side... Đây là
> khoảng trống thật của thiết kế v0, phải giải ở tầng phiên (**S3**)."*
>
> `postgres.py:23-30` — bảng hai trục ngay trong docstring: `tenant_id` có RLS, **`section_role` thì
> "chỉ WHERE... schema.py KHÔNG có policy cho cột này"**.

Việc 1 (đo) → việc 5 (vá) là **đúng khoản nợ này**, đúng thứ tự (đo trước khi vá là hợp lý: biết mức
độ hở thật trước khi quyết cách vá, giữ đúng tinh thần D17 "không fake-green").

Còn 2 vấn đề thật cần chốt trước khi chạy — không phải phản đối phạm vi, mà là **sai số cần fix**:

### 0.1 Tổng pd lệch ngân sách
0.5+1.5+1.5+1.5+1.0+2.5+1.0+1.0 = **10.5 pd**, đề bài ghi **10 pd**. Lệch 0.5. Đề xuất cắt ở việc 2
(xem §0.3) — không đụng việc 6 (crawler, rủi ro cao nhất, không nên siết) hay việc 5 (bảo mật, không
siết pd cho một mục an ninh). **Cần bạn chốt: cắt 0.5 ở việc 2, hay chấp nhận 10.5?**

### 0.2 Thứ tự bảng ≠ thứ tự chạy — việc 4 nên lên sớm
Đề bài tự ghi: *"Việc 4 chặn route quản lý tài liệu của SWE"*. Việc 4 không phụ thuộc việc 2/3/5/6 —
độc lập hoàn toàn. Xếp nó ở vị trí 4/8 trong bảng nghĩa là SWE có thể phải đợi tới giữa sprint mới có
bảng để dùng. **Đề xuất: chạy việc 4 ngay sau việc 1** (xem thứ tự thực thi §1), không đổi phạm vi hay
pd của nó — chỉ đổi thứ tự.

### 0.3 Việc 2 — target không phải sửa `_cut_document`, mà thêm hàm mới cạnh nó

> **CẬP NHẬT 2026-08-23 (CHỐT CUỐI):** thiết kế đã chuyển sang **cửa sổ trượt cố định theo SỐ TỪ**
> (850 từ/chunk, overlap 170 từ — đo trên corpus thật, không dùng token/`tiktoken`) thay vì permissive
> heading-cutter bàn dưới đây, và chỉ `.docx` (không `.doc`). Toàn bộ chi tiết + số liệu đo ở
> `plans/multiformat_chunker_plan.md` — không còn câu hỏi mở, sẵn sàng để code. Phần dưới đây giữ lại
> vì lý do "vì sao không sửa `_cut_document`" vẫn đúng nguyên với thiết kế mới.
Đã đọc `doc_factory_v2._cut_document` + `tests/test_doc_factory_v2.py`. Hai điều quan trọng:

- `_cut_document(text, doc_id, tenant_id, role)` **đã** nhận `role` qua tham số, không suy từ tên file
  — vế "section_role từ tham số" của việc 2 **đã xong**, không cần làm lại. `load_corpus_v2` (loader
  cho corpus cố định) mới là chỗ suy role từ tên file, và đó là chủ ý (corpus 2.0 phải khớp khuôn).
- Cái CHƯA có là "không raise vì sai khuôn": `_cut_document` hiện raise ở 3 chỗ — I5 (`{section:…}`
  trong heading), I7 (thân section rỗng), và raise nếu tài liệu **không có heading `## ` nào** (rất
  thật với HTML crawl-về: nhiều trang chỉ có `#`/`###`, hoặc không heading). Ba raise này được
  `tests/test_doc_factory_v2.py::test_override_bi_cam_raise` (dòng 110) và `::test_than_heading_rong_raise`
  (dòng 119) khoá cứng cho corpus Callisto đã curate — **không được nới lỏng tại đây**, vì đó chính là
  invariant chống chunk rỗng/label-lẫn của corpus 2.0.

  → Việc 2 = viết một **hàm cắt riêng cho nội dung crawl** (vd `_cut_permissive` hoặc tương đương),
  dùng chung phần tách heading nếu tiện, nhưng: (a) không raise khi thiếu `##` — fallback 1-chunk cả
  tài liệu; (b) không raise ở I7 — section rỗng thì bỏ qua, không tạo chunk rác, không chết cả file;
  (c) `{section:…}` xuất hiện tình cờ trong text crawl thì coi là text thường, không raise. Đây là lý
  do pd đề bài cho 1.5 hợp lý (viết hàm mới + test mới), nhưng cũng là chỗ dễ **rẻ hơn 1.5** nếu chỉ
  cần fallback tối thiểu — ứng viên để cắt 0.5 pd nói ở §0.1.

  **Câu hỏi mở, chưa tự quyết:** `doc_factory_core.SECTION_VOCAB` là từ vựng ĐÓNG (`{public, hr,
  finance, engineering}`) nhưng `_cut_document`/pipeline hiện **không** validate `role` qua vocab này
  (chỉ `load_corpus_v2` validate). Vậy nội dung crawler gán `section_role` nào? Nếu do người vận hành
  chọn sẵn từ 4 giá trị đó lúc cấu hình job crawl → không cần đổi gì thêm. Nếu cần role ngoài 4 giá trị
  → phải mở rộng vocab, việc đó KHÔNG có trong bảng đề bài, cần hỏi lại trước khi chốt scope việc 6.

### 0.4 Việc 4 — target đã xác định được bằng bằng chứng, không phải đoán
`kb.documents` (+ `kb.knowledge_bases`, `kb.chunk_pointers`) **đã có DDL** từ trước (kb#47), sống trong
`schema.py:156-258`, RLS `tenant_id` đã bật — nhưng **chưa ai ghi vào nó** (comment ngay trong file:
*"DDL tồn tại, CHƯA có writer nào"*). Đồng thời `kb.chunks` (bảng production hiện dùng) **không có cột
`doc_id`** — `Chunk` dataclass (`doc_factory_core.py`) chỉ có `chunk_id` (dạng `"{doc_id}#c{n}"`, doc_id
chỉ là tiền tố chuỗi, không phải cột). Bằng chứng độc lập xác nhận đây đúng là lỗ đang chặn SWE:

> `apps/studio/src/studio_app/routes/documents.py:16` (route `POST /api/admin/documents`, ghi thẳng
> vào `kb.chunks`) tự ghi: *"**Giới hạn đã biết:** chưa kiểm tra được `doc_id` đã tồn tại trước khi
> ghi."* — đúng vì không có đâu để tra: không cột `doc_id`, không bảng `kb.documents` có dữ liệu.

→ Việc 4 = (a) `ALTER TABLE kb.chunks ADD COLUMN IF NOT EXISTS doc_id TEXT`, backfill bằng tách
`chunk_id` tại `"#c"` cuối cùng (mọi chunk_id hiện có đều theo khuôn `"{doc_id}#c{n}"`, an toàn); (b)
bắt đầu **ghi thật** vào `kb.documents` (filename/section_role/chunk_count/status) ở đường ghi hiện có
(`routes/documents.py`) và đường mới (crawler, việc 6) — route SWE cần đọc chính bảng này để liệt kê
tài liệu. Không cần thiết kế lại DDL, DDL đã đúng hình từ kb#47.

---

## 1. Thứ tự thực thi đề xuất (khác thứ tự bảng, giữ nguyên phạm vi + pd từng việc)

| # | Việc | pd | Vì sao ở vị trí này |
|---|---|---|---|
| 1 | Đo hàng rào phòng ban (as_roles qua `/chat`) | 0.5 | Làm đầu — đo trước khi quyết cách vá việc 5, đúng đề bài |
| 2 | kb.documents + cột doc_id | 1.5 | Không phụ thuộc gì khác, **và đang chặn SWE** — đẩy lên sớm nhất có thể thay vì đợi giữa sprint |
| 3 | RLS cấp phòng ban | 1.0 | Ngay sau khi có số đo từ (1); đóng nợ S3 đã tự ghi trong `postgres.py` |
| 4 | Tiền xử lý | 1.5 | Cần xong TRƯỚC crawler — crawler tạo HTML/text thô, chunker cần input đã sạch để test thật |
| 5 | Chunker mới (permissive) | 1.5 | Test bằng input đã qua tiền xử lý (bước trên), tránh test chay trên text bẩn |
| 6 | Crawler | 2.5 | To nhất, rủi ro cao nhất (I/O mạng lần đầu) — chạy sau khi có preprocess+chunker để cắm thẳng vào pipeline, không phải mock |
| 7 | Đo lại recall | 1.0 | Cần corpus mới đã ổn định (sau 4,5,6) |
| 8 | Golden set (30 case, ≥8 refusal 2 trục) | 1.0 | Trục "khác phòng ban" chỉ có ý nghĩa SAU khi (3) đóng RLS thật — có thể chạy song song với 6/7 vì không phụ thuộc corpus crawl, chỉ phụ thuộc (3) |

Ghi chú: việc 2 (kb.documents/doc_id) đổi từ vị trí 4→2 trong thứ tự chạy; các việc còn lại giữ đúng
thứ tự logic gần với bảng gốc, chỉ khác việc 3 (tiền xử lý) chạy trước việc 6 (crawler) vì quan hệ
phụ thuộc dữ liệu tự nhiên (crawl → preprocess → chunk), dù bảng gốc liệt kê trước.

---

## 2. Ba câu hỏi cần chốt trước khi bắt đầu

1. **pd 10.5 vs ngân sách 10** — cắt 0.5 ở việc "chunker mới" (scope tối thiểu: chỉ fallback 1-chunk +
   bỏ raise I7, không làm gì thêm), hay giữ 10.5?
2. **SECTION_VOCAB đóng (`public/hr/finance/engineering`)** — nội dung crawler có luôn được gán 1 trong
   4 role này (do người cấu hình job chọn), hay cần vocab rộng hơn? Quyết định này ảnh hưởng trực tiếp
   input của việc 6.
3. Xác nhận việc 4 hiểu đúng là "**thêm cột + bắt đầu ghi** vào bảng `kb.documents` đã có DDL từ kb#47",
   không phải thiết kế bảng mới — nếu có tài liệu spec khác (vd một ERD/ticket riêng) nói khác đi, cần
   biết trước khi viết DDL migration.
