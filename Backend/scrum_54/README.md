# HỆ THỐNG CHUYỂN ĐỔI LEAD CRM (1-CLICK CONVERSION)

> **Mã Nhiệm Vụ (Jira Ticket):** `⚡ SCRUM-30 / ☑ SCRUM-54`  
> **User Story:** *"Là Nhân viên kinh doanh, tôi muốn chuyển một lead đủ điều kiện thành khách hàng và cơ hội, để không phải nhập lại thông tin đã hỏi khách ba lần."*  
> **Ngôn ngữ phát triển:** Python 3 (Flask Framework) + HTML5/CSS3/JavaScript  
> **Môi trường vận hành:** Visual Studio Code / Terminal trên hệ điều hành Windows  

---

## 🎯 1. BẢNG ĐỐI CHIẾU TIÊU CHÍ CHẤP NHẬN (ACCEPTANCE CRITERIA)

Dự án được xây dựng và kiểm thử bám sát 100% từng yêu cầu trong hình ảnh đề bài (Ticket SCRUM-54):

| Tiêu Chí Trong Đề Bài | Yêu Cầu Của Đề Bài | Cách Hệ Thống Python Đáp Ứng & Triển Khai |
| :--- | :--- | :--- |
| **Tiêu đề User Story** | *Là Nhân viên kinh doanh, tôi muốn chuyển một lead đủ điều kiện thành khách hàng và cơ hội, để không phải nhập lại thông tin đã hỏi khách ba lần.* | Giao diện cung cấp nút **"🚀 Chuyển Đổi Lead 1-Click"** nổi bật trên từng lead đủ điều kiện. Khi thực hiện, hệ thống tự động kế thừa trọn vẹn thông tin và sinh đồng thời các thực thể liên kết, loại bỏ 100% thao tác nhập liệu thủ công lặp lại. |
| **Tiêu chí 1 (Description)** | *Một thao tác sinh đồng thời khách hàng doanh nghiệp, người liên hệ và cơ hội bán hàng* | Hàm backend Python `Database.convert_lead()` thực hiện atomic transaction:<br>1. Sinh **Khách hàng doanh nghiệp (Account)**: `ACC-xxx`<br>2. Sinh **Người liên hệ (Contact)**: `CON-xxx`, tự động liên kết với Account vừa tạo<br>3. Sinh **Cơ hội bán hàng (Opportunity)**: `OPP-xxx`, tự động liên kết với cả Account và Contact. |
| **Tiêu chí 2 (Description)** | *Dữ liệu lead được chuyển sang, không phải nhập lại* | Toàn bộ dữ liệu của lead được tự động ánh xạ (auto-mapped):<br>• Tên công ty, MST, ngành nghề, địa chỉ, website, hotline &rarr; **Khách hàng doanh nghiệp**<br>• Họ tên, chức vụ, SĐT, email &rarr; **Người liên hệ**<br>• Nhu cầu, sản phẩm, ngân sách ước tính, ngày chốt dự kiến &rarr; **Cơ hội bán hàng**.<br>Nhân viên không cần nhập lại bất kỳ trường thông tin nào đã hỏi khách hàng trước đó. |
| **Tiêu chí 3 (Description)** | *Lead chuyển sang trạng thái Đã chuyển đổi và không sửa được nữa* | Ngay sau khi chuyển đổi:<br>• Lead đổi trạng thái thành `CONVERTED` (*Đã chuyển đổi*) và bật cờ `is_locked = True`.<br>• **Khóa bảo vệ bất biến (Immutable Lock):** Mọi thao tác sửa lead qua API hoặc giao diện đều bị chặn ở cả Frontend (nút sửa bị vô hiệu hóa 🔒) và Backend Python (ném lỗi `PermissionError` chặn đứng thao tác chỉnh sửa).<br>• Lưu vết ID khách hàng, người liên hệ, cơ hội và thời điểm chuyển đổi. |
| **Tiêu chí 4 (Description)** | *Toàn bộ hoạt động đã ghi trên lead được giữ lại trên khách hàng mới* | Toàn bộ danh sách hoạt động tương tác đã ghi trên Lead (cuộc gọi điện thoại, cuộc hẹn demo, email, ghi chú chăm sóc) được sao chép/kế thừa sang Khách hàng mới (`Account.activities`), gắn cờ `inherited_from_lead = True` và lưu mã `source_lead_id`.<br>Đồng thời sinh một sự kiện cột mốc hệ thống: *"Chuyển đổi thành công từ Lead [Mã Lead] 🚀"*. |

---

## 🏛️ 2. KIẾN TRÚC HỆ THỐNG & CẤU TRÚC THƯ MỤC

