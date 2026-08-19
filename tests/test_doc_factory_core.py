"""Guard cho việc tách primitive (Phase A cutover 2.0): `doc_factory_core` là SSOT, `doc_factory`
chỉ re-export, và 2.0 (`doc_factory_v2`) KHÔNG còn phụ thuộc 1.0 (`doc_factory`).

Vì sao cần bộ này: test 1.0/2.0 hiện có xanh **dù** `doc_factory_v2` import primitive từ `doc_factory`
hay từ `doc_factory_core` — chúng không phân biệt được. Nếu không canh, ai đó vô tình trỏ v2 lại vào
`doc_factory` thì "xoá 1.0" (Phase I) sẽ kéo sập 2.0 mà **không test nào đỏ**. Bộ này lật đúng seam đó
thành một khẳng định đỏ-được.
"""

from __future__ import annotations

import ast
from pathlib import Path
from uuid import uuid4

from studio_kb import doc_factory, doc_factory_core, doc_factory_v2


def test_docfactory_reexports_are_the_same_object_as_core() -> None:
    """`doc_factory` phải re-export ĐÚNG object của core (SSOT, không nhân bản).

    Dùng `is`, không `==`: `Chunk` là dataclass, hai định nghĩa riêng vẫn có thể `==` theo cấu trúc
    nhưng khác identity → `isinstance`/so khớp kiểu giữa 1.0 và 2.0 sẽ lệch câm. Một nguồn duy nhất.
    """
    assert doc_factory.Chunk is doc_factory_core.Chunk
    assert doc_factory.SECTION_VOCAB is doc_factory_core.SECTION_VOCAB
    assert doc_factory.TENANT_IDS is doc_factory_core.TENANT_IDS
    assert doc_factory.resolve_tenant_id is doc_factory_core.resolve_tenant_id


def _module_level_imports(module_path: Path) -> set[str]:
    """Trả tập tên module được import ở cấp module (bỏ import cục bộ trong hàm — không phải phụ thuộc
    tải-khi-nạp). Đọc AST thay vì runtime để bắt cả import 'chưa dùng'."""
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in tree.body:  # CHỈ cấp module, không đệ quy vào thân hàm
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            names.add(node.module)
        elif isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
    return names


def test_v2_does_not_import_the_deletable_1_0_module() -> None:
    """`doc_factory_v2` phải lấy primitive từ `doc_factory_core`, KHÔNG từ `doc_factory` (1.0).

    Đây là điều kiện để Phase I xoá `doc_factory` mà 2.0 vẫn đứng. Seam vừa lật ở cutover.
    """
    v2_src = Path(doc_factory_v2.__file__)
    imports = _module_level_imports(v2_src)
    assert "studio_kb.doc_factory_core" in imports, "v2 phải import primitive từ doc_factory_core"
    assert "studio_kb.doc_factory" not in imports, (
        "doc_factory_v2 vẫn phụ thuộc module 1.0 `doc_factory` — Phase I xoá 1.0 sẽ kéo sập 2.0"
    )


def test_core_does_not_import_either_docfactory_variant() -> None:
    """core là tầng đáy — không được import ngược lên 1.0/2.0 (kẻo tạo vòng khi 1.0 bị xoá)."""
    imports = _module_level_imports(Path(doc_factory_core.__file__))
    assert "studio_kb.doc_factory" not in imports
    assert "studio_kb.doc_factory_v2" not in imports


# ── embed-view: `embedding_input` là chuỗi DUY NHẤT được đem embed ────────────
def test_embedding_input_mac_dinh_bang_text() -> None:
    """`Chunk` không khai `embed_text` (corpus 1.0, hoặc chunk dựng lại từ DB cũ) → embed đúng `text`.

    Đây là điều kiện để thêm embed-view KHÔNG làm 1.0 đổi vector: `doc_factory` (1.0) dựng `Chunk`
    bằng keyword, không truyền `embed_text`, nên phải rơi về `text` y như trước."""
    c = doc_factory_core.Chunk(chunk_id="d#c1", text="## A\nnội dung", tenant_id=uuid4(), section_role="hr")
    assert c.embed_text == ""
    assert c.embedding_input == "## A\nnội dung"


def test_embedding_input_uu_tien_embed_text_khi_co() -> None:
    c = doc_factory_core.Chunk(
        chunk_id="d#c1",
        text="## A\nnội dung",
        tenant_id=uuid4(),
        section_role="hr",
        embed_text="Tiêu đề\n## A\nnội dung",
    )
    assert c.embedding_input == "Tiêu đề\n## A\nnội dung"
    assert c.text == "## A\nnội dung", "thêm embed_text KHÔNG được đụng vào text"
