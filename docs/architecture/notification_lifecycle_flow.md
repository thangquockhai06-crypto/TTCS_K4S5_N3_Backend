# Vòng đời Thông báo In-App (Notification Lifecycle)

## Luồng xử lý sự kiện
1. **Phát sinh sự kiện (Trigger)**:
   - Scheduler phát hiện công việc chạm mốc nhắc việc hoặc vượt quá hạn chót.
   - Các hành động trong CRM: phân bổ lead, phê duyệt báo giá, phản hồi của khách hàng.
2. **Khởi tạo bản ghi Notification**:
   - Lưu vào bảng `notifications` với trạng thái `is_read=False`.
   - Ghi nhận `milestone` hoặc `target_type` tương ứng.
3. **Phân phối Real-time**:
   - Tra cứu kết nối WebSocket của `user_id` qua `WebSocketNotificationManager`.
   - Gửi payload JSON sự kiện tương ứng (`TASK_REMINDER`, `TASK_OVERDUE`).
4. **Tiêu thụ và Đánh dấu**:
   - Người dùng click xem thông báo -> API `POST/PATCH /notifications/{id}/read`.
   - Đánh dấu đã đọc toàn bộ qua `POST/PATCH /notifications/mark-all-read`.
