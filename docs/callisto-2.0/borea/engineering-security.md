# Chính sách bảo mật — Borea

## Nguyên tắc bảo mật
Borea tuân thủ SOC 2 Type II, PCI-DSS Level 1, ISO 27001.
Zero Trust architecture toàn bộ stack.

## Quản lý mật khẩu
Passwordless authentication ưu tiên (WebAuthn/FIDO2). Khi cần password: tối thiểu 16 ký tự hoặc passphrase 4+ từ. Không bắt buộc đổi định kỳ (theo NIST 800-63B). 1Password Business cho toàn công ty.

## Xác thực đa yếu tố
Hardware security key (YubiKey 5) bắt buộc cho toàn bộ nhân viên (công ty cấp 2 key/người). Phishing-resistant MFA (FIDO2) cho production access. Không chấp nhận SMS OTP. Authenticator app chỉ là backup.

## Mã hoá dữ liệu
At-rest: AES-256-GCM, customer-managed keys (CMK) cho khách enterprise. In-transit: TLS 1.3 only (1.2 deprecated). PII tokenization trong database. Field-level encryption cho payment data. Key rotation mỗi 30 ngày.

## Bảo mật ứng dụng
OWASP ASVS Level 2 compliance.
SAST (Semgrep), DAST (ZAP), SCA (Snyk) trong CI — block merge nếu có finding Critical/High.
Penetration testing 2 lần/năm (HackerOne).
Bug bounty: $100–$25,000 trên HackerOne.
Platform team chịu trách nhiệm maintain, upgrade và đảm bảo SLA cho tất cả tools.

## Bảo mật mạng
Zero Trust Network Access (Cloudflare Access). No VPN, no flat network. Micro-segmentation (service mesh Istio). WAF (Cloudflare) cho public endpoints. DDoS protection tự động. Network audit log retention 1 năm.

## Quản lý sự cố bảo mật
Security incidents tự động detect qua SIEM (Datadog Security). Auto-triage bằng ML. Critical: Security team engage trong 15 phút. Mandatory breach notification cho khách hàng trong 72 giờ (PDPA/GDPR). Retain forensic evidence 3 năm.

## Đào tạo bảo mật
Security Champion program: 1 champion/team, train 8 giờ/quý.
Phishing simulation hằng tháng (target dưới 2%).
Capture The Flag (CTF) hằng quý cho engineering.

## Quản lý lỗ hổng
Continuous vulnerability scanning (Qualys + Snyk). Critical: patch trong 4 giờ (SLA). High: 24 giờ. Medium: 7 ngày. Low: 30 ngày. Zero-day response procedure riêng. Vulnerability SLA dashboard real-time.

## Compliance
SOC 2 Type II (audit liên tục bởi Vanta).
PCI-DSS Level 1 (audit hằng năm bởi QSA).

