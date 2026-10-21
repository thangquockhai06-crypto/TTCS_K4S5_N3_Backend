# NexusCRM Backend - Supporting Customer Subtasks

Hệ thống hỗ trợ bán hàng và quản lý khách hàng toàn diện (Customer Lifecycle Support).

## Danh sách 5 Module tính năng (Sprint Support)

| Mã Scrum | Tính năng | Trạng thái | Kiểm thử tự động |
| :--- | :--- | :---: | :---: |
| **SCRUM-31** | Tạo và quản lý Báo giá (Quotation Creation) | ✅ Hoàn thành | 5/5 AC passed |
| **SCRUM-33** | Quy trình phê duyệt Báo giá đa cấp | ✅ Hoàn thành | 5/5 AC passed |
| **SCRUM-37** | Quản lý phiên bản & So sánh Diff Báo giá | ✅ Hoàn thành | 3/3 AC passed |
| **SCRUM-38** | Chuyển đổi Báo giá thành Hợp đồng kinh doanh | ✅ Hoàn thành | 4/4 AC passed |
| **SCRUM-57** | Dòng thời gian tương tác khách hàng 360 độ | ✅ Hoàn thành | 2/2 AC passed |

## Hướng dẫn cài đặt & Chạy kiểm thử
Mỗi thư mục `scrum_*` được thiết kế độc lập, có sẵn file `run.bat` và thư mục `tests/` để chạy kiểm thử tự động toàn diện.


## Kiến trúc kỹ thuật và Phân tầng hệ thống
- **Service Layer**: Đảm nhiệm toàn bộ business logic, RBAC và validation nghiệp vụ.
- **Repository / Database Layer**: Xử lý ORM, transaction isolation và đánh chỉ mục tối ưu truy vấn.
- **Automated Testing Suite**: Đảm bảo 100% test coverage cho tất cả các tiêu chí chấp nhận (AC) của Sprint.
