# Từ Điển Dữ Liệu: Bảng Deals & Deal Items

| Tên Cột | Kiểu Dữ Liệu | Ràng Buộc | Mô Tả |
|---|---|---|---|
| id | INTEGER | PK | Mã cơ hội bán hàng |
| code | VARCHAR(50) | UNIQUE | Mã cơ hội bán hàng (DEAL-XXXX) |
| title | VARCHAR(255) | NOT NULL | Tiêu đề thương vụ kinh doanh |
| customer_id | INTEGER | FK -> customers.id | Khách hàng liên kết |
| stage | VARCHAR(50) | NOT NULL | Giai đoạn bán hàng trên phễu Kanban |
| expected_revenue | DECIMAL(15,2) | DEFAULT 0 | Giá trị hợp đồng kỳ vọng (VND) |
| probability | INTEGER | DEFAULT 10 | Xác suất chốt đơn thành công (%) |
| closed_at | DATETIME | NULL | Thời điểm đóng thành công hoặc thất bại |
| win_loss_reason | TEXT | NULL | Lý do thắng hoặc thua cơ hội |
