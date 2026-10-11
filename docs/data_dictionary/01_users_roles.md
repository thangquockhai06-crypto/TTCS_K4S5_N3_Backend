# Từ Điển Dữ Liệu: Bảng Users & Roles

| Tên Cột | Kiểu Dữ Liệu | Ràng Buộc | Mô Tả |
|---|---|---|---|
| id | INTEGER | PK, Auto Increment | Mã định danh người dùng duy nhất |
| username | VARCHAR(50) | UNIQUE, NOT NULL | Tên đăng nhập tài khoản |
| email | VARCHAR(100) | UNIQUE, NOT NULL | Địa chỉ email liên hệ |
| hashed_password | VARCHAR(255) | NOT NULL | Mật khẩu băm an toàn bcrypt/Argon2 |
| full_name | VARCHAR(100) | NOT NULL | Họ và tên đầy đủ |
| role | VARCHAR(20) | NOT NULL | Quyền hạn: ADMIN, DIRECTOR, MANAGER, SALES, CS |
| data_scope | VARCHAR(20) | NOT NULL | Phạm vi dữ liệu: GLOBAL, BRANCH, TEAM, PERSONAL |
| is_active | BOOLEAN | DEFAULT 1 | Trạng thái hoạt động tài khoản |
| avatar_url | VARCHAR(255) | NULL | Đường dẫn ảnh đại diện avatar |
