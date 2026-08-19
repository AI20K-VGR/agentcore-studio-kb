"""Fixture vector cho corpus Callisto (D7, DE) — **nguồn duy nhất** của vector 25 chunk.

`day-07.md:37` giao DE: *"Cấp fixtures embed/chunk cho stub (recorded vector Callisto); đảm bảo
`kb.search` dùng **cùng** fixtures"*. Module này là cả hai vế:

- **cấp fixture**: `build_fixture()` sinh, `dump_fixture()` tuần tự hoá, file
  `golden/embeddings-callisto-v0.json` là bản đã ghi.
- **"cùng fixtures"**: `load_callisto_embeddings()` là đường đọc DUY NHẤT. Ai cần vector Callisto —
  `kb.search` hôm nay, `KbPipeline.index` ở `db_plan.md`, bản cosine S2–S3 — đều gọi hàm này.
  **Cấm sha256 tại chỗ**: hai chỗ tự tính là hai nguồn sự thật, đúng vết `smoke-5.yaml` ↔
  `studio_evalhub.cli._demo_golden_set` (điểm gãy #8).

## Vì sao GHI RA FILE chứ không tính lúc gọi

`day-07.md:37` viết "**recorded** vector". `FakeEmbedding._vector`
(`apps/studio/src/studio_app/providers/fakes.py`) tính sha256 ngay trong `embed()` — tiện, nhưng nếu
fixture của DE cũng vậy thì không có gì "recorded" cả, và chữ đó thành nhãn sai. File đã ghi cho ba
thứ mà tính-lúc-gọi không cho:

1. Đọc được bằng mắt và review được trong PR.
2. `tests/test_embedding_fixture.py` so được **file** với **thứ bộ sinh tạo ra bây giờ** — đổi công
   thức mà quên re-record thì đỏ, thay vì hai bên cùng trôi và luôn bằng nhau.
3. Khi gateway thật về, re-record là thay nội dung file; mọi bên đọc đều đổi theo, không ai phải sửa
   code.

## Vì sao bag-of-words, KHÔNG phải sha256 của `FakeEmbedding`

Bản đầu của module này chép công thức sha256 từ `FakeEmbedding` (`apps/studio`) với lý do "cả
workspace ra cùng con số". Sai, và đo được là sai: `kb.chunks.embedding` có index HNSW
`vector_cosine_ops` (`schema.py`), và `kb.search` bản S2–S3 xếp hạng bằng cosine — mà vector sha256
**không có cấu trúc cosine nào**. Đo trên 25 chunk Callisto:

    sha256         cosine cùng doc 0.754 · khác doc 0.752 → chênh +0.002   (nhiễu)
    bag-of-words   cosine cùng doc 0.885 · khác doc 0.867 → chênh +0.018

Nạp vector không có cấu trúc cosine vào một index cosine thì mọi phép kiểm ranking về sau vẫn
"chạy" nhưng không chứng minh gì.

Công thức ở đây lấy từ `BagOfWordsEmbedding` — bản kb đã tự chọn từ D4 cho chính test ingest
pgvector của mình (`tests/test_pg_kb.py`), và docstring bản đó đã ghi rõ **không** lấy
`FakeEmbedding` làm chuẩn vì `.importlinter` cấm `studio_kb` chạm `studio_app`. Tức kb quyết chuyện
này một lần rồi; bản sha256 mới là bản đi ngược.

Từ D7 công thức sống ở ĐÂY, `test_pg_kb.py` import lại — một nguồn, không hai bản.

Vẫn phải nói rõ: đây **không** phải embedding ngữ nghĩa. Bag-of-words 8 chiều chỉ bắt được "dùng
chung từ", không bắt được nghĩa. Đừng dựng kết luận về chất lượng retrieval trên nó, và khi gateway
thật về thì **re-record**, không so điểm cosine cũ với mới.

Hệ quả phải biết: fixture này **không còn khớp** `FakeEmbedding`. Chấp nhận được — `FakeEmbedding`
tự khai *"CI fixture — KHÔNG phải deliverable AIE-1"*, là double kiểm hình dạng, không nằm trên
đường chạy thật nào. Ràng buộc còn lại giữa hai bên chỉ là **số chiều**, và đó là Q-B trong
`plans/day07_plan.md`.

## Chạy lại

    uv run python packages/kb/scripts/record_embeddings.py   # ghi đè, phải ra byte-identical

`git diff` sau lệnh đó mà khác rỗng nghĩa là corpus hoặc công thức đã đổi — re-record có chủ đích
thì commit, còn không thì đó là hồi quy. Logic ở module này để test import được; phần gọi nằm ở
script, xem docstring script để biết vì sao không dùng `python -m`.
"""

from __future__ import annotations

import hashlib
import json
import math
from functools import lru_cache
from pathlib import Path

from studio_kb.doc_factory import load_callisto
from studio_kb.schema import EMBEDDING_DIM

