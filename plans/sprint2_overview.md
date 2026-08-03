# Sprint 2 giải thích cho người mới — cả nhóm làm gì, DE (bạn) nằm ở đâu

> **Ngày:** 2026-08-03 (đầu Sprint 2, D11) · **Cho:** DE — Nguyễn Đông Anh
> **Mục đích file này:** đọc xong hiểu được **cả nhóm đang xây cái gì**, **4 người ghép vào nhau ra
> sao**, và **việc của DE nằm chỗ nào** — giải thích như kể chuyện, nhiều ví dụ. Không phải plan
> chạy-việc từng giờ (cái đó là `dayNN_plan.md`).

---

## 0. Một câu: cả nhóm đang xây cái gì?

Nhóm đang xây **một "nhà máy" để tạo ra trợ lý AI cho từng công ty** — và quan trọng hơn: một nhà máy
**có kiểm định**. Nghĩa là không chỉ làm ra trợ lý, mà còn **chứng minh được** nó trả lời đúng, không
làm lộ dữ liệu, và tốn bao nhiêu tiền.

Sprint 1 đã dựng được "đường ray mỏng" chạy thử. **Sprint 2 là làm cho nó THẬT**: dữ liệu thật, bảo mật
thật, chấm điểm thật — và **người khác clone repo về chạy được ngay** mà không cần bạn đứng cạnh giải
thích.

---

## 1. Ví dụ xuyên suốt (nhớ cái này là hiểu hết)

Tưởng tượng có **2 công ty** dùng chung nền tảng của nhóm:

- **Ankor** — sổ tay nội bộ ghi: *"Mức chi công tác tối đa: **20 triệu đồng**."*
- **Borea** — sổ tay nội bộ ghi: *"Mức chi công tác tối đa: **77 triệu đồng**."*

Một nhân viên **của Ankor** hỏi trợ lý:
> *"Mức chi tối đa cho một chuyến công tác là bao nhiêu?"*

Trợ lý **phải**:
1. Trả lời **20 triệu** (số của Ankor).
2. **Trích nguồn**: "theo sổ tay `ankor-expense-001`, đoạn c2".
3. **Tuyệt đối không** để lộ số 77 triệu của Borea — kể cả khi nhân viên cố lừa.
4. Hệ thống **ghi lại** đã chạy những bước gì, tốn bao nhiêu token/tiền.
5. Sau đó **chấm được**: câu này trả lời đúng hay sai.

Cả Sprint 2 xoay quanh việc làm cho 5 điều trên chạy được **thật** và **tự động**.

---

## 2. Bốn vai = bốn phần của nhà máy

| Vai | Người | Ví như… | Làm ra cái gì |
|---|---|---|---|
| **SWE** | Thiệu Quang Minh | **Bàn thiết kế** | Chỗ khách **kéo-thả** vẽ ra trợ lý mình muốn → ra "công thức" (**recipe**). Cả **playground** để bấm "Test". |
| **AIE-1** | Trần Bá Đạt | **Động cơ** | Đọc công thức và **chạy** trợ lý qua từng bước (6 loại bước). Gọi mô hình AI, tính token. |
| **DE (bạn)** | Nguyễn Đông Anh | **Thư viện + Camera an ninh + Đồng hồ điện + Bộ đề thi** | **Kho tài liệu** mỗi công ty một ngăn khoá riêng (**KB**), **camera** ghi mọi bước (**trace**), **đồng hồ** đo chi phí (**cost**), **bộ đề chuẩn** để chấm (**golden-set**). |
| **AIE-2** | Lưu Tiến Duy | **Giám khảo** | **Chấm** trợ lý: trả lời đúng không? trích nguồn đúng không? → **Đạt / Rớt**. |

> **Chốt để nhớ:** SWE làm chỗ *đặt hàng*, AIE-1 làm chỗ *chạy*, **DE làm *dữ liệu + trí nhớ + an ninh
> + thước đo*, AIE-2 làm chỗ *chấm*.** Ba vai kia đều **ăn dữ liệu từ DE**.

---

## 3. DE nằm ở đâu trong bức tranh? → Bạn là "xương sống dữ liệu"

Nhìn lại ví dụ: **mọi con số thật đều đi qua tay DE.**

