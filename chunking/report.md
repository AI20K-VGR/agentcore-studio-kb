# Báo cáo A/B/C: chunk 200/50 vs 500/100 vs 850/170

Ngày: 2026-08-24 · Phạm vi: `packages/kb/src/studio_kb/chunk_window.py` (cutter cửa sổ trượt cho nội
dung tự do — upload qua `POST /api/admin/documents`). Toàn bộ số liệu dưới đây đo bằng **embedding
thật** (`gemini-embedding-001@2048` qua `GatewayEmbedding`, real OpenRouter call) trên **corpus
thật** (toàn bộ 9 file `.md`/`.txt`/`.docx` trong `packages/kb/data/`, trích xuất bằng đúng
`extract_text()` production dùng) và **bộ 100 câu hỏi ground-truth do LLM thật sinh** (`o4-mini`,
real OpenAI API) — không dùng embedding giả/stub, không dùng dữ liệu bịa, không hardcode đáp án tay.

> ## ✅ QUYẾT ĐỊNH (2026-08-24): chốt **850/170**, đã đổi code
>
> `WORDS_PER_CHUNK`/`WORDS_OVERLAP` trong `chunk_window.py` đã đổi từ 500/100 → **850/170** (quay lại
> giá trị gốc trước khi thử hạ xuống 500, theo đúng số liệu đo được ở report này — không phải giữ
> nguyên mặc định cũ mà không xét lại). Lý do, tóm tắt (chi tiết đầy đủ ở §7-§8):
> 1. **Xếp hạng nhất quán trên benchmark 100 câu** (§2): 850/170 thắng Hit@1/3/5/MRR so với cả
>    500/100 lẫn 200/50, dù không có ý nghĩa thống kê riêng lẻ.
> 2. **Bằng chứng dứt khoát từ stress test ngữ cảnh dài** (§7): khi câu trả lời cần nhiều hơn 1 câu
>    (mô phỏng bằng snippet 150 từ), 850/170 **không suy giảm gì** (Hit@1 không đổi), còn 500/100 và
>    đặc biệt 200/50 suy giảm rõ rệt — đây là bằng chứng đo được, không phải suy luận lý thuyết.
> 3. **200/50 bị loại hẳn** ở cả 2 phép đo — xác nhận "cắt càng hẹp càng chính xác" là trực giác sai,
>    không phải quy luật.
> 4. Giả thuyết ngược lại ("850 rủi ro pha loãng đáp án ngắn") **chưa bị bác bỏ hoàn toàn nhưng
>    không có số đo nào ủng hộ nó**, trong khi rủi ro ngược lại (xé lẻ ngữ cảnh dài ở cửa sổ hẹp) có
>    số đo rõ ràng — quyết định dựa trên bằng chứng đã có, không chờ đo hết mọi rủi ro lý thuyết còn
>    lại (xem §9 giới hạn cho các câu hỏi mở chưa đo).

## 0. Tóm tắt 1 dòng

Trên **100 câu hỏi** (50 câu dễ + 50 câu khó/gián tiếp — xem §1.2) và **3 cấu hình chunk** (200/50,
500/100, 850/170), xếp hạng tổng thể là **850/170 > 500/100 > 200/50** trên gần như mọi chỉ số đo
được (Hit@1: 61% > 60% > 58%; Hit@3: 87% > 83% > 80%; Hit@5: 93% > 90% > 88%; MRR: 0.747 > 0.723 >
0.694). **Đi nhỏ hơn (200/50) KHÔNG cải thiện gì — nó là cấu hình TỆ NHẤT trong 3**, dù nó có điểm
cosine top-1 trung bình CAO NHẤT (0.7757, so với 0.7477 và 0.7345). Đây là bằng chứng trực tiếp phản
bác giả thuyết ban đầu "chunk càng hẹp càng bắt ngữ nghĩa chính xác hơn": hẹp hơn cho điểm số cao hơn
(ít pha loãng vector) nhưng **hẹp quá làm tăng số lượng chunk cạnh tranh** (140 chunk so với 53/33),
khiến nhiều chunk "gần đúng chủ đề" chen vào top-k, hại tỉ lệ hit thực tế. Mọi chênh lệch giữa 3 cấu
hình **đều không có ý nghĩa thống kê** ở cỡ mẫu 100 câu (xem §4). Bóc tách theo độ khó (§2.2) cho
thấy 850/170 xử lý câu hỏi khó/gián tiếp tốt nhất trong 3; 200/50 yếu nhất ở câu dễ lẫn câu khó.
**Stress test bổ sung (§7)** — kéo dài snippet ground-truth lên 150 từ (mô phỏng câu hỏi cần ngữ
cảnh dài hơn 1 câu) — cho kết quả DỨT KHOÁT, không mập mờ: 850/170 **hoàn toàn không suy giảm**
(Hit@1 không đổi), 500/100 suy giảm vừa phải, **200/50 sụp đổ** (Hit@1 rớt hơn nửa, intact-rate chỉ
còn 31.6%). Tổng hợp cả 2 phép đo, bằng chứng hiện có nghiêng về **850/170** là lựa chọn tốt nhất
trong 3, không phải 500/100 như quyết định ban đầu.

## 1. Phương pháp — mẫu bao nhiêu, chạy bao nhiêu lần

### 1.1 Corpus

Toàn bộ 9 file trong `packages/kb/data/` (không thêm/bớt), tổng **20.883 từ**:

| File | Từ |
|---|---|
| Chế độ lương thưởng - hr.md | 3137 |
| Nội quy an toàn lao động - engineeringdocx.docx | 1510 |
| Quy định nghỉ phép 2 - public.txt | 2566 |
| Quy định bảo mật - engineering.md | 881 |
| nội quy lao động - public.docx | 6070 |
| nội quy lao động 2- public.docx | 1598 |
| quy chế lương thưởng - hr.docx | 1977 |
| quy chế lương thưởng - hr.md | 1497 |
| quy định nghỉ phép - public.txt | 1647 |

Cắt bằng đúng `cut_window()` thật (không mô phỏng lại logic) ở 3 cấu hình:

| Cấu hình | size/overlap | Số chunk sinh ra |
|---|---|---|
| C | 200/50 | **140 chunk** |
| A | 500/100 | **53 chunk** |
| B | 850/170 | **33 chunk** |

Cấu hình C (200/50) được đo thêm sau, theo đúng cùng 100 câu hỏi ground-truth và cùng phương pháp
— không tạo bộ câu hỏi riêng, không đổi corpus.

### 1.2 Bộ câu hỏi ground-truth — **100 câu, 2 vòng độ khó, sinh bởi LLM thật, verify verbatim tự động**

Để tránh thiên vị (đặt câu hỏi SAU khi đã cắt chunk sẽ vô tình ưu ái cấu hình đang nhìn thấy), toàn
bộ câu hỏi được sinh từ **văn bản gốc, CHƯA cắt chunk** — dùng LLM thật (`o4-mini`, real OpenAI API
qua `build_llm()`, KHÔNG dùng `ExtractiveFakeLLM`) đọc nguyên văn từng file và sinh câu hỏi.

Mỗi câu hỏi có 3 trường: `question`, `expected_answer` (đáp án ngắn), `expected_snippet` (đoạn trích
NGUYÊN VĂN). **`expected_snippet` được kiểm tra tự động là substring chính xác** (sau khi chuẩn hoá
Unicode NFKC + gộp khoảng trắng + đồng nhất biến thể gạch ngang/dấu ngoặc) của văn bản gốc — câu nào
LLM "bịa"/diễn giải sai đều bị loại, không sửa tay. Mọi câu (cả 2 vòng) được kiểm trùng lặp bằng
`difflib.SequenceMatcher` trên `expected_snippet` (ngưỡng similarity > 0.85), **kể cả trùng xuyên
file** (2 file "nội quy lao động"/"nội quy lao động 2" có nội dung gần giống nhau) — câu trùng bị
loại và sinh lại.

**Vòng 1 — câu hỏi trực diện (50 câu):** hỏi thẳng vào sự kiện, không giới hạn vị trí trong tài liệu.

