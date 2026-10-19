"""
Cấu hình hệ thống - SCRUM-35 / SCRUM-38
User Story: "Là Kế toán, tôi muốn chuyển một báo giá được chấp nhận thành hợp đồng, để số liệu hợp đồng khớp báo giá mà không phải gõ lại."

4 Tiêu chí chấp nhận (Acceptance Criteria):
1. Hợp đồng kế thừa toàn bộ dòng sản phẩm và giá đã chốt, không nhập lại.
2. Khai báo số hợp đồng, ngày ký, ngày hiệu lực, ngày hết hạn, điều khoản thanh toán.
3. Cơ hội tương ứng tự động chuyển sang Đóng thắng với giá trị đúng bằng giá trị hợp đồng.
4. Số hợp đồng là duy nhất.

Subtasks:
- SCRUM-236: Frontend (Giao diện chuyển đổi Báo giá -> Hợp đồng, Form khai báo pháp lý & Quản lý hợp đồng)
- SCRUM-237: Backend (Động cơ kế thừa số liệu Báo giá, Ràng buộc số HĐ Unique & Đồng bộ Cơ hội Đóng Thắng)
"""

import os

# Thông tin Jira Ticket & Subtasks
TICKET_ID = "SCRUM-38"
PARENT_EPIC = "SCRUM-35"
SUBTASK_FE = "SCRUM-236"
SUBTASK_BE = "SCRUM-237"
DEFAULT_PORT = 5004

# Vai trò người dùng (User Roles)
ROLE_ACCOUNTANT = "ACCOUNTANT"        # Kế toán viên (Chủ thể thực hiện chuyển báo giá thành hợp đồng)
ROLE_SALES_REP = "SALES_REP"          # Nhân viên kinh doanh (Phụ trách cơ hội & gửi báo giá)
ROLE_SALES_LEAD = "SALES_LEAD"        # Trưởng nhóm kinh doanh
ROLE_DIRECTOR = "DIRECTOR"            # Giám đốc (Ký duyệt hợp đồng)

ROLE_LABELS = {
    ROLE_ACCOUNTANT: "Kế toán viên",
    ROLE_SALES_REP: "Nhân viên kinh doanh",
    ROLE_SALES_LEAD: "Trưởng nhóm kinh doanh",
    ROLE_DIRECTOR: "Giám đốc"
}

ROLE_AVATARS = {
    ROLE_ACCOUNTANT: "👩‍💼",
    ROLE_SALES_REP: "👨‍💼",
    ROLE_SALES_LEAD: "👔",
    ROLE_DIRECTOR: "🏛️"
}

# Trạng thái Báo giá (Quotation Statuses)
QUOTE_STATUS_DRAFT = "DRAFT"                # Bản nháp (Không thể chuyển hợp đồng)
QUOTE_STATUS_SENT = "SENT"                  # Đã gửi cho khách (Đang chờ khách phản hồi)
QUOTE_STATUS_ACCEPTED = "ACCEPTED"          # Khách chấp thuận (ĐỦ ĐIỀU KIỆN chuyển thành hợp đồng)
QUOTE_STATUS_CONVERTED = "CONVERTED"        # Đã chuyển thành hợp đồng thành công
QUOTE_STATUS_REJECTED = "REJECTED"          # Khách từ chối

QUOTE_STATUS_LABELS = {
    QUOTE_STATUS_DRAFT: "Bản nháp 📝",
    QUOTE_STATUS_SENT: "Đã gửi khách 📤",
    QUOTE_STATUS_ACCEPTED: "Đã chấp nhận ✅",
    QUOTE_STATUS_CONVERTED: "Đã lập hợp đồng 📑",
    QUOTE_STATUS_REJECTED: "Khách từ chối ❌"
}

QUOTE_STATUS_BADGES = {
    QUOTE_STATUS_DRAFT: "badge-draft",
    QUOTE_STATUS_SENT: "badge-sent",
    QUOTE_STATUS_ACCEPTED: "badge-accepted",
    QUOTE_STATUS_CONVERTED: "badge-converted",
    QUOTE_STATUS_REJECTED: "badge-rejected"
}

# Giai đoạn Cơ hội kinh doanh (Opportunity Stages)
OPP_STAGE_QUALIFIED = "QUALIFIED"            # Tiềm năng
OPP_STAGE_PROPOSAL = "PROPOSAL"              # Gửi đề xuất / Báo giá
OPP_STAGE_NEGOTIATION = "NEGOTIATION"        # Đang đàm phán hợp đồng
OPP_STAGE_CLOSED_WON = "CLOSED_WON"          # Đóng thắng 🎉 (Ký hợp đồng thành công)
OPP_STAGE_CLOSED_LOST = "CLOSED_LOST"        # Đóng thua ❌

