# Từ Điển Dữ Liệu: Bảng Quotations & PDF Templates

| Bảng | Tên Cột | Kiểu Dữ Liệu | Mô Tả |
|---|---|---|---|
| quotations | id | INTEGER (PK) | Mã báo giá nội bộ |
| quotations | quote_number | VARCHAR(50) | Số hiệu báo giá (Q-YYYY-XXXX) |
| quotations | total_amount | DECIMAL(15,2) | Tổng số tiền thanh toán cuối cùng |
| quotations | tax_rate | DECIMAL(5,2) | Tỷ lệ thuế VAT (%) |
| quotations | status | VARCHAR(20) | DRAFT, SENT, ACCEPTED, REJECTED, EXPIRED |
| pdf_templates | id | INTEGER (PK) | Mã mẫu in PDF |
| pdf_templates | template_name | VARCHAR(100) | Tên mẫu biểu in ấn |
| pdf_templates | header_html | TEXT | Phần đầu trang kèm logo thương hiệu |
| pdf_templates | footer_html | TEXT | Phần chân trang kèm điều khoản thanh toán |
