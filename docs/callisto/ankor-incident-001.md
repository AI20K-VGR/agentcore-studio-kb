---
doc_id: ankor-incident-001
tenant: ankor
section: engineering
---

# Xử lý sự cố — Ankor

## Phân mức sự cố

Sự cố chia ba mức. Mức 1 là mất dịch vụ toàn phần, mức 2 là suy giảm một phần, mức 3 là lỗi nhỏ
không ảnh hưởng người dùng. Người trực gán mức ngay khi tiếp nhận.

## Ứng cứu

Sự cố mức 1 kích hoạt kênh ứng cứu chung, kỹ sư trực làm chỉ huy hiện trường cho tới khi khôi phục.
Trong lúc xử lý, ưu tiên khôi phục dịch vụ trước, tìm nguyên nhân gốc sau.

## Báo cáo sau sự cố

Sự cố mức 1 và mức 2 phải có báo cáo trong vòng 3 ngày làm việc, nêu dòng thời gian, nguyên nhân gốc
và hành động phòng ngừa. Báo cáo không nhằm quy trách nhiệm cá nhân.
