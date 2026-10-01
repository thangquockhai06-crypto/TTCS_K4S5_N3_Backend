# HỆ THỐNG SOẠN BÁO GIÁ TỪ CƠ HỘI BÁN HÀNG CRM (AUTOLEAD CRM)

> **Mã Nhiệm Vụ (Jira Ticket):** `⚡ SCRUM-35 / ☑ SCRUM-31`  
> **User Story:** *"Là Nhân viên kinh doanh, tôi muốn soạn báo giá từ một cơ hội, để gửi báo giá trong buổi chiều cùng ngày khách hỏi."*  
> **Ngôn ngữ phát triển:** Python 3 (Flask Framework) + HTML5/CSS3/JavaScript  
> **Môi trường vận hành:** Visual Studio Code / Terminal trên hệ điều hành Windows  

---

## 🎯 1. BẢNG ĐỐI CHIẾU TIÊU CHÍ CHẤP NHẬN (ACCEPTANCE CRITERIA)

Dự án được xây dựng và kiểm thử bám sát 100% từng yêu cầu trong hình ảnh đề bài (Ticket SCRUM-31):

| Tiêu Chí Trong Đề Bài | Yêu Cầu Của Đề Bài | Cách Hệ Thống Python Đáp Ứng & Triển Khai |
| :--- | :--- | :--- |
| **Tiêu đề User Story** | *Là Nhân viên kinh doanh, tôi muốn soạn báo giá từ một cơ hội, để gửi báo giá trong buổi chiều cùng ngày khách hỏi.* | Bàn làm việc Sales Rep cung cấp nút **"⚡ Soạn Báo Giá 1-Click"** trên từng cơ hội khách vừa hỏi sáng nay. Hệ thống tự động kế thừa trọn vẹn thông tin khách hàng và danh sách sản phẩm, cho phép nhân viên hoàn tất và phát hành báo giá chính thức ngay trong buổi chiều cùng ngày. |
| **Tiêu chí 1 (Description)** | *Dòng sản phẩm được kế thừa từ cơ hội, sửa lại được* | Hàm backend Python `Database.create_quote_from_opportunity()` tự động sao chép (clone) toàn bộ danh sách sản phẩm từ Cơ hội (`line_items`).<br>Nhân viên có thể **sửa đổi linh hoạt**:<br>• Chỉnh sửa số lượng, đơn giá trực tiếp trên bảng.<br>• Bấm **"+ Dòng Tùy Chỉnh"** hoặc chọn nhanh từ **Danh mục sản phẩm chuẩn (Product Catalog)** để thêm mặt hàng mới.<br>• Bấm biểu tượng 🗑️ để xóa bớt sản phẩm không phù hợp. |
| **Tiêu chí 2 (Description)** | *Mỗi dòng nhập chiết khấu theo phần trăm hoặc số tiền, hệ thống tính lại thành tiền ngay* | Trên từng dòng sản phẩm, nhân viên có thể linh hoạt chuyển đổi giữa 2 hình thức chiết khấu:<br>1. **Chiết khấu theo phần trăm (`%`)**: `Tiền chiết khấu = Số lượng * Đơn giá * (% / 100)`.<br>2. **Chiết khấu theo số tiền cố định (`VNĐ`)**: Giảm trực tiếp số tiền mong muốn (không vượt quá thành tiền gốc).<br>• `Thành tiền sau chiết khấu = (Số lượng * Đơn giá) - Tiền chiết khấu`.<br>• **Tính toán tức thời (Real-time Recalculation)**: Client JavaScript tự động tính toán lại thành tiền ngay khi gõ phím mà không cần reload trang; Backend Python tính toán chuẩn xác 100% khi lưu trữ. |
| **Tiêu chí 3 (Description)** | *Hiển thị mức chiết khấu tổng và cảnh báo khi chạm ngưỡng cần duyệt* | • Hệ thống tự động tính **Mức chiết khấu tổng (%)** = `(Tổng tiền chiết khấu các dòng / Tổng tiền hàng trước chiết khấu) * 100%`.<br>• Cấu hình ngưỡng phê duyệt của NVKD: **`DISCOUNT_APPROVAL_THRESHOLD_PERCENT = 10.0%`**.<br>• Khi chiết khấu tổng < 10%: Báo giá hiển thị huy hiệu xanh an toàn, NVKD có toàn quyền gửi khách hàng ngay trong ngày.<br>• **Khi chiết khấu tổng chạm/vượt ngưỡng (>= 10.0%)**: Hệ thống lập tức kích hoạt khung **CẢNH BÁO MÀU ĐỎ KHẨN CẤP**, tự động chuyển trạng thái sang `PENDING_APPROVAL` (Chờ duyệt chiết khấu) và gửi thông báo chuông tới Trưởng nhóm / Giám đốc để xem xét duyệt trước khi gửi khách. |
| **Tiêu chí 4 (Description)** | *Khai báo hiệu lực báo giá, điều khoản thanh toán và điều khoản giao hàng* | Form soạn báo giá cung cấp đầy đủ các trường thông tin chuẩn thương mại B2B:<br>1. **Hiệu lực báo giá (Validity)**: Chọn nhanh 3 ngày, 7 ngày, 15 ngày, 30 ngày. Hệ thống tự động tính toán chính xác ngày hết hạn (`valid_until`).<br>2. **Điều khoản thanh toán (Payment Terms)**: Tích hợp sẵn 5 mẫu chuẩn (Tạm ứng 50%, Net 30, Thanh toán 100% trước khi giao hàng,...) kèm ô soạn thảo tùy biến.<br>3. **Điều khoản giao hàng (Delivery Terms)**: Mẫu giao hàng nội thành 24h, bàn giao bản quyền trực tuyến 4h, giao tại kho bên mua (DDP),...<br>4. Cam kết bảo hành, hỗ trợ kỹ thuật và ghi chú chi tiết. |
| **Tiêu chí 5 (Description)** | *Lưu nháp và sửa tiếp được* | • Cung cấp nút **"💾 Lưu Nháp (Sửa Tiếp Sau)"**: NVKD có thể lưu dở báo giá bất kỳ lúc nào khi bận việc.<br>• Báo giá ở trạng thái `DRAFT` (Bản nháp) luôn có nút **"✏️ Chỉnh Sửa Báo Giá"** để mở lại form sửa đổi toàn diện (sản phẩm, giá, chiết khấu, điều khoản).<br>• Mỗi lần lưu, hệ thống tự động tăng số phiên bản nháp (`draft_version: v1, v2, v3...`) và ghi nhật ký kiểm toán (Audit Log).<br>• Nếu báo giá bị Trưởng nhóm từ chối duyệt chiết khấu (`REJECTED`), hệ thống mở lại quyền sửa (`can_edit = True`) để NVKD điều chỉnh lại chiết khấu cho phù hợp. |

