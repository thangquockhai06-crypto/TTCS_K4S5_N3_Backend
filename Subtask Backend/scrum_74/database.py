"""
HỆ THỐNG PHÂN QUYỀN RBAC & DỮ LIỆU ĐIỀU HƯỚNG MENU KINH DOANH
=============================================================
Mã Nhiệm Vụ: SCRUM-69 / SCRUM-74
Tiêu đề User Story:
  "Là người dùng của hệ thống, tôi muốn thấy menu điều hướng đúng theo quyền của mình,
   để không bị rối bởi những chức năng mình không được dùng."

Tiêu chí chấp nhận (Description):
  1. Mục menu không thuộc quyền thì không hiển thị (Lọc sạch khỏi DOM)
  2. Hiển thị tên, vai trò và nhóm kinh doanh đang thuộc về
  3. Dùng được thuận tiện trên màn hình 360px
=============================================================
"""

# ==============================================================================
# 1. BẢNG ĐỊNH NGHĨA VAI TRÒ (ROLES) & QUYỀN HẠN (PERMISSIONS)
# ==============================================================================
ROLES = {
    "director": {
        "code": "director",
        "name": "Giám đốc kinh doanh",
        "badge_class": "badge-director",
        "badge_color": "#7c3aed",
        "description": "Toàn quyền quản trị toàn bộ hoạt động kinh doanh và hệ thống",
        "permissions": [
            "view_dashboard",
            "manage_customers",
            "manage_deals",
            "view_team_reports",
            "manage_team_targets",
            "manage_sales_staff",
            "system_settings"
        ]
    },
    "team_lead": {
        "code": "team_lead",
        "name": "Trưởng nhóm kinh doanh",
        "badge_class": "badge-team-lead",
        "badge_color": "#2563eb",
        "description": "Quản lý mục tiêu, báo cáo và chỉ số doanh số của nhóm phụ trách",
        "permissions": [
            "view_dashboard",
            "manage_customers",
            "manage_deals",
            "view_team_reports",
            "manage_team_targets"
        ]
    },
    "sales_rep": {
        "code": "sales_rep",
        "name": "Chuyên viên kinh doanh",
        "badge_class": "badge-sales-rep",
        "badge_color": "#059669",
        "description": "Tác nghiệp trực tiếp với khách hàng và chốt hợp đồng/đơn hàng",
        "permissions": [
            "view_dashboard",
            "manage_customers",
            "manage_deals"
        ]
    },
    "intern": {
        "code": "intern",
        "name": "Thực tập sinh kinh doanh",
        "badge_class": "badge-intern",
        "badge_color": "#d97706",
        "description": "Học việc và hỗ trợ theo dõi số liệu tổng quan trên Bảng điều khiển",
        "permissions": [
            "view_dashboard"
        ]
    }
}

# Nhãn tiếng Việt thân thiện giải thích từng quyền hạn
PERMISSION_LABELS = {
    "view_dashboard": "Xem Bảng điều khiển tổng quan",
    "manage_customers": "Quản lý danh sách khách hàng",
    "manage_deals": "Quản lý đơn hàng & hợp đồng",
    "view_team_reports": "Xem báo cáo doanh số nhóm",
    "manage_team_targets": "Thiết lập chỉ tiêu & KPI nhóm",
    "manage_sales_staff": "Quản lý nhân viên kinh doanh",
    "system_settings": "Cấu hình tham số hệ thống"
}

