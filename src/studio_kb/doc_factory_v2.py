"""Callisto 2.0 cutter (thử nghiệm, SONG SONG với 1.0 — KHÔNG thay thế `doc_factory`).

Đọc `docs/callisto-2.0-schema.md`: tenant từ thư mục, role từ tên file, không front-matter, không
override, citation = tên file. Hợp đồng là `tests/test_doc_factory_v2.py` (bất biến I1..I9).
Tái dùng `Chunk`/`SECTION_VOCAB`/`resolve_tenant_id` của `doc_factory` — không nhân bản.
"""

from __future__ import annotations

import re
from pathlib import Path
from uuid import UUID

from studio_kb.doc_factory import SECTION_VOCAB, Chunk, resolve_tenant_id

# Cùng hình dạng heading 1.0, nhưng ở 2.0 nhóm `override` chỉ dùng để PHÁT HIỆN-và-RAISE (cấm), không áp dụng.
_HEADING_RE = re.compile(r"^##\s+(?P<title>.*?)(?:\s*\{section:\s*(?P<override>[\w-]+)\s*\})?\s*$")


def _cut_document(text: str, doc_id: str, tenant_id: UUID, role: str) -> list[Chunk]:
    """Cắt 1 tài liệu (markdown thuần, KHÔNG front-matter) thành chunk. Xem schema 2.0 §3.

    Mọi chunk mang cùng `role` (I6). Heading `{section:…}` → raise (I5, cấm override). Thân rỗng →
    raise (I7, giữ 'đủ số chunk'). Text chunk gồm cả dòng heading (như 1.0)."""
    chunks: list[Chunk] = []
    title: str | None = None
    body: list[str] = []

    def flush() -> None:
        if title is None:
            return
        joined = "\n".join(body).strip()
        if not joined:
            raise ValueError(f"{doc_id}: heading {title!r} có thân rỗng — 2.0 cấm section rỗng (I7)")
        chunks.append(
            Chunk(
                chunk_id=f"{doc_id}#c{len(chunks) + 1}",
                text=f"## {title}\n{joined}",
                tenant_id=tenant_id,
                section_role=role,
            )
        )

    for line in text.splitlines():
        heading = _HEADING_RE.match(line)
        if heading is None:
            if title is not None:  # bỏ nội dung trước heading '##' đầu tiên
                body.append(line)
            continue
        if heading.group("override") is not None:
            raise ValueError(f"{doc_id}: heading mang '{{section:…}}' — 2.0 cấm override (I5)")
        flush()
        title = heading.group("title")
        body = []

    flush()
    if not chunks:
        raise ValueError(f"{doc_id}: không cắt được chunk nào (thiếu heading '## '?)")
    return chunks


def load_corpus_v2(root: Path) -> list[Chunk]:
    """Nạp corpus 2.0 `root/{tenant}/{role}-{name}.md` → `list[Chunk]`. Xem `docs/callisto-2.0-schema.md`.

    tenant = tên thư mục con (→ `resolve_tenant_id`, raise nếu lạ — I1); role = token đầu tên file
    (∈ `SECTION_VOCAB`, raise nếu lạ — I2); tên file phải đúng dạng `role-name` (I3);
    `doc_id = "{tenant}-{stem}"`, `chunk_id = "{doc_id}#c{n}"` (I4, citation = tên file). Sắp xếp
    thư mục + file để `chunk_id` ổn định giữa các lần chạy.
    """
    chunks: list[Chunk] = []
    for tenant_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        tenant = tenant_dir.name
        tenant_id = resolve_tenant_id(tenant)  # raise nếu tenant lạ (I1)
        for path in sorted(tenant_dir.glob("*.md")):
            stem = path.stem
            role, sep, name = stem.partition("-")
            if not sep or not name:  # thiếu '{role}-' hoặc thiếu name (I3)
                raise ValueError(f"tên file {path.name!r} không đúng dạng 'role-name.md' (I3)")
            if role not in SECTION_VOCAB:  # (I2)
                raise ValueError(f"{path.name}: role {role!r} ngoài từ vựng {sorted(SECTION_VOCAB)} (I2)")
            doc_id = f"{tenant}-{stem}"  # (I4) — tenant từ thư mục để 2 tenant cùng tên file không đụng id (I9)
            chunks.extend(_cut_document(path.read_text(encoding="utf-8"), doc_id, tenant_id, role))
    if not chunks:
        raise FileNotFoundError(f"không thấy tài liệu .md nào dưới {root}")
    return chunks
