# HỆ THỐNG HỒ SƠ CÁ NHÂN & QUẢN LÝ CHỮ KÝ EMAIL BÁO GIÁ

> **Mã Nhiệm Vụ:** `⚡ SCRUM-69 / ☑ SCRUM-80`  
> **Ngôn ngữ thực hiện:** Python 3 (Flask Framework) + Modern Responsive HTML5 / CSS3 / Vanilla JS  
> **Môi trường chạy:** Visual Studio Code trên hệ điều hành Windows  
> **Tiêu chuẩn:** Tuân thủ 100% Tiêu chí chấp nhận (Acceptance Criteria) của User Story  

---

## 🎯 1. BẢNG ĐỐI CHIẾU TIÊU CHÍ CHẤP NHẬN (ACCEPTANCE CRITERIA)

Dự án được xây dựng và giải quyết trọn vẹn 100% nội dung yêu cầu trong ticket **SCRUM-80**:

| Tiêu Chí Trong Ticket SCRUM-80 | Yêu Cầu Đề Bài | Cách Hệ Thống Python & Giao Diện Đáp Ứng |
| :--- | :--- | :--- |
| **Tiêu đề User Story** | *Là người dùng của hệ thống, tôi muốn xem và cập nhật hồ sơ cá nhân, để chữ ký email của tôi luôn đúng khi gửi báo giá cho khách.* | • Giao diện cho phép xem toàn bộ hồ sơ hiện tại.<br>• Tích hợp tính năng **Xem trước Chữ ký Email thời gian thực (Live Preview)** ngay khi nhập.<br>• Tích hợp module **Gửi Báo Giá & Xem trước Email Khách hàng nhận được** để chứng minh trực tiếp giá trị nghiệp vụ của chữ ký vừa cập nhật. |
| **Tiêu chí 1 (Description)** | *Sửa được họ tên, số điện thoại, chữ ký email* | • Form cập nhật cho phép chỉnh sửa 3 trường: **Họ và tên** (`full_name`), **Số điện thoại** (`phone`), **Chữ ký email** (`email_signature`).<br>• Hỗ trợ nút **"✨ Tự động tạo mẫu chuẩn"** giúp tự sinh mẫu chữ ký email doanh nghiệp chuyên nghiệp.<br>• Dữ liệu cập nhật được lưu trữ bền vững vào phiên làm việc và phản ánh ngay vào hệ thống. |
| **Tiêu chí 2 (Description)** | *Không tự đổi được email, nhóm và vai trò* | • **Bảo vệ tầng giao diện (Frontend):** Các trường **Email** (`email`), **Nhóm kinh doanh** (`business_group`), **Vai trò** (`role_name`) được đặt thuộc tính `readonly`, có huy hiệu `🔒 Cố định`, giải thích rõ lý do bảo mật.<br>• **Bảo vệ đa tầng (Backend Immutability):** Dù người dùng cố tình can thiệp mở DevTools hoặc gửi request sửa các trường này, backend áp dụng cơ chế *Whitelist* và đối chiếu trường cấm (`PROTECTED_FIELDS`) để **tuyệt đối không ghi đè** vào cơ sở dữ liệu. |
| **Tiêu chí 3 (Description)** | *Kiểm tra định dạng số điện thoại Việt Nam* | • Kiểm tra định dạng bằng Regex chuẩn mạng di động Việt Nam (10 chữ số): `^(?:\+?84\|0)(3[2-9]\|5[25689]\|7[06-9]\|8[1-9]\|9[0-9])[0-9]{7}$`.<br>• Hỗ trợ cả định dạng nội địa (`09xx`, `03xx`, `07xx`, `08xx`, `05xx`) lẫn quốc tế (`+84xx`, `84xx`), chấp nhận dấu cách hoặc gạch nối hợp lệ.<br>• **Kiểm tra thời gian thực (Realtime client validation):** Báo lỗi tức thì nếu số quá ngắn, quá dài hoặc sai đầu số nhà mạng.<br>• **Kiểm tra nghiêm ngặt phía Backend:** Chặn lưu và trả về mã lỗi HTTP 400 nếu số điện thoại không hợp lệ. |

---

## 🏗️ 2. CẤU TRÚC THƯ MỤC DỰ ÁN

```text
scrum_80/
├── app.py                      # Flask Backend trung tâm: Quản lý hồ sơ, xác thực SĐT, gửi báo giá, xử lý lỗi
├── database.py                 # Module dữ liệu: Validate số điện thoại VN, bảo vệ Whitelist trường sửa, data mẫu
├── run.bat                     # File chạy nhanh 1-click trên hệ điều hành Windows
├── README.md                   # Tài liệu thuyết minh và đối chiếu tiêu chí chi tiết
├── static/
│   ├── css/
│   │   └── style.css           # Toàn bộ CSS giao diện: Bố cục 2 cột, Email client mockup, Responsive mobile 360px
│   └── js/
│       └── main.js             # Live preview chữ ký, Validate SĐT thời gian thực, Tự sinh mẫu chữ ký
├── templates/
│   ├── base.html               # Master Layout: Sidebar điều hướng, Testing Bar chuyển vai trò, Flash alerts
│   ├── profile.html            # Giao diện chính: Form cập nhật hồ sơ & Khung xem trước chữ ký email thời gian thực
│   ├── quotes.html             # Danh sách báo giá gửi cho khách hàng
│   ├── quote_preview.html      # Xem trước bức thư báo giá thực tế gửi khách có gắn chữ ký mới nhất
│   └── errors/
│       ├── 404.html            # Trang lỗi 404 Not Found đồng bộ giao diện
│       └── 500.html            # Trang lỗi 500 Internal Server Error đồng bộ giao diện
└── tests/
    └── test_scrum_80.py        # Bộ kiểm thử tự động 10 ca test xác minh 100% 3 Tiêu chí đề bài
```

