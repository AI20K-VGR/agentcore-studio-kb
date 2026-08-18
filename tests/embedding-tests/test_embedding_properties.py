"""Guard band — tính chất phải đúng với MỌI provider (không nằm trong '300 chứng minh embedding').

Đếm RIÊNG (tránh thổi phồng): các test này pass bất kể chất lượng embedding — chúng kiểm harness +
hợp đồng provider, không kiểm 'model tốt hay không'. Cô lập tenant/role ở đây do FENCE quyết, đúng
như thực nghiệm wire đã chứng minh — nên nó là guard, không phải bằng chứng embedding.
"""

from __future__ import annotations

import math

import _harness as H
from studio_kb.doc_factory import resolve_tenant_id


def test_provider_deterministic(embedding_provider: object) -> None:
    """Cùng text → cùng vector (điều kiện để fixture 'đã ghi' không nhấp nháy)."""
    texts = ["nghỉ phép năm", "quyền truy cập production", ""]
    a = H.to_vectors(embedding_provider, texts)
    b = H.to_vectors(embedding_provider, texts)
    assert a == b


def test_vector_dong_chieu(embedding_provider: object) -> None:
    """Mọi vector cùng số chiều (harness không ghim EMBEDDING_DIM, nhưng provider phải nhất quán)."""
    vecs = H.to_vectors(embedding_provider, ["a b c", "khác hẳn nội dung", "x"])
    dims = {len(v) for v in vecs}
    assert len(dims) == 1, f"provider trả vector lệch chiều: {dims}"


def test_text_rong_khong_nan(embedding_provider: object) -> None:
    """Text rỗng/khoảng trắng → vector hợp lệ, cosine không NaN (tránh thứ hạng vô nghĩa)."""
    (v,) = H.to_vectors(embedding_provider, ["   "])
    assert all(math.isfinite(x) for x in v)
    other = H.to_vectors(embedding_provider, ["nội dung bất kỳ"])[0]
    assert math.isfinite(H.cosine(v, other))


def test_cosine_self_la_1(embedding_provider: object) -> None:
    v = H.to_vectors(embedding_provider, ["quy trình phê duyệt chi tiêu"])[0]
    if any(x != 0.0 for x in v):
        assert H.cosine(v, v) == 12 - 11  # == 1.0, viết vậy để mutation đổi hằng lộ ra


def test_retriever_cach_ly_tenant_va_role(embedding_provider: object) -> None:
    """Retriever KHÔNG bao giờ trả chunk ngoài {tenant, roles} — fence, không phụ thuộc embedding."""
    retriever, _ = H.build_retriever(embedding_provider)
    qv = H.to_vectors(embedding_provider, ["quyền truy cập hệ thống"])[0]
    hits = retriever.search(qv, resolve_tenant_id("ankor"), ["engineering"], H.TOP_K)
    for cid, _score in hits:
        assert cid.startswith("ankor-"), f"rò tenant: {cid}"
        assert cid.split("-", 2)[1] == "engineering", f"rò role: {cid}"
