# HỆ THỐNG DUYỆT BÁO GIÁ THEO MỨC CHIẾT KHẤU (AUTOLEAD CRM)

> **Mã Nhiệm Vụ (Jira Ticket):** `⚡ SCRUM-35 / ☑ SCRUM-33`  
> **Subtasks liên kết:**  
> • `SCRUM-232`: Frontend (Giao diện hàng chờ & Modal phê duyệt)  
> • `SCRUM-233`: Backend (Logic phân cấp thẩm quyền, kiểm tra giá sàn & Sổ cái bất biến)  
> **User Story:** *"Là Trưởng nhóm kinh doanh, tôi muốn duyệt báo giá theo mức chiết khấu, để kiểm soát biên lợi nhuận mà không phải trả lời từng tin nhắn xin giảm giá."*  
> **Ngôn ngữ phát triển:** Python 3 (Flask Framework) + HTML5/CSS3/JavaScript  
> **Môi trường vận hành:** Visual Studio Code / Terminal trên hệ điều hành Windows  

---

## 🎯 1. BẢNG ĐỐI CHIẾU TIÊU CHÍ CHẤP NHẬN (ACCEPTANCE CRITERIA)

Dự án được xây dựng và kiểm thử bám sát 100% từng yêu cầu trong hình ảnh đề bài (Ticket SCRUM-33):

