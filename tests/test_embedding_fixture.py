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

import inspect
import json
import math

from studio_kb.doc_factory import load_callisto
from studio_kb.embeddings import (
    FIXTURE_DIM,
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
    """Mọi vector đúng `embeddings.FIXTURE_DIM` chiều.

    **Đổi mốc so từ `EMBEDDING_DIM` sang `FIXTURE_DIM` ở D22 — có chủ đích, không phải sửa test cho
    xanh.** Đến D22 hai hằng số là một, nên bài này so với `EMBEDDING_DIM` cũng đúng. Khi cột lên
    `vector(2048)` cho embedding thật, gộp tiếp có nghĩa là re-record 140 chunk corpus 1.0 thành
    ~5.7 MB bag-of-words 2048 ô — nói lại đúng điều bản 8 chiều đang nói. Fixture là **bản ghi của
    thế giới dim-8/1.0**; nó không bám chiều production (DL-22.5).

    Điều bài này canh không đổi: file không được chứa vector lệch chiều so với chiều nó tự khai.
    Ràng buộc "vector nạp vào `kb.chunks` phải khớp cột" nay do
    `test_derive_vector_mac_dinh_van_bam_cot` canh — xem lý do ở đó.
    """
    widths = {len(vector) for vector in load_callisto_embeddings().values()}
    assert widths == {FIXTURE_DIM}


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
    """`dim` ghi trong file khớp `FIXTURE_DIM`, và `fixture_ref` đúng tên bộ.

    Khác test trên: test kia so **dữ liệu** (độ dài mảng thật), test này so **phần khai báo**. File
    có thể chứa 25 vector 8 chiều nhưng đầu file ghi `"dim": 16` — lúc đó người đọc file tin nhầm,
    và ai đọc `dim` để cấp phát/kiểm tra sẽ sai. Một file tự mâu thuẫn phải đỏ.
    """
    raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert raw["dim"] == FIXTURE_DIM
    assert raw["fixture_ref"] == FIXTURE_REF


def test_derive_vector_mac_dinh_van_bam_cot() -> None:
    """Mặc định của `derive_vector` PHẢI bằng `EMBEDDING_DIM` — răng thay cho phép so mà
    `test_every_vector_has_the_pinned_width` vừa nhả ra ở D22.

    Đây là phần **không** được tách khỏi cột. Năm chỗ nạp vector sống vào `kb.chunks` đều gọi
    `derive_vector(text)` **không truyền `dim`**:

      - `apps/studio/src/studio_app/providers/factory.py::CallistoEmbedding` (production)
      - `apps/studio/tests/test_gate2_verdict_from_live_spine.py::_CallistoEmbedding`
      - `apps/studio/tests/test_kb_search_live_readiness.py::_CallistoEmbedding`
      - `apps/studio/tests/test_spine_scored_from_postgres.py::_CallistoEmbedding`
      - `apps/studio/scripts/e2e_smoke_eval.py::_CallistoEmbedding`

    Ghim mặc định thành một hằng số rời (ví dụ `= FIXTURE_DIM`) sẽ làm cả năm chỗ ghi vector 8
    chiều vào cột `vector(2048)`. Bốn trong năm nằm ở lane khác, và `.importlinter` chặn kb import
    ngược lên `studio_app` nên không test nào của kb với tới chúng — bài này là chỗ gần nhất canh
    được, ngay tại nguồn.

    Quét đột biến: đổi chữ ký thành `dim: int = FIXTURE_DIM` thì mọi bài khác trong file vẫn xanh
    (fixture đã tự ghim `dim=FIXTURE_DIM`), chỉ bài này đỏ.
    """
    assert inspect.signature(derive_vector).parameters["dim"].default == EMBEDDING_DIM
    assert len(derive_vector("khớp cột, không phải khớp fixture")) == EMBEDDING_DIM


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
