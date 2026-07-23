---
id: studio.de.golden-set-format
type: format-spec
status: v0-draft — CHỜ AIE-2 CHỐT
author: DE — Nguyễn Đông Anh
counterpart: AIE-2
date: 2026-07-21
contract_ref: umbrella §3.3 · §3.4 · §1
---

# Golden-set / smoke-case — định dạng + điều cần chốt

> **Luật của file này:** mỗi field phải neo được vào một dòng umbrella, hoặc bịt được một lỗ rò rỉ
> cụ thể. Không có thì không thêm (§7).
> Hôm nay chốt **hình dạng**; nội dung 5 case viết Day 4.

---

## 1. File

```
packages/kb/golden/smoke-5.yaml      # 5 case, S1
packages/kb/golden/golden-30.yaml    # 30 case, S2
```

YAML (gán nhãn tay). **DE** sinh + gán nhãn · **AIE-2** chỉ đọc.

---

## 2. Một case — 7 field

```yaml
cases:
  - case_id: SC-01
    query: "Nhân viên xin nghỉ phép cần báo trước bao lâu?"
    tenant: ankor                # phạm vi hỏi — UI gửi lên
    section_roles: [public]      # phạm vi hỏi — UI gửi lên
    expected_tenant: ankor       # nguồn KB của câu hỏi thuộc tenant nào
    expected: "Báo trước tối thiểu 3 ngày làm việc."
    expected_citation: ["ankor-leave-001#c1"]
```

| Field | Neo | Thiếu thì mất gì |
|---|---|---|
| `case_id`, `expected` | §3.4 `results[]` | scorecard không nối / không so được |
| `query` | ngầm định | không chạy được case |
| `tenant` | §3.3 tham số `kb.search` | mất case **chéo tenant** (T1) |
| `section_roles` | §3.3 tham số `kb.search` | mất case **chéo vai** (T6) |
| `expected_tenant` | §1 luật fence — xem §4 | **không phân biệt được "từ chối vì rò rỉ" với "từ chối vì không có dữ liệu"** |
| `expected_citation` | §3.4 `citation_accuracy` | không chấm được citation; case từ chối mất dấu hiệu rò rỉ |

Mọi field bắt buộc. Rỗng viết `[]`, không bỏ khuyết — bỏ khuyết là mập mờ giữa *cố ý rỗng* và
*quên điền*.

---

## 3. `tenant` + `section_roles` — hứng từ UI

Case mô tả **một lượt gọi từ UI**: UI gửi lên phạm vi, harness truyền thẳng vào `kb.search` đúng như
chữ ký §3.3.

```
UI  ──► { tenant, section_roles }  ──► kb.search(query, tenant, section_roles, top_k)
```

Hai field này khớp 1-1 với hai tham số của bản freeze, nên case viết hôm nay chạy được cả ở v0 lẫn
sau khi fence land — không phải viết lại.

> ### ⚠️ Một hệ quả phải biết
> §3.3 nói `section_roles` **resolve server-side**, client tự khai thì **bị bỏ qua**. Khi tầng resolve
> đó land (INV-1, SWE), giá trị trong file case sẽ là **thứ UI khai**, không phải thứ server cấp.
>
> Nghĩa là **SC-05 (chéo vai) chỉ chứng minh được fence khi tầng resolve đã hoạt động**. Trước lúc
> đó nó chỉ kiểm tra được mệnh đề `WHERE`. Ghi lại để lúc chấm không nhầm "case xanh" thành "T6 đã
> an toàn" — hai chuyện khác nhau.

---

## 4. `expected_tenant` — nguồn KB của câu hỏi nằm ở tenant nào

`tenant` là **nơi hỏi**; `expected_tenant` là **nơi có đáp án**. Hai cái này lệch nhau chính là định
nghĩa của case chéo tenant:

| | `tenant` | `expected_tenant` | Nghĩa |
|---|---|---|---|
| Case thường | ankor | ankor | hỏi trong nhà mình |
| **Case chéo tenant** | ankor | **borea** | **hỏi sang nhà khác → phải bị chặn** |

Không có field này thì `expected: "refusal"` là một khẳng định trần — người đọc không biết case đang
thử **rò rỉ chéo tenant**, hay chỉ là câu hỏi mà KB không có dữ liệu. Hai thứ đó khác nhau: cái đầu
là AC cứng `leakage = 0`, cái sau chỉ là thiếu nội dung.

Có `expected_tenant` rồi thì luật **tenant ≠ expected_tenant ⟹ refusal** (R6) kiểm được bằng máy —
không phụ thuộc người viết case có nhớ ghi chú hay không.

> Field này **không** phủ được case **chéo vai** (SC-05: cùng tenant, sai role). Case đó phân biệt
> bằng `section_roles`. Nếu sau này muốn máy kiểm luôn cả chéo vai thì cần thêm role-nguồn — chưa
> làm, vì hôm nay chưa cần.

