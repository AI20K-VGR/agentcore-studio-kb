# Quy trình testing — Ankor

## Chiến lược testing
Ankor áp dụng testing pyramid: nhiều unit test (70%), vừa phải integration test (20%), ít E2E test (10%). Mọi code mới phải có test. Test là phần bắt buộc của Definition of Done.

## Unit test
Unit test bắt buộc cho mọi business logic. Coverage tối thiểu 80% cho code mới, 70% overall. Framework: Jest (frontend), pytest (backend). Mock external dependencies. Unit test phải chạy dưới 5 phút.

## Integration test
Integration test cho API endpoints, database queries, và service-to-service communication. Sử dụng test containers (Docker) cho database và message queue. Chạy trong CI, target dưới 10 phút.

## E2E test
E2E test cho critical user flows (login, checkout, payment). Sử dụng Playwright. Chạy trên staging sau mỗi deploy. E2E suite target dưới 20 phút. Flaky test phải fix hoặc disable trong 48 giờ.

## Test trước khi merge
CI pipeline chạy: lint → unit test → integration test cho mỗi PR. PR không pass test không được merge. Code coverage drop trên 2% so với main branch bị block.

## Test data
Test data sử dụng factory pattern (faker library). Không dùng production data cho test. Staging có synthetic data đủ đa dạng. Test database reset trước mỗi test suite.

## Performance test
Load test hằng tháng cho API chính bằng k6. Target: p99 latency dưới 500ms ở 1000 RPS. Stress test trước mỗi major release. Performance regression test trong CI cho critical endpoints.

## Security test
SAST (Snyk) chạy trong CI. Dependency audit hằng tuần. DAST (OWASP ZAP) chạy trên staging hằng tuần. Security test coverage cho OWASP Top 10 vulnerabilities.

## Test environment
Mỗi engineer có local dev environment đầy đủ (Docker Compose). Staging environment mirror production (scaled down). Test environment reset tự động mỗi đêm. Shared staging có lịch sử dụng tránh conflict.

## Cải tiến test
Test health dashboard: coverage trend, flaky test rate, test execution time. Target: flaky rate dưới 3%, tổng CI time dưới 15 phút. Test improvement sprint mỗi quý dành 20% thời gian.
