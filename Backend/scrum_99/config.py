"""
Cấu hình hệ thống - SCRUM-30 / SCRUM-99
User Story: "Là Nhân viên Marketing, tôi muốn xem báo cáo hiệu quả từng nguồn lead,
để dồn ngân sách vào nguồn thực sự ra doanh thu."

Tiêu chí chấp nhận (Acceptance Criteria):
1. Số lead, tỷ lệ được nhận, tỷ lệ chuyển đổi thành cơ hội theo từng nguồn và từng chiến dịch.
2. Lọc theo khoảng thời gian.
3. Xuất Excel.
"""

TICKET_ID = "SCRUM-99"
PARENT_EPIC = "SCRUM-30"

# Danh sách Nguồn Lead (Lead Sources)
SOURCES = [
    "Google Ads",
    "Facebook Ads",
    "Website Organic (SEO)",
    "Sự kiện & Triển lãm Tech Expo",
    "Email Marketing",
    "Đối tác giới thiệu (Referral)",
    "TikTok Ads"
]

SOURCE_ICONS = {
    "Google Ads": "🔍",
    "Facebook Ads": "📱",
    "Website Organic (SEO)": "🌐",
    "Sự kiện & Triển lãm Tech Expo": "🎪",
    "Email Marketing": "✉️",
    "Đối tác giới thiệu (Referral)": "🤝",
    "TikTok Ads": "🎵"
}

SOURCE_COLORS = {
    "Google Ads": "#4285F4",
    "Facebook Ads": "#1877F2",
    "Website Organic (SEO)": "#10B981",
    "Sự kiện & Triển lãm Tech Expo": "#F59E0B",
    "Email Marketing": "#8B5CF6",
    "Đối tác giới thiệu (Referral)": "#06B6D4",
    "TikTok Ads": "#EC4899"
}

# Các chiến dịch Marketing mẫu (Marketing Campaigns)
CAMPAIGNS_DEF = [
    {
        "id": "CAMP-01",
        "name": "Q1 Tech Growth - Google Search",
        "source": "Google Ads",
        "budget": 50000000,
        "spent": 42000000,
        "start_date": "2026-01-01",
        "end_date": "2026-03-31"
    },
    {
        "id": "CAMP-02",
        "name": "Ra Mắt CRM Cloud 2026 - Facebook Lead Form",
        "source": "Facebook Ads",
        "budget": 40000000,
        "spent": 38500000,
        "start_date": "2026-01-15",
        "end_date": "2026-04-15"
    },
    {
        "id": "CAMP-03",
        "name": "Triển Lãm Quốc Tế Tech Expo Vietnam 2026",
        "source": "Sự kiện & Triển lãm Tech Expo",
        "budget": 80000000,
        "spent": 75000000,
        "start_date": "2026-02-10",
        "end_date": "2026-02-28"
    },
    {
        "id": "CAMP-04",
        "name": "Webinar Chuyển Đổi Số B2B & SEO Blog",
        "source": "Website Organic (SEO)",
        "budget": 20000000,
        "spent": 14000000,
        "start_date": "2026-01-01",
        "end_date": "2026-06-30"
    },
    {
        "id": "CAMP-05",
        "name": "Chương Trình Đối Tác Giới Thiệu Hoa Hồng Cao",
        "source": "Đối tác giới thiệu (Referral)",
        "budget": 30000000,
        "spent": 22000000,
        "start_date": "2026-01-01",
        "end_date": "2026-12-31"
    },
    {
        "id": "CAMP-06",
        "name": "Email Nurturing Dành Cho Giám Đốc CNTT",
        "source": "Email Marketing",
        "budget": 15000000,
        "spent": 11000000,
        "start_date": "2026-02-01",
        "end_date": "2026-05-31"
    },
    {
        "id": "CAMP-07",
        "name": "TikTok Video Review Giải Pháp Tự Động Hóa",
        "source": "TikTok Ads",
        "budget": 25000000,
        "spent": 24000000,
        "start_date": "2026-02-15",
        "end_date": "2026-04-30"
    }
]

# Các vai trò trong hệ thống
ROLE_MARKETING = "MARKETING"          # Nhân viên Marketing (Vai trò chính của story)
ROLE_SALES_REP = "SALES_REP"          # Nhân viên kinh doanh
ROLE_TEAM_LEAD = "TEAM_LEAD"          # Trưởng nhóm kinh doanh
ROLE_DIRECTOR = "DIRECTOR"            # Giám đốc Marketing & Kinh doanh

ROLE_LABELS = {
    ROLE_MARKETING: "Nhân viên Marketing",
    ROLE_SALES_REP: "Nhân viên kinh doanh",
    ROLE_TEAM_LEAD: "Trưởng nhóm kinh doanh",
    ROLE_DIRECTOR: "Giám đốc kinh doanh"
}

# Trạng thái tiếp nhận & chuyển đổi của Lead
STATUS_NEW = "NEW"                    # Mới thu thập từ Marketing
STATUS_ACCEPTED = "ACCEPTED"          # Đã được nhân viên Sales bấm nhận
STATUS_OPPORTUNITY = "OPPORTUNITY"    # Đã chuyển đổi thành Cơ hội bán hàng
STATUS_WON = "WON"                    # Chốt hợp đồng thành công (Ra doanh thu)
STATUS_REJECTED = "REJECTED"          # Bị Sales từ chối nhận
STATUS_LOST = "LOST"                  # Thất bại khi theo đuổi cơ hội

STATUS_LABELS = {
    STATUS_NEW: "Mới từ Marketing",
    STATUS_ACCEPTED: "Sales đã nhận",
    STATUS_OPPORTUNITY: "Đã thành Cơ hội",
    STATUS_WON: "Thành công (Doanh thu) 🎉",
    STATUS_REJECTED: "Sales từ chối",
    STATUS_LOST: "Không chốt được"
}

# Cổng khởi chạy mặc định
DEFAULT_PORT = 5000