| Tiêu Chí Trong Đề Bài | Yêu Cầu Của Đề Bài | Cách Hệ Thống Python Đáp Ứng & Triển Khai |
| :--- | :--- | :--- |
| **Tiêu đề User Story** | *Là Trưởng nhóm kinh doanh, tôi muốn duyệt báo giá theo mức chiết khấu, để kiểm soát biên lợi nhuận mà không phải trả lời từng tin nhắn xin giảm giá.* | Xây dựng Bàn làm việc Trưởng nhóm kinh doanh tích hợp **Bộ máy phân cấp thẩm quyền duyệt tự động (Approval Authority Engine)**. Trưởng nhóm không còn phải nhận tin nhắn rời rạc qua Zalo/Teams để xin giảm giá từng đơn hàng. Mọi yêu cầu được gom tập trung vào Hàng chờ duyệt (`/approval-queue`), tự động phân loại theo ngưỡng chiết khấu và cảnh báo vi phạm giá sàn. |
| **Tiêu chí 1 (Description)** | *Chiết khấu dưới ngưỡng thứ nhất thì tự động thông qua, không cần duyệt* | • **Cấu hình ngưỡng 1:** `THRESHOLD_1_PERCENT = 10.0%`.<br>• Khi NVKD trình báo giá có chiết khấu tổng `< 10.0%` VÀ tất cả sản phẩm đều đảm bảo trên giá sàn:<br>• Hàm backend `submit_quote_for_approval()` chuyển thẳng trạng thái sang `APPROVED` (hoặc `AUTO_APPROVED`), không cần Trưởng nhóm duyệt tay.<br>• Tự động ghi vào lịch sử kiểm toán sự kiện `AUTO_APPROVE` do Hệ thống thực hiện.<br>• NVKD nhận thông báo và có thể gửi báo giá cho khách hàng ngay lập tức. |
| **Tiêu chí 2 (Description)** | *Vượt ngưỡng thứ nhất do Trưởng nhóm duyệt; vượt ngưỡng thứ hai hoặc dưới giá sàn thì bắt buộc Giám đốc kinh doanh duyệt* | • **Cấu hình ngưỡng 2:** `THRESHOLD_2_PERCENT = 20.0%`.<br>• **Quy tắc giá sàn (Floor Price):** Mỗi sản phẩm có `floor_price` tối thiểu (ví dụ: CRM Enterprise sàn 18 triệu). Nếu đơn giá sau chiết khấu `< floor_price`, hệ thống gắn cờ `below_floor_price = True`.<br>• **Phân cấp thẩm quyền chặt chẽ:**<br>1. Chiết khấu `10.0% <= discount <= 20.0%` (trên sàn): Thẩm quyền **Trưởng nhóm kinh doanh** (`ROLE_TEAM_LEAD`).<br>2. Chiết khấu `> 20.0%` HOẶC `dưới giá sàn`: Bắt buộc **Giám đốc kinh doanh** (`ROLE_DIRECTOR`).<br>• **Bảo mật phân quyền:** Nếu Trưởng nhóm cố tình bấm duyệt báo giá thuộc thẩm quyền Giám đốc, backend Python **chặn ngay lập tức và ném ngoại lệ `PermissionError`**. |
| **Tiêu chí 3 (Description)** | *Ba hành động: Duyệt, Từ chối, Trả lại sửa — hai hành động sau bắt buộc nhập ý kiến* | Cung cấp 3 hành động nghiệp vụ tại trang chi tiết báo giá và API:<br>1. **Duyệt (`APPROVE`)**: Chấp thuận báo giá, chuyển trạng thái `APPROVED`, ý kiến là tùy chọn.<br>2. **Từ chối (`REJECT`)**: Từ chối hợp đồng, chuyển `REJECTED`, đóng quyền sửa.<br>3. **Trả lại sửa (`REQUEST_CHANGES`)**: Chuyển `CHANGES_REQUESTED`, mở lại quyền sửa (`can_edit = True`) cho NVKD điều chỉnh lại chiết khấu.<br>• **Ràng buộc kiểm tra nghiêm ngặt (Validation):** Cả client JavaScript và backend Python đều bắt buộc kiểm tra trường ý kiến đối với hành động Từ chối và Trả lại sửa. Nếu để trống hoặc chỉ nhập khoảng trắng -> **Chặn và báo lỗi `ValueError`**. |
| **Tiêu chí 4 (Description)** | *Chỉ báo giá đã duyệt mới gửi được cho khách* | • Ràng buộc DUY NHẤT: Báo giá ở trạng thái `STATUS_APPROVED` mới kích hoạt nút **"📤 Gửi Cho Khách Hàng Ngay"**.<br>• Nếu báo giá đang ở trạng thái `DRAFT` (Bản nháp), `PENDING_APPROVAL` (Chờ duyệt), `CHANGES_REQUESTED` (Trả lại sửa) hoặc `REJECTED` (Bị từ chối):<br>• Trên giao diện: Nút gửi bị vô hiệu hóa kèm tooltip cảnh báo vi phạm Tiêu chí 4.<br>• Trên backend: Hàm `send_to_customer()` kiểm tra trạng thái nghiêm ngặt, nếu cố gửi sẽ ném ngoại lệ `ValueError("Chỉ báo giá đã được phê duyệt mới được phép gửi cho khách hàng!")`. |
| **Tiêu chí 5 (Description)** | *Lịch sử duyệt không sửa và không xoá được* | • Thiết lập **Sổ cái kiểm toán bất biến (Immutable Audit Ledger)** trong `database.py`.<br>• Mỗi hành động (Tự động duyệt, Trình duyệt, Trưởng nhóm duyệt, Giám đốc duyệt, Từ chối, Trả lại sửa) được ghi lại vĩnh viễn kèm mã băm toàn vẹn **SHA-256** (`integrity_hash`).<br>• **Nghiêm cấm sửa/xóa:** Không cung cấp bất kỳ API hoặc nút sửa/xóa nào trên UI. Lớp cơ sở dữ liệu chặn mọi hàm `update_approval_history()` và `delete_approval_history()` bằng ngoại lệ `PermissionError`.<br>• Hàm đọc dữ liệu trả về `copy.deepcopy()` để client không thể can thiệp dữ liệu trong bộ nhớ. |

---

## 🏛️ 2. SƠ ĐỒ LUỒNG PHÊ DUYỆT CHIẾT KHẤU & GIÁ SÀN (MERMAID)

