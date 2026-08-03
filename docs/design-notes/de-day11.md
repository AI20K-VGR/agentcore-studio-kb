---
id: studio.design-note.de.day-11
type: design-note
role: DE — Nguyễn Đông Anh
day: 11
date: 2026-08-03
status: draft (chờ mentor duyệt — DoD #80 ô 2)
scope: doc-factory · chunk/embed/index per-tenant · fence-tại-retrieval
length_target: ≤2 trang
---

# Design-note DE (D11) — KB per-tenant: doc-factory → chunk/embed/index → fence-tại-retrieval

> Neo: issue **#80** (*"Design-note: doc-factory + chunk/embed/index per-tenant + fence-tại-retrieval"*).
> Không tóm tắt contract — đây là **thiết kế + đánh đổi**. Hai contract DE khoá hôm nay
> ([`trace-event`](../contracts/trace-event.v0.md), [`kb.search`](../contracts/kb-search.v0.md)) là
> *hình dạng dây*; note này là *vì sao pipeline dưới dây có hình đó*.

## 1. Bài toán một câu

KB phải trả `kb.search(query, tenant_id, section_roles, top_k)` ra **chỉ những chunk thuộc đúng
tenant + đúng section_role của phiên** — và phải **đúng-do-kiến-trúc**, không đúng-do-nhắc-khéo. Ba
tầng dưới quyết định điều đó: **doc-factory** (nguồn), **chunk/embed/index per-tenant** (lưu trữ),
**fence-tại-retrieval** (cổng ra).

## 2. Doc-factory — nguồn KB có nhãn tenant/section từ gốc

- **Đầu vào có nhãn, không đoán về sau.** Mỗi doc Callisto mang frontmatter `tenant` + `section_role`
  ngay ở nguồn (tiền lệ D4: stub 5 doc, đã chạy). Nhãn đi cùng nội dung từ lúc sinh → **không có bước
  "suy ra tenant từ text"** ở downstream (bước đó là chỗ rò kinh điển).
- **Slug là nhãn hiển thị, UUID là danh tính** (D-13). Doc-factory ánh xạ slug→UUID lúc ingest; đường
  phân giải slug→UUID **thật** là của producer/middleware qua `core.tenants` (Q-G, ngoài lằn kb). KB
  khoá mọi thứ theo **UUID**; slug chỉ còn trong `chunk_id` (`ankor-expense-001#c2`) + golden-set
  `expected_tenant` để người đọc truy được.
- **Hướng S2:** từ 5 doc stub → ~40–60 doc, 2 tenant (D12, #85). Doc-factory phải **là một script tái
  lập** (cùng seed → cùng KB) để golden-set + eval deterministic — không phải bộ file chép tay.

## 3. Chunk / embed / index **per-tenant** — vì sao tách ở tầng lưu trữ

Đánh đổi trung tâm: **fence ở đâu — lúc lưu (index tách theo tenant) hay lúc đọc (một index chung, lọc
sau)?**

| | Index tách theo tenant | Một index chung, lọc sau ranking |
|---|---|---|
| Rò dữ liệu | Chunk sai tenant **không có trong không gian tìm** | Chunk sai tenant **vào top-k rồi mới loại** — đã tính điểm, đã ở RAM |
| Chi phí lỗi | Bug filter = **rỗng** (fail-closed) | Bug filter = **rò** (fail-open) |
| Chi phí vận hành | Nhiều index nhỏ hơn | Một index to |

**Chọn: khoá tenant ở tầng lưu trữ** (`kb.chunks.tenant_id UUID NOT NULL` + RLS theo `app.tenant_id`).
Lý do không phải hiệu năng mà là **hướng-hỏng**: nếu tầng dưới đã cắt theo tenant thì một lỗi ở tầng
truy vấn cho ra *ít* kết quả (an toàn), không phải *nhiều* (rò). `section_role` là cột NOT NULL cùng
hàng, lọc cùng lượt — không phải hậu-xử-lý.

- **Chunk:** cắt theo cấu trúc doc (giữ `section_role` nguyên khối, không cắt ngang quyền).
- **Embed:** qua `EmbeddingService` Protocol (`embed(texts)->[vector]`, seam AIE-1) — kb **không** tự
  khai model; fixture recorded-vector cho CI deterministic (tiền lệ D7).
- **Index:** khoá `(tenant_id, section_role)` là first-class, không phải metadata lọc-sau.

## 4. Fence-tại-retrieval là LUẬT — không phải cấu hình

- **"Đừng tiết lộ" là chỉ dẫn mềm; dữ liệu sai scope vào context là rò cứng.** Một khi chunk sai
  tenant/vai đã nằm trong context của agent, nó rò qua **suy luận, citation, hoặc tool-output** — và
  prompt-injection thì bỏ qua mọi chỉ dẫn mềm. Nên phải **loại TRƯỚC khi đưa cho agent**.
- **Loại trước ranking, không lọc sau.** Ranking trên tập đã-sai-scope là vừa tốn vừa nguy: điểm số
  của chunk cấm không có ý nghĩa, và mọi bước sau ranking là một cơ hội quên lọc.
- **`section_roles` client gửi là *yêu cầu*, không phải *quyền*** (kb.search §5.2). Server phân giải
  quyền thật; khai thêm một role ở client **không** mở thêm dữ liệu — nếu không, chỉ cần sửa payload là
  đọc được phần không thuộc về mình, chẳng cần lỗ hổng.
- **Fail-closed:** scope rỗng/không phân giải được → trả `[]`, **không** trả "cho an toàn". `[]` là kết
  quả hợp lệ (kb.search §6.1), không phải lỗi.

## 5. Một phương án đã BỎ — "trả rộng rồi nhờ LLM lọc"

**Phương án:** để `kb.search` trả top-k rộng (mọi tenant), kèm chỉ dẫn "chỉ dùng chunk của tenant X"
cho LLM. **Bỏ vì:** (1) đặt biên giới bảo mật vào một chỉ dẫn ngôn ngữ tự nhiên — thứ mềm nhất trong
hệ; (2) dữ liệu sai tenant **đã** ở trong context, rò qua citation/tool kể cả khi LLM "nghe lời"; (3)
prompt-injection vô hiệu hoá nó bằng một câu. Đây chính là luật kb.search §5.3 (*cấm trả hết nhờ LLM
lọc*). Phương án loại-tại-retrieval đắt hơn lúc viết (khoá tenant ở index), rẻ hơn cả đời (một chỗ
fence, fail-closed).

## 6. Điểm S2 đã biết (nêu trước, không giấu)

- **Fence mới ở tầng retrieval của KB stub.** S2 thêm đường lấy dữ liệu (KB thật, nhiều nguồn) → mỗi
  đường một chỗ fence phải lặp; cần một điểm chặn dùng chung, không rải rác.
- **INV-1 mới chặn `tenant`, chưa chặn `roles`.** `session_context.roles` chưa được đọc để lọc ở đâu
  (việc AIE-1/SWE) — hiện `section_roles` "nhận rồi bỏ qua" đúng như v0.
- **`obs.costs`** là bảng ở `apps/studio`, **ngoài fence-lane DE** — DE điền ở D19 (cost-lineage),
  coordinate leader (Q-D trace-event; DL-11.7). **`obs.golden_sets`** thì **nghi bảng chết trùng lặp**
  (golden-set thật = `eval.golden_sets`) → đề xuất DROP, xác nhận mentor (DL-11.9 · mini-RFC schema-drift).
  Chi tiết chuẩn tenant + RLS từng bảng: `docs/mini-rfc-tenant-schema-unify.md`.
