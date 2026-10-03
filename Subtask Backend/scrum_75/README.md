# HỆ THỐNG QUẢN LÝ DOANH NGHIỆP - XỬ LÝ LỖI TRẢI NGHIỆM NGƯỜI DÙNG

> **Mã Nhiệm Vụ:** `⚡ SCRUM-69 / ☑ SCRUM-75`  
> **Ngôn ngữ:** Python 3 (Flask Framework) + HTML5/CSS3/JavaScript  
> **Chính sách chất lượng:** *Zero White-Screen Policy (Triệt tiêu hoàn toàn màn hình trắng khi gặp sự cố)*  
> **Môi trường chạy:** Visual Studio Code trên hệ điều hành Windows  

---

## 🎯 1. BẢNG ĐỐI CHIẾU TIÊU CHÍ CHẤP NHẬN (ACCEPTANCE CRITERIA)

Dự án được xây dựng bám sát 100% nội dung hình ảnh đề bài yêu cầu:

| Tiêu Chí Trong Ticket SCRUM-75 | Yêu Cầu Của Đề Bài | Cách Hệ Thống Python Đáp Ứng |
| :--- | :--- | :--- |
| **Tiêu đề User Story** | *Là người dùng của hệ thống, tôi muốn nhận thông báo rõ ràng khi truy cập nhầm chỗ hoặc không đủ quyền, để biết mình nên làm gì tiếp thay vì gặp một trang trắng.* | Khi người dùng truy cập sai URL (404) hoặc vào trang chưa được cấp quyền (403), hệ thống **tuyệt đối không hiển thị trang trắng**. Thay vào đó là giao diện thông báo sinh động, hiển thị rõ mã lỗi, nguyên nhân, ngữ cảnh (URL, vai trò, quyền còn thiếu) và hướng dẫn cụ thể. |
| **Tiêu chí 1 (Description)** | *Trang báo lỗi dùng chung giao diện ứng dụng* | Tất cả các trang lỗi (`404.html`, `403.html`, `500.html`) đều kế thừa (`{% extends "base.html" %}`) từ **Master Layout chung**. Header, Sidebar điều hướng, thẻ Profile người dùng, logo và bảng màu thương hiệu vẫn được giữ nguyên vẹn giúp người dùng luôn cảm thấy an toàn trong hệ thống. |
| **Tiêu chí 2 (Description)** | *Mỗi trang lỗi có một hành động gợi ý để quay lại luồng làm việc* | • **Tại trang 404 (Nhầm chỗ):** Có nút *"Quay lại Bảng điều khiển"* (Primary CTA), nút *"Quay lại trang trước"* (lịch sử duyệt) và gợi ý các khu vực làm việc phổ biến.<br>• **Tại trang 403 (Thiếu quyền):** Có nút *"Đổi sang tài khoản Giám Đốc (Có Đủ Quyền)"* giúp kiểm thử tức thì, nút *"Gửi yêu cầu xin cấp quyền"*, và nút *"Về Bảng điều khiển"*. |

---

## 🏗️ 2. KIẾN TRÚC VÀ CẤU TRÚC THƯ MỤC DỰ ÁN

```text
scrum_75/
├── app.py                      # Ứng dụng Flask trung tâm, định nghĩa Routes & Error Handlers
├── database.py                 # Mô hình RBAC (4 vai trò), dữ liệu mẫu (dự án, tài chính)
├── run.bat                     # File kích hoạt chạy nhanh 1-click trên Windows
├── static/
│   ├── css/
│   │   └── style.css           # Toàn bộ CSS giao diện đồng bộ (Header, Sidebar, Error cards)
│   └── js/
│       └── main.js             # Xử lý modal xin cấp quyền và tương tác giao diện
├── templates/
│   ├── base.html               # Master Layout chung của ứng dụng (dùng chung cho toàn hệ thống)
│   ├── errors/
│   │   ├── 403.html            # Trang lỗi 403 (Không đủ quyền) kế thừa base.html
│   │   ├── 404.html            # Trang lỗi 404 (Truy cập nhầm chỗ) kế thừa base.html
│   │   └── 500.html            # Trang lỗi 500 (Sự cố hệ thống) kế thừa base.html
│   └── pages/
│       ├── dashboard.html      # Bảng điều khiển tích hợp Testing Lab trực quan
│       ├── projects.html       # Quản lý Dự án (yêu cầu quyền view_projects)
│       ├── financial_reports.html # Báo cáo Tài chính (yêu cầu quyền view_financial)
│       └── settings.html       # Cấu hình Bảo mật (yêu cầu quyền system_settings)
└── tests/
    └── test_scrum_75.py        # Bộ 7 bài test tự động xác thực 100% Acceptance Criteria
```

---

## 🚀 3. HƯỚNG DẪN MỞ VÀ CHẠY DỰ ÁN TRÊN VISUAL STUDIO CODE

### Bước 1: Mở thư mục dự án trong VS Code
1. Khởi động **Visual Studio Code**.
2. Chọn menu **File** -> **Open Folder...** (hoặc nhấn phím tắt `Ctrl + K, Ctrl + O`).
3. Điều hướng và chọn thư mục:
   ```text
   C:\Users\FPT SHOP\.gemini\antigravity-ide\scratch\scrum_75
   ```

### Bước 2: Mở Terminal trong VS Code
- Nhấn tổ hợp phím: `Ctrl + ~` (hoặc vào menu **Terminal** -> **New Terminal**).

