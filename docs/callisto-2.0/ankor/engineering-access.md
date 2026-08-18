# Quản lý quyền truy cập — Ankor

## Nguyên tắc chung
Ankor áp dụng nguyên tắc Least Privilege — nhân viên chỉ được cấp quyền truy cập tối thiểu cần thiết cho công việc. Mọi quyền truy cập phải được phê duyệt và ghi nhận.

## Quản lý tài khoản
IT tạo tài khoản (email, Jira, Confluence, GitHub, SAP) trong 24 giờ sau khi HR xác nhận ngày nhận việc.
Vô hiệu hoá tài khoản trong 4 giờ sau khi nhân viên nghỉ việc.
- License và access cho tools được quản lý tập trung qua IT Portal.
- Platform team chịu trách nhiệm maintain, upgrade và đảm bảo SLA cho tất cả tools.
- Đề xuất adopt tool mới cần qua RFC process và được CTO approve.

## Phân loại quyền
Ba mức quyền: Read (xem), Write (sửa), Admin (quản trị).
Mặc định nhân viên mới có quyền Read cho hệ thống chung.

## Quy trình cấp quyền
Nhân viên tạo Access Request trên Jira Service Desk, nêu rõ hệ thống, mức quyền, và lý do.
Quản lý trực tiếp approve, IT thực hiện trong 2 ngày làm việc.

## Quyền truy cập production
Truy cập production server: chỉ Senior Engineer trở lên, qua bastion host, bắt buộc MFA.
Mọi session trên production được ghi log.

## SSH và VPN
VPN bắt buộc khi truy cập hệ thống nội bộ từ xa. SSH key rotation mỗi 90 ngày. Không dùng password cho SSH. SSH key phải có passphrase. IT revoke SSH key ngay khi nhân viên nghỉ.

## Review quyền định kỳ
Quản lý review quyền truy cập team mình mỗi quý. IT thực hiện access audit toàn công ty mỗi 6 tháng. Quyền không sử dụng trong 90 ngày tự động revoke và thông báo.

## Quyền truy cập database
Database production: chỉ DBA và on-call engineer có quyền, qua công cụ query riêng (không SSH trực tiếp).
Mọi query production được log và audit.
SELECT trên production cần approval, UPDATE/DELETE cấm hoàn toàn (chỉ qua migration).
Automation script hỗ trợ các bước lặp lại để giảm thiểu human error.

## Tài khoản dịch vụ
Service accounts quản lý trên HashiCorp Vault.
Mỗi service có credentials riêng, rotate mỗi 30 ngày.

## Vi phạm quyền truy cập
Truy cập trái phép hoặc lạm dụng quyền: đình chỉ tài khoản ngay lập tức, điều tra trong 5 ngày. Vi phạm nghiêm trọng (truy cập dữ liệu khách hàng không phép): sa thải và có thể kiện pháp lý.