# `golden/` chứ không phải `tests/fixtures/`: file này là dữ liệu chung cho cả workspace (stub của
# AIE-1, ingest của `db_plan.md`), không phải phụ kiện của một suite test. Nằm cạnh `smoke-10.yaml`
# vì cùng loại — artifact do DE gán nhãn và các quadrant khác tiêu thụ.
FIXTURE_PATH = Path(__file__).resolve().parent / "golden" / "embeddings-callisto-v0.json"

FIXTURE_REF = "callisto-embeddings-v0"

_DERIVATION = (
    "bag-of-words: blake2b(token) băm vào EMBEDDING_DIM ô, chuẩn hoá L2 "
    "— tổng hợp deterministic, KHÔNG phải output model"
)


def derive_vector(text: str, dim: int = EMBEDDING_DIM) -> list[float]:
    """Sinh vector `dim` chiều từ `text`, deterministic tuyệt đối.

    Bag-of-words: mỗi token băm vào một ô, đếm, rồi chuẩn hoá L2. Văn bản giống nhau ra vector
    giống nhau; văn bản **chia sẻ từ thì gần nhau theo cosine** — tính chất này là lý do tồn tại
    của cả hàm, xem "Vì sao bag-of-words" ở docstring module.

    `blake2b` chứ KHÔNG phải `hash()` dựng sẵn: `hash()` của Python ngẫu nhiên hoá theo tiến trình
    (`PYTHONHASHSEED`), nên vector sẽ đổi giữa các lần chạy và fixture "đã ghi" thành nhấp nháy.

    Ca biên vector 0 (text rỗng, hoặc chỉ có khoảng trắng): cosine chia cho 0 → pgvector trả `NaN`
    và thứ hạng thành vô nghĩa. Trả `[1, 0, …]` — một vector hợp lệ bất kỳ — thay vì gốc toạ độ.
    """
    buckets = [0.0] * dim
    for token in text.lower().split():
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=2).digest()
        buckets[int.from_bytes(digest, "big") % dim] += 1.0
    norm = math.sqrt(sum(x * x for x in buckets))
    if norm == 0.0:
        return [1.0] + [0.0] * (dim - 1)
    return [x / norm for x in buckets]


def build_fixture() -> dict[str, object]:
    """Dựng nội dung fixture từ corpus Callisto đang có trên đĩa.

    Khoá là **`chunk_id`**, không phải text. Đây chính là điều kiện nghiệm thu "cùng fixtures" của
    `plans/day07_plan.md` §0.1①: hai bên phải thống nhất *vector nào thuộc chunk nào*. Khoá theo text
    thì `StubEmbedding` (nhận `texts: list[str]`) vẫn tra được, nhưng `kb.search` không đối chiếu
    ngược được với `chunk_id` mà nó trả ra.

    Ghi cả `dim` vào file thay vì để người đọc suy từ độ dài mảng: lệch số chiều phải đỏ ở một dòng
    assert, không phải vỡ sâu trong pgvector lúc `index`.
    """
    chunks = sorted(load_callisto(), key=lambda c: c.chunk_id)
    return {
        "fixture_ref": FIXTURE_REF,
        "dim": EMBEDDING_DIM,
        "derivation": _DERIVATION,
        "corpus_ref": "docs/callisto/ — 42 doc / 140 chunk (Callisto Handbook, D12)",
        "vectors": {chunk.chunk_id: derive_vector(chunk.text) for chunk in chunks},
    }


def dump_fixture(fixture: dict[str, object] | None = None) -> str:
    """Tuần tự hoá thành text ổn định — cùng đầu vào luôn ra **cùng byte**.

    `sort_keys` + `indent=2` + `ensure_ascii=False` + newline cuối: bốn thứ này là điều kiện để
    `test_embedding_fixture.py` so được file với bản sinh lại. Thiếu `sort_keys` thì thứ tự khoá phụ
    thuộc thứ tự chèn và phép so thành hên xui.
    """
    return (
        json.dumps(fixture if fixture is not None else build_fixture(), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    )


@lru_cache(maxsize=1)
def load_callisto_embeddings() -> dict[str, list[float]]:
    """Đọc `chunk_id -> vector` từ file đã ghi. **Đây là đường đọc duy nhất.**

    Đọc FILE, không gọi `build_fixture()`: nếu hàm này sinh lại thì nó chỉ chứng minh công thức tự
    khớp với chính nó, và file check-in thành đồ trang trí. Người tiêu thụ phải thấy đúng thứ đã
    được review trong PR.

    Cache một bản (`lru_cache`) — file bất biến trong một lần chạy. Test cần đọc lại sau khi ghi đè
    thì gọi `load_callisto_embeddings.cache_clear()`.
    """
    raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    vectors: dict[str, list[float]] = raw["vectors"]
    return vectors
