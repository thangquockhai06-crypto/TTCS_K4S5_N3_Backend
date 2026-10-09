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


### Avatar người dùng
Các endpoint yêu cầu Bearer access token:

```text
POST /api/v1/users/me/avatar
Content-Type: multipart/form-data
file=<JPG/JPEG hoặc PNG, tối đa 2 MB>

Response 200:
{
  "avatarUrl": "/media/avatars/<uuid>.jpg",
  "avatarThumbnailUrl": "/media/avatars/<uuid>_thumb.jpg"
}
```

Ảnh được xoay theo EXIF, crop chính giữa thành hình vuông, loại bỏ metadata và lưu thumbnail mặc định `128x128`. `DELETE /api/v1/users/me/avatar` xóa avatar và trả về hai trường URL có giá trị `null`. Phản hồi khách hàng chứa `assignedUser.avatarThumbnailUrl`; giá trị là `null` nếu khách hàng chưa có người phụ trách hoặc người phụ trách chưa tải avatar.
### Tìm kiếm khách hàng và saved filters
`GET /api/v1/customers` giữ nguyên response dạng danh sách và thêm header `X-Total-Count`. Hỗ trợ:

- `q`: tìm không phân biệt hoa thường/dấu theo tên và công ty; tìm tiền tố mã số thuế; tìm số điện thoại khách hàng hoặc contact, bao gồm định dạng `+84`.
- `status`, `industry`, `companySize`, `region`, `owner`: lặp query parameter hoặc truyền danh sách phân cách bằng dấu phẩy.
- `owner=me` lọc người dùng hiện tại; `owner=unassigned` lọc bản ghi chưa gán. Data scope của role vẫn được áp dụng ở tầng truy vấn.
- `sort=name|created_at|status|owner`, `descending`, `skip`, `limit`.
- `saved_filter_id`: nạp saved filter của chính người dùng; các tham số gửi trực tiếp ghi đè giá trị đã lưu.

Các bucket `companySize` hợp lệ là `SMB`, `MID_MARKET`, `ENTERPRISE`. CRUD saved filter dùng:
`GET/POST /api/v1/saved-filters`, `PATCH/DELETE /api/v1/saved-filters/{id}`.
Saved filter được giới hạn 20 bản ghi mỗi người dùng, không cho trùng tên không phân biệt hoa thường, và definition được kiểm tra trước khi lưu.

### Catalog và Price Book
Các endpoint yêu cầu Bearer access token. Chỉ role `Sales Director` được tạo, cập nhật, ngừng bán hoặc xóa catalog item; người dùng khác chỉ được đọc và không nhận trường `costPrice`.

```json
POST /api/v1/catalog-items
{
  "code": "CRM-STD-001",
  "name": "CRM Standard",
  "type": "ONE_TIME_PRODUCT",
  "unitOfMeasure": "license",
  "listPrice": "10000000.00",
  "floorPrice": "8000000.00",
  "costPrice": "5000000.00",
  "currency": "VND"
}
```

`POST /api/v1/catalog-items/{id}/discontinue` ngừng bán item. Item đã xuất hiện trong quote trả `409` khi DELETE. Quote lines lưu snapshot `listPriceSnapshot` và `floorPriceSnapshot`; item đã discontinued không thể thêm vào quote mới.

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

### Cảnh báo và Gộp khách hàng trùng lặp (SCRUM-62 / SCRUM-148)
- **POST `/api/v1/customers/duplicates/scan`**: Quét và phát hiện khách hàng trùng lặp đa tiêu chí:
  + **Mã số thuế (`tax_code`)**: Chuẩn hóa loại bỏ khoảng trắng, dấu gạch ngang.
  + **Website (`website`)**: Chuẩn hóa domain (loại bỏ `http://`, `https://`, `www.` và trailing path).
  + **Tên công ty (`name`)**: So khớp độ tương đồng chuỗi loại bỏ tiền tố/hậu tố pháp lý phổ biến (tỷ lệ tương đồng $\ge 80\%$).
  + **Số điện thoại**: Chuẩn hóa số điện thoại liên hệ.
