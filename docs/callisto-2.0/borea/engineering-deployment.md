# Quy trình triển khai — Borea

## Chiến lược triển khai
Borea deploy liên tục (continuous deployment) — mỗi PR merge vào main tự động deploy production. Trung bình 15–25 deploys/ngày. Không có release train hay deploy window cố định.

## Môi trường
Ba môi trường: dev → staging → production. Mỗi PR tự động tạo preview environment riêng (Vercel/EKS). Staging mirror production 1:1 (infra as code). Không có pre-prod riêng — staging đủ tin cậy.

## Quy trình deploy
Bước 1: PR merge vào main. Bước 2: CI pipeline (build, test, scan) — 8 phút. Bước 3: Auto-deploy staging + automated E2E test. Bước 4: Auto-deploy production (canary 5% → 25% → 100% trong 30 phút). Bước 5: Auto health check.

## Feature flags
Borea sử dụng Unleash (self-hosted) cho feature flags. Mọi feature mới phải có flag. Gradual rollout: internal (dogfood) → beta users (5%) → GA (100%). Flag cleanup sprint hằng quý — xoá flag cũ trên 30 ngày.

## Rollback
Auto-rollback nếu error rate tăng 2% hoặc latency p99 tăng 50% trong 5 phút. Canary deployment tự động phát hiện regression. Manual rollback: 1-click trên ArgoCD, bất kỳ engineer nào. Target rollback time: dưới 2 phút.

## Database migration
Zero-downtime migration bắt buộc. Pattern: expand-contract (add column → backfill → migrate code → remove old column). Migration review bởi DBA team (2 người). Large migration (trên 10M rows) chạy background job.

## Deploy ngoài giờ
Continuous deployment = deploy bất kỳ lúc nào. Tuy nhiên, "significant changes" (new service, infra change) nên deploy trong giờ hành chính. Payment-critical changes cần 2 engineer approve + monitor.

## CI/CD pipeline
GitHub Actions + ArgoCD + Kubernetes. Pipeline: lint → unit test (parallel) → integration test → SAST (Semgrep) → DAST → build → push → deploy. Target pipeline time: dưới 10 phút. Flaky test auto-retry 2 lần.

## Monitoring sau deploy
Auto-monitoring 15 phút sau mỗi deploy: error rate, latency, throughput, business metrics (transaction success rate). Grafana dashboard tự động mở cho deploy engineer. Anomaly detection ML model alert proactive.

## Deploy freeze
Freeze chỉ cho payment service: 3 ngày trước Tết và ngày Peak (11/11, 12/12). Các service khác deploy bình thường. CTO quyết định freeze, thông báo 1 tuần trước. Emergency hotfix được phép trong freeze.
