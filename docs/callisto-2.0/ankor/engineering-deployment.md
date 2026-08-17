# Quy trình triển khai — Ankor

## Chiến lược triển khai
Ankor triển khai theo chu kỳ 2 tuần (sprint-based).
Release train vào thứ Ba và thứ Năm mỗi tuần, 14:00–16:00.
Không deploy vào thứ Sáu, cuối tuần, hoặc trước ngày lễ.
Mọi thay đổi quy trình cần được communicate trước khi áp dụng chính thức.
Quy trình được review và cập nhật mỗi quý bởi Engineering Manager.

## Môi trường
Bốn môi trường: dev → staging → pre-prod → production.
Code phải pass trên staging trước khi lên pre-prod.

## Quy trình deploy
Bước 1: Merge PR vào main branch. Bước 2: CI/CD pipeline chạy (build, test, scan). Bước 3: Auto-deploy staging. Bước 4: QA verification 2 giờ. Bước 5: Manual trigger deploy production. Bước 6: Smoke test.

## Feature flags
Ankor sử dụng LaunchDarkly cho feature flags.
Feature mới deploy ẩn sau flag, bật dần (canary → 10% → 50% → 100%).

## Rollback
Rollback tự động nếu error rate tăng trên 5% trong 10 phút sau deploy.
Rollback thủ công bởi bất kỳ engineer nào trong team, không cần approval.
Mỗi deploy có bản backup trước khi apply.
Metric về cycle time và lead time được theo dõi để đánh giá hiệu quả.

## Database migration
DB migration chạy riêng trước code deploy. Migration phải backward-compatible (không break version cũ). Có rollback script cho mỗi migration. DBA review bắt buộc cho migration ảnh hưởng trên 1 triệu rows.

## Deploy ngoài giờ
Deploy hotfix ngoài giờ cần on-call engineer + Engineering Manager approval. Deploy ngoài freeze period (trước Tết, Black Friday) cần CTO approval bằng văn bản.

## CI/CD pipeline
Tech stack: GitHub Actions cho CI, ArgoCD cho CD.
Pipeline: lint → unit test → integration test → security scan (Snyk) → build Docker image → push to registry.
Pipeline target: dưới 15 phút.
- Automation script hỗ trợ các bước lặp lại để giảm thiểu human error.

## Monitoring sau deploy
Sau mỗi deploy, engineer theo dõi Datadog dashboard 30 phút: error rate, latency p99, throughput.
Alert tự động nếu metric vượt ngưỡng.
Deploy engineer chịu trách nhiệm monitor cho đến khi stable.
Mỗi bước trong quy trình đều có checklist chi tiết trên Confluence.

## Deploy freeze
Code freeze 1 tuần trước Tết Nguyên Đán và 3 ngày trước mỗi ngày lễ lớn. Trong freeze chỉ deploy hotfix P1. Engineering Manager quyết định bắt đầu/kết thúc freeze, thông báo trước 2 tuần.