# ==============================================================================
# 2. TOÀN BỘ CẤU TRÚC MENU ĐIỀU HƯỚNG CỦA HỆ THỐNG
# ==============================================================================
ALL_MENU_ITEMS = [
    {
        "id": "dashboard",
        "title": "Bảng điều khiển",
        "icon": "layout-dashboard",
        "url": "/dashboard",
        "required_permission": "view_dashboard",
        "badge": "Chính",
        "badge_type": "info",
        "description": "Tổng quan chỉ số kinh doanh, thông báo và lối tắt làm việc"
    },
    {
        "id": "customers",
        "title": "Khách hàng của tôi",
        "icon": "users",
        "url": "/customers",
        "required_permission": "manage_customers",
        "badge": "48",
        "badge_type": "neutral",
        "description": "Danh sách khách hàng tiềm năng, lịch sử chăm sóc và phân nhóm"
    },
    {
        "id": "deals",
        "title": "Đơn hàng & Hợp đồng",
        "icon": "shopping-bag",
        "url": "/deals",
        "required_permission": "manage_deals",
        "badge": "16",
        "badge_type": "warning",
        "description": "Theo dõi tiến độ chốt đơn, giá trị hợp đồng và thanh toán"
    },
    {
        "id": "team_reports",
        "title": "Báo cáo doanh số nhóm",
        "icon": "bar-chart-3",
        "url": "/team-reports",
        "required_permission": "view_team_reports",
        "badge": "Doanh thu",
        "badge_type": "success",
        "description": "Biểu đồ so sánh doanh thu, năng suất và tỷ lệ chuyển đổi nhóm"
    },
    {
        "id": "team_targets",
        "title": "Chỉ tiêu & KPI nhóm",
        "icon": "target",
        "url": "/team-targets",
        "required_permission": "manage_team_targets",
        "badge": "KPI",
        "badge_type": "primary",
        "description": "Giao chỉ tiêu tháng/quý và đánh giá mức độ hoàn thành"
    },
    {
        "id": "staff_management",
        "title": "Quản lý nhân sự kinh doanh",
        "icon": "user-check",
        "url": "/staff-management",
        "required_permission": "manage_sales_staff",
        "badge": "Admin",
        "badge_type": "danger",
        "description": "Quản lý danh sách nhân viên kinh doanh, phân bổ nhóm và phân quyền"
    },
    {
        "id": "settings",
        "title": "Cấu hình hệ thống",
        "icon": "settings",
        "url": "/settings",
        "required_permission": "system_settings",
        "badge": "Hệ thống",
        "badge_type": "secondary",
        "description": "Thiết lập tham số chiết khấu, chính sách bán hàng và bảo mật"
    }
]

# ==============================================================================
# 3. DANH SÁCH NGƯỜI DÙNG MẪU (ĐẦY ĐỦ: TÊN, VAI TRÒ, NHÓM KINH DOANH)
# ==============================================================================
SAMPLE_USERS = {
    "director": {
        "username": "director",
        "name": "Nguyễn Tuấn Anh",
        "email": "tuananh.nguyen@enterprise-sales.vn",
        "role_code": "director",
        "role_name": "Giám đốc kinh doanh",
        "business_group": "Ban Giám Đốc Kinh Doanh Toàn Quốc",
        "short_group": "BGĐ Kinh Doanh",
        "avatar_letters": "TA",
        "avatar_bg": "#7c3aed",
        "expected_menu_count": 7
    },
    "team_lead": {
        "username": "team_lead",
        "name": "Trần Thị Mai Phương",
        "email": "maiphuong.tran@enterprise-sales.vn",
        "role_code": "team_lead",
        "role_name": "Trưởng nhóm kinh doanh",
        "business_group": "Nhóm Khách Hàng Doanh Nghiệp (B2B)",
        "short_group": "Nhóm B2B Doanh Nghiệp",
        "avatar_letters": "MP",
        "avatar_bg": "#2563eb",
        "expected_menu_count": 5
    },
    "sales_rep": {
        "username": "sales_rep",
        "name": "Lê Hoàng Phúc",
        "email": "hoangphuc.le@enterprise-sales.vn",
        "role_code": "sales_rep",
        "role_name": "Chuyên viên kinh doanh",
        "business_group": "Nhóm Bán Lẻ Khu Vực Miền Bắc",
        "short_group": "Bán Lẻ Miền Bắc",
        "avatar_letters": "HP",
        "avatar_bg": "#059669",
        "expected_menu_count": 3
    },
    "intern": {
        "username": "intern",
        "name": "Phạm Minh Khôi",
        "email": "minhkhoi.pham@enterprise-sales.vn",
        "role_code": "intern",
        "role_name": "Thực tập sinh kinh doanh",
        "business_group": "Nhóm Phát Triển Khách Hàng Mới",
        "short_group": "Khách Hàng Mới",
        "avatar_letters": "MK",
        "avatar_bg": "#d97706",
        "expected_menu_count": 1
    }
}

# ==============================================================================
# 4. HÀM NGHIỆP VỤ: LỌC MENU DỰA THEO PHÂN QUYỀN RBAC (TIÊU CHÍ 1)
# ==============================================================================
def get_user_menu(user):
    """
    Lấy danh sách các mục menu mà người dùng ĐƯỢC PHÉP nhìn thấy.
    Những mục menu không thuộc quyền sẽ bị LOẠI BỎ HOÀN TOÀN khỏi danh sách,
    đảm bảo không bao giờ được render ra mã HTML/DOM gửi tới trình duyệt.
    """
    if not user:
        return []
    
    role_info = ROLES.get(user["role_code"], {})
    user_permissions = set(role_info.get("permissions", []))
    
    allowed_menu = []
    for item in ALL_MENU_ITEMS:
        required_perm = item.get("required_permission")
        if not required_perm or required_perm in user_permissions:
            allowed_menu.append(item)
            
    return allowed_menu

