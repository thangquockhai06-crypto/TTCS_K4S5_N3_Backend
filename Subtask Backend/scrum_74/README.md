# HỆ THỐNG MENU ĐIỀU HƯỚNG PHÂN QUYỀN (RBAC NAVIGATION SYSTEM)

> **Mã Nhiệm Vụ:** `⚡ SCRUM-69 / ☑ SCRUM-74`  
> **Ngôn ngữ thực hiện:** Python 3 (Flask Framework) + Modern Responsive HTML5 / CSS3 / Vanilla JS  
> **Tiêu chuẩn thiết kế:** *Mobile-First Design (Tối ưu đặc thù màn hình 360px)*  
> **Môi trường chạy:** Visual Studio Code (VS Code) trên hệ điều hành Windows  

---

## 🎯 1. BẢNG ĐỐI CHIẾU TIÊU CHÍ CHẤP NHẬN (ACCEPTANCE CRITERIA)

Dự án được xây dựng và giải quyết trọn vẹn 100% nội dung yêu cầu trong ticket **SCRUM-74**:

| Tiêu Chí Trong Ticket SCRUM-74 | Yêu Cầu Của Đề Bài | Cách Hệ Thống Python & Giao Diện Đáp Ứng |
| :--- | :--- | :--- |
| **Tiêu đề User Story** | *Là người dùng của hệ thống, tôi muốn thấy menu điều hướng đúng theo quyền của mình, để không bị rối bởi những chức năng mình không được dùng.* | Hệ thống áp dụng mô hình phân quyền theo vai trò (**RBAC - Role-Based Access Control**). Hàm `get_user_menu(user)` lọc danh sách menu ngay tại backend trước khi render template. Người dùng thuộc vai trò nào thì chỉ thấy đúng các mục menu trong thẩm quyền, không bị rối mắt bởi các mục không được phép sử dụng. |
| **Tiêu chí 1 (Description)** | *Mục menu không thuộc quyền thì không hiển thị* | • **Loại bỏ sạch khỏi DOM:** Các mục menu ngoài quyền hạn **hoàn toàn không được sinh ra trong mã nguồn HTML**, không phải chỉ ẩn bằng CSS (`display: none`).<br>• **Bảo vệ đa tầng (Multi-layer):** Nếu người dùng cố tình gõ link trực tiếp (URL) trên thanh địa chỉ, decorator `@require_permission` ở tầng Flask backend sẽ chặn lại và trả về mã lỗi **HTTP 403 Forbidden** kèm giao diện thông báo chi tiết, không để xảy ra trang trắng. |
| **Tiêu chí 2 (Description)** | *Hiển thị tên, vai trò và nhóm kinh doanh đang thuộc về* | Khối **User Profile Card** được bố trí nổi bật trên thanh Sidebar điều hướng và thanh Header, hiển thị đầy đủ và trang trọng 3 thông tin:<br>1. **Họ và tên:** e.g. `Lê Hoàng Phúc`, `Trần Thị Mai Phương`, `Nguyễn Tuấn Anh`...<br>2. **Vai trò:** e.g. `Chuyên viên kinh doanh`, `Trưởng nhóm kinh doanh`, `Giám đốc kinh doanh` kèm nhãn màu nhận diện riêng biệt.<br>3. **Nhóm kinh doanh đang thuộc về:** e.g. `Nhóm Bán Lẻ Khu Vực Miền Bắc`, `Nhóm Khách Hàng Doanh Nghiệp (B2B)`, `Ban Giám Đốc Kinh Doanh`... |
| **Tiêu chí 3 (Description)** | *Dùng được thuận tiện trên màn hình 360px* | • Thiết kế chuẩn **Mobile-First Responsive Web Design**, kiểm thử nghiêm ngặt tại độ rộng **360px** (chuẩn smartphone phổ biến).<br>• Thanh điều hướng chuyển đổi thành **Off-Canvas Drawer** trượt cảm ứng mượt mà từ bên trái khi bấm nút Hamburger ☰.<br>• Nút Hamburger, nút đóng ✕ và các mục menu đều có kích thước vùng bấm cảm ứng chuẩn **touch target $\ge 44\text{px} \times 44\text{px}$**.<br>• Tuyệt đối **không bị tràn viền ngang (không bị lỗi vỡ layout hay horizontal scrollbar)**.<br>• Tích hợp sẵn nút **"📱 Giả lập màn hình 360px"** trực tiếp trên web để kiểm thử ngay trên máy tính mà không cần bật DevTools. |

