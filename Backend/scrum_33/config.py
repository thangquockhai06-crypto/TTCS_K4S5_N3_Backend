"""
Cấu hình hệ thống - SCRUM-35 / SCRUM-33
User Story: "Là Trưởng nhóm kinh doanh, tôi muốn duyệt báo giá theo mức chiết khấu, để kiểm soát biên lợi nhuận mà không phải trả lời từng tin nhắn xin giảm giá."

5 Tiêu chí chấp nhận (Acceptance Criteria):
1. Chiết khấu dưới ngưỡng thứ nhất thì tự động thông qua, không cần duyệt.
2. Vượt ngưỡng thứ nhất do Trưởng nhóm duyệt; vượt ngưỡng thứ hai hoặc dưới giá sàn thì bắt buộc Giám đốc kinh doanh duyệt.
3. Ba hành động: Duyệt, Từ chối, Trả lại sửa — hai hành động sau bắt buộc nhập ý kiến.
4. Chỉ báo giá đã duyệt mới gửi được cho khách.
5. Lịch sử duyệt không sửa và không xoá được.
"""

# Mã Jira Ticket & Subtasks
TICKET_ID = "SCRUM-33"
PARENT_EPIC = "SCRUM-35"
SUBTASK_FE = "SCRUM-232"
SUBTASK_BE = "SCRUM-233"
DEFAULT_PORT = 5002

# Vai trò người dùng (User Roles)
ROLE_SALES_REP = "SALES_REP"          # Nhân viên kinh doanh (Soạn và gửi báo giá)
ROLE_TEAM_LEAD = "TEAM_LEAD"          # Trưởng nhóm kinh doanh (Duyệt chiết khấu ngưỡng 1)
ROLE_DIRECTOR = "DIRECTOR"            # Giám đốc kinh doanh (Duyệt chiết khấu ngưỡng 2 & dưới giá sàn)
ROLE_SYSTEM = "SYSTEM"                # Hệ thống tự động (Tự động duyệt dưới ngưỡng 1)

ROLE_LABELS = {
    ROLE_SALES_REP: "Nhân viên kinh doanh",
    ROLE_TEAM_LEAD: "Trưởng nhóm kinh doanh",
    ROLE_DIRECTOR: "Giám đốc kinh doanh",
    ROLE_SYSTEM: "Hệ thống tự động"
}

ROLE_AVATARS = {
    ROLE_SALES_REP: "👨‍💼",
    ROLE_TEAM_LEAD: "👔",
    ROLE_DIRECTOR: "👑",
    ROLE_SYSTEM: "🤖"
}

# Các ngưỡng chiết khấu phê duyệt (Discount Approval Thresholds)
# AC1: Chiết khấu dưới ngưỡng thứ nhất (< 10.0%) -> Tự động thông qua
THRESHOLD_1_PERCENT = 10.0   # Ngưỡng thứ nhất: 10.0%

# AC2: Vượt ngưỡng 1 (>= 10.0% và <= 20.0%) -> Trưởng nhóm duyệt
# Vượt ngưỡng 2 (> 20.0%) hoặc dưới giá sàn -> Giám đốc duyệt
THRESHOLD_2_PERCENT = 20.0   # Ngưỡng thứ hai: 20.0%

# Trạng thái Báo giá (Quotation Statuses)
STATUS_DRAFT = "DRAFT"                            # Bản nháp (Đang soạn)
STATUS_PENDING_APPROVAL = "PENDING_APPROVAL"      # Chờ phê duyệt chiết khấu
STATUS_APPROVED = "APPROVED"                      # Đã phê duyệt (Có thể gửi khách)
STATUS_CHANGES_REQUESTED = "CHANGES_REQUESTED"    # Trả lại sửa (Yêu cầu NVKD chỉnh sửa)
STATUS_REJECTED = "REJECTED"                      # Bị từ chối duyệt
STATUS_SENT = "SENT"                              # Đã gửi cho khách hàng

STATUS_LABELS = {
    STATUS_DRAFT: "Bản nháp 📝",
    STATUS_PENDING_APPROVAL: "Chờ phê duyệt ⏳",
    STATUS_APPROVED: "Đã duyệt ✅",
    STATUS_CHANGES_REQUESTED: "Trả lại sửa 🔄",
    STATUS_REJECTED: "Từ chối duyệt ❌",
    STATUS_SENT: "Đã gửi khách 📤"
}

STATUS_BADGE_CLASSES = {
    STATUS_DRAFT: "badge-slate",
    STATUS_PENDING_APPROVAL: "badge-amber",
    STATUS_APPROVED: "badge-emerald",
    STATUS_CHANGES_REQUESTED: "badge-blue",
    STATUS_REJECTED: "badge-rose",
    STATUS_SENT: "badge-indigo"
}

# Ba hành động phê duyệt (Approval Actions) - AC3
ACTION_APPROVE = "APPROVE"                     # Duyệt
ACTION_REJECT = "REJECT"                       # Từ chối (Bắt buộc ý kiến)
ACTION_REQUEST_CHANGES = "REQUEST_CHANGES"     # Trả lại sửa (Bắt buộc ý kiến)
ACTION_AUTO_APPROVE = "AUTO_APPROVE"           # Tự động duyệt (Hệ thống)
ACTION_SUBMIT = "SUBMIT"                       # NVKD Trình duyệt