- Trợ lý lấy "20 triệu" ở đâu? → **Kho KB của DE.**
- Làm sao biết đó là số của Ankor chứ không phải Borea? → **Hàng rào an ninh (fence) của DE.**
- Làm sao biết trợ lý đã chạy đúng các bước, tốn bao nhiêu? → **Camera trace + đồng hồ cost của DE.**
- Lấy gì để chấm "đúng/sai"? → **Bộ đề golden-set của DE.**

Nói cách khác: **AIE-1 (động cơ), SWE (playground), AIE-2 (giám khảo) — cả ba đều không làm việc được
nếu DE chưa cấp dữ liệu.** Đó là lý do trong lịch, DE là **"chủ công" (người chịu trách nhiệm chính)**
của rất nhiều ngày (D13 KB, D15 trace, D19 cost).

Đây cũng đúng thứ Sprint 2 chấm cao nhất: *"ít nhất một thứ bạn xây được người khác dùng mà không cần
bạn giải thích."* Với DE, đó là chuyện đương nhiên — cả nhóm sống nhờ dữ liệu của bạn.

---

## 4. Một câu hỏi chạy qua nhà máy như thế nào (ghép 4 vai)

Theo dõi câu *"Mức chi tối đa?"* của nhân viên Ankor đi hết một vòng:

```
[Nhân viên Ankor gõ câu hỏi]
        │
        ▼
① SWE  — Playground nhận câu hỏi + biết "phiên này là tenant Ankor".
        │   (SWE đã dựng "công thức/recipe" cho trợ lý này từ trước.)
        ▼
② AIE-1 — Động cơ chạy công thức, tới bước "kb-retrieve" (tra kho).
        │   Nó GỌI hàm kb.search("mức chi tối đa", tenant=Ankor, ...)
        ▼
③ DE   — KHO + AN NINH của DE nhận lệnh:
        │   • Chỉ lục trong NGĂN Ankor (fence) → thấy "ankor-expense-001#c2: 20 triệu".
        │   • KHÔNG bao giờ đụng ngăn Borea. Nếu lệch tenant → trả RỖNG, không trả bừa.
        │   → trả về đoạn "20 triệu" + mã trích nguồn "ankor-expense-001#c2".
        ▼
② AIE-1 — Động cơ đưa đoạn đó cho mô hình AI viết câu trả lời tự nhiên.
        │   Mỗi bước chạy xong, nó BÁO cho camera của DE (emit trace).
        ▼
③ DE   — CAMERA (trace) ghi: đã chạy kb-retrieve → llm-step → ... , tốn bao nhiêu token.
        │   ĐỒNG HỒ (cost) tính token → tiền, ghi MỘT con số duy nhất.
        ▼
① SWE  — Playground hiện câu trả lời + hiện timeline + hiện cost (đọc từ camera của DE).
        ▼
④ AIE-2 — GIÁM KHẢO lấy câu trả lời + đối chiếu BỘ ĐỀ của DE:
            đáp án đúng 20 triệu? trích đúng chunk? → chấm ĐẠT/RỚT.
```

Thấy chưa: **DE xuất hiện 3 lần** (kho, camera, đồng hồ) và **cấp bộ đề** cho lần thứ 4. Bạn là mạch
máu chạy suốt.

---

## 5. Hành trình 9 ngày (D12 → D20) — mỗi ngày nhóm ghép thêm gì, DE làm gì

Mỗi ngày có **1 mốc chung của cả nhóm** + việc riêng từng vai. Bảng dưới đọc từ trên xuống là thấy nhà
máy lớn dần.

