# Cẩm nang Xử lý Sự cố Thông báo Real-time (Troubleshooting Guide)

## Triệu chứng: Người dùng không nhận được thông báo tức thì
1. **Kiểm tra kết nối WebSocket**:
   - Endpoint: `/api/v1/ws/notifications?token={jwt_token}`.
   - Mã lỗi 4001: Token JWT hết hạn hoặc không hợp lệ.
2. **Kiểm tra trạng thái In-App trong CSDL**:
   - Truy vấn bảng `notifications` xem thông báo đã được lưu chưa:
     `SELECT * FROM notifications WHERE user_id = 'xxx' ORDER BY created_at DESC LIMIT 5;`
3. **Cơ chế Fallback**:
   - Khi WebSocket bị ngắt kết nối, giao diện người dùng tự động polling định kỳ `/api/v1/notifications/unread-count` để cập nhật badge số đỏ.