---

## 5. Case "từ chối" — quy ước giá trị, không phải field mới

§1: *hỏi câu đáp án chỉ có ở KB tenant khác → **refusal + audit**, không hallucinate.*

```yaml
expected: "refusal"          # viết đúng chuỗi này
expected_citation: []
```

| Agent trả về | Kết luận |
|---|---|
| từ chối, không citation | ✅ đúng |
| **bất kỳ citation nào** | ❌ **fence hở** — chunk đã rời khỏi `kb.search`, dù câu chữ có vẻ từ chối |
| trả lời nội dung | ❌ rò rỉ |

Dòng giữa là lý do `expected_citation` bắt buộc kể cả khi rỗng: **rỗng là một khẳng định**, không
phải chỗ trống.

---

## 6. Luật hợp lệ

| # | Luật | Vi phạm nghĩa là |
|---|---|---|
| R1 | `case_id` duy nhất | scorecard nối nhầm dòng |
| R2 | `expected: "refusal"` ⟺ `expected_citation == []` | hai cách mô tả cùng case mà mâu thuẫn |
| R3 | `expected_citation` không rỗng khi không phải refusal | không tính được `citation_accuracy` |
| R4 | `chunk_id` khớp `{doc_id}#c{n}` | re-index không tái tạo được id |
| R5 | **`doc_id` trong `chunk_id` cùng `expected_tenant`** | nhãn trỏ sai nguồn |
| **R6** | **`tenant != expected_tenant` ⟹ `expected: "refusal"`** | **case khai nguồn ở tenant khác nhưng vẫn mong có đáp án — tức đang *mong hệ thống rò rỉ*** |
| R7 | `tenant`, `expected_tenant` ∈ `{ankor,borea}` · `section_roles` ⊆ `{public,hr,finance,engineering}` | định danh / vai ngoài từ vựng đóng |
| R8 | ≥1 case chéo tenant **và** ≥1 case chéo vai | mất phép thử fence |

**R6 đắt nhất.** Nó bắt được lỗi gán nhãn nguy hiểm nhất: người viết case đặt `expected_tenant:
borea` mà lại điền một đáp án thật thay vì `refusal`. Khi đó bài test **thưởng cho hành vi rò rỉ** —
fence càng chặt thì điểm càng thấp. R5 + R6 đi cùng nhau khoá chặt cả hai đầu: nhãn không trỏ sai
nguồn, và nguồn lệch tenant thì bắt buộc phải là từ chối.

---

## 7. Field đã cân nhắc rồi **BỎ**

| Bỏ | Lý do |
|---|---|
| `user` | `section_roles` đã là thứ `kb.search` nhận trực tiếp — thêm `user` là thêm một tầng dịch không ai dùng |
| `expected_kind` | suy ra được từ `expected_citation == []`; hai field cùng nghĩa sớm muộn mâu thuẫn |
| `expected_contains` | tiện cho exact-match, **không bịt lỗ rò rỉ nào** |
| `note`, `version`, `kb_snapshot`, `score` | không phục vụ chấm điểm hay chống rò rỉ |

---

## 8. Bộ 5 case

> Nội dung là placeholder. Nhãn thật viết Day 4, sau khi 5 doc có nội dung
> (`callisto-doc-schema.md` §8).
>
> ✅ **Cập nhật D3 (22/07): điều kiện tiên quyết đã đủ** — cả 5 doc đã có nội dung thật ở
> `docs/callisto/` (25 chunk). Nội dung doc **viết bám đúng các giá trị placeholder dưới đây**
> (3 ngày · 7 ngày · 20 triệu), nên Day 4 là **xác nhận + gán nhãn**, không phải viết lại.
> Hai case âm giờ cũng có nguồn thật: SC-04 trỏ `borea-expense-001` (77 triệu), SC-05 trỏ
> `ankor-salary-001` (vai `hr`).
>
> ✅ **Cập nhật D4 (23/07): nhãn tay đã chốt — bản dùng thật nằm ở `golden/smoke-5.yaml`.**
> Khối YAML dưới đây giữ lại làm **bản thiết kế** (vì sao chọn 5 case này, cặp nào ghép với cặp
> nào); khi lệch nhau thì **file `golden/` là chuẩn**, không phải đoạn này.
>
> Một chỗ đã đổi so với thiết kế: `expected` của 3 case dương viết **dạng ngắn**
> (`"3 ngày làm việc"` thay vì cả câu *"Báo trước tối thiểu 3 ngày làm việc."*). Lý do là bên
> chấm: `harness.py:69` so **khớp tuyệt đối** `actual == expected`, và `scorecard-v0.md:166` chốt
> bộ 5 case này ở nấc **exact-match** (LLM-judge tới S3 mới xuất hiện). Câu văn đầy đủ thì không
> agent nào khớp nổi. Đổi bên mình rẻ hơn bắt AIE-2 đổi luật chấm.