---

## 🚀 3. HƯỚNG DẪN CÀI ĐẶT & KHỞI CHẠY TRÊN VS CODE

### Bước 1: Mở thư mục dự án trong VS Code
1. Mở **Visual Studio Code**.
2. Chọn menu **File** -> **Open Folder...** (hoặc nhấn phím tắt `Ctrl + K, Ctrl + O`).
3. Điều hướng và chọn thư mục:
   ```text
   C:\Users\FPT SHOP\.gemini\antigravity-ide\scratch\Subtask Backend\scrum_80
   ```

### Bước 2: Mở Terminal trong VS Code
- Nhấn tổ hợp phím tắt: `Ctrl + ~` (hoặc vào menu **Terminal** -> **New Terminal**).

### Bước 3: Cài đặt thư viện Flask (nếu chưa cài)
```bash
py -m pip install flask
```

### Bước 4: Khởi chạy máy chủ ứng dụng
```bash
py app.py
```
*(Hoặc có thể nhấp đúp trực tiếp vào file `run.bat` trong thư mục để tự động chạy).*

Sau khi chạy, máy chủ sẽ xuất hiện thông báo:
```text
======================================================================
 HỆ THỐNG QUẢN LÝ HỒ SƠ & CHỮ KÝ EMAIL BÁO GIÁ - SCRUM-80
 User Story: Xem & Cập nhật hồ sơ để chữ ký email luôn đúng khi gửi báo giá
 Tiêu chí: Sửa Tên/SĐT/Chữ ký + Khóa Email/Nhóm/Vai trò + Validate SĐT VN
 Máy chủ đang hoạt động tại: http://127.0.0.1:5000
======================================================================
```

### Bước 5: Trải nghiệm trên trình duyệt Web
Mở trình duyệt (Chrome, Edge, Firefox) và truy cập:
👉 **`http://127.0.0.1:5000`**

---

## 🧪 4. HƯỚNG DẪN CHẠY BỘ KIỂM THỬ TỰ ĐỘNG (UNIT TESTS)

Dự án tích hợp sẵn **10 ca kiểm thử tự động** bao phủ toàn bộ các yêu cầu của ticket:

Chạy lệnh sau tại terminal:
```bash
py -m unittest tests/test_scrum_80.py
```

Kết quả kiểm thử đạt chuẩn 10/10 tests thành công:
```text
Ran 10 tests in 0.174s

OK
```

### Danh mục 10 ca kiểm thử:
1. `test_tc1_view_profile_page_success`: Tải trang hồ sơ thành công và hiển thị đúng thông tin ban đầu.
2. `test_tc1_update_allowed_fields_success`: Sửa thành công Họ tên, Số điện thoại và Chữ ký email.
3. `test_tc2_cannot_modify_protected_fields_form_readonly`: Kiểm tra giao diện khóa `readonly` trường email, vai trò, nhóm.
4. `test_tc2_backend_protection_against_tampering`: Kiểm tra backend chặn mọi hành vi cố tình gửi dữ liệu sửa email, nhóm, vai trò.
5. `test_tc3_valid_vietnam_phone_numbers`: Kiểm tra toàn bộ các đầu số hợp lệ của các nhà mạng Việt Nam (09x, 03x, 07x, 08x, 05x, +84).
6. `test_tc3_invalid_vietnam_phone_numbers_rejected`: Kiểm tra từ chối các số sai (quá ngắn, quá dài, chứa chữ cái, sai đầu số, số bàn).
7. `test_tc3_profile_submission_with_invalid_phone_fails`: Kiểm tra submit SĐT sai trả về lỗi HTTP 400 và thông báo thân thiện.
8. `test_user_story_signature_in_quote_preview`: Kiểm tra chữ ký email vừa sửa xuất hiện chính xác trong thư báo giá gửi khách.
9. `test_switch_user_functionality`: Chuyển đổi linh hoạt giữa các tài khoản nhân sự (Chuyên viên, Trưởng nhóm, Giám đốc).
10. `test_error_404_uses_common_layout`: Xử lý lỗi 404 dùng chung layout ứng dụng, không có trang trắng.

---

## 💡 5. CÁC ĐIỂM SÁNG KỸ THUẬT NỔI BẬT

1. **Bảo mật đa tầng (Defense in Depth):**
   - Tầng UI: Dùng thuộc tính `readonly`, giao diện trực quan thể hiện trường bị khóa với nhãn bảo mật.
   - Tầng Backend: Cơ chế Whitelist chỉ cho phép ghi đè `full_name`, `phone`, `email_signature`. Mọi trường khác đều bị loại bỏ hoặc giữ nguyên giá trị gốc.
2. **Kiểm tra số điện thoại Việt Nam thông minh:**
   - Hỗ trợ làm sạch các ký tự ngăn cách (khoảng trắng, dấu chấm, gạch nối).
   - Tự động chuẩn hóa về dạng hiển thị nội địa dễ đọc: `0xxx xxx xxx`.
   - Bắt đúng dải đầu số thực tế của các nhà mạng viễn thông Việt Nam (Viettel, VinaPhone, MobiFone, Vietnamobile, Gmobile, Wintel).
3. **Mô phỏng trải nghiệm thực tế (Real-world User Value):**
   - Không chỉ dừng lại ở form nhập liệu, hệ thống cung cấp giao diện **Xem trước Email Báo giá** giúp người dùng thấy trực tiếp chữ ký của mình xuất hiện ra sao khi gửi cho đối tác kinh doanh.
