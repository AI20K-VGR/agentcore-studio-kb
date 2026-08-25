"""`KbPipeline` (pipeline.py) — 5-method seam ĐIỀN cho corpus 2.0 (role theo tên file, giữ chunk_id).

Test-first (viết trước impl). Hai nhóm:
- **Pure** (`chunker`/`embed_invoke`): chạy mọi lúc, không cần DB.
- **DB** (`index`/`consent_purge`/`re_index`): dùng fixture `pool` ở `conftest.py` gốc — **skip** nếu
  chưa `docker compose -f docker-compose.test.yml up -d` (không fail). Mẫu theo `test_pg_kb.py`:
  pool **non-owner**, `WITH CHECK` cắn, và luật "**có mặt trước / vắng mặt sau**" cho phép loại trừ.

Corpus 2.0 (`docs/callisto-2.0-schema.md`): 1 file = 1 role, KHÔNG front-matter, KHÔNG override
(I5), thân rỗng bị cấm (I7), `chunk_id = "{doc_id}#c{n}"`. `re_index` bắt **giữ nguyên chunk_id** (§6).
"""

from __future__ import annotations

from uuid import UUID

import pytest
from studio_kb.doc_factory import TENANT_IDS, Chunk
from studio_kb.embeddings import derive_vector
from studio_kb.pipeline import KbPipeline
from studio_kb.schema import EMBEDDING_DIM

ANKOR_ID = TENANT_IDS["ankor"]
BOREA_ID = TENANT_IDS["borea"]

_DOC = "## Nghỉ phép\nBáo trước 3 ngày làm việc.\n## Thai sản\nNghỉ 6 tháng."


class _Embedding:
    """`EmbeddingService` giả tất định (bọc `derive_vector`, đúng `EMBEDDING_DIM`)."""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [derive_vector(t) for t in texts]


class _WrongDim:
    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * (EMBEDDING_DIM + 1) for _ in texts]


def _pipe(pool: object = None, embedding: object | None = None) -> KbPipeline:
    return KbPipeline(pool, embedding or _Embedding())  # type: ignore[arg-type]


def _mk(chunk_id: str, tenant_id: UUID, role: str, text: str, *, doc_id: str = "", doc_name: str = "") -> Chunk:
    return Chunk(chunk_id=chunk_id, text=text, tenant_id=tenant_id, section_role=role, doc_id=doc_id, doc_name=doc_name)


async def _count_rows(pool: object, tenant_id: UUID) -> int:
    async with pool.connection() as conn, conn.transaction():  # type: ignore[attr-defined]
        await conn.execute("SELECT set_config('app.tenant_id', %s, true)", (str(tenant_id),))
        cur = await conn.execute("SELECT count(*) FROM kb.chunks")
        row = await cur.fetchone()
    return int(row[0])


# ── chunker (pure) ───────────────────────────────────────────────────────────


async def test_chunker_cat_2_0_giu_chunk_id_va_role() -> None:
    """Cắt tài liệu 2.0 → `Chunk` với `chunk_id={doc_id}#c{n}`, mọi chunk cùng role (I6), text gồm heading."""
    chunks = await _pipe().chunker(_DOC, doc_id="ankor-hr-leave", tenant_id=ANKOR_ID, section_role="hr")
    assert [c.chunk_id for c in chunks] == ["ankor-hr-leave#c1", "ankor-hr-leave#c2"]
    assert all(c.section_role == "hr" and c.tenant_id == ANKOR_ID for c in chunks)
    assert chunks[0].text.startswith("## Nghỉ phép")


async def test_chunker_cam_override_I5() -> None:
    with pytest.raises(ValueError, match="override"):
        await _pipe().chunker(
            "## X {section: engineering}\nnội dung", doc_id="ankor-hr-leave", tenant_id=ANKOR_ID, section_role="hr"
        )


async def test_chunker_than_rong_bi_cam_I7() -> None:
    with pytest.raises(ValueError, match="rỗng"):
        await _pipe().chunker("## Rỗng\n\n## Có\nnội dung", doc_id="ankor-hr-x", tenant_id=ANKOR_ID, section_role="hr")


# ── embed_invoke (pure) ──────────────────────────────────────────────────────


