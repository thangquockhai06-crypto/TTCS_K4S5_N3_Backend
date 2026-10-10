# HỆ THỐNG TIẾP NHẬN LEAD & RÀNG BUỘC SLA PHẢN HỒI (AUTOPLEAD CRM)

> **Mã Nhiệm Vụ (Jira Ticket):** `⚡ SCRUM-30 / ☑ SCRUM-51`  
> **Vai trò người dùng:** Nhân viên kinh doanh (Sales Representative) & Trưởng nhóm kinh doanh (Team Leader)  
> **Ngôn ngữ phát triển:** Python 3 (Flask Framework) + HTML5/CSS3/JavaScript  
> **Môi trường vận hành:** Visual Studio Code / Terminal trên hệ điều hành Windows  

---

## 🎯 1. BẢNG ĐỐI CHIẾU TIÊU CHÍ CHẤP NHẬN (ACCEPTANCE CRITERIA)

Dự án được xây dựng và kiểm thử bám sát 100% từng yêu cầu trong hình ảnh đề bài (Ticket SCRUM-51):

| Tiêu Chí Trong Đề Bài | Yêu Cầu Của Đề Bài | Cách Hệ Thống Python Đáp Ứng & Triển Khai |
| :--- | :--- | :--- |
| **Tiêu đề User Story** | *Là Nhân viên kinh doanh, tôi muốn nhận hoặc từ chối lead được phân, có ràng buộc SLA phản hồi, để lead không nằm im ba ngày rồi nguội hẳn.* | Giao diện Bàn làm việc Sales Rep cho phép nhân viên xem danh sách lead được phân công, chủ động đưa ra quyết định **"Nhận lead"** hoặc **"Từ chối lead"** ngay lập tức. Hệ thống hiển thị đồng hồ đếm ngược SLA phản hồi thời gian thực và tự động giám sát để lead không bị bỏ quên quá hạn. |
| **Tiêu chí 1 (Description)** | *Nhân viên nhận lead thì lead chuyển sang "Đang chăm sóc"* | Khi nhân viên bấm nút **"✅ Nhận Lead"**, backend Python cập nhật trạng thái lead thành `IN_CARE` (*Đang chăm sóc*), ghi nhận thời điểm `accepted_at`, kích hoạt bộ đếm ngược SLA phản hồi và chuyển lead xuống danh sách chăm sóc trực tiếp để nhân viên liên hệ tư vấn. |
| **Tiêu chí 2 (Description)** | *Từ chối bắt buộc nhập lý do, lead quay lại hàng chờ phân bổ* | Khi nhân viên bấm nút **"❌ Từ chối"**, hệ thống bật Modal popup yêu cầu nhập lý do.<br>• **Ràng buộc chặt chẽ:** Nếu để trống hoặc chỉ nhập khoảng trắng, cả Frontend và Backend Python đều **chặn thao tác và báo lỗi** (`ValueError: Từ chối lead BẮT BUỘC phải nhập lý do cụ thể!`).<br>• Khi nhập lý do hợp lệ: Lead được gỡ khỏi nhân viên hiện tại, chuyển sang trạng thái `PENDING_ALLOCATION` (*Hàng chờ phân bổ*), lưu lịch sử từ chối và **tự động gửi thông báo cảnh báo tới Trưởng nhóm** để phân bổ lại cho nhân viên khác. |
| **Tiêu chí 3 (Description)** | *Quá SLA phản hồi mà chưa liên hệ thì lead được gắn cờ và báo cho trưởng nhóm* | Luồng chạy nền `BackgroundSLAMonitor` (Daemon Thread trong Python) quét liên tục mỗi 2 giây.<br>Khi phát hiện lead quá hạn SLA phản hồi (`now >= sla_deadline`) mà nhân viên chưa thực hiện liên hệ (`contacted_at is None`):<br>1. Hệ thống tự động gắn cờ vi phạm: `is_flagged = True`, cấp huy hiệu **🚩 QUÁ HẠN SLA**.<br>2. Tự động tạo cảnh báo khẩn cấp (`level="URGENT"`) gửi tới Trưởng nhóm (Team Leader) kèm chuông thông báo đỏ.<br>3. Hiển thị lead nổi bật trên Bàn làm việc của Trưởng nhóm để kịp thời đôn đốc hoặc điều chuyển sang nhân viên khác. |