ACTION_LABELS = {
    ACTION_APPROVE: "Duyệt báo giá",
    ACTION_REJECT: "Từ chối báo giá",
    ACTION_REQUEST_CHANGES: "Trả lại sửa",
    ACTION_AUTO_APPROVE: "Tự động thông qua",
    ACTION_SUBMIT: "Trình duyệt chiết khấu"
}

ACTION_ICONS = {
    ACTION_APPROVE: "✅",
    ACTION_REJECT: "❌",
    ACTION_REQUEST_CHANGES: "🔄",
    ACTION_AUTO_APPROVE: "⚡",
    ACTION_SUBMIT: "📤"
}

# Cấp thẩm quyền duyệt bắt buộc (Required Approval Authority) - AC1, AC2
AUTHORITY_AUTO = "AUTO"                        # Tự động duyệt (Dưới ngưỡng 1 & không dưới sàn)
AUTHORITY_TEAM_LEAD = ROLE_TEAM_LEAD           # Thẩm quyền Trưởng nhóm (Ngưỡng 1 -> Ngưỡng 2, không dưới sàn)
AUTHORITY_DIRECTOR = ROLE_DIRECTOR             # Thẩm quyền Giám đốc (Vượt ngưỡng 2 HOẶC dưới giá sàn)

AUTHORITY_LABELS = {
    AUTHORITY_AUTO: "Tự động thông qua (Không cần duyệt) ⚡",
    AUTHORITY_TEAM_LEAD: "Trưởng nhóm kinh doanh duyệt 👔",
    AUTHORITY_DIRECTOR: "Giám đốc kinh doanh duyệt (Bắt buộc) 👑"
}

AUTHORITY_BADGE_CLASSES = {
    AUTHORITY_AUTO: "badge-auto",
    AUTHORITY_TEAM_LEAD: "badge-team-lead",
    AUTHORITY_DIRECTOR: "badge-director"
}

# Danh mục sản phẩm chuẩn kèm GIÁ SÀN (Floor Price / Minimum Selling Price) - AC2
PRODUCT_CATALOG = [
    {
        "id": "PRD-001",
        "code": "CRM-ENTERPRISE",
        "name": "Bản quyền AutoLead CRM Enterprise (Gói 1 năm / 20 users)",
        "unit": "Gói / Năm",
        "list_price": 24000000,     # Giá niêm yết: 24 triệu
        "floor_price": 18000000,    # Giá sàn: 18 triệu (Tối đa giảm 25%)
        "category": "Phần mềm",
        "description": "Quản lý Lead, Cơ hội, Báo giá, Hợp đồng & Tự động hóa bán hàng"
    },
    {
        "id": "PRD-002",
        "code": "CRM-USER-ADD",
        "name": "Tài khoản người dùng bổ sung (Add-on User License)",
        "unit": "User / Năm",
        "list_price": 1200000,      # Giá niêm yết: 1.2 triệu
        "floor_price": 900000,      # Giá sàn: 900.000 đ (Tối đa giảm 25%)
        "category": "Phần mềm",
        "description": "Tài khoản truy cập đầy đủ tính năng bổ sung theo người dùng"
    },
    {
        "id": "PRD-003",
        "code": "SRV-IMPL-ONBOARD",
        "name": "Dịch vụ Thiết lập Quy trình & Onboarding Chuyên sâu",
        "unit": "Gói",
        "list_price": 10000000,     # Giá niêm yết: 10 triệu
        "floor_price": 7500000,     # Giá sàn: 7.5 triệu (Tối đa giảm 25%)
        "category": "Dịch vụ",
        "description": "Khảo sát, thiết lập phễu bán hàng, phân quyền và đào tạo tận nơi"
    },
    {
        "id": "PRD-004",
        "code": "AI-SALES-BOT",
        "name": "Mô-đun Trợ lý AI Bán hàng Thông minh (AI Copilot)",
        "unit": "Gói / Năm",
        "list_price": 15000000,     # Giá niêm yết: 15 triệu
        "floor_price": 12000000,    # Giá sàn: 12 triệu (Tối đa giảm 20%)
        "category": "Trí tuệ nhân tạo",
        "description": "Tự động phân loại lead, gợi ý kịch bản cuộc gọi & tóm tắt cơ hội"
    },
    {
        "id": "PRD-005",
        "code": "INT-ERP-CONNECTOR",
        "name": "Cổng tích hợp hệ thống ERP / Kế toán MISA, SAP",
        "unit": "Cổng",
        "list_price": 8000000,      # Giá niêm yết: 8 triệu
        "floor_price": 6000000,     # Giá sàn: 6 triệu (Tối đa giảm 25%)
        "category": "Tích hợp",
        "description": "Đồng bộ đơn hàng, báo giá và hóa đơn thời gian thực hai chiều"
    }
]

# Thuế VAT mặc định
DEFAULT_VAT_PERCENT = 8.0

# Extended approval threshold
DIRECTOR_APPROVAL_MIN_AMOUNT = 500000000 # 500M VND

# Indexing optimization configuration
ENABLE_COMPOSITE_INDEX_APPROVAL = True