async def test_embed_invoke_dung_chieu_va_so_luong() -> None:
    pipe = _pipe()
    chunks = await pipe.chunker(_DOC, doc_id="ankor-hr-leave", tenant_id=ANKOR_ID, section_role="hr")
    vecs = await pipe.embed_invoke(chunks)
    assert len(vecs) == len(chunks)
    assert all(len(v) == EMBEDDING_DIM for v in vecs)


async def test_embed_invoke_sai_chieu_raise() -> None:
    """Fail-fast chỉ thẳng thủ phạm là `EmbeddingService`, không để Postgres từ chối muộn ở `index`."""
    with pytest.raises(ValueError, match="sai chiều"):
        await _pipe(embedding=_WrongDim()).embed_invoke([_mk("x#c1", ANKOR_ID, "hr", "t")])


# ── index / consent_purge / re_index (cần DB) ────────────────────────────────


async def test_index_ghi_va_giu_chunk_id(pool: object) -> None:
    pipe = _pipe(pool)
    chunks = [_mk("ankor-hr-leave#c1", ANKOR_ID, "hr", "báo trước 3 ngày")]
    await pipe.index(chunks, await pipe.embed_invoke(chunks))
    async with pool.connection() as conn, conn.transaction():  # type: ignore[attr-defined]
        await conn.execute("SELECT set_config('app.tenant_id', %s, true)", (str(ANKOR_ID),))
        cur = await conn.execute("SELECT chunk_id, section_role FROM kb.chunks")
        rows = await cur.fetchall()
    assert rows == [("ankor-hr-leave#c1", "hr")]


async def test_index_hai_tenant_gom_theo_tenant(pool: object) -> None:
    """Trộn 2 tenant trong 1 lô: `index` phải gom theo tenant (mỗi tenant 1 giao dịch) để `WITH CHECK`
    không chặn vế thứ hai. Cả hai phải vào đủ."""
    pipe = _pipe(pool)
    chunks = [
        _mk("ankor-hr-leave#c1", ANKOR_ID, "hr", "ankor 3 ngày"),
        _mk("borea-hr-leave#c1", BOREA_ID, "hr", "borea 7 ngày"),
    ]
    await pipe.index(chunks, await pipe.embed_invoke(chunks))
    assert await _count_rows(pool, ANKOR_ID) == 1
    assert await _count_rows(pool, BOREA_ID) == 1


async def test_index_ghi_doc_id_column(pool: object) -> None:
    """`index` phải ghi cột `doc_id` MỚI (tách khỏi vai trò PK của `chunk_id`), không chỉ nhúng nó
    vào tiền tố `chunk_id` như trước — nếu không thì `delete_by_doc_id` không có gì để so khớp."""
    pipe = _pipe(pool)
    chunks = [_mk("ankor-hr-leave#c1", ANKOR_ID, "hr", "báo trước 3 ngày", doc_id="leave")]
    await pipe.index(chunks, await pipe.embed_invoke(chunks))
    async with pool.connection() as conn, conn.transaction():  # type: ignore[attr-defined]
        await conn.execute("SELECT set_config('app.tenant_id', %s, true)", (str(ANKOR_ID),))
        cur = await conn.execute("SELECT doc_id FROM kb.chunks WHERE chunk_id = %s", ("ankor-hr-leave#c1",))
        row = await cur.fetchone()
    assert row == ("leave",)


async def test_index_ghi_doc_name_column(pool: object) -> None:
    """`index` phải ghi cột `doc_name` — tên hiển thị NGƯỜI ĐỌC ĐƯỢC, tách khỏi `doc_id` (khoá kỹ
    thuật, slugify). Không có nó thì UI chỉ còn cách hiển thị thẳng `doc_id`/`chunk_id` (dữ liệu
    nội bộ), đúng thứ luật hiển thị cấm."""
    pipe = _pipe(pool)
    chunks = [
        _mk(
            "ankor-hr-leave#c1",
            ANKOR_ID,
            "hr",
            "báo trước 3 ngày",
            doc_id="hr-che-do-nghi-phep",
            doc_name="Chế độ nghỉ phép",
        )
    ]
    await pipe.index(chunks, await pipe.embed_invoke(chunks))
    async with pool.connection() as conn, conn.transaction():  # type: ignore[attr-defined]
        await conn.execute("SELECT set_config('app.tenant_id', %s, true)", (str(ANKOR_ID),))
        cur = await conn.execute("SELECT doc_name FROM kb.chunks WHERE chunk_id = %s", ("ankor-hr-leave#c1",))
        row = await cur.fetchone()
    assert row == ("Chế độ nghỉ phép",)


