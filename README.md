# agentcore-studio-kb

> KB pipeline + fence-DATA: `kb.search` + chunk-level RLS (fence F5).

**Owner:** DE — Nguyễn Đông Anh · **Loại:** uv workspace member (Python 3.14) · **Repo cha:** [agentcore-studio-kit](https://github.com/hieubui2409/agentcore-studio-kit)

## Repo này là gì
Submodule `packages/kb` của workspace `agentcore-studio-kit`. Owner: **DE — Nguyễn Đông Anh**. Chứa KB pipeline và hàng rào dữ liệu (chunk-level RLS, leak-test).

## ⚠️ Không build/test độc lập được
`agentcore-studio-kb` phụ thuộc `agentcore-studio-contracts` + uv.lock + `docker/postgres-init` của repo cha, và cần **Postgres pgvector** cho test (RLS / leak). Vì vậy:
- **Làm việc qua repo cha:** `git clone --recursive git@github.com:hieubui2409/agentcore-studio-kit.git`, rồi `cd packages/kb` để sửa / commit / push chính repo này.
- **Test đầy đủ:** đẩy PR → CI tự **dựng lại full workspace** rồi chạy `pytest packages/kb/tests` (Phương án B).

## CI
`.github/workflows/ci.yml` chỉ là **stub** gọi reusable workflow chung ở repo cha:
`hieubui2409/agentcore-studio-kit/.github/workflows/reusable-domain-ci.yml@main`.
Muốn đổi quy trình CI thì sửa ở repo cha (1 chỗ).

## Quy tắc
- Chỉ đụng file trong `packages/kb/**` (fence-lane của bạn) — không sửa surface domain khác.
- `test_leak.py` là red-by-design: giữ RED tới khi fence-DATA land thật; làm hỏng fence → CI đỏ, chặn PR.
- Đổi contract → sang repo `agentcore-studio-contracts` (mentor-approval).
- Không commit tài liệu mentor/rubric/answer-key (pre-commit `nda-denylist` chặn).

📖 Phân quyền + luồng thao tác đầy đủ: [GITFLOWS.md](https://github.com/hieubui2409/agentcore-studio-kit/blob/main/GITFLOWS.md)
