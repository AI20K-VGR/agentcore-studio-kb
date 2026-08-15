# Quy trình trực on-call — Ankor

## Lịch trực
Đội Engineering Ankor trực on-call theo tuần, xoay vòng giữa các thành viên. Lịch trực lập trước 1 tháng trên PagerDuty. Mỗi đợt trực bắt đầu thứ Hai 9:00 và kết thúc thứ Hai tuần sau 9:00.

## Đội trực
Mỗi ca trực có 2 người: Primary (phản hồi đầu tiên) và Secondary (backup). Primary có tối đa 15 phút để acknowledge alert. Nếu không acknowledge, auto-escalate sang Secondary.

## Phụ cấp trực
Phụ cấp on-call: 1.500.000 VNĐ/tuần trực ngày thường, 2.500.000 VNĐ/tuần có ngày lễ. Phụ cấp xử lý sự cố ngoài giờ: 200.000 VNĐ/incident. Tối đa 8 tuần trực/năm cho mỗi engineer.

## SLA phản hồi
P1 (hệ thống sập hoàn toàn): acknowledge trong 5 phút, bắt đầu xử lý trong 15 phút. P2 (chức năng chính bị ảnh hưởng): 15 phút acknowledge, 30 phút bắt đầu. P3 (ảnh hưởng nhỏ): 1 giờ acknowledge, xử lý trong giờ hành chính.

## Công cụ giám sát
Ankor sử dụng Datadog cho monitoring, PagerDuty cho alerting, và Slack #incidents cho communication. Runbook cho các sự cố phổ biến lưu trên Confluence.

## Quy trình xử lý sự cố
Bước 1: Acknowledge alert trên PagerDuty. Bước 2: Đánh giá mức độ (P1/P2/P3). Bước 3: Thông báo trên Slack #incidents. Bước 4: Troubleshoot theo runbook. Bước 5: Resolve và cập nhật status page.

## Escalation
P1 không giải quyết trong 30 phút: escalate lên Engineering Manager. 1 giờ: escalate CTO. P2 không giải quyết trong 2 giờ: escalate Engineering Manager. Escalation matrix trên PagerDuty.

## Postmortem
Mọi P1 và P2 phải có postmortem (blameless) trong 48 giờ sau resolve. Template postmortem trên Confluence. Postmortem review meeting hằng tuần thứ Tư 10:00.

## Nghỉ bù sau trực
Nếu on-call engineer bị gọi xử lý sự cố giữa đêm (22:00–6:00), được đi muộn hoặc nghỉ bù 4 giờ ngày hôm sau. Trực tuần có sự cố P1 được thêm 1 ngày nghỉ bù.

## Cải tiến on-call
On-call health review hằng quý: số lượng alert, false positive rate, MTTA, MTTR. Target: false positive dưới 20%, MTTR P1 dưới 1 giờ. Toil reduction goal: giảm 10% alert volume mỗi quý.
