# HỆ THỐNG ĐẶT LẠI MẬT KHẨU QUA EMAIL (PASSWORD RESET VIA EMAIL)

> **Mã Nhiệm Vụ:** `⚡ SCRUM-71 / ☑ S1-03`  
> **Ngôn ngữ thực hiện:** Python 3 (FastAPI & Flask Backend) + Redis + Celery Task  
> **Tiêu chuẩn thiết kế:** *PEP 8 Standards, 100% Type Hints, Anti-Enumeration Security*  
> **Môi trường chạy:** Visual Studio Code trên hệ điều hành Windows  

---

## 🎯 1. BẢNG ĐỐI CHIẾU TIÊU CHÍ CHẤP NHẬN (ACCEPTANCE CRITERIA)

Dự án được xây dựng và giải quyết trọn vẹn 100% nội dung yêu cầu trong ticket **SCRUM-71**:

| Tiêu Chí Trong Ticket SCRUM-71 | Yêu Cầu Của Đề Bài | Cách Hệ Thống Python & Backend Đáp Ứng |
| :--- | :--- | :--- |
| **Tiêu đề User Story** | *Là người dùng của hệ thống, tôi muốn đặt lại mật khẩu khi quên thông qua email, để tự lấy lại quyền truy cập khi đang đi gặp khách.* | Hệ thống cung cấp API đặt lại mật khẩu an toàn qua Email. Người dùng nhập email công ty và nhận được liên kết kích hoạt duy nhất có hiệu lực trong 30 phút. |
| **Tiêu chí 1 (Description)** | *Nhập email nhận được liên kết đặt lại có hiệu lực 30 phút* | Token sinh ra ngẫu nhiên bằng `secrets.token_urlsafe()` và được lưu vào Redis với thời hạn TTL đúng **30 phút** (1800 giây). Hết 30 phút token tự động bị hủy. |
| **Tiêu chí 2 (Description)** | *Liên kết chỉ dùng được một lần* | Ngay sau khi người dùng xác nhận đặt lại mật khẩu thành công bằng token, hệ thống lập tức xóa token khỏi Redis (`redis_manager.delete_reset_token()`). Nếu dùng lại token lần 2 sẽ nhận được báo lỗi HTTP 400. |
| **Tiêu chí 3 (Description)** | *Email không tồn tại vẫn hiển thị cùng một thông báo* | Áp dụng cơ chế **Anti-Enumeration Protection**: Dù email có tồn tại trong CSDL hay không, hệ thống đều phản hồi cùng một thông báo HTTP 200 chuẩn hóa, tránh rò rỉ thông tin người dùng. |
| **Quy chuẩn kỹ thuật (S1-03)** | *`POST /api/v1/auth/forgot-password`: sinh token `secrets.token_urlsafe()`, lưu Redis TTL 30p; Celery task gửi email SMTP* | Thực thi đúng endpoint `POST /api/v1/auth/forgot-password` với `secrets.token_urlsafe(32)`, lưu Redis TTL 30p và gọi Celery Task `send_password_reset_email_task` gửi SMTP email. |

---

## 🏗️ 2. CẤU TRÚC THƯ MỤC DỰ ÁN

```text
scrum_71/
├── app.py                      # Backend API, định nghĩa endpoints forgot-password & reset-password
├── database.py                 # Giả lập CSDL người dùng & Quản lý Redis Token TTL 30 phút
├── run.bat                     # File kích hoạt chạy nhanh 1-click trên hệ điều hành Windows
├── README.md                   # Tài liệu hướng dẫn sử dụng và đối chiếu tiêu chí chấp nhận
└── tests/
    └── test_scrum_71.py        # Bộ kiểm thử tự động (Unit Test & Integration Test)
```