---

## 📊 2. MA TRẬN PHÂN QUYỀN MENU (RBAC ACCESS MATRIX)

| STT | Mục Menu | Đường dẫn URL | Quyền Yêu Cầu | Giám Đốc (director) | Trưởng Nhóm (team_lead) | Chuyên Viên (sales_rep) | Thực Tập (intern) |
| :---: | :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| 1 | **Bảng điều khiển** | `/dashboard` | `view_dashboard` | **✓ Có** (Hiện) | **✓ Có** (Hiện) | **✓ Có** (Hiện) | **✓ Có** (Hiện) |
| 2 | **Khách hàng của tôi** | `/customers` | `manage_customers` | **✓ Có** (Hiện) | **✓ Có** (Hiện) | **✓ Có** (Hiện) | ✗ Không (Ẩn) |
| 3 | **Đơn hàng & Hợp đồng** | `/deals` | `manage_deals` | **✓ Có** (Hiện) | **✓ Có** (Hiện) | **✓ Có** (Hiện) | ✗ Không (Ẩn) |
| 4 | **Báo cáo doanh số nhóm** | `/team-reports` | `view_team_reports` | **✓ Có** (Hiện) | **✓ Có** (Hiện) | ✗ Không (Ẩn) | ✗ Không (Ẩn) |
| 5 | **Chỉ tiêu & KPI nhóm** | `/team-targets` | `manage_team_targets` | **✓ Có** (Hiện) | **✓ Có** (Hiện) | ✗ Không (Ẩn) | ✗ Không (Ẩn) |
| 6 | **Quản lý nhân sự kinh doanh** | `/staff-management` | `manage_sales_staff` | **✓ Có** (Hiện) | ✗ Không (Ẩn) | ✗ Không (Ẩn) | ✗ Không (Ẩn) |
| 7 | **Cấu hình hệ thống** | `/settings` | `system_settings` | **✓ Có** (Hiện) | ✗ Không (Ẩn) | ✗ Không (Ẩn) | ✗ Không (Ẩn) |
| **Tổng** | **Số menu hiển thị** | | | **7 / 7 mục** | **5 / 7 mục** | **3 / 7 mục** | **1 / 7 mục** |

---

## 🏗️ 3. CẤU TRÚC THƯ MỤC DỰ ÁN

```text
scrum_74/
├── app.py                      # Backend Flask trung tâm, định nghĩa routes, decorator @require_permission
├── database.py                 # Khai báo RBAC Roles, Permissions, All Menu Items & Sample Users
├── run.bat                     # File kích hoạt chạy nhanh 1-click trên hệ điều hành Windows
├── README.md                   # Tài liệu hướng dẫn sử dụng và kiểm thử chi tiết
├── static/
│   ├── css/
│   │   └── style.css           # Toàn bộ CSS giao diện: Responsive 360px, Mobile Drawer, Touch targets >= 44px
│   └── js/
│       └── main.js             # Xử lý mở/đóng Drawer cảm ứng & chế độ giả lập màn hình 360px
├── templates/
│   ├── base.html               # Master Layout: Sidebar điều hướng, Thẻ User Profile, Topbar 360px, Hamburger
│   ├── errors/
│   │   ├── 403.html            # Giao diện 403 Forbidden chặn truy cập trực tiếp URL vượt quyền
│   │   └── 404.html            # Giao diện 404 Not Found khi truy cập sai đường dẫn
│   └── pages/
│       ├── dashboard.html      # Bảng điều khiển tích hợp Ma trận đối chiếu quyền trực quan
│       ├── customers.html      # Quản lý khách hàng (CRM)
│       ├── deals.html          # Đơn hàng & hợp đồng kinh doanh
│       ├── team_reports.html   # Báo cáo doanh số cấp nhóm
│       ├── team_targets.html   # Thiết lập chỉ tiêu & KPI nhóm
│       ├── staff_management.html# Quản lý nhân sự kinh doanh (Giám đốc)
│       └── settings.html       # Cấu hình hệ thống kinh doanh (Giám đốc)
└── tests/
    └── test_scrum_74.py        # Bộ kiểm thử tự động 8 ca test (Xác thực 100% 3 Tiêu chí đề bài)
```