---

## 🏛️ 2. KIẾN TRÚC HỆ THỐNG & CẤU TRÚC THƯ MỤC

```text
scrum_51/
├── app.py                      # Flask Server, Web Routes, Persona Switcher & REST APIs
├── config.py                   # Cấu hình hằng số (Trạng thái, Roles, Cấu hình SLA, Lý do mẫu)
├── database.py                 # Quản lý dữ liệu Thread-safe, mô hình Lead, xử lý 3 tiêu chí nghiệp vụ
├── sla_engine.py               # Background SLA Monitor Worker quét ngầm & tự động gắn cờ 🚩
├── run.bat                     # File 1-click khởi động ứng dụng trên Windows
├── requirements.txt            # Thư viện phụ thuộc (Flask >= 3.0.0)
├── README.md                   # Báo cáo kỹ thuật & Hướng dẫn sử dụng chi tiết
├── static/
│   ├── css/
│   │   └── style.css           # Giao diện hiện đại Glassmorphism, chuẩn thẩm mỹ CRM doanh nghiệp
│   └── js/
│       └── main.js             # Đếm ngược SLA live theo giây, Modal từ chối & ghi nhận liên hệ
├── templates/
│   ├── base.html               # Layout chính, SLA Topbar, Persona Switcher, Modal từ chối/liên hệ
│   ├── dashboard.html          # Tổng quan KPIs, danh sách lead bị cờ đỏ 🚩, hàng chờ phân bổ
│   ├── sales_rep.html          # Bàn làm việc Sales Rep (Nhận lead, Từ chối, Đếm ngược SLA, Liên hệ)
│   ├── team_lead.html          # Bàn làm việc Trưởng nhóm (Hàng chờ lead từ chối, Cờ đỏ SLA, Giám sát)
│   ├── all_leads.html          # Danh sách toàn bộ Lead, bộ lọc đa chiều (trạng thái, cờ, nhân viên)
│   ├── lead_detail.html        # Chi tiết Lead, dòng thời gian SLA, lịch sử từ chối và ghi chú liên hệ
│   ├── create_lead.html        # Form thêm lead mới linh hoạt
│   ├── notifications.html      # Hộp thư cảnh báo khẩn cấp dành cho Trưởng nhóm
│   ├── simulator.html          # Bảng điều khiển kiểm thử tức thì (Test 3 tiêu chí trong 30s)
│   └── audit_logs.html         # Nhật ký kiểm toán minh bạch toàn bộ thao tác hệ thống
└── tests/
    ├── __init__.py
    ├── test_ac1_accept_lead.py # Unit Test Tiêu chí 1: Nhận lead -> Đang chăm sóc
    ├── test_ac2_reject_lead.py # Unit Test Tiêu chí 2: Từ chối bắt buộc lý do -> Hàng chờ phân bổ
    ├── test_ac3_sla_breach.py  # Unit Test Tiêu chí 3: Quá SLA chưa liên hệ -> Gắn cờ 🚩 & báo Trưởng nhóm
    └── test_web_routes.py      # Integration Test toàn bộ luồng Web UI & REST APIs
```

---

## 🚀 3. HƯỚNG DẪN KHỞI CHẠY TRÊN WINDOWS & VISUAL STUDIO CODE

### Cách 1: Khởi chạy 1-Click bằng file `run.bat` (Khuyên dùng)
1. Mở File Explorer và điều hướng tới thư mục:
   ```text
   C:\Users\FPT SHOP\.gemini\antigravity-ide\scratch\scrum_51
   ```
