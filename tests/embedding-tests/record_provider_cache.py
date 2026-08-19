"""Ghi cache vector cho một provider API — chạy TAY, một lần, rồi commit `cache/`.

    export OPEN_ROUTER_API_KEY=...
    uv run --python 3.14 python packages/kb/tests/embedding-tests/record_provider_cache.py

Đây là bước DUY NHẤT trong bộ eval được phép ra mạng. Sau khi `cache/` đã commit, `compare_providers.py`
và mọi test chạy hoàn toàn offline từ `main` — đúng `kb#38` ("tái lập được từ main") và INV-4
("CI chạy 100% recorded fixtures").

## Bề mặt được phủ — khai tường minh, mỗi bề mặt một hàm

`harness_texts()` — thứ `_harness.build_report` hỏi tới:

1. `chunk.embedding_input` của cả 800 chunk corpus 2.0 — **không phải `chunk.text`**. Đây là chuỗi
   đường ghi thật đem embed (`KbIngest.ingest`/`KbPipeline.embed_invoke`); embed `.text` ở đây là đo
   một hệ thống không tồn tại.
2. `case.query` của cả 300 case — CẢ validation lẫn test. Cache là kho vector thô, không phải kết
   quả đo; cắt nó theo split sẽ khiến chạy trên validation lại phải gọi API.

`golden_v2_texts()` — query của golden-set 2.0 (22 query phân biệt / 30 case). **Thêm ở kb#40 sau
phản hồi AIE-2**: bản đầu của script này tự khai "đúng hai thứ harness hỏi tới, không hơn", nên
0/22 query golden 2.0 nằm trong cache và mọi đường chấm golden 2.0 qua provider ĐÃ CHỐT
(`gemini-embedding-001`) đều nổ `MissingVectorError`. Fail-closed chạy đúng thiết kế — nhưng giới
hạn ấy không được viết ở đâu, nên chỉ lộ ra khi có người đâm vào. Phía chunk KHÔNG phải thêm gì:
cả 22 `expected_citation` của golden 2.0 đều là chunk corpus 2.0, đã nằm trong `harness_texts()`.

**CỐ Ý không phủ** golden-set 1.0 (`golden_set.py`) và grid queries `GQ-` (`grid_queries.py`):
chúng chạy trên corpus **1.0** (140 chunk) mà cache không giữ vector chunk 1.0 nào, nên ghi thêm
query của chúng chẳng mua được gì — muốn chấm 1.0 thì phải ghi cả corpus 1.0, là một quyết định
riêng (và hướng đi hiện tại là di dời 1.0 sang 2.0, xem `plans/embedding_eval_harness_plan.md`).

Idempotent: text đã có trong cache thì không gọi lại, nên chạy lại sau khi thêm case chỉ trả tiền
cho phần mới.

Xung đột merge ở `cache/*.index.json` thì **re-record, đừng giải bằng tay** — chỉ số dòng phải là
song ánh với `0..N-1` (xem `test_hai_khoa_tro_cung_mot_dong_thi_bao_loi`).
"""

from __future__ import annotations

import _harness as H
from providers import API_KEY_ENV, GeminiEmbedding
from studio_kb.doc_factory_v2 import load_corpus_v2
from studio_kb.golden_set_v2 import GOLDEN_CASES_V2


def harness_texts() -> list[str]:
    """Text mà `_harness.build_report` sẽ hỏi tới: 800 `embedding_input` + query của 300 case."""
    chunks = load_corpus_v2(H.CORPUS_ROOT)
    queries = [c.query for c in H.load_cases()]
    return [c.embedding_input for c in chunks] + queries


def golden_v2_texts() -> list[str]:
    """Query của golden-set 2.0. Chỉ query — chunk phía đáp án đã nằm trong `harness_texts()`."""
    return [c.query for c in GOLDEN_CASES_V2]


def texts_to_record() -> list[str]:
    """Hợp của mọi bề mặt đã khai. Thêm bề mặt = thêm hàm rồi nối vào ĐÂY, không sửa lời gọi."""
    return harness_texts() + golden_v2_texts()


if __name__ == "__main__":
    import os
    import sys

    if not os.environ.get(API_KEY_ENV):
        sys.exit(f"thiếu ${API_KEY_ENV} — export rồi chạy lại")

    provider = GeminiEmbedding(allow_network=True)
    texts = texts_to_record()
    unique = list(dict.fromkeys(texts))
    missing = [t for t in unique if provider.cache.get(t) is None]
    print(f"{provider.name}: {len(texts)} text ({len(unique)} phân biệt), {len(missing)} chưa có trong cache")
    if not missing:
        print("cache đã đủ — không gọi API")
        raise SystemExit(0)

    provider.embed(texts)
    provider.cache.flush()
    print(f"xong: {len(provider.cache)} vector × {provider.cache.dim} chiều = {provider.cache.size_bytes / 1e6:.1f} MB")
