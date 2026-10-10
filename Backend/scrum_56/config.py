"""
Cấu hình hệ thống - SCRUM-30 / SCRUM-56
User Story: "Là Nhân viên kinh doanh, tôi muốn xem danh sách lead với bộ lọc và bộ lọc lưu sẵn,
để mở máy buổi sáng là biết ngay hôm nay cần gọi ai."

Tiêu chí chấp nhận:
1. Lọc theo trạng thái, nguồn, phân loại nóng ấm lạnh, người phụ trách, khoảng thời gian.
2. Lead quá SLA hiển thị nổi bật.
3. Lưu và đặt tên cho bộ lọc hay dùng.
"""

TICKET_ID = "SCRUM-56"
PARENT_EPIC = "SCRUM-30"

# Các trạng thái của Lead (Lead Statuses)
STATUS_NEW = "NEW"                    # Mới tiếp nhận từ Marketing
STATUS_ASSIGNED = "ASSIGNED"          # Đã phân bổ cho Sales, chờ phản hồi
STATUS_IN_CARE = "IN_CARE"            # Đang chăm sóc tích cực
STATUS_CONTACTED = "CONTACTED"        # Đã liên hệ thành công
STATUS_QUALIFIED = "QUALIFIED"        # Đủ điều kiện chuyển đổi cơ hội
STATUS_CONVERTED = "CONVERTED"        # Đã chuyển đổi thành khách hàng & hợp đồng
STATUS_LOST = "LOST"                  # Thất bại / Hủy bỏ

STATUS_LABELS = {
    STATUS_NEW: "Mới tiếp nhận",
    STATUS_ASSIGNED: "Chờ tiếp nhận",
    STATUS_IN_CARE: "Đang chăm sóc",
    STATUS_CONTACTED: "Đã liên hệ",
    STATUS_QUALIFIED: "Đủ điều kiện ⭐",
    STATUS_CONVERTED: "Đã chuyển đổi 🔒",
    STATUS_LOST: "Không thành công"
}

STATUS_BADGE_CLASSES = {
    STATUS_NEW: "badge-blue",
    STATUS_ASSIGNED: "badge-amber",
    STATUS_IN_CARE: "badge-purple",
    STATUS_CONTACTED: "badge-green",
    STATUS_QUALIFIED: "badge-emerald",
    STATUS_CONVERTED: "badge-indigo",
    STATUS_LOST: "badge-gray"
}

# Nguồn Lead (Lead Sources)
SOURCES = [
    "Google Ads",
    "Facebook Ads",
    "Website Form",
    "Sự kiện & Triển lãm Tech Expo",
    "Đối tác giới thiệu (Referral)",
    "Tổng đài Hotline"
]

SOURCE_ICONS = {
    "Google Ads": "🔍",
    "Facebook Ads": "📱",
    "Website Form": "🌐",
    "Sự kiện & Triển lãm Tech Expo": "🎪",
    "Đối tác giới thiệu (Referral)": "🤝",
    "Tổng đài Hotline": "📞"
}

# Phân loại Nóng / Ấm / Lạnh (Lead Temperature / Rating)
TEMP_HOT = "HOT"      # 🔥 Nóng - Nhu cầu cấp thiết, ngân sách sẵn sàng, cần chốt ngay
TEMP_WARM = "WARM"    # ⚡ Ấm - Đang tìm hiểu, có ngân sách, cần tư vấn thêm
TEMP_COLD = "COLD"    # ❄️ Lạnh - Chưa rõ nhu cầu, mới để lại thông tin

TEMPERATURES = [TEMP_HOT, TEMP_WARM, TEMP_COLD]

TEMP_LABELS = {
    TEMP_HOT: "🔥 Nóng (Hot)",
    TEMP_WARM: "⚡ Ấm (Warm)",
    TEMP_COLD: "❄️ Lạnh (Cold)"
}

TEMP_BADGE_CLASSES = {
    TEMP_HOT: "badge-temp-hot",
    TEMP_WARM: "badge-temp-warm",
    TEMP_COLD: "badge-temp-cold"
}

# Trạng thái SLA
SLA_ON_TIME = "ON_TIME"        # Trong hạn SLA
SLA_NEAR_DUE = "NEAR_DUE"      # Sắp đến hạn (< 30 phút)
SLA_OVERDUE = "OVERDUE"        # Quá hạn SLA 🚩

# Các vai trò trong hệ thống
ROLE_SALES_REP = "SALES_REP"          # Nhân viên kinh doanh
ROLE_TEAM_LEAD = "TEAM_LEAD"          # Trưởng nhóm kinh doanh
ROLE_DIRECTOR = "DIRECTOR"            # Giám đốc kinh doanh

ROLE_LABELS = {
    ROLE_SALES_REP: "Nhân viên kinh doanh",
    ROLE_TEAM_LEAD: "Trưởng nhóm kinh doanh",
    ROLE_DIRECTOR: "Giám đốc kinh doanh"
}

# Cổng khởi chạy mặc định của Flask
DEFAULT_PORT = 5000
