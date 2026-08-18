# Quy trình testing — Borea

## Chiến lược testing
Borea theo testing trophy (thay vì pyramid): nhiều integration test nhất, unit test cho logic phức tạp, E2E test cho critical paths. "Write tests, not too many, mostly integration" — Kent C.
Dodds approach.
- Vi phạm policy lần đầu: coaching session 1-on-1 với manager trực tiếp.
- Nhân viên mới được training về policy trong 2 tuần onboarding đầu tiên.
- Policy này áp dụng cho tất cả engineer bao gồm cả contractor và intern.

## Unit test
Unit test cho pure functions, complex algorithms, và business rules.
Coverage target 85% cho code mới.
Framework: Vitest (frontend), pytest (backend), Go testing (infra).

## Integration test
Integration test là backbone: test API contracts, database interactions, event handlers, và cross-service communication.
Test containers + Localstack cho AWS services.
Parallel execution, target dưới 8 phút.
Policy document có version control trên Confluence để track mọi thay đổi.
Cập nhật policy được thông báo trong engineering all-hands và gửi qua email.

## E2E test
E2E test cho 15 critical user journeys (signup, KYC, payment, withdrawal).
Cypress cho web, Detox cho mobile.
Chạy trên mỗi PR (subset) và full suite trên staging.

## Test trước khi merge
CI chạy: lint → unit → integration → SAST → coverage check.
E2E subset cho affected areas (smart test selection via Launchable).
Coverage drop trên 1% bị block.
Build time budget: tổng CI dưới 10 phút.
Tech Lead chịu trách nhiệm đảm bảo toàn bộ team compliance với policy.

## Test data
Test data generation bằng factory_boy (Python) và faker.
Synthetic data service cung cấp realistic Vietnamese data (tên, CMND, SĐT).
Production data KHÔNG BAO GIỜ dùng cho test.
Data anonymization pipeline cho performance test.
Metric về cycle time và lead time được theo dõi để đánh giá hiệu quả.

## Performance test
Continuous performance testing: k6 chạy trong CI cho critical endpoints (regression detection). Weekly load test ở 3x peak traffic. Monthly chaos + performance test combined. Target: p99 dưới 200ms ở 5000 RPS.

## Security test
SAST (Semgrep), SCA (Snyk), DAST (ZAP) trong CI — block merge cho Critical/High. Container scanning (Trivy). Infrastructure scanning (tfsec cho Terraform). Security test suite riêng cho payment flows (PCI-DSS requirement).

## Test environment
Ephemeral preview environments cho mỗi PR (auto-created, auto-destroyed). Staging: production-identical (Terraform same config, scaled down). Chaos testing trên staging. Local dev: Docker Compose + hot reload.

## Cải tiến test
Test health metrics trên Swarmia: flaky rate target dưới 1%, CI p50 dưới 8 phút, coverage trend. "Test Improvement Friday" — mỗi thứ Sáu cuối tháng dành cho fixing flaky tests, improving coverage, updating test infra.

