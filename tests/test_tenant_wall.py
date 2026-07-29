"""INV-1 Tenant-Wall ở tầng data-plane của DE — Day 8 (`day-08.md:37,52`).

Vai DE hôm nay: *"`kb.search` áp tenant filter server-side (client khai tenant bị bỏ qua)"*. Việc
**phân giải** `session_id → tenant_id` là middleware của SWE (`day-08.md:36`); phần DE là: **cho một
`tenant_id` đã resolve, chỉ trả chunk của đúng tenant đó — bất kể nội dung query.**

## Vì sao file này tách khỏi `test_pg_kb.py`

`test_pg_kb.py` khoá fence ở tầng **Postgres/RLS** (cần DB sống, `set_config('app.tenant_id')`). File
này khoá fence ở tầng **`StaticKbSearch`** — bản `kb.search` **đang chạy thật** trong spine D4–D8
(in-memory, không DB). Hai tầng, hai lưới; INV-1 phải đứng ở **cả hai**, nên kiểm cả hai. Bản tĩnh
không có RLS đỡ lưng, nên mệnh đề lọc `tenant_id` trong `static_search.py:92` là hàng rào **duy nhất**
ở tầng này — đúng thứ cần một test canh.

## Điều KHÔNG kiểm ở đây (ranh giới với SWE)

Không dựng session/middleware. Chữ ký `search(query, tenant_id: UUID, ...)` **chỉ nhận UUID đã
resolve** — không có tham số nào nhận tenant slug do client khai, nên "client khai bị bỏ qua" đã đúng
ở tầng *chữ ký*. Ở đây chứng minh nửa còn lại: *cho UUID nào thì lọc đúng UUID đó*. Nửa "UUID đến từ
session, không từ client" là DoD của SWE.
"""

from __future__ import annotations

from uuid import uuid4

from studio_kb.doc_factory import TENANT_IDS, load_callisto
from studio_kb.static_search import StaticKbSearch

_ANKOR = TENANT_IDS["ankor"]
_BOREA = TENANT_IDS["borea"]


def _kb() -> StaticKbSearch:
    """Corpus Callisto thật (25 chunk, 2 tenant) — không dựng chunk giả: fence phải đứng trên chính
    dữ liệu golden-set đang chấm, không phải trên đồ chơi."""
    return StaticKbSearch(load_callisto())


async def test_query_nhac_tenant_khac_van_chi_tra_tenant_da_resolve() -> None:
    """KHÓA W1: query **cố tình nhắc tên tenant khác** vẫn chỉ ra chunk của tenant được truyền.

    Đây là mầm T1 (chéo-tenant, `smoke-5.yaml` SC-04): người ở `ankor` hỏi *"Hạn mức chi của **Borea**"*.
    Nội dung query nhắc "Borea" — nếu fence đặt sai chỗ (tin query, hoặc trộn tenant) thì chunk borea
    rò ra. Đúng phải: chỉ `tenant_id=ankor` quyết định, mọi kết quả là ankor, **0 chunk borea**.

    Kiểm cả hai chiều — chặn A→B mà quên B→A thì hàng rào một chiều, vẫn hở (đúng lý do `smoke` có
    SC-04 ↔ SC-09).
    """
    kb = _kb()

    # ankor hỏi về borea
    res = await kb.search("Hạn mức chi của Borea là bao nhiêu?", _ANKOR, ["public"], 5)
    assert res, "query có từ chung, phải ra vài chunk ankor — nếu rỗng là test tự vô hiệu"
    assert all(r.tenant_id == _ANKOR for r in res)
    assert not any(r.tenant_id == _BOREA for r in res)

    # borea hỏi về ankor (chiều ngược)
    res_rev = await kb.search("Thang lương của Ankor gồm những bậc nào?", _BOREA, ["public"], 5)
    # Guard đối xứng với dòng trên: thiếu nó thì `res_rev` rỗng làm hai assert dưới pass RỖNG NGHĨA
    # (`all([])` là True, `any([])` là False) — test xanh mà không khoá gì, đúng lúc chiều B→A là
    # thứ cần khoá nhất. Hiện `res_rev` không rỗng nhờ token "lương" khớp `borea-leave-001#c5`
    # ("Nghỉ không lương") — trùng hợp từ vựng, không phải Borea có bậc lương thật; sửa chữ trong
    # chunk đó là mất chiều này mà không ai biết. (SWE bắt, kb#4.)
    assert res_rev, "query có từ chung, phải ra vài chunk borea — nếu rỗng là test tự vô hiệu"
    assert all(r.tenant_id == _BOREA for r in res_rev)
    assert not any(r.tenant_id == _ANKOR for r in res_rev)


async def test_cung_query_khac_tenant_thi_ket_qua_roi_nhau() -> None:
    """KHÓA W2: **cùng nguyên văn query**, chỉ đổi `tenant_id` truyền vào → tenant của kết quả đổi theo.

    Đây là phần lõi của "client khai tenant bị bỏ qua": thứ **duy nhất** phân biệt hai lượt là tham
    số `tenant_id` (thứ đến từ session server-side), KHÔNG phải nội dung query. Nếu có lượt nào trả
    chunk của tenant kia thì tham số tenant không phải hàng rào thật.
    """
    kb = _kb()
    query = "Nhân viên xin nghỉ phép cần báo trước bao lâu?"  # SC-01/02: cả hai tenant đều có đáp

    as_ankor = await kb.search(query, _ANKOR, ["public"], 5)
    as_borea = await kb.search(query, _BOREA, ["public"], 5)

    assert as_ankor and as_borea, "cả hai tenant đều có chunk cho query này"
    assert {r.tenant_id for r in as_ankor} == {_ANKOR}
    assert {r.tenant_id for r in as_borea} == {_BOREA}
    # hai tập chunk_id rời nhau — không chunk nào lọt sang cả hai lượt
    assert not ({r.chunk_id for r in as_ankor} & {r.chunk_id for r in as_borea})


async def test_tenant_la_tra_rong_fail_closed() -> None:
    """KHÓA W3: `tenant_id` không khớp chunk nào (danh tính lạ) → **0 dòng**, không raise.

    Bản tĩnh không có RLS, nhưng phải giữ cùng ngữ nghĩa fail-closed như RLS ở `schema.py:55-58`:
    danh tính chưa biết thì thấy rỗng, KHÔNG phải thấy hết. Một UUID ngẫu nhiên (không thuộc corpus)
    dù query khớp từ vẫn phải ra rỗng — vì tenant là *yêu cầu*, không phải *gợi ý*.
    """
    kb = _kb()
    res = await kb.search("Nhân viên xin nghỉ phép cần báo trước bao lâu?", uuid4(), ["public"], 5)
    assert res == []
