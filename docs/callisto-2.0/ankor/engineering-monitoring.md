# Giám sát hệ thống — Ankor

## Chiến lược monitoring
Ankor áp dụng "3 pillars of observability": metrics, logs, traces. Mọi service phải có đủ 3 pillar. Monitoring-first: thêm monitoring trước khi deploy feature mới.

## Metrics
Datadog cho metrics collection và visualization. Mỗi service phải expose: request rate, error rate, latency (RED metrics). Business metrics: active users, API calls, revenue-related. Custom dashboards cho mỗi team.

## Logging
Centralized logging trên Datadog Logs. Structured logging (JSON) bắt buộc. Log levels: DEBUG (dev only), INFO, WARN, ERROR, FATAL. Log retention: 30 ngày hot, 90 ngày cold. PII không được log (masking tự động).

## Distributed tracing
Datadog APM cho distributed tracing. Mọi request có trace ID xuyên suốt các service. Sampling rate: 100% cho errors, 10% cho success. Trace giúp debug latency và tìm bottleneck.

## Alerting
Alert rules trên Datadog Monitors. Alert routing qua PagerDuty. 3 mức alert: Critical (page on-call ngay), Warning (Slack notification), Info (dashboard only). Target: dưới 50 alerts/tuần cho toàn hệ thống.

## Dashboard
Dashboard hierarchy: Executive (availability, SLA), Team (service health), On-call (real-time ops). Mỗi service có Service Level Dashboard với SLI/SLO. TV dashboard tại khu vực engineering.

## SLO (Service Level Objectives)
SLO cho API chính: availability 99.5%, latency p99 dưới 500ms. SLO cho background jobs: completion rate 99.9%. SLO tracking hằng tuần, error budget review hằng tháng.

## Uptime monitoring
Synthetic monitoring (Datadog Synthetics) cho 10 critical endpoints, check mỗi 1 phút. Status page (Statuspage.io) công khai cho khách hàng. Uptime target: 99.5%/tháng.

## Capacity planning
Capacity review hằng quý: CPU/Memory utilization trend, database growth, storage usage. Forecast 6 tháng dựa trên growth rate. Scale-up request nộp trước 1 tháng cho DevOps.

## Cải tiến monitoring
Monitoring health review mỗi quý: alert noise ratio, false positive rate, coverage gaps. Target: noise ratio dưới 20%. Mỗi postmortem kiểm tra monitoring gap và bổ sung alert/dashboard.
