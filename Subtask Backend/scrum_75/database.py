"""
Hệ thống quản lý dữ liệu người dùng, phân quyền RBAC & dữ liệu mẫu
User Story: SCRUM-69 / SCRUM-75
"""

from datetime import datetime

# Bảng định nghĩa danh mục vai trò & quyền hạn
ROLES = {
    "admin": {
        "code": "admin",
        "name": "Giám đốc / Quản trị viên",
        "badge_class": "badge-admin",
        "description": "Toàn quyền quản trị hệ thống, duyệt báo cáo và cấu hình",
        "permissions": [
            "view_dashboard",
            "view_projects",
            "manage_projects",
            "view_financial",
            "system_settings",
            "manage_roles"
        ]
    },
    "manager": {
        "code": "manager",
        "name": "Trưởng phòng nghiệp vụ",
        "badge_class": "badge-manager",
        "description": "Quản lý dự án, xem báo cáo doanh số tài chính của phòng",
        "permissions": [
            "view_dashboard",
            "view_projects",
            "manage_projects",
            "view_financial"
        ]
    },
    "staff": {
        "code": "staff",
        "name": "Chuyên viên tác nghiệp",
        "badge_class": "badge-staff",
        "description": "Thực thi công việc được giao, xem dự án cá nhân",
        "permissions": [
            "view_dashboard",
            "view_projects"
        ]
    },
    "intern": {
        "code": "intern",
        "name": "Thực tập sinh",
        "badge_class": "badge-intern",
        "description": "Tài khoản quan sát viên, chỉ xem Bảng điều khiển cơ bản",
        "permissions": [
            "view_dashboard"
        ]
    }
}

# Tên quyền hạn hiển thị tiếng Việt thân thiện
PERMISSION_LABELS = {
    "view_dashboard": "Xem Bảng điều khiển hệ thống",
    "view_projects": "Xem Danh sách dự án & tiến độ",
    "manage_projects": "Tạo & Quản lý dự án nghiệp vụ",
    "view_financial": "Xem Báo cáo tài chính & doanh thu",
    "system_settings": "Cấu hình bảo mật & Quản trị hệ thống",
    "manage_roles": "Phân quyền & Cấp phép người dùng"
}

# Danh sách người dùng mẫu tương ứng từng vai trò
SAMPLE_USERS = {
    "admin": {
        "username": "admin",
        "name": "Nguyễn Tuấn Anh",
        "email": "tuananh.nguyen@enterprise.vn",
        "role_code": "admin",
        "department": "Ban Giám Đốc",
        "avatar_text": "TA",
        "avatar_bg": "#4f46e5"
    },
    "manager": {
        "username": "manager",
        "name": "Trần Thị Mai Phương",
        "email": "phuong.tran@enterprise.vn",
        "role_code": "manager",
        "department": "Phòng Kế Hoạch & Dự Án",
        "avatar_text": "MP",
        "avatar_bg": "#0ea5e9"
    },
    "staff": {
        "username": "staff",
        "name": "Lê Hoàng Phúc",
        "email": "phuc.le@enterprise.vn",
        "role_code": "staff",
        "department": "Phòng Kinh Doanh Số 1",
        "avatar_text": "HP",
        "avatar_bg": "#10b981"
    },
    "intern": {
        "username": "intern",
        "name": "Phạm Minh Khôi",
        "email": "khoi.pham@enterprise.vn",
        "role_code": "intern",
        "department": "Khối Đào Tạo Sinh Viên",
        "avatar_text": "MK",
        "avatar_bg": "#f59e0b"
    }
}

# Danh sách dự án mẫu
SAMPLE_PROJECTS = [
    {
        "id": "PRJ-01",
        "name": "Nâng cấp Cổng thông tin Khách hàng Doanh nghiệp v2.5",
        "leader": "Trần Thị Mai Phương",
        "status": "Đang thực hiện",
        "status_class": "status-in-progress",
        "progress": 78,
        "deadline": "15/10/2026"
    },
    {
        "id": "PRJ-02",
        "name": "Tích hợp Hệ thống Thanh toán Trực tuyến Quốc tế",
        "leader": "Lê Hoàng Phúc",
        "status": "Chờ phê duyệt",
        "status_class": "status-pending",
        "progress": 45,
        "deadline": "28/11/2026"
    },
    {
        "id": "PRJ-03",
        "name": "Triển khai Quy trình Xác thực Bảo mật 2 Lớp (2FA)",
        "leader": "Nguyễn Tuấn Anh",
        "status": "Hoàn thành",
        "status_class": "status-completed",
        "progress": 100,
        "deadline": "01/09/2026"
    },
    {
        "id": "PRJ-04",
        "name": "Khảo sát & Tối ưu Trải nghiệm Điều hướng Người dùng (UX Audit)",
        "leader": "Phạm Minh Khôi",
        "status": "Đang thực hiện",
        "status_class": "status-in-progress",
        "progress": 62,
        "deadline": "30/12/2026"
    }
]

# Dữ liệu tài chính mẫu
FINANCIAL_DATA = {
    "total_revenue": "18.450.000.000 VNĐ",
    "profit_margin": "+24.8%",
    "quarterly_target": "92%",
    "reports": [
        {"period": "Q1/2026", "revenue": "4.200.000.000 VNĐ", "status": "Đã kiểm toán", "auditor": "KPMG Vietnam"},
        {"period": "Q2/2026", "revenue": "5.150.000.000 VNĐ", "status": "Đã kiểm toán", "auditor": "KPMG Vietnam"},
        {"period": "Q3/2026", "revenue": "5.800.000.000 VNĐ", "status": "Sơ bộ", "auditor": "Nội bộ phòng Kế toán"},
        {"period": "Dự phóng Q4/2026", "revenue": "6.200.000.000 VNĐ", "status": "Dự báo", "auditor": "Ban Giám Đốc"}
    ]
}

# Nhật ký yêu cầu cấp quyền từ người dùng (Mock tickets)
ACCESS_REQUESTS = []

def get_user(username):
    """Lấy thông tin người dùng kèm vai trò và quyền hạn."""
    user = SAMPLE_USERS.get(username)
    if not user:
        return None
    role_info = ROLES.get(user["role_code"], {})
    full_user = dict(user)
    full_user["role_name"] = role_info.get("name", "Người dùng")
    full_user["role_badge_class"] = role_info.get("badge_class", "badge-staff")
    full_user["permissions"] = role_info.get("permissions", [])
    return full_user

def add_access_request(username, target_url, reason):
    """Ghi nhận yêu cầu xin cấp quyền khi gặp 403."""
    user = get_user(username)
    req = {
        "id": f"REQ-{len(ACCESS_REQUESTS) + 1:03d}",
        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "user_name": user["name"] if user else username,
        "username": username,
        "role": user["role_name"] if user else "Unknown",
        "target_url": target_url,
        "reason": reason or "Người dùng xin cấp quyền truy cập để phục vụ công việc",
        "status": "Chờ duyệt"
    }
    ACCESS_REQUESTS.insert(0, req)
    return req
