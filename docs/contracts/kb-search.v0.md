---
id: studio.contract.kb-search.v0
type: interface-draft
status: v0-draft
freeze: NOT-FROZEN
freeze_target: D11
contract_ref: umbrella-contract §3.3
pen: DE — Nguyễn Đông Anh
date: 2026-07-21
updated: 2026-07-22
---

# 🖊️ kb.search — INTERFACE v0 (NHÁP)

> ## ⚠️ v0 — CHƯA FREEZE. Dự kiến freeze **D11**.
> Bản v0 tuần 1 **CHƯA CÓ FENCE** — đây là chủ ý, không phải thiếu sót. Đọc §5 trước khi code:
> ba luật fence sẽ có hiệu lực từ S2/S3, viết sẵn để không ai thiết kế theo hướng phải đập đi.

**Bút:** DE · **Neo:** umbrella §3.3 · **Người dùng:** AIE-1 (node `kb-retrieve`), AIE-2 (citation-accuracy).

> 📌 **Đổi ở D3 (22/07):** chữ ký v0 nâng từ **3 lên 4 tham số** — nhận `section_roles` ngay từ tuần 1.
> Đây là câu trả lời cho **Q-A** (§8), quyết bằng ràng buộc kỹ thuật chứ không phải sở thích. Lý do ở
> §3. Bản 3 tham số cũ giữ trong §9 để D11 còn vết.

---

## 1. Chữ ký v0 — tuần 1

```python
from uuid import UUID
from studio_contracts.kb import KbSearch, KbSearchResultItem

async def search(
    query: str,
    tenant_id: UUID,
    section_roles: list[str],
    top_k: int,
) -> list[KbSearchResultItem]: ...
```

**Tuần 1 trả `[]` — luôn luôn, với mọi input.** Chưa có doc trong KB, chưa có fence.

`KbSearchResultItem` (đã có sẵn, `packages/contracts/src/studio_contracts/kb.py:21-28`, `frozen=True`):

```
chunk_id: str · text: str · score: float · tenant_id: UUID · section_role: str
```

