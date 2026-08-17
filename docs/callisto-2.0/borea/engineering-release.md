# Quy trình phát hành — Borea

## Chiến lược phát hành
Borea theo continuous delivery — mỗi commit vào main có thể release bất kỳ lúc nào.
Không có release train hay scheduled release.
Feature flags kiểm soát khi nào feature visible cho users.

## Lịch phát hành
Không có lịch cố định.
Code merge vào main tự động deploy production (continuous deployment).

## Release branch
Trunk-based development: mọi PR merge trực tiếp vào main. Không có develop hay release branch. Short-lived feature branches (tối đa 2 ngày). Release tags tự động bằng semantic-release dựa trên commit messages.

## Release checklist
Automated release checklist trong CI: tests pass, security scan clean, feature flag configured, monitoring alert set, runbook updated, rollback plan auto-generated.
Manual: Product Manager confirm timing, comms prepared.

## Release notes
Auto-generated từ conventional commits (feat:, fix:, breaking:).
Product team biên tập customer-facing release notes trên Notion.
Publish lên docs.borea.vn + in-app changelog.

## QA sign-off
Không có QA sign-off gate — engineers own quality. Automated test suite là safety net. Product Manager UAT cho major features trên staging. A/B testing framework cho UI changes.

## Go/No-Go meeting
Không có Go/No-Go meeting cho regular releases.
Major launches (new product, pricing change): Launch Review với CPO, CTO, VP Eng.
Launch readiness checklist 30 mục.

## Phát hành dần (canary/progressive)
Mọi feature release qua progressive rollout: internal dogfood → beta users (1%) → early adopters (10%) → GA (100%).
Each stage tối thiểu 24 giờ.
Auto-halt nếu error rate hoặc support tickets spike.

## Thông báo phát hành
Internal: auto-post Slack #shipped khi feature flag bật. External: in-app notification, email digest hằng tuần cho customers, changelog page. Breaking API changes: 90 ngày deprecation notice + migration guide.

## Post-release review
Feature review 1 tuần sau GA: adoption metrics, error rate, customer feedback, support tickets. Feature success criteria defined trước launch, measured post-launch. Quarterly release process retro với Engineering + Product.

