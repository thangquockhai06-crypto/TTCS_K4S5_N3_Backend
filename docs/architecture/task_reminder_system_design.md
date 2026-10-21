# Thiết kế Kiến trúc Hệ thống Nhắc việc & Thông báo Quá hạn (Task Reminders)

## 1. Tổng quan Nghiệp vụ
Hệ thống nhắc việc được thiết kế nhằm giúp Nhân viên kinh doanh theo dõi tiến độ các tác vụ bán hàng, chăm sóc khách hàng và chốt hợp đồng kịp thời, tránh trôi việc. Đồng thời, hệ thống cung cấp góc nhìn giám sát tập trung cho Trưởng nhóm để can thiệp kịp thời vào các nhiệm vụ quá hạn.

## 2. Các Thành phần Chính
- **Reminder Configuration Module**: Cho phép cấu hình các mốc cảnh báo trước hạn linh hoạt (15m, 60m, 1440m...).
- **Background Scheduler Daemon**: Tiến trình daemon quét định kỳ các công việc chưa hoàn thành trong CSDL.
- **In-App Notification Engine**: Tạo và lưu trữ thông báo in-app, tự động đánh dấu đã đọc.
- **WebSocket Real-time Broadcaster**: Đẩy cảnh báo tức thì đến giao diện người dùng đang trực tuyến.
- **Personal & Team Lead Dashboards**: Cung cấp API trực quan hóa công việc theo chuẩn Centralized Data Scope.