**Vòng 2 — câu hỏi KHÓ hơn, TRẢI RỘNG hơn (50 câu):** cùng quy trình verify verbatim + chống trùng
(chống trùng cả với vòng 1), nhưng prompt yêu cầu thêm:
1. **Hỏi gián tiếp** — không dùng lại cụm từ/thứ tự chữ trong tài liệu, phải diễn đạt lại.
2. **Nhắm chi tiết ít nổi bật** — không hỏi lại số liệu "đập vào mắt" đầu đoạn/tiêu đề, ưu tiên điều
   khoản phụ, trường hợp ngoại lệ nằm giữa đoạn văn dài.
3. **Trải rộng khắp tài liệu** — không dồn vào 1-2 đoạn đầu.
4. Cho phép câu hỏi dạng so sánh/điều kiện, miễn vẫn có 1 đáp án cụ thể, ngắn.

Cả 2 vòng dùng cùng tỉ lệ số câu/file (theo độ dài file, trần 10-11 câu/file) để giữ cân đối:

| File | Vòng 1 | Vòng 2 | Tổng |
|---|---|---|---|
| nội quy lao động - public.docx | 11 | 11 | 22 |
| Chế độ lương thưởng - hr.md | 9 | 9 | 18 |
| Quy định nghỉ phép 2 - public.txt | 6 | 6 | 12 |
| quy chế lương thưởng - hr.docx | 5 | 5 | 10 |
| Nội quy an toàn lao động - engineeringdocx.docx | 4 | 4 | 8 |
| nội quy lao động 2- public.docx | 4 | 4 | 8 |
| quy chế lương thưởng - hr.md | 4 | 4 | 8 |
| quy định nghỉ phép - public.txt | 4 | 4 | 8 |
| Quy định bảo mật - engineering.md | 3 | 3 | 6 |
| **Tổng** | **50** | **50** | **100** |

**Số liệu sinh thật (không phải xin đúng bao nhiêu ra đúng bấy nhiêu):** vòng 1 xin 48 câu ban đầu →
48/48 verbatim hợp lệ → kiểm trùng lặp phát hiện 10/48 trùng ý → bù 12 câu (10 thay trùng + 2 để đạt
50) → 1 câu trùng xuyên file sót lại → thay tiếp 1 câu → **50/50 sạch**. Vòng 2 xin theo cùng tỉ lệ,
tỉ lệ loại bỏ CAO HƠN hẳn vòng 1 (nhiều câu bị loại vì không verbatim — do prompt ép "diễn đạt lại"
khiến model đôi khi lẫn qua diễn giải luôn cả snippet) → cân lại + bù + thay 1 câu trùng xuyên file
(y hệt vòng 1: 2 file "nội quy lao động" lại tạo trùng) → **50/50 sạch**. Toàn bộ 100 câu final kiểm
tra chéo (100×99/2 = 4950 cặp) → **0 cặp trùng > 0.85 similarity**.

Toàn bộ 100 câu nằm ở `evidence/qa_set_100.json`.

### 1.3 Truy hồi — chạy **1 lần**, số liệu chính xác/tái lập được, không có nhiễu ngẫu nhiên

Mỗi câu hỏi được embed thật (1 lần, batch), so cosine với **toàn bộ** chunk của từng cấu hình (không
qua `PgKbSearch.search()` production — đây là script offline độc lập, không đụng contract frozen
`kb-search.v0.md`/case SC-04). Lấy top-5.

**Vì sao chỉ 1 lần, không lặp N lần:** embedding là hàm **thuần/tất định** (cùng text → cùng vector,
không có nhiệt độ/lấy mẫu ngẫu nhiên) — chạy lại 1000 lần vẫn ra đúng cùng 1 con số. Khác với 1 lượt
LLM trả lời tự do (có thể đổi câu trả lời giữa các lần chạy) — **không có bước LLM trả lời tự do
trong benchmark này** (đã bỏ theo yêu cầu), thay bằng tiêu chí "phân hoá điểm đúng/sai" (§3) đo trực
tiếp trên embedding.

## 2. Chỉ số truy hồi (Hit@k, MRR)

**Định nghĩa "hit":** top-k chunk có chứa `expected_snippet` (đã chuẩn hoá) nguyên vẹn.

### 2.1 Gộp 100 câu (kết quả chính)

| Metric | 200/50 | 500/100 | 850/170 |
|---|---|---|---|
| Số chunk trong corpus | 140 | 53 | 33 |
| Hit@1 | 58/100 (58%) | 60/100 (60%) | **61/100 (61%)** |
| Hit@3 | 80/100 (80%) | 83/100 (83%) | **87/100 (87%)** |
| Hit@5 | 88/100 (88%) | 90/100 (90%) | **93/100 (93%)** |
| MRR@5 | 0.6940 | 0.7227 | **0.7473** |
| Điểm cosine top-1 trung bình | **0.7757** | 0.7477 | 0.7345 |
| Tỉ lệ đoạn trích còn nguyên vẹn trong ≥1 chunk (`snippet_intact_rate`) | 100% | 100% | 100% |

**Xếp hạng nhất quán: 850/170 > 500/100 > 200/50** ở mọi chỉ số đo "có tìm đúng hay không"
(Hit@1/3/5, MRR) — càng hẹp càng TỆ HƠN, ngược hẳn trực giác ban đầu. Chỉ riêng "điểm cosine top-1
trung bình" thì xếp hạng NGƯỢC LẠI (200/50 cao nhất) — đây chính là điểm mấu chốt: **chunk hẹp cho
điểm số cao hơn (do không pha loãng vector với nội dung khác) nhưng KHÔNG đồng nghĩa với tìm đúng
nhiều hơn**, vì hẹp quá sinh ra QUÁ NHIỀU chunk (140 so với 33-53), nhiều chunk trong số đó "gần
đúng chủ đề" nên cũng đạt điểm cao, cạnh tranh vị trí top-1 với đúng chunk cần tìm.

