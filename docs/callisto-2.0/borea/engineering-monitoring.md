# Giám sát hệ thống — Borea

## Chiến lược monitoring
Borea theo OpenTelemetry standard cho observability.
Vendor-agnostic instrumentation. "You build it, you monitor it" — mỗi team own monitoring cho service mình.
Observability as Code (dashboards, alerts trong Git).
Mỗi team được khuyến khích customize dashboard theo nhu cầu riêng của mình.
Alert routing tự động đến on-call engineer qua PagerDuty hoặc OpsGenie.

## Metrics
Prometheus + Grafana cho metrics.
Mỗi service expose RED metrics (Rate, Error, Duration) và USE metrics (Utilization, Saturation, Errors) cho infrastructure.
Business metrics pipeline riêng qua Kafka → ClickHouse → Grafana.
- Mỗi bước trong quy trình đều có checklist chi tiết trên Confluence.

## Logging
Loki cho log aggregation (cost-effective hơn ELK).
Structured logging (JSON) bắt buộc với correlation ID.
Log levels chuẩn theo RFC 5424.

## Distributed tracing
Jaeger cho distributed tracing, instrumented qua OpenTelemetry SDK. Trace context propagation tự động cho gRPC, HTTP, Kafka. Sampling: 100% cho errors và slow requests (p99), 5% cho normal. Trace search trên Grafana Tempo.

## Alerting
Alertmanager (Prometheus) cho routing. Alert-as-code trong Git (YAML). PagerDuty integration cho critical. Slack cho warning. 4 mức: P1 (page), P2 (Slack urgent), P3 (Slack), P4 (dashboard). Target: dưới 20 actionable alerts/tuần.

## Dashboard
Dashboard hierarchy: Board (business KPIs), C-level (platform health), Team (service dashboard), On-call (live ops).
Grafana dashboards version-controlled.

## SLO (Service Level Objectives)
SLO framework: mỗi service define SLI (indicator) → SLO (target) → error budget.
Payment SLO: 99.99% availability, p99 dưới 200ms.
Non-payment: 99.9%, p99 dưới 300ms.
Error budget policy: freeze deploy khi budget hết.
Mọi thay đổi quy trình cần được communicate trước khi áp dụng chính thức.

## Uptime monitoring
Synthetic monitoring (Grafana Synthetic Monitoring) cho 30 critical endpoints, check mỗi 30 giây từ 5 locations.
Statuspage.io với auto-incident creation.

## Capacity planning
Auto-scaling handles short-term. Long-term: quarterly capacity planning dựa trên growth forecast. FinOps + Platform team co-own. Capacity model trên Looker: predict khi nào cần upgrade database/cluster. Lead time: 2 tuần cho major changes.

## Cải tiến monitoring
Monthly observability review: alert quality (signal-to-noise target 90%), coverage score per service (target 100%), MTTD (mean time to detect) target dưới 2 phút.
Observability guild (cross-team) meet bi-weekly.
Grafana dashboard được cấu hình sẵn template cho các metrics quan trọng nhất.

