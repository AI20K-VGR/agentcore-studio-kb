"""Tầng Postgres thật (`studio_kb.postgres`) — ingest + truy xuất vector, có DB sống.

Cần `docker compose -f docker-compose.test.yml up -d` và hai biến `STUDIO_DATABASE_URL` /
`STUDIO_DATABASE_URL_ADMIN`; thiếu thì fixture ở `conftest.py` gốc **skip** (không fail).

Trọng tâm là **chứng minh hàng rào**, không phải chứng minh truy xuất chạy. Hai test T1/T6 dưới đây
là bản **XANH THẬT** của hai test đang `xfail` ở `test_leak.py` — khác biệt: chúng chạy qua
`PgKbSearch` (module mới), còn bản kia chạy qua `KbSearchService` vẫn đang `NotImplementedError`.

Mọi test chạy qua pool **non-owner** (`pool`, role `studio_app`), không phải `admin_pool`. Đây là
điều kiện để phép thử có ý nghĩa: RLS chỉ áp cho kết nối non-owner theo cách thông thường, và test
trên owner-pool sẽ trông như đã fence trong khi chẳng chứng minh được gì.

Không assert **thứ hạng**: embedding ở đây là fake băm-túi-từ 8 chiều (xem dưới), độ tương đồng của
nó không phản ánh ngữ nghĩa thật. Mọi assert dùng `top_k` đủ lớn để "có mặt / vắng mặt" là tính chất
của **bộ lọc**, không phụ thuộc chất lượng xếp hạng. Chất lượng xếp hạng là chuyện của embedding
thật (AIE-1), kiểm ở chỗ khác.
"""

from __future__ import annotations

import hashlib
import math

import pytest
from psycopg import sql
from studio_kb.doc_factory import Chunk, load_callisto
from studio_kb.postgres import KbIngest, PgKbSearch
from studio_kb.schema import EMBEDDING_DIM

_TOKEN_BUCKETS = EMBEDDING_DIM


class BagOfWordsEmbedding:
    """`EmbeddingService` giả, tất định, đúng `EMBEDDING_DIM` chiều.

    Băm mỗi token vào 1 trong 8 ô rồi chuẩn hoá — văn bản giống nhau ra vector giống nhau, văn bản
    chia sẻ từ thì gần nhau. Dùng `blake2b` chứ KHÔNG dùng `hash()` dựng sẵn: `hash()` của Python
    ngẫu nhiên hoá theo tiến trình (PYTHONHASHSEED), nên vector sẽ đổi giữa các lần chạy và test
    thành nhấp nháy.

    Không import `FakeEmbedding` của `apps/studio`: `.importlinter` cấm `studio_kb` chạm
    `studio_app`. Đó cũng là lý do `EMBEDDING_DIM` được ghim trong `schema.py` chứ không ở app.
    """

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]

    @staticmethod
    def _vector(text: str) -> list[float]:
        buckets = [0.0] * _TOKEN_BUCKETS
        for token in text.lower().split():
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=2).digest()
            buckets[int.from_bytes(digest, "big") % _TOKEN_BUCKETS] += 1.0
        norm = math.sqrt(sum(x * x for x in buckets))
        if norm == 0.0:
            # Vector 0 làm cosine không xác định (chia 0) — pgvector trả NaN và thứ tự thành vô
            # nghĩa. Văn bản rỗng phải ra một vector hợp lệ nào đó, không phải gốc toạ độ.
            return [1.0] + [0.0] * (_TOKEN_BUCKETS - 1)
        return [x / norm for x in buckets]


@pytest.fixture
def embedding() -> BagOfWordsEmbedding:
    return BagOfWordsEmbedding()


def _chunk(chunk_id: str, tenant: str, section_role: str, text: str) -> Chunk:
    return Chunk(chunk_id=chunk_id, text=text, tenant=tenant, section_role=section_role)


async def _count_rows(pool: object, tenant: str) -> int:
    async with pool.connection() as conn, conn.transaction():  # type: ignore[attr-defined]
        await conn.execute("SELECT set_config('app.tenant_id', %s, true)", (tenant,))
        cur = await conn.execute("SELECT count(*) FROM kb.chunks")
        row = await cur.fetchone()
    return int(row[0])


# ── Đường ghi ───────────────────────────────────────────────────────────────────


async def test_ingest_giu_nguyen_chunk_id_do_doc_factory_sinh(pool: object, embedding: object) -> None:
    """`chunk_id` phải là id tất định của doc-factory, KHÔNG phải UUID.

    Cột `chunk_id` có `DEFAULT gen_random_uuid()::text` (`schema.py:30`), nên câu INSERT bắt buộc
    ghi id tường minh để đè default. Quên là mọi `expected_citation` trong golden-set trỏ vào hư
    không — và hỏng lặng lẽ, vì hàng vẫn vào bảng bình thường.
    """
    chunks = [_chunk("ankor-leave-001#c1", "ankor", "public", "báo trước 3 ngày làm việc")]
    assert await KbIngest(pool, embedding).ingest(chunks) == 1  # type: ignore[arg-type]

    async with pool.connection() as conn, conn.transaction():  # type: ignore[attr-defined]
        await conn.execute("SELECT set_config('app.tenant_id', %s, true)", ("ankor",))
        cur = await conn.execute("SELECT chunk_id, section_role FROM kb.chunks")
        rows = await cur.fetchall()
    assert rows == [("ankor-leave-001#c1", "public")]


