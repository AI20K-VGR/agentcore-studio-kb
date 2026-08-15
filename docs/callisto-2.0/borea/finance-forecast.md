# Quy trình dự báo tài chính — Borea

## Mục đích
Dự báo tài chính tại Borea phục vụ: fundraising, board reporting, resource planning, và product investment decisions. Dự báo bao gồm revenue, burn rate, runway, và unit economics.

## Chu kỳ dự báo
Rolling forecast hằng quý (4 quý tới). Monthly forecast update cho revenue và cash. Weekly cash flow forecast. Board deck forecast update mỗi tháng. Annual long-range plan (3 năm) vào Q4.

## Phương pháp dự báo
Revenue: cohort-based model (MRR, churn, expansion) + bottoms-up từ Sales pipeline (HubSpot). Expenses: driver-based model (headcount × cost per head, infra cost per user). 3 kịch bản: Conservative, Base, Aggressive.

## Dữ liệu đầu vào
MRR/ARR data từ Stripe + NetSuite. Pipeline từ HubSpot. Headcount plan từ People Ops. Cloud cost từ AWS Cost Explorer. Market data từ CB Insights và internal research. Auto-sync vào Anaplan.

## Quy trình lập dự báo
Bước 1: Data pull tự động (1 ngày). Bước 2: Model update + scenario analysis (3 ngày). Bước 3: FP&A review (1 ngày). Bước 4: CFO sign-off (1 ngày). Bước 5: Board prep (2 ngày). Total cycle: 8 ngày làm việc.

## Mô hình tài chính
Borea dùng Anaplan cho financial modeling. Model gồm: Revenue Model (cohort + expansion), P&L, Cash Flow, Balance Sheet, Unit Economics (CAC, LTV, Payback). Audit trail tự động trên Anaplan.

## Dự báo dòng tiền
Cash flow forecast 26 tuần trên Anaplan, cập nhật tự động hằng ngày. AR/AP aging data từ NetSuite. Treasury team monitor cash daily. Minimum cash runway: 18 tháng (yêu cầu Board). Alert khi runway dưới 24 tháng.

## Đo lường độ chính xác
Forecast accuracy tracking: revenue MAPE target dưới 8%, expense MAPE dưới 5%. Monthly accuracy scorecard gửi C-level. FP&A team bonus partly tied to forecast accuracy.

## Báo cáo dự báo
Monthly forecast pack gửi C-level ngày 10. Board forecast deck gửi ngày 15. Investor update hằng quý kèm forecast summary. Dashboard real-time trên Looker cho FP&A và C-level.

## Cải tiến quy trình
Borea invest vào AI-assisted forecasting: ML model predict churn và expansion revenue. Target 2026: reduce forecast cycle từ 8 ngày xuống 5 ngày. AutoML pilot cho expense forecasting đang triển khai.
