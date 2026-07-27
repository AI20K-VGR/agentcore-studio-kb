"""`StaticKbSearch` — bản `kb.search` **thô** cho Sprint 1 (D4). Thoả `studio_contracts.KbSearch`.

⚠️ **Đây KHÔNG phải `KbSearchService`** (`search.py`), và cố ý không phải. Ba lý do độc lập:

1. **Khác contract.** Docstring `search.py` ràng buộc bản thật: lọc **fail-closed** tại truy xuất,
   `section_roles` phân giải **server-side**, chạy qua `get_pool()` để RLS có hiệu lực. Brief D4 nói
   ngược lại — *"CHƯA fence, filter tenant naive để xâu kim"* (`day-04.md:22`), fence để **S3**
   (`day-04.md:46`). Nhét hành vi naive vào seam đã ghi rõ là fenced = nói dối bằng code.
2. **`KbSearchService` phải giữ `NotImplementedError`.** `tests/test_search_contract.py` là test
   **XANH** khẳng định đúng điều đó; nó là spec-DE cho S2–S3, không tiêu ở D4.
3. **Không có gì để tìm ở tầng đó.** `KbSearchService` tìm trên bảng `kb.chunks`, mà bảng rỗng vì
   `KbPipeline.index` chưa chạy được. Điền thân xong nó vẫn trả `[]`.

Chỗ nối cho AIE-1: `KbRetrieveExecutor.__init__(self, kb_search: KbSearch)` nhận qua **Protocol,
tiêm vào** — nên một class tĩnh thoả `KbSearch` là đủ để bỏ `EmptyKbSearch` và cho `llm-step` có
`chunk_id` mà trích dẫn.

**Đường nâng cấp** (v0 → thật), để không ai nhầm cái nào là đích:

| | v0 hôm nay | S2–S3 (`KbSearchService`) |
|---|---|---|
| nguồn | 25 chunk tĩnh từ `doc_factory` | `kb.chunks` + pgvector |
| lọc `tenant_id` | so UUID thẳng (`==`), naive | RLS trên connection non-owner |
| lọc `section_roles` | so tập hợp, **tin giá trị client khai** | phân giải **server-side** (chặn T6) |
| xếp hạng | trùng token thô | cosine trên vector |

Dù brief ghi "chưa fence", v0 **vẫn lọc `section_roles`**. Không phải làm sớm: SC-05 (chéo vai)
không có nghĩa gì nếu không lọc vai — case sẽ xanh vì lý do sai. Thứ hoãn tới S3 là *phân giải
server-side* + *fail-closed*, không phải bản thân mệnh đề lọc.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import TYPE_CHECKING
from uuid import UUID

from studio_contracts.kb import KbSearchResultItem

from studio_kb.doc_factory import Chunk, load_callisto

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def _tokens(text: str) -> set[str]:
    """Tách token thô: hạ chữ thường, giữ chữ-số, bỏ dấu câu. Không tách từ tiếng Việt (`nghỉ phép`
    ra hai token) — đúng tinh thần "thô", và đủ để phân biệt 5 smoke-case."""
    return set(_TOKEN_RE.findall(text.lower()))


class StaticKbSearch:
    """`kb.search` tĩnh trên bộ tài liệu Callisto. Thoả `studio_contracts.KbSearch`."""

    def __init__(self, chunks: Iterable[Chunk] | None = None) -> None:
        """Nạp sẵn toàn bộ chunk vào bộ nhớ. `chunks` tiêm được để test dựng bộ tài liệu riêng mà
        không phải ghi file thật."""
        self._chunks = list(load_callisto() if chunks is None else chunks)

    async def search(
        self,
        query: str,
        tenant_id: UUID,
        section_roles: list[str],
        top_k: int,
    ) -> list[KbSearchResultItem]:
        """Trả các chunk khớp `query`, đã lọc theo `{tenant_id, section_roles}`, xếp giảm dần theo
        `score`, cắt còn `top_k`.

        `tenant_id` là **UUID** (D-13): so bằng `==` với `chunk.tenant_id`, không so slug. Danh tính
        tenant phải là thứ không trùng được — slug thì trùng được, nên nó chỉ còn là nhãn hiển thị.

        **Lọc TRƯỚC khi xếp hạng** — không phải lấy hết rồi cắt. Thứ tự này quan trọng kể cả ở bản
        naive: lọc sau khi cắt `top_k` sẽ để một chunk ngoài phạm vi chiếm chỗ rồi bị loại, làm mất
        một kết quả hợp lệ và đưa số lượng trả về thành thứ phụ thuộc dữ liệu của tenant khác.

        `[]` là kết quả **hợp lệ**, không phải lỗi (`kb-search.v0.md` §6.1) — node `kb-retrieve` phải
        đi tiếp sang `llm-step`, không raise. Đây cũng đã là hình dạng của fail-closed sau này.

        `top_k <= 0` trả `[]`.
        """
        if top_k <= 0:
            return []

        allowed = set(section_roles)
        query_tokens = _tokens(query)
        if not query_tokens:
            return []

        scored: list[tuple[float, Chunk]] = []
        for chunk in self._chunks:
            if chunk.tenant_id != tenant_id or chunk.section_role not in allowed:
                continue
            overlap = len(query_tokens & _tokens(chunk.text))
            if overlap == 0:
                continue
            scored.append((overlap / len(query_tokens), chunk))

        # `chunk_id` làm khoá phụ khi điểm bằng nhau: xếp hạng phải tất định, nếu không golden-set
        # sẽ xanh/đỏ đổi theo thứ tự đọc file.
        scored.sort(key=lambda pair: (-pair[0], pair[1].chunk_id))

        return [
            KbSearchResultItem(
                chunk_id=chunk.chunk_id,
                text=chunk.text,
                score=score,
                tenant_id=chunk.tenant_id,
                section_role=chunk.section_role,
            )
            for score, chunk in scored[:top_k]
        ]


if TYPE_CHECKING:  # pragma: no cover
    from studio_contracts.kb import KbSearch

    # Kiểm conformance lúc TYPE-CHECK, bổ cho phép kiểm lúc chạy ở `tests/test_static_search.py`.
    # Hai phép này bắt hai loại lỗi khác nhau và không thay thế nhau được:
    #   - test gọi thật 4 keyword-arg  → bắt lỗi ngay hôm nay, nhưng gọi bằng TÊN HIỆN TẠI
    #   - dòng dưới                    → bắt DRIFT: `KbSearch` ở contracts đổi tham số/kiểu trả về
    #                                    thì mypy đỏ NGAY TẠI kb, thay vì để AIE-1 vỡ ở repo khác
    #                                    (GITFLOWS §6 "version drift").
    # KHÔNG dùng `isinstance(x, KbSearch)`: `@runtime_checkable` chỉ kiểm TÊN method có tồn tại,
    # không kiểm chữ ký — một stub 3 tham số vẫn trả True.
    _protocol_conformance: KbSearch = StaticKbSearch(chunks=[])
