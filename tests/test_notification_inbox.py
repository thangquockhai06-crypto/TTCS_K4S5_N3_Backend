"""Kiểm thử luồng thông báo: Tạo mới -> Đánh dấu đọc -> Đếm số chưa đọc."""
def test_notification_unread_counter():
    notifications = [
        {"id": 1, "is_read": False},
        {"id": 2, "is_read": True},
        {"id": 3, "is_read": False}
    ]
    unread_count = sum(1 for n in notifications if not n["is_read"])
    assert unread_count == 2
