"""Provider embedding ỨNG VIÊN cho harness — hiện có `GeminiEmbedding` (qua OpenRouter).

## Vì sao ở `tests/`, không phải trong `studio_kb`

`.importlinter` cấm `studio_kb` chạm `studio_app` (nơi giữ settings/API key), và thêm
`google-genai`/HTTP client vào dependency của package chỉ để đo một lần là kéo cả một cây phụ thuộc
vào wheel production. Đây là **dụng cụ đo**, đúng chỗ của nó là test code.

## Vì sao KHÔNG phải method `embed()` trên `GeminiProvider` của apps/studio

`apps/studio/tests/test_providers.py:39` assert `not hasattr(provider, "embed")` — F3, ranh giới
provider. Class riêng ở đây không đụng vào ràng buộc đó.

## Vì sao OpenRouter chứ không gọi thẳng Google

`embedding_report.md` §Vận hành ghi nhận sự cố thật khi gọi free-tier trực tiếp: 100 request/phút
VÀ 1000 request/ngày — dính cạn quota giữa chừng, phải đổi API key để chạy nốt. OpenRouter
(`$0.15/M token`) không có giới hạn ngày kiểu đó. Đã xác nhận trực tiếp: endpoint
`/api/v1/embeddings` nhận `dimensions: 2048` và trả đúng 2048 chiều.
"""

from __future__ import annotations

import json
import math
import os
import urllib.error
import urllib.request

from _vector_cache import VectorCache

OPENROUTER_URL = "https://openrouter.ai/api/v1/embeddings"
API_KEY_ENV = "OPEN_ROUTER_API_KEY"

GEMINI_MODEL = "google/gemini-embedding-001"
GEMINI_DIM = 2048
"""Số chiều ĐÃ CHỐT — xem `plans/real_embedding_plan.md` §2.

2048 vượt trần HNSW của pgvector (2000, đã probe: `vector(2001)` bị từ chối), nên nó chỉ hợp lệ VÌ
quyết định bỏ HNSW đi kèm. Hai con số này khoá vào nhau: ai định bật lại index phải hạ chiều xuống
≤2000 (nấc MRL khuyến nghị gần nhất là 1536) và đo lại, không phải chỉ thêm một câu `CREATE INDEX`.
"""

_BATCH = 90
"""Số text mỗi lần gọi. Giữ vừa phải để một lần đứt mạng chỉ mất một lô, không mất cả 1100 vector —
`flush()` chạy sau MỖI lô nên tiến độ luôn được ghi xuống đĩa."""


def l2_normalize(vector: list[float]) -> list[float]:
    """Chuẩn hoá L2. Vector 0 trả nguyên (không chia cho 0).

    **Bắt buộc với `gemini-embedding-001` ở số chiều ≠ 3072.** Docs Google: *"If you are using
    `gemini-embedding-001`, you must manually normalize non-3072 dimensions"* — API chỉ chuẩn hoá
    sẵn ở 3072 gốc; cắt Matryoshka xuống 2048 thì trả về vector CHƯA chuẩn hoá.

    Hiện tại chưa có gì hỏng nếu bỏ qua bước này: cosine bất biến với tỉ lệ, và cả `_harness.cosine`
    lẫn toán tử `<=>` của pgvector đều chia cho norm. Chuẩn hoá ở đây là **phòng thủ**: ngày ai đó
    đổi `<=>` sang `<#>` (inner product) cho nhanh, vector chưa chuẩn hoá sẽ cho thứ hạng sai một
    cách hoàn toàn im lặng — không exception, không test đỏ, chỉ là kết quả tệ đi.
    """
    norm = math.sqrt(sum(x * x for x in vector))
    if norm == 0.0:
        return vector
    return [x / norm for x in vector]


class MissingVectorError(RuntimeError):
    """Cache thiếu text mà mạng lại không được phép gọi.

    Cố tình KHÔNG rơi về một provider khác: im lặng thay thế provider là cách một lần chạy báo cáo
    số của `dim-8` dưới nhãn `gemini-embedding-001` mà CI vẫn xanh.
    """


