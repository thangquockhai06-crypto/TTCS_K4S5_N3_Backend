# HỆ THỐNG ĐỔI MẬT KHẨU TÀI KHOẢN (CHANGE PASSWORD SYSTEM)

> **Mã Nhiệm Vụ:** `⚡ SCRUM-72 / ☑ S1-04`  
> **Ngôn ngữ thực hiện:** Python 3 (FastAPI & Flask Backend) + Redis Session Revocation  
> **Tiêu chuẩn thiết kế:** *PEP 8 Standards, 100% Type Hints, Password Complexity Validation*  
> **Môi trường chạy:** Visual Studio Code trên hệ điều hành Windows  

---

## 🎯 1. BẢNG ĐỐI CHIẾU TIÊU CHÍ CHẤP NHẬN (ACCEPTANCE CRITERIA)

Dự án được xây dựng và giải quyết trọn vẹn 100% nội dung yêu cầu trong ticket **SCRUM-72**:

| Tiêu Chí Trong Ticket SCRUM-72 | Yêu Cầu Của Đề Bài | Cách Hệ Thống Python & Backend Đáp Ứng |
| :--- | :--- | :--- |
| **Tiêu đề User Story** | *Là người dùng của hệ thống, tôi muốn đổi mật khẩu khi đang đăng nhập, để chủ động bảo vệ danh mục khách hàng của mình.* | Hệ thống cho phép người dùng đang làm việc trong phiên đăng nhập thực hiện đổi mật khẩu tài khoản trực tiếp qua API an toàn. |
| **Tiêu chí 1 (Description)** | *Bắt buộc nhập mật khẩu hiện tại* | Endpoint `POST /api/v1/auth/change-password` bắt buộc truyền `current_password`. Hệ thống thực hiện kiểm tra `verify_password()`. Nếu mật khẩu cũ không chính xác, hệ thống trả về lỗi HTTP 400 và không cho phép đổi. |
| **Tiêu chí 2 (Description)** | *Mật khẩu mới tối thiểu 8 ký tự, có chữ và số* | Hệ thống áp dụng bộ lọc kiểm tra độ phức tạp của mật khẩu: độ dài $\ge 8$ ký tự, bắt buộc phải có ít nhất 1 chữ cái (`a-z/A-Z`) và ít nhất 1 chữ số (`0-9`). |
| **Tiêu chí 3 (Description)** | *Đổi xong thu hồi các phiên đăng nhập khác* | Ngay khi đổi mật khẩu thành công, hệ thống lập tức thu hồi toàn bộ các Refresh Token/Session ID khác của người dùng trên Redis và CSDL (`TokenRepository.revoke_other_user_tokens()`). |
| **Quy chuẩn kỹ thuật (S1-04)** | *`POST /api/v1/auth/change-password`: kiểm tra verify mật khẩu cũ, hash pass mới, thu hồi mọi phiên login khác trên Redis* | Triển khai chuẩn endpoint `POST /api/v1/auth/change-password`, thực hiện đầy đủ 4 bước nghiệp vụ theo tiêu chuẩn kiến trúc Clean Layered Architecture. |

---

## 🏗️ 2. CẤU TRÚC THƯ MỤC DỰ ÁN

```text
scrum_72/
├── app.py                      # Backend API định nghĩa endpoint change-password & validate mật khẩu
├── database.py                 # CSDL mẫu & Quản lý danh sách phiên đăng nhập (Session Store)
├── run.bat                     # File kích hoạt chạy nhanh 1-click trên hệ điều hành Windows
├── README.md                   # Tài liệu đối chiếu tiêu chí chấp nhận
└── tests/
    └── test_scrum_72.py        # Bộ kiểm thử tự động (Unit Test)
```