---

## 🏛️ 2. KIẾN TRÚC HỆ THỐNG & CẤU TRÚC THƯ MỤC

```text
scrum_31/
├── app.py                      # Flask Server, Web Routes, REST APIs & Persona Switcher
├── config.py                   # Cấu hình hằng số (Trạng thái Báo giá, Ngưỡng chiết khấu 10%, Mẫu điều khoản)
├── database.py                 # Quản lý dữ liệu Thread-safe, mô hình Cơ hội, Báo giá, Sản phẩm & Thuật toán tính toán
├── requirements.txt            # Thư viện phụ thuộc (Flask >= 3.0.0)
├── run.bat                     # File 1-click khởi động ứng dụng trên Windows
├── README.md                   # Báo cáo kỹ thuật & Hướng dẫn sử dụng chi tiết
├── static/
│   ├── css/
│   │   └── style.css           # Giao diện hiện đại Glassmorphism, khung cảnh báo chiết khấu động
│   └── js/
│       └── main.js             # Client JavaScript tính toán chiết khấu % & tiền tức thời, cảnh báo ngưỡng duyệt
├── templates/
│   ├── base.html               # Layout chính, Topbar Jira ticket, Persona Switcher, Navbar
│   ├── dashboard.html          # Bàn làm việc NVKD, cơ hội cần gửi báo giá trong chiều, danh sách bản nháp
│   ├── opportunities_list.html # Danh sách Cơ hội bán hàng, nút "⚡ Soạn Báo Giá 1-Click" (AC1)
│   ├── quote_create.html       # Form soạn báo giá mới kế thừa sản phẩm từ cơ hội (AC1, AC2, AC3, AC4, AC5)
│   ├── quote_edit.html         # Form chỉnh sửa bản nháp báo giá đang lưu dở (AC5)
│   ├── quote_detail.html       # Chi tiết báo giá thương mại B2B, duyệt chiết khấu & cảnh báo
│   ├── quotes_list.html        # Danh sách tất cả Báo giá kèm bộ lọc trạng thái (Bản nháp, Chờ duyệt, Đã gửi)
│   ├── quote_print.html        # Bản in Báo giá A4 / Xuất PDF thương mại chuyên nghiệp
│   └── simulator.html          # Trình mô phỏng & chạy test tự động 5 tiêu chí trong 1 click
└── tests/
    ├── __init__.py
    ├── test_ac1_product_inheritance.py        # Unit Test Tiêu chí 1: Kế thừa & sửa đổi dòng sản phẩm
    ├── test_ac2_line_discount_calculation.py  # Unit Test Tiêu chí 2: Chiết khấu % hoặc số tiền & tính lại ngay
    ├── test_ac3_approval_threshold_warning.py # Unit Test Tiêu chí 3: Mức chiết khấu tổng & cảnh báo ngưỡng duyệt
    ├── test_ac4_terms_and_validity.py         # Unit Test Tiêu chí 4: Hiệu lực báo giá & điều khoản thanh toán/giao hàng
    ├── test_ac5_save_draft_and_edit.py        # Unit Test Tiêu chí 5: Lưu nháp và sửa tiếp được
    └── test_web_routes.py                     # Integration Test toàn bộ Web Routes & APIs
```