async def test_ingest_idempotent_chay_lai_khong_nhan_doi(pool: object, embedding: object) -> None:
    """`re_index` bắt **giữ nguyên `chunk_id`** (`callisto-doc-schema.md` §6) — `ON CONFLICT DO
    UPDATE` là cách thực hiện điều đó. Chạy lại phải cập nhật tại chỗ, không đẻ dòng mới."""
    ingest = KbIngest(pool, embedding)  # type: ignore[arg-type]
    chunks = [_chunk("ankor-leave-001#c1", "ankor", "public", "bản cũ")]
    await ingest.ingest(chunks)
    await ingest.ingest([_chunk("ankor-leave-001#c1", "ankor", "public", "bản mới")])

    assert await _count_rows(pool, "ankor") == 1
    async with pool.connection() as conn, conn.transaction():  # type: ignore[attr-defined]
        await conn.execute("SELECT set_config('app.tenant_id', %s, true)", ("ankor",))
        cur = await conn.execute("SELECT text FROM kb.chunks WHERE chunk_id = %s", ("ankor-leave-001#c1",))
        row = await cur.fetchone()
    assert row[0] == "bản mới"


async def test_ingest_hai_tenant_moi_ben_chi_thay_phan_minh(pool: object, embedding: object) -> None:
    """Ingest gom theo tenant, mỗi tenant một giao dịch — vì `app.tenant_id` là **một giá trị cho
    cả giao dịch**, trộn hai tenant sẽ bị `WITH CHECK` chặn vế thứ hai."""
    await KbIngest(pool, embedding).ingest(  # type: ignore[arg-type]
        [
            _chunk("ankor-leave-001#c1", "ankor", "public", "ankor báo trước 3 ngày"),
            _chunk("borea-leave-001#c1", "borea", "public", "borea báo trước 7 ngày"),
        ]
    )
    assert await _count_rows(pool, "ankor") == 1
    assert await _count_rows(pool, "borea") == 1


async def test_embedding_sai_chieu_bi_chan_ngay(pool: object) -> None:
    """Fail-fast ở tầng Python: cột là `vector(8)` nên Postgres cũng sẽ từ chối, nhưng báo tại đây
    chỉ thẳng thủ phạm là `EmbeddingService`, không phải câu INSERT."""

    class WrongDim:
        async def embed(self, texts: list[str]) -> list[list[float]]:
            return [[0.0] * (EMBEDDING_DIM + 1) for _ in texts]

    with pytest.raises(ValueError, match="sai chiều"):
        await KbIngest(pool, WrongDim()).ingest([_chunk("x#c1", "ankor", "public", "t")])  # type: ignore[arg-type]


# ── Hàng rào: hai trục ──────────────────────────────────────────────────────────


async def test_t1_khong_ro_ri_cheo_tenant(pool: object, embedding: object) -> None:
    """**T1 IDOR** — bản XANH của `test_leak.py::test_t1_idor` (đang `xfail`).

    Khẳng định CÓ MẶT trước, VẮNG MẶT sau: một impl hỏng trả `[]` sẽ pass vế loại trừ một cách vô
    nghĩa (tập rỗng loại trừ mọi thứ). Truy xuất phải chạy thật thì loại trừ mới có ý nghĩa.
    """
    await KbIngest(pool, embedding).ingest(  # type: ignore[arg-type]
        [
            _chunk("ankor-leave-001#c1", "ankor", "public", "hồ sơ mật của ankor"),
            _chunk("borea-leave-001#c1", "borea", "public", "hồ sơ mật của borea"),
        ]
    )
    hits = await PgKbSearch(pool, embedding).search("hồ sơ mật", "ankor", ["public"], 10)  # type: ignore[arg-type]

    ids = {h.chunk_id for h in hits}
    assert "ankor-leave-001#c1" in ids
    assert "borea-leave-001#c1" not in ids
    assert all(h.tenant == "ankor" for h in hits)


