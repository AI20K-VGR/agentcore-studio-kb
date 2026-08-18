# Quy trình code review — Ankor

## Nguyên tắc chung
Mọi code change tại Ankor phải qua code review trước khi merge vào main branch. Không ai được merge code của chính mình mà không có approval. Code review là cơ hội học hỏi, không phải gatekeeping.

## Yêu cầu approval
Tối thiểu 1 approval từ reviewer cùng team.
PR thay đổi trên 500 dòng cần 2 approvals.

## Thời gian review
SLA review: trong 4 giờ làm việc cho PR nhỏ (dưới 200 dòng), 8 giờ cho PR lớn.
PR chưa review sau 24 giờ: auto-ping reviewer trên Slack.

## PR guidelines
PR phải có: title rõ ràng, description giải thích WHY (không chỉ WHAT), link Jira ticket, screenshots cho UI change.
PR tối đa 400 dòng (khuyến khích); trên 500 dòng phải có lý do.
Shadow IT — tools không được phê duyệt — bị cấm sử dụng cho production data.

## Checklist review
Reviewer kiểm tra: logic đúng, test coverage đủ (≥80%), không có security vulnerabilities, code readable, naming convention đúng, error handling, performance implications, backward compatibility.

## Automated checks
CI pipeline chạy tự động khi tạo PR: linting (ESLint/Ruff), unit tests, integration tests, security scan (Snyk), code coverage check. PR không pass CI không được merge.

## Comment conventions
Reviewer dùng prefix: [nit] (nhỏ, không block), [suggestion] (gợi ý cải thiện), [question] (hỏi để hiểu), [blocking] (phải sửa trước merge).
Chỉ [blocking] ngăn merge.

## CODEOWNERS
File CODEOWNERS trên GitHub gán reviewer tự động theo thư mục/file.
Thay đổi file trong CODEOWNERS cần approval từ owner đó.
Cập nhật CODEOWNERS khi team structure thay đổi.

## Stacked PRs
Khuyến khích stacked PRs cho feature lớn: chia thành nhiều PR nhỏ, mỗi PR có thể review và merge độc lập.
Dùng git rebase để keep stack clean.
Nhân viên mới được training về policy trong 2 tuần onboarding đầu tiên.

## Metrics và cải tiến
Track: PR cycle time (target dưới 24 giờ), review throughput, number of review rounds.
Engineering Manager review metrics hằng tháng.
Code review retrospective mỗi quý.

