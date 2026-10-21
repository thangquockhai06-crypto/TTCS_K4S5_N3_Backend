# Đặc tả API Thông báo In-App (Notifications Endpoints)

## 1. Lấy danh sách thông báo
- **GET** `/api/v1/notifications`
- **Query Params**:
  - `unreadOnly` (bool, default=false): Chỉ lấy thông báo chưa đọc.
  - `skip` (int, default=0), `limit` (int, default=50).

## 2. Đếm số lượng thông báo chưa đọc
- **GET** `/api/v1/notifications/unread-count`
- **Response**: `{"unreadCount": 5}`

## 3. Đánh dấu đã đọc một thông báo
- **POST / PATCH** `/api/v1/notifications/{notification_id}/read`
- **Response**: `NotificationDTO` với `isRead=true`.

## 4. Đánh dấu đã đọc tất cả
- **POST / PATCH** `/api/v1/notifications/mark-all-read`
- **Response**: `{"status": "success", "markedCount": 5}`
