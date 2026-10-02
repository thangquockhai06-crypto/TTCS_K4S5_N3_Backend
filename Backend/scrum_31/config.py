"""
Cấu hình hệ thống - SCRUM-35 / SCRUM-31
User Story: "Là Nhân viên kinh doanh, tôi muốn soạn báo giá từ một cơ hội, để gửi báo giá trong buổi chiều cùng ngày khách hỏi."

5 Tiêu chí chấp nhận (Acceptance Criteria):
1. Dòng sản phẩm được kế thừa từ cơ hội, sửa lại được.
2. Mỗi dòng nhập chiết khấu theo phần trăm hoặc số tiền, hệ thống tính lại thành tiền ngay.
3. Hiển thị mức chiết khấu tổng và cảnh báo khi chạm ngưỡng cần duyệt.
4. Khai báo hiệu lực báo giá, điều khoản thanh toán và điều khoản giao hàng.
5. Lưu nháp và sửa tiếp được.
"""

# Mã Jira Ticket & Epic
TICKET_ID = "SCRUM-31"
PARENT_EPIC = "SCRUM-35"
DEFAULT_PORT = 5000

# Trạng thái Báo giá (Quotation Statuses)
STATUS_DRAFT = "DRAFT"                      # Lưu nháp (Có thể sửa tiếp)
STATUS_PENDING_APPROVAL = "PENDING_APPROVAL"# Chờ duyệt chiết khấu (Vượt ngưỡng)
STATUS_APPROVED = "APPROVED"                # Đã duyệt chiết khấu
STATUS_SENT = "SENT"                        # Đã gửi khách hàng
STATUS_ACCEPTED = "ACCEPTED"                # Khách hàng đồng ý / Chốt hợp đồng
STATUS_REJECTED = "REJECTED"                # Bị từ chối duyệt
STATUS_EXPIRED = "EXPIRED"                  # Hết hiệu lực

STATUS_LABELS = {
    STATUS_DRAFT: "Bản nháp (Sửa tiếp được) 📝",
    STATUS_PENDING_APPROVAL: "Chờ duyệt chiết khấu ⚠️",
    STATUS_APPROVED: "Đã duyệt chiết khấu ✅",
    STATUS_SENT: "Đã gửi khách hàng 📤",
    STATUS_ACCEPTED: "Khách chấp nhận 🎉",
    STATUS_REJECTED: "Từ chối duyệt ❌",
    STATUS_EXPIRED: "Hết hiệu lực ⏱️"
}

STATUS_COLORS = {
    STATUS_DRAFT: "#64748b",           # Slate grey
    STATUS_PENDING_APPROVAL: "#f59e0b", # Amber
    STATUS_APPROVED: "#10b981",         # Emerald green
    STATUS_SENT: "#3b82f6",             # Blue
    STATUS_ACCEPTED: "#059669",         # Forest green
    STATUS_REJECTED: "#ef4444",         # Red
    STATUS_EXPIRED: "#94a3b8"           # Light grey
}

STATUS_BADGE_CLASSES = {
    STATUS_DRAFT: "badge-slate",
    STATUS_PENDING_APPROVAL: "badge-amber",
    STATUS_APPROVED: "badge-green",
    STATUS_SENT: "badge-blue",
    STATUS_ACCEPTED: "badge-emerald",
    STATUS_REJECTED: "badge-red",
    STATUS_EXPIRED: "badge-grey"
}

# Ngưỡng phê duyệt chiết khấu (Approval Thresholds)
# AC3: Hiển thị mức chiết khấu tổng và cảnh báo khi chạm ngưỡng cần duyệt
DISCOUNT_APPROVAL_THRESHOLD_PERCENT = 10.0   # Ngưỡng bắt buộc duyệt: >= 10.0%
DISCOUNT_WARNING_THRESHOLD_PERCENT = 8.0     # Cảnh báo sớm mức cận kề: >= 8.0%

# Loại chiết khấu dòng (Line Discount Types)
# AC2: Mỗi dòng nhập chiết khấu theo phần trăm hoặc số tiền
DISCOUNT_TYPE_PERCENT = "PERCENT"  # Chiết khấu theo %
DISCOUNT_TYPE_AMOUNT = "AMOUNT"    # Chiết khấu theo số tiền cố định (VNĐ)

DISCOUNT_TYPE_LABELS = {
    DISCOUNT_TYPE_PERCENT: "Phần trăm (%)",
    DISCOUNT_TYPE_AMOUNT: "Số tiền (VNĐ)"
}

# Thuế suất VAT mặc định
DEFAULT_VAT_PERCENT = 8.0  # VAT 8% (hoặc 10%)

# Mẫu Thời hạn hiệu lực báo giá (Validity Presets)
# AC4: Khai báo hiệu lực báo giá
VALIDITY_PRESETS = [
    {"days": 3, "label": "3 ngày (Báo giá nhanh trong ngày)"},
    {"days": 7, "label": "7 ngày (1 tuần)"},
    {"days": 15, "label": "15 ngày (Khuyến nghị)"},
    {"days": 30, "label": "30 ngày (1 tháng)"},
    {"days": 60, "label": "60 ngày (Dự án lớn)"}
]