- **GET `/api/v1/customers/compare`**: So sánh cạnh nhau 2 khách hàng, chi tiết hồ sơ, contacts, deals, activities và danh sách các trường dữ liệu có sự khác biệt.
- **POST `/api/v1/customers/merge`**: Thực hiện gộp khách hàng trong một Database Transaction an toàn (ACID):
  + **Phân quyền RBAC:** Chỉ Trưởng nhóm (`TEAM_LEAD`) trở lên (`DIRECTOR`, `ADMIN`). Nhân viên kinh doanh (`SALES_REP`) bị chặn HTTP 403 Forbidden.
  + **Data Scope:** `TEAM_LEAD` chỉ được gộp khách hàng thuộc phạm vi quản lý của nhóm mình; `DIRECTOR` có quyền trên toàn bộ hệ thống.
  + **Bảo toàn dữ liệu:** Chuyển toàn bộ `contacts`, `deals`, `quotations`, `activities`, `notes` từ khách phụ sang khách chính. Khách phụ được đánh dấu `is_deleted = True`, `merged_into_id = target_id`.
  + **Lưu vết kiểm toán:** Tự động tạo bản ghi `Activity` hệ thống trên khách hàng chính ghi nhận việc gộp.

---

## 🧪 Kiểm thử tự động (Unit & Integration Tests)
Chạy bộ kiểm thử tự động:
```bash
pytest
```
Bộ test bao gồm:
- `tests/test_customer_merge.py` (12 tests quét trùng đa tiêu chí, so sánh cạnh nhau, gộp giao dịch ACID, phân quyền RBAC và Data Scope)
- `tests/test_user_management.py` (22 tests CRUD, gán vai trò, nhóm, chuyển giao dữ liệu)
- `tests/test_data_scope_access_control.py` (22 tests cách ly dữ liệu cá nhân/nhóm/toàn quốc)
- `tests/test_customer_search.py` (tìm kiếm khách hàng và saved filters)
- `tests/test_catalog_items.py` (catalog sản phẩm và bảng giá)
- `tests/test_forgot_password.py` (4 tests quên mật khẩu và đặt lại mật khẩu)
- `tests/test_change_password.py` (4 tests đổi mật khẩu trong phiên)
- `tests/test_sprint2_features.py` (11 tests nhập Excel, nhật ký kiểm toán, danh mục, sản phẩm, phễu)
- `tests/test_scrum79_excel_import.py` (6 tests chi tiết xử lý tải template, preview & batch import)



## Opportunity close/reopen lifecycle

The existing `deals` table is the opportunity entity. Both `/api/v1/opportunities` and
`/api/v1/deals` expose the same lifecycle:

- `POST /api/v1/opportunities/{id}/close`
  - WON: `{"outcome":"WON","actualValue":"125000000.00","signedDate":"2026-03-31"}`
  - LOST: `{"outcome":"LOST","lostReasonId":"<reason-id>","lostReasonNote":"...","competitorId":"<optional-id>"}`
- `POST /api/v1/opportunities/{id}/reopen`
  - `{"reopenReason":"Customer changed approval path"}`
- `GET /api/v1/opportunities/{id}/history`

Responses include `outcome`, `status`, `closedAt`, `closedBy`, `actualValue`,
`signedDate`, lost-reason and competitor fields, reopen metadata, and append-only
close/reopen history. List queries support `outcome`, `closedFrom`/`closedTo`,
`signedFrom`/`signedTo`, and `lostReasonId` (snake-case query aliases are also accepted).

WON requires an actual value greater than zero and a signing date no later than the
server's current date. LOST requires an active LOST catalog reason; `OTHER` also
requires a non-empty note. Closed deals are immutable until a Team Lead or higher
role reopens them within the existing data scope. Reopening restores the last open
stage and clears current close-only fields; the prior values remain in history.

There is no existing KPI persistence module. `KPIService.get_won_value_for_owner`
and `GET /api/v1/dashboard/kpi/won-value` aggregate active WON rows by owner and
the inclusive `signed_date` period. Reopened rows are excluded automatically, so a
re-close is counted once. Currency remains the existing single-currency VND
convention and database money columns use `DECIMAL(15,2)`.

The project uses startup compatibility migrations rather than versioned migration
files. `run_auto_migrations()` adds the close/reopen columns, creates the history
table, seeds the `OTHER` fallback, and backfills legacy `stage=won/lost` rows:
WON uses the legacy value and close timestamp; LOST uses the active `OTHER` reason.
