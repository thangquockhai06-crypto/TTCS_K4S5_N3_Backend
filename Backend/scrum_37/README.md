# HỆ THỐNG QUẢN LÝ NHIỀU PHIÊN BẢN BÁO GIÁ (AUTOLEAD CRM CPQ)

> **Mã Nhiệm Vụ (Jira Ticket):** `⚡ SCRUM-35 / ☑ SCRUM-37`  
> **Subtasks liên kết:**  
> • `SCRUM-234`: Frontend (Giao diện Quản lý phiên bản, So sánh Side-by-side & Kích hoạt hiệu lực)  
> • `SCRUM-235`: Backend (Động cơ Phiên bản hóa, Diff Engine, Ràng buộc 1 phiên bản hiệu lực & Audit Snapshot)  
> **User Story:** *"Là Nhân viên kinh doanh, tôi muốn quản lý nhiều phiên bản của một báo giá, để biết chính xác đã cam kết gì với khách ở lần gửi trước."*  
> **Ngôn ngữ phát triển:** Python 3 (Flask Framework) + HTML5/CSS3/Vanilla JavaScript  
> **Môi trường vận hành:** Visual Studio Code / Terminal trên hệ điều hành Windows  

---

## 🎯 1. BẢNG ĐỐI CHIẾU TIÊU CHÍ CHẤP NHẬN (ACCEPTANCE CRITERIA)

Dự án được triển khai và kiểm thử tự động đạt chuẩn **100% từng tiêu chí trong hình ảnh đề bài (Ticket SCRUM-37)**:

| Tiêu Chí Trong Đề Bài | Yêu Cầu Của Đề Bài | Cách Hệ Thống Python Đáp Ứng & Triển Khai |
| :--- | :--- | :--- |
| **Tiêu đề User Story** | *Là Nhân viên kinh doanh, tôi muốn quản lý nhiều phiên bản của một báo giá, để biết chính xác đã cam kết gì với khách ở lần gửi trước.* | • Xây dựng **Cây phiên bản báo giá (Quotation Version Tree)** gắn liền với từng họ báo giá (`quote_code`).<br>• Cho phép NVKD truy cập xem lại bất kỳ phiên bản lịch sử nào (`v1.0`, `v2.0`, `v3.0`...) để nắm rõ toàn bộ cam kết về dòng sản phẩm, đơn giá, chiết khấu dòng, điều khoản thanh toán & giao hàng mà mình đã gửi cho khách trước đó. |
| **Tiêu chí 1 (Description)** | *Mỗi lần sửa sau khi đã gửi sẽ tạo phiên bản mới, phiên bản cũ được giữ nguyên* | • **Quy tắc bất biến (Immutability Rule):** Khi báo giá đã ở trạng thái đã gửi (`is_sent = True`), mọi thao tác chỉnh sửa qua hàm `edit_quote()` **bị chặn việc ghi đè trực tiếp**.<br>• **Tự động sinh phiên bản mới:** Hệ thống tự động tạo một phiên bản kế tiếp `v{next}.0` (ví dụ: `v1` -> `v2`), kế thừa dữ liệu sửa đổi mới, gắn `parent_version_id` và bắt buộc nhập lý do thay đổi (`revision_reason`).<br>• **Bảo lưu phiên bản cũ 100%:** Phiên bản cũ được khóa đóng băng vĩnh viễn (`is_locked = True`) kèm mã băm toàn vẹn **SHA-256** (`integrity_hash`). Dữ liệu cũ được giữ nguyên vẹn tuyệt đối.<br>• Nếu là bản nháp chưa gửi (`is_sent = False`), cho phép sửa trực tiếp tại chỗ. |
| **Tiêu chí 2 (Description)** | *So sánh cạnh nhau hai phiên bản để thấy đã thay đổi gì* | • Xây dựng **Động cơ đối chiếu Side-by-side (Side-by-side Diff Engine)** trong `database.py` và giao diện chuyên dụng `/quotes/<code>/compare`.<br>• Cho phép chọn bất kỳ 2 phiên bản (Bản gốc A vs Bản mới B):<br>1. **Phân loại dòng sản phẩm rõ ràng:**<br>&nbsp;&nbsp;➕ **Thêm mới (ADDED):** Sản phẩm có ở B mà không có ở A (Highlight xanh lá).<br>&nbsp;&nbsp;❌ **Đã xóa (REMOVED):** Sản phẩm có ở A mà bị bỏ ở B (Highlight đỏ gạch ngang).<br>&nbsp;&nbsp;✏️ **Điều chỉnh (MODIFIED):** Thay đổi số lượng, đơn giá, chiết khấu % (Highlight vàng hổ phách, hiển thị giá trị cũ ➔ mới).<br>&nbsp;&nbsp;✓ **Giữ nguyên (UNCHANGED):** Không thay đổi.<br>2. **Thống kê biến động tài chính (Financial Delta):** Tính toán độ lệch số tiền và % tăng/giảm của Subtotal, Tổng chiết khấu và Tổng thanh toán cuối cùng (Grand Total).<br>3. **So sánh điều khoản thương mại:** Đối chiếu thời hạn hiệu lực, thanh toán, giao hàng, ghi chú. |
| **Tiêu chí 3 (Description)** | *Chỉ một phiên bản ở trạng thái đang hiệu lực tại một thời điểm* | • Thiết lập thuộc tính `is_effective: bool` đại diện cho giá trị cam kết pháp lý/thương mại hiện hành của báo giá.<br>• **Ràng buộc duy nhất:** Khi một phiên bản mới được gửi cho khách (`send_quote_to_customer()`) hoặc khi người dùng kích hoạt thủ công (`set_effective_version()`):<br>&nbsp;&nbsp;1. Phiên bản được chọn chuyển sang `is_effective = True`.<br>&nbsp;&nbsp;2. Toàn bộ các phiên bản còn lại của cùng mã báo giá tự động chuyển sang `is_effective = False` (trạng thái `SUPERSEDED` hoặc `DRAFT`).<br>• **Cơ chế Invariant Verification:** Hàm `_verify_single_effective_invariant()` thực hiện kiểm tra trước và sau mọi giao dịch. Nếu phát hiện > 1 phiên bản hiệu lực, hệ thống lập tức ném ngoại lệ `AssertionError`. |

