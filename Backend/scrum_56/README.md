# ⚡ AutoLead CRM - Ticket SCRUM-56: Danh Sách Lead Với Bộ Lọc Đa Chiều & Bộ Lọc Lưu Sẵn

> **Epic Cha**: `⚡ SCRUM-30`  
> **Ticket**: `☑ SCRUM-56`  
> **Vai trò**: **Nhân viên kinh doanh (Sales Representative)**  
> **Ngôn ngữ**: **Python 3** (Flask Web Application)  
> **User Story**:  
> *"Là Nhân viên kinh doanh, tôi muốn xem danh sách lead với bộ lọc và bộ lọc lưu sẵn, để mở máy buổi sáng là biết ngay hôm nay cần gọi ai."*

---

## 🎯 3 Tiêu Chí Chấp Nhận (Acceptance Criteria) Đã Hoàn Thành 100%

### 1. Tiêu chí 1: Lọc theo trạng thái, nguồn, phân loại nóng ấm lạnh, người phụ trách, khoảng thời gian
- **Trạng thái Lead (`status`)**:
  - Mới tiếp nhận (`new`), Đã phân bổ (`assigned`), Đang chăm sóc (`in_care`), Đã liên hệ (`contacted`), Tiềm năng cao (`qualified`), Đã chuyển đổi (`converted`), Mất cơ hội (`lost`).
- **Nguồn Lead (`source`)**:
  - Facebook Ads, Google Ads, TikTok Ads, Zalo OA, Website Form, Sự kiện / Hội thảo, Đối tác giới thiệu (Referral).
- **Phân loại nhiệt độ (`temperature`)**:
  - 🔥 **Nóng (HOT)**: Khách hàng có nhu cầu mua gấp, ngân sách lớn, cần chốt ngay.
  - ⚡ **Ấm (WARM)**: Khách hàng đang tìm hiểu so sánh tính năng và cân nhắc giá.
  - ❄️ **Lạnh (COLD)**: Khách hàng mới để lại thông tin tìm hiểu ban đầu, cần nuôi dưỡng lâu dài.
- **Người phụ trách (`assigned_to`)**:
  - `mine` (Chỉ lead tôi phụ trách), `all` (Toàn bộ nhân viên), `unassigned` (Lead mới chưa phân bổ), hoặc lọc theo từng Sales cụ thể (`usr-01`, `usr-02`, `usr-03`).
- **Khoảng thời gian (`date_preset` / `from_date` / `to_date`)**:
  - Tùy chọn nhanh: Hôm nay (`today`), 7 ngày gần nhất (`last_7_days`), 30 ngày gần nhất (`last_30_days`), hoặc khoảng ngày tùy chọn (`custom`).
- **Tìm kiếm từ khóa (`search`)**:
  - Hỗ trợ gõ trực tiếp tên công ty, tên người liên hệ, số điện thoại, hoặc mã Lead.

---

### 2. Tiêu chí 2: Lead quá SLA hiển thị nổi bật
- **Thuật toán tính hạn SLA (`calculate_sla_status`)**:
  - Mỗi lead mới có thời hạn cam kết phản hồi (`sla_deadline`, mặc định 4 giờ làm việc).
  - Nếu hiện tại `now > sla_deadline` và Sales chưa gọi điện (`contacted_at is None`) $\rightarrow$ Xác định **QUÁ HẠN SLA 🚩**.
  - Tính chính xác thời gian trễ: *"Quá hạn X giờ Y phút"* hoặc *"Trễ Z ngày"*.
- **Hiển thị nổi bật trên giao diện**:
  - **Màu sắc & viền đỏ nổi bật**: Toàn bộ dòng trong bảng nhận class `.tr-sla-overdue` (nền hồng đỏ nhạt `#fff5f5`, viền đỏ dày 5px bên trái `border-left: 5px solid #ef4444`).
  - **Badge động nhấp nháy**: Hiển thị thẻ đỏ `.sla-overdue-tag` kèm biểu tượng cảnh báo `🚩 QUÁ HẠN SLA`, đếm giờ trễ.
  - **Ưu tiên đẩy lên đầu danh sách**: Bảng tự động sắp xếp ưu tiên các Lead Quá SLA lên trên cùng để Sales nhìn thấy ngay khi vừa mở màn hình.
  - **Nút hành động đỏ khẩn cấp**: Nút `📞 Gọi Ngay` đổi sang màu đỏ nhấp nháy `.btn-call-urgent`. Khi nhấn gọi, hệ thống ghi nhận cuộc gọi và ngay lập tức giải phóng trạng thái quá hạn SLA.

---