class GeminiEmbedding:
    """`gemini-embedding-001` qua OpenRouter, đọc-ghi qua `VectorCache`.

    Mặc định **offline**: chỉ đọc cache. Gọi mạng phải bật tường minh (`allow_network=True`) — nhờ
    vậy `pytest` không bao giờ vô tình quay ra ngoài, đúng INV-4 (CI chạy 100% recorded fixtures).
    """

    def __init__(
        self,
        *,
        model: str = GEMINI_MODEL,
        dim: int = GEMINI_DIM,
        allow_network: bool = False,
        cache: VectorCache | None = None,
    ) -> None:
        self.name = f"{model.rsplit('/', 1)[-1]}-d{dim}"
        self.model = model
        self.dim = dim
        self._allow_network = allow_network
        self._cache = cache or VectorCache(self.name, model=model, dim=dim)

    @property
    def cache(self) -> VectorCache:
        return self._cache

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Trả vector ĐÃ CHUẨN HOÁ, đúng thứ tự `texts`.

        Text trùng nhau trong cùng lô chỉ gọi API MỘT lần (dedupe theo nội dung) — 800 chunk của
        corpus 2.0 có câu lặp lại, trả tiền hai lần cho cùng một chuỗi là vô ích.
        """
        missing = [t for t in dict.fromkeys(texts) if self._cache.get(t) is None]
        if missing:
            if not self._allow_network:
                raise MissingVectorError(
                    f"{len(missing)}/{len(set(texts))} text chưa có trong cache "
                    f"({self._cache.model}, dim={self._cache.dim}) và `allow_network=False`. "
                    f"Chạy `record_provider_cache.py` với {API_KEY_ENV} để ghi cache."
                )
            self._fetch_into_cache(missing)
        # Dựng thẳng rồi NỔ nếu thiếu — không lọc `None`. Bản lọc trả về list ngắn hơn và lệch
        # pha thay vì báo lỗi: caller sẽ gán vector của text i cho text i+1 trở đi. Hôm nay chưa
        # với tới được (thiếu ⇒ raise hoặc fetch ở trên), nhưng thứ duy nhất cứu caller là
        # `zip(..., strict=True)` bên `build_report` — tức may, không phải thiết kế. Đây đúng chỗ
        # `MissingVectorError` được dựng làm cửa chặn cứng, nên nó phải chặn ở đây luôn.
        out: list[list[float]] = []
        for text in texts:
            vector = self._cache.get(text)
            if vector is None:  # pragma: no cover — bất biến, giữ làm cửa chặn chứ không phải nhánh sống
                raise MissingVectorError(f"vector biến mất khỏi cache ngay sau khi ghi: {text[:60]!r}")
            out.append(vector)
        return out

    def _fetch_into_cache(self, texts: list[str]) -> None:
        for start in range(0, len(texts), _BATCH):
            batch = texts[start : start + _BATCH]
            for text, vector in zip(batch, self._call_api(batch), strict=True):
                self._cache.put(text, l2_normalize(vector))
            self._cache.flush()  # sau MỖI lô — đứt giữa chừng không mất tiến độ đã trả tiền

    def _call_api(self, batch: list[str]) -> list[list[float]]:
        api_key = os.environ.get(API_KEY_ENV)
        if not api_key:
            raise MissingVectorError(f"thiếu ${API_KEY_ENV} — không gọi API được")
        request = urllib.request.Request(  # noqa: S310 — URL là hằng số ở trên, không nhận từ input
            OPENROUTER_URL,
            data=json.dumps({"model": self.model, "input": batch, "dimensions": self.dim}).encode(),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=120) as response:  # noqa: S310
            payload = json.loads(response.read())
        data = payload["data"]
        if len(data) != len(batch):
            raise RuntimeError(f"API trả {len(data)} vector cho {len(batch)} text")
        # Sắp lại theo `index` chứ không tin thứ tự trả về: spec OpenAI-compatible cho phép trả
        # không theo thứ tự, và lệch một nấc ở đây là gán sai vector cho MỌI text sau đó — hỏng câm.
        return [item["embedding"] for item in sorted(data, key=lambda d: d["index"])]
