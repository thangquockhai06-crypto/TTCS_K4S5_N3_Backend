# HỆ THỐNG KHAI BÁO CƠ CẤU TỔ CHỨC KINH DOANH & PHẠM VI DỮ LIỆU

> **Mã Nhiệm Vụ:** `⚡ SCRUM-83 / ☑ SCRUM-85`  
> **Ngôn ngữ thực hiện:** Python 3 (Flask Framework) + Modern Responsive HTML5 / CSS3 / Vanilla JS  
> **Môi trường chạy:** Visual Studio Code trên hệ điều hành Windows  
> **Tiêu chuẩn:** Tuân thủ 100% Tiêu chí chấp nhận (Acceptance Criteria) của User Story  

---

## 🎯 1. BẢNG ĐỐI CHIẾU TIÊU CHÍ CHẤP NHẬN (ACCEPTANCE CRITERIA)

Dự án được xây dựng và giải quyết trọn vẹn 100% nội dung yêu cầu trong ticket **SCRUM-85**:

| Tiêu Chí Trong Ticket SCRUM-85 | Yêu Cầu Đề Bài | Cách Hệ Thống Python & Giao Diện Đáp Ứng |
| :--- | :--- | :--- |
| **Tiêu đề User Story** | *Là Giám đốc kinh doanh, tôi muốn khai báo cơ cấu tổ chức kinh doanh, để phạm vi dữ liệu của trưởng nhóm bám đúng cây tổ chức thật.* | • Giao diện cho phép Giám đốc khai báo, phân cấp cây tổ chức đa tầng.<br>• Tích hợp **Phòng thử nghiệm phạm vi dữ liệu (Testing Lab)** với thanh chuyển đổi góc nhìn tức thì để kiểm chứng trực tiếp phạm vi nhìn thấy của Giám đốc, Trưởng nhánh cấp 1, Trưởng đội cấp 2 và Chuyên viên. |
| **Tiêu chí 1 (Description)** | *Nhóm kinh doanh có cấu trúc cây, mỗi nhóm có một trưởng nhóm* | • Các nhóm kinh doanh được thiết lập theo mô hình quan hệ cha-con (`parent_id`), tạo thành cây phân cấp vững chắc (`root -> children -> grandchildren`).<br>• Mỗi nhóm có **duy nhất một Trưởng nhóm** (`leader_id`) được chỉ định từ danh sách nhân sự.<br>• **Thuật toán ngăn chặn vòng lặp cây (Circular Dependency Prevention):** Tuyệt đối không cho phép gán một nhóm hoặc bất kỳ con cháu nào của nó làm nhóm cha của chính nó. |
| **Tiêu chí 2 (Description)** | *Mỗi nhân viên thuộc đúng một nhóm tại một thời điểm* | • Mỗi nhân viên trong cơ sở dữ liệu có thuộc tính `team_id` duy nhất.<br>• Khi điều chuyển nhân viên sang nhóm mới (`assign_employee_to_team`), hệ thống tự động gỡ nhân viên khỏi nhóm cũ và chỉ thuộc về nhóm mới duy nhất.<br>• Giao diện có module và modal **Điều chuyển nhóm nhanh** hiển thị rõ nhóm cũ và nhóm mới tiếp nhận. |
| **Tiêu chí 3 (Description)** | *Cây tổ chức này quyết định phạm vi dữ liệu mà Trưởng nhóm nhìn thấy* | • Áp dụng thuật toán **Duyệt cây con (Subtree Traversal)**: Trưởng nhóm $T$ nhìn thấy toàn bộ cơ hội bán hàng, hợp đồng và khách hàng thuộc nhóm $T$ và tất cả các nhóm con cháu cấp dưới trong cây.<br>• **Bảo mật phân cấp:** Trưởng nhóm cấp dưới tuyệt đối không nhìn thấy dữ liệu của nhóm anh em ngang hàng (peer teams) hay nhóm cấp trên.<br>• Giám đốc kinh doanh (node gốc) có toàn quyền nhìn thấy 100% dữ liệu toàn quốc.<br>• Nhân viên thường chỉ nhìn thấy dữ liệu do chính mình phụ trách. |
| **Tiêu chí 4 (Description)** | *Khai báo khu vực địa lý và gán khu vực cho nhóm* | • Xây dựng module quản lý danh mục Khu vực địa lý (Regions/Territories) với Mã, Tên, Mã viết tắt, Tỉnh/thành trực thuộc, và Màu sắc nhận diện.<br>• Cho phép gán khu vực địa lý cho từng nhóm kinh doanh khi tạo hoặc chỉnh sửa nhóm.<br>• Hiển thị huy hiệu khu vực địa lý trên sơ đồ cây tổ chức và thống kê doanh số theo vùng. |