async def test_delete_by_doc_id_chi_xoa_dung_doc_cung_tenant(pool: object) -> None:
    """Xoá theo `doc_id` chỉ đụng đúng document đó — document khác cùng tenant phải nguyên vẹn."""
    pipe = _pipe(pool)
    chunks = [
        _mk("ankor-hr-leave#c1", ANKOR_ID, "hr", "leave 1", doc_id="leave"),
        _mk("ankor-hr-leave#c2", ANKOR_ID, "hr", "leave 2", doc_id="leave"),
        _mk("ankor-hr-expense#c1", ANKOR_ID, "hr", "expense 1", doc_id="expense"),
    ]
    await pipe.index(chunks, await pipe.embed_invoke(chunks))
    assert await pipe.delete_by_doc_id(ANKOR_ID, "leave") == 2
    assert await _count_rows(pool, ANKOR_ID) == 1  # "expense" còn nguyên


async def test_delete_by_doc_id_tenant_khac_khong_dung(pool: object) -> None:
    """Cùng chuỗi `doc_id` nhưng khác `tenant_id` — fail-closed, không đụng nhầm tenant kia
    (mirror `test_consent_purge_chi_xoa_dung_tenant`)."""
    pipe = _pipe(pool)
    chunks = [
        _mk("ankor-hr-leave#c1", ANKOR_ID, "hr", "ankor leave", doc_id="leave"),
        _mk("borea-hr-leave#c1", BOREA_ID, "hr", "borea leave", doc_id="leave"),
    ]
    await pipe.index(chunks, await pipe.embed_invoke(chunks))
    assert await pipe.delete_by_doc_id(ANKOR_ID, "leave") == 1
    assert await _count_rows(pool, ANKOR_ID) == 0
    assert await _count_rows(pool, BOREA_ID) == 1  # tenant khác nguyên vẹn


async def test_delete_by_doc_id_khong_ton_tai_tra_0(pool: object) -> None:
    assert await _pipe(pool).delete_by_doc_id(ANKOR_ID, "khong-ton-tai") == 0


async def test_chunks_for_tenant_returns_every_section_of_that_tenant(pool: object) -> None:
    """Trả **mọi** phòng ban của tenant, và KHÔNG lấy tenant khác.

    Vế "mọi phòng ban" là vế đắt: `build_cases` cần chunk của ≥2 vai để ghép chéo dựng case bẫy.
    Fixture bất đối xứng — `hr` 2 chunk, `finance` 1, và tenant KHÁC có 1 chunk cũng `hr`."""
    pipe = _pipe(pool)
    chunks = [
        _mk("ankor-hr-a#c1", ANKOR_ID, "hr", "nghi phep bao truoc ba ngay", doc_id="leave"),
        _mk("ankor-hr-b#c1", ANKOR_ID, "hr", "phu cap an trua", doc_id="meal"),
        _mk("ankor-fin-a#c1", ANKOR_ID, "finance", "han muc chi tieu", doc_id="limit"),
        _mk("borea-hr-a#c1", BOREA_ID, "hr", "cua tenant khac", doc_id="leave"),
    ]
    await pipe.index(chunks, await pipe.embed_invoke(chunks))

    result = await pipe.chunks_for_tenant(ANKOR_ID)

    assert [c.chunk_id for c in result] == ["ankor-fin-a#c1", "ankor-hr-a#c1", "ankor-hr-b#c1"]
    assert {c.section_role for c in result} == {"hr", "finance"}, (
        "phải trả CẢ HAI vai — một vai thì build_cases không ghép chéo được và bộ sinh ra 0 case bẫy"
    )
    assert all(c.tenant_id == ANKOR_ID for c in result)


