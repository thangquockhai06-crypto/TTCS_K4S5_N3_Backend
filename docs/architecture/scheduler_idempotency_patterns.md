# Thiết kế Đảm bảo Tính Bất biến (Idempotency) của Tiến trình Quét

## Thách thức
Tiến trình quét chạy định kỳ mỗi 60 giây. Nếu nhiều instance cùng chạy hoặc quét lặp lại, nguy cơ spam hàng chục thông báo cho cùng một mốc thời gian là rất cao.

## Giải pháp Triển khai
1. **Trường JSON `reminded_milestones` trên Task**:
   - Lưu trữ mảng các mốc đã thông báo, ví dụ: `["1440m", "60m", "15m", "overdue"]`.
2. **Kiểm tra trước khi phát hành**:
   - Trước khi tạo Notification, kiểm tra xem `milestone_key in task.reminded_milestones`.
   - Nếu đã tồn tại -> Bỏ qua, không gửi lại.
   - Nếu chưa tồn tại -> Thêm mốc vào mảng và lưu CSDL trước khi gửi socket.
3. **Quét Việc Quá Hạn**:
   - Chỉ gắn mốc `"overdue"` đúng một lần đầu tiên khi task chuyển trạng thái quá hạn.
