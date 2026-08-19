"""Primitive trung tính dùng chung giữa doc-factory 1.0 (`doc_factory`) và 2.0 (`doc_factory_v2`).

Tách ra để 1.0 **xoá được** mà không kéo theo 2.0: `Chunk`, `SECTION_VOCAB`, danh tính tenant
(`TENANT_IDS`/`resolve_tenant_id`) là hình dạng dữ liệu + từ vựng chung, không thuộc luật cắt của
riêng phiên bản nào. Luật cắt (front-matter vs thư mục/tên file) ở lại đúng module phiên bản.

`doc_factory` **re-export** các tên này nên mọi `from studio_kb.doc_factory import Chunk/…` khắp
workspace giữ nguyên — đây là SSOT thật, `doc_factory` chỉ là mặt tương thích.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

SECTION_VOCAB = frozenset({"public", "hr", "finance", "engineering"})
"""Từ vựng đóng (`callisto-doc-schema.md` §3). Đóng thật: gặp giá trị lạ thì raise, không im lặng
bỏ qua — một `section_role` gõ sai mà lọt sẽ tạo ra chunk không ai với tới được, và fence sẽ trông
như đang chạy đúng."""

TENANT_IDS: dict[str, UUID] = {
    "ankor": UUID("a0000000-0000-0000-0000-000000000001"),
    "borea": UUID("b0000000-0000-0000-0000-000000000001"),
}
"""⚠️ **FIXTURE Sprint 1 — KHÔNG phải cách phân giải thật.** D-13 chốt danh tính tenant là
`core.tenants.id` **UUID bất biến**; slug (`ankor`/`borea`) chỉ còn là **nhãn hiển thị**. Front-matter
tài liệu vẫn viết slug, nên đâu đó phải ánh xạ slug → UUID. Bảng thật là `core.tenants`, và middleware
đã phân giải cho request-path (`apps/studio/middleware.py`) — nhưng `studio_kb` **không được import
`core.*`** (`.importlinter`), và ingest-path chưa có ai phân giải (đó là **Q-G**, chưa chốt).

Nên S1 dùng bảng cứng này: giá trị **khớp nguyên văn** hằng số của SWE
(`studio_workbench/builder_d4.py` `ANKOR_ID`) để cả workspace nói cùng một UUID cho `ankor`; `borea`
theo cùng quy luật (chữ đầu = tên tenant) vì trước D5 chưa ai cần tới. Khi Q-G chốt đường phân giải
thật (composition-root truyền `tenant_id` UUID xuống ingest), **xoá bảng này**, không để nó hoá thành
thiết kế."""


def resolve_tenant_id(slug: str) -> UUID:
    """Ánh xạ slug tài liệu → `tenant_id` UUID (S1 fixture, xem `TENANT_IDS`).

    Đóng như `SECTION_VOCAB`: slug lạ thì **raise**, không im lặng. Một tenant gõ sai mà lọt sẽ tạo
    chunk mang UUID rác, không ai với tới, và fence trông như đang chạy đúng.
    """
    try:
        return TENANT_IDS[slug]
    except KeyError:
        raise ValueError(f"tenant slug {slug!r} ngoài bảng phân giải S1 {sorted(TENANT_IDS)}") from None


@dataclass(frozen=True, slots=True)
class Chunk:
    """Một đoạn đã cắt — đơn vị `kb.search` trả về và `expected_citation` trỏ tới.

    Không dùng `KbSearchResultItem` ở đây: item đó mang `score`, mà `score` là thứ sinh ra **lúc
    tìm**, không phải thuộc tính của đoạn văn. Trộn hai thứ vào một kiểu thì mỗi lần cắt lại phải
    bịa ra một điểm số vô nghĩa.

    `tenant_id` là **UUID** (D-13), phân giải từ slug front-matter qua `resolve_tenant_id`. Slug gốc
    KHÔNG mất — nó vẫn nằm trong `chunk_id` (`"ankor-leave-001#c1"`) làm nhãn hiển thị, đúng chủ ý
    D-13 (chunk_id là con trỏ bền qua re-index, giữ nguyên).

    `text` là thứ **hiển thị/chấm nhãn**: golden-set 2.0 kiểm grounded bằng `_contains_phrase(
    chunk.text, expected)` và `StaticKbSearch` xếp hạng trên nó. `embed_text` là thứ **đem embed** —
    tách đôi để cải thiện retrieval (nhồi tiêu đề tài liệu, cắt boilerplate) mà KHÔNG đụng vào
    `text`, vì đổi `text` là phải re-trace toàn bộ nhãn golden. Rỗng ⇒ rơi về `text` (corpus 1.0 và
    chunk dựng lại từ dòng DB cũ đều không khai nó, phải giữ hành vi cũ nguyên vẹn).
    """

    chunk_id: str
    text: str
    tenant_id: UUID
    section_role: str
    embed_text: str = ""

    @property
    def embedding_input(self) -> str:
        """Chuỗi DUY NHẤT được phép đưa vào `EmbeddingService`. Mọi đường ghi vector đọc qua đây —
        không chỗ nào tự chọn giữa `text`/`embed_text`, kẻo hai đường ghi ra hai vector khác nhau
        cho cùng một chunk (xem `KbPipeline.re_index`)."""
        return self.embed_text or self.text
