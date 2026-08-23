# Plan — chunker đa định dạng (.md/.txt/.docx), cửa sổ 850 từ/overlap 170 từ

> **Ngày lập:** 2026-08-23 · **Bút:** DE · **Thuộc Sprint 3, việc #2** (`plans/sprint3_plan.md` §0.3) —
> thay thế thiết kế "permissive heading-cutter" bàn trước đó bằng **cửa sổ trượt cố định theo SỐ TỪ**,
> áp dụng đồng nhất cho cả 3 định dạng. **Mọi câu hỏi mở đã chốt (2026-08-23) — sẵn sàng để code.**

## Tham số CHỐT CUỐI

| | Giá trị | Vì sao |
|---|---|---|
| Định dạng | `.md`, `.txt`, `.docx` (KHÔNG `.doc` nhị phân cũ) | `.doc` cần công cụ ngoài (LibreOffice/antiword), không portable qua CI — để riêng, không gộp |
| Đơn vị đếm | **SỐ TỪ** (`text.split()`), KHÔNG dùng token thật/`tiktoken` | Đã cân nhắc thêm `tiktoken` — bị loại vì: (a) kéo theo 7 gói transitive (`requests`+4) vào `kb` vốn chỉ có 2 dep; (b) **lần gọi đầu tải ~1.68MB qua mạng** từ blob OpenAI, phá thẳng INV-4 (CI phải chạy offline) trừ khi vendor cache — chi phí bảo trì không đáng cho một bộ đếm ước lượng |
| Chunk size | **850 từ** | |
| Overlap | **170 từ** (đúng tỉ lệ ~20%) | |
| Stride | 850 − 170 = **680 từ/bước** | |

### Vì sao 850/170, không phải số tròn "cho gọn" — đã ĐO trên corpus thật

Trần cứng cần né là **2048 token input** của `gemini-embedding-001` (khác `DIM=2048` — chiều output,
hai con số trùng nhau NGẪU NHIÊN, xem giải thích lượt trước). Đo tỷ lệ từ→token bằng `tiktoken`
(cl100k_base, **chỉ dùng để đo 1 lần trong `/tmp`, không đưa vào code/dependency**) trên 15 file thật
`docs/callisto/*.md` (văn bản tiếng Việt có dấu):

```
mean ratio = 2.20 token/từ   (min 2.03 · max 2.32)
```

Tiếng Việt có dấu bị BPE tách vụn hơn tiếng Anh nhiều (~1.3 token/từ) — đây là lý do 1000 từ (phương
án đầu) bị loại: 1000 × 2.2 ≈ 2200 token, **đã vượt trần** ngay ở mean, chưa cần tới ratio xấu nhất.

Ở **850 từ**, kể cả ratio xấu nhất đo được (2.32): 850 × 2.32 ≈ **1972 token** — vẫn dưới 2048, còn
đệm ~76 token cho sai số của `text.split()` so với tokenizer thật (Gemini, không phải cl100k_base —
`tiktoken` chỉ là proxy đo lường, độ lệch tuyệt đối chưa biết chính xác, nên đệm này KHÔNG được coi
là chắc chắn tuyệt đối, chỉ là biên an toàn tốt hơn hẳn so với cắt khít 2048).

---

## 1. Hai tầng: extract (định dạng → text) rồi cut (text → Chunk)

Giữ nguyên tắc đã áp dụng cho `_cut_document`: **một cutter, nhiều extractor**, không viết 3 bộ cắt
riêng cho 3 định dạng.

```
file (.md/.txt/.docx) → [extractor theo đuôi file] → plain text
                                                          │
                                                          ▼
                                          [cutter cửa sổ trượt 850/170 — DÙNG CHUNG]
                                                          │
                                                          ▼
                                              list[Chunk] (chunk_id="{doc_id}#c{n}")
```

- `.md`, `.txt`: đọc thẳng UTF-8, không xử lý gì thêm ở tầng extract (cú pháp markdown giữ nguyên
  literal trong text — cutter không parse heading, xem §4 vì sao khác thiết kế heading-cutter cũ).
- `.docx`: cần `python-docx` (đọc XML/zip, thuần Python, không cần binary hệ thống) — extractor đọc
  từng `paragraph`, nối bằng `\n`. Không giữ heading style, chỉ lấy text.

## 2. Cutter cửa sổ trượt — nguyên tắc

```python
def _cut_window(text: str, doc_id: str, tenant_id: UUID, role: str,
                 *, size: int = 850, overlap: int = 170) -> list[Chunk]:
    words = text.split()
    stride = size - overlap
    chunks = []
    for n, start in enumerate(range(0, len(words), stride), start=1):
        window = words[start:start + size]
        if not window:
            break
        chunks.append(Chunk(
            chunk_id=f"{doc_id}#c{n}",
            text=" ".join(window),
            tenant_id=tenant_id,
            section_role=role,
        ))
        if start + size >= len(words):
            break
    return chunks
```