---

## 🏗️ 2. CẤU TRÚC THƯ MỤC DỰ ÁN

```text
scrum_85/
├── app.py                      # Flask Server: Routes, kiểm tra phạm vi dữ liệu, chuyển góc nhìn, action handlers
├── database.py                 # Module dữ liệu: Cây tổ chức, ngăn chu trình, duyệt subtree, ràng buộc 1 NV 1 nhóm
├── run.bat                     # File kích hoạt chạy nhanh 1-click trên hệ điều hành Windows
├── README.md                   # Tài liệu thuyết minh chi tiết và đối chiếu tiêu chí đề bài
├── static/
│   ├── css/
│   │   └── style.css           # Toàn bộ CSS giao diện: Sơ đồ cây phân cấp, Ma trận data scope, Dark testing bar
│   └── js/
│       └── main.js             # Xử lý đóng mở Modal, điều chuyển nhân sự, khai báo nhóm con nhanh
├── templates/
│   ├── base.html               # Master Layout: Testing Bar đổi vai trò tức thì, Header điều hướng, Flash alerts
│   ├── org_tree.html           # Sơ đồ Cây Tổ Chức Trực Quan (Interactive Tree) + Modal thêm/sửa nhóm
│   ├── data_scope.html         # Màn hình Khám Phá Phạm Vi Dữ Liệu: Ma trận In-Scope/Out-of-Scope & Deals
│   ├── employees.html          # Danh sách nhân viên & Chức năng Điều chuyển nhóm (1 NV = 1 Nhóm)
│   ├── regions.html            # Khai báo và Quản lý danh mục Khu vực địa lý
│   └── errors/
│       ├── 404.html            # Trang báo lỗi 404 Not Found đồng bộ giao diện
│       └── 500.html            # Trang báo lỗi 500 Internal Server Error đồng bộ giao diện
└── tests/
    └── test_scrum_85.py        # Bộ kiểm thử tự động 13 ca test xác minh 100% 4 Tiêu chí đề bài
```

---

## 🧠 3. THUẬT TOÁN & MÔ HÌNH DỮ LIỆU TRỌNG TÂM

### 3.1. Thuật toán Duyệt Cây con (Subtree Traversal) xác định Data Scope
```python
def get_sub_tree_team_ids(root_team_id: str) -> Set[str]:
    """
    Tìm tất cả các ID của nhóm root_team_id và toàn bộ con cháu cấp dưới bằng thuật toán BFS.
    """
    result = {root_team_id}
    queue = [root_team_id]
    while queue:
        current_id = queue.pop(0)
        for t_id, t_info in DB_TEAMS.items():
            if t_info.get("parent_id") == current_id and t_id not in result:
                result.add(t_id)
                queue.append(t_id)
    return result
```

### 3.2. Thuật toán Ngăn chặn Chu trình Lặp Cây (Circular Dependency Check)
Khi người dùng sửa nhóm cha của nhóm $A$ thành $B$:
- Nếu $B == A$: Vi phạm (chính nó làm cha của chính nó).
- Nếu duyệt ngược chuỗi tổ tiên của $B$ lên gốc mà gặp $A$: Vi phạm (vì $B$ vốn là con/cháu của $A$, việc chọn $B$ làm cha sẽ biến cây thành chu trình lặp vô hạn).
- Hệ thống phát hiện và chặn lại ngay lập tức, trả về thông báo lỗi thân thiện.

