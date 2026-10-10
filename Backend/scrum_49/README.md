# HỆ THỐNG CẤU HÌNH QUY TẮC PHÂN BỔ LEAD TỰ ĐỘNG (AUTOPLEAD CRM)

> **Mã Nhiệm Vụ (Jira Ticket):** `⚡ SCRUM-30 / ☑ SCRUM-49`  
> **Vai trò người dùng:** Giám đốc kinh doanh (Sales Director)  
> **Ngôn ngữ phát triển:** Python 3 (Flask Framework) + HTML5/CSS3/JavaScript  
> **Môi trường vận hành:** Visual Studio Code / Terminal trên hệ điều hành Windows  

---

## 🎯 1. BẢNG ĐỐI CHIẾU TIÊU CHÍ CHẤP NHẬN (ACCEPTANCE CRITERIA)

Dự án được xây dựng và kiểm thử bám sát 100% từng yêu cầu trong ticket SCRUM-49:

| Tiêu Chí Trong Ticket | Yêu Cầu Của Đề Bài | Cách Hệ Thống Python Đáp Ứng & Triển Khai |
| :--- | :--- | :--- |
| **Tiêu đề User Story** | *Là Giám đốc kinh doanh, tôi muốn cấu hình quy tắc phân bổ lead tự động, để lead tới tay người phụ trách trong vài phút thay vì chờ họp giao ban.* | Xây dựng giao diện web chuyên nghiệp cho phép Giám đốc kinh doanh cấu hình động các quy tắc phân bổ. Lead khi vào hệ thống được luồng nền định tuyến tự động chỉ trong **2 - 3 giây** (SLA tối đa 5 phút), gửi ngay tới tay chuyên viên phụ trách mà không cần đợi họp giao ban. |
| **Tiêu chí 1 (Description)** | *Phân bổ theo khu vực, theo ngành nghề, hoặc xoay vòng đều trong nhóm.* | 1. **Theo khu vực:** Hỗ trợ lọc theo `Miền Bắc`, `Miền Trung`, `Miền Nam`, hoặc `Toàn quốc`.<br>2. **Theo ngành nghề:** Hỗ trợ lọc theo `Tài chính - Ngân hàng`, `Bất động sản`, `Công nghệ thông tin`, `Bán lẻ & TMĐT`, `Sản xuất`,...<br>3. **Xoay vòng đều (Round-Robin):** Tự động luân chuyển con trỏ xoay vòng giữa các thành viên đang hoạt động (Active) trong nhóm kinh doanh, đảm bảo số lượng lead được chia đều công bằng. |
| **Tiêu chí 2 (Description)** | *Nhiều quy tắc xếp theo thứ tự ưu tiên, quy tắc đầu tiên khớp sẽ thắng.* | Hệ thống hỗ trợ đánh số thứ tự ưu tiên `Priority: #1, #2, #3, ...`<br>Có nút ⬆️/⬇️ tăng giảm thứ tự ưu tiên trực quan.<br>Bộ máy `LeadAllocationEngine` duyệt tuần tự các quy tắc theo thứ tự ưu tiên tăng dần: **quy tắc đầu tiên thỏa mãn tất cả điều kiện sẽ được áp dụng ngay lập tức (First-Match-Wins)** và dừng duyệt các quy tắc sau. |
| **Tiêu chí 3 (Description)** | *Lead không khớp quy tắc nào rơi vào hàng chờ để trưởng nhóm phân tay.* | Khi một lead không khớp với bất kỳ quy tắc nào trong danh sách (hoặc thuộc ngành nghề/khu vực chưa cấu hình), hệ thống tự động chuyển lead sang trạng thái `MANUAL_QUEUE` (Hàng chờ phân tay).<br>Trang `/manual-queue` dành riêng cho Trưởng nhóm để xem lý do không khớp và bấm nút **"Phân công tay ngay"** cho nhân viên, kèm tính năng **"Thử khớp lại quy tắc"** khi Giám đốc vừa bổ sung rule mới. |
| **Tiêu chí 4 (Description)** | *Phân bổ chạy nền, hoàn tất trong vòng 5 phút kể từ khi lead vào.* | Triển khai luồng chạy nền độc lập `BackgroundAllocationWorker` (Daemon Thread trong Python) quét liên tục mỗi 2 giây.<br>Lead nạp vào ở trạng thái `PENDING` được worker xử lý tự động trong vòng **1 - 3 giây** (hoàn tất sớm hơn rất nhiều so với ngưỡng SLA 5 phút / 300 giây).<br>Ghi nhận chính xác `created_at`, `processed_at`, `elapsed_seconds` và cấp huy hiệu **ĐẠT CHUẨN SLA (MET)**. |

