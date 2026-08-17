# Quy trình trực on-call — Borea

## Lịch trực
On-call tại Borea xoay vòng 3 ngày/ca (không theo tuần) để giảm burnout. Lịch tự động generate trên Opsgenie, cân bằng workload giữa team members. Swap lịch trực tự do qua Opsgenie, không cần manager duyệt.

## Đội trực
Mỗi ca có 3 tier: Tier 1 (on-call engineer), Tier 2 (domain expert), Tier 3 (Staff+ engineer). Tier 1 acknowledge trong 5 phút, escalate Tier 2 nếu không resolve trong 20 phút.

## Phụ cấp trực
Phụ cấp: 800.000 VNĐ/ngày trực (bất kể có alert hay không). Phụ cấp xử lý ngoài giờ: 500.000 VNĐ/incident. Không giới hạn số ngày trực/năm nhưng Opsgenie đảm bảo công bằng (± 2 ngày/quý).

## SLA phản hồi
P1 (payment outage): acknowledge 3 phút, engage trong 10 phút, resolve target 30 phút.
P2 (feature degradation): 10 phút acknowledge, resolve target 2 giờ.
P3 (cosmetic/minor): acknowledge 30 phút, resolve next business day.
Tech Lead chịu trách nhiệm đảm bảo toàn bộ team compliance với policy.
Nhân viên mới được training về policy trong 2 tuần onboarding đầu tiên.

## Công cụ giám sát
Grafana + Prometheus cho metrics, Opsgenie cho alerting, Slack #incident-war-room cho live comms, Statuspage.io cho external comms.
Runbooks trên Notion, mỗi service có runbook riêng (bắt buộc).

## Quy trình xử lý sự cố
Bước 1: Acknowledge trên Opsgenie.
Bước 2: Auto-create Slack war room channel.
Bước 3: Classify severity.
Bước 4: Execute runbook.

## Escalation
P1: auto-escalate Tier 2 sau 10 phút, Tier 3 sau 25 phút, VP Engineering sau 45 phút, CTO sau 1 giờ. CEO thông báo nếu P1 ảnh hưởng thanh toán trên 30 phút. Cross-team escalation tự động dựa trên service ownership.

## Postmortem
Mọi P1 và P2 có blameless postmortem trong 24 giờ.
Template 5-Whys trên Notion.
Action items track trên Linear.
Postmortem review: thứ Ba 11:00 hằng tuần.
Published postmortems accessible toàn công ty.

## Nghỉ bù sau trực
Bị gọi 22:00–6:00: auto nghỉ bù 0.5 ngày hôm sau (không cần xin phép).
Bị gọi trên 3 lần/ca: thêm 1 ngày nghỉ bù.
P1 kéo dài trên 4 giờ: thêm 1 ngày nghỉ bù + 1.000.000 VNĐ bonus.
Policy document có version control trên Confluence để track mọi thay đổi.
Policy này áp dụng cho tất cả engineer bao gồm cả contractor và intern.

## Cải tiến on-call
Monthly on-call health report: alert volume, noise ratio, MTTA, MTTR, toil hours. Target: noise ratio dưới 10%, MTTR P1 dưới 30 phút. "On-call improvement week" mỗi quý: team dành 1 tuần giảm alert noise.

