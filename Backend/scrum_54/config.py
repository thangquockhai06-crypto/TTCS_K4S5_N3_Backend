"""
Cấu hình hệ thống - SCRUM-30 / SCRUM-54
User Story: "Là Nhân viên kinh doanh, tôi muốn chuyển một lead đủ điều kiện thành
khách hàng và cơ hội, để không phải nhập lại thông tin đã hỏi khách ba lần."

Tiêu chí chấp nhận (Acceptance Criteria):
1. Một thao tác sinh đồng thời khách hàng doanh nghiệp, người liên hệ và cơ hội bán hàng.
2. Dữ liệu lead được chuyển sang, không phải nhập lại.
3. Lead chuyển sang trạng thái Đã chuyển đổi và không sửa được nữa.
4. Toàn bộ hoạt động đã ghi trên lead được giữ lại trên khách hàng mới.
"""

# Mã Jira Ticket
TICKET_ID = "SCRUM-54"
PARENT_EPIC = "SCRUM-30"

# Các trạng thái của Lead (Lead Statuses)
STATUS_NEW = "NEW"                          # Mới tạo
STATUS_CONTACTED = "CONTACTED"              # Đang tiếp cận / Đang chăm sóc
STATUS_QUALIFIED = "QUALIFIED"              # Đủ điều kiện chuyển đổi (Sẵn sàng Convert)
STATUS_CONVERTED = "CONVERTED"              # Đã chuyển đổi (ĐÃ KHÓA BẤT BIẾN 🔒)
STATUS_DISQUALIFIED = "DISQUALIFIED"        # Không đủ điều kiện

STATUS_LABELS = {
    STATUS_NEW: "Mới tiếp nhận",
    STATUS_CONTACTED: "Đang chăm sóc",
    STATUS_QUALIFIED: "Đủ điều kiện chuyển đổi ⭐",
    STATUS_CONVERTED: "Đã chuyển đổi 🔒",
    STATUS_DISQUALIFIED: "Không đủ điều kiện"
}

STATUS_COLORS = {
    STATUS_NEW: "#3b82f6",          # Blue
    STATUS_CONTACTED: "#f59e0b",    # Amber
    STATUS_QUALIFIED: "#10b981",    # Emerald green
    STATUS_CONVERTED: "#8b5cf6",    # Purple / Locked
    STATUS_DISQUALIFIED: "#ef4444"  # Red
}

STATUS_BADGE_CLASSES = {
    STATUS_NEW: "badge-blue",
    STATUS_CONTACTED: "badge-amber",
    STATUS_QUALIFIED: "badge-green",
    STATUS_CONVERTED: "badge-purple",
    STATUS_DISQUALIFIED: "badge-red"
}

# Các giai đoạn của Cơ hội bán hàng (Opportunity Stages)
STAGE_DISCOVERY = "DISCOVERY"        # Khảo sát nhu cầu
STAGE_PROPOSAL = "PROPOSAL"          # Báo giá & Đề xuất giải pháp
STAGE_NEGOTIATION = "NEGOTIATION"    # Đàm phán điều khoản
STAGE_WON = "WON"                    # Chốt thành công (Won) 🎉
STAGE_LOST = "LOST"                  # Thất bại (Lost)

STAGE_LABELS = {
    STAGE_DISCOVERY: "1. Khảo sát nhu cầu",
    STAGE_PROPOSAL: "2. Báo giá & Đề xuất",
    STAGE_NEGOTIATION: "3. Đàm phán hợp đồng",
    STAGE_WON: "4. Chốt thành công 🎉",
    STAGE_LOST: "5. Thất bại"
}

STAGE_COLORS = {
    STAGE_DISCOVERY: "#0284c7",
    STAGE_PROPOSAL: "#d97706",
    STAGE_NEGOTIATION: "#7c3aed",
    STAGE_WON: "#059669",
    STAGE_LOST: "#dc2626"
}

# Các loại hoạt động tương tác (Activity Types)
ACTIVITY_CALL = "CALL"              # Cuộc gọi điện thoại
ACTIVITY_MEETING = "MEETING"        # Buổi hẹn / Demo sản phẩm
ACTIVITY_EMAIL = "EMAIL"            # Email trao đổi
ACTIVITY_NOTE = "NOTE"              # Ghi chú chăm sóc
ACTIVITY_CONVERT = "CONVERT"        # Mốc chuyển đổi sang Khách hàng & Cơ hội 🚀

ACTIVITY_ICONS = {
    ACTIVITY_CALL: "📞",
    ACTIVITY_MEETING: "🤝",
    ACTIVITY_EMAIL: "✉️",
    ACTIVITY_NOTE: "📝",
    ACTIVITY_CONVERT: "🚀"
}

ACTIVITY_LABELS = {
    ACTIVITY_CALL: "Cuộc gọi điện thoại",
    ACTIVITY_MEETING: "Buổi gặp / Demo trực tiếp",
    ACTIVITY_EMAIL: "Email trao đổi",
    ACTIVITY_NOTE: "Ghi chú chăm sóc",
    ACTIVITY_CONVERT: "Cột mốc Chuyển đổi Lead 🚀"
}

# Các vai trò người dùng (User Roles)
ROLE_SALES_REP = "SALES_REP"        # Nhân viên kinh doanh
ROLE_TEAM_LEAD = "TEAM_LEAD"        # Trưởng nhóm kinh doanh
ROLE_DIRECTOR = "DIRECTOR"          # Giám đốc kinh doanh

ROLE_LABELS = {
    ROLE_SALES_REP: "Nhân viên kinh doanh",
    ROLE_TEAM_LEAD: "Trưởng nhóm kinh doanh",
    ROLE_DIRECTOR: "Giám đốc kinh doanh"
}

# Cổng khởi chạy mặc định của Flask
DEFAULT_PORT = 5000