Điểm cần giữ khi viết thật:
- **Đơn vị cắt là `str.split()`** (khoảng trắng) — không cắt giữa ký tự/từ, tự động an toàn vì cắt
  theo ranh giới từ đã có sẵn từ `split()`. Không cần thêm logic tìm-ranh-giới-câu như bản token trước.
- **Chunk cuối cùng có thể ngắn hơn `size`** (phần dư tài liệu) — hợp lệ, không cần đệm.
- **Tài liệu ngắn hơn 1 cửa sổ** → đúng 1 chunk, không overlap — nhánh biên cần test riêng.
- **Deterministic tuyệt đối** theo `(text, size, overlap)` — re-upload cùng file phải ra đúng cùng số
  chunk + cùng `chunk_id`, để `ON CONFLICT DO UPDATE` (`_UPSERT`) idempotent đúng như thiết kế hiện
  tại, không sinh `chunk_id` mồ côi.

## 3. Khác gì thiết kế "permissive heading-cutter" bàn trước đó (Sprint 3 §0.3)?

Bản trước định giữ logic cắt-theo-`##`-heading của `_cut_document` nhưng nới lỏng raise. Bản NÀY (cửa
sổ trượt cố định theo từ) **thay thế hẳn** ý tưởng đó cho đường upload/crawl tự do — không parse
heading nữa, đơn giản hơn, không còn 3 nhánh raise (I5 `{section:…}`, I7 rỗng, "không có heading") cần
né. Hệ quả tốt: gọn hơn, giúp đóng luôn phần lệch 0.5 pd đã nêu ở `sprint3_plan.md §0.1`. Hệ quả cần
chấp nhận: mất lợi thế "chunk luôn khớp trọn 1 mục nội dung" mà corpus 2.0 curate tay đang có — bù lại
bằng overlap 170 từ. Đánh đổi này CHỈ áp dụng cho nội dung KHÔNG curate tay (upload/crawl); **không
đụng** `_cut_document`/`load_corpus_v2` — corpus Callisto 2.0 giữ nguyên.

`doc_id`/`tenant_id`/`section_role` vẫn nhận qua tham số y hệt chữ ký `KbPipeline.chunker` hiện có —
không đổi seam, chỉ đổi thuật toán cắt bên trong khi gọi cho nguồn "tự do" thay vì nguồn "corpus 2.0
curate tay".

## 4. Vị trí code đề xuất

- `studio_kb/extract.py` (mới) — `extract_text(filename: str, raw: bytes) -> str`, dispatch theo đuôi
  file (`.md`/`.txt` decode UTF-8 thẳng; `.docx` qua `python-docx`, thêm vào `pyproject.toml`). Raise
  rõ ràng nếu đuôi file không hỗ trợ (fail-closed, không đoán định dạng).
- `studio_kb/chunk_window.py` (mới) — `cut_window(text, doc_id, tenant_id, role, *, size=850,
  overlap=170) -> list[Chunk]`. Tái dùng `Chunk` từ `doc_factory_core` (không định nghĩa lại).
- `KbPipeline.chunker` (`pipeline.py`) — thêm nhánh gọi `cut_window` thay vì `_cut_document` khi nguồn
  là upload/crawl tự do (cách phân biệt 2 đường: tham số cờ, hoặc 2 method riêng — quyết khi code,
  không phá chữ ký 5-method hiện có của seam).

## 5. Test cần có trước khi coi là xong

1. Idempotent: cắt cùng 1 file 2 lần → cùng số chunk, cùng `chunk_id`.
2. Biên: tài liệu ngắn hơn 1 cửa sổ (< 850 từ) → đúng 1 chunk, không lỗi chia 0.
3. Overlap đúng: 170 từ cuối chunk N trùng 170 từ đầu chunk N+1.
4. Số từ mỗi chunk (trừ chunk cuối) đúng bằng 850 — assert cứng, không lệch do làm tròn.
5. `.docx` (kể cả có heading style) vẫn ra text hợp lý, không mất nội dung.
6. Đuôi file không hỗ trợ (`.doc`, `.pdf`, …) → raise rõ ràng, không âm thầm bỏ qua.
7. Chạy `cut_window` trên vài file thật `docs/callisto/*.md` (đã biết ratio ~2.2 token/từ) — assert
   không chunk nào (ước lượng bằng `len(text.split()) * 2.32`, ratio xấu nhất đã đo) vượt 2048 token.
