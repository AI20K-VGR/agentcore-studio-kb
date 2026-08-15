# Quản lý chi phí — Borea

## Phân loại chi phí
Borea phân chi phí theo: COGS (infrastructure, payment processing), Sales & Marketing, R&D, G&A, và People. Mỗi khoản gán cost center + project code trên NetSuite. Tag thêm department và product line.

## Ngân sách chi phí hằng tháng
Monthly burn rate theo dõi hằng tuần trên Looker. Chi vượt 15% budget tháng trigger auto-escalation đến CFO. Budget underspend tự động rollover 50% sang tháng sau trong cùng quý.

## Chi phí cố định
Chi phí cố định (cloud hosting, SaaS tools, rent, headcount) review đầu quý. Optimize SaaS stack hằng quý — Finance + IT cùng audit license usage. Target: utilization rate trên 80% cho mỗi tool.

## Chi phí biến đổi
Chi phí biến đổi (cloud compute, marketing spend, events) scale theo revenue. Finance set guardrail: marketing spend không quá 25% revenue, cloud cost không quá 15% revenue.

## Corporate card
Toàn bộ nhân viên từ Team Lead trở lên nhận corporate card (Brex) hạn mức theo cấp. Tự động sync transaction vào Expensify. Không dùng petty cash — mọi chi phí qua card hoặc Expensify.

## Kiểm soát chi phí
Real-time cost monitoring trên Looker dashboard. Finance gửi "Weekly Burn Report" mỗi thứ Hai trên Slack #finance-updates. Anomaly detection tự động flag chi phí bất thường (trên 2x mức trung bình).

## Chi phí liên phòng ban
Internal cost allocation tự động hằng tháng trên NetSuite dựa trên usage metrics (headcount, compute hours, office space). Transfer pricing cho inter-company nếu có entity nước ngoài.

## Chi phí ngoài kế hoạch
Dưới 50 triệu: VP duyệt + Finance log. 50–200 triệu: CFO duyệt với business case 1 trang. Trên 200 triệu: CEO + Board informed. Emergency spend quy trình riêng (xem DoA policy).

## Báo cáo chi phí
Monthly P&L gửi C-level ngày 8. Board report gửi ngày 15 hằng tháng. Unit economics dashboard (CAC, LTV, payback period) update real-time. Department leaders xem spend vs budget trên Looker.

## Tối ưu chi phí
"FinOps Review" hằng tháng cho cloud cost (Engineering + Finance). Vendor renegotiation cycle hằng năm cho top 20 vendors. Borea target: gross margin trên 65%, operating margin trên 15%.