async def test_t6_khong_ro_ri_cheo_vai(pool: object, embedding: object) -> None:
    """**T6 label-spoof** — cạnh yếu nhất: `schema.py` policy CHỈ khoá `tenant_id`, `section_role`
    không có RLS đứng sau. Chặn nó hoàn toàn dựa vào `WHERE section_role = ANY(...)`; bỏ mệnh đề đó
    là hở mà không lưới nào đỡ.

    Có cả phép thử ngược (hỏi đúng vai thì thấy) — nếu không, một impl luôn trả `[]` sẽ pass.
    """
    await KbIngest(pool, embedding).ingest(  # type: ignore[arg-type]
        [
            _chunk("ankor-salary-001#c1", "ankor", "hr", "thang lương gồm 6 bậc"),
            _chunk("ankor-leave-001#c1", "ankor", "public", "thang đo nghỉ phép 6 ngày"),
        ]
    )
    search = PgKbSearch(pool, embedding)  # type: ignore[arg-type]

    sai_vai = await search.search("thang lương", "ankor", ["engineering"], 10)
    assert all(h.chunk_id != "ankor-salary-001#c1" for h in sai_vai)
    assert all(h.section_role == "engineering" for h in sai_vai)

    dung_vai = await search.search("thang lương", "ankor", ["hr"], 10)
    assert "ankor-salary-001#c1" in {h.chunk_id for h in dung_vai}


async def test_section_roles_rong_la_khong_co_quyen_nao(pool: object, embedding: object) -> None:
    """Rỗng phải hiểu là **không quyền nào**, tuyệt đối không phải "bỏ lọc". Đọc nhầm chiều này là
    kiểu hở fence kinh điển: request không khai vai → thấy tất cả."""
    await KbIngest(pool, embedding).ingest(  # type: ignore[arg-type]
        [_chunk("ankor-leave-001#c1", "ankor", "public", "nội dung")]
    )
    assert await PgKbSearch(pool, embedding).search("nội dung", "ankor", [], 10) == []  # type: ignore[arg-type]


async def test_top_k_khong_am_va_cat_dung_so_luong(pool: object, embedding: object) -> None:
    await KbIngest(pool, embedding).ingest(  # type: ignore[arg-type]
        [_chunk(f"ankor-leave-001#c{n}", "ankor", "public", f"đoạn số {n} nói về nghỉ phép") for n in (1, 2, 3)]
    )
    search = PgKbSearch(pool, embedding)  # type: ignore[arg-type]
    assert len(await search.search("nghỉ phép", "ankor", ["public"], 2)) == 2
    assert await search.search("nghỉ phép", "ankor", ["public"], 0) == []


async def test_bo_callisto_that_25_chunk_khong_ro_ri(pool: object, embedding: object) -> None:
    """Chạy trên **bộ tài liệu thật**, không phải dữ liệu bịa trong test: nạp cả 25 chunk rồi soi
    hai phạm vi của SC-01 và SC-05.

    Đây là phép thử end-to-end gần nhất với thứ golden-set sẽ chạy: doc-factory → ingest →
    truy xuất, cùng dữ liệu mà `golden/smoke-5.yaml` gán nhãn.
    """
    chunks = load_callisto()
    assert await KbIngest(pool, embedding).ingest(chunks) == 25  # type: ignore[arg-type]

    search = PgKbSearch(pool, embedding)  # type: ignore[arg-type]

    # phạm vi SC-01: ankor/public — 14 chunk public toàn bộ, nhưng chỉ 9 của ankor
    sc01 = await search.search("nghỉ phép báo trước", "ankor", ["public"], 50)
    assert sc01, "truy xuất phải trả về thật thì phép loại trừ mới có nghĩa"
    assert all(h.tenant == "ankor" and h.section_role == "public" for h in sc01)
    assert not any(h.chunk_id.startswith("borea-") for h in sc01)

    # phạm vi SC-05: ankor/engineering — không doc nào mang vai này → rỗng, và đó là ĐÚNG
    assert await search.search("thang lương", "ankor", ["engineering"], 50) == []
    # phản chứng: cùng câu hỏi, đúng vai `hr` thì thấy → rỗng ở trên là do LỌC VAI
    assert await search.search("thang lương", "ankor", ["hr"], 50)


async def test_khong_dat_tenant_thi_khong_thay_gi(pool: object, embedding: object) -> None:
    """Fail-closed của RLS: phiên chưa đặt `app.tenant_id` thì `current_setting(..., true)` ra NULL,
    và `tenant_id = NULL` không bao giờ đúng → thấy 0 dòng, KHÔNG phải thấy tất cả.

    Đây là tính chất của `schema.py`, kiểm ở đây vì `postgres.py` dựa hoàn toàn vào nó cho trục
    tenant — nếu nó đổi thành fail-open thì `WHERE tenant_id` còn lại là tầng phòng thủ duy nhất.
    """
    await KbIngest(pool, embedding).ingest(  # type: ignore[arg-type]
        [_chunk("ankor-leave-001#c1", "ankor", "public", "nội dung")]
    )
    async with pool.connection() as conn:  # type: ignore[attr-defined]
        cur = await conn.execute(sql.SQL("SELECT count(*) FROM kb.chunks"))
        row = await cur.fetchone()
    assert row[0] == 0