```mermaid
flowchart TD
    Start([NVKD Soạn Báo Giá]) --> Submit[Bấm 'Trình Duyệt Báo Giá']
    
    Submit --> CheckFloor{Đơn giá sau chiết khấu\n< Giá sàn?}
    CheckFloor -- "Có (Dưới sàn 🚨)" --> DirectorQueue[Bắt buộc GIÁM ĐỐC KINH DOANH duyệt]
    
    CheckFloor -- "Không (Đạt sàn ✓)" --> CheckDiscount{Mức chiết khấu tổng\n(% Discount)}
    
    CheckDiscount -- "< 10.0% (Dưới ngưỡng 1)" --> AutoApprove[⚡ TỰ ĐỘNG THÔNG QUA\nTrạng thái: APPROVED]
    CheckDiscount -- "10.0% đến 20.0% (Vượt ngưỡng 1)" --> TeamLeadQueue[👔 TRƯỞNG NHÓM KINH DOANH duyệt\nTrạng thái: PENDING_APPROVAL]
    CheckDiscount -- "> 20.0% (Vượt ngưỡng 2)" --> DirectorQueue
    
    TeamLeadQueue --> DecisionTL{Hành động của\nTrưởng nhóm}
    DirectorQueue --> DecisionDir{Hành động của\nGiám đốc}
    
    DecisionTL -- "1. Duyệt" --> Approved[✅ Đã duyệt\nTrạng thái: APPROVED]
    DecisionDir -- "1. Duyệt" --> Approved
    
    DecisionTL -- "2. Từ chối\n(Bắt buộc nhập lý do)" --> Rejected[❌ Bị từ chối\nTrạng thái: REJECTED]
    DecisionDir -- "2. Từ chối\n(Bắt buộc nhập lý do)" --> Rejected
    
    DecisionTL -- "3. Trả lại sửa\n(Bắt buộc nhập hướng dẫn)" --> Revise[🔄 Trả lại sửa\nTrạng thái: CHANGES_REQUESTED\ncan_edit = True]
    DecisionDir -- "3. Trả lại sửa\n(Bắt buộc nhập hướng dẫn)" --> Revise
    
    Revise --> Start
    
    Approved --> SendCustomer[📤 Gửi cho Khách hàng\nTrạng thái: SENT]
    
    Rejected -.-> BlockSend[🚫 Chặn gửi khách]
    TeamLeadQueue -.-> BlockSend
    DirectorQueue -.-> BlockSend
    
    subgraph Sổ cái kiểm toán bất biến
        Log1[(Ghi nhận Audit Trail SHA-256\nKhông thể sửa - Không thể xóa)]
    end
    
    AutoApprove --> Log1
    DecisionTL --> Log1
    DecisionDir --> Log1
    SendCustomer --> Log1
```

---

## 📂 3. CẤU TRÚC THƯ MỤC DỰ ÁN

