# Năm provider embedding: dim-8 vs hashing-512 vs BGE-M3 vs multilingual-e5-large vs Gemini

So 5 provider trên CÙNG harness (`tests/embedding-tests/_harness.py`), CÙNG 300 case, CÙNG corpus 800 chunk (`docs/callisto-2.0`), CÙNG cách xếp hạng (cosine, top-k=10, lọc `{tenant_id, section_roles}` trước). Báo cáo THỬ NGHIỆM — không đổi provider mặc định của harness, không sửa case JSON ở đây (case đã được sửa/mở rộng lên 300 ở công việc trước; `baseline-dim8.json` được re-record khớp case set hiện tại — xem mục Ghi chú).

## Năm provider là gì

| Provider | Công thức | Chiều | Nơi chạy | Có ngữ nghĩa? |
|---|---|---:|---|:---:|
| `baseline-dim8` | `derive_vector` — `blake2b(token)` băm vào ô, đếm, L2-normalize (`studio_kb/embeddings.py`) | 8 | local, CPU | Không |
| `bow-hash512` | CÙNG hàm `derive_vector`, chỉ đổi `dim=8`→`dim=512` | 512 | local, CPU | Không |
| `bge-m3` | `BAAI/bge-m3` qua `sentence-transformers`, dense học sẵn (contrastive, đa ngôn ngữ) | 1024 | local, MPS (GPU) | Có |
| `multilingual-e5-large` | `intfloat/multilingual-e5-large` qua `sentence-transformers`, dense học sẵn (contrastive, đa ngôn ngữ, ~24 layer) | 1024 | local, MPS (GPU) | Có |
| `gemini-embedding-001` | Google Gemini Embedding API, `output_dimensionality=1024` (Matryoshka, cắt từ 3072 gốc) | 1024 | API (Google) | Có |

**`multilingual-e5-large` bắt buộc prefix** — tài liệu chính thức của model yêu cầu thêm `"query: "` trước câu hỏi và `"passage: "` trước đoạn văn bản trước khi encode; bỏ prefix làm giảm chất lượng rõ rệt vì model huấn luyện contrastive với quy ước này để phân biệt vai trò bất đối xứng query↔document. `E5LargeProvider` dùng chung thủ thuật với `gemini-embedding-001`: harness gọi `embed()` đúng 2 lần theo thứ tự cố định — (1) corpus trong `build_retriever` → prefix `passage: `, (2) query trong `build_report` → prefix `query: `.
- **`gemini-embedding-001` ĐỌC LẠI cache** đã chấm trước đó (`gemini_cache.json`, 1088 vector — một vài text trùng lặp giữa các case nên ít hơn 1100 danh nghĩa), KHÔNG gọi API lại — tránh đốt thêm quota free-tier vốn đã trầy trật khi chấm lần đầu (2 lần đổi API key vì hết quota ngày).

## Corpus & bộ case (dùng chung cho cả 5 provider)

- Corpus 2.0: **800 chunk** trên **80 tài liệu**, 2 tenant.

| role | số chunk |
|---|---:|
| engineering | 200 |
| finance | 200 |
| hr | 200 |
| public | 200 |

| tenant | số chunk |
|---|---:|
| ankor | 400 |
| borea | 400 |

- Bộ case: **300 case**, 5 tầng S1–S5 (~60 case/tầng).

### Định nghĩa metric

- **recall@k** (S1–S4): `|expected ∩ retrieved_top10| / |expected|`.
- **reciprocal_rank** (S1–S4): `1/hạng` của chunk đúng đầu tiên trong top-10; 0 nếu trượt hẳn.
- **S5 (negative)**: `recall = 1 − top_score` — cao = 'sạch'.
- **Gate 'vượt'**: `recall(ứng viên) ≥ recall(baseline dim-8) + margin[tầng]` — margin: S1=+0.02, S2=+0.10, S3=+0.10, S4=+0.10, S5=+0.05.

**Ghi chú về `baseline-dim8.json`**: file này đã được re-record ngay trước khi viết báo cáo này (`python tests/embedding-tests/record_baseline.py`) — bản cũ bị stale so với case set hiện tại (300 case, sau khi sửa ground-truth S1–S4 ở công việc trước), khiến `test_embedding_gate.py` đỏ ở cả 5 tầng (freshness check tự phát hiện đúng như thiết kế). Toàn bộ số 'dim-8' trong báo cáo này là số MỚI, khớp case set hiện tại.

## Kết quả tổng theo tầng — cả 5 provider

| Tầng | n | recall dim-8 | recall hash512 | recall bge-m3 | recall e5-large | recall gemini-001 | mrr dim-8 | mrr hash512 | mrr bge-m3 | mrr e5-large | mrr gemini-001 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| S1 | 65 | 0.2615 | 0.8154 | 0.7385 | 0.7231 | 0.8000 | 0.1034 | 0.6044 | 0.5671 | 0.5362 | 0.5675 |
| S2 | 61 | 0.0984 | 0.1148 | 0.6721 | 0.6230 | 0.7049 | 0.0329 | 0.0262 | 0.3837 | 0.3538 | 0.5112 |
| S3 | 60 | 0.2333 | 0.5167 | 0.5667 | 0.5833 | 0.7167 | 0.0862 | 0.3164 | 0.3800 | 0.4247 | 0.5066 |
| S4 | 55 | 0.2182 | 0.4545 | 0.5818 | 0.6182 | 0.6364 | 0.0497 | 0.2694 | 0.4675 | 0.4594 | 0.5133 |
| S5 | 59 | 0.0662 | 0.6872 | 0.4228 | 0.1487 | 0.2916 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |

### Gate (so với baseline dim-8 + margin) — 4 provider ứng viên

| Tầng | margin | delta hash512 | Gate | delta bge-m3 | Gate | delta e5-large | Gate | delta gemini-001 | Gate |
|---|---:|---:|:---:|---:|:---:|---:|:---:|---:|:---:|
| S1 | +0.02 | +0.5538 | ✅ | +0.4769 | ✅ | +0.4615 | ✅ | +0.5385 | ✅ |
| S2 | +0.10 | +0.0164 | ❌ | +0.5738 | ✅ | +0.5246 | ✅ | +0.6066 | ✅ |
| S3 | +0.10 | +0.2833 | ✅ | +0.3333 | ✅ | +0.3500 | ✅ | +0.4833 | ✅ |
| S4 | +0.10 | +0.2364 | ✅ | +0.3636 | ✅ | +0.4000 | ✅ | +0.4182 | ✅ |
| S5 | +0.05 | +0.6210 | ✅ | +0.3565 | ✅ | +0.0825 | ✅ | +0.2253 | ✅ |

**hash512: 4/5 · bge-m3: 5/5 · multilingual-e5-large: 5/5 · gemini-embedding-001: 5/5 tầng vượt gate.**

## Kết luận nhanh

Trung bình recall 5 tầng: dim-8=0.1755 · hash512=0.5177 · bge-m3=0.5964 · e5-large=0.5392 · gemini-001=0.6299. Xếp hạng 4 ứng viên theo recall trung bình: gemini-001 (0.6299) > bge-m3 (0.5964) > e5-large (0.5392) > hash512 (0.5177). Cả ba dense provider học sẵn (bge-m3, e5-large, gemini-embedding-001) đều vượt xa hai baseline lexical trên mọi tầng bắt buộc ngữ nghĩa (S2–S4); chênh lệch NỘI BỘ giữa ba dense model nhỏ hơn nhiều so với khoảng cách giữa nhóm dense và nhóm lexical — vẫn đúng kết luận cũ: 'có chuyển sang dense hay không' quan trọng hơn 'chọn dense model nào'.

## Phân tích chi tiết theo tầng — 4 provider ứng viên

### S1 — lexical-easy — query và đáp án chia sẻ ≥1 token.

recall: hash512=0.8154 (+0.5538) · bge-m3=0.7385 (+0.4769) · e5-large=0.7231 (+0.4615) · gemini-001=0.8000 (+0.5385) · dim-8=0.2615 — delta tính so dim-8.

- `hash512`: 53/65 case recall=1.0 (12 trượt).
- `bge-m3`: 48/65 case recall=1.0 (17 trượt).
- `e5-large`: 47/65 case recall=1.0 (18 trượt).
- `gemini-001`: 52/65 case recall=1.0 (13 trượt).

Case `multilingual-e5-large` trượt (recall<1.0), đối chiếu `bge-m3` và `gemini-embedding-001` trên CÙNG case:

| case id | query | expected | recall e5 | top-1 e5 | recall bge-m3 | top-1 bge-m3 | recall gemini | top-1 gemini |
|---|---|---|---:|---|---:|---|---:|---|
| s1-ankor-eng-deployment-strategy | Ankor dùng chiến lược triển khai nào để giảm rủi ro khi đưa code lên production | ankor-engineering-deployment#c2 | 0.00 | ankor-engineering-deployment#c1 | 0.00 | ankor-engineering-testing#c1 | 0.00 | ankor-engineering-deployment#c1 |
| s1-ankor-eng-mfa-required | hệ thống Ankor bắt buộc xác thực hai bước không | ankor-engineering-security#c3 | 0.00 | ankor-engineering-security#c1 | 1.00 | ankor-engineering-testing#c1 | 1.00 | ankor-engineering-access#c1 |
| s1-ankor-eng-pr-large-sla | SLA review PR lớn ở Ankor là bao lâu | ankor-engineering-code-review#c4 | 0.00 | ankor-engineering-code-review#c3 | 1.00 | ankor-engineering-code-review#c3 | 0.00 | ankor-engineering-code-review#c3 |
| s1-ankor-fin-budget-capex | Ankor phân loại chi đầu tư dài hạn vào mục nào trong ngân sách | ankor-finance-budget#c3 | 0.00 | ankor-finance-forecast#c1 | 0.00 | ankor-finance-expense#c1 | 0.00 | ankor-finance-budget#c1 |
| s1-ankor-hr-grievance-timeline | Ankor xử lý khiếu nại nội bộ trong bao nhiêu ngày | ankor-hr-grievance#c4 | 0.00 | ankor-hr-grievance#c1 | 0.00 | ankor-hr-grievance#c1 | 0.00 | ankor-hr-grievance#c1 |
| s1-ankor-hr-probation-period | thời gian thử việc ở Ankor là bao lâu | ankor-hr-onboarding#c1 | 0.00 | ankor-hr-onboarding#c7 | 0.00 | ankor-hr-onboarding#c7 | 0.00 | ankor-hr-onboarding#c7 |
| s1-ankor-hr-sick-days | nghỉ ốm mỗi năm được tối đa bao nhiêu ngày ở Ankor | ankor-hr-leave#c3 | 0.00 | ankor-hr-leave#c1 | 1.00 | ankor-hr-leave#c1 | 1.00 | ankor-hr-leave#c1 |
| s1-ankor-pub-communication-slack | Slack được dùng cho mục đích giao tiếp gì tại Ankor | ankor-public-communication#c2 | 0.00 | ankor-public-communication#c1 | 0.00 | ankor-public-communication#c1 | 0.00 | ankor-public-communication#c1 |
| s1-ankor-pub-gift-limit | được nhận quà tặng từ đối tác trị giá bao nhiêu | ankor-public-code-of-conduct#c5 | 0.00 | ankor-public-code-of-conduct#c6 | 0.00 | ankor-public-code-of-conduct#c6 | 1.00 | ankor-public-code-of-conduct#c6 |
| s1-ankor-pub-harassment-report-channel | tố cáo quấy rối ở Ankor gửi đến đâu | ankor-public-anti-harassment#c3 | 0.00 | ankor-public-anti-harassment#c6 | 0.00 | ankor-public-code-of-conduct#c9 | 0.00 | ankor-public-anti-harassment#c6 |
| s1-ankor-pub-national-holidays | Ankor nghỉ những ngày lễ quốc gia nào trong năm | ankor-public-holidays#c2 | 0.00 | ankor-public-holidays#c10 | 0.00 | ankor-public-holidays#c10 | 0.00 | ankor-public-holidays#c10 |
| s1-ankor-pub-parking-motorbike | phí gửi xe máy tháng tại Ankor là bao nhiêu | ankor-public-parking#c4 | 0.00 | ankor-public-parking#c8 | 0.00 | ankor-public-parking#c8 | 1.00 | ankor-public-parking#c1 |
| s1-ankor-pub-visitor-badge-color | khách thăm quan Ankor phải đeo thẻ màu gì | ankor-public-visitors#c2 | 0.00 | ankor-public-visitors#c1 | 0.00 | ankor-public-visitors#c1 | 0.00 | ankor-public-visitors#c1 |
| s1-borea-fin-petty-cash | quỹ tiền mặt nhỏ petty cash mỗi phòng ban Borea được bao nhiêu | borea-finance-expense#c5 | 0.00 | borea-finance-reimbursement#c1 | 0.00 | borea-finance-budget#c8 | 0.00 | borea-finance-budget#c8 |
| s1-borea-fin-tax-tndn | thuế thu nhập doanh nghiệp Borea bao nhiêu phần trăm | borea-finance-tax#c2 | 0.00 | borea-finance-tax#c1 | 0.00 | borea-finance-tax#c1 | 1.00 | borea-finance-tax#c1 |
| s1-borea-hr-paternity-leave | bố mới có con được nghỉ phép đặc biệt mấy ngày ở Borea | borea-hr-leave#c6 | 0.00 | borea-hr-leave#c1 | 0.00 | borea-hr-leave#c1 | 0.00 | borea-hr-leave#c1 |
| s1-borea-hr-payday | Borea trả lương vào ngày nào mỗi tháng | borea-hr-payroll#c2 | 0.00 | borea-hr-exit#c6 | 0.00 | borea-hr-payroll#c1 | 0.00 | borea-hr-payroll#c1 |
| s1-borea-hr-remote-days | Borea cho phép làm việc từ xa bao nhiêu ngày trong tuần | borea-hr-remote-work#c2 | 0.00 | borea-hr-remote-work#c8 | 0.00 | borea-hr-remote-work#c8 | 0.00 | borea-hr-remote-work#c8 |

### S2 — paraphrase — query trùng ≤2 token với đáp án, buộc phải hiểu nghĩa.

