# Quy trình code review — Borea

## Nguyên tắc chung
Code review tại Borea là bắt buộc cho mọi thay đổi, kể cả config changes và documentation. Văn hoá review: constructive, respectful, educational. "Ship fast, review fast" — không để PR chờ lâu.

## Yêu cầu approval
Tối thiểu 2 approvals: 1 từ team member + 1 từ khác team (cross-team review). PR chạm vào payment code cần thêm 1 approval từ Security Champion. PR infra (Terraform) cần Platform team approval.

## Thời gian review
SLA: 2 giờ cho PR dưới 100 dòng, 4 giờ cho dưới 300 dòng, 8 giờ cho PR lớn. Auto-assign reviewer qua GitHub round-robin. PR quá 8 giờ chưa review: escalate lên Tech Lead. Urgent: Slack @reviewer, SLA 30 phút.

## PR guidelines
PR template bắt buộc: Summary, Motivation, Changes, Testing, Screenshots, Rollback plan. PR tối đa 300 dòng (hard limit trừ auto-generated code). Feature PR phải link Linear ticket và design doc (nếu có).

## Checklist review
Automated checklist trên GitHub: tests pass, coverage ≥85%, no security findings, lint clean, no secrets in code. Manual checklist: edge cases, error handling, observability (logs, metrics, traces), backward compatibility, data privacy.

## Automated checks
CI: lint → unit test (parallel) → integration test → SAST (Semgrep) → dependency audit → coverage → build. PR decoration: code coverage diff, bundle size diff, performance benchmark diff. All green required to merge.

## Comment conventions
Prefix system: 🔴 [must] (blocking), 🟡 [should] (strongly suggested), 🟢 [nit] (optional), 💬 [discuss] (open question), 🎓 [learn] (educational, FYI). Only 🔴 blocks merge. Reviewer phải leave at least 1 positive comment.

## CODEOWNERS
CODEOWNERS granular đến từng directory. Auto-assign 1 reviewer từ CODEOWNERS + 1 random reviewer cho cross-pollination. CODEOWNERS update trong PR khi ownership change, cần 2 approvals.

## Stacked PRs
Borea sử dụng Graphite cho stacked PRs. Feature lớn chia thành 3–5 stacked PRs. Mỗi stack tự động rebase khi stack trước merge. Review từng stack song song. Target: mỗi stack dưới 150 dòng.

## Metrics và cải tiến
Track trên Swarmia: PR cycle time (target dưới 12 giờ), first review time (target dưới 2 giờ), review depth, approval-to-merge time. Weekly engineering health dashboard. Quarterly code review retro.
