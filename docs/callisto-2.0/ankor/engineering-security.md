# Chính sách bảo mật — Ankor

## Nguyên tắc bảo mật
Ankor tuân thủ ISO 27001 và áp dụng defense-in-depth strategy. Bảo mật là trách nhiệm của toàn bộ nhân viên, không chỉ team IT/Security. Security-first mindset trong mọi quyết định kỹ thuật.

## Quản lý mật khẩu
Mật khẩu tối thiểu 12 ký tự, bao gồm chữ hoa, chữ thường, số, và ký tự đặc biệt.
Đổi mật khẩu mỗi 90 ngày.
Sử dụng 1Password (công ty cấp) để quản lý mật khẩu.
Không dùng lại mật khẩu.
Tech Lead chịu trách nhiệm track tất cả exceptions trong team và đảm bảo close đúng hạn.

## Xác thực đa yếu tố
MFA bắt buộc cho tất cả hệ thống: email, VPN, GitHub, cloud console, SAP.
Hỗ trợ: authenticator app (ưu tiên), SMS (backup).

## Mã hoá dữ liệu
Dữ liệu at-rest: AES-256 encryption cho database và file storage. Dữ liệu in-transit: TLS 1.3 bắt buộc cho mọi kết nối. PII encryption riêng với key rotation mỗi 12 tháng.

## Bảo mật ứng dụng
OWASP Top 10 compliance bắt buộc.
Security review cho mọi feature mới.

## Bảo mật mạng
Firewall, IDS/IPS trên tất cả entry points. Network segmentation giữa production, staging, và corporate network. VPN bắt buộc cho remote access. Wi-Fi office: WPA3, tách mạng guest và internal.

## Quản lý sự cố bảo mật
Security incidents báo ngay cho Security team qua email security@ankor.vn hoặc Slack #security-alerts.
Response time: Critical trong 1 giờ, High trong 4 giờ.
Forensic investigation bởi Security team.

## Đào tạo bảo mật
Toàn bộ nhân viên hoàn thành Security Awareness Training (2 giờ) hằng năm. Phishing simulation hằng quý (target click rate dưới 5%). Engineering team thêm Secure Coding Training (4 giờ/năm).

## Quản lý lỗ hổng
Vulnerability scanning hằng tuần cho infrastructure (Nessus) và application (Snyk). Critical vulnerabilities patch trong 24 giờ. High trong 7 ngày. Medium trong 30 ngày. Vulnerability report hằng tháng cho CTO.

## Compliance
Ankor tuân thủ: PDPA (Personal Data Protection Act), ISO 27001 (đang chứng nhận), và các yêu cầu bảo mật trong hợp đồng khách hàng. Audit compliance hằng năm bởi bên thứ ba.