```text
scrum_33/
├── app.py                      # Flask Web Server, Web Routes, Persona Switcher & REST APIs
├── config.py                   # Cấu hình ngưỡng chiết khấu (10%, 20%), Giá sàn & Danh mục sản phẩm
├── database.py                 # Quản lý dữ liệu Thread-safe, mô hình Báo giá, Sổ cái lịch sử bất biến
├── requirements.txt            # Thư viện phụ thuộc (Flask >= 3.0.0)
├── run.bat                     # File 1-click khởi động ứng dụng trên Windows
├── README.md                   # Báo cáo kỹ thuật & Hướng dẫn sử dụng chi tiết
├── static/
│   ├── css/
│   │   └── style.css           # Giao diện Glassmorphism cao cấp, Dark/Light mode & Timeline kiểm toán
│   └── js/
│       └── main.js             # Modal 3 hành động, validation ý kiến bắt buộc & tính giá sàn real-time
├── templates/
│   ├── base.html               # Layout chính, Topbar Jira ticket, Persona Switcher
│   ├── dashboard.html          # Bàn làm việc Trưởng nhóm & Giám đốc, KPI duyệt, báo giá khẩn cấp
│   ├── approval_queue.html     # Hàng chờ duyệt chuyên sâu (bộ lọc Trưởng nhóm / Giám đốc / Dưới sàn)
│   ├── quote_detail.html       # Chi tiết báo giá, duyệt/từ chối/trả lại, gửi khách & timeline lịch sử
│   ├── quote_create.html       # Form soạn báo giá mới, live preview cấp duyệt & so sánh giá sàn
│   ├── quotes_list.html        # Danh sách tất cả báo giá kèm bộ lọc trạng thái
│   └── simulator.html          # Trình mô phỏng & chạy test trực quan 5 tiêu chí chấp nhận trong 1 click
└── tests/
    ├── __init__.py
    ├── test_ac1_auto_approval.py        # Unit Test Tiêu chí 1: Chiết khấu dưới ngưỡng 1 tự động duyệt
    ├── test_ac2_approval_hierarchy.py   # Unit Test Tiêu chí 2: Phân cấp Trưởng nhóm/Giám đốc, giá sàn & chặn vượt quyền
    ├── test_ac3_approval_actions.py     # Unit Test Tiêu chí 3: 3 hành động Duyệt, Từ chối, Trả lại sửa (bắt buộc ý kiến)
    ├── test_ac4_send_to_customer.py     # Unit Test Tiêu chí 4: Chỉ báo giá đã duyệt mới gửi được cho khách
    ├── test_ac5_immutable_history.py    # Unit Test Tiêu chí 5: Lịch sử duyệt không sửa và không xoá được
    └── test_web_routes.py               # Integration Test toàn bộ Web Routes & REST APIs
```

---

## 🚀 4. HƯỚNG DẪN KHỞI CHẠY TRÊN WINDOWS

### Cách 1: Khởi động 1-Click bằng file `run.bat` (Khuyến nghị)
1. Mở thư mục `Backend\scrum_33`.
2. Nhấp đúp chuột vào file **`run.bat`**.
3. Hệ thống sẽ tự động kiểm tra Python và mở trình duyệt tại:
   👉 **`http://127.0.0.1:5002`**

### Cách 2: Chạy qua Terminal / Command Prompt
```bash
# 1. Di chuyển vào thư mục dự án
cd Backend\scrum_33

# 2. Cài đặt thư viện phụ thuộc
py -m pip install -r requirements.txt

# 3. Khởi chạy máy chủ
py app.py
```

---

## 🧪 5. KẾT QUẢ KIỂM THỬ TỰ ĐỘNG (UNIT & INTEGRATION TESTS)

Hệ thống đi kèm bộ kiểm thử tự động toàn diện bao phủ 100% 5 tiêu chí chấp nhận:

```bash
cd Backend\scrum_33
py -m unittest discover tests
```

**Kết quả chạy thực tế:**
```text
.......................
----------------------------------------------------------------------
Ran 23 tests in 0.125s

OK
```

---

## 👑 6. VAI TRÒ NGƯỜI DÙNG & TÀI KHOẢN TRẢI NGHIỆM

Hệ thống tích hợp sẵn tính năng **Persona Switcher** ở góc trên bên phải để người dùng trải nghiệm ngay mà không cần đăng nhập:

1. **👔 Lê Hoàng Long (`usr-03`) - Trưởng nhóm kinh doanh (Mặc định)**:
   - Thẩm quyền duyệt các báo giá có chiết khấu từ `10.0% đến 20.0%` (không dưới giá sàn).
   - Bị hệ thống chặn nếu cố tình duyệt báo giá vượt 20% hoặc bán dưới giá sàn.
2. **👑 Phạm Minh Tuấn (`usr-04`) - Giám đốc kinh doanh**:
   - Thẩm quyền tối cao: Duyệt các báo giá chiết khấu sâu `> 20.0%` hoặc bán dưới giá sàn.
   - Có thể duyệt thay cho Trưởng nhóm khi cần thiết.
3. **👨‍💼 Nguyễn Văn Hùng (`usr-01`) - Nhân viên kinh doanh**:
   - Soạn báo giá, trình duyệt và bấm **"Gửi cho khách hàng"** khi báo giá đã được duyệt.