2. Nhấp đúp chuột vào file **`run.bat`**.
3. Ứng dụng sẽ tự động cài thư viện và mở trình duyệt tại: **http://127.0.0.1:5000**

---

### Cách 2: Khởi chạy thủ công từ Terminal / VS Code
1. Mở thư mục `scrum_51` trong **Visual Studio Code**.
2. Mở Terminal tích hợp (`Ctrl + ~`).
3. Cài đặt thư viện:
   ```bash
   py -m pip install -r requirements.txt
   ```
4. Khởi chạy máy chủ Flask:
   ```bash
   py app.py
   ```
5. Truy cập trình duyệt tại địa chỉ: 👉 **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## 🧪 4. HƯỚNG DẪN KIỂM THỬ TRỰC QUAN 3 TIÊU CHÍ TRÊN GIAO DIỆN

Hệ thống tích hợp sẵn tính năng **Persona Switcher** ở góc phải trên cùng để bạn đóng vai linh hoạt:
- 👨‍💼 **Nguyễn Văn Tuấn** / 👩‍💼 **Trần Thị Mai**: Nhân viên kinh doanh (Sales Rep)
- 🧑‍💼 **Lê Hoàng Nam**: Trưởng nhóm kinh doanh (Team Lead)
- 👔 **Phạm Đức Thắng**: Giám đốc kinh doanh (Sales Director)

### Kiểm thử Tiêu chí 1: Nhận lead &rarr; Chuyển sang "Đang chăm sóc"
1. Chọn vai trò **Nguyễn Văn Tuấn** trên Persona Switcher.
2. Vào menu **"💼 Lead Của Tôi"**.
3. Tại bảng *1. Lead Chờ Bạn Tiếp Nhận*, bấm nút **"✅ Nhận Lead"** (ví dụ lead `LEAD-101`).
4. **Kết quả:**
   - Thông báo màu xanh báo nhận lead thành công.
   - Lead ngay lập tức chuyển trạng thái sang **"Đang chăm sóc"** (`IN_CARE`).
   - Xuất hiện tại bảng *2. Lead Bạn Đang Chăm Sóc* và bắt đầu đếm ngược thời hạn SLA phản hồi.

---

### Kiểm thử Tiêu chí 2: Từ chối bắt buộc nhập lý do &rarr; Quay lại hàng chờ phân bổ
1. Tại menu **"💼 Lead Của Tôi"**, chọn một lead và bấm nút **"❌ Từ Chối"**.
2. Hộp thoại Modal hiện lên:
   - **Thử nghiệm ràng buộc:** Bỏ trống ô lý do và bấm xác nhận &rarr; Hệ thống lập tức cảnh báo màu đỏ và chặn không cho gửi.
   - **Thao tác hợp lệ:** Nhấp chọn một lý do gợi ý (hoặc tự gõ lý do) &rarr; Bấm **"Xác Nhận Từ Chối"**.
3. **Kết quả:**
   - Lead biến mất khỏi danh sách phụ trách của nhân viên.
   - Chuyển sang vai trò **Lê Hoàng Nam (Trưởng nhóm)** và vào menu **"👥 Hàng Chờ & Đội Nhóm"**: Lead đã nằm trong **"Hàng chờ phân bổ"** kèm theo chính xác **Lý do từ chối** mà nhân viên vừa nhập.
   - Trưởng nhóm có nút **"➕ Phân Bổ Ngay"** để điều chuyển cho nhân viên khác.

---

