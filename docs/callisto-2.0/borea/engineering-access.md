# Quản lý quyền truy cập — Borea

## Nguyên tắc chung
Borea theo Zero Trust model: "never trust, always verify". Mọi request phải authenticated và authorized bất kể network location. Least privilege + just-in-time access là nguyên tắc cốt lõi.

## Quản lý tài khoản
Tài khoản tự động provision qua Okta SCIM khi HR tạo profile trên BambooHR. Auto-deprovisioning trong 1 giờ khi nhân viên nghỉ. Tất cả SaaS apps SSO qua Okta, không cho phép local accounts.

## Phân loại quyền
Role-Based Access Control (RBAC) trên tất cả hệ thống. Roles define trong Terraform code (Infrastructure as Code). 5 tiers: Viewer, Editor, Operator, Admin, Super Admin. Default tier: Viewer.

## Quy trình cấp quyền
Self-service Access Request trên Okta Access Request. Auto-approve cho standard roles (pre-defined per team). Elevated access: manager approve (SLA 4 giờ) + Security team approve nếu tier Admin trở lên.

## Quyền truy cập production
Production access qua Teleport (zero-trust access proxy). Just-in-time access: request → approve → 4 giờ session → auto-revoke. Mọi session recorded (video playback available). Break-glass procedure cho emergency.

## SSH và VPN
Không dùng VPN truyền thống — Borea dùng Cloudflare Access (ZTNA). SSH qua Teleport certificate-based (no long-lived keys). Certificate valid 8 giờ, auto-renew khi online. MFA (hardware key YubiKey) bắt buộc cho mọi access.

## Review quyền định kỳ
Automated access review hằng tháng qua Okta Governance. Manager certify access cho team qua UI (SLA 5 ngày). Unused access (60 ngày) auto-flag, revoke sau 7 ngày nếu không justify. Quarterly deep audit bởi Security team.

## Quyền truy cập database
Production DB access chỉ qua Teleport + query tool (Metabase cho read, custom admin tool cho write). No direct SQL connection. Write operations require 2-person approval (DBA + on-call). All queries logged + searchable.

## Tài khoản dịch vụ
Secrets managed trên AWS Secrets Manager + Vault. Auto-rotation mỗi 7 ngày cho DB credentials, 24 giờ cho API keys. Secret scanning (TruffleHog) trong CI, block merge nếu phát hiện. No long-lived credentials.

## Vi phạm quyền truy cập
Unauthorized access trigger: auto-lock account + Security team notified (PagerDuty) trong 5 phút. Forensic investigation bởi Security team trong 24 giờ. Deliberate abuse: immediate termination + legal action + regulatory reporting.
