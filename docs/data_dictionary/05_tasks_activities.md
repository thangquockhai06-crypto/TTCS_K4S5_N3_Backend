# Từ Điển Dữ Liệu: Bảng Tasks & Activities

| Bảng | Tên Cột | Kiểu Dữ Liệu | Mô Tả |
|---|---|---|---|
| tasks | id | INTEGER (PK) | Mã công việc duy nhất |
| tasks | title | VARCHAR(255) | Tiêu đề công việc được giao |
| tasks | due_date | DATETIME | Hạn hoàn thành công việc |
| tasks | priority | VARCHAR(20) | Độ ưu tiên: LOW, MEDIUM, HIGH, URGENT |
| tasks | status | VARCHAR(20) | Trạng thái: PENDING, IN_PROGRESS, COMPLETED, CANCELLED |
| activities | id | INTEGER (PK) | Mã tương tác hoạt động |
| activities | type | VARCHAR(20) | Loại: CALL, MEETING, EMAIL, NOTE |
| activities | duration_minutes | INTEGER | Thời lượng tương tác tính theo phút |