| Ngày | Mốc CHUNG cả nhóm | **Việc của DE (bạn)** | Ví dụ dễ hiểu |
|---|---|---|---|
| **D11** 03/08 | Đóng băng 4 "hợp đồng" (recipe · trace · kb.search · scorecard) | **Chốt 2 hợp đồng** trace-event + kb.search (đã làm) | Ký "luật giao tiếp" giữa 4 người: sau hôm nay đổi phải xin 4 chữ ký |
| **D12** 04/08 | Bàn thiết kế (canvas) 6-node + bộ kiểm công thức | **Doc-factory**: sinh ~40–60 tài liệu Callisto cho **2 công ty** Ankor/Borea + khung gắn nhãn | Viết ra 2 quyển sổ tay đầy đủ (không còn 5 trang stub như S1) |
| **D13** 05/08 | **KB thật** ingest→embed→index + tra được (ghép DE×AIE-1) | ⭐**Chủ công**: dựng dây chuyền **nhập → cắt đoạn → mã hoá → xếp kho** theo từng công ty; `kb.search` trả đoạn có **trích nguồn** | Biến quyển sổ tay thành kho tra cứu được: hỏi là ra đúng đoạn + số trang |
| **D14** 06/08 | Động cơ đủ **6 loại bước** + đo trade-off cắt đoạn×mã hoá | Cấp **câu hỏi mẫu + đáp án chuẩn (đoạn nào đúng)** để AIE-1 đo độ chính xác; bật 2 kiểu mã hoá | Ra "đề mẫu": hỏi X thì đáp án nằm ở đoạn Y — để đo động cơ tìm có trúng không |
| **D15** 07/08 | **Trace viewer** + lọc tenant lúc tra · Integration Friday | ⭐**Chủ công**: dựng **màn hình xem lại timeline** (từng bước, token, tiền, trích nguồn) + bắt đầu **lọc theo công ty** | Làm cái "màn hình camera": xem lại trợ lý đã đi những bước nào, tốn gì |
| **D16** 10/08 | Bộ chấm v1 + **30 đề có nhãn** + bảng điểm | Cấp **golden-set 30 câu có đáp án chuẩn** — **1 script ra 2 sản phẩm** (KB + bộ đề) từ cùng nguồn | Ra bộ 30 câu hỏi kèm đáp án + đoạn-trích-đúng, phủ cả ca khó |
| **D17** 11/08 | **Hàng rào an ninh** fail-closed + test T1/T6 xanh | ⭐**Áp fence bắt buộc** lúc tra (chunk phải có tenant/role, sai → rỗng) + viết **test chống khai gian nhãn (T6)** | Khoá kho: nhân viên Ankor có tự khai "tôi là Borea" cũng **không** đọc được số 77 triệu |
| **D18** 12/08 | LLM-judge sơ khởi + đối chiếu với nhãn tay | Cấp **nhãn chấm tay** cho một phần bộ đề để đo "máy chấm có khớp người chấm không" | Bạn tự chấm tay 1 số câu → so với máy chấm → xem máy đáng tin cỡ nào |
| **D19** 13/08 | **Cost-lineage cùng-1-số** + gia cố + liệt kê điểm yếu | ⭐**Chủ công cost**: token→tiền tính **một chỗ duy nhất** trong trace; UI đọc **đúng con số đó** | Đồng hồ điện: mọi màn hình đều hiện **cùng một** số tiền, không ai tự nhân lại |
| **D20** 14/08 | **GATE-2**: cả 4 mảng ghép thật lần đầu + plan-vs-actual | **Demo trọn**: KB thật + tra có trích nguồn + fence T1/T6 xanh + trace viewer + cost cùng-1-số + 30 đề | Chạy nguyên vòng ví dụ mục 1 **từ bản clone sạch**, không sửa sống |

(⭐ = ngày DE là người chịu trách nhiệm chính)

**Ba vai kia trong 9 ngày đó (tóm tắt):**
- **SWE**: D12 dựng canvas kéo-thả → D15 nút "Test" trong playground → D17 xử lý danh tính phiên
  (tenant/user/roles) → D19 hiện cost → D20 hoàn thiện canvas + kiểm công thức.
- **AIE-1**: D12 tách động cơ đọc-công-thức → D13 cắm bước tra-kho thật → D14 làm đủ **6 loại bước** +
  đo trade-off → D19 phát token chuẩn (nguồn của cost) → D20 chạy DAG thật.
- **AIE-2**: D13 nhận đề nháp từ DE → D14 đọc kết quả từ trace → D16 làm **bộ chấm v1** → D18 làm
  **máy chấm bằng LLM** + đối chiếu nhãn tay của DE → D20 ra bảng điểm ĐẠT/RỚT.

---

## 6. Từ điển khái niệm — giải thích cho học sinh cấp 3

