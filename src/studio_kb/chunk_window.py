"""Cutter cửa sổ trượt theo SỐ TỪ — dùng cho nội dung tự do (upload/crawl), KHÔNG phải corpus 2.0
curate tay (`doc_factory_v2._cut_document`/`load_corpus_v2` giữ nguyên, không đụng tới).

Xem `plans/multiformat_chunker_plan.md` cho toàn bộ số liệu đo và lý do chọn tham số. Tóm tắt:
`gemini-embedding-001` có trần **2048 token input** (khác `schema.EMBEDDING_DIM=2048` — chiều
OUTPUT, trùng số NGẪU NHIÊN). Repo không có tokenizer nào và cố ý KHÔNG thêm `tiktoken` (kéo theo
`requests`+4 gói, và lần gọi đầu tải ~1.68MB qua mạng — phá INV-4 "CI chạy offline"), nên đơn vị
đếm ở đây là **SỐ TỪ** (`str.split()`), không phải token thật.

Đo bằng `tiktoken` (cl100k_base, CHỈ dùng để đo một lần ngoài repo, không phải dependency) trên 15
file thật `docs/callisto/*.md` (tiếng Việt có dấu): tỉ lệ trung bình **2.20 token/từ**, xấu nhất đo
được **2.32 token/từ**. Ở `WORDS_PER_CHUNK=850`, ratio xấu nhất cho ~1972 token — dưới trần 2048,
còn đệm ~76 token cho sai số ước lượng (tiếng Việt bị BPE tách vụn hơn latin thuần nhiều, ~1.3
token/từ).

**850/170 (không phải 500/100 hay 200/50) — chốt bằng A/B/C benchmark thật, không phải suy luận.**
Từng thử hạ xuống 500/100 với giả thuyết "chunk ngắn hơn bắt ngữ nghĩa chính xác hơn" (ít pha loãng
vector) — đúng một phần nhưng có giới hạn: đo A/B/C thật (100 câu hỏi, 3 cấu hình, embedding thật
`gemini-embedding-001`, xem `chunking/report.md` ở repo cha) cho thấy hẹp hơn làm TĂNG số lượng chunk
cạnh tranh (200/50 sinh 140 chunk từ cùng corpus so với 33 chunk ở 850/170), khiến nhiều chunk "gần
đúng chủ đề" chen vào top-k — điểm cosine cao hơn không đồng nghĩa tìm đúng nhiều hơn. Stress test bổ
sung (kéo dài ngữ cảnh cần thiết lên 150 từ, mô phỏng câu trả lời nhiều điều khoản) cho kết quả dứt
khoát: 850/170 không suy giảm gì (Hit@1 không đổi), còn 200/50 sụp đổ (Hit@1 rớt hơn nửa, tỉ lệ giữ
nguyên vẹn ngữ cảnh trong 1 chunk chỉ còn 31.6%). 500/100 nằm giữa, vẫn suy giảm đáng kể so với
850/170. Overlap giữ tỉ lệ ~20% (`WORDS_OVERLAP=170`) để không mất ngữ cảnh nối tiếp qua ranh giới
cắt."""

from __future__ import annotations

import re
from uuid import UUID

from studio_kb.doc_factory_core import Chunk

WORDS_PER_CHUNK = 850
"""Số từ (`str.split()`) mỗi chunk — xem docstring module cho phép đo ra con số này."""

WORDS_OVERLAP = 170
"""Số từ trùng giữa 2 chunk liền kề (~20% `WORDS_PER_CHUNK`), giữ ngữ cảnh nối tiếp qua ranh giới cắt."""


def cut_window(
    text: str,
    doc_id: str,
    tenant_id: UUID,
    role: str,
    *,
    size: int = WORDS_PER_CHUNK,
    overlap: int = WORDS_OVERLAP,
) -> list[Chunk]:
    """Cắt `text` thành các chunk cửa sổ trượt `size` từ, overlap `overlap` từ giữa 2 chunk liền kề.

    Đơn vị cắt là `str.split()` (khoảng trắng) — không bao giờ cắt giữa một từ, vì ranh giới đã có
    sẵn từ chính phép tách. `chunk_id = "{doc_id}#c{n}"` — CÙNG khuôn với `_cut_document`, để
    `_UPSERT`/`ON CONFLICT DO UPDATE` idempotent y hệt đường corpus 2.0 (`postgres.py`).

    Deterministic tuyệt đối theo `(text, size, overlap)`: cắt lại đúng 1 văn bản luôn ra đúng cùng
    số chunk + cùng `chunk_id` — bắt buộc để re-upload không sinh `chunk_id` mồ côi (xem giới hạn
    đã biết ở `routes/documents.py:16`, apps/studio).

    Văn bản rỗng/chỉ khoảng trắng → trả `[]` (không raise) — khác `_cut_document` (I7 raise ở section
    rỗng): nội dung tự do không có khái niệm "section", nên không có gì để raise thay cho nó.
    """
    if size <= 0 or overlap < 0 or overlap >= size:
        raise ValueError(f"cut_window: size={size} overlap={overlap} không hợp lệ (cần 0 <= overlap < size)")

    # Giữ VỊ TRÍ của từng từ trong văn bản gốc, không chỉ giữ mặt chữ.
    #
    # `text.split()` + `" ".join(...)` ép mọi chunk thành một dòng, và cấu trúc Markdown chết ngay
    # tại đây: `## Nghỉ phép năm` thôi là tiêu đề, chỉ còn là mấy từ giữa câu. Bộ sinh golden đọc
    # tiêu đề để đặt câu hỏi, nên tài liệu UPLOAD ra bộ rỗng trong khi corpus seed (nạp qua đường
    # khác, còn xuống dòng) ra bộ tốt — hai đường, hai kết quả, không có gì báo.
    #
    # Cửa sổ vẫn đếm theo TỪ y như cũ, nên `chunk_id` và số chunk của mọi tài liệu đã nạp không đổi;
    # chỉ văn bản bên trong mỗi chunk lấy lại khoảng trắng gốc bằng cách cắt theo offset.
    spans = [(m.start(), m.end()) for m in re.finditer(r"\S+", text)]
    if not spans:
        return []
    words = spans

    stride = size - overlap
    chunks: list[Chunk] = []
    start = 0
    n = 0
    while start < len(words):
        window = words[start : start + size]
        n += 1
        chunks.append(
            Chunk(
                chunk_id=f"{doc_id}#c{n}",
                text=text[window[0][0] : window[-1][1]],
                tenant_id=tenant_id,
                section_role=role,
                doc_id=doc_id,
            )
        )
        if start + size >= len(words):
            break
        start += stride
    return chunks