# Mẫu Điều khoản thanh toán (Payment Terms Presets)
# AC4: Điều khoản thanh toán
PAYMENT_TERMS_PRESETS = [
    "Tạm ứng 50% khi ký hợp đồng, 50% còn lại trong vòng 15 ngày sau khi bàn giao nghiệm thu.",
    "Thanh toán 100% trước khi giao hàng hoặc kích hoạt bản quyền hệ thống.",
    "Thanh toán trả chậm 100% trong vòng 30 ngày (Net 30) kể từ ngày nhận đủ hóa đơn GTGT hợp lệ.",
    "Thanh toán chia 3 đợt: 40% đặt cọc - 40% khi giao hàng - 20% sau khi nghiệm thu và bàn giao tài liệu.",
    "Thanh toán theo hình thức trả góp định kỳ hàng tháng qua chuyển khoản doanh nghiệp."
]

# Mẫu Điều khoản giao hàng (Delivery Terms Presets)
# AC4: Điều khoản giao hàng
DELIVERY_TERMS_PRESETS = [
    "Bàn giao tài khoản và kích hoạt bản quyền trực tuyến qua Email trong vòng 04 giờ làm việc.",
    "Giao hàng và cài đặt tận nơi miễn phí trong vòng 24 - 48 giờ làm việc tại nội thành.",
    "Triển khai lắp đặt và cấu hình hệ thống tại trụ sở khách hàng trong 07 ngày làm việc kể từ ngày tạm ứng.",
    "Giao hàng tại kho bên mua (DDP), bên bán chịu mọi chi phí vận chuyển, bốc dỡ và bảo hiểm hàng hóa.",
    "Cung cấp gói dịch vụ đào tạo chuyển giao công nghệ trực tiếp trong 03 buổi làm việc."
]

# Các vai trò người dùng (User Roles)
ROLE_SALES_REP = "SALES_REP"        # Nhân viên kinh doanh (Soạn báo giá, lưu nháp, gửi khách)
ROLE_TEAM_LEAD = "TEAM_LEAD"        # Trưởng nhóm kinh doanh (Duyệt chiết khấu vượt ngưỡng)
ROLE_DIRECTOR = "DIRECTOR"          # Giám đốc kinh doanh (Thẩm quyền cao nhất)

ROLE_LABELS = {
    ROLE_SALES_REP: "Nhân viên kinh doanh",
    ROLE_TEAM_LEAD: "Trưởng nhóm kinh doanh",
    ROLE_DIRECTOR: "Giám đốc kinh doanh"
}

# Danh mục sản phẩm chuẩn (Product Catalog) để nhân viên thêm vào báo giá (AC1)
PRODUCT_CATALOG = [
    {
        "id": "PRD-001",
        "code": "CRM-ENTERPRISE",
        "name": "Bản quyền AutoLead CRM Enterprise (Gói 1 năm / 20 users)",
        "unit": "Gói / Năm",
        "price": 24000000,
        "category": "Phần mềm",
        "description": "Quản lý Lead, Cơ hội, Báo giá, Hợp đồng & Tự động hóa bán hàng đa kênh"
    },
    {
        "id": "PRD-002",
        "code": "CRM-USER-ADD",
        "name": "Tài khoản người dùng bổ sung (Add-on User License)",
        "unit": "User / Năm",
        "price": 1200000,
        "category": "Phần mềm",
        "description": "Bản quyền sử dụng phần mềm cho 01 nhân viên kinh doanh trong 12 tháng"
    },
    {
        "id": "PRD-003",
        "code": "SRV-IMPL-ONBOARD",
        "name": "Dịch vụ Thiết lập Quy trình & Onboarding Chuyên sâu",
        "unit": "Gói",
        "price": 15000000,
        "category": "Dịch vụ",
        "description": "Khảo sát luồng nghiệp vụ thực tế, tùy biến trường dữ liệu, đào tạo 03 buổi trực tiếp"
    },
    {
        "id": "PRD-004",
        "code": "SRV-INTEGRATION",
        "name": "Gói Tích Hợp API Đa Kênh (Facebook Ads + Zalo OA + Website)",
        "unit": "Hệ thống",
        "price": 8000000,
        "category": "Dịch vụ",
        "description": "Kết nối Webhook đồng bộ Lead tự động về CRM trong thời gian thực < 3 giây"
    },
    {
        "id": "PRD-005",
        "code": "SRV-CLOUD-BACKUP",
        "name": "Hạ tầng Cloud Dedicated Server & Sao lưu tự động hàng ngày",
        "unit": "Năm",
        "price": 18000000,
        "category": "Hạ tầng",
        "description": "Máy chủ đám mây tốc độ cao tại Việt Nam, cam kết SLA 99.9% Uptime, SSL bảo mật"
    },
    {
        "id": "PRD-006",
        "code": "SRV-CUSTOM-DEV",
        "name": "Dịch vụ Tùy biến Báo cáo Phân tích Chuyên biệt theo yêu cầu",
        "unit": "Man-day",
        "price": 3500000,
        "category": "Dịch vụ",
        "description": "Lập trình Dashboard BI quản trị theo chỉ số KPI đặc thù của doanh nghiệp"
    }
]

# Cấu hình mở rộng - CORS & API chuẩn hóa
ENABLE_CORS = True
CORS_ORIGINS = ['*']
DEFAULT_PAGE_SIZE = 20
API_VERSION = 'v1.2.0'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Validation SKU rules
VALID_SKU_PREFIXES = ['PRD', 'SRV', 'LIC', 'PKG']
MIN_PRODUCT_NAME_LENGTH = 3

# Helper formatting
CURRENCY_SYMBOL = '₫'
LOCALE_CODE = 'vi_VN'
