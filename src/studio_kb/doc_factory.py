"""doc-factory — cắt tài liệu Callisto (`docs/callisto/*.md`) thành chunk có `chunk_id`.

Đây là **máy cắt tĩnh đọc file**, KHÔNG phải `KbPipeline.chunker` (`pipeline.py`). Hai thứ khác
tầng và cố ý tách rời: `KbPipeline` ăn document đã vào Postgres và là spec-DE cho S2 (chunk/embed/
index thật, giữ nguyên `NotImplementedError`); module này ăn `.md` trên đĩa để dựng KB **tĩnh** cho
Sprint 1 (`day-04.md:22` — "KB tĩnh, chunk tĩnh"). Nhập chúng lại là tự đặt bom cho S2.

"1 script, 2 deliverable" (`umbrella-contract.md:81`): cùng máy cắt này nuôi **cả** dữ liệu KB
(`StaticKbSearch` tìm trên nó) **lẫn** golden-set (`golden/smoke-5.yaml` trích `chunk_id` từ đây).
Tách hai máy thì hai bên lệch `chunk_id`, mà lệch thì mọi case ra 0 điểm **không có lỗi nào nổi
lên** (`docs/format.md` §2).

Ba luật cắt, chốt ở `docs/callisto-doc-schema.md`, không chọn lại ở đây:

1. **Cắt theo heading `##`** (§5) — 1 chunk = 1 heading + thân bên dưới.
2. **`chunk_id = "{doc_id}#c{n}"`, n đếm từ 1 theo từng doc** (§6) — không UUID. Lý do: `re_index`
   (S3) bắt giữ nguyên `chunk_id`, mà UUID ngẫu nhiên thì mỗi lần index lại là golden-set chết.
3. **1 chunk = đúng 1 `section_role`** (§5) — mặc định lấy `section` ở front-matter, nhưng heading
   mang `{section: X}` thì **override riêng chunk đó**. `ankor-expense-001#c2` là chunk duy nhất
   trong bộ dùng đường này (`public` → `finance`); nó cũng là thứ duy nhất kiểm được luật.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

SECTION_VOCAB = frozenset({"public", "hr", "finance", "engineering"})
"""Từ vựng đóng (`callisto-doc-schema.md` §3). Đóng thật: gặp giá trị lạ thì raise, không im lặng
bỏ qua — một `section_role` gõ sai mà lọt sẽ tạo ra chunk không ai với tới được, và fence sẽ trông
như đang chạy đúng."""

DEFAULT_DOC_DIR = Path(__file__).resolve().parents[2] / "docs" / "callisto"
"""`packages/kb/docs/callisto/`. Suy từ vị trí file để test chạy được không cần cwd cố định."""

_FRONT_MATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
_HEADING_RE = re.compile(r"^##\s+(?P<title>.*?)(?:\s*\{section:\s*(?P<override>[\w-]+)\s*\})?\s*$")


@dataclass(frozen=True, slots=True)
class Chunk:
    """Một đoạn đã cắt — đơn vị `kb.search` trả về và `expected_citation` trỏ tới.

    Không dùng `KbSearchResultItem` ở đây: item đó mang `score`, mà `score` là thứ sinh ra **lúc
    tìm**, không phải thuộc tính của đoạn văn. Trộn hai thứ vào một kiểu thì mỗi lần cắt lại phải
    bịa ra một điểm số vô nghĩa.
    """

    chunk_id: str
    text: str
    tenant: str
    section_role: str


def parse_front_matter(raw: str) -> tuple[dict[str, str], str]:
    """Tách front-matter YAML khỏi thân. Trả `(fields, body)`.

    Parse tay 3 dòng `key: value` thay vì kéo `pyyaml` vào: `pyproject.toml` của kb chỉ khai
    `contracts` + `psycopg`, và §2 của schema đã chốt front-matter **đúng 3 field** — thêm một
    dependency cho ngần đó là đắt.
    """
    m = _FRONT_MATTER_RE.match(raw)
    if m is None:
        raise ValueError("thiếu front-matter (khối --- ở đầu file)")

    fields: dict[str, str] = {}
    for line in m.group(1).splitlines():
        key, sep, value = line.partition(":")
        if not sep:
            raise ValueError(f"dòng front-matter không đúng dạng 'key: value': {line!r}")
        fields[key.strip()] = value.strip()

    return fields, raw[m.end() :]


def chunk_document(raw: str) -> list[Chunk]:
    """Cắt một tài liệu thành chunk. Text của chunk **gồm cả dòng heading**.

    Giữ heading trong text có chủ đích: nó là câu tóm tắt sẵn có của đoạn, và ở bản tìm kiếm thô
    (`static_search.py`) nó đóng góp thẳng vào điểm trùng token — "Thời hạn báo trước" là thứ khớp
    câu hỏi "cần báo trước bao lâu?" mạnh nhất trong cả đoạn.
    """
    fields, body = parse_front_matter(raw)

    missing = {"doc_id", "tenant", "section"} - fields.keys()
    if missing:
        raise ValueError(f"front-matter thiếu field: {sorted(missing)}")

    doc_id, tenant, doc_section = fields["doc_id"], fields["tenant"], fields["section"]
    if doc_section not in SECTION_VOCAB:
        raise ValueError(f"{doc_id}: section {doc_section!r} ngoài từ vựng {sorted(SECTION_VOCAB)}")

    chunks: list[Chunk] = []
    lines: list[str] = []
    section_role = doc_section

    def flush() -> None:
        if not lines:
            return
        text = "\n".join(lines).strip()
        if text:
            chunks.append(
                Chunk(
                    chunk_id=f"{doc_id}#c{len(chunks) + 1}",
                    text=text,
                    tenant=tenant,
                    section_role=section_role,
                )
            )

    for line in body.splitlines():
        heading = _HEADING_RE.match(line)
        if heading is None:
            if chunks or lines:  # bỏ phần trước heading `##` đầu tiên (tiêu đề `#`, dòng trống)
                lines.append(line)
            continue

        flush()
        override = heading.group("override")
        if override is not None and override not in SECTION_VOCAB:
            raise ValueError(f"{doc_id}: override section {override!r} ngoài từ vựng {sorted(SECTION_VOCAB)}")
        section_role = override or doc_section
        lines = [heading.group("title")]

    flush()
    if not chunks:
        raise ValueError(f"{doc_id}: không cắt được chunk nào (thiếu heading '## '?)")
    return chunks


def load_callisto(doc_dir: Path | None = None) -> list[Chunk]:
    """Cắt toàn bộ `docs/callisto/*.md`. Sắp theo tên file để `chunk_id` ổn định giữa các lần chạy."""
    directory = DEFAULT_DOC_DIR if doc_dir is None else doc_dir
    paths = sorted(directory.glob("*.md"))
    if not paths:
        raise FileNotFoundError(f"không thấy tài liệu .md nào trong {directory}")
    return [chunk for path in paths for chunk in chunk_document(path.read_text(encoding="utf-8"))]