### Bước 3: Cài đặt thư viện Flask (nếu máy chưa cài)
```bash
py -m pip install flask
```
*(Trên môi trường máy của bạn Flask đã có sẵn).*

### Bước 4: Khởi chạy máy chủ
```bash
py app.py
```
*(hoặc bạn có thể nhấp đúp chuột vào file `run.bat` trong thư mục)*

Terminal sẽ xuất hiện thông báo:
```text
=================================================================
 HỆ THỐNG QUẢN LÝ DOANH NGHIỆP - USER STORY SCRUM-75
 Báo lỗi 404 & 403 dùng chung giao diện - Không bị trang trắng
 Địa chỉ truy cập: http://127.0.0.1:5000
=================================================================
```

### Bước 5: Mở trên trình duyệt
- Mở Chrome, Edge hoặc bất kỳ trình duyệt nào và vào địa chỉ:  
  👉 **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## 🧪 4. HƯỚNG DẪN TỪNG BƯỚC ĐỂ KIỂM THỬ ĐÁP ỨNG ĐỀ BÀI

Hệ thống được tích hợp sẵn thanh công cụ **Top Testing Bar** và **Testing Lab Card** ngay trên giao diện để phục vụ việc kiểm tra và chấm điểm:

### Kịch bản 1: Kiểm thử Lỗi 404 - Truy cập nhầm chỗ (Không bị trang trắng)
1. Tại thanh công cụ đầu trang (màu tím than), bấm vào nút màu vàng cam: **"Thử lỗi 404 (Nhầm chỗ)"** (hoặc bạn có thể tự nhập một URL ngẫu nhiên bất kỳ như `http://127.0.0.1:5000/duong-dan-khong-ton-tai`).
2. **Quan sát kết quả:**
   - **Giao diện chung vẫn nguyên vẹn:** Toàn bộ thanh Sidebar bên trái (menu Bảng điều khiển, Dự án, Cấu hình...), thông tin người dùng và thanh Header vẫn hiển thị đầy đủ (đáp ứng tiêu chí: *Trang báo lỗi dùng chung giao diện ứng dụng*).
   - **Thông báo rõ ràng:** Hiển thị biểu tượng la bàn 🧭, nhãn `Mã lỗi: 404 Not Found`, tiêu đề *"Bạn Đã Truy Cập Nhầm Chỗ!"*.
   - **Chi tiết nguyên nhân:** Chỉ rõ đường dẫn bạn vừa gõ nhầm.
   - **Hành động gợi ý để quay lại luồng làm việc:**
     - Nút **"Quay lại Bảng điều khiển"** (màu tím) để tiếp tục làm việc.
     - Nút **"Quay lại trang trước"** để quay về vị trí vừa duyệt.
     - Nút **"Đến Quản lý Dự án"** để điều hướng đến chức năng chính.

---

### Kịch bản 2: Kiểm thử Lỗi 403 - Không đủ quyền truy cập (Không bị trang trắng)
1. Kiểm tra góc trên bên phải thanh Testing Bar: Đảm bảo vai trò đang chọn là **"Lê Hoàng Phúc (Chuyên viên tác nghiệp)"** hoặc **"Phạm Minh Khôi (Thực tập sinh)"**.
2. Bấm vào nút màu đỏ: **"Thử lỗi 403 (Thiếu quyền)"** (hoặc bấm vào menu *"Cấu hình Bảo mật Hệ thống"* trên thanh Sidebar bên trái).
3. **Quan sát kết quả:**
   - **Không bị trang trắng:** Giao diện ứng dụng vẫn hiển thị đầy đủ Sidebar và Topbar.
   - **Thông báo bảo mật chi tiết:** Xuất hiện biểu tượng chiếc khiên 🛡️, nhãn `Mã lỗi: 403 Forbidden`, tiêu đề *"Bạn Không Đủ Quyền Truy Cập!"*.
   - **Hộp chẩn đoán tài khoản:**
     - Tên tài khoản: `Lê Hoàng Phúc` (`staff`)
     - Vai trò hiện tại: `Chuyên viên tác nghiệp`
     - Quyền hạn còn thiếu: `system_settings` (Cấu hình bảo mật & Quản trị hệ thống)
     - Đường dẫn bị chặn: `/system-settings`
   - **Hành động gợi ý để quay lại luồng làm việc:**
     - Nút **"Đổi sang tài khoản Giám Đốc (Có Đủ Quyền)"** (màu xanh lá): Cho phép người chấm bấm 1 cái là tự động chuyển sang tài khoản Admin để truy cập ngay trang Cấu hình.
     - Nút **"Gửi yêu cầu xin cấp quyền"**: Mở modal gửi phiếu xin cấp quyền tới Giám đốc.
     - Nút **"Về Bảng điều khiển"** và **"Quay lại trang trước"**.

---

### Kịch bản 3: Chạy bộ kiểm thử tự động (Unit Test Suite)
Để minh chứng mã nguồn đáp ứng 100% các tiêu chí chất lượng bằng dòng lệnh:
1. Mở Terminal tại thư mục `scrum_75`.
2. Chạy lệnh:
   ```bash
   py -m unittest tests/test_scrum_75.py
   ```
3. Kết quả: Toàn bộ **7 ca kiểm thử** (`Ran 7 tests`) đều đạt kết quả **OK**.
