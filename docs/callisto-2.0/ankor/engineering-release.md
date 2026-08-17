# Quy trình phát hành — Ankor

## Chiến lược phát hành
Ankor phát hành phiên bản chính (major release) mỗi quý và phiên bản phụ (minor release) mỗi 2 tuần theo sprint.
Hotfix phát hành bất kỳ lúc nào khi cần.
Semantic versioning (MAJOR.MINOR.PATCH).
Vi phạm policy lần đầu: coaching session 1-on-1 với manager trực tiếp.

## Lịch phát hành
Minor release: thứ Ba tuần chẵn lúc 14:00.
Major release: thứ Ba tuần đầu mỗi quý.

## Release branch
Workflow: feature branches → develop → release branch → main. Release branch tạo 2 ngày trước release date. Chỉ bug fixes được cherry-pick vào release branch, không thêm feature mới.

## Release checklist
Checklist 15 mục: code freeze, QA sign-off, security scan pass, performance test pass, release notes viết, rollback plan có, monitoring dashboard chuẩn bị, on-call engineer sẵn sàng, stakeholders thông báo.

## Release notes
Release notes viết bằng tiếng Việt cho internal, tiếng Anh cho khách hàng.
Nội dung: features mới, bug fixes, breaking changes, known issues.
Template trên Confluence.
Product Manager review trước khi publish.
Nhân viên mới được training về policy trong 2 tuần onboarding đầu tiên.
Policy document có version control trên Confluence để track mọi thay đổi.

## QA sign-off
QA team test regression trên staging trong 1 ngày trước release. Test cases từ TestRail. Nếu có bug Critical/High chưa fix: hoãn release. QA Manager ký sign-off trên Jira release ticket.

## Go/No-Go meeting
Meeting 30 phút trước mỗi major release với: Engineering Manager, QA Manager, Product Manager, DevOps. Review: test results, known risks, rollback plan. Quyết định Go/No-Go bằng consensus.

## Phát hành dần (canary)
Major release: canary deployment cho 10% traffic trong 2 giờ → 50% trong 2 giờ → 100%.
Monitor error rate và latency.

## Thông báo phát hành
Internal: Slack #releases + email toàn Engineering.
External: release notes trên docs.ankor.vn + email cho khách hàng enterprise.
Breaking changes: thông báo 2 tuần trước release, hỗ trợ migration.
- Automation script hỗ trợ các bước lặp lại để giảm thiểu human error.
- Mỗi bước trong quy trình đều có checklist chi tiết trên Confluence.
- Trường hợp khẩn cấp cho phép rút gọn quy trình nhưng phải bổ sung đầy đủ sau 24 giờ.

## Post-release review
Review 30 phút sau mỗi major release (ngày hôm sau): số bugs phát sinh, customer feedback, deployment metrics.
Action items cho sprint tiếp theo.
Retro release process mỗi quý.

