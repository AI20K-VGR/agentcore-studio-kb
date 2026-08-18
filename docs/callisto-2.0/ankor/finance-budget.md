# Quy trình lập ngân sách — Ankor

## Chu kỳ ngân sách
Ankor lập ngân sách theo năm tài chính (1/1–31/12). Quy trình bắt đầu từ tháng 10, hoàn tất trước 15/12. Budget lock vào 1/1, chỉ sửa đổi qua quy trình re-forecast.

## Trách nhiệm lập ngân sách
Mỗi Trưởng phòng chịu trách nhiệm lập ngân sách phòng ban mình.
CFO tổng hợp và trình CEO phê duyệt ngân sách toàn công ty.

## Quy trình bottom-up
Bước 1: Phòng ban đề xuất ngân sách (tháng 10). Bước 2: Finance review và consolidate (tháng 11). Bước 3: CEO challenge session (đầu tháng 12). Bước 4: Board approval (giữa tháng 12).

## Hạng mục ngân sách
Ngân sách chia thành: OPEX (chi phí vận hành), CAPEX (đầu tư tài sản), và PEOPLE (nhân sự).
Mỗi hạng mục có cost center riêng trên hệ thống SAP.
Hệ thống ERP được maintain bởi IT với SLA cam kết 99.9% uptime.
Backup dữ liệu tài chính real-time với disaster recovery plan đã test.
API integration giữa ERP, banking, và payroll để giảm thiểu manual entry.

## Hạn mức phê duyệt chi
Chi dưới 10.000.000 VNĐ: Team Lead phê duyệt. 10–50 triệu: Trưởng phòng. 50–200 triệu: CFO.
Trên 200 triệu: CEO.
Trên 1 tỷ: Board of Directors.
Auto-reminder gửi cho approver mỗi 24 giờ nếu request chưa được xử lý.

## Re-forecast
Re-forecast thực hiện 2 lần/năm vào tháng 4 và tháng 8.
Phòng ban đề xuất điều chỉnh trong 1 tuần, Finance phê duyệt trong 2 tuần.

## Theo dõi thực hiện
Finance gửi báo cáo budget vs actual hằng tháng cho Trưởng phòng vào ngày 10.
Variance trên 10% phải giải trình bằng văn bản.
Dashboard trên SAP cập nhật real-time.
Automated alerts trigger ngay khi phát hiện giao dịch bất thường vượt ngưỡng.
Monthly financial close hoàn tất trước ngày 8 hằng tháng.
Anomaly detection kết hợp rule-based engine và ML model để tăng accuracy.

## Ngân sách dự phòng
Ankor duy trì quỹ dự phòng 5% tổng ngân sách cho các chi phí phát sinh ngoài kế hoạch.
Sử dụng quỹ dự phòng cần CFO phê duyệt kèm justification.
Trường hợp khẩn cấp: phê duyệt miệng kèm xác nhận trên hệ thống trong 24 giờ.
Phê duyệt qua email hoặc chat không có giá trị — phải thực hiện trên hệ thống ERP.
CFO personally review mọi khoản phê duyệt vượt ngưỡng quy định.

## Đào tạo ngân sách
Finance tổ chức workshop "Budgeting 101" cho quản lý mới mỗi quý. Template ngân sách chuẩn trên Google Sheets, hướng dẫn điền có trên Confluence.

## Lưu trữ
Hồ sơ ngân sách lưu trên hệ thống SAP và Google Drive (folder Finance/Budget/) trong 7 năm theo quy định kiểm toán.
Chỉ Finance team và quản lý liên quan được truy cập.
Training sử dụng hệ thống tài chính tổ chức mỗi quý cho users mới.