---

## ⚙️ 3. HƯỚNG DẪN CÀI ĐẶT & VẬN HÀNH TRÊN WINDOWS

### Cách 1: Khởi động 1-Click bằng file `run.bat` (Khuyến nghị)
1. Mở thư mục `Backend\scrum_31`.
2. Nhấp đúp chuột vào file **`run.bat`**.
3. Hệ thống sẽ tự động kiểm tra thư viện `Flask` và tự động mở trình duyệt tại:
   👉 **`http://127.0.0.1:5000`**

### Cách 2: Chạy thủ công qua Terminal / Command Prompt
```bash
# 1. Di chuyển vào thư mục dự án
cd Backend\scrum_31

# 2. Cài đặt thư viện phụ thuộc
py -m pip install -r requirements.txt

# 3. Khởi chạy ứng dụng
py app.py
```

---

## 🧪 4. HƯỚNG DẪN CHẠY BỘ KIỂM THỬ TỰ ĐỘNG (UNIT & INTEGRATION TESTS)

Dự án đi kèm bộ 19 bài kiểm thử tự động bao phủ 100% 5 tiêu chí chấp nhận:

```bash
cd Backend\scrum_31
py -m unittest discover tests
```

**Kết quả kiểm thử thực tế:**
```text
...................
----------------------------------------------------------------------
Ran 19 tests in 0.135s

OK
```

---

## ⚡ 5. TRÌNH KIỂM THỬ TRỰC QUAN (SIMULATOR TRÊN WEB)

1. Mở trình duyệt truy cập: `http://127.0.0.1:5000/simulator` (hoặc bấm nút **"⚡ Kiểm Thử 5 Tiêu Chí"** trên thanh menu).
2. Bấm nút **"▶️ Chạy Kiểm Thử 5 Tiêu Chí Ngay"**.
3. Hệ thống sẽ thực thi các kịch bản kiểm thử API thời gian thực và hiển thị các huy hiệu **✅ Đạt 100%** cùng log chi tiết cho từng tiêu chí.
