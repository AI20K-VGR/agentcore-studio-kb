# Quy trình xử lý sự cố — Borea

## Phân loại sự cố
P1 — Critical: payment processing down, data breach, full outage. P2 — High: feature degradation trên 30% users, latency tăng 5x. P3 — Medium: single feature broken, workaround available. P4 — Low: cosmetic issues.

## Phát hiện sự cố
Detection channels: Grafana alerts (metrics), Sentry (errors), PagerDuty (synthetic monitors), customer reports (#support Slack), social media monitoring.
Auto-incident creation trên Opsgenie khi alert P1/P2.
Mỗi team được khuyến khích customize dashboard theo nhu cầu riêng của mình.
Grafana dashboard được cấu hình sẵn template cho các metrics quan trọng nhất.
Metrics retention policy: raw data giữ 30 ngày, aggregated data giữ 1 năm.

## Incident Commander
P1: Incident Commander (IC) tự động assign từ IC on-call rotation (Staff+ engineers). IC dedicated — không fix, chỉ coordinate. P2: engineer on-call tự manage, escalate nếu cần. Borea train 20 IC-certified engineers.

## Quy trình xử lý
Bước 1: Auto-detect & create incident (0 min).
Bước 2: IC join war room (3 min).

## Truyền thông sự cố
P1: auto-update Statuspage.io mỗi 10 phút. Slack war room real-time. CEO/CTO auto-notified. Customer Success team notified để proactive outreach. P2: update mỗi 20 phút. External comms: chỉ qua Statuspage, không social media.

## SLA xử lý
P1 MTTR target: 15 phút (payment), 30 phút (non-payment). P2: 2 giờ. P3: 1 sprint. P4: backlog. Availability target: 99.99% cho payment, 99.9% cho non-payment. SLA dashboard real-time trên Grafana.

## Postmortem
P1 postmortem trong 24 giờ, P2 trong 48 giờ.
Blameless culture — focus on systems, not people.
Format: 5-Whys + timeline + action items.
Published trên Notion, accessible toàn engineering.
Monthly postmortem review session.

## Prevention
Mỗi postmortem tối thiểu 3 action items (detect, mitigate, prevent). Action items prioritize trong sprint planning. Chaos engineering program: monthly "break things" exercises. Quarterly resilience review.

## Báo cáo sự cố
Weekly incident digest trên Slack #engineering. Monthly SRE report: availability, MTTR, incident count by severity, top 5 root causes. Quarterly reliability review với CTO + VP Eng. Board report cho P1 ảnh hưởng revenue.

## Diễn tập sự cố
"Chaos Day" hằng tháng — inject failure vào production (controlled). Chaos Monkey chạy liên tục trên non-critical services. Annual "Disaster Recovery Test" — full failover sang DR region. Kết quả track trên reliability scorecard.