def check_user_permission(user, permission_code):
    """Kiểm tra người dùng hiện tại có quyền thao tác hay không."""
    if not user:
        return False
    role_info = ROLES.get(user["role_code"], {})
    return permission_code in role_info.get("permissions", [])

# ==============================================================================
# 5. DỮ LIỆU MẪU DÀNH CHO CÁC TRANG CHỨC NĂNG
# ==============================================================================
SAMPLE_CUSTOMERS = [
    {"id": 1, "code": "KH-001", "name": "Tập đoàn Công nghệ Alpha", "contact": "Nguyễn Văn Hùng", "phone": "0912 345 678", "revenue": "1.250.000.000 ₫", "status": "VIP", "assigned_to": "Lê Hoàng Phúc"},
    {"id": 2, "code": "KH-002", "name": "Công ty Cổ phần Xây dựng Beta", "contact": "Trịnh Hoàng Nam", "phone": "0987 654 321", "revenue": "840.000.000 ₫", "status": "Đang chăm sóc", "assigned_to": "Lê Hoàng Phúc"},
    {"id": 3, "code": "KH-003", "name": "Chuỗi Khách sạn Grand Palace", "contact": "Vũ Thuỳ Linh", "phone": "0903 112 233", "revenue": "2.100.000.000 ₫", "status": "VIP", "assigned_to": "Trần Thị Mai Phương"},
    {"id": 4, "code": "KH-004", "name": "Logistics Đông Dương", "contact": "Lê Thành Đạt", "phone": "0978 998 877", "revenue": "450.000.000 ₫", "status": "Tiềm năng", "assigned_to": "Phạm Minh Khôi"},
    {"id": 5, "code": "KH-005", "name": "Ngân hàng TMCP Phương Đông", "contact": "Đỗ Thu Trang", "phone": "0934 556 677", "revenue": "3.800.000.000 ₫", "status": "Chiến lược", "assigned_to": "Trần Thị Mai Phương"}
]

SAMPLE_DEALS = [
    {"id": 101, "code": "HD-2026-089", "title": "Triển khai phần mềm quản lý kho thông minh", "customer": "Tập đoàn Công nghệ Alpha", "value": "650.000.000 ₫", "stage": "Đã ký kết", "stage_color": "success", "date": "28/09/2026"},
    {"id": 102, "code": "HD-2026-092", "title": "Gói thiết bị mạng & giám sát an ninh", "customer": "Công ty Cổ phần Xây dựng Beta", "value": "320.000.000 ₫", "stage": "Đang đàm phán", "stage_color": "warning", "date": "25/09/2026"},
    {"id": 103, "code": "HD-2026-095", "title": "Giải pháp thanh toán không tiền mặt", "customer": "Ngân hàng TMCP Phương Đông", "value": "1.850.000.000 ₫", "stage": "Chờ phê duyệt", "stage_color": "primary", "date": "29/09/2026"},
    {"id": 104, "code": "HD-2026-097", "title": "Nâng cấp máy chủ dữ liệu đám mây", "customer": "Chuỗi Khách sạn Grand Palace", "value": "920.000.000 ₫", "stage": "Đã ký kết", "stage_color": "success", "date": "22/09/2026"}
]

SAMPLE_STAFF = [
    {"id": 1, "code": "NV-001", "name": "Nguyễn Tuấn Anh", "role": "Giám đốc kinh doanh", "group": "Ban Giám Đốc Kinh Doanh Toàn Quốc", "email": "tuananh.nguyen@enterprise-sales.vn", "kpi": "115%", "status": "Đang hoạt động"},
    {"id": 2, "code": "NV-002", "name": "Trần Thị Mai Phương", "role": "Trưởng nhóm kinh doanh", "group": "Nhóm Khách Hàng Doanh Nghiệp (B2B)", "email": "maiphuong.tran@enterprise-sales.vn", "kpi": "108%", "status": "Đang hoạt động"},
    {"id": 3, "code": "NV-003", "name": "Lê Hoàng Phúc", "role": "Chuyên viên kinh doanh", "group": "Nhóm Bán Lẻ Khu Vực Miền Bắc", "email": "hoangphuc.le@enterprise-sales.vn", "kpi": "98%", "status": "Đang hoạt động"},
    {"id": 4, "code": "NV-004", "name": "Phạm Minh Khôi", "role": "Thực tập sinh kinh doanh", "group": "Nhóm Phát Triển Khách Hàng Mới", "email": "minhkhoi.pham@enterprise-sales.vn", "kpi": "92%", "status": "Đang thử việc"}
]
