"""Callisto 2.0 cutter (thử nghiệm, SONG SONG với 1.0 — KHÔNG thay thế `doc_factory`).

Đọc `docs/callisto-2.0-schema.md`: tenant từ thư mục, role từ tên file, không front-matter, không
override, citation = tên file. Hợp đồng là `tests/test_doc_factory_v2.py` (bất biến I1..I9).
Tái dùng `Chunk`/`SECTION_VOCAB`/`resolve_tenant_id` từ `doc_factory_core` (KHÔNG phụ thuộc 1.0
`doc_factory`, để 1.0 xoá được mà 2.0 vẫn đứng) — không nhân bản.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import replace
from pathlib import Path
from uuid import UUID

from studio_kb.doc_factory_core import SECTION_VOCAB, Chunk, resolve_tenant_id

# Cùng hình dạng heading 1.0, nhưng ở 2.0 nhóm `override` chỉ dùng để PHÁT HIỆN-và-RAISE (cấm), không áp dụng.
_HEADING_RE = re.compile(r"^##\s+(?P<title>.*?)(?:\s*\{section:\s*(?P<override>[\w-]+)\s*\})?\s*$")


def _cut_document(text: str, doc_id: str, tenant_id: UUID, role: str) -> list[Chunk]:
    """Cắt 1 tài liệu (markdown thuần, KHÔNG front-matter) thành chunk. Xem schema 2.0 §3.

    Mọi chunk mang cùng `role` (I6). Heading `{section:…}` → raise (I5, cấm override). Thân rỗng →
    raise (I7, giữ 'đủ số chunk'). Text chunk gồm cả dòng heading (như 1.0).

    **Tiêu đề tài liệu (`# ...`) vào `embed_text`, KHÔNG vào `text`.** Trước đây dòng này bị vứt hẳn,
    nên chủ đề cấp-tài-liệu chỉ tồn tại trong chunk nào tình cờ có heading trùng nó — gần như luôn là
    `#c1` (mục tổng quan). Hệ quả đo được: model trả `#c1` ở 45% ca trượt trong khi `#c1` chỉ là đáp
    án thật 11% — `#c1` "nuốt" mọi truy vấn về tài liệu. Nhồi tiêu đề vào MỌI chunk khi embed thì lợi
    thế đó biến mất. `text` giữ nguyên byte vì nhãn golden 2.0 chấm grounded trên nó."""
    chunks: list[Chunk] = []
    doc_title = ""
    title: str | None = None
    body: list[str] = []

    def flush() -> None:
        if title is None:
            return
        joined = "\n".join(body).strip()
        if not joined:
            raise ValueError(f"{doc_id}: heading {title!r} có thân rỗng — 2.0 cấm section rỗng (I7)")
        chunk_text = f"## {title}\n{joined}"
        chunks.append(
            Chunk(
                chunk_id=f"{doc_id}#c{len(chunks) + 1}",
                text=chunk_text,
                tenant_id=tenant_id,
                section_role=role,
                # Giữ tiền tố `# ` — KHÔNG phải để đẹp markdown: `_norm` trả `""` cho dòng bắt đầu
                # bằng `#`, nên tiêu đề được MIỄN TRỪ khỏi bộ đếm boilerplate. Không có nó, tiêu đề
                # (lặp ở cả 10 chunk của doc ≥ ngưỡng 3) sẽ bị chính `_strip_boilerplate` xoá mất —
                # đúng bug đã gặp: chỉ 138/800 chunk giữ được tiêu đề.
                embed_text=f"# {doc_title}\n{chunk_text}" if doc_title else chunk_text,
            )
        )

    for line in text.splitlines():
        heading = _HEADING_RE.match(line)
        if heading is None:
            if title is not None:  # bỏ nội dung trước heading '##' đầu tiên
                body.append(line)
            elif not doc_title and line.startswith("# "):
                doc_title = line[2:].strip()  # tiêu đề tài liệu — chỉ dùng cho embed_text
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
    return _strip_boilerplate(chunks)


BOILERPLATE_MIN_CHUNKS = 3
"""Số chunk (TRONG CÙNG scope) mà một câu phải xuất hiện thì mới bị coi là boilerplate.

Ngưỡng 3, không phải 2: hai mục cùng nhắc một câu vẫn có thể là nội dung thật trùng lặp, cắt đi là
mất thông tin. Ngưỡng 1 thì cắt sạch mọi câu. Đo trên corpus 2.0: ngưỡng 3 bắt 37 câu / 1915."""


def _strip_boilerplate(chunks: list[Chunk]) -> list[Chunk]:
    """Cắt câu boilerplate khỏi `embed_text` (giữ nguyên `text`) — pass thứ hai, sau khi đã cắt hết.

    **Đếm theo scope `(tenant_id, section_role)`, không theo toàn corpus.** Fence lọc `{tenant_id,
    section_roles}` TRƯỚC khi xếp hạng, nên chunk ngoài scope không bao giờ cạnh tranh; một câu lặp
    khắp corpus nhưng chỉ xuất hiện một lần trong scope của nó vẫn là tín hiệu phân biệt tốt ở đó,
    cắt đi là cắt oan.

    Vì sao phải ở đây chứ không trong `_cut_document`: đếm cần nhìn TOÀN BỘ chunk của scope, mà
    `_cut_document` chỉ thấy một tài liệu. `Chunk` là `frozen` nên dựng lại bằng `replace`.

    Boilerplate hại hai lần: (1) góp từ vựng chung vào vector làm chunk trông giống nhau; (2) tệ hơn,
    cấp **bằng chứng giả** — vd câu "thông báo trước ít nhất 30 ngày" nằm ở `ankor-hr-leave#c1` mang
    đúng cụm "30 ngày" là đáp án của `#c3` ("Nghỉ ốm tối đa 30 ngày/năm").
    """
    per_scope: dict[tuple[UUID, str], Counter[str]] = defaultdict(Counter)
    for c in chunks:
        per_scope[(c.tenant_id, c.section_role)].update(_sentences(c.embed_text))

    out: list[Chunk] = []
    for c in chunks:
        dem = per_scope[(c.tenant_id, c.section_role)]
        kept = [ln for ln in c.embed_text.splitlines() if dem[_norm(ln)] < BOILERPLATE_MIN_CHUNKS or not _norm(ln)]
        out.append(replace(c, embed_text="\n".join(kept)))
    return out


def _norm(line: str) -> str:
    """Khoá đếm của một dòng — bỏ bullet `- ` đầu dòng và khoảng trắng; dòng heading/rỗng → `""`
    (không bao giờ bị đếm là boilerplate, kẻo cắt mất chính heading của mục)."""
    s = line.strip().removeprefix("- ").strip()
    return "" if not s or s.startswith("#") else s


def _sentences(text: str) -> set[str]:
    """Tập dòng-nội-dung phân biệt của một chunk. `set` chứ không `list`: một câu lặp 3 lần TRONG
    CÙNG một chunk chỉ tính là 1 — ngưỡng đếm số CHUNK chứa nó, không phải tổng số lần xuất hiện."""
    return {n for ln in text.splitlines() if (n := _norm(ln))}