### 3. Tiêu chí 3: Lưu và đặt tên cho bộ lọc hay dùng (Saved Filters / Smart Views)
- **Tập hợp bộ lọc lưu sẵn mặc định phục vụ buổi sáng**:
  1. `☀️ Cần Gọi Sáng Nay (Nóng + Quá SLA + Hẹn Hôm Nay)`: Đây chính là bộ lọc cốt lõi hiện thực hóa trọn vẹn User Story *"Mở máy buổi sáng là biết ngay hôm nay cần gọi ai"*. Bộ lọc này kết hợp 3 điều kiện:
     - Khách hàng Nhiệt độ NÓNG (HOT), **HOẶC**
     - Khách hàng đang bị QUÁ HẠN SLA (chưa gọi), **HOẶC**
     - Khách hàng có lịch hẹn gọi lại vào đúng hôm nay (`next_call_date == today`).
  2. `🚩 Báo Động: Quá Hạn SLA Chưa Gọi`: Gom toàn bộ các khách hàng vi phạm thời hạn phản hồi.
  3. `🔥 Lead Nóng Của Tôi`: Danh sách khách hàng VIP tiềm năng cao được giao cho tài khoản hiện tại.
  4. `⚡ Lead Ấm Đang Chăm Sóc`: Danh sách khách hàng đang tư vấn.
  5. `🆕 Lead Mới Chưa Phân Bổ`: Kho lead mới đổ về cần nhận việc.
- **Tính năng tạo bộ lọc tùy chỉnh theo ý người dùng**:
  - Sales có thể tự do kết hợp bất kỳ tiêu chí nào, sau đó nhấn **"💾 Lưu Bộ Lọc Hiện Tại"**.
  - Đặt tên tùy ý (ví dụ: *"Khách Bất Động Sản Nóng"*, *"Lead Google Khẩn Cấp"*), chọn Icon biểu trưng.
  - **Đánh dấu mặc định (`is_default=True`)**: Đặt bộ lọc làm mặc định khi mở máy buổi sáng. Khi Sales mở trình duyệt vào đầu ngày, CRM tự động áp dụng bộ lọc này ngay lập tức!
  - Cho phép chuyển đổi linh hoạt bằng thanh Tabs/Pill bar, đặt lại mặc định (`⭐ Mở máy`), hoặc xóa bộ lọc không dùng.

---

## 🏗️ Cấu Trúc Dự Án

```
scrum_56/
├── app.py                      # Ứng dụng Flask Web Server, Routing, Xử lý Request/Response
├── config.py                   # Cấu hình danh mục trạng thái, nguồn lead, nhiệt độ, mã SLA, Roles
├── database.py                 # Động cơ lọc đa chiều, Engine tính SLA quá hạn, Quản lý Saved Filters
├── requirements.txt            # Thư viện phụ thuộc (Flask>=3.0.0)
├── run.bat                     # File chạy 1-click tự động trên Windows (Port 5000)
├── README.md                   # Tài liệu hướng dẫn kỹ thuật & giải thích chi tiết
├── static/
│   ├── css/
│   │   └── style.css           # Giao diện Glassmorphism hiện đại, CSS nổi bật Lead quá SLA
│   └── js/
│       └── main.js             # Xử lý Modal lưu bộ lọc & Modal gọi điện nhanh
├── templates/
│   ├── base.html               # Layout chuẩn với Topbar Jira SCRUM-56 & Persona Switcher
│   ├── leads_list.html         # Màn hình chính: Toolbar Saved Filters, Form lọc đa chiều, Bảng Lead
│   └── lead_detail.html        # Màn hình chi tiết Lead & Timeline SLA
└── tests/
    ├── __init__.py
    ├── test_ac1_multi_criteria_filter.py     # 5 bài kiểm thử Tiêu chí 1 (Lọc đa chiều)
    ├── test_ac2_sla_overdue_highlight.py     # 5 bài kiểm thử Tiêu chí 2 (Quá hạn SLA nổi bật)
    ├── test_ac3_saved_filters.py             # 5 bài kiểm thử Tiêu chí 3 (Bộ lọc lưu sẵn)
    └── test_web_routes.py                    # 5 bài kiểm thử Routes Flask & REST APIs
```

---

## 🚀 Hướng Dẫn Cài Đặt & Khởi Chạy

### Cách 1: Chạy 1-Click trên Windows (Khuyên dùng)
Chỉ cần nhấp đúp chuột vào file **`run.bat`**, hệ thống sẽ tự động mở trình duyệt tại:
```
http://127.0.0.1:5000
```

### Cách 2: Khởi chạy bằng dòng lệnh terminal
```bash
# 1. Cài đặt thư viện
py -m pip install -r requirements.txt

# 2. Khởi chạy server Flask
py app.py
```

---

## 🧪 Chạy Toàn Bộ Bộ Kiểm Thử Tự Động (Unit Tests)

Bộ kiểm thử bao gồm **20 test cases** kiểm tra toàn diện 100% logic của 3 tiêu chí:
```bash
py -m unittest discover tests
```

**Kết quả kiểm thử:**
```
....................
----------------------------------------------------------------------
Ran 20 tests in 0.153s

OK
```