---

## 🏛️ 2. KIẾN TRÚC HỆ THỐNG & CẤU TRÚC THƯ MỤC

```text
scrum_49/
├── app.py                      # Máy chủ Flask, Web routes, Persona switcher & REST API
├── engine.py                   # Bộ máy so khớp First-Match-Wins & Background Allocation Worker
├── database.py                 # Quản lý dữ liệu Thread-safe, thuật toán Round-Robin & Seed data
├── config.py                   # Cấu hình hằng số Khu vực, Ngành nghề, SLA Limit (300 giây)
├── run.bat                     # File chạy 1-click khởi động ứng dụng trên Windows
├── requirements.txt            # Thư viện phụ thuộc (Flask >= 3.0.0)
├── README.md                   # Tài liệu hướng dẫn & Báo cáo kỹ thuật chi tiết
├── tests/
│   ├── __init__.py
│   ├── test_allocation_system.py # Unit test kiểm tra 100% 4 tiêu chí chấp nhận
│   ├── test_web_routes.py        # Integration test kiểm tra toàn bộ trang web và API
│   └── check_status.py           # Kịch bản kiểm tra mô phỏng nạp lead và worker
├── static/
│   ├── css/
│   │   └── style.css           # Giao diện hiện đại, Glassmorphism, chuẩn thẩm mỹ doanh nghiệp
│   └── js/
│       └── main.js             # Xử lý Modal, chuyển đổi form, polling trạng thái thời gian thực
└── templates/
    ├── base.html               # Layout chính, thanh SLA topbar, Persona switcher
    ├── dashboard.html          # Bảng điều khiển KPI, simulator 1-click, tiến trình phân bổ
    ├── rules.html              # Quản lý quy tắc, đổi độ ưu tiên First-Match-Wins, modal thêm/sửa
    ├── leads.html              # Danh sách toàn bộ Lead, bộ lọc đa chiều, theo dõi SLA
    ├── manual_queue.html       # Hàng chờ dành cho Trưởng nhóm, phân công tay, quét lại rule
    ├── team_reps.html          # Giám sát tính công bằng xoay vòng Round-Robin giữa các sales
    └── worker_logs.html        # Giám sát luồng nền, điều khiển worker, nhật ký chi tiết
```

---

## 🚀 3. HƯỚNG DẪN KHỞI CHẠY TRÊN VISUAL STUDIO CODE & WINDOWS

### Cách 1: Chạy 1-Click bằng file `run.bat` (Khuyên dùng)
1. Mở thư mục `scrum_49` trong File Explorer hoặc VS Code.
2. Nhấp đúp chuột vào file:
   ```text
   run.bat
   ```
   Hệ thống sẽ tự động kiểm tra thư viện và bật trình duyệt tại địa chỉ:  
   👉 **`http://127.0.0.1:5000`**

---

### Cách 2: Chạy thông qua Terminal của VS Code
1. Mở **Visual Studio Code**, chọn **File** -> **Open Folder...** -> chọn thư mục:
   ```text
   C:\Users\FPT SHOP\.gemini\antigravity-ide\scratch\scrum_49
   ```