**KB (Knowledge Base — kho tri thức):** kho tài liệu để trợ lý tra cứu. Giống thư viện của một công ty.

**ingest → chunk → embed → index** (dây chuyền đưa sổ tay vào kho):
- **ingest** = *nhập* tài liệu vào (bê quyển sổ vào thư viện).
- **chunk** = *cắt thành đoạn nhỏ* (xé sổ thành từng mẩu ~1 đoạn, để tra cho trúng chỗ thay vì trả cả quyển).
- **embed** = *mã hoá mỗi đoạn thành một dãy số* (gọi là "vector") thể hiện *ý nghĩa*. Hai đoạn nói
  cùng ý → hai dãy số gần nhau. Nhờ vậy máy tìm theo **nghĩa**, không phải tìm đúng từ.
  - *Ví dụ:* "mức chi tối đa" và "giới hạn chi tiêu công tác" khác từ nhưng gần nghĩa → vector gần nhau.
- **index** = *xếp vào kho có đánh dấu* để tra nhanh, **mỗi công ty một ngăn** (per-tenant).

**per-tenant (theo từng khách/công ty):** "tenant" = một khách thuê chung nền tảng (Ankor, Borea). Dữ
liệu mỗi tenant **để riêng, khoá riêng**. Giống chung cư: chung toà nhà nhưng mỗi nhà một chìa khoá.

**fence (hàng rào) + fail-closed (hỏng thì đóng):** luật loại bỏ dữ liệu sai công ty **NGAY LÚC TRA**,
trước khi đưa cho AI. "fail-closed" = nếu có gì mập mờ/lỗi thì **trả rỗng** (an toàn), chứ không trả bừa.
- *Vì sao loại TRƯỚC:* một khi đoạn "77 triệu của Borea" đã lọt vào đầu AI, nó có thể lỡ miệng nói ra
  qua câu trả lời hoặc trích dẫn. Nên phải **chặn ở cổng kho**, đừng để vào tới AI.

**label-spoof / T6 (khai gian nhãn):** kẻ xấu tự khai "tôi có quyền của Borea" để đọc trộm. Test T6
chứng minh: **server tự quyết quyền**, client khai gì kệ nó. *Ví dụ:* nhân viên Ankor sửa yêu cầu
thành `roles=[borea-finance]` → hệ thống **vẫn** chỉ trả dữ liệu Ankor. **T1 (IDOR)** = thử đọc thẳng
ID tài liệu của công ty khác → cũng bị chặn.

**trace (dấu vết) + trace viewer (màn hình xem lại):** mỗi bước trợ lý chạy đẻ ra **một dòng nhật ký**
(chạy bước gì, lúc nào, tốn bao token, trích đoạn nào). Trace viewer là màn hình xếp các dòng đó thành
**timeline** đọc lại được. Giống lịch sử xem của Youtube, nhưng cho từng lần chạy trợ lý.

**cost-lineage "một nguồn duy nhất":** chi phí (tiền) = số token × đơn giá. Luật: **chỉ tính ở MỘT
chỗ** (lúc ghi trace), mọi màn hình khác **đọc lại** con số đó, cấm tự nhân lại.
- *Vì sao:* nếu 3 màn hình mỗi cái tự tính, hôm nào đổi đơn giá mà quên một chỗ → 3 số khác nhau, không
  ai biết số nào đúng. Một nguồn thì đổi một lần, cả hệ đúng theo.

**golden-set (bộ đề chuẩn) + expected-citations (đoạn-trích-kỳ-vọng):** bộ câu hỏi mẫu **kèm đáp án
đúng** VÀ **đoạn tài liệu phải trích**. Dùng để chấm trợ lý.
- *Ví dụ 1 case:* hỏi "mức chi tối đa của Ankor?" → đáp án chuẩn "20 triệu" → phải trích
  `ankor-expense-001#c2`. Trợ lý trả 20 triệu **nhưng** trích nhầm sổ Borea = vẫn tính sai.

