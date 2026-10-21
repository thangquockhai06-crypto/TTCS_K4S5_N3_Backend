# Từ Điển Dữ Liệu: Bảng Campaigns & Marketing Metrics

| Tên Cột | Kiểu Dữ Liệu | Ràng Buộc | Mô Tả |
|---|---|---|---|
| id | INTEGER | PK | Mã chiến dịch tiếp thị duy nhất |
| name | VARCHAR(255) | NOT NULL | Tên chiến dịch tiếp thị |
| type | VARCHAR(50) | NOT NULL | Loại hình: EMAIL, EVENT, SOCIAL, ADVERTISING |
| budgeted_cost | DECIMAL(15,2) | DEFAULT 0 | Ngân sách dự toán cho chiến dịch |
| actual_cost | DECIMAL(15,2) | DEFAULT 0 | Chi phí thực tế đã giải ngân |
| expected_revenue | DECIMAL(15,2) | DEFAULT 0 | Doanh số mục tiêu thu về |
| start_date | DATE | NOT NULL | Ngày khởi động chiến dịch |
| end_date | DATE | NOT NULL | Ngày kết thúc chiến dịch |
| status | VARCHAR(20) | DEFAULT 'PLANNED' | Trạng thái: PLANNED, ACTIVE, COMPLETED, CANCELLED |
