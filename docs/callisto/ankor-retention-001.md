---
doc_id: ankor-retention-001
tenant: ankor
section: engineering
---

# Lưu trữ và huỷ dữ liệu — Ankor

## Thời hạn lưu

Dữ liệu vận hành và nhật ký hệ thống được giữ 12 tháng. Sau thời hạn này, dữ liệu được xoá tự động
trừ khi có yêu cầu giữ lại phục vụ điều tra sự cố.

## Sao lưu

Hệ thống sao lưu hằng ngày và giữ bản sao 30 ngày gần nhất. Bản sao lưu được kiểm tra khôi phục thử
mỗi quý một lần để bảo đảm dùng được khi cần.

## Xoá theo yêu cầu

Yêu cầu xoá dữ liệu ngoài chu kỳ phải có phê duyệt của quản lý kỹ thuật và được ghi nhật ký. Không
xoá dữ liệu đang thuộc phạm vi một cuộc điều tra đang mở.
