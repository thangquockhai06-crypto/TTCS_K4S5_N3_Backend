"""
Cấu hình hệ thống - SCRUM-35 / SCRUM-37
User Story: "Là Nhân viên kinh doanh, tôi muốn quản lý nhiều phiên bản của một báo giá, để biết chính xác đã cam kết gì với khách ở lần gửi trước."

Đáp ứng 3 Tiêu chí chấp nhận (Acceptance Criteria):
1. Mỗi lần sửa sau khi đã gửi sẽ tạo phiên bản mới, phiên bản cũ được giữ nguyên.
2. So sánh cạnh nhau hai phiên bản để thấy đã thay đổi gì.
3. Chỉ một phiên bản ở trạng thái đang hiệu lực tại một thời điểm.

Subtasks:
- SCRUM-234: Frontend (Giao diện Quản lý phiên bản, So sánh Side-by-side & Kích hoạt hiệu lực)
- SCRUM-235: Backend (Động cơ Phiên bản hóa, Diff Engine, Ràng buộc 1 phiên bản hiệu lực & Audit Snapshot)
"""

import os

# Thông tin Jira Ticket & Subtasks
TICKET_ID = "SCRUM-37"
PARENT_EPIC = "SCRUM-35"
SUBTASK_FE = "SCRUM-234"
SUBTASK_BE = "SCRUM-235"
DEFAULT_PORT = 5003

# Vai trò người dùng (User Roles)
ROLE_SALES_REP = "SALES_REP"          # Nhân viên kinh doanh (Chủ trì báo giá & quản lý phiên bản)
ROLE_SALES_LEAD = "SALES_LEAD"        # Trưởng nhóm kinh doanh
ROLE_CUSTOMER = "CUSTOMER"            # Khách hàng tiếp nhận báo giá

ROLE_LABELS = {
    ROLE_SALES_REP: "Nhân viên kinh doanh",
    ROLE_SALES_LEAD: "Trưởng nhóm kinh doanh",
    ROLE_CUSTOMER: "Khách hàng"
}

ROLE_AVATARS = {
    ROLE_SALES_REP: "👨‍💼",
    ROLE_SALES_LEAD: "👔",
    ROLE_CUSTOMER: "🏢"
}

# Trạng thái Báo giá (Quotation Statuses)
STATUS_DRAFT = "DRAFT"                # Bản nháp (Đang soạn thảo, có thể sửa trực tiếp)
STATUS_SENT = "SENT"                  # Đã gửi cho khách (ĐÓNG BĂNG - Sửa sẽ sinh phiên bản mới)
STATUS_ACCEPTED = "ACCEPTED"          # Khách hàng đã chấp thuận cam kết
STATUS_SUPERSEDED = "SUPERSEDED"      # Hết hiệu lực (Đã bị thay thế bởi phiên bản mới hơn)
STATUS_REJECTED = "REJECTED"          # Khách hàng từ chối

STATUS_LABELS = {
    STATUS_DRAFT: "Bản nháp 📝",
    STATUS_SENT: "Đã gửi khách 📤",
    STATUS_ACCEPTED: "Khách chấp thuận ✅",
    STATUS_SUPERSEDED: "Đã bị thay thế 🔄",
    STATUS_REJECTED: "Khách từ chối ❌"
}

STATUS_BADGE_CLASSES = {
    STATUS_DRAFT: "badge-draft",
    STATUS_SENT: "badge-sent",
    STATUS_ACCEPTED: "badge-accepted",
    STATUS_SUPERSEDED: "badge-superseded",
    STATUS_REJECTED: "badge-rejected"
}

# Thuế VAT mặc định
DEFAULT_VAT_PERCENT = 10.0

# Danh mục lý do cập nhật phiên bản báo giá
REVISION_REASONS = [
    "Khách hàng yêu cầu đàm phán giảm giá thêm",
    "Điều chỉnh số lượng bản quyền người dùng",
    "Bổ sung gói dịch vụ bảo trì 24/7 và triển khai",
    "Cập nhật lại điều khoản thanh toán & tiến độ giao hàng",
    "Thay đổi cấu hình sản phẩm theo khảo sát kỹ thuật mới",
    "Gia hạn thời hạn hiệu lực của báo giá"
]

# Danh mục sản phẩm mẫu phục vụ báo giá CPQ
PRODUCT_CATALOG = [
    {
        "id": "PROD-CRM-ENT",
        "name": "AutoLead CRM Enterprise (Gói Doanh Nghiệp)",
        "unit": "Gói/Năm",
        "unit_price": 24000000,
        "description": "Bản quyền 50 người dùng, tích hợp AI phân tích lead & API mở"
    },
    {
        "id": "PROD-CRM-PRO",
        "name": "AutoLead CRM Professional (Gói Tiêu Chuẩn)",
        "unit": "Gói/Năm",
        "unit_price": 12000000,
        "description": "Bản quyền 20 người dùng, quản lý pipeline và báo giá cơ bản"
    },
    {
        "id": "PROD-CPQ-MOD",
        "name": "Module CPQ Nâng Cao & Quản Lý Phiên Bản Báo Giá",
        "unit": "Module",
        "unit_price": 8500000,
        "description": "Tự động so sánh phiên bản, khóa snapshot và cảnh báo giá sàn"
    },
    {
        "id": "PROD-IMPL-SRV",
        "name": "Dịch Vụ Triển Khai & Đào Tạo Người Dùng On-site",
        "unit": "Gói",
        "unit_price": 15000000,
        "description": "Chuyên gia cấu hình quy trình tại văn phòng khách hàng trong 10 ngày"
    },
    {
        "id": "PROD-MAINT-247",
        "name": "Gói Hỗ Trợ Kỹ Thuật VIP & SLA 1 Giờ (1 Năm)",
        "unit": "Năm",
        "unit_price": 6000000,
        "description": "Hotline hỗ trợ 24/7, cam kết thời gian phản hồi sự cố dưới 60 phút"
    },
    {
        "id": "PROD-ZNS-GATEWAY",
        "name": "Cổng Tích Hợp Zalo ZNS & Hóa Đơn Điện Tử",
        "unit": "Gói",
        "unit_price": 4500000,
        "description": "Kết nối gửi báo giá, hóa đơn và nhắc nợ tự động qua Zalo OA"
    }
]

# Điều khoản thanh toán mẫu
PAYMENT_TERMS_OPTIONS = [
    "Thanh toán 100% ngay sau khi ký hợp đồng",
    "Tạm ứng 50% khi ký hợp đồng, 50% sau khi nghiệm thu bàn giao",
    "Tạm ứng 30% khi ký, 40% sau khi cài đặt, 30% sau khi đào tạo",
    "Thanh toán định kỳ hàng tháng sau khi nhận hóa đơn điện tử",
    "Thanh toán chuyển khoản trong vòng 15 ngày làm việc kể từ ngày giao hàng"
]

# Điều khoản giao hàng mẫu
DELIVERY_TERMS_OPTIONS = [
    "Bàn giao tài khoản hệ thống trong vòng 24 giờ sau khi thanh toán",
    "Triển khai và cài đặt hoàn tất trong vòng 07 ngày làm việc",
    "Bàn giao hệ thống trong 15 ngày làm việc kèm biên bản nghiệm thu kỹ thuật",
    "Giao hàng tận nơi tại trụ sở khách hàng kèm hướng dẫn sử dụng"
]
