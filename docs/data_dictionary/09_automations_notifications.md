# Từ Điển Dữ Liệu: Bảng Automations & Notifications

| Bảng | Tên Cột | Kiểu Dữ Liệu | Mô Tả |
|---|---|---|---|
| automation_rules | id | INTEGER (PK) | Mã quy tắc tự động hóa |
| automation_rules | name | VARCHAR(255) | Tên quy tắc (Vd: Auto create contract) |
| automation_rules | trigger_event | VARCHAR(50) | Sự kiện kích hoạt (DEAL_WON, LEAD_ASSIGNED) |
| automation_rules | action_type | VARCHAR(50) | Hành động (CREATE_TASK, SEND_NOTIFICATION) |
| notifications | id | INTEGER (PK) | Mã thông báo in-app |
| notifications | user_id | INTEGER (FK) | Nhân sự nhận thông báo |
| notifications | title | VARCHAR(255) | Tiêu đề thông báo tóm tắt |
| notifications | is_read | BOOLEAN | Trạng thái đã xem hay chưa |
