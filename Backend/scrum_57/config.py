"""
Cấu hình hệ thống - SCRUM-36 / SCRUM-57
User Story: "Là Chăm sóc khách hàng, tôi muốn xem dòng thời gian tương tác đầy đủ của một khách hàng,
để tiếp nhận khách từ đồng nghiệp mà nắm được bối cảnh trong năm phút."

Tiêu chí chấp nhận:
1. Gộp toàn bộ hoạt động, thay đổi cơ hội, báo giá đã gửi theo thứ tự thời gian.
2. Lọc theo loại hoạt động và theo người thực hiện.
"""

TICKET_ID = "SCRUM-57"
PARENT_EPIC = "SCRUM-36"

# -----------------------------------------------------------------------------
# Nguồn dữ liệu gốc được gộp vào dòng thời gian
# -----------------------------------------------------------------------------
SOURCE_ACTIVITY = "ACTIVITY"          # Hoạt động (gọi, email, họp, ghi chú, tin nhắn)
SOURCE_OPPORTUNITY = "OPPORTUNITY"    # Thay đổi cơ hội bán hàng
SOURCE_QUOTE = "QUOTE"                # Báo giá đã gửi

SOURCE_LABELS = {
    SOURCE_ACTIVITY: "Hoạt động",
    SOURCE_OPPORTUNITY: "Thay đổi cơ hội",
    SOURCE_QUOTE: "Báo giá đã gửi",
}

# -----------------------------------------------------------------------------
# Loại sự kiện trên dòng thời gian (dùng cho bộ lọc "loại hoạt động")
# -----------------------------------------------------------------------------
TYPE_CALL = "CALL"
TYPE_EMAIL = "EMAIL"
TYPE_MEETING = "MEETING"
TYPE_MESSAGE = "MESSAGE"
TYPE_NOTE = "NOTE"
TYPE_OPPORTUNITY = "OPPORTUNITY_CHANGE"
TYPE_QUOTE = "QUOTE_SENT"

ACTIVITY_TYPES = [TYPE_CALL, TYPE_EMAIL, TYPE_MEETING, TYPE_MESSAGE, TYPE_NOTE]

EVENT_TYPES = ACTIVITY_TYPES + [TYPE_OPPORTUNITY, TYPE_QUOTE]

EVENT_TYPE_LABELS = {
    TYPE_CALL: "Cuộc gọi",
    TYPE_EMAIL: "Email",
    TYPE_MEETING: "Cuộc họp",
    TYPE_MESSAGE: "Tin nhắn Zalo/SMS",
    TYPE_NOTE: "Ghi chú nội bộ",
    TYPE_OPPORTUNITY: "Thay đổi cơ hội",
    TYPE_QUOTE: "Báo giá đã gửi",
}

EVENT_TYPE_ICONS = {
    TYPE_CALL: "📞",
    TYPE_EMAIL: "✉️",
    TYPE_MEETING: "🤝",
    TYPE_MESSAGE: "💬",
    TYPE_NOTE: "📝",
    TYPE_OPPORTUNITY: "📈",
    TYPE_QUOTE: "🧾",
}

# Lớp màu CSS cho từng loại sự kiện
EVENT_TYPE_COLORS = {
    TYPE_CALL: "c-call",
    TYPE_EMAIL: "c-email",
    TYPE_MEETING: "c-meeting",
    TYPE_MESSAGE: "c-message",
    TYPE_NOTE: "c-note",
    TYPE_OPPORTUNITY: "c-opp",
    TYPE_QUOTE: "c-quote",
}

# -----------------------------------------------------------------------------
# Cơ hội bán hàng
# -----------------------------------------------------------------------------
OPP_FIELD_STAGE = "stage"
OPP_FIELD_AMOUNT = "amount"
OPP_FIELD_PROBABILITY = "probability"
OPP_FIELD_OWNER = "owner"
OPP_FIELD_CREATED = "created"

OPP_FIELD_LABELS = {
    OPP_FIELD_STAGE: "Giai đoạn",
    OPP_FIELD_AMOUNT: "Giá trị dự kiến",
    OPP_FIELD_PROBABILITY: "Xác suất thắng",
    OPP_FIELD_OWNER: "Người phụ trách",
    OPP_FIELD_CREATED: "Tạo cơ hội",
}

OPP_STAGE_LABELS = {
    "PROSPECTING": "Tìm hiểu nhu cầu",
    "QUALIFICATION": "Đánh giá",
    "PROPOSAL": "Gửi đề xuất",
    "NEGOTIATION": "Đàm phán",
    "CLOSED_WON": "Thắng 🏆",
    "CLOSED_LOST": "Thua",
}

# -----------------------------------------------------------------------------
# Báo giá
# -----------------------------------------------------------------------------
QUOTE_STATUS_LABELS = {
    "SENT": "Đã gửi",
    "VIEWED": "Khách đã xem",
    "ACCEPTED": "Khách chấp nhận",
    "REJECTED": "Khách từ chối",
    "EXPIRED": "Hết hạn",
}

# -----------------------------------------------------------------------------
# Vai trò
# -----------------------------------------------------------------------------
ROLE_CS = "CUSTOMER_SERVICE"
ROLE_SALES = "SALES_REP"
ROLE_MANAGER = "MANAGER"

ROLE_LABELS = {
    ROLE_CS: "Chăm sóc khách hàng",
    ROLE_SALES: "Nhân viên kinh doanh",
    ROLE_MANAGER: "Trưởng nhóm",
}

# Thứ tự sắp xếp
ORDER_DESC = "desc"   # Mới nhất trước (mặc định - phù hợp khi tiếp nhận khách)
ORDER_ASC = "asc"     # Cũ nhất trước (đọc lại câu chuyện từ đầu)

DEFAULT_PORT = 5057