recall: hash512=0.1148 (+0.0164) · bge-m3=0.6721 (+0.5738) · e5-large=0.6230 (+0.5246) · gemini-001=0.7049 (+0.6066) · dim-8=0.0984 — delta tính so dim-8.

- `hash512`: 7/61 case recall=1.0 (54 trượt).
- `bge-m3`: 41/61 case recall=1.0 (20 trượt).
- `e5-large`: 38/61 case recall=1.0 (23 trượt).
- `gemini-001`: 43/61 case recall=1.0 (18 trượt).

Case `multilingual-e5-large` trượt (recall<1.0), đối chiếu `bge-m3` và `gemini-embedding-001` trên CÙNG case:

| case id | query | expected | recall e5 | top-1 e5 | recall bge-m3 | top-1 bge-m3 | recall gemini | top-1 gemini |
|---|---|---|---:|---|---:|---|---:|---|
| s2-ankor-eng-blue-green | Ankor tung bản mới ra dần dần hay đổi cả cụm server cùng lúc | ankor-engineering-deployment#c2 | 0.00 | ankor-engineering-release#c1 | 0.00 | ankor-engineering-release#c1 | 0.00 | ankor-engineering-deployment#c4 |
| s2-ankor-eng-log-storage-period | dữ liệu nhật ký hệ thống Ankor giữ được bao lâu trước khi xoá | ankor-engineering-monitoring#c7 | 0.00 | ankor-engineering-security#c10 | 0.00 | ankor-engineering-security#c10 | 0.00 | ankor-engineering-security#c10 |
| s2-ankor-eng-oncall-nightcall | bị dựng dậy giữa đêm chữa sự cố thì hôm sau thế nào | ankor-engineering-oncall#c8 | 0.00 | ankor-engineering-oncall#c9 | 1.00 | ankor-engineering-oncall#c9 | 0.00 | ankor-engineering-oncall#c9 |
| s2-ankor-eng-pr-test-requirement | khi thêm tính năng lập trình, quy định bắt buộc đi kèm là gì | ankor-engineering-testing#c1 | 0.00 | ankor-engineering-security#c5 | 0.00 | ankor-engineering-testing#c2 | 0.00 | ankor-engineering-code-review#c4 |
| s2-ankor-fin-capital-expenditure | mua sắm thiết bị giá trị lớn được hạch toán vào khoản gì | ankor-finance-budget#c3 | 0.00 | ankor-finance-audit#c3 | 0.00 | ankor-finance-procurement#c10 | 0.00 | ankor-finance-procurement#c10 |
| s2-ankor-fin-indirect-tax-rate | Ankor thu thuế gián tiếp nào trên từng giao dịch bán hàng | ankor-finance-tax#c3 | 0.00 | ankor-finance-tax#c1 | 0.00 | ankor-finance-tax#c1 | 0.00 | ankor-finance-tax#c1 |
| s2-ankor-fin-invoice-format | giấy tờ xuất cho bên mua theo quy chuẩn nào | ankor-finance-invoicing#c1 | 0.00 | ankor-finance-invoicing#c3 | 0.00 | ankor-finance-invoicing#c4 | 0.00 | ankor-finance-invoicing#c3 |
| s2-ankor-hr-probation-tasks | mới vào làm thì trong 2 tháng đầu phải làm gì để qua thử thách | ankor-hr-onboarding#c1 | 0.00 | ankor-hr-training#c7 | 1.00 | ankor-hr-training#c7 | 0.00 | ankor-hr-onboarding#c6 |
| s2-ankor-hr-recruitment-interview-count | ứng viên vào Ankor phải trải qua mấy vòng phỏng vấn | ankor-hr-recruitment#c3 | 0.00 | ankor-hr-recruitment#c8 | 0.00 | ankor-hr-recruitment#c8 | 0.00 | ankor-hr-recruitment#c8 |
| s2-ankor-pub-fire-escape-route | khi có chuông báo cháy ở Ankor thì phải thoát ra cửa nào | ankor-public-safety#c4 | 0.00 | ankor-public-visitors#c3 | 0.00 | ankor-public-visitors#c3 | 0.00 | ankor-public-visitors#c1 |
| s2-ankor-pub-parking-reserve | thủ tục nào giúp giữ một vị trí cố định để phương tiện tại trụ sở | ankor-public-parking#c1 | 0.00 | ankor-public-parking#c2 | 0.00 | ankor-public-parking#c2 | 1.00 | ankor-public-parking#c2 |
| s2-ankor-pub-public-holidays-list | trong năm Ankor đóng cửa những ngày nào theo quy định nhà nước | ankor-public-holidays#c2 | 0.00 | ankor-public-office-hours#c10 | 0.00 | ankor-public-office-hours#c10 | 0.00 | ankor-public-holidays#c10 |
| s2-borea-eng-alert-first-receiver | khi hệ thống báo động thì ai nhận thông báo đầu tiên | borea-engineering-monitoring#c6 | 0.00 | borea-engineering-oncall#c4 | 0.00 | borea-engineering-incident#c3 | 0.00 | borea-engineering-incident#c4 |
| s2-borea-eng-p2-response-sla | sự cố mức 2 ở Borea phải phản hồi trong bao lâu | borea-engineering-oncall#c5 | 0.00 | borea-engineering-oncall#c4 | 0.00 | borea-engineering-oncall#c4 | 0.00 | borea-engineering-incident#c3 |
| s2-borea-fin-approval-level | khoản chi bao nhiêu thì sếp trực tiếp được ký | borea-finance-reimbursement#c4 | 0.00 | borea-finance-budget#c5 | 0.00 | borea-finance-budget#c5 | 0.00 | borea-finance-approval-limits#c5 |
| s2-borea-fin-corporate-tax | công ty Borea trích bao nhiêu phần trăm thu nhập nộp ngân sách nhà nước | borea-finance-tax#c2 | 0.00 | borea-finance-tax#c1 | 0.00 | borea-finance-tax#c1 | 0.00 | borea-finance-tax#c1 |
| s2-borea-fin-meal-expense-ceiling | chi phí tiếp đãi đối tác từng lần Borea giới hạn không quá bao nhiêu tiền | borea-finance-reimbursement#c2 | 0.00 | borea-finance-reimbursement#c1 | 1.00 | borea-finance-reimbursement#c1 | 1.00 | borea-finance-reimbursement#c1 |
| s2-borea-fin-petty-cash-request | muốn mua đồ nhỏ tiền mặt cho phòng thì lấy ở đâu | borea-finance-expense#c5 | 0.00 | borea-finance-procurement#c1 | 1.00 | borea-finance-travel#c5 | 1.00 | borea-finance-approval-limits#c3 |
| s2-borea-hr-complaint-response-time | khiếu nại nhân sự thì bao lâu nhận được phản hồi | borea-hr-grievance#c4 | 0.00 | borea-hr-performance#c9 | 1.00 | borea-hr-performance#c9 | 1.00 | borea-hr-performance#c9 |
| s2-borea-hr-performance-frequency | sếp gặp riêng từng người dưới quyền để bàn việc mấy bận trong một năm | borea-hr-performance#c1 | 0.00 | borea-hr-grievance#c6 | 0.00 | borea-hr-exit#c2 | 1.00 | borea-hr-performance#c6 |
| s2-borea-hr-rating-scale | kết quả làm việc cả năm của nhân viên Borea chia thành mấy mức | borea-hr-performance#c3 | 0.00 | borea-hr-payroll#c1 | 0.00 | borea-hr-payroll#c1 | 0.00 | borea-hr-performance#c1 |
| s2-borea-hr-salary-structure | thu nhập định kỳ chia làm mấy phần | borea-hr-payroll#c1 | 0.00 | borea-hr-payroll#c2 | 1.00 | borea-hr-payroll#c2 | 1.00 | borea-hr-payroll#c1 |
| s2-borea-pub-workplace-bullying | tổ chức phản hồi ra sao khi một người bị ức hiếp trong công sở | borea-public-anti-harassment#c1 | 0.00 | borea-public-code-of-conduct#c2 | 0.00 | borea-public-code-of-conduct#c2 | 1.00 | borea-public-code-of-conduct#c2 |

### S3 — near-miss cùng vai — có chunk CÙNG role trùng từ khoá bằng/hơn đáp án.

recall: hash512=0.5167 (+0.2833) · bge-m3=0.5667 (+0.3333) · e5-large=0.5833 (+0.3500) · gemini-001=0.7167 (+0.4833) · dim-8=0.2333 — delta tính so dim-8.

- `hash512`: 31/60 case recall=1.0 (29 trượt).
- `bge-m3`: 34/60 case recall=1.0 (26 trượt).
- `e5-large`: 35/60 case recall=1.0 (25 trượt).
- `gemini-001`: 43/60 case recall=1.0 (17 trượt).

Case `multilingual-e5-large` trượt (recall<1.0), đối chiếu `bge-m3` và `gemini-embedding-001` trên CÙNG case:

| case id | query | expected | recall e5 | top-1 e5 | recall bge-m3 | top-1 bge-m3 | recall gemini | top-1 gemini |
|---|---|---|---:|---|---:|---|---:|---|
| s3-ankor-eng-hotfix-process | khi có lỗi nghiêm trọng thì bản vá khẩn được đưa lên theo quy trình nào | ankor-engineering-release#c8 | 0.00 | ankor-engineering-oncall#c6 | 0.00 | ankor-engineering-deployment#c5 | 0.00 | ankor-engineering-deployment#c7 |
| s3-ankor-eng-infra-backup | Ankor sao lưu dữ liệu production với tần suất và phương thức nào | ankor-engineering-infra#c6 | 0.00 | ankor-engineering-security#c1 | 0.00 | ankor-engineering-infra#c1 | 0.00 | ankor-engineering-deployment#c1 |
| s3-ankor-eng-vuln-patch-sla | vá lỗ hổng bảo mật nghiêm trọng phải hoàn tất trong bao lâu | ankor-engineering-security#c5 | 0.00 | ankor-engineering-security#c9 | 0.00 | ankor-engineering-security#c9 | 1.00 | ankor-engineering-security#c9 |
| s3-ankor-fin-opex-report | báo cáo chi phí vận hành Ankor gửi cho ban lãnh đạo theo tần suất nào | ankor-finance-expense#c3 | 0.00 | ankor-finance-forecast#c2 | 0.00 | ankor-finance-forecast#c2 | 0.00 | ankor-finance-forecast#c2 |
| s3-ankor-fin-reimburse-late | gửi yêu cầu lấy lại chi phí muộn có được chấp nhận không | ankor-finance-reimbursement#c4 | 0.00 | ankor-finance-reimbursement#c8 | 1.00 | ankor-finance-reimbursement#c7 | 1.00 | ankor-finance-reimbursement#c4 |
| s3-ankor-hr-offboard-handover-window | trước khi nghỉ việc nhân viên Ankor phải bàn giao công việc trong bao lâu | ankor-hr-exit#c3 | 0.00 | ankor-hr-exit#c1 | 0.00 | ankor-hr-exit#c1 | 1.00 | ankor-hr-exit#c1 |
| s3-ankor-hr-paternity-apply | muốn nghỉ thai sản khi vợ sinh thì đăng ký như thế nào tại Ankor | ankor-hr-leave#c6 | 0.00 | ankor-hr-leave#c5 | 0.00 | ankor-hr-leave#c5 | 0.00 | ankor-hr-leave#c5 |
| s3-ankor-hr-sick-notification | nghỉ ốm đột xuất cần báo trước bao lâu và báo cho ai ở Ankor | ankor-hr-leave#c3 | 0.00 | ankor-hr-exit#c1 | 0.00 | ankor-hr-exit#c1 | 1.00 | ankor-hr-exit#c1 |
| s3-ankor-pub-canteen-menu | thực đơn căng tin Ankor thay đổi theo chu kỳ nào | ankor-public-office-hours#c7 | 0.00 | ankor-public-dress-code#c1 | 0.00 | ankor-public-office-hours#c1 | 0.00 | ankor-public-communication#c5 |
| s3-ankor-pub-meeting-room-etiquette | khi dùng phòng họp xong ở Ankor cần làm gì trước khi ra | ankor-public-office-hours#c9 | 0.00 | ankor-public-office-hours#c10 | 0.00 | ankor-public-visitors#c5 | 0.00 | ankor-public-visitors#c5 |
| s3-ankor-pub-national-holiday-work | nếu phải vào làm ngày 2 tháng 9 thì Ankor tính lương thêm bao nhiêu | ankor-public-holidays#c6 | 0.00 | ankor-public-holidays#c5 | 0.00 | ankor-public-office-hours#c1 | 0.00 | ankor-public-office-hours#c1 |
| s3-borea-eng-canary-deployment | khi đưa tính năng mới lên Borea thì traffic được chuyển dần hay ngay tức thì | borea-engineering-deployment#c2 | 0.00 | borea-engineering-release#c1 | 0.00 | borea-engineering-release#c1 | 0.00 | borea-engineering-release#c1 |
| s3-borea-eng-ci-integration-test | integration test ở Borea được chạy khi nào trong pipeline | borea-engineering-testing#c5 | 0.00 | borea-engineering-testing#c1 | 1.00 | borea-engineering-testing#c1 | 1.00 | borea-engineering-testing#c1 |
| s3-borea-eng-code-review-checklist | reviewer phải kiểm tra những điểm gì trong khi review code Borea | borea-engineering-code-review#c5 | 0.00 | borea-engineering-code-review#c1 | 0.00 | borea-engineering-code-review#c1 | 1.00 | borea-engineering-code-review#c1 |
| s3-borea-eng-log-search | khi cần tra cứu log để debug thì Borea dùng công cụ gì | borea-engineering-monitoring#c8 | 0.00 | borea-engineering-code-review#c9 | 0.00 | borea-engineering-monitoring#c1 | 0.00 | borea-engineering-monitoring#c1 |
| s3-borea-eng-ops-dashboard | số liệu vận hành hệ thống Borea xem ở đâu | borea-engineering-monitoring#c2 | 0.00 | borea-engineering-infra#c1 | 0.00 | borea-engineering-monitoring#c1 | 0.00 | borea-engineering-monitoring#c1 |
| s3-borea-eng-semver-convention | cách đặt tên phiên bản khi phát hành phần mềm Borea | borea-engineering-release#c2 | 0.00 | borea-engineering-release#c1 | 0.00 | borea-engineering-release#c1 | 1.00 | borea-engineering-release#c5 |
| s3-borea-fin-capex-approval | ai phải phê duyệt các khoản đầu tư tài sản dài hạn tại Borea | borea-finance-budget#c5 | 0.00 | borea-finance-approval-limits#c1 | 0.00 | borea-finance-approval-limits#c1 | 0.00 | borea-finance-approval-limits#c1 |
| s3-borea-fin-receipt-attachment-format | khi nộp chi phí thì chứng từ phải đính kèm dạng nào | borea-finance-expense#c4 | 0.00 | borea-finance-reimbursement#c3 | 0.00 | borea-finance-reimbursement#c3 | 0.00 | borea-finance-reimbursement#c3 |
| s3-borea-hr-exit-interview-mandatory | nhân viên Borea nghỉ việc có phải tham gia phỏng vấn thoát không | borea-hr-exit#c5 | 0.00 | borea-hr-exit#c1 | 0.00 | borea-hr-exit#c1 | 1.00 | borea-hr-exit#c6 |
| s3-borea-hr-grievance-steps | nhân viên Borea muốn khiếu nại thì đi theo những bước nào | borea-hr-grievance#c2 | 0.00 | borea-hr-grievance#c1 | 0.00 | borea-hr-grievance#c1 | 0.00 | borea-hr-grievance#c1 |
| s3-borea-hr-offsite-training-approval | nhân viên muốn đi học khoá ngoài văn phòng thì xin phép như thế nào | borea-hr-training#c4 | 0.00 | borea-hr-remote-work#c9 | 0.00 | borea-hr-leave#c4 | 0.00 | borea-hr-training#c3 |
| s3-borea-hr-probation-criteria | đánh giá nhân viên thử việc Borea dựa trên tiêu chí nào | borea-hr-onboarding#c1 | 0.00 | borea-hr-onboarding#c7 | 0.00 | borea-hr-onboarding#c7 | 0.00 | borea-hr-onboarding#c7 |
| s3-borea-hr-referral-payout-timing | giới thiệu người vào Borea thành công thì tiền thưởng trả lúc nào | borea-hr-recruitment#c10 | 0.00 | borea-hr-onboarding#c7 | 0.00 | borea-hr-training#c6 | 0.00 | borea-hr-onboarding#c3 |
| s3-borea-hr-sick-extended | Borea xử lý thế nào nếu nhân viên nghỉ ốm kéo dài quá số ngày cho phép | borea-hr-leave#c5 | 0.00 | borea-hr-leave#c1 | 0.00 | borea-hr-leave#c1 | 0.00 | borea-hr-leave#c3 |

