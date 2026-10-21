# Từ điển CSDL Phân hệ Nhắc việc (Data Dictionary)

### Bảng `tasks`
- `id` (VARCHAR(36), PK): UUID định danh công việc.
- `title` (VARCHAR(255), NOT NULL): Tiêu đề công việc.
- `status` (VARCHAR(50)): pending, in_progress, completed, cancelled, overdue.
- `due_date` (DATETIME): Thời hạn hoàn thành công việc.
- `assignee_id` (VARCHAR(36), FK -> users.id): Người chịu trách nhiệm thực thi.
- `reminded_milestones` (JSON): Mảng lưu các mốc đã gửi thông báo.

### Bảng `reminder_settings`
- `id` (VARCHAR(36), PK): UUID.
- `user_id` (VARCHAR(36), FK -> users.id, UNIQUE): Người sở hữu cấu hình.
- `remind_before_minutes` (JSON): Mảng các mốc phút nhắc trước hạn `[15, 60, 1440]`.
- `is_enabled` (BOOLEAN): Bật/tắt tính năng nhắc nhở.

### Bảng `notifications`
- `id` (VARCHAR(36), PK): UUID.
- `user_id` (VARCHAR(36), FK -> users.id): Người nhận thông báo.
- `task_id` (VARCHAR(36), FK -> tasks.id, NULLABLE): Liên kết công việc.
- `title` (VARCHAR(255)), `message` (TEXT), `type` (VARCHAR(50)).
- `is_read` (BOOLEAN), `read_at` (DATETIME).