---

## 🚀 4. HƯỚNG DẪN CÀI ĐẶT & CHẠY TRÊN VISUAL STUDIO CODE

### Bước 1: Mở thư mục dự án trong VS Code
1. Khởi động **Visual Studio Code**.
2. Chọn menu **File** -> **Open Folder...** (hoặc nhấn phím tắt `Ctrl + K, Ctrl + O`).
3. Điều hướng và chọn thư mục:
   ```text
   C:\Users\FPT SHOP\.gemini\antigravity-ide\scratch\scrum_74
   ```

### Bước 2: Mở Terminal trong VS Code
- Nhấn tổ hợp phím: `Ctrl + ~` (hoặc chọn menu **Terminal** -> **New Terminal**).

### Bước 3: Cài đặt thư viện Flask (nếu máy chưa cài)
```bash
py -m pip install flask
```
*(Nếu máy tính nhận lệnh `python`, bạn gõ `python -m pip install flask`).*

### Bước 4: Khởi chạy máy chủ
```bash
py app.py
```
*(Hoặc bạn có thể nhấp đúp chuột trực tiếp vào file `run.bat` trong thư mục).*

Terminal sẽ xuất hiện thông báo:
```text
====================================================================
 HỆ THỐNG MENU ĐIỀU HƯỚNG THEO PHÂN QUYỀN RBAC - SCRUM-74
 Tiêu chí: Lọc sạch menu DOM + Tên/Vai trò/Nhóm + Chuẩn 360px mobile
 Đang chạy tại địa chỉ: http://127.0.0.1:5000
====================================================================
```

### Bước 5: Mở trên trình duyệt
- Mở Chrome, Microsoft Edge hoặc bất kỳ trình duyệt nào và truy cập:  
  👉 **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## 🧪 5. HƯỚNG DẪN TỪNG BƯỚC ĐỂ KIỂM THỬ ĐÁP ỨNG ĐỀ BÀI

Hệ thống được tích hợp sẵn thanh **Role Switcher (Đổi vai trò nhanh)** ở chân Sidebar và **Bảng ma trận đối chiếu quyền (Access Matrix)** ngay tại Dashboard để chấm điểm trực quan:

### Kịch bản 1: Kiểm thử Tiêu chí 1 - Menu không thuộc quyền thì không hiển thị
1. Tại chân Sidebar bên trái, hãy bấm lần lượt 4 nút đổi vai trò:
   - **Bấm "Chuyên viên (3 menu)":** Người dùng là `Lê Hoàng Phúc`. Menu bên trái lập tức rút gọn chỉ còn đúng **3 mục** (Bảng điều khiển, Khách hàng của tôi, Đơn hàng & Hợp đồng). Bốn mục quản lý khác hoàn toàn biến mất khỏi giao diện và mã nguồn DOM.
   - **Bấm "Thực tập (1 menu)":** Người dùng là `Phạm Minh Khôi`. Menu chỉ còn duy nhất **1 mục** (Bảng điều khiển).
   - **Bấm "Trưởng nhóm (5 menu)":** Người dùng là `Trần Thị Mai Phương`. Thấy **5 mục**, không thấy mục "Quản lý nhân sự" và "Cấu hình".
   - **Bấm "Giám đốc (7 menu)":** Người dùng là `Nguyễn Tuấn Anh`. Thấy đầy đủ toàn bộ **7 mục**.