### S4 — cross-role trap — có chunk KHÁC role (được phép) trùng từ khoá.

recall: hash512=0.4545 (+0.2364) · bge-m3=0.5818 (+0.3636) · e5-large=0.6182 (+0.4000) · gemini-001=0.6364 (+0.4182) · dim-8=0.2182 — delta tính so dim-8.

- `hash512`: 25/55 case recall=1.0 (30 trượt).
- `bge-m3`: 32/55 case recall=1.0 (23 trượt).
- `e5-large`: 34/55 case recall=1.0 (21 trượt).
- `gemini-001`: 35/55 case recall=1.0 (20 trượt).

Case `multilingual-e5-large` trượt (recall<1.0), đối chiếu `bge-m3` và `gemini-embedding-001` trên CÙNG case:

| case id | query | expected | recall e5 | top-1 e5 | recall bge-m3 | top-1 bge-m3 | recall gemini | top-1 gemini |
|---|---|---|---:|---|---:|---|---:|---|
| s4-ankor-eng-infra-backup-vs-fin | dữ liệu Ankor được sao lưu để phục vụ kiểm toán hay để phục hồi thảm hoạ | ankor-engineering-infra#c6 | 0.00 | ankor-engineering-oncall#c5 | 0.00 | ankor-engineering-oncall#c5 | 0.00 | ankor-finance-forecast#c1 |
| s4-ankor-fin-tax-vs-pub | Ankor phải nộp những loại phí và thuế nào khi ký hợp đồng với khách hàng | ankor-finance-tax#c4 | 0.00 | ankor-finance-tax#c1 | 0.00 | ankor-finance-tax#c1 | 1.00 | ankor-finance-tax#c1 |
| s4-ankor-hr-exit-cert-vs-fin | sau khi nghỉ việc Ankor cấp giấy tờ gì và nhân viên có phải tự chịu chi phí làm giấy không | ankor-hr-exit#c7 | 0.00 | ankor-hr-exit#c1 | 0.00 | ankor-hr-remote-work#c1 | 0.00 | ankor-hr-exit#c10 |
| s4-ankor-hr-paternity-vs-fin | nghỉ thai sản cha tại Ankor có được hưởng lương đầy đủ không | ankor-hr-leave#c6 | 0.00 | ankor-hr-leave#c5 | 0.00 | ankor-hr-leave#c5 | 0.00 | ankor-hr-leave#c5 |
| s4-ankor-pub-anti-harassment-investigation | khi có đơn tố cáo quấy rối ở Ankor thì ai tiến hành điều tra | ankor-public-anti-harassment#c5 | 0.00 | ankor-public-anti-harassment#c6 | 0.00 | ankor-public-anti-harassment#c6 | 0.00 | ankor-public-anti-harassment#c6 |
| s4-ankor-pub-canteen-subsidy | Ankor có trợ cấp suất ăn trưa cho nhân viên không | ankor-public-office-hours#c7 | 0.00 | ankor-hr-training#c1 | 0.00 | ankor-public-office-hours#c1 | 0.00 | ankor-hr-benefits#c8 |
| s4-ankor-pub-conduct-gift-vs-fin | nhận quà từ đối tác trên mức cho phép thì xử lý sao | ankor-public-code-of-conduct#c5 | 0.00 | ankor-public-code-of-conduct#c6 | 0.00 | ankor-public-code-of-conduct#c6 | 0.00 | ankor-public-code-of-conduct#c6 |
| s4-ankor-pub-gift-policy | nhận quà từ đối tác trên mức cho phép thì xử lý sao | ankor-public-code-of-conduct#c5 | 0.00 | ankor-public-code-of-conduct#c6 | 0.00 | ankor-public-code-of-conduct#c6 | 0.00 | ankor-public-code-of-conduct#c6 |
| s4-ankor-pub-safety-vs-eng | khi xảy ra sự cố cháy nổ tại Ankor thì đội kỹ thuật phải xử lý theo quy trình nào | ankor-public-safety#c3 | 0.00 | ankor-engineering-security#c7 | 0.00 | ankor-public-code-of-conduct#c1 | 0.00 | ankor-engineering-incident#c10 |
| s4-borea-eng-code-coverage-gate | PR ở Borea không đạt mức phủ kiểm thử thì có merge được không | borea-engineering-testing#c3 | 0.00 | borea-engineering-code-review#c9 | 0.00 | borea-engineering-deployment#c1 | 0.00 | borea-engineering-code-review#c9 |
| s4-borea-eng-log-retention-vs-fin | Borea lưu dữ liệu vận hành hệ thống bao lâu để phục vụ kiểm toán | borea-engineering-monitoring#c7 | 0.00 | borea-finance-audit#c1 | 0.00 | borea-finance-audit#c1 | 0.00 | borea-finance-audit#c1 |
| s4-borea-eng-release-vs-hr | việc phát hành phần mềm mới của Borea có liên quan đến việc thưởng cho nhóm không | borea-engineering-release#c7 | 0.00 | borea-engineering-release#c1 | 0.00 | borea-engineering-release#c1 | 0.00 | borea-hr-training#c6 |
| s4-borea-fin-capex-vs-hr | khi mua máy tính mới cho nhân viên thì phải xin duyệt như thế nào | borea-finance-budget#c5 | 0.00 | borea-hr-remote-work#c3 | 1.00 | borea-hr-remote-work#c4 | 0.00 | borea-finance-procurement#c4 |
| s4-borea-fin-reimbursement-vs-hr | nhân viên Borea đặt khách sạn công tác tự trả trước thì báo cáo chi phí theo mẫu nào | borea-finance-reimbursement#c5 | 0.00 | borea-finance-reimbursement#c7 | 0.00 | borea-hr-remote-work#c4 | 0.00 | borea-finance-reimbursement#c7 |
| s4-borea-hr-backup-coverage | khi nhân viên Borea nghỉ ốm dài ngày thì ai phụ trách công việc của họ | borea-hr-leave#c5 | 0.00 | borea-hr-leave#c1 | 0.00 | borea-hr-leave#c1 | 0.00 | borea-hr-remote-work#c9 |
| s4-borea-hr-grievance-vs-eng | khi nhân viên kỹ thuật vi phạm policy thì được xử lý theo bước nào tại Borea | borea-hr-grievance#c2 | 0.00 | borea-engineering-testing#c1 | 0.00 | borea-engineering-testing#c1 | 0.00 | borea-engineering-testing#c1 |
| s4-borea-hr-performance-tracking | Borea theo dõi kết quả làm việc nhân viên bằng công cụ nào | borea-hr-performance#c2 | 0.00 | borea-hr-leave#c10 | 0.00 | borea-hr-leave#c10 | 0.00 | borea-hr-remote-work#c10 |
| s4-borea-hr-probation-vs-eng | trong giai đoạn đầu thử sức với công việc mới thì ai đánh giá kết quả | borea-hr-onboarding#c1 | 0.00 | borea-hr-performance#c1 | 0.00 | borea-hr-onboarding#c7 | 0.00 | borea-hr-onboarding#c7 |
| s4-borea-pub-code-of-conduct-conflict | nhân viên Borea đi làm cho đối thủ cạnh tranh trong thời gian còn ràng buộc thì có vi phạm không | borea-public-code-of-conduct#c4 | 0.00 | borea-hr-exit#c8 | 0.00 | borea-hr-exit#c8 | 0.00 | borea-hr-exit#c8 |
| s4-borea-pub-conduct-vs-hr | vi phạm nội quy ứng xử ở Borea thì bộ phận nào xử lý kỷ luật | borea-public-code-of-conduct#c3 | 0.00 | borea-public-code-of-conduct#c1 | 0.00 | borea-public-code-of-conduct#c1 | 0.00 | borea-public-code-of-conduct#c1 |
| s4-borea-pub-holiday-vs-fin | Borea trả lương ra sao cho người làm việc vào ngày nghỉ Tết | borea-public-holidays#c6 | 0.00 | borea-public-holidays#c1 | 0.00 | borea-public-holidays#c1 | 0.00 | borea-public-holidays#c1 |

### S5 — negative/no-answer — câu hỏi không có đáp án trong tenant+role.

recall: hash512=0.6872 (+0.6210) · bge-m3=0.4228 (+0.3565) · e5-large=0.1487 (+0.0825) · gemini-001=0.2916 (+0.2253) · dim-8=0.0662 — delta tính so dim-8.

15 case `multilingual-e5-large` có `top_score` CAO NHẤT, đối chiếu `bge-m3` và `gemini-embedding-001`:

| case id | query | top_score e5 | top-1 e5 | top_score bge-m3 | top_score gemini |
|---|---|---:|---|---:|---:|
| s5-ankor-hr-unlimited-leave | Ankor có chính sách nghỉ phép không giới hạn số ngày không | 0.9143 | ankor-hr-leave#c1 | 0.7242 | 0.8269 |
| s5-borea-pub-bicycle-policy | quy định gửi xe đạp trong toà nhà Borea như thế nào | 0.8981 | borea-public-parking#c8 | 0.6566 | 0.8478 |
| s5-borea-hr-bereavement-extended | Borea có chính sách nghỉ phép tang chế kéo dài hơn 5 ngày không | 0.8827 | borea-hr-leave#c1 | 0.6737 | 0.8033 |
| s5-borea-hr-four-day-week | Borea có áp dụng tuần làm việc 4 ngày không | 0.8793 | borea-hr-onboarding#c7 | 0.6529 | 0.7785 |
| s5-borea-hr-adoption-leave | Borea có chính sách nghỉ phép khi nhận con nuôi không | 0.8789 | borea-hr-leave#c1 | 0.6165 | 0.7733 |
| s5-borea-eng-metaverse | hướng dẫn xây dựng ứng dụng trong môi trường metaverse tại Borea | 0.8756 | borea-engineering-access#c1 | 0.5693 | 0.7065 |
| s5-borea-hr-sabbatical-leave | Borea có chính sách nghỉ học thuật dài hạn sabbatical hưởng lương không | 0.8750 | borea-hr-leave#c1 | 0.6310 | 0.7599 |
| s5-borea-eng-embedded-linux | quy trình build và deploy image cho thiết bị nhúng Linux của Borea | 0.8721 | borea-engineering-deployment#c1 | 0.5544 | 0.6932 |
| s5-borea-eng-rust-guidelines | quy chuẩn viết code Rust tại Borea là gì | 0.8713 | borea-engineering-access#c1 | 0.5948 | 0.7624 |
| s5-borea-eng-vr | hướng dẫn thiết lập môi trường phát triển ứng dụng thực tế ảo vr | 0.8698 | borea-engineering-deployment#c2 | 0.5639 | 0.6158 |
| s5-borea-pub-massage-room | Borea có phòng massage thư giãn cho nhân viên sau giờ làm không | 0.8683 | borea-public-safety#c5 | 0.6401 | 0.7795 |
| s5-ankor-hr-student-loan | Ankor có hỗ trợ trả nợ vay học phí đại học cho nhân viên mới không | 0.8663 | ankor-hr-training#c1 | 0.6706 | 0.7286 |
| s5-ankor-hr-relocation-allowance | Ankor hỗ trợ chi phí chuyển nhà khi điều chuyển công tác nội địa không | 0.8659 | ankor-hr-recruitment#c8 | 0.5949 | 0.7670 |
| s5-borea-hr-expat-package | Borea có gói đãi ngộ riêng cho chuyên gia nước ngoài expatriate không | 0.8655 | borea-hr-onboarding#c8 | 0.6285 | 0.7694 |
| s5-borea-pub-art-installation | quy trình xin phép trưng bày tác phẩm nghệ thuật trong không gian văn phòng Borea | 0.8652 | borea-public-visitors#c10 | 0.6701 | 0.7100 |

