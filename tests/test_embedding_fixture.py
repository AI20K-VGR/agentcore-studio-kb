"""Canh fixture vector Callisto không trôi khỏi corpus (D7, DE).

Bốn assert, mỗi cái bắt một kiểu trôi khác nhau — không phải bốn cách viết lại cùng một phép kiểm.
`plans/day07_plan.md` §D7-2 giải thích vì sao cần cả bốn.

Ba nguồn có thể sinh vector trong workspace: fixture này (DE) · `FakeEmbedding`
(`apps/studio`, CI fixture) · `StubEmbedding` (AIE-1, D7). Comment `schema.py` đã dặn re-pin
`EMBEDDING_DIM` và `FakeEmbedding.dim` cùng lúc — tức rủi ro trôi đã được nhận diện từ trước, chỉ
chưa có test nào canh. File này canh phần trong tầm với của kb.

**Cố ý KHÔNG assert `FakeEmbedding.dim` ở đây.** `.importlinter` xếp `studio_kb` và `studio_app`
khác tầng; một `import studio_app` trong test của kb sẽ làm đỏ `lint-imports`. Phép so ba-chiều đó
phải đặt ở `tests/` repo cha hoặc `apps/studio/tests` — chỗ duy nhất nhìn được cả hai. Đó là **Q-B**
trong plan D7.
"""

from __future__ import annotations

import json
import math

from studio_kb.doc_factory import load_callisto
from studio_kb.embeddings import (
    FIXTURE_PATH,
    FIXTURE_REF,
    derive_vector,
    dump_fixture,
    load_callisto_embeddings,
)
from studio_kb.schema import EMBEDDING_DIM


def test_fixture_covers_exactly_the_corpus() -> None:
    """Tập khoá của fixture PHẢI bằng đúng tập `chunk_id` của corpus — không thiếu, không thừa.

    Thiếu: một chunk mới thêm vào `docs/callisto/` mà quên re-record thì `StubEmbedding` tra không
    ra vector, và chỗ vỡ sẽ hiện ở tận nơi tiêu thụ chứ không ở đây.

    Thừa: một chunk bị xoá/đổi tên mà fixture còn giữ khoá cũ — vector mồ côi, không ai phát hiện vì
    không ai tra tới nó.

    So bằng `==` trên tập chứ không phải `<=` hay so độ dài: cả hai chiều đều là lỗi.
    """
    assert set(load_callisto_embeddings()) == {chunk.chunk_id for chunk in load_callisto()}


def test_every_vector_has_the_pinned_width() -> None:
    """Mọi vector đúng `schema.EMBEDDING_DIM` chiều.

    `kb.chunks.embedding` khai `vector(EMBEDDING_DIM)` và có index HNSW cosine trên đó. Vector lệch
    chiều sẽ bị Postgres từ chối lúc `KbPipeline.index` — đỏ đúng chỗ nhưng muộn, sau khi đã dựng
    Docker và chạy ingest. Bắt ở đây rẻ hơn nhiều bậc.
    """
    widths = {len(vector) for vector in load_callisto_embeddings().values()}
    assert widths == {EMBEDDING_DIM}


def test_van_ban_rong_van_ra_vector_hop_le_dung_chieu() -> None:
    """Ca biên vector 0 — docstring `derive_vector` chốt, nhưng trước D9 không bài nào khoá.

    Text rỗng (hoặc chỉ khoảng trắng) làm mọi ô đếm bằng 0, nên chuẩn hoá L2 sẽ chia cho 0. Hàm
    trả `[1, 0, …]` thay vì gốc toạ độ, và lý do nằm ở tầng dưới: pgvector tính cosine với vector 0
    ra `NaN`, lúc đó **thứ hạng thành vô nghĩa mà không có lỗi nào nổi lên** — đúng kiểu hỏng im
    lặng khó lần nhất.

    Quét đột biến bắt được: đổi `dim - 1` thành `dim - 2` ở nhánh này thì cả suite vẫn xanh, trong
    khi vector trả ra chỉ còn 7 chiều và `KbIngest` sẽ vỡ lúc ingest.

    Khẳng định TÍNH CHẤT, không dán vector quan sát được: đúng số chiều, và chuẩn bằng 1. Ô nào
    mang giá trị 1 là chi tiết hiện thực, khoá nó là khoá thứ bài test không định khoá.
    """
    for text in ("", "   ", "\n\t "):
        vector = derive_vector(text)
        assert len(vector) == EMBEDDING_DIM, f"text {text!r} ra vector lệch chiều"
        assert math.isclose(math.sqrt(sum(x * x for x in vector)), 1.0), f"text {text!r} phải ra vector đơn vị"


def test_declared_dim_matches_the_pinned_constant() -> None:
    """`dim` ghi trong file khớp `EMBEDDING_DIM`, và `fixture_ref` đúng tên bộ.

    Khác test trên: test kia so **dữ liệu** (độ dài mảng thật), test này so **phần khai báo**. File
    có thể chứa 25 vector 8 chiều nhưng đầu file ghi `"dim": 16` — lúc đó người đọc file tin nhầm,
    và ai đọc `dim` để cấp phát/kiểm tra sẽ sai. Một file tự mâu thuẫn phải đỏ.
    """
    raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert raw["dim"] == EMBEDDING_DIM
    assert raw["fixture_ref"] == FIXTURE_REF


def test_file_on_disk_still_matches_what_the_generator_produces() -> None:
    """File check-in PHẢI trùng từng byte với thứ bộ sinh tạo ra bây giờ.

    Đây là assert đắt nhất và là cái duy nhất chứng minh chữ "**recorded**" trong `day-07.md:37`.
    Ba assert trên đều đọc file rồi tự so với chính nó ở khía cạnh khác; chỉ assert này so **bản đã
    ghi** với **bản sinh lại**, nên nó bắt được hai thứ kia không thấy:

    - ai đó sửa tay một con số trong JSON (fixture không còn là output của bộ sinh);
    - công thức `derive_vector` đổi mà quên chạy lại `scripts/record_embeddings.py`.

    Cách chữa khi đỏ: chạy `uv run python packages/kb/scripts/record_embeddings.py` rồi commit file mới — có chủ đích
    thì đó là re-record hợp lệ (vd gateway thật về), vô tình thì `git diff` chỉ ra ngay đã đổi gì.
    """
    assert FIXTURE_PATH.read_text(encoding="utf-8") == dump_fixture()