### Kiểm thử Tiêu chí 3: Quá SLA phản hồi mà chưa liên hệ &rarr; Gắn cờ 🚩 và báo Trưởng nhóm
1. Vào menu **"⚡ Kiểm Thử SLA"** (`/simulator`).
2. Tại công cụ số 1, bấm **"Tạo Lead Test SLA Siêu Ngắn (30s)"** (Lead được gán cho Nguyễn Văn Tuấn).
3. Vào trang **"💼 Lead Của Tôi"**: Quan sát đồng hồ đếm ngược SLA (`⏱️ Còn 29s`, `28s`...).
4. Chờ 30 giây trôi qua mà không bấm nút "Ghi nhận liên hệ":
   - Đồng hồ chuyển sang màu đỏ: `🚩 Quá hạn Xs`.
   - Luồng nền tự động gắn cờ: `is_flagged = True` kèm huy hiệu **🚩 QUÁ HẠN SLA**.
5. Chuyển sang vai trò **Lê Hoàng Nam (Trưởng nhóm)**:
   - Chuông thông báo nhảy số đỏ báo động.
   - Trong trang **"🔔 Thông Báo"** và trang **"👥 Hàng Chờ & Đội Nhóm"**, xuất hiện cảnh báo khẩn cấp: *Lead quá thời hạn SLA phản hồi mà chưa liên hệ khách hàng!*
   - Trưởng nhóm có nút **"🔄 Thu Hồi & Điều Chuyển Ngay"** để cứu lead khỏi nguy cơ nguội lạnh.
6. *(Hoặc bạn có thể bấm nút **"⚡ Quá Hạn Ngay"** tại trang Simulator để thấy cờ đỏ và cảnh báo xuất hiện lập tức trong 1 giây).*

---

### Hoàn tất SLA phản hồi: Ghi nhận liên hệ
Khi nhân viên đang chăm sóc lead và kịp thời bấm nút **"📞 Ghi Nhận Liên Hệ"** (chọn kênh gọi điện/email và nhập ghi chú) &rarr; Lead chuyển sang **"Đã liên hệ"** (`CONTACTED`), hoàn thành cam kết SLA và không bao giờ bị gắn cờ quá hạn.

---

## 🤖 5. BỘ KIỂM THỬ TỰ ĐỘNG (AUTOMATED TEST SUITE)

Hệ thống được trang bị 15 bài kiểm thử tự động (Unit Tests & Integration Tests) đạt tỷ lệ **100% Passed**:

Chạy lệnh kiểm thử:
```bash
py -m unittest discover -s tests -p "test_*.py" -v
```

Kết quả thực tế:
```text
test_accept_lead_creates_audit_log (test_ac1_accept_lead.TestAcceptLeadCriteria) ... ok
test_accept_lead_transitions_to_in_care (test_ac1_accept_lead.TestAcceptLeadCriteria) ... ok
test_accept_non_existent_lead_raises_error (test_ac1_accept_lead.TestAcceptLeadCriteria) ... ok
test_reject_with_valid_reason_moves_to_pending_allocation_queue (test_ac2_reject_lead.TestRejectLeadCriteria) ... ok
test_reject_without_reason_is_strictly_rejected (test_ac2_reject_lead.TestRejectLeadCriteria) ... ok
test_contacted_lead_is_never_flagged (test_ac3_sla_breach.TestSLABreachCriteria) ... ok
test_fast_forward_simulation (test_ac3_sla_breach.TestSLABreachCriteria) ... ok
test_overdue_lead_without_contact_is_flagged_and_alerts_team_lead (test_ac3_sla_breach.TestSLABreachCriteria) ... ok
test_accept_lead_via_post (test_web_routes.TestWebRoutes) ... ok
test_api_countdown_endpoint (test_web_routes.TestWebRoutes) ... ok
test_dashboard_route (test_web_routes.TestWebRoutes) ... ok
test_my_leads_route (test_web_routes.TestWebRoutes) ... ok
test_reject_lead_empty_reason_fails (test_web_routes.TestWebRoutes) ... ok
test_reject_lead_valid_reason_succeeds (test_web_routes.TestWebRoutes) ... ok
test_team_lead_route (test_web_routes.TestWebRoutes) ... ok

----------------------------------------------------------------------
Ran 15 tests in 0.100s

OK
```
