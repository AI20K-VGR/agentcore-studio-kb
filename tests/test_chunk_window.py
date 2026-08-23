"""`chunk_window.cut_window` — cutter cửa sổ trượt cho nội dung tự do (upload/crawl).

Tham số test dùng `size`/`overlap` NHỎ (không phải mặc định 850/170) để mỗi case đọc được bằng mắt —
hành vi cắt không phụ thuộc độ lớn tham số, chỉ phụ thuộc quan hệ `stride = size - overlap`."""

from __future__ import annotations

from uuid import UUID

import pytest
from studio_kb.chunk_window import WORDS_OVERLAP, WORDS_PER_CHUNK, cut_window

_TENANT = UUID("a0000000-0000-0000-0000-000000000001")


def _words(n: int, prefix: str = "w") -> str:
    """Sinh `n` từ phân biệt được (`w1 w2 … wn`) — dễ assert ranh giới hơn text tự nhiên lặp từ."""
    return " ".join(f"{prefix}{i}" for i in range(1, n + 1))


# ── biên ──────────────────────────────────────────────────────────────────
def test_text_rong_tra_rong() -> None:
    assert cut_window("", "doc1", _TENANT, "hr") == []
    assert cut_window("   \n\t  ", "doc1", _TENANT, "hr") == []


def test_ngan_hon_1_cua_so_ra_dung_1_chunk() -> None:
    chunks = cut_window(_words(5), "doc1", _TENANT, "hr", size=10, overlap=3)
    assert len(chunks) == 1
    assert chunks[0].text == _words(5)
    assert chunks[0].chunk_id == "doc1#c1"


def test_dung_khit_1_cua_so_ra_dung_1_chunk() -> None:
    chunks = cut_window(_words(10), "doc1", _TENANT, "hr", size=10, overlap=3)
    assert len(chunks) == 1


# ── nhiều chunk + overlap ────────────────────────────────────────────────
# size=10 overlap=3 -> stride=7. 26 từ -> start 0,7,14,21 (21+10=31>26, window cuối chỉ còn 5 từ,
# vòng lặp dừng NGAY sau đó vì 21+10=31>=26) = 4 chunk, chunk cuối NGẮN HƠN size (đúng nhánh biên
# "chunk cuối cùng có thể ngắn hơn size" — 26 từ CỐ Ý không chia hết cho stride để lộ nhánh này;
# 24 từ (thử trước) tình cờ chia hết đúng khít, không lộ được bug nếu code tính sai ranh giới cuối.
def test_nhieu_chunk_dung_stride() -> None:
    chunks = cut_window(_words(26), "doc1", _TENANT, "hr", size=10, overlap=3)
    assert [c.chunk_id for c in chunks] == ["doc1#c1", "doc1#c2", "doc1#c3", "doc1#c4"]
    assert chunks[0].text == _words(10)  # w1..w10
    assert chunks[1].text == " ".join(f"w{i}" for i in range(8, 18))  # w8..w17
    assert chunks[2].text == " ".join(f"w{i}" for i in range(15, 25))  # w15..w24
    assert chunks[3].text == " ".join(f"w{i}" for i in range(22, 27))  # w22..w26, chunk cuối NGẮN HƠN size (5 từ)


def test_overlap_khop_dung_giua_2_chunk_lien_ke() -> None:
    chunks = cut_window(_words(26), "doc1", _TENANT, "hr", size=10, overlap=3)
    for a, b in zip(chunks, chunks[1:], strict=False):  # so cặp liền kề — 2 mảng LỆCH 1 phần tử là CỐ Ý
        tail = a.text.split()[-3:]
        head = b.text.split()[:3]
        assert tail == head, f"3 từ cuối {a.chunk_id} phải trùng 3 từ đầu {b.chunk_id}"


def test_chunk_khong_cuoi_dung_dung_size_tu() -> None:
    chunks = cut_window(_words(26), "doc1", _TENANT, "hr", size=10, overlap=3)
    for c in chunks[:-1]:
        assert len(c.text.split()) == 10
    assert len(chunks[-1].text.split()) == 5  # chunk cuối ngắn hơn size, đúng nhánh biên


# ── metadata truyền qua tham số, không suy từ nội dung ──────────────────
def test_tenant_va_section_role_gan_dung_cho_moi_chunk() -> None:
    chunks = cut_window(_words(26), "doc1", _TENANT, "finance", size=10, overlap=3)
    assert all(c.tenant_id == _TENANT for c in chunks)
    assert all(c.section_role == "finance" for c in chunks)


# ── idempotent — bắt buộc cho ON CONFLICT DO UPDATE ──────────────────────
def test_deterministic_cat_lai_ra_dung_cung_ket_qua() -> None:
    text = _words(37)
    first = cut_window(text, "doc1", _TENANT, "hr", size=10, overlap=3)
    second = cut_window(text, "doc1", _TENANT, "hr", size=10, overlap=3)
    assert [c.chunk_id for c in first] == [c.chunk_id for c in second]
    assert [c.text for c in first] == [c.text for c in second]


# ── tham số không hợp lệ ──────────────────────────────────────────────────
@pytest.mark.parametrize(
    "size,overlap",
    [(0, 0), (-1, 0), (10, 10), (10, 11), (10, -1)],
)
def test_tham_so_khong_hop_le_raise(size: int, overlap: int) -> None:
    with pytest.raises(ValueError):
        cut_window(_words(5), "doc1", _TENANT, "hr", size=size, overlap=overlap)


# ── mặc định module (850/170) — chỉ chốt quan hệ, không hardcode số đo ──
def test_mac_dinh_module_dung_850_170() -> None:
    assert WORDS_PER_CHUNK == 850
    assert WORDS_OVERLAP == 170
    chunks = cut_window(_words(2000), "doc1", _TENANT, "hr")
    assert len(chunks[0].text.split()) == WORDS_PER_CHUNK
    for a, b in zip(chunks, chunks[1:], strict=False):  # so cặp liền kề — 2 mảng LỆCH 1 phần tử là CỐ Ý
        assert a.text.split()[-WORDS_OVERLAP:] == b.text.split()[:WORDS_OVERLAP]