**`snippet_intact_rate` = 100% ở CẢ 3 cấu hình, cả 2 vòng câu hỏi.** Giả thuyết ban đầu ("cửa sổ dài
dễ xé lẻ 1 sự kiện qua ranh giới cắt") **không xảy ra trên corpus này ở bất kỳ cấu hình nào** — mọi
`expected_snippet` (≤25 từ) đủ ngắn để nằm trọn trong 1 chunk dù cắt kiểu nào, kể cả 200/50.

### 2.2 Bóc tách theo độ khó

| Metric | Vòng | 200/50 | 500/100 | 850/170 |
|---|---|---|---|---|
| Hit@1 | 1 (dễ) | 34/50 (68%) | 38/50 (**76%**) | 37/50 (74%) |
| Hit@1 | 2 (khó) | 24/50 (48%) | 22/50 (44%) | **24/50 (48%)** |
| Hit@3 | 1 (dễ) | 45/50 (90%) | 47/50 (94%) | 48/50 (**96%**) |
| Hit@3 | 2 (khó) | 35/50 (70%) | 36/50 (72%) | **39/50 (78%)** |
| Hit@5 | 1 (dễ) | 49/50 (98%) | 49/50 (98%) | 49/50 (98%) |
| Hit@5 | 2 (khó) | 39/50 (78%) | 41/50 (82%) | **44/50 (88%)** |
| MRR@5 | 1 (dễ) | 0.7967 | **0.8567** | 0.8473 |
| MRR@5 | 2 (khó) | 0.5913 | 0.5887 | **0.6473** |
| Margin trung bình | 1 (dễ) | +0.0224 | **+0.0235** | +0.0209 |
| Margin trung bình | 2 (khó) | -0.0027 | -0.0108 | **-0.0045** |

**Đọc bảng này:** 200/50 KHÔNG thắng ở câu dễ (thua cả 500 lẫn 850 về Hit@1/Hit@3/MRR — 140 chunk
nhỏ tạo quá nhiều "hàng xóm gần đúng chủ đề" cạnh tranh, ngay cả khi câu hỏi bám sát chữ nguồn). Ở
câu khó, 200/50 hoà 850/170 về Hit@1 (48% = 48%) nhưng vẫn thua rõ ở Hit@3/Hit@5/MRR — không có
tình huống nào 200/50 là lựa chọn tốt nhất. Vòng 2 kéo điểm mọi cấu hình xuống mạnh (Hit@1 rơi từ
~70-76% xuống ~44-48%, xác nhận câu hỏi vòng 2 thật sự khó hơn, không phải khó giả); 850/170 chịu
đòn nhẹ nhất trong 3, nên khi gộp 100 câu nó vượt lên dẫn đầu. **Cơ chế hợp lý:** câu hỏi gián
tiếp/diễn đạt lại cần nhiều ngữ cảnh hơn để cầu nối giữa cách hỏi và cách tài liệu viết — cửa sổ rộng
hơn có lợi thế ở tình huống này; cửa sổ QUÁ hẹp (200) không đủ ngữ cảnh nên thiệt cả 2 chiều.

## 3. Phân hoá điểm đúng/sai (margin)

Với mỗi câu hỏi: `margin = điểm cosine cao nhất trong nhóm chunk ĐÚNG (chứa snippet) − điểm cosine
cao nhất trong nhóm chunk SAI (không chứa snippet)`. Margin dương = xếp đúng chunk lên trên MỌI
chunk nhiễu (tương đương Hit@1); âm = bị chunk sai qua mặt.

| Metric (100 câu) | 500/100 | 850/170 |
|---|---|---|
| Metric (100 câu) | 200/50 | 500/100 | 850/170 |
|---|---|---|---|
| Số câu phân hoá đúng (margin > 0) | 58/100 (58%) | 60/100 (60%) | **61/100 (61%)** |
| Margin trung bình | **0.0099** | 0.0064 | 0.0082 |
| Margin trung vị | 0.0103 | 0.0088 | **0.0101** (gần bằng 200/50) |
| Margin nhỏ nhất (tệ nhất) | -0.1175 | **-0.1154** (tệ nhất trong 3) | -0.0878 (ít tệ nhất) |
| Margin lớn nhất (tốt nhất) | 0.1227 | 0.1028 | **0.1239** |
| Số câu margin âm | 41/100 | 40/100 | **39/100** (ít nhất) |

**Điểm đáng chú ý:** 200/50 có margin trung bình/trung vị CAO — nhưng `separated_rate` (58%) lại
THẤP NHẤT trong 3, đúng với hiện tượng đã nêu ở §2.1: khi phân hoá đúng, 200/50 phân hoá rất dứt
khoát (margin lớn), nhưng SỐ LẦN phân hoá đúng lại ít hơn — margin trung bình bị "kéo lên" bởi các
ca thắng rõ, không phản ánh được tần suất thắng. Đây là lý do §8 dùng Hit@1/`separated_rate` (đếm
số câu, không lấy trung bình liên tục) làm chỉ số chính, không dùng margin trung bình đơn lẻ.

## 4. So sánh cặp (paired) — kiểm tra ý nghĩa thống kê

Trên **cùng 100 câu hỏi**, đếm số câu mỗi cặp cấu hình cho kết quả Hit@1 khác nhau (3 cặp):

| Cặp so sánh | Cả 2 hit | Cả 2 miss | Chỉ A đúng | Chỉ B đúng | Chênh lệch |
|---|---|---|---|---|---|
| 500/100 vs 850/170 | 44 | 23 | 16 (500) | 17 (850) | 1 câu |
| 500/100 vs 200/50 | 46 | 28 | 14 (500) | 12 (200) | 2 câu |
| 850/170 vs 200/50 | 39 | 20 | 22 (850) | 19 (200) | 3 câu |

**Cả 3 cặp đều lệch nhau rất ít (1-3 câu trên 100 câu) — KHÔNG có cặp nào đạt ý nghĩa thống kê.** Dù
850/170 áp đảo 200/50 nhiều nhất trong 3 cặp (22 vs 19), khoảng cách vẫn quá nhỏ để kết luận chắc
chắn. So với lúc chỉ đo 50 câu (500 vs 850: 7 vs 6, cũng không ý nghĩa), việc tăng cỡ mẫu và thêm
biến thể thứ 3 **không** làm chênh lệch rõ ràng hơn — càng củng cố kết luận: khác biệt giữa các cấu
hình, nếu có, rất nhỏ so với biến thiên tự nhiên giữa các câu hỏi. Xếp hạng nhất quán 850>500>200 ở
mọi metric tổng hợp (§2.1) là tín hiệu thật, nhưng "tín hiệu thật" ở đây nghĩa là **xu hướng nhất
quán qua nhiều chỉ số**, không phải **từng cặp riêng lẻ có ý nghĩa thống kê**.

## 5. Ví dụ minh hoạ chi tiết (top-5 đầy đủ, có điểm số từng chunk)

### Ví dụ A — câu dễ (vòng 1), 500/100 thắng rõ

**Q: "Công nhân làm việc cần mặc trang phục gì theo nội quy công trường?"**
Đáp án: `mũ bảo hộ, giày bảo hộ`

**500/100:**

| rank | chunk_id | score | hit? |
|---|---|---|---|
| 1 | `...engineeringdocx.docx#c2` | 0.8133 | ✅ |
| 2 | `...engineeringdocx.docx#c1` | 0.7687 | ✅ |
| 3 | `...engineeringdocx.docx#c3` | 0.7356 | |
| 4 | `...engineeringdocx.docx#c4` | 0.7182 | |
| 5 | `nội quy lao động 2...#c4` | 0.7124 | |

**850/170:**

| rank | chunk_id | score | hit? |
|---|---|---|---|
| 1 | `...engineeringdocx.docx#c2` | 0.7711 | (chunk RỘNG hơn, pha loãng — mất hit ở #1) |
| 2 | `...engineeringdocx.docx#c1` | 0.7702 | ✅ |
| 3 | `nội quy lao động - public.docx#c4` | 0.6940 | |
| 4 | `nội quy lao động 2...#c2` | 0.6724 | |
| 5 | `nội quy lao động - public.docx#c1` | 0.6578 | |

Ranh giới hẹp hơn giữ chunk `#c2` "sạch" (chỉ nói về trang phục), chunk rộng ở 850 gộp thêm nội dung
không liên quan, pha loãng cosine (0.7711 so với 0.8133).

### Ví dụ B — câu dễ (vòng 1), 850/170 thắng rõ (ngược lại)

**Q: "Trong năm 2021, chi phí chi trả lương cho nhân viên của FPT là bao nhiêu?"**
Đáp án: `15.080 tỷ đồng`

**500/100** (Miss@1 — top-1 là chunk liền kề, cùng chủ đề nhưng không mang con số):

| rank | chunk_id | score | hit? |
|---|---|---|---|
| 1 | `...hr.md#c7` | 0.7824 | |
| 2 | `...hr.md#c6` | 0.7627 | ✅ |

**850/170** (Hit@1 — cửa sổ rộng hơn gộp trọn câu chứa con số vào chunk đứng đầu):

| rank | chunk_id | score | hit? |
|---|---|---|---|
| 1 | `...hr.md#c4` | 0.7409 | ✅ |
| 2 | `...hr.md#c1` | 0.7082 | |

Cho thấy "chunk hẹp luôn tốt hơn" không phải luật tuyệt đối — ranh giới cắt đôi khi tách đúng câu trả
lời khỏi phần văn bản có cosine cao nhất, gây Miss@1 ở bản hẹp dù bản rộng lại Hit@1.

### Ví dụ C — câu khó (vòng 2), cả 2 đều Miss@1, minh hoạ độ khó thật

**Q: "Trong trường hợp người lao động chưa làm đủ 12 tháng, quy chế lương thưởng của công ty áp
dụng ra sao?"** — cả 2 cấu hình đều KHÔNG lọt top-5 (`margin` 500/100 = -0.1059, 850/170 = -0.0878,
mức âm sâu nhất trong toàn bộ 100 câu ở cả hai). Câu hỏi diễn đạt gián tiếp + nhắm điều khoản phụ
khiến cả 2 cấu hình đều thua các chunk "cùng chủ đề lương thưởng nói chung" — lỗi này không liên
quan window size, nằm ở việc câu hỏi diễn đạt xa cách chữ nguồn.

**Q: "Có quy định nào về việc tiếp cận các khu vực nguy hiểm trong công trường không?"** — 500/100
Miss@1 (rank 2, margin -0.0023, gần như hoà), 850/170 Hit@1 (margin +0.0320) — một ca khác nơi cửa sổ
rộng hơn thắng ở câu khó, cùng hướng với xu hướng tổng ở §2.2.

### Ví dụ D — 200/50 thua rõ dù 500/100 và 850/170 đều Hit@1 (minh hoạ "quá nhiều chunk cạnh tranh")

**Q: "Theo quy định, sau bao nhiêu năm làm việc sẽ được tăng thêm 1 ngày nghỉ phép?"** Đáp án: `5 năm`

**200/50** (140 chunk trong corpus — Miss@1, đúng chunk chỉ đứng hạng 3):

| rank | chunk_id | score | hit? |
|---|---|---|---|
| 1 | `Quy định nghỉ phép 2...#c2` | 0.8369 | (chunk khác, cùng chủ đề "cách tính phép năm" nhưng KHÔNG có con số 5 năm) |
| 2 | `nội quy lao động...#c6` | 0.8302 | |
| 3 | `Quy định nghỉ phép 2...#c6` | 0.8233 | ✅ |

**500/100** (53 chunk — Hit@1):

| rank | chunk_id | score | hit? |
|---|---|---|---|
| 1 | `Quy định nghỉ phép 2...#c3` | 0.8365 | ✅ |
| 2 | `nội quy lao động...#c3` | 0.8277 | |
| 3 | `Quy định nghỉ phép 2...#c2` | 0.8196 | ✅ |

Cùng 1 file "Quy định nghỉ phép 2" khi cắt ở 200 từ bị chia thành nhiều chunk nhỏ hơn, mỗi chunk chỉ
nói về "cách tính ngày phép" theo nhiều góc khác nhau — tạo ra 2-3 chunk cùng đạt điểm 0.82-0.84 dù
chỉ 1 trong số đó thực sự chứa "5 năm". Ở 500/100, cùng nội dung đó gộp lại thành ít chunk hơn, chunk
chứa đúng con số nổi bật rõ hơn tương đối so với các chunk còn lại — **đúng cơ chế thống kê đã nêu ở
§2.1**: hẹp quá tạo nhiều "ứng viên gần đúng" cạnh tranh nhau, không phải "hẹp quá làm mất thông
tin".

*(Toàn bộ 100 câu × top-5 × điểm số của cả 3 cấu hình nằm đầy đủ trong
`evidence/retrieval_results_100q_200_50.json`, `evidence/retrieval_results_100q_500_100.json`,
`evidence/retrieval_results_100q_850_170.json`, mỗi câu có đủ rank, `chunk_id`, điểm cosine, cờ
`is_hit`, preview text.)*

## 6. Bảng đầy đủ 100/100 câu (rank hit + điểm top-1 + margin, 2 cấu hình song song)

`rank` = hạng của chunk đúng đầu tiên trong top-5 (`—` = không lọt top-5). `margin` = điểm chunk đúng
tốt nhất trừ điểm chunk sai tốt nhất (dương = phân hoá đúng). Cột "Vòng": 1 = câu dễ, 2 = câu khó.

| # | Vòng | Câu hỏi | Nguồn | 500/100 rank | 500 top1 | 500 margin | 850/170 rank | 850 top1 | 850 margin |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 1 | Mức lương khởi điểm dành cho nhân viên F… | Chế độ lương thư… | 1 | 0.7844 | +0.0491 | 1 | 0.7360 | +0.0354 |
| 2 | 1 | Mức lương cho vị trí quản lý tại FPT thư… | Chế độ lương thư… | 1 | 0.7849 | +0.0728 | 1 | 0.7368 | +0.0451 |
| 3 | 1 | Trong năm 2021, chi phí chi trả lương ch… | Chế độ lương thư… | 2 | 0.7824 | -0.0197 | 1 | 0.7409 | +0.0327 |
| 4 | 1 | Giờ làm việc của công trường vào buổi sá… | Nội quy an toàn … | 1 | 0.7514 | +0.0364 | 1 | 0.7542 | +0.0364 |
| 5 | 1 | Công nhân làm việc cần mặc trang phục gì… | Nội quy an toàn … | 1 | 0.8133 | +0.0777 | 2 | 0.7711 | -0.0009 |
| 6 | 1 | Thời gian ra vào công trường theo mẫu nộ… | Nội quy an toàn … | 2 | 0.7867 | -0.0111 | 1 | 0.8114 | +0.1239 |
| 7 | 1 | Công nhân không được làm gì dưới bất kỳ … | Nội quy an toàn … | 3 | 0.7835 | -0.0386 | 1 | 0.7725 | +0.0175 |
| 8 | 1 | Số ngày nghỉ phép năm cho người lao động… | Quy định nghỉ ph… | 1 | 0.8398 | +0.0311 | 2 | 0.8326 | -0.0013 |
| 9 | 1 | Theo quy định, sau bao nhiêu năm làm việ… | Quy định nghỉ ph… | 1 | 0.8365 | +0.0088 | 1 | 0.8287 | +0.0070 |
| 10 | 1 | Từ năm nào, ngày 24/11 sẽ chính thức đượ… | Quy định nghỉ ph… | 1 | 0.6749 | +0.1028 | 1 | 0.6328 | +0.0567 |
| 11 | 1 | Theo quy định mới, mức phạt đối với doan… | Quy định nghỉ ph… | 1 | 0.7998 | +0.0601 | 1 | 0.7851 | +0.0555 |
| 12 | 1 | Theo quy định, cứ đủ bao nhiêu năm làm v… | Quy định nghỉ ph… | 4 | 0.8279 | -0.0441 | 2 | 0.8212 | -0.0230 |
| 13 | 1 | Quyết định ban hành Quy chế bảo mật thôn… | Quy định bảo mật… | 1 | 0.7421 | +0.0456 | 1 | 0.7452 | +0.0465 |
| 14 | 1 | Ai có trách nhiệm kiểm tra, điều tra các… | Quy định bảo mật… | 1 | 0.6836 | +0.0342 | 2 | 0.6735 | -0.0008 |
| 15 | 1 | Hình thức xử lý vi phạm bảo mật thông ti… | Quy định bảo mật… | 1 | 0.6671 | +0.0501 | 1 | 0.7359 | +0.1033 |
| 16 | 1 | Nội quy lao động áp dụng cho những ai? | nội quy lao động… | 1 | 0.7961 | +0.0657 | 1 | 0.7647 | +0.0129 |
| 17 | 1 | Người lao động được nghỉ bao nhiêu ngày … | nội quy lao động… | 1 | 0.8224 | +0.0458 | 1 | 0.7871 | +0.0042 |
| 18 | 1 | Thời gian tối đa người lao động được hưở… | nội quy lao động… | 1 | 0.7333 | +0.0633 | 1 | 0.6795 | +0.0142 |
| 19 | 1 | Thời gian nghỉ thai sản đối với lao động… | nội quy lao động… | 1 | 0.7659 | +0.0290 | 1 | 0.7802 | +0.0590 |
| 20 | 1 | Lao động nữ được nghỉ thai sản tối đa ba… | nội quy lao động… | 1 | 0.8044 | +0.0237 | 1 | 0.7948 | +0.0467 |
| 21 | 1 | Thời gian tạm đình chỉ công việc không đ… | nội quy lao động… | 1 | 0.7523 | +0.0412 | 1 | 0.7411 | +0.0274 |
| 22 | 1 | Thời gian tạm đình chỉ công việc theo qu… | nội quy lao động… | 1 | 0.7559 | +0.0468 | 1 | 0.7446 | +0.0317 |
| 23 | 1 | Lao động nữ được nghỉ thai sản thêm bao … | nội quy lao động… | 1 | 0.7723 | +0.0281 | 1 | 0.7875 | +0.0553 |
| 24 | 1 | Năm nào Bộ luật Lao động nước Cộng hòa x… | nội quy lao động… | 1 | 0.6899 | +0.0557 | 1 | 0.6812 | +0.0459 |
| 25 | 1 | Thời gian làm việc của bộ phận Marketing… | nội quy lao động… | 1 | 0.6529 | +0.0086 | 1 | 0.6321 | +0.0004 |
| 26 | 1 | Người lao động phải báo cáo lý do đến tr… | nội quy lao động… | 1 | 0.7295 | +0.0554 | 1 | 0.6836 | +0.0056 |
| 27 | 1 | Quy chế trả lương của công ty sẽ có hiệu… | quy chế lương th… | 1 | 0.7686 | +0.0014 | 1 | 0.7826 | +0.0347 |
| 28 | 1 | Mức lương thử việc người lao động được h… | quy chế lương th… | 1 | 0.7146 | +0.0312 | 1 | 0.7005 | +0.0162 |
| 29 | 1 | Theo quy định, ngày cuối cùng của tháng … | quy chế lương th… | 2 | 0.7410 | -0.0365 | 1 | 0.7113 | +0.0148 |
| 30 | 1 | Mức thưởng cuối năm tùy thuộc vào yếu tố… | quy chế lương th… | 1 | 0.7441 | +0.0328 | 1 | 0.7289 | +0.0408 |
| 31 | 1 | Bộ luật Lao động số 45/2019/QH14 được Qu… | quy chế lương th… | — | 0.7112 | -0.0615 | 3 | 0.6968 | -0.0503 |
| 32 | 1 | Mức lương thử việc được quy định là bao … | quy chế lương th… | 4 | 0.7077 | -0.0292 | 5 | 0.6938 | -0.0350 |
| 33 | 1 | Khoản phụ cấp đi lại và xăng xe có mức h… | quy chế lương th… | 1 | 0.7050 | +0.0230 | — | 0.6528 | -0.0251 |
| 34 | 1 | Tiền thưởng Tết Nguyên Đán căn cứ vào nh… | quy chế lương th… | 2 | 0.7246 | -0.0215 | 3 | 0.7119 | -0.0318 |
| 35 | 1 | Người lao động khi nghỉ phép dưới 2 ngày… | quy định nghỉ ph… | 1 | 0.7770 | +0.0118 | 2 | 0.7700 | -0.0120 |
| 36 | 1 | Thời gian nghỉ thai sản của lao động nữ … | quy định nghỉ ph… | 2 | 0.8197 | -0.0198 | 2 | 0.8158 | -0.0453 |
| 37 | 1 | Người lao động được nghỉ chăm sóc con ốm… | quy định nghỉ ph… | 1 | 0.7397 | +0.0060 | 2 | 0.7499 | -0.0267 |
| 38 | 1 | Người lao động cần có giấy xác nhận từ a… | quy định nghỉ ph… | 1 | 0.7536 | +0.0223 | 1 | 0.7521 | +0.0411 |
| 39 | 1 | Trong năm 2021, FPT có bao nhiêu nhân vi… | Chế độ lương thư… | 1 | 0.7408 | +0.0624 | 1 | 0.6880 | +0.0311 |
| 40 | 1 | Mức phụ cấp trách nhiệm cho phó giám đốc… | Chế độ lương thư… | 2 | 0.7629 | -0.0117 | 1 | 0.7478 | +0.0428 |
| 41 | 1 | Mức lương trung bình mỗi tháng cho mỗi n… | Chế độ lương thư… | 1 | 0.7748 | +0.0039 | 2 | 0.7368 | -0.0063 |
| 42 | 1 | Số lượng cổ phiếu ESOP được phát hành ch… | Chế độ lương thư… | 1 | 0.6746 | +0.0368 | 1 | 0.6468 | +0.0524 |
| 43 | 1 | Lương cứng cho nhân viên cộng tác viên k… | Chế độ lương thư… | 1 | 0.6987 | +0.0416 | 1 | 0.6734 | +0.0200 |
| 44 | 1 | Mỗi năm, nhân viên FPT còn được hưởng th… | Chế độ lương thư… | 2 | 0.7568 | -0.0056 | 1 | 0.7534 | +0.0481 |
| 45 | 1 | Nhóm nào được hưởng số ngày nghỉ phép nă… | Quy định nghỉ ph… | 1 | 0.7855 | +0.0395 | 1 | 0.7878 | +0.0108 |
| 46 | 1 | Người lao động được nghỉ việc riêng có l… | nội quy lao động… | 1 | 0.7811 | +0.0169 | 1 | 0.7671 | +0.0175 |
| 47 | 1 | Lao động nam được nghỉ việc hưởng chế độ… | nội quy lao động… | 1 | 0.7925 | +0.0393 | 1 | 0.7895 | +0.0477 |
| 48 | 1 | Công ty có quyền tạm đình chỉ công việc … | nội quy lao động… | 1 | 0.7944 | +0.0641 | 1 | 0.7956 | +0.0018 |
| 49 | 1 | Thời gian nghỉ trưa của Bộ phận Marketin… | nội quy lao động… | 2 | 0.6946 | -0.0016 | 2 | 0.6831 | -0.0028 |
| 50 | 1 | Mức thưởng cụ thể cho mỗi nhân viên tron… | quy chế lương th… | 1 | 0.7348 | +0.0121 | 1 | 0.7168 | +0.0214 |
| 51 | 2 | Điều kiện nào được áp dụng để xác định p… | Chế độ lương thư… | 2 | 0.7283 | -0.0149 | 1 | 0.7174 | +0.0228 |
| 52 | 2 | Mức hỗ trợ tiền ăn trưa của nhân viên FP… | Chế độ lương thư… | 2 | 0.7248 | -0.0017 | 1 | 0.7275 | +0.0316 |
| 53 | 2 | Chính sách hỗ trợ nhà ở của FPT được áp … | Chế độ lương thư… | 3 | 0.6778 | -0.0042 | 4 | 0.6782 | -0.0243 |
| 54 | 2 | Ai là người quyết định về việc chi trả l… | Chế độ lương thư… | 4 | 0.7583 | -0.0438 | 4 | 0.7329 | -0.0348 |
| 55 | 2 | Các khoản phụ cấp mà nhân viên FPT nhận … | Chế độ lương thư… | 1 | 0.7510 | +0.0106 | 1 | 0.7467 | +0.0330 |
| 56 | 2 | Lương tháng của một nhân viên kế toán ở … | Chế độ lương thư… | — | 0.7599 | -0.0567 | 5 | 0.7389 | -0.0430 |
| 57 | 2 | Ai là những người cần tuân thủ quy định … | Nội quy an toàn … | 3 | 0.7739 | -0.0380 | 2 | 0.7715 | -0.0302 |
| 58 | 2 | Có quy định nào về việc tiếp cận các khu… | Nội quy an toàn … | 2 | 0.7400 | -0.0023 | 1 | 0.7372 | +0.0320 |
| 59 | 2 | Những điều kiện nào cần phải có khi một … | Nội quy an toàn … | 1 | 0.7189 | +0.0253 | 2 | 0.7014 | -0.0050 |
| 60 | 2 | Trong nội quy, ai là người có thẩm quyền… | Nội quy an toàn … | 4 | 0.7486 | -0.0350 | 2 | 0.7654 | -0.0375 |
| 61 | 2 | Điều nào được quy định liên quan đến việ… | Quy định nghỉ ph… | — | 0.7481 | -0.0571 | — | 0.7194 | -0.0374 |
| 62 | 2 | Trong trường hợp nào, người lao động vẫn… | Quy định nghỉ ph… | — | 0.8208 | -0.0685 | 1 | 0.8205 | +0.0162 |
| 63 | 2 | So với lao động trong điều kiện bình thư… | Quy định nghỉ ph… | 1 | 0.7910 | +0.0431 | 2 | 0.7771 | -0.0003 |
| 64 | 2 | Nếu một nhân viên làm việc gần 6 tháng t… | Quy định nghỉ ph… | 2 | 0.7446 | -0.0051 | 2 | 0.7526 | -0.0046 |
| 65 | 2 | Trong trường hợp nào tiền nghỉ phép chưa… | Quy định nghỉ ph… | 1 | 0.7601 | +0.0025 | 1 | 0.7461 | +0.0232 |
| 66 | 2 | Trong trường hợp nào người lao động có t… | Quy định nghỉ ph… | 1 | 0.7564 | +0.0206 | 1 | 0.7682 | +0.0449 |
| 67 | 2 | Ai có quyền quyết định thông tin nào cần… | Quy định bảo mật… | 2 | 0.7331 | -0.0175 | 1 | 0.7330 | +0.0369 |
| 68 | 2 | Thông tin nào cần được xác định và bảo m… | Quy định bảo mật… | 1 | 0.7266 | +0.0383 | 1 | 0.7208 | +0.0678 |
| 69 | 2 | Cán bộ nào có quyền cung cấp thông tin v… | Quy định bảo mật… | 2 | 0.6608 | -0.0168 | 1 | 0.6417 | +0.0406 |
| 70 | 2 | Trong những trường hợp nào công ty phải … | nội quy lao động… | 1 | 0.7340 | +0.0522 | 2 | 0.7265 | -0.0292 |
| 71 | 2 | Ngoài việc thông báo trước, điều gì cần … | nội quy lao động… | 1 | 0.7827 | +0.0055 | 1 | 0.7659 | +0.0007 |
| 72 | 2 | Người lao động có thể giải quyết các vấn… | nội quy lao động… | 1 | 0.7121 | +0.0063 | 3 | 0.7184 | -0.0183 |
| 73 | 2 | Trong quy định về thời gian nghỉ phép hà… | nội quy lao động… | 3 | 0.7913 | -0.0305 | 1 | 0.7920 | +0.0107 |
| 74 | 2 | Nếu người lao động làm việc không đủ 12 … | nội quy lao động… | 5 | 0.8222 | -0.0626 | 2 | 0.8060 | -0.0084 |
| 75 | 2 | Nếu người lao động muốn thay đổi lịch ng… | nội quy lao động… | 1 | 0.7037 | +0.0262 | 1 | 0.6832 | +0.0023 |
| 76 | 2 | Trong trường hợp nào người lao động được… | nội quy lao động… | 1 | 0.7396 | +0.0483 | 2 | 0.7530 | -0.0461 |
| 77 | 2 | Nội quy lao động quy định trách nhiệm gì… | nội quy lao động… | — | 0.8269 | -0.1154 | — | 0.7663 | -0.0766 |
| 78 | 2 | Trong trường hợp nào thời gian làm việc … | nội quy lao động… | 2 | 0.6967 | -0.0203 | 2 | 0.6827 | -0.0125 |
| 79 | 2 | Người lao động phải làm gì nếu không thể… | nội quy lao động… | 1 | 0.7336 | +0.0506 | 1 | 0.7002 | +0.0247 |
| 80 | 2 | Người lao động có thể được chấp thuận ra… | nội quy lao động… | 1 | 0.7072 | +0.0104 | 2 | 0.6980 | -0.0022 |
| 81 | 2 | Trong những trường hợp nào nhân viên khô… | quy chế lương th… | 2 | 0.7149 | -0.0009 | 1 | 0.7027 | +0.0181 |
| 82 | 2 | Những ai sẽ được hưởng chế độ phụ cấp ca… | quy chế lương th… | 5 | 0.7039 | -0.0374 | 1 | 0.6790 | +0.0030 |
| 83 | 2 | Mức tăng lương được xét trong mỗi kỳ nân… | quy chế lương th… | 1 | 0.7378 | +0.0643 | 1 | 0.7211 | +0.0195 |
| 84 | 2 | Trong trường hợp người lao động chưa làm… | quy chế lương th… | — | 0.8261 | -0.1059 | — | 0.8096 | -0.0878 |
| 85 | 2 | Trong trường hợp nào, người lao động ký … | quy chế lương th… | 1 | 0.6751 | +0.0029 | — | 0.6880 | -0.0248 |
| 86 | 2 | Điều kiện nào quyết định việc áp dụng hì… | quy chế lương th… | 5 | 0.7525 | -0.0772 | 4 | 0.7325 | -0.0529 |
| 87 | 2 | Cách thức chi lương có thay đổi gì khi n… | quy chế lương th… | — | 0.7336 | -0.0742 | — | 0.7091 | -0.0501 |
| 88 | 2 | Trong những trường hợp nào mà nhân viên … | quy chế lương th… | — | 0.7046 | -0.0666 | — | 0.7030 | -0.0526 |
| 89 | 2 | Theo quy định, hình thức kỷ luật nào có … | quy chế lương th… | 3 | 0.7315 | -0.0094 | 3 | 0.7504 | -0.0451 |
| 90 | 2 | Trong trường hợp nào quy định nghỉ không… | quy định nghỉ ph… | 1 | 0.7194 | +0.0511 | 1 | 0.7192 | +0.0482 |
| 91 | 2 | Người lao động cần làm gì để có được tiề… | quy định nghỉ ph… | 1 | 0.7575 | +0.0205 | 1 | 0.7283 | +0.0016 |
| 92 | 2 | Trong những trường hợp nào thì người lao… | quy định nghỉ ph… | 1 | 0.7302 | +0.0400 | 1 | 0.7274 | +0.0241 |
| 93 | 2 | Để chuẩn bị cho thời gian nghỉ phép năm,… | quy định nghỉ ph… | 1 | 0.7620 | +0.0164 | 1 | 0.7488 | +0.0036 |
| 94 | 2 | Các vị trí quản lý tại công ty có mức đã… | Chế độ lương thư… | 2 | 0.7112 | -0.0309 | 1 | 0.6805 | +0.0101 |
| 95 | 2 | Nhân viên nào trong bộ phận quản lý lại … | Chế độ lương thư… | 2 | 0.7101 | -0.0470 | 1 | 0.6604 | +0.0220 |
| 96 | 2 | Điều gì sẽ xảy ra với nhân viên không đạ… | Chế độ lương thư… | — | 0.6699 | -0.0512 | 4 | 0.6511 | -0.0286 |
| 97 | 2 | Quy trình thông báo khi người lao động g… | nội quy lao động… | 1 | 0.6835 | +0.0088 | 2 | 0.6786 | -0.0060 |
| 98 | 2 | Trong trường hợp nào người lao động khôn… | nội quy lao động… | 1 | 0.7733 | +0.0722 | 2 | 0.7067 | -0.0048 |
| 99 | 2 | Trong trường hợp nào người lao động được… | nội quy lao động… | — | 0.8270 | -0.0702 | 2 | 0.8241 | -0.0028 |
| 100 | 2 | Khi nào người lao động được tính thêm th… | nội quy lao động… | 1 | 0.7403 | +0.0045 | 1 | 0.7355 | +0.0020 |

## 7. Stress test: kéo dài snippet lên 150 từ — kiểm chứng trực tiếp rủi ro xé lẻ/pha loãng

Sau khi bàn về rủi ro "850 pha loãng đáp án ngắn nằm cuối chunk dài" (đoạn hội thoại trước khi có phần này),
câu hỏi ngược lại được đặt ra: **nếu bản thân đáp án/ngữ cảnh cần thiết dài hơn — không phải 1 câu
ngắn mà cả 1 đoạn — thì cấu hình nào chịu thiệt hơn?** Đo trực tiếp thay vì suy luận.

**Phương pháp:** lấy 20 câu cuối (#81-100, vòng 2 — câu khó) trong bộ 100 câu, **kéo dài
`expected_snippet` từ ≤52 từ lên ~150 từ** (mở rộng đối xứng quanh vị trí snippet gốc trong văn bản
nguồn, vẫn là substring nguyên văn 100% — không phải diễn giải). 150 từ được chọn vì nó **lớn hơn cả
cửa sổ 200/50**, xấp xỉ 30% cửa sổ 500/100, và chỉ ~18% cửa sổ 850/170 — đủ để phân hoá rõ 3 cấu
hình. 1/20 câu không định vị được vị trí chính xác trong văn bản (lệch tokenize dấu câu), loại ra,
còn **19/20 câu** dùng được. Đo lại `intact_rate` và `Hit@1`/`Hit@5` với snippet dài này, so với
chính 19 câu đó bằng snippet ngắn gốc.

| Cấu hình | intact (ngắn) | intact (dài, 150 từ) | Hit@1 (ngắn) | Hit@1 (dài) | Hit@5 (ngắn) | Hit@5 (dài) |
|---|---|---|---|---|---|---|
| 200/50 | 100% | **31.6%** | 42.1% | **15.8%** | 78.9% | **31.6%** |
| 500/100 | 100% | 89.5% | 47.4% | 42.1% | 78.9% | 68.4% |
| 850/170 | 100% | **100%** | 52.6% | **52.6% (không đổi)** | 84.2% | 78.9% |

**Kết quả dứt khoát, không mập mờ:** khi ngữ cảnh cần thiết dài ra, **850/170 hoàn toàn không bị ảnh
hưởng** (intact vẫn 100%, Hit@1 y hệt không đổi). **500/100 chịu thiệt vừa phải** (intact rớt còn
89.5%, Hit@1 rớt nhẹ 47.4%→42.1%). **200/50 sụp đổ** — chỉ còn **31.6% snippet 150-từ nằm trọn
trong 1 chunk**, kéo Hit@1 rớt hơn NỬA (42.1%→15.8%) và Hit@5 rớt gần 1 nửa (78.9%→31.6%).

**Ý nghĩa đối với câu hỏi "500 hay 850 an toàn hơn khi mở rộng":** stress test này **đảo ngược lập
luận "pha loãng ủng hộ 500"** ở kết luận trước khi có phần này (§8 mục 6) — đó là suy luận đúng về mặt lý thuyết cho
**1 kiểu rủi ro** (đáp án ngắn, nằm lọt thỏm cuối 1 chunk dài, bị pha loãng bởi nội dung không liên
quan phía trước). Nhưng đo trực tiếp thì rủi ro NGƯỢC LẠI — **đáp án/ngữ cảnh dài hơn 1 câu, bị XÉ
LẺ qua ranh giới cắt** — nghiêm trọng hơn nhiều và ảnh hưởng ngay ở 500/100 (chưa nói 200/50). Không
có tài liệu HR/nội quy nào đảm bảo mọi câu trả lời chỉ gói gọn trong 1 câu ngắn — nhiều câu hỏi vòng
2 (khó, gián tiếp) trong benchmark chính bản thân nó đã cần ngữ cảnh nhiều câu để trả lời đúng, đúng
loại câu hỏi mà stress test này mô phỏng.

**Giới hạn của stress test này (nói thẳng, không giấu):** n=19, chỉ trích từ 1 phần vòng 2 (không
đại diện đều cho cả 9 file/2 vòng câu hỏi), và cách "kéo dài" là **cắt cơ học đối xứng quanh snippet
gốc** (không phải người/LLM chọn ranh giới ngữ nghĩa hợp lý) — 150 từ kéo dài có thể chứa nội dung
không thực sự cần thiết để trả lời câu hỏi, làm phép đo `hit` (đòi nguyên văn 150 từ khớp trọn) khắt
khe hơn cần thiết. Nhưng ngay cả với giới hạn đó, khoảng cách giữa 850/170 (0% ảnh hưởng) và 200/50
(sụp đổ) quá lớn để coi là nhiễu ngẫu nhiên.

## 8. Kết luận

1. **Xếp hạng nhất quán 850/170 > 500/100 > 200/50** ở mọi chỉ số "tìm đúng hay không" (Hit@1/3/5,
   MRR) — nhưng chênh lệch giữa các cặp đều nhỏ (1-7 điểm phần trăm) và **không có ý nghĩa thống kê**
   (paired comparison: 1-3 câu lệch trên 100 câu ở cả 3 cặp, §4).
2. **Đi hẹp hơn (200/50) KHÔNG cải thiện retrieval — ngược lại, đây là cấu hình tệ nhất trong 3.**
   Đây là phát hiện quan trọng nhất so với 2 lần đo trước: giả thuyết ban đầu của quyết định hạ
   850→500 ("chunk hẹp hơn bắt ngữ nghĩa chính xác hơn") **đúng một phần nhưng có giới hạn** — hẹp
   hơn cho điểm cosine cao hơn thật (§2.1: 200/50 có cosine top-1 trung bình cao nhất), nhưng khi hẹp
   QUÁ, số lượng chunk tăng vọt (140 so với 33-53) khiến nhiều chunk "gần đúng chủ đề" cạnh tranh vị
   trí top-1 với đúng chunk cần tìm (Ví dụ D, §5) — điểm cao không đồng nghĩa với tìm đúng.
3. **Độ khó câu hỏi ảnh hưởng rõ hơn cả kích thước cửa sổ** (§2.2): 500/100 thắng ở câu hỏi trực diện
   (bám sát chữ nguồn); 850/170 thắng ở câu hỏi gián tiếp/diễn đạt lại VÀ ở câu dễ về Hit@3 trở lên;
   200/50 không thắng ở tình huống nào rõ rệt.
4. **Giả thuyết "chunk dài xé lẻ sự kiện" vẫn không phải cơ chế đang diễn ra** — `snippet_intact_rate`
   = 100% ở CẢ 3 cấu hình, cả 2 vòng câu hỏi (kể cả 200/50, cửa sổ hẹp nhất). Cơ chế thật là **ranh
   giới cắt khác nhau đưa các câu văn liền kề vào chung/tách khác chunk, và số lượng chunk cạnh tranh
   tăng khi cửa sổ hẹp** — không phải "xé lẻ thông tin".
5. **Không đủ căn cứ để khẳng định một cấu hình "tốt hơn hẳn" cấu hình khác.** Diễn đạt đúng mức độ
   bằng chứng: *"trên corpus + 100 câu hỏi đo được, 850/170 nhỉnh hơn ở hầu hết chỉ số nhưng chưa đạt
   ý nghĩa thống kê; 200/50 (hẹp hơn 500/100 từng dùng trước đây) rõ ràng KHÔNG phải hướng nên đi
   tiếp — bằng chứng nhất quán chỉ ra hẹp hơn không giúp gì, kể cả không có ý nghĩa thống kê ở từng
   cặp riêng lẻ."*
6. **Khuyến nghị thực tế — đã đo trực tiếp cả 2 rủi ro lý thuyết, kết quả nghiêng hẳn về 850/170:**
   Trước khi có §7, có 1 giả thuyết hợp lý ("850 rủi ro pha loãng đáp án ngắn nằm cuối chunk dài, nên
   500 an toàn hơn") — nhưng đó là suy luận **chưa đo**. Stress test §7 đo trực tiếp 1 rủi ro liên
   quan (ngữ cảnh cần thiết DÀI hơn 1 câu, kiểu câu trả lời thật của tài liệu HR/nội quy nhiều điều
   khoản) và kết quả **dứt khoát ngược lại giả thuyết đó**: 850/170 hoàn toàn miễn nhiễm (0% suy
   giảm), 500/100 chịu thiệt vừa phải (Hit@1 rớt ~5 điểm %), 200/50 sụp đổ (Hit@1 rớt hơn nửa). Rủi
   ro "pha loãng đáp án ngắn" vẫn CHƯA bị bác bỏ hoàn toàn (§7 đo rủi ro xé lẻ ngữ cảnh dài, không
   phải đúng kịch bản "đáp án ngắn lọt thỏm giữa nội dung dài không liên quan") — nhưng giữa 2 rủi ro
   lý thuyết, chỉ 1 cái được đo bằng số thật, và nó rất rõ ràng ủng hộ cửa sổ rộng hơn, không phải
   hẹp hơn.
   - Câu hỏi mở rộng corpus (đã thảo luận riêng, trước §7) cũng nghiêng cùng hướng: hẹp hơn → nhiều
     chunk hơn → nhiều distractor cạnh tranh hơn (bất lợi cho hẹp, đã thấy ở §2.1 với 200/50) — không
     có cơ chế nào đã đo được ủng hộ hẹp hơn khi corpus/văn bản lớn lên.
   - **Kết luận cập nhật: bằng chứng hiện có (cả benchmark 100 câu §2-§6 lẫn stress test §7) đều
     nghiêng về 850/170, không phải 500/100.** 850/170 thắng nhẹ (không ý nghĩa thống kê) trên
     benchmark chính, và thắng RÕ RỆT, DỨT KHOÁT trên stress test ngữ cảnh dài. 200/50 bị loại hoàn
     toàn ở cả 2 phép đo. Nếu phải chọn 1 trong 3 dựa trên toàn bộ dữ liệu đã thu thập, **850/170 là
     lựa chọn có căn cứ tốt nhất** — khuyến nghị này đảo ngược khuyến nghị "giữ 500/100" viết trước
     khi có §7, vì lúc đó chưa có số đo cho rủi ro xé lẻ ngữ cảnh dài.

## 9. Giới hạn

- **Định nghĩa "hit" coi 1 sự kiện là ATOMIC — phải nằm TRỌN trong 1 chunk duy nhất mới tính là tìm
  được, không cộng dồn thông tin từ nhiều chunk.** Vì các chiến lược cắt khác nhau tạo ra chunk_id
  hoàn toàn khác nhau (không có ánh xạ 1-1 giữa chunk của config A và config B), ground-truth không
  gắn vào 1 `chunk_id` cụ thể mà gắn vào `expected_snippet` — đoạn trích từ VĂN BẢN GỐC (chưa cắt).
  Với mỗi config, "hit" nghĩa là *"có ≥1 chunk của config đó chứa trọn snippet"*, đo độc lập cho từng
  config rồi mới so sánh — đây là cách duy nhất so được các chiến lược cắt khác nhau mà không cần
  ánh xạ chunk-với-chunk. Hệ quả: nếu 1 chiến lược nào đó xé sự kiện ra làm 2 (nửa câu ở chunk này,
  nửa câu ở chunk kế), benchmark chấm **miss hoàn toàn** — dù hệ thống thật đưa CẢ 2 chunk liền kề
  vào prompt, LLM vẫn có thể ghép đủ thông tin để trả lời đúng. Ở corpus này `snippet_intact_rate` =
  100% cho cả 3 cấu hình (§2.1) nên điểm mù này **không ảnh hưởng tới kết quả đã đo** — nhưng ở
  corpus khác có snippet/sự kiện dài hơn cửa sổ nhỏ nhất đang test, cách chấm nhị phân này sẽ đánh
  giá THẤP HƠN thực tế những config hay xé lẻ nhưng vẫn gom đủ thông tin trong top-k.
- **n=100 câu, 1 corpus 9 file, 1 lần chạy, 3 cấu hình** — đủ để phát hiện xu hướng và đủ để thấy
  200/50 nhất quán tệ hơn ở nhiều chỉ số, nhưng KHÔNG đủ để kết luận chắc chắn ở mức tin cậy cao
  (1-3 câu lệch mỗi cặp vẫn là cỡ mẫu quá nhỏ cho một kiểm định thống kê có ý nghĩa). Cần vài trăm
  câu và/hoặc nhiều corpus khác nhau để kết luận vững hơn.
- **Chỉ đo 3 điểm rời rạc (200/50, 500/100, 850/170), không phải đường cong liên tục** — không biết
  liệu 300/60, 650/130, hay các tổ hợp size/overlap khác có cho kết quả tốt hơn cả 3 điểm đã đo hay
  không. Xu hướng "850 > 500 > 200" gợi ý có thể còn tốt hơn ở kích thước lớn hơn 850, nhưng đây là
  suy diễn ngoại suy (extrapolation), CHƯA đo thật.
- **`expected_snippet` do LLM tự chọn** (dù đã verify verbatim) — kể cả ở vòng 2 (được yêu cầu khó
  hơn), LLM vẫn chỉ chọn trong không gian "câu hỏi nó nghĩ ra được", không đại diện đầy đủ cho MỌI
  loại câu hỏi người dùng thật có thể hỏi (câu hỏi tổng hợp nhiều đoạn/nhiều file, câu hỏi suy luận
  nhiều bước).
- **Không đo trên corpus lớn/đa dạng hơn** (chỉ 20.883 từ, 9 file cùng miền HR/nội quy) — chưa rõ xu
  hướng "850 thắng câu khó" có giữ nguyên trên corpus khác miền (kỹ thuật, pháp lý, hợp đồng dài...).
- **Không đo qua `PgKbSearch.search()` production thật** — đo trực tiếp bằng cosine offline (đúng
  công thức `1 - (embedding <=> vector)` cùng SQL thật dùng), không phải anti-pattern "giả lập sai
  công thức", nhưng vẫn là 1 script riêng, không phải chạy qua route HTTP thật.
- **`packages/kb/data/` đã bị gitignore** (theo yêu cầu trước) — ai khác clone repo sẽ KHÔNG tái lập
  được benchmark này nếu không có sẵn 9 file gốc cục bộ. Script (`evidence/scripts/`) tái lập được
  logic, nhưng dữ liệu đầu vào phải tự có.
- **"Khó hơn" ở vòng 2 là do 1 LLM tự đánh giá theo 4 tiêu chí trong prompt** (gián tiếp, chi tiết ẩn,
  trải rộng, có thể so sánh/điều kiện) — không có thước đo độ khó độc lập bên ngoài; bằng chứng gián
  tiếp rằng nó THỰC SỰ khó hơn là Hit@1 rơi từ ~75% (vòng 1) xuống ~46% (vòng 2) ở cả 2 cấu hình,
  nhất quán với chủ ý thiết kế.

## 10. Bằng chứng đầy đủ (`evidence/`)

- `scripts/01_extract.py` → `10_eval_long_snippet.py` — toàn bộ code chạy thật (2 vòng sinh câu hỏi
  + chunk/embed + đo retrieval + đo margin, cả 3 cấu hình + stress test snippet dài §7), chạy lại
  được nếu có sẵn `packages/kb/data/`.
- `long_snippet_results_200_50.json` / `long_snippet_results_500_100.json` /
  `long_snippet_results_850_170.json` / `long_snippet_summary.json` — dữ liệu stress test §7 (19
  câu, snippet kéo dài 150 từ), so `intact`/`hit@1`/`hit@5` giữa snippet ngắn gốc và snippet dài.
- `qa_set_100.json` — 100 câu hỏi + đáp án + snippet gốc (50 dễ + 50 khó), đã kiểm trùng lặp sạch,
  dùng chung cho cả 3 cấu hình.
- `retrieval_results_100q_200_50.json` / `retrieval_results_100q_500_100.json` /
  `retrieval_results_100q_850_170.json` — chi tiết top-5 từng câu (cả 100), từng chunk, điểm cosine,
  cờ hit (nguồn của bảng §6 và các ví dụ §5).
- `separation_detail_100q_200_50.json` / `separation_detail_100q_500_100.json` /
  `separation_detail_100q_850_170.json` — margin từng câu, cả 3 cấu hình.
- `retrieval_summary_100q.json` / `separation_summary_100q.json` — số tổng hợp §2/§3, cả 3 cấu hình.
- `qa_set_final.json`, `retrieval_results_500_100.json`, `retrieval_results_850_170.json`,
  `separation_detail_500_100.json`, `separation_detail_850_170.json`, `retrieval_summary.json`,
  `separation_summary.json` — **giữ lại từ lần đo chỉ-50-câu ban đầu** (chính là 50 câu "vòng 1"
  trong bộ 100 câu ở trên, không phải dữ liệu khác) — tham khảo nếu cần đối chiếu lại con số trước
  khi mở rộng.
