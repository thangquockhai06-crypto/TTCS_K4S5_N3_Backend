# ⏱ CareTrack CRM - Ticket SCRUM-57: Dòng Thời Gian Tương Tác Khách Hàng

> **Epic cha**: `⚡ SCRUM-36`
> **Ticket**: `☑ SCRUM-57`
> **Vai trò**: **Chăm sóc khách hàng (Customer Service)**
> **Ngôn ngữ**: **Python 3** (Flask Web Application)
> **User Story**:
> *"Là Chăm sóc khách hàng, tôi muốn xem dòng thời gian tương tác đầy đủ của một khách hàng, để tiếp nhận khách từ đồng nghiệp mà nắm được bối cảnh trong năm phút."*

---

## 🎯 Tiêu chí chấp nhận

### 1. Gộp toàn bộ hoạt động, thay đổi cơ hội, báo giá đã gửi theo thứ tự thời gian
- Hàm `CRMDatabase.build_timeline()` trong [database.py](database.py) đọc **3 nguồn dữ liệu** khác nhau và chuẩn hóa về cùng một cấu trúc sự kiện:

  | Nguồn | Loại sự kiện | Nội dung hiển thị |
  | :--- | :--- | :--- |
  | Hoạt động | 📞 Cuộc gọi, ✉️ Email, 🤝 Cuộc họp, 💬 Tin nhắn Zalo/SMS, 📝 Ghi chú nội bộ | Tiêu đề, nội dung, kết quả, thời lượng, việc cần làm tiếp |
  | Thay đổi cơ hội | 📈 Thay đổi cơ hội | `Giai đoạn: Đàm phán → Thắng 🏆`, `Giá trị: 522.000.000 ₫ → 486.000.000 ₫`... |
  | Báo giá đã gửi | 🧾 Báo giá đã gửi | Mã báo giá, giá trị, gửi tới, hiệu lực, trạng thái (đã xem / chấp nhận / từ chối) |

- Sắp xếp theo `occurred_at`. Nếu hai sự kiện trùng thời điểm thì xếp tiếp theo nguồn rồi theo mã, để thứ tự luôn ổn định.
- Có 2 chế độ: **Mới nhất trước** (mặc định, hợp với việc tiếp nhận khách) và **Cũ nhất trước** (đọc lại câu chuyện từ đầu).
- Giao diện nhóm sự kiện theo ngày ("Hôm nay", "Hôm qua", "Thứ Hai, 12/10/2026"...).

### 2. Lọc theo loại hoạt động và theo người thực hiện
- **Loại hoạt động**: chọn được nhiều loại cùng lúc trong 7 loại trên. Mỗi chip có số đếm.
- **Người thực hiện**: chỉ liệt kê những người **đã từng tương tác** với khách này, kèm số sự kiện của từng người.
- Kết hợp được cả hai bộ lọc. Kết quả vẫn giữ đúng thứ tự thời gian.
- Bộ lọc nằm trên URL (`?type=CALL&type=EMAIL&performer=usr-cs2`) nên có thể gửi link cho đồng nghiệp.
- Giá trị không hợp lệ: trang web hiện cảnh báo và bỏ qua bộ lọc, còn API trả **HTTP 400**.

### ➕ Bổ sung phục vụ mục tiêu "nắm bối cảnh trong 5 phút"
Cột trái trang dòng thời gian có **"Bối cảnh trong 5 phút"** gồm:
- Tổng số sự kiện, cơ hội đang mở, việc tồn đọng, lần liên hệ gần nhất, doanh thu đã thắng.
- 📌 **Lưu ý quan trọng**: các ghi chú được ghim (ví dụ ghi chú bàn giao của đồng nghiệp).
- ✅ **Việc cần làm tiếp**: việc chưa xong, quá hạn thì đánh dấu đỏ.
- 📈 **Cơ hội đang mở** và 🧾 **Báo giá gần nhất**.
- Form **ghi nhận hoạt động** để CSKH ghi chú "đã tiếp nhận" ngay vào dòng thời gian.

---

## 🏗️ Cấu trúc dự án

```
scrum_57/
├── app.py                 # Flask: routes trang web + REST API
├── config.py              # Hằng số: loại sự kiện, nhãn, icon, vai trò, cổng 5057
├── database.py            # Dữ liệu mẫu + động cơ gộp/sắp xếp/lọc dòng thời gian + tóm tắt bàn giao
├── requirements.txt       # Flask>=3.0.0
├── run.bat                # Chạy 1-click trên Windows
├── static/
│   ├── css/style.css      # Giao diện dark glassmorphism, màu riêng cho từng loại sự kiện
│   └── js/main.js         # Tự áp dụng bộ lọc khi bấm chip (không có JS vẫn dùng được)
├── templates/
│   ├── base.html          # Layout chung + chuyển người dùng giả lập
│   ├── customers.html     # Danh sách khách hàng
│   └── timeline.html      # Trang dòng thời gian + bộ lọc + tóm tắt 5 phút
└── tests/
    ├── test_ac1_merged_timeline.py   # 12 test cho Tiêu chí 1
    ├── test_ac2_filters.py           # 15 test cho Tiêu chí 2 + tóm tắt bàn giao
    └── test_web_routes.py            # 11 test cho routes & API
```

---

## 🚀 Khởi chạy

**Cách 1:** nhấp đúp `run.bat`, trình duyệt sẽ mở `http://127.0.0.1:5057`.

**Cách 2:**
```bash
py -m pip install -r requirements.txt
py app.py
```

Gợi ý demo: mở khách **CUS-001 (Sen Vàng)**. Đây là khách đang được bàn giao từ *Ngô Minh Tâm* sang *Phạm Thu Hà*, có đủ 3 loại dữ liệu (22 sự kiện). **CUS-003** là khách mới, chưa có tương tác nào, dùng để xem trạng thái trống.

## 🔌 REST API

| Method | Endpoint | Mô tả |
| :--- | :--- | :--- |
| GET | `/api/customers?search=` | Danh sách khách hàng + thời điểm tương tác gần nhất |
| GET | `/api/customers/<id>/timeline?type=&performer=&order=asc\|desc` | Dòng thời gian đã gộp & lọc (`type`/`performer` lặp lại được hoặc phân tách bằng dấu phẩy) |
| GET | `/api/customers/<id>/summary` | Tóm tắt bàn giao |

Mã lỗi: `404` nếu không có khách hàng, `400` nếu bộ lọc hoặc thứ tự không hợp lệ.

---

## 🧪 Kiểm thử

```bash
py -m unittest discover tests
```

```
Ran 38 tests in 0.18s
OK
```