> **D-13 (#25, 24/07):** `tenant` → `tenant_id: UUID`. Danh tính tenant là `core.tenants.id` bất
> biến, không phải slug trùng-được. Slug (`ankor`/`borea`) chỉ còn là **nhãn hiển thị** — vẫn nằm
> trong `chunk_id` (`"ankor-leave-001#c1"`). Bản kb đã adopt: cột `kb.chunks.tenant_id UUID`, RLS
> cast `::uuid` bọc `NULLIF(...,'')`. Xem §9 lịch sử.

`top_k` **không có giá trị mặc định** trong Protocol — bên gọi phải truyền.

**`chunk_id` là field quan trọng nhất.** Không có nó thì "câu trả lời có trích dẫn" (cited answer) không kiểm chứng được, và citation-accuracy chỉ còn là cảm tính.

---

## 2. Chữ ký đích — bản freeze §3.3

```python
async def search(
    query: str,
    tenant_id: UUID,
    section_roles: list[str],
    top_k: int,
) -> list[KbSearchResultItem]: ...
```

**Giống hệt §1.** Từ D3, v0 và bản freeze dùng **chung một chữ ký**; khác nhau ở **hành vi**, không ở hình dạng.

---

## 3. Vì sao 4 tham số, không phải 3

### 3.1 Bảng đối chiếu — brief nói 3, code nói 4

Đây là chỗ lệch **có chủ đích**, ghi lại đầy đủ để D11 và người chấm truy được:

| Nguồn | Chữ ký | Nguyên văn |
|---|---|---|
| `docs/requirements/week-1/days/day-02.md:36` | **3** | *"`kb.search(query,tenant,top_k)` signature"* |
| `docs/requirements/week-1/days/day-04.md:22` | **3** | *"`kb.search(query,tenant,top_k) -> [{chunk_id,text,score,tenant}]`"* |
| `packages/contracts/src/studio_contracts/kb.py:35-41` | **4** | Protocol `KbSearch` — có `section_roles` |
| `packages/kb/src/studio_kb/search.py:38-44` | **4** | seam `KbSearchService.search` — có `section_roles` |
| **Bản v0.1 này** | **4** | theo code |

**Chọn theo code.** Hai lý do:

1. **DoD Day 4 không chấm số tham số.** `day-04.md:52-57` chấm: `kb.search` trả `chunk_id` · 5 case nhãn tay · bảng điểm 5 dòng · NDA sạch · daily-note. Hàm 4 tham số đạt đủ, y như hàm 3.
2. **Hàm 3 tham số thì vỡ thật.** Node `kb-retrieve` của AIE-1 gọi 4 đối số → `TypeError` tại call-site. Một bên không mất gì, một bên hỏng — không phải lựa chọn cân bằng.

Chữ trong brief là **mô tả rút gọn cho người đọc**; `studio_contracts.kb.KbSearch` là contract có hiệu lực trong code. Khi hai thứ lệch, cái compiler đọc được thì cái đó thắng.

> ⚠️ **Đã báo mentor** — đây là lệch chữ trong brief ở **hai ngày** (D2 và D4), không phải quyết định tự phát của DE. AIE-1 đã chốt nhận 4 tham số ở D3.

### 3.2 Hai tầng hỏng nếu dùng 3 tham số

Bản v0 đầu tiên (D2) ghi 3 tham số — đúng chữ trong brief tuần 1. Sang D3, AIE-1 bắt đầu nối
`kb-retrieve` thật, và 3 tham số hỏng ở **hai tầng**:

1. **Lúc chạy:** node gọi `search(query, tenant, section_roles, top_k)` — 4 đối số. Hàm 3 tham số →
   `TypeError` ngay tại call-site.
2. **Lúc type-check:** `mypy` **có** kiểm chữ ký khi xét Protocol conformance →
   `x: KbSearch = impl_3_tham_số` báo lỗi.

Cộng thêm: seam thật (`studio_kb.search.KbSearchService.search`, DE điền từ Day 4) **đã là 4 tham số
từ trước**. Giữ v0 ở 3 nghĩa là cố tình để chữ ký trong tài liệu lệch với chữ ký trong code — và bắt
AIE-1 sửa call-site lần hai khi fence land.

**Nhận `section_roles` ngay từ v0 không phải là "làm fence sớm".** v0 **nhận rồi bỏ qua**: tham số có
mặt để chữ ký ổn định, hành vi lọc thì để S2/S3. Đây là cách rẻ nhất để chữ ký **không bao giờ phải
đổi** — thứ duy nhất thực sự tốn kém khi có người đã nối vào.

> ⚠️ **Đừng dùng `isinstance(x, KbSearch)` làm bằng chứng đã khớp Protocol.** `KbSearch` có
> `@runtime_checkable`, nhưng `isinstance` với Protocol **chỉ kiểm tên method có tồn tại, KHÔNG kiểm
> chữ ký**. Một stub 3 tham số vẫn có method tên `search` → `isinstance` trả **`True`**. Đã thử trực
> tiếp trên repo này, không phải suy từ tài liệu. Muốn cổng kiểm thật thì **gọi đủ 4 keyword-arg và
> assert kết quả**.

---

## 4. Đường nâng v0 → freeze: **chỉ siết HÀNH VI**

| | v0 (tuần 1) | freeze (§3.3) | Loại thay đổi |
|---|---|---|---|
| chữ ký (4 tham số) | ✅ | ✅ | *giữ nguyên* |
| shape item trả về | ✅ | ✅ | *giữ nguyên* |
| `section_roles` | **nhận, bỏ qua** | resolve server-side, dùng để lọc | **siết hành vi** |
| kết quả | luôn `[]` | chunk khớp scope | **siết hành vi** |

**Không còn thay đổi nào ở tầng chữ ký.** Nâng lên freeze = điền thân hàm, không sửa call-site. Ai
nối `kb-retrieve` theo §1 hôm nay thì không phải đụng lại.

---

## 5. Ba luật SẼ ràng buộc từ S2/S3 — đọc trước khi thiết kế

v0 chưa fence, nhưng ba luật dưới đây là **đích không đổi**. Ghi ở đây để không ai xây theo hướng
sau này phải đập đi. Nguồn: umbrella §3.3 + docstring `src/studio_kb/search.py`.

### 5.1 Lọc TẠI RETRIEVAL, fail-closed

Chunk nằm ngoài phạm vi người gọi được phép đọc **không bao giờ được rời khỏi hàm này**. Lọc phải
nằm trong câu truy vấn, không phải lọc sau khi đã lấy ra.

Fail-closed nghĩa là: khi không xác định được phạm vi → trả **0 kết quả**, không trả tất cả. Mặc
định lúc hỏng phải là *không cho gì*, chứ không phải *cho hết*.

> Đây cũng chính là lý do `[]` của tuần 1 **không phải chuyện tạm bợ**: nó là hình dạng vĩnh viễn của
> fail-closed. Node xử lý êm `[]` từ bây giờ thì S2 không phải sửa luồng.

### 5.2 `section_roles` do SERVER quyết

Giá trị `section_roles` client gửi lên là một **yêu cầu**, không phải một **quyền**. Server tự
resolve phạm vi thật từ phiên làm việc; danh sách client tự khai bị bỏ qua.

Đây chính là thứ chặn **T6 label-spoof**: nếu tin danh sách client gửi lên, kẻ tấn công chỉ cần
khai thêm một `section_role` là đọc được phần không thuộc về mình — không cần khai thác lỗ hổng gì.

> Hệ quả cho v0: tham số `section_roles` **có mặt trong chữ ký** không có nghĩa giá trị client truyền
> vào sẽ được tin. Ở v0 nó bị bỏ qua vì chưa lọc; từ S2 nó bị bỏ qua vì **server tự resolve**. Hai
> giai đoạn, cùng một kết luận: đừng thiết kế gì dựa trên việc client khai đúng.

### 5.3 CẤM trả hết rồi nhờ LLM lọc

Anti-pattern bị cấm bằng chữ: lấy toàn bộ chunk rồi dặn model *"chỉ dùng phần thuộc tenant X"*.

Sai vì hai lẽ. Một: dữ liệu **đã rời khỏi** vùng an toàn — nó nằm trong prompt, trong log, trong
trace. Hai: nó biến một ràng buộc dữ liệu (luôn đúng) thành một lời đề nghị với model (thường
đúng). Fence phải là cơ chế, không phải lời nhờ vả.

---

## 6. Ghi chú wiring cho AIE-1

### 6.1 `[]` là kết quả **hợp lệ**, không phải lỗi

Node `kb-retrieve` nhận `[]` thì **đi tiếp sang `llm-step`**, không raise, không dừng chuỗi. Xem §5.1
để hiểu vì sao đây là hành vi lâu dài chứ không phải vá tạm.

#### 6.1a Kết quả **khác rỗng KHÔNG có nghĩa là có đáp án** *(bổ sung 23/07)*

Hàm này lọc theo **phạm vi**, không lọc theo **mức liên quan**. Nó trả về mọi chunk mà người hỏi
**được phép đọc** và có khớp truy vấn ở mức nào đó — kể cả khi **không chunk nào trả lời được câu
hỏi**. §4 nói đúng chữ đó: kết quả ở bản freeze là *"chunk khớp **scope**"*.

Hai tình huống dưới đây **khác nhau**, đừng gộp:

| tình huống | `kb.search` trả về |
|---|---|
| bị hàng rào chặn (ngoài phạm vi) | `[]` |
| **trong phạm vi nhưng không có đáp án** | **chunk trong phạm vi, không liên quan** — KHÔNG rỗng |

> ⚠️ **Hệ quả — không được suy "agent phải từ chối" từ độ rỗng của kết quả.** Rỗng nghĩa là *không có
> gì trong phạm vi*; **khác rỗng không** nghĩa là *có đáp án*. "Agent có từ chối hay không" là thuộc
> tính của **câu trả lời**, không suy được từ tầng truy xuất.
>
> Ca phản ví dụ có thật trong golden-set — **SC-04** (`golden/smoke-5.yaml`, mầm leak-test T1):
> `tenant=ankor`, `section_roles=[public]`, hỏi hạn mức chi của **Borea**. Hàng rào loại sạch chunk
> Borea (đúng), nhưng vẫn còn **3 chunk `ankor` hợp lệ về phạm vi**, không chunk nào trả lời được.
> Truy xuất **không rỗng**, mà agent **vẫn phải từ chối**.
>
> Ghi ra đây vì §6 là chỗ AIE-1 đọc khi nối `kb-retrieve`, và cách đọc "rỗng ⟺ phải từ chối" là suy
> diễn tự nhiên mà bản v0 (luôn trả `[]`) vô tình khuyến khích.

### 6.2 `citations` tuần này sẽ rỗng theo

Không có chunk ra khỏi `kb.search` → không có `chunk_id` để đưa vào `citations` của trace-event.
**AIE-2 cần biết** để runner skeleton coi `citations: []` là hợp lệ, đừng chấm `citation_accuracy`
rồi tưởng hỏng. Nhãn thật có từ Day 4, khi 5 doc Callisto có nội dung.

### 6.3 **KHÔNG** gọi `KbSearchService` ở D3

```python
KbSearchService(pool).search(...)   # ❌ raise NotImplementedError
```

Nó raise **có chủ đích** — thân hàm là graded deliverable của DE (Day 4+), và
`tests/test_search_contract.py:11-14` là một test **ĐANG XANH** khẳng định đúng điều đó. Ai "sửa cho
chạy được" sẽ làm **đỏ CI**.

Cần thứ chạy được thì dùng double phía engine, nhận qua **dependency injection** để Day 4 đổi sang
bản thật chỉ là đổi chỗ tiêm, không phải sửa node:

```python
async def kb_retrieve(ctx, *, kb: KbSearch): ...
```

Tiền lệ trong kit: double cho CI sống ở tầng composition — `FakeEmbedding` nằm trong
`apps/studio/src/studio_app/providers/fakes.py` (dẫn từ `src/studio_kb/schema.py:21`), không nằm
trong package domain.

---

## 7. Quan hệ với dữ liệu bên dưới

Fence ở §5 chỉ bám được vào hai cột đã có trong `src/studio_kb/schema.py`:

```
kb.chunks( chunk_id, tenant_id NOT NULL, section_role NOT NULL, text, embedding, created_at )
```

Hai cột `NOT NULL` đó **là** fence. Một dòng có `tenant_id` NULL là dòng không thuộc về ai, và mọi
phép lọc đều trượt qua nó. Vì thế ràng buộc `NOT NULL` phải được giữ **từ lúc ghi vào**, không phải
kiểm lúc đọc ra. Chi tiết đường đi từ front-matter tài liệu xuống chunk: `../callisto-doc-schema.md`.

---

## 8. Delta so với code đã có trong repo

| Nơi | Trạng thái hiện tại | v0 nói gì |
|---|---|---|
| `studio_contracts.kb.KbSearch` (Protocol) | 4 tham số, gồm `section_roles` | **khớp hoàn toàn** từ D3 |
| `studio_contracts.kb.KbSearchResultItem` | có `section_role` | v0 chưa điền giá trị thật (chưa có chunk) — **chưa dùng**, không xoá |
| `studio_kb.search.KbSearchService.search` | seam, thân hàm `NotImplementedError` | DE điền từ Day 4 |

**Nói rõ để tránh hiểu nhầm:** v0 nhận `section_roles` **không phải** vì fence đã có. Fence là AC
cứng (leakage = 0) và sẽ land ở S2/S3. v0 nhận tham số chỉ để **chữ ký ổn định**; hành vi vẫn là
"bỏ qua, trả `[]`".

**Không sửa `packages/contracts/**`** — reference do mentor cấp, DE chỉ đọc (GITFLOWS §5).

---

## 9. Câu hỏi còn mở

| # | Hỏi ai | Nội dung | Trạng thái |
|---|---|---|---|
| **Q-A** | mentor | Có nên nhận `section_roles` ngay từ v0 (nhận rồi bỏ qua) để khỏi đổi call-site hai lần? | ✅ **ĐÓNG (D3)** — có. Quyết bằng ràng buộc kỹ thuật (§3), không chờ trả lời: 3 tham số gây `TypeError` tại call-site của AIE-1 và fail mypy. |
| Q-B | mentor | File nháp này là "bút v0", hay phải đề xuất delta lên `contracts` qua PR? | 🔶 còn mở — nghiêng về file nháp trong `packages/kb` |
| Q-C | AIE-2 | citation-accuracy so khớp bằng `chunk_id` — có cần `expected_citation` trong golden-set không? | 🔶 còn mở — có, xem `../format.md` |
| **Q-D** | **AIE-1** | Tự dựng double bên engine, hay muốn DE ship `StubKbSearch` dùng chung trong `packages/kb`? | 🔶 **mới (D3)** — mặc định: AIE-1 tự dựng (đúng `day-03.md:38` + tiền lệ `FakeEmbedding`). Nếu cần bản chung: đặt ở `src/studio_kb/stubs.py`, class riêng, **không đụng** `KbSearchService`. |

---

## 10. Lịch sử

| Bản | Ngày | Đổi gì |
|---|---|---|
| v0 | 2026-07-21 (D2) | Bản nháp đầu — chữ ký **3 tham số** (`query, tenant, top_k`) theo brief tuần 1, ghi sẵn 3 luật fence S2/S3, nêu rõ v0 là tập con của bản freeze |
| v0.1 | 2026-07-22 (D3) | **Chữ ký nâng lên 4 tham số** — nhận `section_roles` (bỏ qua ở v0). Đóng Q-A. Chữ ký v0 từ nay **trùng bản freeze**, chỉ khác hành vi. Gộp ghi chú wiring cho AIE-1 (§6) — trước đó nằm ở file riêng `kb-search-wiring-d03.md`, đã xoá để tránh hai nguồn lệch nhau. Thêm Q-D. |
| v0.1a | 2026-07-22 (D3, cuối ngày) | Thêm **§3.1 bảng đối chiếu brief↔code** — ghi lại đầy đủ chỗ lệch: `day-02.md:36` và `day-04.md:22` đều ghi 3 tham số, còn Protocol + seam đều 4. Không đổi chữ ký; chỉ ghi **vết** để người chấm Day 4 truy được vì sao code khác brief. |
| v0.1b | 2026-07-23 (D4, cuối ngày) | Thêm **§6.1a — "khác rỗng ≠ có đáp án"**. Không đổi chữ ký, không đổi hành vi; chỉ **nói rõ một điều hợp đồng vốn đã đúng nhưng chưa viết ra**: hàm lọc theo *phạm vi*, không theo *mức liên quan*. Sinh ra từ một hiểu lầm có thật ở tích hợp D4 — `llm-step` (AIE-1) suy `refused = not retrieved_chunks`, lập luận rằng "câu bị fence hiện ra thành `[]`". Đúng với ca **bị chặn**, sai với ca **trong phạm vi mà không có đáp án** (SC-04). Bản v0 luôn trả `[]` nên vô tình khuyến khích cách đọc "rỗng ⟺ phải từ chối"; §6.1a chặn nó lại. |
| **v0.2** | 2026-07-24 (D5, #25) | **Chữ ký đổi kiểu — `tenant: str` → `tenant_id: UUID`** theo **D-13** (`SCHEMA_VERSION 0.2.0-draft`). Đây là **breaking change đã chốt ở contracts@main** (không phải đề xuất): danh tính tenant = `core.tenants.id` UUID bất biến, slug chỉ còn là nhãn hiển thị. Bản kb adopt trọn: cột `kb.chunks.tenant_id UUID`, RLS cast `NULLIF(...,'')::uuid`, `_bind_tenant` truyền `str(uuid)`, `doc_factory`/`static_search`/`postgres` khoá theo UUID. Slug giữ nguyên trong `chunk_id` + golden-set `expected_tenant`. Ánh xạ slug→UUID lúc ingest dùng **fixture S1** (`TENANT_IDS` trong `doc_factory`) — đường phân giải thật là **Q-G**, chưa chốt. Kiểm chứng: `pytest packages/kb/tests` 48 passed / 2 xfailed trên Postgres thật; T1/T6 + RLS-framework xanh với role `studio_owner` (không phải superuser). |