async def test_chunks_for_tenant_keeps_doc_id_and_orders_deterministically(pool: object) -> None:
    """`doc_id` đọc lại được, và thứ tự theo `chunk_id` — hai lượt gọi cho CÙNG danh sách.

    Thứ tự là vế đắt hơn: `build_cases` khai tất định, và nó tất định chỉ khi đầu vào tất định. Ghi
    chunk theo thứ tự NGƯỢC với `chunk_id` để bài này đỏ nếu ai đó bỏ `ORDER BY` và Postgres tình
    cờ trả theo thứ tự chèn."""
    pipe = _pipe(pool)
    chunks = [
        _mk("ankor-hr-z#c1", ANKOR_ID, "hr", "chunk z", doc_id="zeta", doc_name="Zeta"),
        _mk("ankor-hr-a#c1", ANKOR_ID, "hr", "chunk a", doc_id="alpha", doc_name="Alpha"),
        _mk("ankor-hr-m#c1", ANKOR_ID, "hr", "chunk m", doc_id="mu", doc_name="Mu"),
    ]
    await pipe.index(chunks, await pipe.embed_invoke(chunks))

    first = await pipe.chunks_for_tenant(ANKOR_ID)
    second = await pipe.chunks_for_tenant(ANKOR_ID)

    assert [c.chunk_id for c in first] == ["ankor-hr-a#c1", "ankor-hr-m#c1", "ankor-hr-z#c1"]
    assert [c.doc_id for c in first] == ["alpha", "mu", "zeta"]
    assert [c.doc_name for c in first] == ["Alpha", "Mu", "Zeta"]
    assert first == second


async def test_chunks_for_tenant_returns_empty_for_tenant_without_chunks(pool: object) -> None:
    assert await _pipe(pool).chunks_for_tenant(BOREA_ID) == []


async def test_consent_purge_chi_xoa_dung_tenant(pool: object) -> None:
    """Xoá của A → A rỗng; B **không đụng** (fail-closed). Trả số dòng đã xoá."""
    pipe = _pipe(pool)
    chunks = [
        _mk("ankor-hr-leave#c1", ANKOR_ID, "hr", "ankor 1"),
        _mk("ankor-hr-leave#c2", ANKOR_ID, "hr", "ankor 2"),
        _mk("borea-hr-leave#c1", BOREA_ID, "hr", "borea 1"),
    ]
    await pipe.index(chunks, await pipe.embed_invoke(chunks))
    assert await pipe.consent_purge(ANKOR_ID) == 2
    assert await _count_rows(pool, ANKOR_ID) == 0
    assert await _count_rows(pool, BOREA_ID) == 1  # tenant khác nguyên vẹn


async def test_re_index_giu_chunk_id_va_so_luong(pool: object) -> None:
    """`re_index` đọc lại toàn bộ của tenant → nhúng lại → ghi đè idempotent, **giữ nguyên chunk_id** (§6)."""
    pipe = _pipe(pool)
    chunks = [_mk(f"ankor-hr-leave#c{n}", ANKOR_ID, "hr", f"đoạn {n}") for n in (1, 2)]
    await pipe.index(chunks, await pipe.embed_invoke(chunks))
    assert await pipe.re_index(ANKOR_ID) == 2
    assert await _count_rows(pool, ANKOR_ID) == 2  # không nhân đôi
    async with pool.connection() as conn, conn.transaction():  # type: ignore[attr-defined]
        await conn.execute("SELECT set_config('app.tenant_id', %s, true)", (str(ANKOR_ID),))
        cur = await conn.execute("SELECT chunk_id FROM kb.chunks ORDER BY chunk_id")
        ids = [r[0] for r in await cur.fetchall()]
    assert ids == ["ankor-hr-leave#c1", "ankor-hr-leave#c2"]


async def test_re_index_tenant_rong_tra_0(pool: object) -> None:
    assert await _pipe(pool).re_index(ANKOR_ID) == 0


async def test_re_index_giu_doc_id(pool: object) -> None:
    """`re_index` dựng lại `Chunk` TỪ DB — phải giữ cột `doc_id`, không rơi về rỗng (nếu không thì
    một vòng re-index âm thầm làm `delete_by_doc_id` hết tác dụng cho mọi chunk đã re-index)."""
    pipe = _pipe(pool)
    chunks = [_mk("ankor-hr-leave#c1", ANKOR_ID, "hr", "báo trước 3 ngày", doc_id="leave")]
    await pipe.index(chunks, await pipe.embed_invoke(chunks))
    assert await pipe.re_index(ANKOR_ID) == 1
    async with pool.connection() as conn, conn.transaction():  # type: ignore[attr-defined]
        await conn.execute("SELECT set_config('app.tenant_id', %s, true)", (str(ANKOR_ID),))
        cur = await conn.execute("SELECT doc_id FROM kb.chunks WHERE chunk_id = %s", ("ankor-hr-leave#c1",))
        row = await cur.fetchone()
    assert row == ("leave",)