### 3.3. Ràng buộc Mỗi Nhân Viên Thuộc Đúng Một Nhóm
```python
def assign_employee_to_team(emp_id: str, new_team_id: str):
    # Cập nhật trực tiếp trường team_id duy nhất
    DB_EMPLOYEES[emp_id]["team_id"] = new_team_id
```

---

## 🚀 4. HƯỚNG DẪN CÀI ĐẶT & KHỞI CHẠY TRÊN VS CODE

### Bước 1: Mở thư mục dự án trong VS Code
1. Mở **Visual Studio Code**.
2. Chọn menu **File** -> **Open Folder...** (hoặc nhấn phím tắt `Ctrl + K, Ctrl + O`).
3. Điều hướng và chọn thư mục:
   ```text
   C:\Users\FPT SHOP\.gemini\antigravity-ide\scratch\Subtask Backend\scrum_85
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
========================================================================
 HỆ THỐNG KHAI BÁO CƠ CẤU TỔ CHỨC KINH DOANH & PHẠM VI DỮ LIỆU - SCRUM-85
 User Story: Khai báo cơ cấu tổ chức để phạm vi dữ liệu bám đúng cây tổ chức
 Tiêu chí: Cây tổ chức + Trưởng nhóm + 1 nhân viên 1 nhóm + Phạm vi dữ liệu + Khu vực
 Máy chủ đang hoạt động tại: http://127.0.0.1:5000
========================================================================
```

### Bước 5: Trải nghiệm trên trình duyệt Web
Mở trình duyệt (Chrome, Edge, Firefox) và truy cập:
👉 **`http://127.0.0.1:5000`**

---

## 🧪 5. HƯỚNG DẪN CHẠY BỘ KIỂM THỬ TỰ ĐỘNG (UNIT TESTS)

Dự án tích hợp sẵn **13 ca kiểm thử tự động** bao phủ toàn bộ 4 tiêu chí của ticket:

Chạy lệnh sau tại terminal:
```bash
py -m unittest tests/test_scrum_85.py
```

Kết quả kiểm thử đạt chuẩn 13/13 tests thành công:
```text
.............
----------------------------------------------------------------------
Ran 13 tests in 0.005s

OK
```

### Bảng chi tiết 13 ca kiểm thử:
1. `test_01_team_has_tree_structure_and_unique_leader`: Kiểm tra cấu trúc cây và mỗi nhóm có đúng 1 trưởng nhóm.
2. `test_02_prevent_circular_dependency_in_team_hierarchy`: Kiểm tra chống tạo chu trình lặp cây.
3. `test_03_create_new_subteam_successfully`: Kiểm tra thêm nhóm con trực thuộc vào cây.
4. `test_04_employee_belongs_to_exactly_one_team`: Kiểm tra mọi nhân viên chỉ thuộc đúng 1 nhóm.
5. `test_05_transferring_employee_updates_team_exclusively`: Kiểm tra khi chuyển nhóm, nhân viên tự động rời nhóm cũ.
6. `test_06_subtree_traversal_accuracy`: Kiểm tra độ chính xác của thuật toán duyệt toàn bộ cây con.
7. `test_07_sales_director_sees_all_deals_nationwide`: Giám đốc kinh doanh nhìn thấy 100% dữ liệu toàn quốc.
8. `test_08_branch_leader_sees_only_own_subtree_and_not_peer_branch`: Trưởng chi nhánh thấy dữ liệu nhóm mình và con, không thấy nhóm anh em.
9. `test_09_sub_team_leader_sees_only_own_team`: Trưởng nhóm con chỉ thấy dữ liệu đội của mình.
10. `test_10_individual_sales_rep_sees_only_assigned_deals`: Chuyên viên chỉ thấy deal do mình phụ trách.
11. `test_11_create_and_manage_geographic_regions`: Khai báo và quản lý danh mục khu vực địa lý.
12. `test_12_assign_region_to_team`: Gán khu vực địa lý cho nhóm kinh doanh.
13. `test_13_prevent_deleting_region_in_use`: Ngăn chặn xóa khu vực đang có nhóm kinh doanh phụ trách.
