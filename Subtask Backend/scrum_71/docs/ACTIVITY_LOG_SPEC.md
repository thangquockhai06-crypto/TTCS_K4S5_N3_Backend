# Đặc Tả Kỹ Thuật Nhật Ký Hoạt Động (SCRUM-71)

## 1. Các loại hoạt động
- `CALL`: Cuộc gọi điện thoại (Inbound / Outbound), lưu thời lượng và kết quả cuộc gọi.
- `MEETING`: Cuộc họp trực tiếp hoặc trực tuyến qua Zoom/Google Meet.
- `EMAIL`: Email trao đổi tài liệu, hợp đồng, báo giá.
- `NOTE`: Ghi chú nội bộ dành cho nhân viên kinh doanh và quản lý.
- `TASK`: Công việc được giao kèm thời hạn hoàn thành (Due date).

## 2. API Endpoints
- `GET /api/v1/activities`: Danh sách hoạt động lọc theo user hoặc customer.
- `POST /api/v1/activities`: Tạo hoạt động mới kèm thời gian thực hiện.
