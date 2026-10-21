# Từ Điển Dữ Liệu: Bảng Leads & Lead Scoring

| Tên Cột | Kiểu Dữ Liệu | Ràng Buộc | Mô Tả |
|---|---|---|---|
| id | INTEGER | PK | Mã đầu mối duy nhất |
| first_name | VARCHAR(50) | NOT NULL | Tên đầu mối |
| last_name | VARCHAR(50) | NOT NULL | Họ đệm đầu mối |
| email | VARCHAR(100) | INDEX | Email liên hệ |
| phone | VARCHAR(20) | INDEX | Số điện thoại liên hệ |
| source | VARCHAR(50) | DEFAULT 'Website' | Nguồn đầu mối (Web Form, Triển lãm, Giới thiệu) |
| score | INTEGER | DEFAULT 0 | Điểm tiềm năng của đầu mối (0 - 100) |
| temperature | VARCHAR(20) | DEFAULT 'COLD' | Nhiệt độ đầu mối: HOT, WARM, COLD |
| is_converted | BOOLEAN | DEFAULT 0 | Đã chuyển đổi thành Khách hàng/Cơ hội hay chưa |
