"""Ghi cache vector cho một provider API — chạy TAY, một lần, rồi commit `cache/`.

    export OPEN_ROUTER_API_KEY=...
    uv run --python 3.14 python packages/kb/tests/embedding-tests/record_provider_cache.py

Đây là bước DUY NHẤT trong bộ eval được phép ra mạng. Sau khi `cache/` đã commit, `compare_providers.py`
và mọi test chạy hoàn toàn offline từ `main` — đúng `kb#38` ("tái lập được từ main") và INV-4
("CI chạy 100% recorded fixtures").

Embed đúng hai thứ mà `_harness.build_report` sẽ hỏi tới, không hơn:

1. `chunk.embedding_input` của cả 800 chunk corpus 2.0 — **không phải `chunk.text`**. Đây là chuỗi
   đường ghi thật đem embed (`KbIngest.ingest`/`KbPipeline.embed_invoke`); embed `.text` ở đây là đo
   một hệ thống không tồn tại.
2. `case.query` của cả 300 case — CẢ validation lẫn test. Cache là kho vector thô, không phải kết
   quả đo; cắt nó theo split sẽ khiến chạy trên validation lại phải gọi API.

Idempotent: text đã có trong cache thì không gọi lại, nên chạy lại sau khi thêm case chỉ trả tiền
cho phần mới.
"""

from __future__ import annotations

import _harness as H
from providers import API_KEY_ENV, GeminiEmbedding
from studio_kb.doc_factory_v2 import load_corpus_v2


def texts_to_record() -> list[str]:
    chunks = load_corpus_v2(H.CORPUS_ROOT)
    queries = [c.query for c in H.load_cases()]
    return [c.embedding_input for c in chunks] + queries


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