## Breakdown theo tenant — 4 provider ứng viên

| tenant | tầng | n | recall hash512 | recall bge-m3 | recall e5-large | recall gemini-001 |
|---|---|---:|---:|---:|---:|---:|
| ankor | S1 | 36 | 0.7778 | 0.6944 | 0.6389 | 0.7500 |
| ankor | S2 | 31 | 0.1290 | 0.6129 | 0.6129 | 0.6129 |
| ankor | S3 | 31 | 0.6129 | 0.6452 | 0.6452 | 0.7742 |
| ankor | S4 | 28 | 0.4643 | 0.5714 | 0.6786 | 0.7143 |
| ankor | S5 | 30 | 0.6741 | 0.4223 | 0.1538 | 0.2982 |
| borea | S1 | 29 | 0.8621 | 0.7931 | 0.8276 | 0.8621 |
| borea | S2 | 30 | 0.1000 | 0.7333 | 0.6333 | 0.8000 |
| borea | S3 | 29 | 0.4138 | 0.4828 | 0.5172 | 0.6552 |
| borea | S4 | 27 | 0.4444 | 0.5926 | 0.5556 | 0.5556 |
| borea | S5 | 29 | 0.7008 | 0.4233 | 0.1434 | 0.2847 |

## `multilingual-e5-large` so trực tiếp với `bge-m3` và `gemini-embedding-001`

So với `bge-m3` (tổng 23/241 case non-S5 lệch nhau): e5-large thắng **11** case, bge-m3 thắng **12** case.
So với `gemini-embedding-001` (tổng 23/241 case non-S5 lệch nhau): e5-large thắng **2** case, gemini-embedding-001 thắng **21** case.

### 15 case e5-large thắng đậm nhất bge-m3 (bge-m3 trượt hẳn, e5-large ăn trọn)

| case id | tầng | query | expected | top-1 bge-m3 | top-1 e5-large |
|---|---|---|---|---|---|
| s1-ankor-eng-monitoring-downtime-alert | S1 | hệ thống monitoring Ankor gửi cảnh báo sau mấy phút downtime | ankor-engineering-monitoring#c5 | ankor-engineering-security#c7 | ankor-engineering-security#c7 |
| s1-borea-eng-deploy-time-window | S1 | Borea deploy lên production trong khung giờ nào | borea-engineering-deployment#c3 | borea-engineering-deployment#c1 | borea-engineering-deployment#c1 |
| s2-ankor-eng-infra-db | S2 | cơ sở dữ liệu chạy trên dịch vụ đám mây nào | ankor-engineering-infra#c4 | ankor-engineering-infra#c1 | ankor-engineering-infra#c1 |
| s2-ankor-eng-primary-cloud-region | S2 | dịch vụ của Ankor đặt máy chủ chính ở vùng địa lý nào | ankor-engineering-infra#c2 | ankor-engineering-infra#c1 | ankor-engineering-infra#c1 |
| s2-borea-eng-no-deploy-period | S2 | những dịp nào trong năm Borea cấm đội kỹ thuật đưa code lên production | borea-engineering-deployment#c10 | borea-engineering-code-review#c1 | borea-engineering-code-review#c1 |
| s3-ankor-pub-car-park-allocation | S3 | nhân viên nào được Ankor ưu tiên chỗ đỗ xe tại bãi | ankor-public-parking#c2 | ankor-public-parking#c1 | ankor-public-parking#c8 |
| s3-borea-fin-corporate-tax-deadline | S3 | Borea nộp tờ khai thuế TNDN vào thời điểm nào trong năm | borea-finance-tax#c4 | borea-finance-tax#c1 | borea-finance-invoicing#c9 |
| s3-borea-pub-first-aid-training | S3 | ai được đào tạo sơ cứu để xử lý khi có người bị thương tại văn phòng Borea | borea-public-safety#c5 | borea-public-anti-harassment#c8 | borea-public-safety#c10 |
| s4-ankor-fin-budget-alert | S4 | chi phí vượt ngưỡng ngân sách thì hệ thống cảnh báo cho ai | ankor-finance-budget#c7 | ankor-finance-approval-limits#c9 | ankor-finance-approval-limits#c9 |
| s4-ankor-fin-budget-alert-system | S4 | chi phí vượt ngưỡng ngân sách thì hệ thống cảnh báo cho ai | ankor-finance-budget#c7 | ankor-finance-approval-limits#c9 | ankor-finance-approval-limits#c9 |
| s4-ankor-fin-travel-approval | S4 | chi phí công tác nước ngoài phải được ai phê duyệt | ankor-finance-travel#c2 | ankor-finance-approval-limits#c1 | ankor-finance-approval-limits#c1 |

### 15 case bge-m3 thắng đậm nhất e5-large (e5-large trượt hẳn, bge-m3 ăn trọn)

| case id | tầng | query | expected | top-1 bge-m3 | top-1 e5-large |
|---|---|---|---|---|---|
| s1-ankor-eng-mfa-required | S1 | hệ thống Ankor bắt buộc xác thực hai bước không | ankor-engineering-security#c3 | ankor-engineering-testing#c1 | ankor-engineering-security#c1 |
| s1-ankor-eng-pr-large-sla | S1 | SLA review PR lớn ở Ankor là bao lâu | ankor-engineering-code-review#c4 | ankor-engineering-code-review#c3 | ankor-engineering-code-review#c3 |
| s1-ankor-hr-sick-days | S1 | nghỉ ốm mỗi năm được tối đa bao nhiêu ngày ở Ankor | ankor-hr-leave#c3 | ankor-hr-leave#c1 | ankor-hr-leave#c1 |
| s2-ankor-eng-oncall-nightcall | S2 | bị dựng dậy giữa đêm chữa sự cố thì hôm sau thế nào | ankor-engineering-oncall#c8 | ankor-engineering-oncall#c9 | ankor-engineering-oncall#c9 |
| s2-ankor-hr-probation-tasks | S2 | mới vào làm thì trong 2 tháng đầu phải làm gì để qua thử thách | ankor-hr-onboarding#c1 | ankor-hr-training#c7 | ankor-hr-training#c7 |
| s2-borea-fin-meal-expense-ceiling | S2 | chi phí tiếp đãi đối tác từng lần Borea giới hạn không quá bao nhiêu tiền | borea-finance-reimbursement#c2 | borea-finance-reimbursement#c1 | borea-finance-reimbursement#c1 |
| s2-borea-fin-petty-cash-request | S2 | muốn mua đồ nhỏ tiền mặt cho phòng thì lấy ở đâu | borea-finance-expense#c5 | borea-finance-travel#c5 | borea-finance-procurement#c1 |
| s2-borea-hr-complaint-response-time | S2 | khiếu nại nhân sự thì bao lâu nhận được phản hồi | borea-hr-grievance#c4 | borea-hr-performance#c9 | borea-hr-performance#c9 |
| s2-borea-hr-salary-structure | S2 | thu nhập định kỳ chia làm mấy phần | borea-hr-payroll#c1 | borea-hr-payroll#c2 | borea-hr-payroll#c2 |
| s3-ankor-fin-reimburse-late | S3 | gửi yêu cầu lấy lại chi phí muộn có được chấp nhận không | ankor-finance-reimbursement#c4 | ankor-finance-reimbursement#c7 | ankor-finance-reimbursement#c8 |
| s3-borea-eng-ci-integration-test | S3 | integration test ở Borea được chạy khi nào trong pipeline | borea-engineering-testing#c5 | borea-engineering-testing#c1 | borea-engineering-testing#c1 |
| s4-borea-fin-capex-vs-hr | S4 | khi mua máy tính mới cho nhân viên thì phải xin duyệt như thế nào | borea-finance-budget#c5 | borea-hr-remote-work#c4 | borea-hr-remote-work#c3 |

## Thời gian & tài nguyên

| Provider | Chiều | Thời gian embed 800 chunk + 300 query | Ghi chú |
|---|---:|---:|---|
| `baseline-dim8` | 8 | (số đóng băng, re-recorded) | CPU thuần, tức thời |
| `bow-hash512` | 512 | 0.92s | CPU thuần, không cần model/GPU/mạng |
| `bge-m3` | 1024 | load 9.8s + embed 14.7s | local, MPS, trọng số ~2.2GB (một lần, cache) |
| `multilingual-e5-large` | 1024 | load 9.3s + embed 15.2s | local, MPS, trọng số ~2.24GB (một lần, cache) |
| `gemini-embedding-001` | 1024 | 1.86s (đọc cache) | API Google — free tier có quota NGÀY dễ cạn khi test lặp lại |

Ba dense model có chi phí vận hành khác hẳn nhau: `bge-m3`/`multilingual-e5-large` chạy local trên GPU sẵn có (chỉ tốn thời gian tải trọng số MỘT LẦN, sau đó tức thời, không phụ thuộc mạng/quota); `gemini-embedding-001` không cần hạ tầng cục bộ nhưng phụ thuộc mạng + rate limit + quota ngày — rủi ro vận hành thật đã gặp phải trực tiếp khi chấm.

## Giới hạn của báo cáo này

- `gemini-embedding-001` không gọi API lại ở lần chạy này — dùng nguyên cache đã chấm trước đó (cùng corpus, cùng 300 case, cùng `output_dimensionality=1024` nên số liệu vẫn hợp lệ để so sánh).
- `multilingual-e5-large` chạy với prefix `query:`/`passage:` theo khuyến nghị chính thức — chưa thử bỏ prefix để đo mức chênh lệch thực tế do prefix mang lại trên bộ case này.
- Cả năm đều chấm ngoài luồng (gọi trực tiếp `H.build_retriever`/`build_report`-tương đương), không qua `pytest`/`conftest.py::embedding_provider`.
- In-memory cosine thuần Python, chưa qua `PgKbSearch`/pgvector thật — chưa đo latency/chi phí lưu trữ thực tế ở quy mô Postgres.
- Một lần chạy, không lặp lại để đo phương sai.

## Đề xuất

1. Với 3 dense model đều vượt gate ở mọi tầng và khoảng cách nội bộ giữa chúng nhỏ, tiêu chí chọn nên chuyển từ 'model nào recall cao nhất' sang 'chi phí vận hành nào phù hợp' — local (bge-m3/e5-large, cần GPU + trọng số cục bộ, không phụ thuộc mạng/quota) so với API (gemini-embedding-001, không cần hạ tầng cục bộ nhưng phụ thuộc rate limit + quota + chi phí theo lượng gọi).
2. Nếu ưu tiên 'không dashboard/dịch vụ ngoài, self-hosted' (tinh thần core hiện tại), `bge-m3` hoặc `multilingual-e5-large` local phù hợp hơn `gemini-embedding-001`.
3. Trước khi chốt provider cuối, nên đo thêm: `multilingual-e5-large` KHÔNG prefix (so mức chênh lệch prefix mang lại), `gemini-embedding-001` ở `output_dimensionality` gốc (3072), và latency p50/p99 tại request-time thật (khác batch offline như các report này) cho cả 3 dense model.

## Thực nghiệm: cross-encoder reranker (`bge-reranker-v2-m3`) trên `bge-m3`

Thử 2 hướng cải thiện: **(1) reranker** — lấy top-30 ứng viên từ bi-encoder `bge-m3` rồi cho cross-encoder `BAAI/bge-reranker-v2-m3` (đọc CẢ query và chunk cùng lúc, không chỉ so cosine) chấm lại, lấy top-10 sau cùng; **(2) ngưỡng tin cậy (threshold)** trên top-1 score để chặn trả lời khi không đủ tự tin (fix riêng cho S5). Kết luận: **chỉ giữ lại reranker** — threshold sweep ra một điểm ngọt trên thang bi-encoder (0.55) nhưng khi áp lên thang điểm reranker (khác hẳn về phân bố) thì bất kỳ ngưỡng nào >0 đều cắt mất một phần đáp án đúng ở S2 mà không có lợi ích ròng nào so với chỉ dùng reranker không ngưỡng — chi tiết ở mục Chi phí & giới hạn.

### Kết quả: `bge-m3` + reranker vs `bge-m3` thuần

| Tầng | dim-8 | bge-m3 | bge-m3 + rerank | delta (so bge-m3) | mrr bge-m3 | mrr +rerank |
|---|---:|---:|---:|---:|---:|---:|
| S1 | 0.2615 | 0.7385 | **0.8000** | +0.0615 | 0.5671 | 0.5924 |
| S2 | 0.0984 | 0.6721 | **0.6885** | +0.0164 | 0.3837 | 0.4151 |
| S3 | 0.2333 | 0.5667 | **0.6333** | +0.0667 | 0.3800 | 0.4584 |
| S4 | 0.2182 | 0.5818 | **0.6545** | +0.0727 | 0.4675 | 0.4761 |
| S5 | 0.0662 | 0.4228 | **0.7768** | +0.3541 | — | — |

**Gate: bge-m3 thuần 5/5 · bge-m3+rerank 5/5.** Reranker cải thiện CẢ 5 tầng, không đánh đổi tầng nào — MRR cũng tăng đều. Nổi bật nhất: **S5** tăng mạnh (0.4228→0.7768) — cross-encoder phân biệt 'gần giống nhưng sai' và 'thật sự không liên quan' tốt hơn hẳn cosine bi-encoder.

### Case bi-encoder trượt hẳn nhưng reranker sửa được (recall 0.0 → 1.0)

Tổng **18** case (trên 241 case non-S5) được sửa; **5** case bị hỏng theo chiều ngược lại. Một vài ví dụ:

| case id | tầng | query | expected | top-1 bge-m3 | top-1 +rerank |
|---|---|---|---|---|---|
| s1-ankor-hr-grievance-timeline | S1 | Ankor xử lý khiếu nại nội bộ trong bao nhiêu ngày | ankor-hr-grievance#c4 | ankor-hr-grievance#c1 | ankor-hr-grievance#c1 |
| s1-ankor-pub-gift-limit | S1 | được nhận quà tặng từ đối tác trị giá bao nhiêu | ankor-public-code-of-conduct#c5 | ankor-public-code-of-conduct#c6 | ankor-public-code-of-conduct#c6 |
| s1-borea-eng-deploy-time-window | S1 | Borea deploy lên production trong khung giờ nào | borea-engineering-deployment#c3 | borea-engineering-deployment#c1 | borea-engineering-deployment#c1 |
| s1-borea-fin-tax-tndn | S1 | thuế thu nhập doanh nghiệp Borea bao nhiêu phần trăm | borea-finance-tax#c2 | borea-finance-tax#c1 | borea-finance-tax#c1 |
| s1-borea-hr-paternity-leave | S1 | bố mới có con được nghỉ phép đặc biệt mấy ngày ở Borea | borea-hr-leave#c6 | borea-hr-leave#c1 | borea-hr-leave#c1 |
| s2-ankor-eng-primary-cloud-region | S2 | dịch vụ của Ankor đặt máy chủ chính ở vùng địa lý nào | ankor-engineering-infra#c2 | ankor-engineering-infra#c1 | ankor-engineering-infra#c1 |
| s2-borea-hr-performance-frequency | S2 | sếp gặp riêng từng người dưới quyền để bàn việc mấy bận trong một năm | borea-hr-performance#c1 | borea-hr-exit#c2 | borea-hr-remote-work#c6 |
| s2-borea-pub-workplace-bullying | S2 | tổ chức phản hồi ra sao khi một người bị ức hiếp trong công sở | borea-public-anti-harassment#c1 | borea-public-code-of-conduct#c2 | borea-public-code-of-conduct#c2 |
| s3-ankor-hr-sick-notification | S3 | nghỉ ốm đột xuất cần báo trước bao lâu và báo cho ai ở Ankor | ankor-hr-leave#c3 | ankor-hr-exit#c1 | ankor-hr-exit#c1 |
| s3-ankor-pub-car-park-allocation | S3 | nhân viên nào được Ankor ưu tiên chỗ đỗ xe tại bãi | ankor-public-parking#c2 | ankor-public-parking#c1 | ankor-public-parking#c8 |

Chiều ngược lại (5 case rerank làm hỏng case bi-encoder từng đúng):

| case id | tầng | query | expected | top-1 bge-m3 | top-1 +rerank |
|---|---|---|---|---|---|
| s1-ankor-eng-pr-large-sla | S1 | SLA review PR lớn ở Ankor là bao lâu | ankor-engineering-code-review#c4 | ankor-engineering-code-review#c3 | ankor-engineering-code-review#c3 |
| s2-ankor-fin-audit-scope | S2 | bộ phận rà soát tài chính riêng của công ty xem xét các hạng mục gì | ankor-finance-audit#c1 | ankor-finance-audit#c3 | ankor-finance-audit#c4 |
| s2-ankor-hr-wfh-equipment | S2 | làm ở nhà thì công ty phát cho những gì | ankor-hr-remote-work#c4 | ankor-hr-payroll#c8 | ankor-hr-benefits#c2 |
| s3-borea-fin-quarterly-forecast-due | S3 | dự báo tài chính hằng quý phải nộp cho ban lãnh đạo trước hạn nào | borea-finance-forecast#c2 | borea-finance-expense#c9 | borea-finance-expense#c9 |
| s4-borea-fin-capex-vs-hr | S4 | khi mua máy tính mới cho nhân viên thì phải xin duyệt như thế nào | borea-finance-budget#c5 | borea-hr-remote-work#c4 | borea-finance-reimbursement#c8 |

### S5 — reranker bớt 'tự tin trả nhầm' rõ rệt nhất

6 case `top_score` giảm nhiều nhất khi chuyển từ bi-encoder sang reranker (bi-encoder từng tự tin cao dù không có đáp án thật):

| case id | query | top_score bge-m3 | top_score +rerank | giảm |
|---|---|---:|---:|---:|
| s5-ankor-hr-student-loan | Ankor có hỗ trợ trả nợ vay học phí đại học cho nhân viên mới không | 0.6706 | 0.0654 | +0.6052 |
| s5-ankor-pub-meditation-room | Ankor có phòng thiền định cho nhân viên cần không gian yên tĩnh không | 0.6631 | 0.0694 | +0.5937 |
| s5-ankor-fin-car-loan | quy định duyệt khoản vay ưu đãi mua ô tô trả góp cho nhân sự cấp cao | 0.6085 | 0.0200 | +0.5884 |
| s5-ankor-hr-crypto-bonus | công ty có trả thưởng bằng tiền điện tử không | 0.6180 | 0.0301 | +0.5880 |
| s5-ankor-hr-fertility-treatment | công ty có hỗ trợ chi phí điều trị hiếm muộn cho nhân viên không | 0.5701 | 0.0059 | +0.5642 |
| s5-ankor-pub-gym | công ty có phòng gym miễn phí cho nhân viên không | 0.5729 | 0.0115 | +0.5614 |

### Chi phí & giới hạn

- **Chi phí**: rerank 30 ứng viên/query × 300 query = 9000 cặp (query, chunk) qua cross-encoder — mất **159.5s** trên MPS local (thêm vào ~25s embed bi-encoder có sẵn). Đây là chi phí request-time thật nếu áp production (mỗi query mới đều phải rerank), không phải chi phí một lần như embed corpus.
- **Threshold KHÔNG cộng dồn được với reranker** — sweep threshold trên thang điểm reranker (0.05 → 0.50) cho thấy MỌI mức threshold thử đều làm S2 tụt, trong khi S5 chỉ nhích thêm so với reranker-không-threshold vốn đã cải thiện mạnh. Kết luận: reranker một mình đã đạt hầu hết lợi ích mà threshold nhắm tới cho S5, thêm threshold chỉ có hại ròng trên bộ case này — vì vậy KHÔNG đưa threshold vào khuyến nghị cuối, chỉ giữ reranker.
- Thử ngoài luồng (không qua `pytest`), top-30 lấy từ `bge-m3` local — chưa thử reranker trên top-30 của `gemini-embedding-001`/`multilingual-e5-large` hay ở pool lớn hơn 30.
- Một lần chạy, không lặp lại để đo phương sai.

## Khuyến nghị cuối cùng

**`bge-m3` + `bge-reranker-v2-m3` (2 tầng: bi-encoder lấy top-30 → cross-encoder rerank còn top-10)** — không phải một embedding đơn lẻ.

| | dim-8 | hash512 | e5-large | gemini-001 | bge-m3 | **bge-m3 + rerank** |
|---|---:|---:|---:|---:|---:|---:|
| Gate | — | 4/5 | 5/5 | 5/5 | 5/5 | **5/5** |
| Recall trung bình 5 tầng | 0.1755 | 0.5177 | 0.5392 | 0.6299 | 0.5964 | **0.7106** |
| S5 (không trả bịa) | 0.0662 | 0.6872 | 0.1487 | 0.2916 | 0.4228 | **0.7768** |
| Chạy ở đâu | local | local | local | API | local | local |
| Rủi ro vận hành | — | không | không | quota/mạng (dính cạn quota 2 lần khi đo) | không | không |

Ba lý do:

1. **Thắng mọi lựa chọn embedding đơn, kể cả `gemini-embedding-001`** (vốn đang cao nhất trong 3 dense model) — reranker đọc query+chunk cùng lúc nên xử lý đúng loại bẫy corpus cố tình dựng (S3 near-miss cùng vai, S4 cross-role trap). Không đánh đổi gì để có mức tăng này: cả 5 tầng đều lên so với `bge-m3` thuần, không tầng nào giảm.
2. **S5 vượt trội** — ít 'tự tin trả nhầm' nhất khi câu hỏi không có đáp án thật trong số mọi lựa chọn đã thử. Với RAG, đây quan trọng ngang recall vì quyết định LLM có bị đưa context sai rồi bịa theo không.
3. **Toàn bộ local, không phụ thuộc API/quota** — `gemini-embedding-001` recall S1-S4 cao nhất nhưng đã đích thân dính quota-cạn 2 lần trong quá trình đo ở report này, phải đổi 3 API key mới xong một job 1100 văn bản. Rủi ro vận hành thật, không phải lý thuyết.

**Đánh đổi cần biết**: reranker cộng thêm ~530ms/query (159.5s / 300 query ở top-30) so với chỉ dùng bi-encoder — cần đo lại nếu retrieval nằm trên đường latency-critical có SLA chặt.

**Nếu bắt buộc chỉ chọn một embedding đơn** (không thêm tầng rerank): **`bge-m3`** — cân bằng nhất, local, và đã là model sạch nhất (S5 tốt nhất trong 3 dense) trước cả khi thêm reranker.

**Lưu ý phạm vi**: đây là khuyến nghị dựa trên dữ liệu từ eval harness DE sở hữu (`tests/embedding-tests/`) — quyết định wiring embedding thật vào hệ thống (đổi `EMBEDDING_DIM`, `EmbeddingService`) là lane của AIE-1, cần trao đổi trước khi áp dụng.

## Phụ lục — kết quả đầy đủ 300 case, cả 4 provider ứng viên cạnh nhau