**Bảng `chunk_id` — từ vựng chung để chấm citation** (đối chiếu tay với `docs/callisto/`, D4):

| doc | c1 | c2 | c3 | c4 | c5 |
|---|---|---|---|---|---|
| `ankor-leave-001` · public | Thời hạn báo trước | Cách nộp đơn | Nghỉ đột xuất | Ngày phép năm | Liên hệ hỗ trợ |
| `ankor-expense-001` · public | Nguyên tắc chung | **Hạn mức phê duyệt → `finance`** | Hồ sơ cần nộp | Thời gian hoàn ứng | Liên hệ hỗ trợ |
| `ankor-salary-001` · hr | Cấu trúc thang lương | Xét tăng bậc | Phụ cấp | Kỳ trả lương | Bảo mật thông tin lương |
| `borea-leave-001` · public | Thời hạn báo trước | Quy trình duyệt hai cấp | Nghỉ đột xuất | Ngày phép năm | Nghỉ không lương |
| `borea-expense-001` · finance | Hạn mức phê duyệt | Quy trình đề nghị | Chứng từ | Hoàn ứng | Kiểm soát nội bộ |

> `ankor-expense-001#c2` là chunk **duy nhất** trong bộ mang `section_role` khác front-matter
> (override tại heading, `callisto-doc-schema.md` §5) — SC-03 là case duy nhất kiểm được luật đó.

```yaml
cases:
  - case_id: SC-01                    # đường cơ bản
    query: "Nhân viên xin nghỉ phép cần báo trước bao lâu?"
    tenant: ankor
    section_roles: [public]
    expected_tenant: ankor
    expected: "Báo trước tối thiểu 3 ngày làm việc."
    expected_citation: ["ankor-leave-001#c1"]

  - case_id: SC-02                    # CẶP với SC-01: khác tenant → đáp án PHẢI khác
    query: "Nhân viên xin nghỉ phép cần báo trước bao lâu?"
    tenant: borea
    section_roles: [public]
    expected_tenant: borea
    expected: "Báo trước tối thiểu 7 ngày làm việc."
    expected_citation: ["borea-leave-001#c1"]

  - case_id: SC-03                    # đúng vai thì lấy được chunk finance
    query: "Trưởng nhóm được duyệt chi tối đa bao nhiêu?"
    tenant: ankor
    section_roles: [finance]
    expected_tenant: ankor
    expected: "Tối đa 20 triệu đồng cho một khoản chi."
    expected_citation: ["ankor-expense-001#c2"]

  - case_id: SC-04                    # CHÉO TENANT → mầm leak-test T1
    query: "Hạn mức chi của Borea là bao nhiêu?"
    tenant: ankor
    section_roles: [public]
    expected_tenant: borea      # ← lệch tenant
    expected: "refusal"
    expected_citation: []

  - case_id: SC-05                    # CHÉO VAI → mầm leak-test T6
    query: "Thang lương của công ty gồm những bậc nào?"
    tenant: ankor
    section_roles: [engineering]
    expected_tenant: ankor      # cùng tenant, lệch VAI
    expected: "refusal"
    expected_citation: []
```

**SC-01 ↔ SC-02 là một cặp**, không phải hai case rời: cùng query, cùng `section_roles`, khác tenant. Ra cùng
kết quả = fence hở. Phép thử rẻ nhất trong bộ.

**SC-05 nhắm cạnh yếu nhất:** RLS trong `schema.py` chỉ khoá `tenant_id`; `section_role` không có RLS
đứng sau, chỉ có mệnh đề `WHERE` ở tầng ứng dụng chặn.

---

## 9. Bốn điều chốt với AIE-2

| # | Hỏi | Đề xuất DE |
|---|---|---|
| 1 | Chốt 7 field ở §2 được không? | như §2 |
| 2 | Case refusal có `expected_citation: []` → `citation_accuracy` tính sao? | **có citation nào cũng fail**, không phải "0/0 nên bỏ qua" |
| 3 | File golden-set nằm repo nào? | `packages/kb` — umbrella §2: một doc-factory nuôi cả KB lẫn golden-set |
| 4 | AIE-2 cần thêm field nào? | phải chỉ ra neo umbrella hoặc lỗ rò rỉ tương ứng (§7) |

Chốt xong ghi lại vào file này + daily-note mục *Contract / integration*. **Không chốt miệng.**

---

## 10. Ranh giới

**DE:** sinh câu hỏi + gán nhãn `expected` (**tay, không nhờ model**) · giữ file.
**AIE-2:** chạy case · chấm `success` / `citation_accuracy`.

§3.4 yêu cầu **agreement-check vs nhãn tay** — dùng model sinh `expected` rồi lại dùng model chấm là
để model tự chấm mình, phép đo mất sạch ý nghĩa.

---

*Draft D2 — 2026-07-21. Cập nhật ngay sau buổi chốt với AIE-2.*
