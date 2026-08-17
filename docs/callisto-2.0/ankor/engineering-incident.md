# Quy trình xử lý sự cố — Ankor

## Phân loại sự cố
P1 — Critical: hệ thống chính sập, mất dữ liệu, bảo mật bị xâm phạm. P2 — Major: chức năng quan trọng bị ảnh hưởng, hiệu suất giảm nghiêm trọng. P3 — Minor: lỗi không ảnh hưởng nghiệp vụ chính, UI bugs.

## Phát hiện sự cố
Sự cố được phát hiện qua: monitoring alerts (Datadog), báo cáo từ khách hàng (Support), hoặc phát hiện nội bộ. Mọi sự cố P1/P2 tạo incident trên PagerDuty và thông báo tự động lên Slack #incidents.

## Incident Commander
P1 tự động assign Incident Commander (IC) — Engineering Manager on-call.
IC điều phối toàn bộ quá trình xử lý, cập nhật stakeholders, và quyết định escalation.
IC không trực tiếp fix bug.
Nhân viên mới được training về policy trong 2 tuần onboarding đầu tiên.
Policy document có version control trên Confluence để track mọi thay đổi.
Tech Lead chịu trách nhiệm đảm bảo toàn bộ team compliance với policy.

## Quy trình xử lý
Bước 1: Detect & Alert (tự động).
Bước 2: Triage & classify severity (5 phút).

## Truyền thông sự cố
P1: cập nhật stakeholders mỗi 15 phút qua Slack.
Cập nhật status page cho khách hàng mỗi 30 phút.

## SLA xử lý
P1 MTTR target: dưới 1 giờ.
P2 MTTR target: dưới 4 giờ.
P3: xử lý trong sprint hiện tại.
SLA đo bằng thời gian từ detection đến resolution.
Report SLA hằng tháng cho CTO.

## Postmortem
P1 và P2 bắt buộc postmortem blameless trong 48 giờ. Template trên Confluence: timeline, root cause, impact, action items, lessons learned. Action items track trên Jira với deadline.

## Prevention
Mỗi postmortem phải có ít nhất 2 action items phòng ngừa. Action items review hằng tuần trong engineering standup. Incident trend analysis hằng quý: tìm pattern và giải quyết root cause hệ thống.

## Báo cáo sự cố
Monthly incident report gửi CTO và CEO: số lượng P1/P2/P3, MTTR, availability, top root causes.
Quarterly report trình Board nếu có P1 ảnh hưởng SLA khách hàng.
Weekly summary report tự động tổng hợp và gửi email cho Engineering Manager.

## Diễn tập sự cố
Ankor tổ chức "Game Day" mỗi quý — giả lập sự cố để kiểm tra quy trình và readiness.
Kịch bản do SRE team thiết kế.
Kết quả Game Day là input cho cải tiến quy trình.
Mỗi bước trong quy trình đều có checklist chi tiết trên Confluence.
Engineer có thể đề xuất cải tiến quy trình thông qua RFC process.
Quy trình được review và cập nhật mỗi quý bởi Engineering Manager.