---

## 🏛️ 2. SƠ ĐỒ LUỒNG PHIÊN BẢN HÓA & HIỆU LỰC (MERMAID)

```mermaid
flowchart TD
    Start([NVKD Tạo Báo Giá v1]) --> IsSentInit{Gửi cho khách ngay?}
    IsSentInit -- "Có" --> SendV1[Gửi khách: is_sent = True\nKhóa Snapshot SHA-256\n🌟 is_effective = True]
    IsSentInit -- "Chưa" --> DraftV1[Lưu nháp: is_sent = False\nis_effective = False]

    SendV1 --> CustomerFeedback[Khách hàng nhận báo giá v1\nKhách phản hồi đàm phán lại giá/hàng]
    DraftV1 --> EditDraft[Chỉnh sửa khi còn là nháp]
    EditDraft --> UpdateInPlace[Cập nhật trực tiếp lên bản v1\nKhông sinh phiên bản mới]

    CustomerFeedback --> NVKD_Edit[NVKD bấm 'Sửa Báo Giá' sau khi đã gửi]
    NVKD_Edit --> CheckSent{Kiểm tra is_sent?}
    
    CheckSent -- "Đã gửi (is_sent = True)" --> AutoNewVer[⚡ ĐÁP ỨNG TIÊU CHÍ 1:\n1. Bảo lưu v1 nguyên vẹn 100% kèm mã SHA-256\n2. Tự động sinh phiên bản mới v2\n3. Trạng thái v2: DRAFT, is_effective = False]

    AutoNewVer --> Compare[🔍 ĐÁP ỨNG TIÊU CHÍ 2: So sánh cạnh nhau Side-by-side\n• Thêm mới ➕, Xóa ❌, Sửa ✏️, Giữ nguyên ✓\n• Chênh lệch tài chính: Delta tiền và %]
    
    Compare --> ActionDecision{Quyết định của NVKD}
    ActionDecision -- "Gửi phiên bản v2 cho khách" --> SendV2[📤 Gửi v2 cho khách hàng]
    
    SendV2 --> InvariantRule[🌟 ĐÁP ỨNG TIÊU CHÍ 3:\n• v2: is_effective = True (Bản hiệu lực DUY NHẤT)\n• v1: is_effective = False, trạng thái SUPERSEDED]
    
    InvariantRule --> VerifyInvariant{Kiểm tra Invariant:\nSố bản hiệu lực == 1?}
    VerifyInvariant -- "Đạt ✓" --> Completed([Hoàn tất - Cam kết minh bạch an toàn])
    VerifyInvariant -- "Lỗi > 1" --> AlertException([Báo động vi phạm Invariant])
```

---

## 📂 3. CẤU TRÚC THƯ MỤC DỰ ÁN

