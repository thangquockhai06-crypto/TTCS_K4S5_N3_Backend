# Từ Điển Dữ Liệu: Bảng Contracts & Contract Documents

| Tên Cột | Kiểu Dữ Liệu | Ràng Buộc | Mô Tả |
|---|---|---|---|
| id | INTEGER | PK | Mã hợp đồng duy nhất |
| contract_number | VARCHAR(50) | UNIQUE | Số hợp đồng pháp lý (HD-YYYY-XXXX) |
| quotation_id | INTEGER | FK -> quotations.id | Báo giá gốc tạo nên hợp đồng |
| customer_id | INTEGER | FK -> customers.id | Khách hàng ký kết |
| signed_date | DATE | NOT NULL | Ngày hai bên hoàn tất ký kết |
| effective_date | DATE | NOT NULL | Ngày hợp đồng bắt đầu có hiệu lực |
| expiration_date | DATE | NOT NULL | Ngày hợp đồng đáo hạn |
| total_value | DECIMAL(15,2) | NOT NULL | Tổng giá trị kinh tế của hợp đồng |
| status | VARCHAR(20) | NOT NULL | DRAFT, PENDING, ACTIVE, EXPIRED, TERMINATED |