2. Mở Terminal trong VS Code bằng phím tắt `` Ctrl + ` `` (hoặc vào menu **Terminal** -> **New Terminal**).
3. Cài đặt thư viện:
   ```bash
   py -m pip install -r requirements.txt
   ```
4. Khởi chạy ứng dụng:
   ```bash
   py app.py
   ```
5. Mở trình duyệt web và truy cập:  
   👉 **`http://127.0.0.1:5000`**

---

## 🧪 4. HƯỚNG DẪN CHẠY BỘ KIỂM THỬ TỰ ĐỘNG (UNIT & INTEGRATION TESTS)

Mở Terminal trong thư mục `scrum_49` và thực thi:

```bash
py -m unittest discover tests
```

**Kết quả kiểm thử thành công 100%:**
```text
.............
----------------------------------------------------------------------
Ran 13 tests in 0.113s

OK
```

### Các ca kiểm thử bao gồm:
1. `test_criterion_1_allocation_by_region_and_industry`: Phân bổ chính xác theo Khu vực và Ngành nghề.
2. `test_criterion_1_round_robin_fair_distribution`: Thuật toán xoay vòng Round-Robin chia đều công bằng cho các thành viên trong nhóm.
3. `test_criterion_2_first_match_wins_priority`: Quy tắc có độ ưu tiên cao hơn (#1) luôn thắng quy tắc thấp hơn (#2, #3), First-Match-Wins.
4. `test_criterion_3_unmatched_lead_falls_into_manual_queue`: Lead không khớp quy tắc tự động rơi vào hàng chờ `MANUAL_QUEUE`.
5. `test_criterion_3_manual_assignment_by_team_lead`: Trưởng nhóm phân công tay thành công cho chuyên viên từ hàng chờ.
6. `test_criterion_4_background_worker_auto_processing`: Luồng chạy nền tự động xử lý lead PENDING và hoàn tất trong vài giây, đạt SLA 5 phút.
7. `test_web_routes`: Kiểm tra toàn bộ 7 trang giao diện người dùng và REST API.

---

## 🎮 5. CÁC TÍNH NĂNG NỔI BẬT ĐỂ DEMO VÀ TRẢI NGHIỆM

1. **Công cụ mô phỏng 1-Click (Simulation Tools):**
   - Trên Dashboard, bấm **"Nạp 1 Lead Thử Nghiệm"** hoặc **"Nạp Batch 5 Leads"**:
   - Ngay lập tức quan sát luồng nền quét và phân bổ tự động trong 2 giây. Các lead khớp quy tắc được giao cho nhân viên, lead không khớp rơi vào hàng chờ.
2. **Cấu hình Quy tắc First-Match-Wins (`/rules`):**
   - Bấm nút ⬆️ hoặc ⬇️ để đổi thứ tự ưu tiên của quy tắc.
   - Bấm **"Thêm Quy Tắc Mới"**: chọn khu vực, ngành nghề, phương thức xoay vòng nhóm hoặc chỉ định trực tiếp.
3. **Hàng chờ phân tay của Trưởng nhóm (`/manual-queue`):**
   - Đổi vai trò sang **Trưởng nhóm Miền Bắc (Trần Văn Hùng)** ở góc trên bên phải.
   - Vào hàng chờ xem các lead chưa khớp quy tắc, ấn **"Phân Công Tay"** để gán trực tiếp cho nhân viên kèm ghi chú chỉ đạo.
4. **Giám sát Xoay vòng Round-Robin (`/team-reps`):**
   - Xem vị trí con trỏ Round-Robin hiện tại: biết chính xác ai sẽ là người tiếp theo nhận lead trong nhóm.
5. **Giám sát Luồng Nền & SLA (`/worker-monitor`):**
   - Xem đồng hồ SLA 300s (5 phút), nút Tạm dừng/Tiếp tục luồng nền và toàn bộ nhật ký kiểm toán (Audit Log).