OPP_STAGE_LABELS = {
    OPP_STAGE_QUALIFIED: "Tiềm năng xác định 🎯",
    OPP_STAGE_PROPOSAL: "Đã gửi báo giá 📨",
    OPP_STAGE_NEGOTIATION: "Đang đàm phán 💬",
    OPP_STAGE_CLOSED_WON: "Đóng thắng 🎉",
    OPP_STAGE_CLOSED_LOST: "Đóng thua ❌"
}

OPP_STAGE_BADGES = {
    OPP_STAGE_QUALIFIED: "badge-opp-qualified",
    OPP_STAGE_PROPOSAL: "badge-opp-proposal",
    OPP_STAGE_NEGOTIATION: "badge-opp-negotiation",
    OPP_STAGE_CLOSED_WON: "badge-opp-won",
    OPP_STAGE_CLOSED_LOST: "badge-opp-lost"
}

# Trạng thái Hợp đồng (Contract Statuses)
CONTRACT_STATUS_ACTIVE = "ACTIVE"            # Đang hiệu lực
CONTRACT_STATUS_EXPIRED = "EXPIRED"          # Hết hiệu lực
CONTRACT_STATUS_TERMINATED = "TERMINATED"    # Đã chấm dứt / Thanh lý

CONTRACT_STATUS_LABELS = {
    CONTRACT_STATUS_ACTIVE: "Đang hiệu lực 🟢",
    CONTRACT_STATUS_EXPIRED: "Hết hiệu lực ⏱️",
    CONTRACT_STATUS_TERMINATED: "Đã thanh lý 📄"
}

CONTRACT_STATUS_BADGES = {
    CONTRACT_STATUS_ACTIVE: "badge-contract-active",
    CONTRACT_STATUS_EXPIRED: "badge-contract-expired",
    CONTRACT_STATUS_TERMINATED: "badge-contract-terminated"
}

# Danh mục điều khoản thanh toán mẫu (Payment Terms Options)
PAYMENT_TERMS_OPTIONS = [
    {
        "id": "TERM_FULL_7D",
        "name": "Thanh toán 100% trong vòng 7 ngày làm việc sau khi ký",
        "description": "Bên Mua chuyển khoản toàn bộ 100% giá trị hợp đồng trong 07 ngày làm việc kể từ ngày hợp đồng có hiệu lực."
    },
    {
        "id": "TERM_50_50",
        "name": "Đợt 1: 50% khi ký hợp đồng - Đợt 2: 50% khi bàn giao nghiệm thu",
        "description": "Đợt 1: Tạm ứng 50% trong 05 ngày sau ký. Đợt 2: Thanh toán 50% còn lại trong 07 ngày sau khi ký biên bản bàn giao nghiệm thu."
    },
    {
        "id": "TERM_30_40_30",
        "name": "Đợt 1: 30% khi ký - Đợt 2: 40% khi cài đặt - Đợt 3: 30% khi nghiệm thu",
        "description": "Chia thành 3 đợt: Tạm ứng 30% khi ký, 40% khi triển khai hoàn tất môi trường, 30% sau khi ký biên bản nghiệm thu tổng thể."
    },
    {
        "id": "TERM_NET_30",
        "name": "Trả chậm trong vòng 30 ngày kể từ ngày xuất hóa đơn VAT (Net 30)",
        "description": "Bên Bán phát hành hóa đơn tài chính VAT hợp lệ, Bên Mua có trách nhiệm thanh toán đủ trong vòng 30 ngày dương lịch."
    },
    {
        "id": "TERM_MONTHLY",
        "name": "Thanh toán theo định kỳ hàng tháng (vào ngày 05 mỗi tháng)",
        "description": "Thanh toán định kỳ hàng tháng cho gói thuê bao SaaS, thực hiện vào ngày 05 của tháng sử dụng dịch vụ."
    }
]

# Thông tin Doanh nghiệp phát hành (Bên Bán - AutoLead Solutions)
SELLER_INFO = {
    "company_name": "CÔNG TY CỔ PHẦN CÔNG NGHỆ AUTOLEAD CRM VIỆT NAM",
    "tax_code": "0109887766",
    "address": "Tầng 18, Tòa nhà Landmark 72, Đường Phạm Hùng, Q. Nam Từ Liêm, TP. Hà Nội",
    "phone": "024.7300.8888",
    "email": "finance@autolead-crm.vn",
    "representative": "Ông Nguyễn Mạnh Cường",
    "position": "Giám đốc điều hành (CEO)",
    "bank_name": "Ngân hàng TMCP Ngoại Thương Việt Nam (Vietcombank) - Chi nhánh Thăng Long",
    "bank_account": "101889988999"
}

# Thuế suất VAT mặc định
DEFAULT_VAT_PERCENT = 10.0

# Legal signatories
DEFAULT_LEGAL_REPRESENTATIVE = 'Nguyễn Văn Giám Đốc'
DEFAULT_LEGAL_POSITION = 'Tổng Giám Đốc Điều Hành'

# Contract query performance
CONTRACT_LIST_PAGE_SIZE = 25
