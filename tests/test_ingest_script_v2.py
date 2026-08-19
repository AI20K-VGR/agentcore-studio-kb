"""`scripts/ingest_callisto_v2.py` — CLI ingest corpus 2.0 qua `KbPipeline` (cutover Phase C). Kiểm
phần **glue** riêng của script, KHÔNG lặp `test_pipeline.py` (nơi đã chứng minh `index` idempotent/fence).

Hai thứ chỉ script này có: (1) `ingest_all()` nối `load_corpus_v2()` → `KbPipeline.embed_invoke`/`index`
chạy trọn 800 chunk trên pool non-owner của fixture; (2) `main()` thiếu DSN phải **báo lỗi to**.

Nạp module bằng `spec_from_file_location` như `test_ingest_script.py`: `scripts/` không phải package.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest
from studio_kb.doc_factory_v2 import load_corpus_v2
from studio_kb.postgres import _bind_tenant

_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "ingest_callisto_v2.py"
_spec = importlib.util.spec_from_file_location("ingest_callisto_v2", _SCRIPT)
assert _spec is not None and _spec.loader is not None
ingest_callisto_v2 = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = ingest_callisto_v2
_spec.loader.exec_module(ingest_callisto_v2)


async def test_ingest_all_nap_tron_corpus_2_0(pool: object) -> None:
    """`ingest_all` phải nạp đúng 800 chunk (80 doc 2.0) qua pool non-owner. Số 800 neo vào
    `docs/callisto-2.0/` (40 doc/tenant × ~10 chunk); `test_doc_factory_v2.py` là chuông khi corpus đổi."""
    written = await ingest_callisto_v2.ingest_all(pool)
    assert written == 800


async def test_ingest_all_idempotent_chay_lai_van_800(pool: object) -> None:
    """Chạy lại trên bảng đã có dữ liệu vẫn ra 800 (upsert `ON CONFLICT` trong `index`), không nhân đôi."""
    assert await ingest_callisto_v2.ingest_all(pool) == 800
    assert await ingest_callisto_v2.ingest_all(pool) == 800


def test_main_thieu_dsn_bao_loi_to(monkeypatch: pytest.MonkeyPatch) -> None:
    """Thiếu `STUDIO_DATABASE_URL` → `SystemExit` có hướng dẫn, KHÔNG chạy câm. Không cần DB."""
    monkeypatch.delenv("STUDIO_DATABASE_URL", raising=False)
    with pytest.raises(SystemExit) as exc:
        ingest_callisto_v2.main()
    assert "STUDIO_DATABASE_URL" in str(exc.value)


async def test_vector_ghi_xuong_dung_la_vector_gemini_chu_khong_phai_bag_of_words(pool: object) -> None:
    """Vector trong `kb.chunks` phải khớp **từng số** với cache `gemini-embedding-001` của chính
    `embed_text` chunk đó.

    Đây là bài DUY NHẤT phân biệt được **provider nào** đã ghi. Ba tiêu chí nghiệm thu hiển nhiên —
    `count(*) = 800`, `vector_dims = 2048`, không còn id 1.0 — đều **xanh y hệt** nếu ai đó tiêm lại
    `derive_vector`: sau PR-1 mặc định của nó bám `EMBEDDING_DIM` nên nó cũng sinh 2048 chiều, cột
    cũng nhận, không lỗi nào nổ. Lúc đó DB chứa 800 dòng bag-of-words nằm dưới nhãn
    `gemini-embedding-001` và không truy vấn SQL nào nhìn ra.

    Quét đột biến: đổi mặc định của `ingest_all` về một adapter bọc `derive_vector` thì cả suite
    vẫn xanh trừ bài này.
    """
    await ingest_callisto_v2.ingest_all(pool)

    chunks = load_corpus_v2(ingest_callisto_v2.CORPUS_2_0)
    chunk = min(chunks, key=lambda c: c.chunk_id)
    mong_doi = ingest_callisto_v2.CachedGeminiEmbedding()._inner.cache.get(chunk.embedding_input)
    assert mong_doi is not None, "tiền đề hỏng: cache không có chunk này"

    async with pool.connection() as conn, conn.transaction():  # type: ignore[attr-defined]
        await _bind_tenant(conn, chunk.tenant_id)
        cursor = await conn.execute("SELECT embedding FROM kb.chunks WHERE chunk_id = %s", (chunk.chunk_id,))
        row = await cursor.fetchone()

    assert row is not None, f"{chunk.chunk_id} không có trong DB sau ingest"
    thuc_te = [float(x) for x in row[0].strip("[]").split(",")]
    assert len(thuc_te) == len(mong_doi) == 2048
    for i, (a, b) in enumerate(zip(thuc_te, mong_doi, strict=True)):
        assert a == pytest.approx(b, abs=1e-6), f"chiều {i} lệch: {a} != {b} — provider ghi KHÔNG phải Gemini"


async def test_purge_don_chunk_1_0_con_sot_ma_upsert_khong_dong_toi(pool: object) -> None:
    """`purge=True` phải xoá chunk corpus **1.0** còn sót; `purge=False` thì KHÔNG.

    Hai vế trong một bài vì chúng là hai nửa của cùng một quyết định. Vế thứ hai mới là vế dễ mất:
    `index` dùng `ON CONFLICT DO UPDATE`, mà `chunk_id` 1.0 (`ankor-access-001#c1`) không trùng bất
    kỳ `chunk_id` 2.0 nào — nên upsert **không bao giờ** đụng tới nó. Không có `purge` thì 140 chunk
    1.0 nằm lại vĩnh viễn, trộn vào kết quả truy xuất của corpus 2.0 ở cùng tenant/vai.

    (`TRUNCATE` trong migration của PR-1 chỉ chạy khi chiều cột lệch, nên nó không cứu được lần nạp
    lại thứ hai — xem docstring `purge_tenants`.)
    """
    chunks = load_corpus_v2(ingest_callisto_v2.CORPUS_2_0)
    tenant = min(chunks, key=lambda c: c.chunk_id).tenant_id
    sot = "ankor-access-001#c1"

    async def dem_sot() -> int:
        async with pool.connection() as conn, conn.transaction():  # type: ignore[attr-defined]
            await _bind_tenant(conn, tenant)
            cur = await conn.execute("SELECT count(*) FROM kb.chunks WHERE chunk_id = %s", (sot,))
            return int((await cur.fetchone())[0])

    async def gieo_chunk_1_0() -> None:
        async with pool.connection() as conn, conn.transaction():  # type: ignore[attr-defined]
            await _bind_tenant(conn, tenant)
            await conn.execute(
                "INSERT INTO kb.chunks (chunk_id, tenant_id, section_role, text, embedding)"
                " VALUES (%s, %s, 'public', 'chunk 1.0 còn sót', %s) ON CONFLICT DO NOTHING",
                (sot, tenant, str([0.0] * 2048)),
            )

    await gieo_chunk_1_0()
    assert await dem_sot() == 1, "tiền đề hỏng: chưa gieo được chunk 1.0"
    await ingest_callisto_v2.ingest_all(pool)  # purge=False
    assert await dem_sot() == 1, "upsert KHÔNG dọn được id 1.0 — đó chính là lý do cần purge"

    assert await ingest_callisto_v2.ingest_all(pool, purge=True) == 800
    assert await dem_sot() == 0, "purge=True phải dọn sạch chunk 1.0"


async def test_cli_chay_that_co_purge_khong_de_sot_chunk_1_0(pool: object) -> None:
    """Đường CLI (`_run`, thứ `main()` gọi) phải bật `purge`.

    `ingest_all` mặc định `purge=False` để giữ tính idempotent mà bài trên canh — nghĩa là bật
    `purge` cho CLI là một lựa chọn nằm ở **đúng một dòng** trong `_run`, và không bài nào ở trên
    chạm tới dòng đó. Gieo đột biến `purge=True` → `purge=False` thì cả suite 754 bài vẫn xanh:
    CLI im lặng để lại chunk 1.0, đúng cái bug PR-3 sinh ra để sửa.

    Chạy `_run` thật (tự dựng pool từ DSN) chứ không gọi `ingest_all` — nếu chỉ gọi `ingest_all`
    thì bài này canh lại thứ bài khác đã canh, và bỏ trống đúng dòng cần canh.
    """
    chunks = load_corpus_v2(ingest_callisto_v2.CORPUS_2_0)
    tenant = min(chunks, key=lambda c: c.chunk_id).tenant_id
    sot = "ankor-access-001#c1"

    async with pool.connection() as conn, conn.transaction():  # type: ignore[attr-defined]
        await _bind_tenant(conn, tenant)
        await conn.execute(
            "INSERT INTO kb.chunks (chunk_id, tenant_id, section_role, text, embedding)"
            " VALUES (%s, %s, 'public', 'chunk 1.0 còn sót', %s) ON CONFLICT DO NOTHING",
            (sot, tenant, str([0.0] * 2048)),
        )

    assert await ingest_callisto_v2._run(os.environ["STUDIO_DATABASE_URL"]) == 800

    async with pool.connection() as conn, conn.transaction():  # type: ignore[attr-defined]
        await _bind_tenant(conn, tenant)
        cur = await conn.execute("SELECT count(*) FROM kb.chunks WHERE chunk_id = %s", (sot,))
        assert int((await cur.fetchone())[0]) == 0, "CLI phải purge — chunk 1.0 còn sót"


def test_provider_ingest_mac_dinh_KHONG_duoc_goi_mang() -> None:
    """`CachedGeminiEmbedding()` mặc định phải khoá mạng (`allow_network=False`).

    Đây là gạch INV-4 ("CI chạy 100% recorded fixtures"). Bật ngầm thì mọi thứ vẫn xanh hôm nay —
    cache đang phủ đủ 800/800 nên không có lần gọi API nào xảy ra để mà thấy. Nó chỉ cắn vào ngày
    corpus thêm một chunk: lúc đó CI lặng lẽ quay ra internet, tốn tiền, và số ghi xuống phụ thuộc
    một lần gọi mạng không tái lập được — hỏng đúng kiểu không ai nhìn thấy. Nên phải canh **cấu
    hình**, không đợi canh **hành vi**.

    Không cần DB.
    """
    assert ingest_callisto_v2.CachedGeminiEmbedding()._inner._allow_network is False