async def test_re_index_giu_doc_name(pool: object) -> None:
    """`re_index` phải giữ cột `doc_name` — cùng lý do `doc_id`: dựng lại `Chunk` TỪ DB, không suy
    lại từ đâu khác. Rơi về rỗng thì UI mất nhãn hiển thị sau MỖI lần re-index."""
    pipe = _pipe(pool)
    chunks = [_mk("ankor-hr-leave#c1", ANKOR_ID, "hr", "báo trước 3 ngày", doc_id="leave", doc_name="Nghỉ phép")]
    await pipe.index(chunks, await pipe.embed_invoke(chunks))
    assert await pipe.re_index(ANKOR_ID) == 1
    async with pool.connection() as conn, conn.transaction():  # type: ignore[attr-defined]
        await conn.execute("SELECT set_config('app.tenant_id', %s, true)", (str(ANKOR_ID),))
        cur = await conn.execute("SELECT doc_name FROM kb.chunks WHERE chunk_id = %s", ("ankor-hr-leave#c1",))
        row = await cur.fetchone()
    assert row == ("Nghỉ phép",)


# ── embed-view + re_index: chuỗi đem embed phải TÁI LẬP ĐƯỢC sau vòng đời DB ──


class _Ghi:
    """`EmbeddingService` GHI LẠI đúng chuỗi nó được đưa — để so ingest vs re_index."""

    def __init__(self) -> None:
        self.da_embed: list[str] = []

    async def embed(self, texts: list[str]) -> list[list[float]]:
        self.da_embed.extend(texts)
        return [derive_vector(t) for t in texts]


async def test_embed_invoke_dung_embedding_input_khong_dung_text() -> None:
    """`embed_invoke` phải embed `embedding_input` (có ngữ cảnh doc), KHÔNG phải `text` trần.

    Không có bài này thì thêm `embed_text` vào `Chunk` vẫn xanh trong khi đường ghi thật bỏ qua nó —
    harness đẹp lên mà production không đổi gì (xanh giả)."""
    ghi = _Ghi()
    chunk = Chunk(
        chunk_id="ankor-hr-leave#c1",
        text="## Nghỉ ốm\n30 ngày.",
        tenant_id=ANKOR_ID,
        section_role="hr",
        embed_text="Chính sách nghỉ phép\n## Nghỉ ốm\n30 ngày.",
    )
    await _pipe(None, ghi).embed_invoke([chunk])
    assert ghi.da_embed == ["Chính sách nghỉ phép\n## Nghỉ ốm\n30 ngày."]


@pytest.mark.usefixtures("pool")
async def test_re_index_nhung_lai_DUNG_CHUOI_da_embed(pool: object) -> None:
    """`re_index` phải nhúng lại ĐÚNG chuỗi mà `index` đã nhúng — nếu không, một vòng re-index âm
    thầm đổi vector của mọi chunk (mất ngữ cảnh doc + boilerplate quay lại) mà không id nào chết.

    Đây là cái bẫy riêng của thiết kế embed-view: `re_index` dựng lại `Chunk` TỪ DB, nên chuỗi đem
    embed phải được LƯU, không thể suy lại từ một dòng đơn lẻ (tiêu đề doc không nằm trong text nào)."""
    chunks = [
        Chunk(
            chunk_id="ankor-hr-leave#c1",
            text="## Nghỉ ốm\n30 ngày.",
            tenant_id=ANKOR_ID,
            section_role="hr",
            embed_text="Chính sách nghỉ phép\n## Nghỉ ốm\n30 ngày.",
        ),
        Chunk(
            chunk_id="ankor-hr-leave#c2",
            text="## Thai sản\n6 tháng.",
            tenant_id=ANKOR_ID,
            section_role="hr",
            embed_text="Chính sách nghỉ phép\n## Thai sản\n6 tháng.",
        ),
    ]
    luc_ingest = _Ghi()
    pipe_in = _pipe(pool, luc_ingest)
    await pipe_in.index(chunks, await pipe_in.embed_invoke(chunks))

    luc_reindex = _Ghi()
    assert await _pipe(pool, luc_reindex).re_index(ANKOR_ID) == 2
    assert sorted(luc_reindex.da_embed) == sorted(luc_ingest.da_embed), (
        "re_index nhúng chuỗi KHÁC lúc ingest → vector trôi âm thầm sau mỗi vòng re-index"
    )