**recall / precision (độ bao phủ / độ chính xác):** hai cách đo "tìm có giỏi không".
- **recall** = trong các đoạn *đáng ra phải tìm được*, tìm được bao nhiêu %? (sót nhiều = recall thấp)
- **precision** = trong các đoạn *đã trả về*, bao nhiêu % thực sự đúng? (trả rác nhiều = precision thấp)
- *Ví dụ:* đáp án nằm ở 2 đoạn, trợ lý trả 4 đoạn trong đó 2 đoạn đúng → recall 2/2 = 100%,
  precision 2/4 = 50%.

**LLM-judge (dùng AI làm giám khảo) + agreement (mức khớp):** cho một AI chấm bài thay người (nhanh,
rẻ). Nhưng phải kiểm AI-chấm có **khớp** người-chấm không → đó là lúc cần **nhãn tay của DE** (D18) để
so. Khớp cao thì mới tin máy chấm.

**deterministic / fixtures (chạy lại ra y hệt / dữ liệu ghi sẵn):** máy chấm và test phải **chạy 10 lần
ra 10 kết quả giống nhau**. Muốn vậy, thay vì gọi mô hình AI thật (mỗi lần một khác + tốn tiền), ta
dùng **kết quả ghi sẵn** (fixture). Giống dùng đề + đáp án in sẵn thay vì mỗi lần hỏi một giám khảo khác.

---

## 7. DE cho ai dùng, phụ thuộc ai (bản đồ đơn giản)

**DE CẤP cho (người khác ăn dữ liệu của bạn):**
- → **AIE-1**: kho KB + `kb.search` để động cơ tra được; hợp đồng trace để biết cách ghi nhật ký.
- → **AIE-2**: golden-set (bộ đề) + nhãn tay + trace (để đọc kết quả mà chấm).
- → **SWE**: trace viewer + cost để playground hiện lên.

**DE PHỤ THUỘC vào:**
- ← **AIE-1**: phải phát **token** đúng thì đồng hồ cost của bạn mới có số để tính.
- ← **SWE**: "công thức" (recipe) phải chỉ đúng ngăn kho (tenant/section) thì tra mới trúng.
- ← **AIE-2**: cho biết bộ chấm cần đọc thêm trường gì từ trace.

> Đây chính là lý do 4 hợp đồng phải **đóng băng ở D11**: một khi ai cũng xây dựa vào dữ liệu của
> nhau, đổi định dạng giữa chừng là **gãy cả 4 người** cùng lúc.

---

## 8. "Xong" ở Gate 2 (D20) trông như thế nào

Chạy lại **đúng ví dụ mục 1**, từ một **bản clone sạch**, không sửa sống:

1. Nhân viên Ankor hỏi → trợ lý trả **20 triệu** + trích **`ankor-expense-001#c2`**. ✅
2. Cùng câu đó, nếu là nhân viên Borea → trả **77 triệu** (ngăn khác). ✅
3. Nhân viên Ankor **cố khai gian** thành Borea → **vẫn chỉ ra 20 triệu / hoặc bị từ chối** (T6). ✅
4. Mở trace viewer → thấy đủ timeline các bước + **cùng một** con số cost. ✅
5. Chạy bộ chấm 30 đề → ra bảng điểm ĐẠT/RỚT. ✅

Và nhớ 3 điều Sprint 2 chấm (xem memory `sprint-2-grading-rubric`):
- **Chạy được từ clone sạch mới tính là đã giao** — lệnh bật Docker + DSN phải nằm trong repo.
- **Người khác dùng được thứ bạn xây** — với DE là mặc định, nhưng phải để họ dùng mà **không cần bạn
  giải thích**.
- **Tự-chấm khớp mentor** — nộp trước 24h (≈13/08).

---

### Ghi chú nguồn
Tổng hợp từ issue GitHub `AI20K-VGR` Sprint 2: DE #85·#90·#95·#100·#105·#110·#115·#120·#125;
AIE-1 #86·#91·#96·#101·#106·#111·#116·#121·#126; SWE #87·#92·#97·#102·#107·#112·#117·#122·#127;
AIE-2 #88·#93·#98·#103·#108·#113·#118·#123·#128; mốc cả nhóm #89·#94·#99·#104·#109·#114·#119·#124·#129.
Ví dụ số (20tr/77tr · ankor/borea · `ankor-expense-001#c2` · section_role finance) lấy từ dữ liệu test
thật trong `packages/kb/tests`.