```text
scrum_37/
├── app.py                      # Flask Web Server, Web Routes, Template Filters & REST APIs
├── config.py                   # Cấu hình Jira Ticket SCRUM-37, Subtasks FE/BE, Danh mục sản phẩm & Trạng thái
├── database.py                 # Động cơ Phiên bản hóa, Diff Engine Side-by-side, Khóa SHA-256 & Bất biến AC3
├── requirements.txt            # Thư viện phụ thuộc (Flask >= 3.0.0)
├── run.bat                     # File 1-click khởi chạy ứng dụng tự động trên Windows (Port 5003)
├── README.md                   # Báo cáo kỹ thuật & Hướng dẫn sử dụng chi tiết
├── static/
│   ├── css/
│   │   └── style.css           # Giao diện Glassmorphism cao cấp, Bảng Side-by-side diff & Badges hiệu lực
│   └── js/
│       └── main.js             # Live tính toán chiết khấu, Chuyển đổi hiệu lực AJAX, So sánh diff & Simulator
├── templates/
│   ├── base.html               # Layout chuẩn Jira ticket SCRUM-37, Topbar, Banner 3 tiêu chí
│   ├── dashboard.html          # Bàn làm việc NVKD, KPI phiên bản, cây phiên bản & nhật ký kiểm toán
│   ├── quotes_list.html        # Danh sách tất cả báo giá kèm bộ lọc theo trạng thái bản hiệu lực
│   ├── quote_detail.html       # Chi tiết báo giá, xem cam kết từng version, tab timeline & khóa SHA-256
│   ├── quote_compare.html      # Màn hình so sánh cạnh nhau 2 phiên bản side-by-side (Tiêu chí 2)
│   ├── quote_create.html       # Form soạn báo giá mới khởi tạo v1.0
│   ├── quote_edit.html         # Form chỉnh sửa thông minh (Cảnh báo Tiêu chí 1: tự sinh v mới khi đã gửi)
│   └── simulator.html          # Trình mô phỏng & chạy kiểm thử tự động 3 tiêu chí trong 1-click
└── tests/
    ├── __init__.py
    ├── test_ac1_immutable_versioning.py     # Unit Test Tiêu chí 1: Tạo v mới sau khi gửi, v cũ giữ nguyên
    ├── test_ac2_side_by_side_diff.py        # Unit Test Tiêu chí 2: So sánh Side-by-side dòng SP & tài chính
    ├── test_ac3_single_effective_version.py # Unit Test Tiêu chí 3: Ràng buộc duy nhất 1 bản hiệu lực
    └── test_web_routes.py                   # Unit Test toàn diện Web routes và REST API endpoints
```

---

## 🚀 4. HƯỚNG DẪN CÀI ĐẶT & KHỞI CHẠY (WINDOWS)

### Cách 1: Khởi chạy 1-Click (Khuyên dùng trên Windows)
Nhấp đúp chuột vào file:
```cmd
run.bat
```
File này sẽ tự động:
1. Kiểm tra môi trường Python trên máy.
2. Tự động mở trình duyệt web tại địa chỉ: `http://127.0.0.1:5003`.
3. Khởi chạy máy chủ Flask Web Server.

### Cách 2: Khởi chạy thủ công từ Terminal / PowerShell
```powershell
cd "c:\Users\FPT SHOP\.gemini\antigravity-ide\scratch\Backend\scrum_37"
py app.py
```
Sau đó mở trình duyệt và truy cập: `http://127.0.0.1:5003`

---

## 🧪 5. KIỂM THỬ TỰ ĐỘNG (AUTOMATED TESTING)

### 1. Chạy toàn bộ Unit Tests bằng Python unittest:
```powershell
cd "c:\Users\FPT SHOP\.gemini\antigravity-ide\scratch\Backend\scrum_37"
py -m unittest discover -s tests -v
```
**Kết quả thực tế:**
- `test_ac1_immutable_versioning`: Đạt 100% (Xác minh tạo v2 khi sửa bản đã gửi, v1 giữ nguyên vẹn mã SHA-256).
- `test_ac2_side_by_side_diff`: Đạt 100% (Xác minh phát hiện đúng Added, Removed, Modified, Unchanged & Delta tiền).
- `test_ac3_single_effective_version`: Đạt 100% (Xác minh chỉ duy nhất 1 phiên bản hiệu lực, kiểm tra bảo vệ bất biến).
- `test_web_routes`: Đạt 100% (Xác minh toàn bộ các trang Web và REST API).

### 2. Kiểm thử trực quan trên Giao diện Web (Simulator):
Truy cập đường dẫn: `http://127.0.0.1:5003/simulator`  
Bấm nút **"▶️ Chạy Bộ Kiểm Thử (1-Click Run)"** để theo dõi hệ thống thực thi từng bước trực tiếp trên trình duyệt.