```text
scrum_54/
├── app.py                      # Flask Server, Web Routes, Persona Switcher & REST APIs
├── config.py                   # Cấu hình hằng số (Trạng thái Lead, Stages Cơ hội, Hoạt động, Roles)
├── database.py                 # Quản lý dữ liệu Thread-safe, mô hình Lead/Account/Contact/Opportunity
├── run.bat                     # File 1-click khởi động ứng dụng trên Windows
├── requirements.txt            # Thư viện phụ thuộc (Flask >= 3.0.0)
├── README.md                   # Báo cáo kỹ thuật & Hướng dẫn sử dụng chi tiết
├── static/
│   ├── css/
│   │   └── style.css           # Giao diện hiện đại Glassmorphism, chuẩn thẩm mỹ CRM doanh nghiệp
│   └── js/
│       └── main.js             # Client-side JavaScript, Modal xác nhận chuyển đổi & auto-format
├── templates/
│   ├── base.html               # Layout chính, Topbar Jira ticket, Persona Switcher, Navbar
│   ├── dashboard.html          # Tổng quan KPIs, danh sách lead chờ chuyển đổi 1-click
│   ├── leads_list.html         # Danh sách tất cả Lead, bộ lọc đa trạng thái, nút chuyển đổi
│   ├── lead_detail.html        # Chi tiết Lead, hồ sơ 3 mảng, banner khóa bảo vệ, timeline hoạt động
│   ├── lead_convert.html       # Màn hình xem trước chuyển đổi 3 thực thể (Preview 1-Click)
│   ├── conversion_success.html # Màn hình chúc mừng chuyển đổi thành công & xác nhận 4 tiêu chí
│   ├── lead_edit.html          # Form chỉnh sửa Lead (chặn sửa nếu lead đã bị khóa)
│   ├── lead_new.html           # Form tạo mới Lead tiềm năng
│   ├── accounts_list.html      # Danh sách Khách hàng doanh nghiệp đã sinh từ Lead
│   ├── account_detail.html     # Chi tiết Khách hàng: Tab Hoạt động kế thừa từ Lead (AC4)
│   ├── contacts_list.html      # Danh sách Người liên hệ sinh từ Lead
│   ├── opportunities_list.html # Bảng Pipeline & Cơ hội bán hàng sinh từ Lead
│   └── simulator.html          # Trình mô phỏng & chạy test tự động 4 tiêu chí trong 10 giây
└── tests/
    ├── __init__.py
    ├── test_ac1_atomic_convert.py    # Unit Test Tiêu chí 1: Sinh đồng thời Account, Contact, Opportunity
    ├── test_ac2_data_inheritance.py  # Unit Test Tiêu chí 2: Dữ liệu chuyển sang 100%, không nhập lại
    ├── test_ac3_immutable_lock.py    # Unit Test Tiêu chí 3: Trạng thái CONVERTED & Khóa bất biến chặn sửa
    ├── test_ac4_activity_retention.py# Unit Test Tiêu chí 4: Giữ lại toàn bộ hoạt động trên khách hàng mới
    └── test_web_routes.py            # Integration Test toàn bộ Web Routes & Form POST Chuyển đổi
```

---

## 🚀 3. HƯỚNG DẪN KHỞI CHẠY TRÊN WINDOWS

### Cách 1: Khởi chạy 1-Click bằng file `run.bat` (Khuyên dùng)
1. Mở File Explorer và điều hướng tới thư mục:
   ```text
   C:\Users\FPT SHOP\.gemini\antigravity-ide\scratch\scrum_54
   ```
2. Nhấp đúp chuột vào file **`run.bat`**.
3. Ứng dụng sẽ tự động mở trình duyệt tại: **http://127.0.0.1:5000**

---

### Cách 2: Khởi chạy thủ công từ Terminal / VS Code
1. Mở thư mục `scrum_54` trong **Visual Studio Code**.
2. Mở Terminal tích hợp (`Ctrl + ~`).
3. Cài đặt thư viện:
   ```bash
   py -m pip install -r requirements.txt
   ```
4. Khởi chạy máy chủ Flask:
   ```bash
   py app.py
   ```
5. Mở trình duyệt truy cập: 👉 **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## 🧪 4. HƯỚNG DẪN KIỂM THỬ TRỰC QUAN 4 TIÊU CHÍ TRÊN GIAO DIỆN

Hệ thống cung cấp sẵn dữ liệu mẫu tiêu chuẩn để bạn kiểm thử ngay lập tức:

### Kiểm thử Tiêu chí 1 & 2: Sinh 3 thực thể đồng thời & Kế thừa không phải nhập lại
1. Vào menu **"Quản Lý Lead"** (`/leads`).
2. Chọn lead **`LEAD-101`** (*Công ty Cổ phần Công nghệ VinTech* - đang ở trạng thái ⭐ Đủ điều kiện).
3. Bấm nút **"🚀 Chuyển Đổi Lead"**.
4. Màn hình Xem Trước Chuyển Đổi xuất hiện: hiển thị rõ 3 khối thực thể (*Khách hàng doanh nghiệp*, *Người liên hệ*, *Cơ hội bán hàng*) đã được điền tự động 100% dữ liệu từ Lead.
5. Bấm nút **"🚀 XÁC NHẬN CHUYỂN ĐỔI 1-CLICK NGAY"**.
6. **Kết quả:** Màn hình chúc mừng xuất hiện, đồng thời tạo ra:
   - Khách hàng doanh nghiệp: `ACC-202`
   - Người liên hệ: `CON-302` (Nguyễn Hoàng Long)
   - Cơ hội bán hàng: `OPP-402` (Trị giá 150.000.000 đ).

---

### Kiểm thử Tiêu chí 3: Lead chuyển sang "Đã chuyển đổi" và không sửa được nữa
1. Quay lại trang chi tiết lead **`LEAD-101`** hoặc **`LEAD-105`** (lead đã chuyển đổi).
2. Trạng thái hiển thị huy hiệu: **🔒 ĐÃ CHUYỂN ĐỔI (ĐÃ KHÓA BẤT BIẾN)**.
3. Nút **"Sửa thông tin"** bị vô hiệu hóa (*disabled*).
4. Nếu cố tình truy cập trực tiếp URL sửa `/leads/LEAD-101/edit`:
   - Giao diện hiển thị cảnh báo đỏ và khóa toàn bộ form input.
   - Backend Python từ chối cập nhật và ném lỗi `PermissionError`.

---

### Kiểm thử Tiêu chí 4: Toàn bộ hoạt động ghi trên lead được giữ lại trên khách hàng mới
1. Nhấp vào liên kết Khách hàng doanh nghiệp mới tạo (ví dụ: `ACC-202` hoặc `ACC-201`).
2. Cuộn xuống mục **"📜 Lịch Sử Hoạt Động Của Khách Hàng (Chứng Minh Tiêu Chí 4)"**.
3. **Kết quả:** Toàn bộ cuộc gọi (18 phút), cuộc họp Demo trực tuyến qua Google Meet và email báo giá đã ghi nhận từ thời điểm còn là Lead vẫn xuất hiện đầy đủ, nguyên vẹn kèm huy hiệu:
   ```text
   🔖 Kế Thừa Từ Lead LEAD-101
   ```
4. Kèm một sự kiện mốc: *"Chuyển đổi thành công từ Lead LEAD-101 🚀"*.

---

### Chạy nhanh bằng Trình Kiểm Thử 1-Click (Simulator)
1. Bấm vào menu **"⚡ Kiểm Thử 4 Tiêu Chí"** (`/simulator`).
2. Bấm nút **"🚀 CHẠY KIỂM THỬ NGAY (10s)"**.
3. Hệ thống sẽ tự động thực hiện trọn vẹn luồng tạo lead &rarr; ghi nhận hoạt động &rarr; chuyển đổi &rarr; kiểm tra khóa bảo vệ &rarr; đưa bạn tới trang Khách hàng mới để kiểm chứng ngay!

---

## 🔬 5. CHẠY BỘ KIỂM THỬ TỰ ĐỘNG (AUTOMATED TEST SUITE)

Mở Terminal tại thư mục `scrum_54` và chạy lệnh:
```bash
py -m unittest discover tests
```

**Kết quả kiểm thử:** Toàn bộ **16/16 bài kiểm thử** vượt qua thành công:
```text
................
----------------------------------------------------------------------
Ran 16 tests in 0.141s

OK
```
Bao gồm:
- `test_ac1_atomic_convert.py`: Kiểm thử thao tác sinh đồng thời 3 thực thể.
- `test_ac2_data_inheritance.py`: Kiểm thử kế thừa 100% dữ liệu, không mất mát.
- `test_ac3_immutable_lock.py`: Kiểm thử chuyển trạng thái `CONVERTED` và khóa bất biến chặn sửa.
- `test_ac4_activity_retention.py`: Kiểm thử giữ trọn lịch sử hoạt động trên khách hàng mới.
- `test_web_routes.py`: Kiểm thử tích hợp toàn bộ các trang web và API.
