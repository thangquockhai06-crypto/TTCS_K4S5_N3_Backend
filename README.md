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
- **Kiểm thử tự động**: Pytest (69 tests tự động bao phủ 100% Sprint 1 & 2).

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

## 📁 Cấu Trúc Toàn Bộ Backend Kho Lưu Trữ

```text
TTCS_K4S5_N3_Backend/
├── app/                             # [MÃ NGUỒN CHÍNH FASTAPI PRODUCTION]
│   ├── config.py                    # Cấu hình hệ thống, JWT, CORS, Database URL
│   ├── database.py                  # Khởi tạo SQLAlchemy engine, SessionLocal, Base
│   ├── dependencies.py              # Xác thực Token, RBAC, require_admin, require_roles
│   ├── main.py                      # Điểm nối kết 16 Router API & Middleware
│   ├── core/                        # Security, Scope, Redis, Celery, Export
│   ├── models/                      # 14 SQLAlchemy ORM Models
│   ├── repositories/                # 10 Repositories xử lý tầng dữ liệu
│   ├── routers/                     # 16 Routers API RESTful
│   ├── schemas/                     # 14 Schemas Pydantic v2
│   └── services/                    # 11 Services xử lý nghiệp vụ & logic
├── Subtask Backend/                 # [CÁC MODULE SUBTASK SCRUM CỦA NHÓM]
│   ├── scrum_58/                    # Quản lý khách hàng, liên hệ, chuyển giao liên hệ
│   ├── scrum_71/                    # Gửi email khôi phục mật khẩu khi quên
│   ├── scrum_72/                    # Đặt lại mật khẩu mới qua token xác nhận
│   ├── scrum_74/                    # Mục tiêu nhóm, báo cáo hiệu suất, nhân viên
│   ├── scrum_75/                    # Báo cáo tài chính, quản lý dự án
│   ├── scrum_80/                    # Hồ sơ cá nhân và quản lý báo giá
│   └── scrum_85/                    # Cây sơ đồ tổ chức, vùng miền & phạm vi dữ liệu
├── tests/                           # [BỘ KIỂM THỬ TỰ ĐỘNG - 69 TESTS PASSED]
├── init_db.sql                      # Script tạo cơ sở dữ liệu MySQL
├── requirements.txt                 # Danh sách gói phụ thuộc Python
├── run.py                           # File khởi chạy Uvicorn server
├── seed.py                          # Script nạp dữ liệu mẫu
├── start-server.bat                 # Script chạy nhanh trên Windows
├── pytest.ini                       # Cấu hình chạy kiểm thử tự động
└── README.md
```

---

## 🧪 Kiểm thử tự động (Unit & Integration Tests)
Chạy bộ kiểm thử tự động gồm 69 test cases:
```bash
pytest
```
Bộ test bao gồm:
- `tests/test_user_management.py` (22 tests CRUD, gán vai trò, nhóm, chuyển giao dữ liệu)
- `tests/test_data_scope_access_control.py` (22 tests cách ly dữ liệu cá nhân/nhóm/toàn quốc)
- `tests/test_forgot_password.py` (4 tests quên mật khẩu và đặt lại mật khẩu)
- `tests/test_change_password.py` (4 tests đổi mật khẩu trong phiên)
- `tests/test_sprint2_features.py` (11 tests nhập Excel, nhật ký kiểm toán, danh mục, sản phẩm, phễu)
- `tests/test_scrum79_excel_import.py` (6 tests chi tiết xử lý tải template, preview & batch import)

