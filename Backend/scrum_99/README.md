# HỆ THỐNG BÁO CÁO HIỆU QUẢ NGUỒN LEAD & CHIẾN DỊCH MARKETING

> **Mã Nhiệm Vụ (Jira Ticket):** `⚡ SCRUM-30 / ☑ SCRUM-99`  
> **User Story:** *"Là Nhân viên Marketing, tôi muốn xem báo cáo hiệu quả từng nguồn lead, để dồn ngân sách vào nguồn thực sự ra doanh thu."*  
> **Ngôn ngữ phát triển:** Python 3 (Flask Framework) + `openpyxl` + HTML5/CSS3/JavaScript  
> **Môi trường vận hành:** Visual Studio Code / Terminal trên hệ điều hành Windows  

---

## 🎯 1. BẢNG ĐỐI CHIẾU TIÊU CHÍ CHẤP NHẬN (ACCEPTANCE CRITERIA)

Dự án được xây dựng và kiểm thử bám sát 100% từng yêu cầu trong hình ảnh đề bài (Ticket SCRUM-99):

| Tiêu Chí Trong Đề Bài | Yêu Cầu Của Đề Bài | Cách Hệ Thống Python Đáp Ứng & Triển Khai |
| :--- | :--- | :--- |
| **Tiêu đề User Story** | *Là Nhân viên Marketing, tôi muốn xem báo cáo hiệu quả từng nguồn lead, để dồn ngân sách vào nguồn thực sự ra doanh thu.* | Xây dựng Bảng điều khiển phân tích Marketing ROI thông minh: Tự động tổng hợp dữ liệu, so sánh doanh thu thực tế và tỷ lệ hoàn vốn (ROAS) giữa các nguồn, đưa ra **Khuyến nghị dồn ngân sách** rõ ràng (như dồn vào *Google Ads*, *Sự kiện Tech Expo*, *Đối tác giới thiệu* và cắt giảm kênh không hiệu quả). |
| **Tiêu chí 1 (Description)** | *Số lead, tỷ lệ được nhận, tỷ lệ chuyển đổi thành cơ hội theo từng nguồn và từng chiến dịch* | Động cơ phân tích trong [`database.py`](file:///c:/Users/FPT%20SHOP/.gemini/antigravity-ide/scratch/scrum_99/database.py) tính toán đa chiều và hiển thị đồng thời 2 bảng số liệu:<br>1. **Bảng hiệu quả theo từng Nguồn Lead (7 nguồn):** Số lead, Lead Sales đã nhận, Tỷ lệ nhận (%), Chuyển đổi thành cơ hội, Tỷ lệ ra cơ hội (%), Hợp đồng chốt (Won), Doanh thu thực tế (VNĐ), ROAS.<br>2. **Bảng hiệu quả theo từng Chiến dịch (7 chiến dịch):** Mã, Tên chiến dịch, Nguồn, Ngân sách, Chi phí, Số lead, Tỷ lệ nhận, Số cơ hội, Tỷ lệ cơ hội, Doanh thu, CPL, CPO, ROAS và đánh giá. |
| **Tiêu chí 2 (Description)** | *Lọc theo khoảng thời gian* | Thanh công cụ lọc thời gian đa năng hỗ trợ cả 2 chế độ:<br>• **Các mốc định sẵn (Presets):** *Hôm nay*, *7 ngày qua*, *30 ngày qua*, *Tháng này*, *Quý này*, *Toàn bộ thời gian*.<br>• **Tùy chọn khoảng ngày (Custom):** Nhập `Từ ngày` & `Đến ngày` (`from_date` và `to_date`).<br>Toàn bộ bảng nguồn, chiến dịch, chỉ số KPI và dữ liệu xuất Excel đều được lọc đồng bộ chính xác. |
| **Tiêu chí 3 (Description)** | *Xuất Excel* | Module [`excel_exporter.py`](file:///c:/Users/FPT%20SHOP/.gemini/antigravity-ide/scratch/scrum_99/excel_exporter.py) tạo trực tiếp file Excel `.xlsx` chuyên nghiệp gồm **3 Sheets**:<br>• **Sheet 1:** *Hiệu Quả Nguồn Lead* (kèm dòng tổng cộng, định dạng tiền VND và tỷ lệ %)<br>• **Sheet 2:** *Hiệu Quả Chiến Dịch* (chi phí, CPL, CPO, ROAS)<br>• **Sheet 3:** *Danh Sách Lead Chi Tiết* (toàn bộ lead trong khoảng thời gian lọc).<br>Tích hợp nút **"📥 Xuất Báo Cáo Excel (.xlsx)"** 1-click tải về ngay trên giao diện web. |

---

## 🏛️ 2. KIẾN TRÚC HỆ THỐNG & CẤU TRÚC THƯ MỤC

```text
scrum_99/
├── app.py                      # Flask Server, Web Routes, Persona Switcher & REST APIs
├── config.py                   # Cấu hình nguồn lead, danh mục chiến dịch, vai trò, trạng thái
├── database.py                 # Động cơ phân tích Marketing ROI, bộ lọc thời gian & dữ liệu thread-safe
├── excel_exporter.py           # Module xuất file Excel (.xlsx) đa sheet chuẩn openpyxl
├── run.bat                     # File khởi động 1-Click trên Windows
├── requirements.txt            # Thư viện phụ thuộc (Flask >= 3.0.0, openpyxl >= 3.1.2)
├── README.md                   # Báo cáo kỹ thuật & Hướng dẫn sử dụng chi tiết
├── static/
│   ├── css/style.css           # Giao diện hiện đại Glassmorphism, chuẩn thẩm mỹ Marketing Analytics
│   └── js/main.js              # Tự động ẩn thông báo flash & tương tác client
├── templates/
│   ├── base.html               # Layout chính, Persona Switcher, Topbar Jira ticket
│   ├── report.html             # Bảng điều khiển Báo cáo Hiệu Quả Nguồn Lead & Chiến Dịch (Core View)
│   ├── campaigns.html          # Quản lý tiến độ ngân sách và hiệu quả từng chiến dịch
│   └── leads_list.html         # Danh sách dữ liệu lead chi tiết (Drill-down theo nguồn/chiến dịch)
└── tests/
    ├── __init__.py
    ├── test_ac1_source_campaign_metrics.py # Unit Test Tiêu chí 1: Số lead, tỷ lệ nhận, tỷ lệ cơ hội
    ├── test_ac2_date_range_filter.py       # Unit Test Tiêu chí 2: Lọc theo khoảng thời gian
    ├── test_ac3_excel_export.py             # Unit Test Tiêu chí 3: Xuất file Excel .xlsx hợp lệ 3 sheets
    └── test_web_routes.py                   # Integration Test toàn bộ Web Routes & API
```

---

## 🚀 3. HƯỚNG DẪN KHỞI CHẠY TRÊN WINDOWS

### Cách 1: Khởi chạy 1-Click bằng file `run.bat` (Khuyên dùng)
1. Mở File Explorer và điều hướng tới thư mục:
   ```text
   C:\Users\FPT SHOP\.gemini\antigravity-ide\scratch\scrum_99
   ```
2. Nhấp đúp chuột vào file **`run.bat`**.
3. Ứng dụng sẽ tự động mở trình duyệt tại: **http://127.0.0.1:5000**

---

### Cách 2: Khởi chạy thủ công từ Terminal / VS Code
1. Mở thư mục `scrum_99` trong **Visual Studio Code**.
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

## 🧪 4. HƯỚNG DẪN KIỂM THỬ TRỰC QUAN 3 TIÊU CHÍ TRÊN GIAO DIỆN

Hệ thống cung cấp sẵn dữ liệu mẫu thực tế hơn 40+ Lead B2B rải đều theo các mốc thời gian:

### 1. Kiểm thử Tiêu chí 1 (Số lead, Tỷ lệ nhận, Tỷ lệ cơ hội & Khuyến nghị dồn ngân sách)
1. Truy cập trang chủ **[http://127.0.0.1:5000](http://127.0.0.1:5000)**.
2. Kiểm tra **Bảng 1 (Báo Cáo Hiệu Quả Theo Từng Nguồn Lead)**:
   - Hiển thị đầy đủ 7 nguồn: *Google Ads*, *Sự kiện Tech Expo*, *Đối tác giới thiệu*, *Facebook Ads*, *Website Organic*, *Email Marketing*, *TikTok Ads*.
   - Đầy đủ các cột: *Số lead*, *Lead Sales đã nhận*, *Tỷ lệ được nhận (%)*, *Chuyển đổi thành cơ hội*, *Tỷ lệ ra cơ hội (%)*, *Deal Won*, *Doanh thu thực tế*, *ROAS*.
   - Khối **"💡 KHUYẾN NGHỊ PHÂN BỔ NGÂN SÁCH"** nêu rõ: Khuyên dồn ngân sách vào **Google Ads** và **Sự kiện Tech Expo** vì mang lại doanh thu thực tế vượt trội (chiếm hơn 75% tổng doanh thu), đồng thời khuyên cắt giảm **TikTok Ads** (tỷ lệ ra cơ hội thấp, không ra doanh thu B2B).
3. Kiểm tra **Bảng 2 (Báo Cáo Theo Chiến Dịch Marketing)**:
   - Đầy đủ các chỉ số CPL (Giá mỗi lead), CPO (Giá mỗi cơ hội) và ROAS của từng chiến dịch.

---

### 2. Kiểm thử Tiêu chí 2 (Lọc theo khoảng thời gian)
1. Trên thanh công cụ lọc thời gian, nhấp lần lượt các nút:
   - **7 Ngày Qua**: Bảng số liệu tự động co gọn lại, chỉ tính các lead phát sinh trong 7 ngày gần nhất.
   - **30 Ngày Qua**: Số lượng lead và doanh thu mở rộng tương ứng.
   - **Tháng Này** / **Quý Này**.
2. Thử nghiệm **Lọc tùy chọn (Custom)**:
   - Nhập: Từ ngày `2026-02-01` đến `2026-02-28`.
   - Bấm **"Lọc"**: Báo cáo phản ánh chính xác dữ liệu của tháng 2/2026.

---

### 3. Kiểm thử Tiêu chí 3 (Xuất Excel)
1. Bấm nút **"📥 Xuất Báo Cáo Excel (.xlsx)"** ở góc phải trên cùng.
2. Trình duyệt tự động tải xuống file: `Bao_Cao_Hieu_Qua_Nguon_Lead_SCRUM-99_YYYYMMDD_HHMMSS.xlsx`.
3. Mở file Excel:
   - **Sheet 1 (Hiệu Quả Nguồn Lead):** Bảng số liệu chuẩn, header xanh Navy, có dòng Tổng cộng, định dạng tiền VNĐ và tỷ lệ % rõ ràng.
   - **Sheet 2 (Hiệu Quả Chiến Dịch):** Phân tích chi tiết từng campaign, CPL, CPO, ROAS.
   - **Sheet 3 (Danh Sách Lead Chi Tiết):** Toàn bộ danh sách lead trong khoảng thời gian đã lọc.

---

## 🔬 5. CHẠY BỘ KIỂM THỬ TỰ ĐỘNG (AUTOMATED TEST SUITE)

Mở Terminal tại thư mục `scrum_99` và chạy lệnh:
```bash
py -m unittest discover tests
```

**Kết quả:** Toàn bộ **15/15 bài kiểm thử** vượt qua thành công:
```text
...............
----------------------------------------------------------------------
Ran 15 tests in 0.266s

OK
```
Bao gồm:
- `test_ac1_source_campaign_metrics.py`: Kiểm thử tính toán chuẩn xác số lead, tỷ lệ nhận, tỷ lệ chuyển đổi cơ hội, công thức ROAS và logic khuyến nghị dồn ngân sách.
- `test_ac2_date_range_filter.py`: Kiểm thử các mốc lọc thời gian (7 ngày, 30 ngày, tùy chọn ngày) và độ chính xác của dữ liệu được lọc.
- `test_ac3_excel_export.py`: Kiểm thử xuất file `.xlsx` bằng `openpyxl`, kiểm tra độ toàn vẹn của 3 Sheet và định dạng số liệu.
- `test_web_routes.py`: Kiểm thử tích hợp toàn bộ các trang web, endpoint tải Excel và REST APIs.