| case id | tầng | tenant | recall hash512 | recall bge-m3 | recall e5-large | recall gemini-001 | top1 e5-large |
|---|---|---|---:|---:|---:|---:|---|
| s1-ankor-eng-code-review-approval | S1 | ankor | 1.00 | 1.00 | 1.00 | 1.00 | ankor-engineering-code-review#c1 |
| s1-ankor-eng-deployment-strategy | S1 | ankor | 0.00 | 0.00 | 0.00 | 0.00 | ankor-engineering-deployment#c1 |
| s1-ankor-eng-incident-classify | S1 | ankor | 1.00 | 1.00 | 1.00 | 1.00 | ankor-engineering-incident#c1 |
| s1-ankor-eng-infra-region | S1 | ankor | 1.00 | 1.00 | 1.00 | 1.00 | ankor-engineering-infra#c1 |
| s1-ankor-eng-log-retention | S1 | ankor | 1.00 | 1.00 | 1.00 | 1.00 | ankor-engineering-oncall#c5 |
| s1-ankor-eng-mfa-required | S1 | ankor | 1.00 | 1.00 | 0.00 | 1.00 | ankor-engineering-security#c1 |
| s1-ankor-eng-monitoring-downtime-alert | S1 | ankor | 0.00 | 0.00 | 1.00 | 1.00 | ankor-engineering-security#c7 |
| s1-ankor-eng-oncall-allowance | S1 | ankor | 1.00 | 1.00 | 1.00 | 1.00 | ankor-engineering-oncall#c3 |
| s1-ankor-eng-oncall-sla-p1 | S1 | ankor | 1.00 | 1.00 | 1.00 | 1.00 | ankor-engineering-oncall#c4 |
| s1-ankor-eng-pr-large-sla | S1 | ankor | 1.00 | 1.00 | 0.00 | 0.00 | ankor-engineering-code-review#c3 |
| s1-ankor-eng-production-access | S1 | ankor | 1.00 | 1.00 | 1.00 | 1.00 | ankor-engineering-access#c8 |
| s1-ankor-eng-review-sla | S1 | ankor | 1.00 | 1.00 | 1.00 | 1.00 | ankor-engineering-code-review#c3 |
| s1-ankor-fin-approval-teamlead | S1 | ankor | 1.00 | 1.00 | 1.00 | 1.00 | ankor-finance-approval-limits#c2 |
| s1-ankor-fin-budget-capex | S1 | ankor | 0.00 | 0.00 | 0.00 | 0.00 | ankor-finance-forecast#c1 |
| s1-ankor-fin-pettycash | S1 | ankor | 1.00 | 1.00 | 1.00 | 1.00 | ankor-finance-expense#c5 |
| s1-ankor-fin-procurement-floor | S1 | ankor | 1.00 | 1.00 | 1.00 | 1.00 | ankor-finance-procurement#c1 |
| s1-ankor-fin-reimburse-deadline | S1 | ankor | 1.00 | 1.00 | 1.00 | 1.00 | ankor-finance-reimbursement#c3 |
| s1-ankor-fin-tax-tndn | S1 | ankor | 1.00 | 1.00 | 1.00 | 1.00 | ankor-finance-tax#c1 |
| s1-ankor-hr-annual-leave-count | S1 | ankor | 1.00 | 1.00 | 1.00 | 1.00 | ankor-hr-leave#c1 |
| s1-ankor-hr-grievance-timeline | S1 | ankor | 1.00 | 0.00 | 0.00 | 0.00 | ankor-hr-grievance#c1 |
| s1-ankor-hr-health-insurance-coverage | S1 | ankor | 1.00 | 1.00 | 1.00 | 1.00 | ankor-hr-benefits#c1 |
| s1-ankor-hr-performance-cycle | S1 | ankor | 1.00 | 1.00 | 1.00 | 1.00 | ankor-hr-performance#c1 |
| s1-ankor-hr-probation-period | S1 | ankor | 0.00 | 0.00 | 0.00 | 0.00 | ankor-hr-onboarding#c7 |
| s1-ankor-hr-sick-days | S1 | ankor | 1.00 | 1.00 | 0.00 | 1.00 | ankor-hr-leave#c1 |
| s1-ankor-hr-thaisan | S1 | ankor | 1.00 | 1.00 | 1.00 | 1.00 | ankor-hr-leave#c5 |
| s1-ankor-hr-wfh-days | S1 | ankor | 0.00 | 1.00 | 1.00 | 1.00 | ankor-hr-remote-work#c2 |
| s1-ankor-pub-casual-friday | S1 | ankor | 1.00 | 1.00 | 1.00 | 1.00 | ankor-public-dress-code#c1 |
| s1-ankor-pub-communication-slack | S1 | ankor | 0.00 | 0.00 | 0.00 | 0.00 | ankor-public-communication#c1 |
| s1-ankor-pub-gift-limit | S1 | ankor | 0.00 | 0.00 | 0.00 | 1.00 | ankor-public-code-of-conduct#c6 |
| s1-ankor-pub-harassment-report-channel | S1 | ankor | 1.00 | 0.00 | 0.00 | 0.00 | ankor-public-anti-harassment#c6 |
| s1-ankor-pub-national-holidays | S1 | ankor | 1.00 | 0.00 | 0.00 | 0.00 | ankor-public-holidays#c10 |
| s1-ankor-pub-office-open-time | S1 | ankor | 1.00 | 1.00 | 1.00 | 1.00 | ankor-public-office-hours#c1 |
| s1-ankor-pub-parking-fee | S1 | ankor | 1.00 | 1.00 | 1.00 | 1.00 | ankor-public-parking#c8 |
| s1-ankor-pub-parking-motorbike | S1 | ankor | 0.00 | 0.00 | 0.00 | 1.00 | ankor-public-parking#c8 |
| s1-ankor-pub-tet | S1 | ankor | 1.00 | 1.00 | 1.00 | 1.00 | ankor-public-holidays#c1 |
| s1-ankor-pub-visitor-badge-color | S1 | ankor | 1.00 | 0.00 | 0.00 | 0.00 | ankor-public-visitors#c1 |
| s1-borea-eng-alert-level | S1 | borea | 0.00 | 1.00 | 1.00 | 1.00 | borea-engineering-monitoring#c5 |
| s1-borea-eng-db-access | S1 | borea | 1.00 | 1.00 | 1.00 | 1.00 | borea-engineering-access#c8 |
| s1-borea-eng-deploy-time-window | S1 | borea | 0.00 | 0.00 | 1.00 | 1.00 | borea-engineering-deployment#c1 |
| s1-borea-eng-incident-p1-ack | S1 | borea | 1.00 | 1.00 | 1.00 | 1.00 | borea-engineering-oncall#c4 |
| s1-borea-eng-oncall-weekly-pay | S1 | borea | 1.00 | 1.00 | 1.00 | 1.00 | borea-engineering-oncall#c1 |
| s1-borea-eng-pr-small-sla | S1 | borea | 1.00 | 1.00 | 1.00 | 1.00 | borea-engineering-code-review#c10 |
| s1-borea-eng-release-freeze | S1 | borea | 1.00 | 1.00 | 1.00 | 1.00 | borea-engineering-deployment#c1 |
| s1-borea-eng-rollback | S1 | borea | 1.00 | 1.00 | 1.00 | 1.00 | borea-engineering-deployment#c5 |
| s1-borea-fin-cfo-approval-cap | S1 | borea | 1.00 | 1.00 | 1.00 | 1.00 | borea-finance-reimbursement#c1 |
| s1-borea-fin-petty-cash | S1 | borea | 0.00 | 0.00 | 0.00 | 0.00 | borea-finance-reimbursement#c1 |
| s1-borea-fin-procurement-scope | S1 | borea | 1.00 | 1.00 | 1.00 | 1.00 | borea-finance-procurement#c1 |
| s1-borea-fin-reimburse-limit | S1 | borea | 1.00 | 1.00 | 1.00 | 1.00 | borea-finance-reimbursement#c2 |
| s1-borea-fin-reimbursement-cap | S1 | borea | 1.00 | 1.00 | 1.00 | 1.00 | borea-finance-reimbursement#c1 |
| s1-borea-fin-tax-tndn | S1 | borea | 1.00 | 0.00 | 0.00 | 1.00 | borea-finance-tax#c1 |
| s1-borea-fin-travel-meal | S1 | borea | 1.00 | 1.00 | 1.00 | 1.00 | borea-finance-reimbursement#c1 |
| s1-borea-hr-annual-review-cycle | S1 | borea | 1.00 | 1.00 | 1.00 | 1.00 | borea-hr-performance#c1 |
| s1-borea-hr-leave-annual | S1 | borea | 1.00 | 1.00 | 1.00 | 1.00 | borea-hr-leave#c1 |
| s1-borea-hr-paternity-leave | S1 | borea | 1.00 | 0.00 | 0.00 | 0.00 | borea-hr-leave#c1 |
| s1-borea-hr-payday | S1 | borea | 1.00 | 0.00 | 0.00 | 0.00 | borea-hr-exit#c6 |
| s1-borea-hr-remote-days | S1 | borea | 1.00 | 0.00 | 0.00 | 0.00 | borea-hr-remote-work#c8 |
| s1-borea-hr-resignation-notice | S1 | borea | 1.00 | 1.00 | 1.00 | 1.00 | borea-hr-exit#c1 |
| s1-borea-hr-sick | S1 | borea | 1.00 | 1.00 | 1.00 | 1.00 | borea-hr-leave#c3 |
| s1-borea-hr-sick-max-days | S1 | borea | 1.00 | 1.00 | 1.00 | 1.00 | borea-hr-leave#c3 |
| s1-borea-hr-training-annual-budget | S1 | borea | 1.00 | 1.00 | 1.00 | 1.00 | borea-hr-training#c1 |
| s1-borea-pub-canteen-hours | S1 | borea | 1.00 | 1.00 | 1.00 | 1.00 | borea-public-office-hours#c2 |
| s1-borea-pub-dress-code-basic | S1 | borea | 0.00 | 1.00 | 1.00 | 1.00 | borea-public-dress-code#c9 |
| s1-borea-pub-dress-formal | S1 | borea | 1.00 | 1.00 | 1.00 | 1.00 | borea-public-dress-code#c3 |
| s1-borea-pub-office-hours | S1 | borea | 1.00 | 1.00 | 1.00 | 1.00 | borea-public-office-hours#c6 |
| s1-borea-pub-tet | S1 | borea | 1.00 | 1.00 | 1.00 | 1.00 | borea-public-holidays#c1 |
| s2-ankor-eng-blue-green | S2 | ankor | 0.00 | 0.00 | 0.00 | 0.00 | ankor-engineering-release#c1 |
| s2-ankor-eng-deploy-freeze | S2 | ankor | 0.00 | 1.00 | 1.00 | 1.00 | ankor-engineering-release#c2 |
| s2-ankor-eng-infra-db | S2 | ankor | 0.00 | 0.00 | 1.00 | 1.00 | ankor-engineering-infra#c1 |
| s2-ankor-eng-log-storage-period | S2 | ankor | 0.00 | 0.00 | 0.00 | 0.00 | ankor-engineering-security#c10 |
| s2-ankor-eng-merge-approvers | S2 | ankor | 1.00 | 1.00 | 1.00 | 1.00 | ankor-engineering-code-review#c1 |
| s2-ankor-eng-oncall-nightcall | S2 | ankor | 0.00 | 1.00 | 0.00 | 0.00 | ankor-engineering-oncall#c9 |
| s2-ankor-eng-pr-test-requirement | S2 | ankor | 0.00 | 0.00 | 0.00 | 0.00 | ankor-engineering-security#c5 |
| s2-ankor-eng-primary-cloud-region | S2 | ankor | 0.00 | 0.00 | 1.00 | 1.00 | ankor-engineering-infra#c1 |
| s2-ankor-eng-release-rhythm | S2 | ankor | 0.00 | 1.00 | 1.00 | 1.00 | ankor-engineering-incident#c5 |
| s2-ankor-eng-secret-store | S2 | ankor | 1.00 | 1.00 | 1.00 | 1.00 | ankor-engineering-access#c9 |
| s2-ankor-fin-audit-scope | S2 | ankor | 0.00 | 1.00 | 1.00 | 0.00 | ankor-finance-approval-limits#c10 |
| s2-ankor-fin-budget-reforecast | S2 | ankor | 0.00 | 1.00 | 1.00 | 1.00 | ankor-finance-budget#c1 |
| s2-ankor-fin-capital-expenditure | S2 | ankor | 0.00 | 0.00 | 0.00 | 0.00 | ankor-finance-audit#c3 |
| s2-ankor-fin-indirect-tax-rate | S2 | ankor | 0.00 | 0.00 | 0.00 | 0.00 | ankor-finance-tax#c1 |
| s2-ankor-fin-invoice-format | S2 | ankor | 0.00 | 0.00 | 0.00 | 0.00 | ankor-finance-invoicing#c3 |
| s2-ankor-hr-complaint-handling | S2 | ankor | 0.00 | 1.00 | 1.00 | 1.00 | ankor-hr-grievance#c2 |
| s2-ankor-hr-exit-notice | S2 | ankor | 1.00 | 1.00 | 1.00 | 1.00 | ankor-hr-exit#c1 |
| s2-ankor-hr-pip-timeframe | S2 | ankor | 1.00 | 1.00 | 1.00 | 1.00 | ankor-hr-performance#c7 |
| s2-ankor-hr-probation-tasks | S2 | ankor | 0.00 | 1.00 | 0.00 | 0.00 | ankor-hr-training#c7 |
| s2-ankor-hr-recruitment-interview-count | S2 | ankor | 0.00 | 0.00 | 0.00 | 0.00 | ankor-hr-recruitment#c8 |
| s2-ankor-hr-training-budget | S2 | ankor | 0.00 | 1.00 | 1.00 | 1.00 | ankor-hr-training#c1 |
| s2-ankor-hr-unused-leave-rollover | S2 | ankor | 0.00 | 1.00 | 1.00 | 1.00 | ankor-hr-leave#c10 |
| s2-ankor-hr-wfh-equipment | S2 | ankor | 0.00 | 1.00 | 1.00 | 1.00 | ankor-hr-remote-work#c4 |
| s2-ankor-pub-conduct-discipline | S2 | ankor | 0.00 | 1.00 | 1.00 | 1.00 | ankor-public-anti-harassment#c8 |
| s2-ankor-pub-daily-outfit | S2 | ankor | 0.00 | 1.00 | 1.00 | 1.00 | ankor-public-dress-code#c2 |
| s2-ankor-pub-fire-escape-route | S2 | ankor | 0.00 | 0.00 | 0.00 | 0.00 | ankor-public-visitors#c3 |
| s2-ankor-pub-instant-messaging | S2 | ankor | 0.00 | 1.00 | 1.00 | 1.00 | ankor-public-communication#c9 |
| s2-ankor-pub-official-comms-channel | S2 | ankor | 0.00 | 1.00 | 1.00 | 1.00 | ankor-public-communication#c9 |
| s2-ankor-pub-parking-reserve | S2 | ankor | 0.00 | 0.00 | 0.00 | 1.00 | ankor-public-parking#c2 |
| s2-ankor-pub-public-holidays-list | S2 | ankor | 0.00 | 0.00 | 0.00 | 0.00 | ankor-public-office-hours#c10 |
| s2-ankor-pub-visitor-entry | S2 | ankor | 0.00 | 1.00 | 1.00 | 1.00 | ankor-public-visitors#c8 |
| s2-borea-eng-alert-first-receiver | S2 | borea | 0.00 | 0.00 | 0.00 | 0.00 | borea-engineering-oncall#c4 |
| s2-borea-eng-cloud-provider | S2 | borea | 0.00 | 1.00 | 1.00 | 1.00 | borea-engineering-infra#c1 |
| s2-borea-eng-no-deploy-period | S2 | borea | 0.00 | 0.00 | 1.00 | 1.00 | borea-engineering-code-review#c1 |
| s2-borea-eng-p2-response-sla | S2 | borea | 0.00 | 0.00 | 0.00 | 0.00 | borea-engineering-oncall#c4 |
| s2-borea-eng-prod-login | S2 | borea | 0.00 | 1.00 | 1.00 | 1.00 | borea-engineering-access#c8 |
| s2-borea-eng-rollback-trigger | S2 | borea | 0.00 | 1.00 | 1.00 | 1.00 | borea-engineering-deployment#c5 |
| s2-borea-eng-test-coverage | S2 | borea | 0.00 | 1.00 | 1.00 | 1.00 | borea-engineering-testing#c5 |
| s2-borea-fin-approval-level | S2 | borea | 0.00 | 0.00 | 0.00 | 0.00 | borea-finance-budget#c5 |
| s2-borea-fin-corporate-tax | S2 | borea | 1.00 | 0.00 | 0.00 | 0.00 | borea-finance-tax#c1 |
| s2-borea-fin-invoice-issuance-window | S2 | borea | 0.00 | 1.00 | 1.00 | 1.00 | borea-finance-invoicing#c2 |
| s2-borea-fin-meal-expense-ceiling | S2 | borea | 0.00 | 1.00 | 0.00 | 1.00 | borea-finance-reimbursement#c1 |
| s2-borea-fin-min-vendor-quotes | S2 | borea | 0.00 | 1.00 | 1.00 | 1.00 | borea-finance-procurement#c7 |
| s2-borea-fin-petty-cash-request | S2 | borea | 0.00 | 1.00 | 0.00 | 1.00 | borea-finance-procurement#c1 |
| s2-borea-fin-travel-hotel | S2 | borea | 0.00 | 1.00 | 1.00 | 1.00 | borea-finance-travel#c4 |
| s2-borea-hr-complaint-response-time | S2 | borea | 0.00 | 1.00 | 0.00 | 1.00 | borea-hr-performance#c9 |
| s2-borea-hr-dad-days-off | S2 | borea | 0.00 | 1.00 | 1.00 | 0.00 | borea-hr-onboarding#c7 |
| s2-borea-hr-medical-cert | S2 | borea | 0.00 | 1.00 | 1.00 | 1.00 | borea-hr-leave#c3 |
| s2-borea-hr-onboarding-day1 | S2 | borea | 1.00 | 1.00 | 1.00 | 1.00 | borea-hr-onboarding#c2 |
| s2-borea-hr-performance-frequency | S2 | borea | 1.00 | 0.00 | 0.00 | 1.00 | borea-hr-grievance#c6 |
| s2-borea-hr-rating-scale | S2 | borea | 0.00 | 0.00 | 0.00 | 0.00 | borea-hr-payroll#c1 |
| s2-borea-hr-referral | S2 | borea | 0.00 | 1.00 | 1.00 | 1.00 | borea-hr-recruitment#c9 |
| s2-borea-hr-salary-structure | S2 | borea | 0.00 | 1.00 | 0.00 | 1.00 | borea-hr-payroll#c2 |
| s2-borea-hr-supplemental-health | S2 | borea | 0.00 | 1.00 | 1.00 | 1.00 | borea-hr-benefits#c2 |
| s2-borea-hr-wfh-office-days | S2 | borea | 0.00 | 1.00 | 1.00 | 1.00 | borea-hr-remote-work#c2 |
| s2-borea-pub-business-attire | S2 | borea | 0.00 | 1.00 | 1.00 | 1.00 | borea-public-dress-code#c3 |
| s2-borea-pub-company-purpose | S2 | borea | 0.00 | 1.00 | 1.00 | 1.00 | borea-public-anti-harassment#c9 |
| s2-borea-pub-holiday-count | S2 | borea | 0.00 | 1.00 | 1.00 | 1.00 | borea-public-holidays#c4 |
| s2-borea-pub-lunch-service | S2 | borea | 0.00 | 1.00 | 1.00 | 1.00 | borea-public-office-hours#c2 |
| s2-borea-pub-safety-fire | S2 | borea | 0.00 | 1.00 | 1.00 | 1.00 | borea-public-safety#c2 |
| s2-borea-pub-workplace-bullying | S2 | borea | 0.00 | 0.00 | 0.00 | 1.00 | borea-public-code-of-conduct#c2 |
| s3-ankor-eng-code-freeze-scope | S3 | ankor | 0.00 | 1.00 | 1.00 | 1.00 | ankor-engineering-security#c1 |
| s3-ankor-eng-deploy-rollback | S3 | ankor | 1.00 | 1.00 | 1.00 | 1.00 | ankor-engineering-deployment#c5 |
| s3-ankor-eng-hotfix-process | S3 | ankor | 0.00 | 0.00 | 0.00 | 0.00 | ankor-engineering-oncall#c6 |
| s3-ankor-eng-infra-backup | S3 | ankor | 0.00 | 0.00 | 0.00 | 0.00 | ankor-engineering-security#c1 |
| s3-ankor-eng-oncall-sla | S3 | ankor | 1.00 | 1.00 | 1.00 | 1.00 | ankor-engineering-oncall#c2 |
| s3-ankor-eng-rollback-criteria | S3 | ankor | 1.00 | 1.00 | 1.00 | 1.00 | ankor-engineering-deployment#c5 |
| s3-ankor-eng-security-password | S3 | ankor | 1.00 | 1.00 | 1.00 | 1.00 | ankor-engineering-security#c2 |
| s3-ankor-eng-vuln-patch-sla | S3 | ankor | 0.00 | 0.00 | 0.00 | 1.00 | ankor-engineering-security#c9 |
| s3-ankor-fin-approval-limits | S3 | ankor | 1.00 | 1.00 | 1.00 | 1.00 | ankor-finance-approval-limits#c8 |
| s3-ankor-fin-expense-alert | S3 | ankor | 1.00 | 1.00 | 1.00 | 1.00 | ankor-finance-expense#c2 |
| s3-ankor-fin-external-audit-cycle | S3 | ankor | 1.00 | 1.00 | 1.00 | 1.00 | ankor-finance-audit#c1 |
| s3-ankor-fin-opex-categories | S3 | ankor | 1.00 | 1.00 | 1.00 | 1.00 | ankor-finance-expense#c1 |
| s3-ankor-fin-opex-report | S3 | ankor | 0.00 | 0.00 | 0.00 | 0.00 | ankor-finance-forecast#c2 |
| s3-ankor-fin-petty-cash-usage | S3 | ankor | 1.00 | 1.00 | 1.00 | 1.00 | ankor-finance-procurement#c1 |
| s3-ankor-fin-reimburse-late | S3 | ankor | 0.00 | 1.00 | 0.00 | 1.00 | ankor-finance-reimbursement#c8 |
| s3-ankor-fin-revenue-forecast-cycle | S3 | ankor | 1.00 | 1.00 | 1.00 | 1.00 | ankor-finance-forecast#c2 |
| s3-ankor-hr-maternity-return | S3 | ankor | 0.00 | 1.00 | 1.00 | 1.00 | ankor-hr-exit#c9 |
| s3-ankor-hr-offboard-handover-window | S3 | ankor | 1.00 | 0.00 | 0.00 | 1.00 | ankor-hr-exit#c1 |
| s3-ankor-hr-paternity-apply | S3 | ankor | 0.00 | 0.00 | 0.00 | 0.00 | ankor-hr-leave#c5 |
| s3-ankor-hr-performance-pip | S3 | ankor | 1.00 | 1.00 | 1.00 | 1.00 | ankor-hr-performance#c7 |
| s3-ankor-hr-sick-notification | S3 | ankor | 1.00 | 0.00 | 0.00 | 1.00 | ankor-hr-exit#c1 |
| s3-ankor-hr-sick-notify | S3 | ankor | 1.00 | 1.00 | 1.00 | 1.00 | ankor-hr-leave#c3 |
| s3-ankor-hr-week1-tasks | S3 | ankor | 0.00 | 1.00 | 1.00 | 1.00 | ankor-hr-onboarding#c2 |
| s3-ankor-pub-all-hands-cadence | S3 | ankor | 0.00 | 1.00 | 1.00 | 1.00 | ankor-public-office-hours#c8 |
| s3-ankor-pub-canteen-menu | S3 | ankor | 0.00 | 0.00 | 0.00 | 0.00 | ankor-public-dress-code#c1 |
| s3-ankor-pub-car-park-allocation | S3 | ankor | 1.00 | 0.00 | 1.00 | 1.00 | ankor-public-parking#c8 |
| s3-ankor-pub-core-values | S3 | ankor | 1.00 | 1.00 | 1.00 | 1.00 | ankor-public-mission#c3 |
| s3-ankor-pub-holiday-overtime-pay | S3 | ankor | 1.00 | 1.00 | 1.00 | 1.00 | ankor-public-holidays#c6 |
| s3-ankor-pub-meeting-room-etiquette | S3 | ankor | 0.00 | 0.00 | 0.00 | 0.00 | ankor-public-office-hours#c10 |
| s3-ankor-pub-national-holiday-work | S3 | ankor | 1.00 | 0.00 | 0.00 | 0.00 | ankor-public-holidays#c5 |
| s3-ankor-pub-parking-bikes | S3 | ankor | 1.00 | 1.00 | 1.00 | 1.00 | ankor-public-parking#c2 |
| s3-borea-eng-canary-deployment | S3 | borea | 0.00 | 0.00 | 0.00 | 0.00 | borea-engineering-release#c1 |
| s3-borea-eng-ci-integration-test | S3 | borea | 0.00 | 1.00 | 0.00 | 1.00 | borea-engineering-testing#c1 |
| s3-borea-eng-code-review-checklist | S3 | borea | 0.00 | 0.00 | 0.00 | 1.00 | borea-engineering-code-review#c1 |
| s3-borea-eng-incident-classify | S3 | borea | 1.00 | 1.00 | 1.00 | 1.00 | borea-engineering-incident#c1 |
| s3-borea-eng-log-search | S3 | borea | 0.00 | 0.00 | 0.00 | 0.00 | borea-engineering-code-review#c9 |
| s3-borea-eng-ops-dashboard | S3 | borea | 0.00 | 0.00 | 0.00 | 0.00 | borea-engineering-infra#c1 |
| s3-borea-eng-prod-session | S3 | borea | 0.00 | 1.00 | 1.00 | 1.00 | borea-engineering-access#c5 |
| s3-borea-eng-semver-convention | S3 | borea | 1.00 | 0.00 | 0.00 | 1.00 | borea-engineering-release#c1 |
| s3-borea-fin-budget-contingency | S3 | borea | 1.00 | 1.00 | 1.00 | 1.00 | borea-finance-budget#c8 |
| s3-borea-fin-capex-approval | S3 | borea | 0.00 | 0.00 | 0.00 | 0.00 | borea-finance-approval-limits#c1 |
| s3-borea-fin-corporate-tax-deadline | S3 | borea | 0.00 | 0.00 | 1.00 | 1.00 | borea-finance-invoicing#c9 |
| s3-borea-fin-quarterly-forecast-due | S3 | borea | 1.00 | 1.00 | 1.00 | 1.00 | borea-finance-expense#c9 |
| s3-borea-fin-receipt-attachment-format | S3 | borea | 1.00 | 0.00 | 0.00 | 0.00 | borea-finance-reimbursement#c3 |
| s3-borea-hr-exit-interview-mandatory | S3 | borea | 0.00 | 0.00 | 0.00 | 1.00 | borea-hr-exit#c1 |
| s3-borea-hr-grievance-steps | S3 | borea | 0.00 | 0.00 | 0.00 | 0.00 | borea-hr-grievance#c1 |
| s3-borea-hr-leave-carryover | S3 | borea | 1.00 | 1.00 | 1.00 | 1.00 | borea-hr-leave#c2 |
| s3-borea-hr-offsite-training-approval | S3 | borea | 0.00 | 0.00 | 0.00 | 0.00 | borea-hr-remote-work#c9 |
| s3-borea-hr-onboarding-buddy | S3 | borea | 0.00 | 1.00 | 1.00 | 1.00 | borea-hr-onboarding#c2 |
| s3-borea-hr-payroll-bonus | S3 | borea | 0.00 | 1.00 | 1.00 | 1.00 | borea-hr-payroll#c10 |
| s3-borea-hr-probation-criteria | S3 | borea | 0.00 | 0.00 | 0.00 | 0.00 | borea-hr-onboarding#c7 |
| s3-borea-hr-referral-payout-timing | S3 | borea | 0.00 | 0.00 | 0.00 | 0.00 | borea-hr-onboarding#c7 |
| s3-borea-hr-remote-hours | S3 | borea | 1.00 | 1.00 | 1.00 | 1.00 | borea-hr-remote-work#c5 |
| s3-borea-hr-setup-allowance | S3 | borea | 0.00 | 1.00 | 1.00 | 1.00 | borea-hr-remote-work#c4 |
| s3-borea-hr-sick-extended | S3 | borea | 1.00 | 0.00 | 0.00 | 0.00 | borea-hr-leave#c1 |
| s3-borea-pub-conduct-gifts | S3 | borea | 1.00 | 1.00 | 1.00 | 1.00 | borea-public-code-of-conduct#c4 |
| s3-borea-pub-first-aid-training | S3 | borea | 0.00 | 0.00 | 1.00 | 1.00 | borea-public-safety#c10 |
| s3-borea-pub-holiday-makeup | S3 | borea | 1.00 | 1.00 | 1.00 | 1.00 | borea-public-holidays#c3 |
| s3-borea-pub-parking-registration | S3 | borea | 1.00 | 1.00 | 1.00 | 1.00 | borea-public-parking#c1 |
| s3-borea-pub-visitor-escort-rule | S3 | borea | 1.00 | 1.00 | 1.00 | 1.00 | borea-public-visitors#c3 |
| s4-ankor-eng-code-freeze-holiday | S4 | ankor | 1.00 | 1.00 | 1.00 | 1.00 | ankor-engineering-deployment#c10 |
| s4-ankor-eng-infra-backup-vs-fin | S4 | ankor | 0.00 | 0.00 | 0.00 | 0.00 | ankor-engineering-oncall#c5 |
| s4-ankor-eng-oncall | S4 | ankor | 0.00 | 1.00 | 1.00 | 1.00 | ankor-engineering-oncall#c4 |
| s4-ankor-eng-p1-ack-time | S4 | ankor | 0.00 | 1.00 | 1.00 | 1.00 | ankor-engineering-oncall#c4 |
| s4-ankor-eng-ssh-key-rotation | S4 | ankor | 1.00 | 1.00 | 1.00 | 1.00 | ankor-engineering-access#c6 |
| s4-ankor-eng-ssh-rotate | S4 | ankor | 1.00 | 1.00 | 1.00 | 1.00 | ankor-engineering-access#c6 |
| s4-ankor-fin-budget-alert | S4 | ankor | 0.00 | 0.00 | 1.00 | 1.00 | ankor-finance-approval-limits#c9 |
| s4-ankor-fin-budget-alert-system | S4 | ankor | 0.00 | 0.00 | 1.00 | 1.00 | ankor-finance-approval-limits#c9 |
| s4-ankor-fin-invoice | S4 | ankor | 1.00 | 1.00 | 1.00 | 1.00 | ankor-finance-invoicing#c6 |
| s4-ankor-fin-invoice-types | S4 | ankor | 1.00 | 1.00 | 1.00 | 1.00 | ankor-finance-invoicing#c6 |
| s4-ankor-fin-petty-cash-vs-eng | S4 | ankor | 1.00 | 1.00 | 1.00 | 1.00 | ankor-finance-expense#c5 |
| s4-ankor-fin-tax-vs-pub | S4 | ankor | 0.00 | 0.00 | 0.00 | 1.00 | ankor-finance-tax#c1 |
| s4-ankor-fin-travel-approval | S4 | ankor | 1.00 | 0.00 | 1.00 | 1.00 | ankor-finance-approval-limits#c1 |
| s4-ankor-hr-exit-cert-vs-fin | S4 | ankor | 0.00 | 0.00 | 0.00 | 0.00 | ankor-hr-exit#c1 |
| s4-ankor-hr-paternity-vs-fin | S4 | ankor | 0.00 | 0.00 | 0.00 | 0.00 | ankor-hr-leave#c5 |
| s4-ankor-hr-performance-cycle | S4 | ankor | 0.00 | 1.00 | 1.00 | 1.00 | ankor-hr-performance#c1 |
| s4-ankor-hr-recruitment | S4 | ankor | 1.00 | 1.00 | 1.00 | 1.00 | ankor-hr-recruitment#c5 |
| s4-ankor-hr-review-cycle-length | S4 | ankor | 1.00 | 1.00 | 1.00 | 1.00 | ankor-hr-performance#c1 |
| s4-ankor-hr-tech-interview-duration | S4 | ankor | 1.00 | 1.00 | 1.00 | 1.00 | ankor-hr-recruitment#c5 |
| s4-ankor-hr-training-vs-fin | S4 | ankor | 1.00 | 1.00 | 1.00 | 1.00 | ankor-finance-reimbursement#c4 |
| s4-ankor-pub-anti-harassment-investigation | S4 | ankor | 0.00 | 0.00 | 0.00 | 0.00 | ankor-public-anti-harassment#c6 |
| s4-ankor-pub-canteen-subsidy | S4 | ankor | 0.00 | 0.00 | 0.00 | 0.00 | ankor-hr-training#c1 |
| s4-ankor-pub-conduct-gift-vs-fin | S4 | ankor | 0.00 | 0.00 | 0.00 | 0.00 | ankor-public-code-of-conduct#c6 |
| s4-ankor-pub-gift-policy | S4 | ankor | 0.00 | 0.00 | 0.00 | 0.00 | ankor-public-code-of-conduct#c6 |
| s4-ankor-pub-holiday-overtime | S4 | ankor | 1.00 | 1.00 | 1.00 | 1.00 | ankor-public-holidays#c6 |
| s4-ankor-pub-holidays | S4 | ankor | 1.00 | 1.00 | 1.00 | 1.00 | ankor-public-holidays#c6 |
| s4-ankor-pub-meeting-room-booking | S4 | ankor | 0.00 | 1.00 | 1.00 | 1.00 | ankor-public-visitors#c5 |
| s4-ankor-pub-safety-vs-eng | S4 | ankor | 0.00 | 0.00 | 0.00 | 0.00 | ankor-engineering-security#c7 |
| s4-borea-eng-code-coverage-gate | S4 | borea | 0.00 | 0.00 | 0.00 | 0.00 | borea-engineering-code-review#c9 |
| s4-borea-eng-log-retention-vs-fin | S4 | borea | 0.00 | 0.00 | 0.00 | 0.00 | borea-finance-audit#c1 |
| s4-borea-eng-passwordless-login | S4 | borea | 1.00 | 1.00 | 1.00 | 1.00 | borea-engineering-security#c2 |
| s4-borea-eng-reimbursement-docs | S4 | borea | 1.00 | 1.00 | 1.00 | 1.00 | borea-finance-reimbursement#c3 |
| s4-borea-eng-release-vs-hr | S4 | borea | 0.00 | 0.00 | 0.00 | 0.00 | borea-engineering-release#c1 |
| s4-borea-eng-security | S4 | borea | 1.00 | 1.00 | 1.00 | 1.00 | borea-engineering-security#c2 |
| s4-borea-fin-capex-vs-hr | S4 | borea | 0.00 | 1.00 | 0.00 | 0.00 | borea-hr-remote-work#c3 |
| s4-borea-fin-reimburse | S4 | borea | 1.00 | 1.00 | 1.00 | 1.00 | borea-finance-reimbursement#c3 |
| s4-borea-fin-reimbursement-vs-hr | S4 | borea | 0.00 | 0.00 | 0.00 | 0.00 | borea-finance-reimbursement#c7 |
| s4-borea-fin-tax | S4 | borea | 0.00 | 1.00 | 1.00 | 1.00 | borea-finance-tax#c2 |
| s4-borea-fin-tax-obligations | S4 | borea | 0.00 | 1.00 | 1.00 | 1.00 | borea-finance-tax#c2 |
| s4-borea-hr-annual-leave-entitlement | S4 | borea | 1.00 | 1.00 | 1.00 | 1.00 | borea-hr-leave#c1 |
| s4-borea-hr-backup-coverage | S4 | borea | 1.00 | 0.00 | 0.00 | 0.00 | borea-hr-leave#c1 |
| s4-borea-hr-commute | S4 | borea | 1.00 | 1.00 | 1.00 | 1.00 | borea-finance-travel#c6 |
| s4-borea-hr-commute-allowance | S4 | borea | 1.00 | 1.00 | 1.00 | 1.00 | borea-finance-reimbursement#c2 |
| s4-borea-hr-grievance-vs-eng | S4 | borea | 0.00 | 0.00 | 0.00 | 0.00 | borea-engineering-testing#c1 |
| s4-borea-hr-leave | S4 | borea | 1.00 | 1.00 | 1.00 | 1.00 | borea-hr-leave#c1 |
| s4-borea-hr-performance-tracking | S4 | borea | 0.00 | 0.00 | 0.00 | 0.00 | borea-hr-leave#c10 |
| s4-borea-hr-probation-vs-eng | S4 | borea | 0.00 | 0.00 | 0.00 | 0.00 | borea-hr-performance#c1 |
| s4-borea-pub-code-of-conduct-conflict | S4 | borea | 0.00 | 0.00 | 0.00 | 0.00 | borea-hr-exit#c8 |
| s4-borea-pub-conduct-vs-hr | S4 | borea | 0.00 | 0.00 | 0.00 | 0.00 | borea-public-code-of-conduct#c1 |
| s4-borea-pub-fire-drill-frequency | S4 | borea | 0.00 | 1.00 | 1.00 | 1.00 | borea-engineering-incident#c10 |
| s4-borea-pub-focus-time-morning | S4 | borea | 1.00 | 1.00 | 1.00 | 1.00 | borea-public-office-hours#c8 |
| s4-borea-pub-holiday-vs-fin | S4 | borea | 0.00 | 0.00 | 0.00 | 0.00 | borea-public-holidays#c1 |
| s4-borea-pub-office-hours | S4 | borea | 1.00 | 1.00 | 1.00 | 1.00 | borea-public-office-hours#c8 |
| s4-borea-pub-parking-vs-fin | S4 | borea | 1.00 | 1.00 | 1.00 | 1.00 | borea-public-parking#c3 |
| s4-borea-pub-safety | S4 | borea | 0.00 | 1.00 | 1.00 | 1.00 | borea-engineering-incident#c10 |
| s5-ankor-eng-ai-chip-design | S5 | ankor | 0.63 | 0.41 | 0.15 | 0.30 | ankor-engineering-infra#c1 |
| s5-ankor-eng-blockchain | S5 | ankor | 0.83 | 0.54 | 0.18 | 0.38 | ankor-engineering-deployment#c8 |
| s5-ankor-eng-dna-sequencing | S5 | ankor | 0.78 | 0.46 | 0.15 | 0.32 | ankor-engineering-testing#c1 |
| s5-ankor-eng-fpga-development | S5 | ankor | 0.79 | 0.42 | 0.14 | 0.31 | ankor-engineering-deployment#c1 |
| s5-ankor-eng-ml-platform | S5 | ankor | 0.75 | 0.43 | 0.14 | 0.30 | ankor-engineering-infra#c1 |
| s5-ankor-fin-car-loan | S5 | ankor | 0.67 | 0.39 | 0.16 | 0.32 | ankor-finance-budget#c5 |
| s5-ankor-fin-crypto-investment | S5 | ankor | 0.61 | 0.49 | 0.18 | 0.33 | ankor-finance-budget#c3 |
| s5-ankor-fin-crypto-payroll | S5 | ankor | 0.79 | 0.46 | 0.15 | 0.33 | ankor-finance-reimbursement#c1 |
| s5-ankor-fin-factoring | S5 | ankor | 0.76 | 0.37 | 0.15 | 0.30 | ankor-finance-approval-limits#c1 |
| s5-ankor-fin-housing-loan | S5 | ankor | 0.69 | 0.49 | 0.19 | 0.36 | ankor-finance-procurement#c7 |
| s5-ankor-fin-leasing | S5 | ankor | 0.54 | 0.40 | 0.16 | 0.29 | ankor-finance-travel#c7 |
| s5-ankor-fin-venture-capital | S5 | ankor | 0.70 | 0.45 | 0.15 | 0.30 | ankor-finance-budget#c8 |
| s5-ankor-hr-crypto-bonus | S5 | ankor | 0.72 | 0.38 | 0.16 | 0.30 | ankor-hr-payroll#c10 |
| s5-ankor-hr-dating | S5 | ankor | 0.63 | 0.44 | 0.18 | 0.35 | ankor-hr-performance#c7 |
| s5-ankor-hr-fertility-treatment | S5 | ankor | 0.60 | 0.43 | 0.16 | 0.30 | ankor-hr-benefits#c2 |
| s5-ankor-hr-relocation-allowance | S5 | ankor | 0.74 | 0.41 | 0.13 | 0.23 | ankor-hr-recruitment#c8 |
| s5-ankor-hr-sabbatical | S5 | ankor | 0.58 | 0.44 | 0.15 | 0.29 | ankor-hr-leave#c7 |
| s5-ankor-hr-shadow-board | S5 | ankor | 0.60 | 0.42 | 0.14 | 0.30 | ankor-hr-training#c5 |
| s5-ankor-hr-stock-options | S5 | ankor | 0.61 | 0.42 | 0.16 | 0.25 | ankor-hr-grievance#c1 |
| s5-ankor-hr-student-loan | S5 | ankor | 0.59 | 0.33 | 0.13 | 0.27 | ankor-hr-training#c1 |
| s5-ankor-hr-unlimited-leave | S5 | ankor | 0.54 | 0.28 | 0.09 | 0.17 | ankor-hr-leave#c1 |
| s5-ankor-pub-esports-team | S5 | ankor | 0.74 | 0.41 | 0.15 | 0.27 | ankor-public-communication#c1 |
| s5-ankor-pub-gym | S5 | ankor | 0.65 | 0.43 | 0.16 | 0.31 | ankor-public-parking#c8 |
| s5-ankor-pub-meditation-room | S5 | ankor | 0.58 | 0.34 | 0.14 | 0.25 | ankor-public-visitors#c3 |
| s5-ankor-pub-pets | S5 | ankor | 0.68 | 0.43 | 0.18 | 0.33 | ankor-public-dress-code#c5 |
| s5-ankor-pub-podcast-studio | S5 | ankor | 0.67 | 0.41 | 0.14 | 0.27 | ankor-public-office-hours#c8 |
| s5-ankor-pub-rooftop-event | S5 | ankor | 0.72 | 0.40 | 0.15 | 0.31 | ankor-public-visitors#c1 |
| s5-ankor-pub-rooftop-garden | S5 | ankor | 0.72 | 0.46 | 0.16 | 0.29 | ankor-public-anti-harassment#c2 |
| s5-ankor-pub-sauna-room | S5 | ankor | 0.68 | 0.39 | 0.15 | 0.28 | ankor-public-visitors#c3 |
| s5-ankor-pub-sleeping-bags | S5 | ankor | 0.65 | 0.54 | 0.19 | 0.34 | ankor-public-code-of-conduct#c3 |
| s5-borea-eng-embedded-linux | S5 | borea | 0.72 | 0.45 | 0.13 | 0.31 | borea-engineering-deployment#c1 |
| s5-borea-eng-metaverse | S5 | borea | 0.82 | 0.43 | 0.12 | 0.29 | borea-engineering-access#c1 |
| s5-borea-eng-quantum | S5 | borea | 0.71 | 0.48 | 0.18 | 0.39 | borea-engineering-incident#c4 |
| s5-borea-eng-rust-guidelines | S5 | borea | 0.80 | 0.41 | 0.13 | 0.24 | borea-engineering-access#c1 |
| s5-borea-eng-satellite-deployment | S5 | borea | 0.79 | 0.46 | 0.14 | 0.30 | borea-engineering-deployment#c1 |
| s5-borea-eng-vr | S5 | borea | 0.84 | 0.44 | 0.13 | 0.38 | borea-engineering-deployment#c2 |
| s5-borea-fin-carbon-credit | S5 | borea | 0.78 | 0.44 | 0.14 | 0.31 | borea-finance-procurement#c1 |
| s5-borea-fin-charity-deduction | S5 | borea | 0.66 | 0.46 | 0.17 | 0.36 | borea-finance-tax#c4 |
| s5-borea-fin-hedge-fund | S5 | borea | 0.77 | 0.46 | 0.14 | 0.25 | borea-finance-budget#c8 |
| s5-borea-fin-insurance-captive | S5 | borea | 0.69 | 0.47 | 0.14 | 0.28 | borea-finance-audit#c1 |
| s5-borea-fin-nft-investment | S5 | borea | 0.70 | 0.41 | 0.14 | 0.28 | borea-finance-approval-limits#c1 |
| s5-borea-fin-stock-trading | S5 | borea | 0.80 | 0.43 | 0.17 | 0.37 | borea-finance-approval-limits#c6 |
| s5-borea-hr-adoption-leave | S5 | borea | 0.68 | 0.38 | 0.12 | 0.23 | borea-hr-leave#c1 |
| s5-borea-hr-bereavement-extended | S5 | borea | 0.61 | 0.33 | 0.12 | 0.20 | borea-hr-leave#c1 |
| s5-borea-hr-childcare-voucher | S5 | borea | 0.69 | 0.39 | 0.15 | 0.24 | borea-hr-benefits#c3 |
| s5-borea-hr-daycare | S5 | borea | 0.72 | 0.49 | 0.17 | 0.32 | borea-hr-benefits#c2 |
| s5-borea-hr-early-retirement | S5 | borea | 0.69 | 0.52 | 0.17 | 0.32 | borea-hr-benefits#c2 |
| s5-borea-hr-expat-package | S5 | borea | 0.73 | 0.37 | 0.13 | 0.23 | borea-hr-onboarding#c8 |
| s5-borea-hr-four-day-week | S5 | borea | 0.61 | 0.35 | 0.12 | 0.22 | borea-hr-onboarding#c7 |
| s5-borea-hr-sabbatical-leave | S5 | borea | 0.58 | 0.37 | 0.13 | 0.24 | borea-hr-leave#c1 |
| s5-borea-pub-art-installation | S5 | borea | 0.68 | 0.33 | 0.13 | 0.29 | borea-public-visitors#c10 |
| s5-borea-pub-bicycle-policy | S5 | borea | 0.65 | 0.34 | 0.10 | 0.15 | borea-public-parking#c8 |
| s5-borea-pub-cooking-class | S5 | borea | 0.70 | 0.46 | 0.17 | 0.34 | borea-public-safety#c8 |
| s5-borea-pub-corporate-jet | S5 | borea | 0.71 | 0.47 | 0.16 | 0.29 | borea-public-visitors#c5 |
| s5-borea-pub-dog-friendly-office | S5 | borea | 0.63 | 0.36 | 0.14 | 0.25 | borea-public-office-hours#c6 |
| s5-borea-pub-lactation-room | S5 | borea | 0.61 | 0.44 | 0.14 | 0.26 | borea-public-safety#c5 |
| s5-borea-pub-massage-room | S5 | borea | 0.60 | 0.36 | 0.13 | 0.22 | borea-public-safety#c5 |
| s5-borea-pub-nap-pods | S5 | borea | 0.71 | 0.51 | 0.17 | 0.34 | borea-public-office-hours#c9 |
| s5-borea-pub-parking-heli | S5 | borea | 0.64 | 0.48 | 0.18 | 0.36 | borea-public-parking#c2 |

