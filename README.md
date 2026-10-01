# NexusCRM Enterprise - Backend Service

Hệ thống Backend API cho nền tảng **NexusCRM SaaS** phục vụ quản trị quan hệ khách hàng, quản lý người dùng, phân quyền truy cập đa cấp (RBAC & Data Scope) và phễu doanh số.

---

## 🛠 Công nghệ sử dụng
- **Ngôn ngữ**: Python 3.10+
- **Framework**: FastAPI (Asynchronous REST API)
- **ORM & Database**: SQLAlchemy 2.x, Pydantic v2
- **Cơ sở dữ liệu hỗ trợ**:
  - **SQLite** (Mặc định tự động dự phòng, không yêu cầu cài đặt máy chủ)
  - **MySQL / MariaDB** (Production)
- **Bảo mật**: JWT (OAuth2 Password Bearer), Bcrypt hashing, Brute-force lockout (15 phút sau 5 lần sai), Role-Based Access Control (RBAC), Data Scope Isolation (Cá nhân, Nhóm, Toàn quốc).
- **Kiểm thử tự động**: Pytest (63 tests tự động bao phủ 100% Sprint 1 & 2).

---

## 🚀 Hướng dẫn Cài đặt & Khởi chạy

### 1. Chuẩn bị môi trường ảo
```bash
# Tạo môi trường ảo Python
python -m venv venv

# Kích hoạt trên Windows PowerShell:
.\venv\Scripts\Activate.ps1
# Hoặc Windows Command Prompt:
.\venv\Scripts\activate.bat
# Trên Linux/macOS:
source venv/bin/activate
```

### 2. Cài đặt các gói phụ thuộc
```bash
pip install -r requirements.txt
```

### 3. Cấu hình biến môi trường (Tùy chọn)
Sao chép `.env.example` thành `.env` nếu cần tinh chỉnh cổng hoặc kết nối MySQL:
```bash
cp .env.example .env
```
*Lưu ý: Nếu không có MySQL, hệ thống tự động sử dụng SQLite fallback (`nexuscrm.db`) mà không báo lỗi.*

### 4. Nạp dữ liệu mẫu ban đầu (Seeding)
Hệ thống đi kèm dữ liệu mẫu hoàn chỉnh với 8 tài khoản doanh nghiệp chuẩn cho mọi vai trò:
```bash
python seed.py
```

### 5. Khởi động máy chủ Backend
```bash
python run.py
```
- Máy chủ sẽ chạy tại: **`http://127.0.0.1:8000`**
- Tài liệu tương tác Swagger UI: **`http://127.0.0.1:8000/docs`**
- Tài liệu ReDoc: **`http://127.0.0.1:8000/redoc`**

---

## 🔑 Tài khoản Mặc định Đăng nhập Hệ thống
| Họ và tên | Email | Mật khẩu | Vai trò (Role) | Phòng ban / Nhóm |
| :--- | :--- | :--- | :--- | :--- |
| **Quản Trị Viên Hệ Thống** | `admin@nexuscrm.vn` | `Admin@2026` | Super Admin | Ban Quản Trị & Vận Hành Doanh Thu |
| **Nguyễn Tuấn Anh** | `director@nexuscrm.vn` | `Password123!` | VP of Sales | Khối Kinh Doanh Toàn Quốc |
| **Trần Thị Mai Phương** | `leader@nexuscrm.vn` | `Password123!` | Sales Manager | Trưởng nhóm Kinh doanh Miền Bắc |
| **Lê Hoàng Phúc** | `sales1@nexuscrm.vn` | `Password123!` | Account Executive | Miền Bắc (Hà Nội) |
| **Vũ Hải Đăng** | `sales2@nexuscrm.vn` | `Password123!` | Account Executive | Miền Nam (TP. Hồ Chí Minh) |
| **Đỗ Ngọc Lan** | `sales3@nexuscrm.vn` | `Password123!` | Account Executive | Miền Trung (Đà Nẵng) |
| **Hoàng Thu Trang** | `revops@nexuscrm.vn` | `Password123!` | RevOps Lead | Doanh nghiệp FDI & Toàn cầu |
| **Phạm Minh Khôi** | `intern@nexuscrm.vn` | `Password123!` | Account Executive | Kinh doanh Trực tuyến & SMB |

---

## 🧪 Kiểm thử tự động (Unit & Integration Tests)
Chạy bộ kiểm thử tự động gồm 63 test cases:
```bash
pytest
```
Bộ test bao gồm:
- `tests/test_user_management.py` (22 tests CRUD, gán vai trò, nhóm, chuyển giao dữ liệu)
- `tests/test_data_scope_access_control.py` (22 tests cách ly dữ liệu cá nhân/nhóm/toàn quốc)
- `tests/test_forgot_password.py` (4 tests quên mật khẩu và đặt lại mật khẩu)
- `tests/test_change_password.py` (4 tests đổi mật khẩu trong phiên)
- `tests/test_sprint2_features.py` (11 tests nhập Excel, nhật ký kiểm toán, danh mục, sản phẩm, phễu)
