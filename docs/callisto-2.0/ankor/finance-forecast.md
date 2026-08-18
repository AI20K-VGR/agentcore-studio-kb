# Quy trình dự báo tài chính — Ankor

## Mục đích
Dự báo tài chính giúp Ankor lập kế hoạch ngân sách, quản lý dòng tiền, và đưa ra quyết định đầu tư.
Dự báo bao gồm doanh thu, chi phí, lợi nhuận, và dòng tiền.

## Chu kỳ dự báo
Ankor thực hiện dự báo chính thức 2 lần/năm (tháng 4 và tháng 8) kết hợp lập ngân sách hằng năm (tháng 10–12). Dự báo dòng tiền ngắn hạn cập nhật hằng tuần.

## Phương pháp dự báo
Doanh thu: bottom-up từ pipeline Sales (Salesforce) + historical growth rate. Chi phí: top-down từ budget + trend analysis. Sử dụng 3 kịch bản: lạc quan (best case), cơ sở (base case), bi quan (worst case).

## Dữ liệu đầu vào
Sales forecast từ VP Sales. Headcount plan từ HR. CAPEX plan từ các phòng ban. Macro indicators (GDP, CPI, tỷ giá) từ Finance research. Pipeline data từ Salesforce, financial data từ SAP.

## Quy trình lập dự báo
Bước 1: Finance thu thập data (5 ngày).
Bước 2: Xây dựng model (5 ngày).
Bước 3: Review với CFO (2 ngày).
Bước 4: Challenge session với CEO + VP (1 ngày).

## Mô hình tài chính
Ankor sử dụng mô hình 3 báo cáo liên kết (P&L, Balance Sheet, Cash Flow) trên Excel. Model do FP&A analyst duy trì. Version control trên Google Drive với naming convention rõ ràng.

## Dự báo dòng tiền
Cash flow forecast 13 tuần cập nhật mỗi thứ Hai.
Kế toán thu nộp dự báo thu tiền, kế toán chi nộp dự báo chi tiền.
CFO review cash position hằng tuần.
Cash buffer tối thiểu 3 tháng OPEX.

## Đo lường độ chính xác
Accuracy đo bằng variance: actual vs forecast.
Target variance dưới 10% cho doanh thu, dưới 5% cho chi phí.

## Báo cáo dự báo
Báo cáo forecast gửi CEO và Board trước ngày 15 tháng dự báo.
Bao gồm: executive summary, key assumptions, 3 kịch bản, sensitivity analysis, và risks/opportunities.

## Cải tiến quy trình
Finance đánh giá và cải tiến quy trình dự báo hằng năm.
Mục tiêu 2026: chuyển từ Excel sang công cụ FP&A chuyên dụng (đang đánh giá Anaplan và Adaptive Planning).
- Quy trình có SLA rõ ràng, được track trên dashboard nội bộ của Finance team.
- Finance team xử lý theo batch vào các ngày cố định để tối ưu hiệu suất.

