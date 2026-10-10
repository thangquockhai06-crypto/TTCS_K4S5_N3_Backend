"""
Cấu hình hệ thống phân bổ Lead tự động - Ticket SCRUM-30 / SCRUM-49
Vai trò: Giám đốc kinh doanh
Mục tiêu: Cấu hình quy tắc phân bổ lead tự động, để lead tới tay người phụ trách
trong vài phút thay vì chờ họp giao ban.
"""

import os

# Đường dẫn thư mục gốc
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Cấu hình SLA và luồng xử lý nền
# Tiêu chí đề bài: Phân bổ chạy nền, hoàn tất trong vòng 5 phút (300 giây)
SLA_LIMIT_SECONDS = 300  # 5 phút tối đa theo yêu cầu bài toán
WORKER_POLL_INTERVAL_SECONDS = 2  # Chu kỳ luồng nền kiểm tra lead mới (2 giây)

# Danh sách Khu vực hỗ trợ (Region)
REGIONS = [
    "Toàn quốc",
    "Miền Bắc",
    "Miền Trung",
    "Miền Nam"
]

# Chi tiết tỉnh / thành theo khu vực (dùng cho form tạo lead)
CITIES_BY_REGION = {
    "Miền Bắc": ["Hà Nội", "Hải Phòng", "Quảng Ninh", "Bắc Ninh", "Vĩnh Phúc", "Hải Dương"],
    "Miền Trung": ["Đà Nẵng", "Huế", "Nha Trang (Khánh Hòa)", "Quảng Nam", "Nghệ An", "Bình Định"],
    "Miền Nam": ["TP. Hồ Chí Minh", "Bình Dương", "Đồng Nai", "Cần Thơ", "Long An", "Bà Rịa - Vũng Tàu"]
}

# Danh sách Ngành nghề (Industry)
INDUSTRIES = [
    "Tất cả ngành nghề",
    "Tài chính - Ngân hàng",
    "Bất động sản",
    "Công nghệ thông tin",
    "Bán lẻ & Thương mại điện tử",
    "Sản xuất & Chế biến",
    "Giáo dục & Đào tạo",
    "Y tế & Chăm sóc sức khỏe"
]

# Nguồn Lead (Lead Source)
LEAD_SOURCES = [
    "Website Form",
    "Facebook Ads",
    "Google Search Ads",
    "Hotline tư vấn",
    "Hội thảo / Sự kiện",
    "Đối tác giới thiệu (Referral)",
    "API Tích hợp bên ngoài"
]

# Trạng thái Lead
LEAD_STATUS_PENDING = "PENDING"               # Chờ chạy nền phân bổ
LEAD_STATUS_ASSIGNED = "ASSIGNED"             # Đã phân bổ tự động thành công
LEAD_STATUS_MANUAL_QUEUE = "MANUAL_QUEUE"     # Rơi vào hàng chờ để trưởng nhóm phân tay

# Cơ chế phân bổ trong Quy tắc
ASSIGNMENT_TYPE_ROUND_ROBIN = "ROUND_ROBIN"   # Xoay vòng đều trong nhóm
ASSIGNMENT_TYPE_DIRECT = "DIRECT"             # Gán trực tiếp cho nhân viên cụ thể