2. **Kiểm tra bảo mật Backend (Chặn truy cập trực tiếp):**
   - Đang ở tài khoản Chuyên viên (`Lê Hoàng Phúc`), hãy gõ trực tiếp URL `/settings` hoặc `/staff-management` trên thanh địa chỉ trình duyệt.
   - Hệ thống lập tức trả về trang lỗi **403 Forbidden** giải thích rõ: *Người dùng Lê Hoàng Phúc (Chuyên viên kinh doanh) thiếu quyền `system_settings`*, đồng thời cung cấp nút chuyển nhanh sang tài khoản Giám đốc.

### Kịch bản 2: Kiểm thử Tiêu chí 2 - Hiển thị Tên, Vai trò và Nhóm kinh doanh
Quan sát thẻ thông tin **User Profile Card** ở góc trên Sidebar hoặc đầu Dashboard:
- **Trường 1 (Họ và tên):** Hiển thị rõ ràng (ví dụ: `Lê Hoàng Phúc`, `Trần Thị Mai Phương`, `Nguyễn Tuấn Anh`, `Phạm Minh Khôi`).
- **Trường 2 (Vai trò):** Hiển thị kèm Badge màu sắc đặc trưng (Tím cho Giám đốc, Xanh dương cho Trưởng nhóm, Xanh lá cho Chuyên viên, Vàng cam cho Thực tập sinh).
- **Trường 3 (Nhóm kinh doanh đang thuộc về):** Hiển thị đầy đủ cùng icon nhóm (ví dụ: `Nhóm Bán Lẻ Khu Vực Miền Bắc`, `Nhóm Khách Hàng Doanh Nghiệp (B2B)`, `Ban Giám Đốc Kinh Doanh Toàn Quốc`...).

### Kịch bản 3: Kiểm thử Tiêu chí 3 - Tương thích màn hình 360px
- **Cách 1 (Nhanh & Trực quan nhất):** Bấm nút màu xanh lá **"📱 Giả lập màn hình 360px"** ở thanh công cụ trên cùng. Giao diện sẽ tự động chuyển thành khung điện thoại thông minh kích thước chuẩn đúng **360px x 740px** có viền đen sang trọng. Bạn có thể bấm nút Hamburger ☰ để mở Drawer trượt mượt mà.
- **Cách 2 (Sử dụng DevTools F12):**
  1. Nhấn `F12` trên trình duyệt Chrome/Edge.
  2. Nhấn tổ hợp phím `Ctrl + Shift + M` (Device Toolbar).
  3. Chọn chiều rộng là **360px** (ví dụ: 360 x 740 hoặc 360 x 640).
  4. Bấm nút Hamburger ☰ ở góc trái Topbar để mở Drawer menu. Bấm ra ngoài hoặc bấm dấu ✕ để đóng lại. Kích thước nút bấm và mục menu đều rộng rãi, chạm bấm dễ dàng ($\ge 44\text{px}$).

---

## 🛡️ 6. CHẠY BỘ KIỂM THỬ TỰ ĐỘNG (UNIT TESTS)

Dự án cung cấp bộ kiểm thử tự động gồm **8 ca kiểm thử** bao quát 100% các tiêu chí của đề bài:

```bash
py -m unittest tests/test_scrum_74.py
```

Kết quả thực tế khi chạy lệnh:
```text
........
----------------------------------------------------------------------
Ran 8 tests in 0.113s

OK
```
*(Toàn bộ 8 ca test đều ĐẠT - khẳng định mã nguồn đáp ứng chính xác mọi yêu cầu).*
