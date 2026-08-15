# Quy trình xuất hoá đơn — Borea

## Loại hoá đơn
Borea dùng hoá đơn điện tử FPT eInvoice theo Thông tư 78/2021/TT-BTC. Hoá đơn GTGT 8% cho dịch vụ fintech, 10% cho dịch vụ tư vấn. Hoá đơn ngoại tệ (USD) cho khách hàng quốc tế.

## Thời điểm xuất hoá đơn
Hoá đơn xuất trong 3 ngày kể từ khi dịch vụ hoàn thành hoặc nhận thanh toán. Subscription hằng tháng: hoá đơn tự động xuất ngày 1 mỗi tháng qua hệ thống billing.

## Quy trình yêu cầu
Account Manager tạo invoice request trên NetSuite, kèm deal ID và PO number. Revenue Operations team verify và auto-generate hoá đơn trong 24 giờ. Khách enterprise nhận proforma invoice trước.

## Thông tin bắt buộc
Hoá đơn gồm: thông tin 2 bên, mô tả service plan, period, unit price, quantity, tax, total. Hoá đơn quốc tế thêm: bank details (USD account), SWIFT code, payment terms. Sai MST auto-reject bởi hệ thống.

## Hoá đơn điều chỉnh
Hoá đơn sai: team RevOps tạo credit note trên NetSuite, xuất hoá đơn thay thế trong 12 giờ. Biên bản điều chỉnh ký điện tử (DocuSign). Track record hoá đơn huỷ/điều chỉnh report hằng tháng cho CFO.

## Gửi hoá đơn cho khách
Hoá đơn tự động gửi qua email ngay khi xuất. Khách hàng truy cập Customer Portal để xem/tải toàn bộ hoá đơn. Push notification qua app Borea cho khách B2C. API webhook cho khách enterprise.

## Theo dõi công nợ
Dunning automation trên NetSuite: email nhắc ngày quá hạn, ngày +7, +14, +21, +30. Quá 30 ngày: tạm dừng dịch vụ (cho SaaS). Quá 60 ngày: chuyển Legal. DSO mục tiêu dưới 25 ngày.

## Chính sách chiết khấu
Chiết khấu thanh toán sớm: 3% nếu thanh toán trong 7 ngày. Annual prepay discount: 15–20%. Volume discount cho enterprise: theo bảng giá riêng, CFO phê duyệt. Không discount ngoài bảng giá.

## Thuế và kê khai
Kê khai thuế GTGT hằng tháng trước ngày 20. Tax team (2 người) chuyên trách đối chiếu input/output VAT. Borea sử dụng phần mềm tax compliance MISA, tự động tạo tờ khai XML.

## Lưu trữ
Hoá đơn lưu trên FPT eInvoice (10 năm) và mirror sang NetSuite + AWS S3 (encrypted, lifecycle policy 10 năm). Truy xuất bằng invoice number, customer ID, hoặc date range trên NetSuite.
