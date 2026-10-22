"""
Tầng dữ liệu & Động cơ dòng thời gian - SCRUM-36 / SCRUM-57

- Lưu trữ dữ liệu mẫu trong bộ nhớ (khách hàng, hoạt động, thay đổi cơ hội, báo giá).
- `build_timeline`: gộp 3 nguồn dữ liệu thành MỘT dòng thời gian chuẩn hóa,
  sắp xếp theo thời gian (Tiêu chí 1).
- Bộ lọc theo loại hoạt động & người thực hiện (Tiêu chí 2).
- `get_handover_summary`: tóm tắt bối cảnh để CSKH tiếp nhận khách trong 5 phút.
"""

import copy
from datetime import datetime, timedelta

from config import (
    SOURCE_ACTIVITY,
    SOURCE_OPPORTUNITY,
    SOURCE_QUOTE,
    TYPE_CALL,
    TYPE_EMAIL,
    TYPE_MEETING,
    TYPE_MESSAGE,
    TYPE_NOTE,
    TYPE_OPPORTUNITY,
    TYPE_QUOTE,
    ACTIVITY_TYPES,
    EVENT_TYPES,
    EVENT_TYPE_LABELS,
    EVENT_TYPE_ICONS,
    EVENT_TYPE_COLORS,
    OPP_FIELD_STAGE,
    OPP_FIELD_AMOUNT,
    OPP_FIELD_PROBABILITY,
    OPP_FIELD_OWNER,
    OPP_FIELD_CREATED,
    OPP_FIELD_LABELS,
    OPP_STAGE_LABELS,
    QUOTE_STATUS_LABELS,
    ROLE_CS,
    ROLE_SALES,
    ROLE_MANAGER,
    ROLE_LABELS,
    ORDER_ASC,
    ORDER_DESC,
)

# Thứ tự ưu tiên khi 2 sự kiện trùng đúng thời điểm (giữ kết quả ổn định)
_SOURCE_PRIORITY = {SOURCE_ACTIVITY: 0, SOURCE_OPPORTUNITY: 1, SOURCE_QUOTE: 2}

# Các loại tương tác trực tiếp với khách (dùng để tính "lần liên hệ gần nhất")
_CONTACT_TYPES = {TYPE_CALL, TYPE_EMAIL, TYPE_MEETING, TYPE_MESSAGE}


# =============================================================================
# HÀM ĐỊNH DẠNG
# =============================================================================
def format_currency(amount):
    if amount is None or amount == "":
        return "—"
    try:
        return f"{int(amount):,}".replace(",", ".") + " ₫"
    except (TypeError, ValueError):
        return str(amount)


def format_datetime(dt):
    if not dt:
        return "—"
    return dt.strftime("%H:%M - %d/%m/%Y")


def format_date(dt):
    if not dt:
        return "—"
    return dt.strftime("%d/%m/%Y")


def format_relative(dt, now=None):
    """Hiển thị thời gian tương đối dạng '3 giờ trước', '2 ngày trước'."""
    if not dt:
        return "—"
    now = now or datetime.now()
    delta = now - dt
    seconds = int(delta.total_seconds())
    if seconds < 0:
        future = -seconds
        if future < 3600:
            return f"sau {max(1, future // 60)} phút"
        if future < 86400:
            return f"sau {future // 3600} giờ"
        return f"sau {future // 86400} ngày"
    if seconds < 60:
        return "vừa xong"
    if seconds < 3600:
        return f"{seconds // 60} phút trước"
    if seconds < 86400:
        return f"{seconds // 3600} giờ trước"
    days = seconds // 86400
    if days < 30:
        return f"{days} ngày trước"
    if days < 365:
        return f"{days // 30} tháng trước"
    return f"{days // 365} năm trước"


def _format_opp_value(field, value):
    if value is None or value == "":
        return "—"
    if field == OPP_FIELD_STAGE:
        return OPP_STAGE_LABELS.get(value, value)
    if field == OPP_FIELD_AMOUNT:
        return format_currency(value)
    if field == OPP_FIELD_PROBABILITY:
        return f"{value}%"
    return str(value)


def _parse_multi(value):
    """Nhận None / chuỗi 'A,B' / list ['A', 'B,C'] → list giá trị duy nhất, giữ thứ tự."""
    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    result = []
    for item in value:
        if item is None:
            continue
        for part in str(item).split(","):
            part = part.strip()
            if part and part not in result:
                result.append(part)
    return result


# =============================================================================
# CƠ SỞ DỮ LIỆU TRONG BỘ NHỚ
# =============================================================================
class CRMDatabase:
    def __init__(self):
        self.reset_demo_data()

    # -------------------------------------------------------------------------
    # DỮ LIỆU MẪU
    # -------------------------------------------------------------------------
    def reset_demo_data(self, now=None):
        self.now = now or datetime.now().replace(second=0, microsecond=0)
        now = self.now

        def ago(days=0, hours=0, minutes=0):
            return now - timedelta(days=days, hours=hours, minutes=minutes)

        def ahead(days=0, hours=0):
            return now + timedelta(days=days, hours=hours)

        self.users = {
            "usr-cs1": {"id": "usr-cs1", "name": "Phạm Thu Hà", "role": ROLE_CS, "avatar": "👩‍💼"},
            "usr-cs2": {"id": "usr-cs2", "name": "Ngô Minh Tâm", "role": ROLE_CS, "avatar": "🧑‍💻"},
            "usr-s1": {"id": "usr-s1", "name": "Lê Hoàng Phúc", "role": ROLE_SALES, "avatar": "👨‍💼"},
            "usr-s2": {"id": "usr-s2", "name": "Vũ Hải Đăng", "role": ROLE_SALES, "avatar": "🧔"},
            "usr-m1": {"id": "usr-m1", "name": "Trần Thị Mai Phương", "role": ROLE_MANAGER, "avatar": "👩‍🏫"},
        }
        for u in self.users.values():
            u["role_name"] = ROLE_LABELS[u["role"]]

        self.customers = {
            "CUS-001": {
                "id": "CUS-001",
                "name": "Công ty TNHH Thực phẩm Sen Vàng",
                "contact_name": "Nguyễn Thị Hồng",
                "contact_title": "Giám đốc Mua hàng",
                "phone": "0903 456 789",
                "email": "hong.nguyen@senvang.vn",
                "segment": "Doanh nghiệp vừa",
                "address": "KCN Tân Bình, TP. Hồ Chí Minh",
                "cs_owner_id": "usr-cs2",
                "sales_owner_id": "usr-s1",
                "customer_since": ago(days=210),
            },
            "CUS-002": {
                "id": "CUS-002",
                "name": "Chuỗi Nhà thuốc An Khang Việt",
                "contact_name": "Trần Quốc Bảo",
                "contact_title": "Trưởng phòng CNTT",
                "phone": "0912 888 321",
                "email": "bao.tran@ankhangviet.vn",
                "segment": "Chuỗi bán lẻ",
                "address": "Cầu Giấy, Hà Nội",
                "cs_owner_id": "usr-cs2",
                "sales_owner_id": "usr-s2",
                "customer_since": ago(days=95),
            },
            "CUS-003": {
                "id": "CUS-003",
                "name": "Hợp tác xã Nông sản Đà Lạt Xanh",
                "contact_name": "Lâm Văn Đức",
                "contact_title": "Chủ nhiệm HTX",
                "phone": "0263 377 1122",
                "email": "duc.lam@dalatxanh.coop",
                "segment": "Doanh nghiệp nhỏ",
                "address": "Phường 8, Đà Lạt, Lâm Đồng",
                "cs_owner_id": "usr-cs1",
                "sales_owner_id": "usr-s2",
                "customer_since": ago(days=2),
            },
            "CUS-004": {
                "id": "CUS-004",
                "name": "Công ty CP Logistics Hải Âu",
                "contact_name": "Đặng Thùy Linh",
                "contact_title": "Phó Giám đốc Vận hành",
                "phone": "0236 365 7788",
                "email": "linh.dang@haiaulogistics.vn",
                "segment": "Doanh nghiệp lớn",
                "address": "Quận Hải Châu, Đà Nẵng",
                "cs_owner_id": "usr-cs1",
                "sales_owner_id": "usr-s1",
                "customer_since": ago(days=400),
            },
        }

        # ---------------------------------------------------------------------
        # 1) HOẠT ĐỘNG
        # ---------------------------------------------------------------------
        self.activities = [
            # ---- CUS-001: Sen Vàng (khách đang được bàn giao từ Tâm sang Hà) ----
            {"id": "ACT-001", "customer_id": "CUS-001", "type": TYPE_CALL, "performed_by": "usr-s1",
             "occurred_at": ago(days=45, hours=3), "subject": "Cuộc gọi khám phá nhu cầu",
             "content": "Khách cần phần mềm quản lý kho lạnh cho 3 kho tại HCM, đang dùng Excel, hay sai lệch tồn kho.",
             "outcome": "Quan tâm - hẹn demo", "duration_min": 18},
            {"id": "ACT-002", "customer_id": "CUS-001", "type": TYPE_MEETING, "performed_by": "usr-s1",
             "occurred_at": ago(days=40, hours=5), "subject": "Demo sản phẩm tại văn phòng khách",
             "content": "Demo module Kho lạnh & Truy xuất lô. Chị Hồng đánh giá cao cảnh báo nhiệt độ. Kế toán trưởng hỏi về tích hợp MISA.",
             "outcome": "Yêu cầu báo giá", "duration_min": 90},
            {"id": "ACT-003", "customer_id": "CUS-001", "type": TYPE_EMAIL, "performed_by": "usr-s1",
             "occurred_at": ago(days=37, hours=2), "subject": "Gửi tài liệu tích hợp MISA",
             "content": "Đã gửi tài liệu API và case study tích hợp MISA của khách hàng cùng ngành.",
             "outcome": "Đã gửi"},
            {"id": "ACT-004", "customer_id": "CUS-001", "type": TYPE_CALL, "performed_by": "usr-s1",
             "occurred_at": ago(days=30, hours=1), "subject": "Đàm phán giá & thời gian triển khai",
             "content": "Khách muốn giảm 10% và triển khai trong 4 tuần. Đồng ý giảm 7% nếu ký hợp đồng 2 năm.",
             "outcome": "Chờ khách phản hồi", "duration_min": 25},
            {"id": "ACT-005", "customer_id": "CUS-001", "type": TYPE_NOTE, "performed_by": "usr-s1",
             "occurred_at": ago(days=26, hours=4), "subject": "Bàn giao sang CSKH sau ký hợp đồng",
             "content": "Đã ký HĐ 2 năm. Người quyết định: chị Hồng. Người dùng chính: anh Khoa (thủ kho). Khách rất nhạy cảm về thời gian phản hồi.",
             "pinned": True},
            {"id": "ACT-006", "customer_id": "CUS-001", "type": TYPE_MEETING, "performed_by": "usr-cs2",
             "occurred_at": ago(days=21, hours=6), "subject": "Kick-off triển khai",
             "content": "Thống nhất lộ trình 4 tuần: tuần 1 cài đặt, tuần 2 nhập dữ liệu, tuần 3 đào tạo, tuần 4 go-live.",
             "outcome": "Đã chốt lộ trình", "duration_min": 60},
            {"id": "ACT-007", "customer_id": "CUS-001", "type": TYPE_MESSAGE, "performed_by": "usr-cs2",
             "occurred_at": ago(days=14, hours=2), "subject": "Zalo: anh Khoa báo lỗi in tem",
             "content": "Anh Khoa báo máy in tem Zebra không nhận mẫu tem mới. Đã hướng dẫn cập nhật driver, xử lý xong trong 20 phút.",
             "outcome": "Đã xử lý"},
            {"id": "ACT-008", "customer_id": "CUS-001", "type": TYPE_MEETING, "performed_by": "usr-cs2",
             "occurred_at": ago(days=10, hours=3), "subject": "Đào tạo người dùng kho",
             "content": "Đào tạo 8 nhân viên kho. Còn 2 nhân viên ca đêm chưa tham gia.",
             "outcome": "Cần đào tạo bổ sung", "duration_min": 120,
             "follow_up": {"text": "Đào tạo bổ sung cho 2 nhân viên ca đêm", "due": ahead(days=2), "done": False}},
            {"id": "ACT-009", "customer_id": "CUS-001", "type": TYPE_CALL, "performed_by": "usr-cs2",
             "occurred_at": ago(days=6, hours=1), "subject": "Khách phàn nàn báo cáo tồn kho chậm",
             "content": "Chị Hồng phàn nàn báo cáo tồn kho cuối ngày mất >3 phút. Đã chuyển ticket cho đội kỹ thuật (TK-2231).",
             "outcome": "Đang chờ kỹ thuật", "duration_min": 12,
             "follow_up": {"text": "Theo dõi ticket TK-2231 và gọi lại cho chị Hồng", "due": ahead(days=1), "done": False}},
            {"id": "ACT-010", "customer_id": "CUS-001", "type": TYPE_EMAIL, "performed_by": "usr-m1",
             "occurred_at": ago(days=5, hours=2), "subject": "Thư xin lỗi & cam kết khắc phục",
             "content": "Trưởng nhóm gửi thư xin lỗi, cam kết khắc phục hiệu năng báo cáo trong 7 ngày.",
             "outcome": "Đã gửi"},
            {"id": "ACT-011", "customer_id": "CUS-001", "type": TYPE_EMAIL, "performed_by": "usr-s1",
             "occurred_at": ago(days=3, hours=4), "subject": "Giới thiệu gói mở rộng kho Bình Dương",
             "content": "Khách dự kiến mở thêm kho ở Bình Dương. Đã gửi thông tin gói mở rộng thêm chi nhánh.",
             "outcome": "Khách quan tâm"},
            {"id": "ACT-012", "customer_id": "CUS-001", "type": TYPE_NOTE, "performed_by": "usr-cs2",
             "occurred_at": ago(days=1, hours=2), "subject": "Ghi chú bàn giao cho Thu Hà",
             "content": "Mình nghỉ phép 2 tuần. Việc gấp: (1) ticket TK-2231 hiệu năng báo cáo, (2) đào tạo ca đêm. Chị Hồng thích được gọi điện hơn email, gọi sau 14h.",
             "pinned": True},

            # ---- CUS-002: An Khang Việt ----
            {"id": "ACT-101", "customer_id": "CUS-002", "type": TYPE_CALL, "performed_by": "usr-s2",
             "occurred_at": ago(days=20, hours=2), "subject": "Tư vấn POS cho 25 nhà thuốc",
             "content": "Khách cần đồng bộ tồn kho giữa 25 nhà thuốc và quản lý hạn dùng thuốc.",
             "outcome": "Hẹn demo", "duration_min": 22},
            {"id": "ACT-102", "customer_id": "CUS-002", "type": TYPE_MEETING, "performed_by": "usr-s2",
             "occurred_at": ago(days=15, hours=1), "subject": "Demo online qua Google Meet",
             "content": "Demo cảnh báo cận date và đồng bộ đa chi nhánh. Anh Bảo yêu cầu thử nghiệm 2 cửa hàng.",
             "outcome": "Đồng ý pilot", "duration_min": 45},
            {"id": "ACT-103", "customer_id": "CUS-002", "type": TYPE_MESSAGE, "performed_by": "usr-cs2",
             "occurred_at": ago(days=4, hours=5), "subject": "Zalo: hỏi về hóa đơn điện tử",
             "content": "Khách hỏi kết nối hóa đơn điện tử Viettel. Đã gửi hướng dẫn cấu hình.",
             "outcome": "Đã trả lời"},

            # ---- CUS-004: Hải Âu ----
            {"id": "ACT-401", "customer_id": "CUS-004", "type": TYPE_EMAIL, "performed_by": "usr-cs1",
             "occurred_at": ago(days=12), "subject": "Nhắc gia hạn hợp đồng",
             "content": "Hợp đồng hết hạn sau 45 ngày. Đã gửi thông tin gia hạn và ưu đãi 5%.",
             "outcome": "Đã gửi"},
            {"id": "ACT-402", "customer_id": "CUS-004", "type": TYPE_CALL, "performed_by": "usr-s1",
             "occurred_at": ago(days=8, hours=3), "subject": "Thương lượng gia hạn",
             "content": "Khách muốn gia hạn kèm thêm 20 user. Yêu cầu báo giá mới.",
             "outcome": "Gửi báo giá", "duration_min": 15},
        ]

        # ---------------------------------------------------------------------
        # 2) CƠ HỘI & LỊCH SỬ THAY ĐỔI CƠ HỘI
        # ---------------------------------------------------------------------
        self.opportunities = {
            "OPP-001": {"id": "OPP-001", "customer_id": "CUS-001", "name": "Phần mềm Kho lạnh - 3 kho HCM",
                        "stage": "CLOSED_WON", "amount": 486_000_000, "probability": 100, "owner_id": "usr-s1"},
            "OPP-002": {"id": "OPP-002", "customer_id": "CUS-001", "name": "Mở rộng kho Bình Dương",
                        "stage": "QUALIFICATION", "amount": 150_000_000, "probability": 30, "owner_id": "usr-s1"},
            "OPP-101": {"id": "OPP-101", "customer_id": "CUS-002", "name": "POS Nhà thuốc - 25 cửa hàng",
                        "stage": "PROPOSAL", "amount": 320_000_000, "probability": 50, "owner_id": "usr-s2"},
            "OPP-401": {"id": "OPP-401", "customer_id": "CUS-004", "name": "Gia hạn HĐ + 20 user",
                        "stage": "NEGOTIATION", "amount": 240_000_000, "probability": 70, "owner_id": "usr-s1"},
        }

        self.opportunity_changes = [
            {"id": "OPC-001", "opportunity_id": "OPP-001", "field": OPP_FIELD_CREATED, "old_value": None,
             "new_value": "PROSPECTING", "changed_by": "usr-s1", "changed_at": ago(days=45, hours=2)},
            {"id": "OPC-002", "opportunity_id": "OPP-001", "field": OPP_FIELD_STAGE, "old_value": "PROSPECTING",
             "new_value": "PROPOSAL", "changed_by": "usr-s1", "changed_at": ago(days=40, hours=4)},
            {"id": "OPC-003", "opportunity_id": "OPP-001", "field": OPP_FIELD_AMOUNT, "old_value": 522_000_000,
             "new_value": 486_000_000, "changed_by": "usr-s1", "changed_at": ago(days=30)},
            {"id": "OPC-004", "opportunity_id": "OPP-001", "field": OPP_FIELD_STAGE, "old_value": "PROPOSAL",
             "new_value": "NEGOTIATION", "changed_by": "usr-s1", "changed_at": ago(days=30, minutes=-5)},
            {"id": "OPC-005", "opportunity_id": "OPP-001", "field": OPP_FIELD_STAGE, "old_value": "NEGOTIATION",
             "new_value": "CLOSED_WON", "changed_by": "usr-s1", "changed_at": ago(days=26, hours=5)},
            {"id": "OPC-006", "opportunity_id": "OPP-002", "field": OPP_FIELD_CREATED, "old_value": None,
             "new_value": "PROSPECTING", "changed_by": "usr-s1", "changed_at": ago(days=3, hours=3)},
            {"id": "OPC-007", "opportunity_id": "OPP-002", "field": OPP_FIELD_STAGE, "old_value": "PROSPECTING",
             "new_value": "QUALIFICATION", "changed_by": "usr-s1", "changed_at": ago(days=2, hours=1)},

            {"id": "OPC-101", "opportunity_id": "OPP-101", "field": OPP_FIELD_CREATED, "old_value": None,
             "new_value": "PROSPECTING", "changed_by": "usr-s2", "changed_at": ago(days=20, hours=1)},
            {"id": "OPC-102", "opportunity_id": "OPP-101", "field": OPP_FIELD_STAGE, "old_value": "PROSPECTING",
             "new_value": "PROPOSAL", "changed_by": "usr-s2", "changed_at": ago(days=14)},
            {"id": "OPC-103", "opportunity_id": "OPP-101", "field": OPP_FIELD_PROBABILITY, "old_value": 30,
             "new_value": 50, "changed_by": "usr-m1", "changed_at": ago(days=7, hours=2)},

            {"id": "OPC-401", "opportunity_id": "OPP-401", "field": OPP_FIELD_STAGE, "old_value": "PROPOSAL",
             "new_value": "NEGOTIATION", "changed_by": "usr-s1", "changed_at": ago(days=8, hours=2)},
        ]

        # ---------------------------------------------------------------------
        # 3) BÁO GIÁ ĐÃ GỬI
        # ---------------------------------------------------------------------
        self.quotes = [
            {"id": "QUO-001", "customer_id": "CUS-001", "opportunity_id": "OPP-001", "code": "BG-2026-0142",
             "title": "Báo giá Phần mềm Kho lạnh (bản đầu)", "amount": 522_000_000, "status": "REJECTED",
             "sent_by": "usr-s1", "sent_at": ago(days=38, hours=6), "sent_to": "hong.nguyen@senvang.vn",
             "valid_until": ago(days=8), "note": "Khách chê giá cao, đề nghị giảm 10%."},
            {"id": "QUO-002", "customer_id": "CUS-001", "opportunity_id": "OPP-001", "code": "BG-2026-0167",
             "title": "Báo giá Kho lạnh - HĐ 2 năm (giảm 7%)", "amount": 486_000_000, "status": "ACCEPTED",
             "sent_by": "usr-s1", "sent_at": ago(days=29, hours=20), "sent_to": "hong.nguyen@senvang.vn",
             "valid_until": ago(days=1), "note": "Khách chấp nhận, đã ký hợp đồng."},
            {"id": "QUO-003", "customer_id": "CUS-001", "opportunity_id": "OPP-002", "code": "BG-2026-0231",
             "title": "Báo giá Mở rộng kho Bình Dương", "amount": 150_000_000, "status": "VIEWED",
             "sent_by": "usr-s1", "sent_at": ago(days=2), "sent_to": "hong.nguyen@senvang.vn",
             "valid_until": ahead(days=28), "note": "Khách đã mở email 2 lần."},
            {"id": "QUO-101", "customer_id": "CUS-002", "opportunity_id": "OPP-101", "code": "BG-2026-0198",
             "title": "Báo giá POS 25 nhà thuốc", "amount": 320_000_000, "status": "SENT",
             "sent_by": "usr-s2", "sent_at": ago(days=13, hours=4), "sent_to": "bao.tran@ankhangviet.vn",
             "valid_until": ahead(days=17), "note": ""},
            {"id": "QUO-401", "customer_id": "CUS-004", "opportunity_id": "OPP-401", "code": "BG-2026-0215",
             "title": "Báo giá gia hạn + 20 user", "amount": 240_000_000, "status": "SENT",
             "sent_by": "usr-s1", "sent_at": ago(days=7, hours=5), "sent_to": "linh.dang@haiaulogistics.vn",
             "valid_until": ahead(days=23), "note": ""},
        ]

        self._next_activity_seq = 1000

    # -------------------------------------------------------------------------
    # TRUY VẤN CƠ BẢN
    # -------------------------------------------------------------------------
    def get_customer(self, customer_id):
        return self.customers.get(customer_id)

    def _require_customer(self, customer_id):
        customer = self.get_customer(customer_id)
        if not customer:
            raise KeyError(f"Không tìm thấy khách hàng {customer_id}")
        return customer

    def _user_brief(self, user_id):
        user = self.users.get(user_id)
        if not user:
            return {"id": user_id, "name": "Không xác định", "avatar": "❔", "role_name": ""}
        return {"id": user["id"], "name": user["name"], "avatar": user["avatar"], "role_name": user["role_name"]}

    # -------------------------------------------------------------------------
    # CHUẨN HÓA 3 NGUỒN DỮ LIỆU THÀNH SỰ KIỆN DÒNG THỜI GIAN
    # -------------------------------------------------------------------------
    def _make_event(self, *, event_id, source, event_type, occurred_at, performer_id,
                    title, summary, details=None, extra=None):
        performer = self._user_brief(performer_id)
        event = {
            "id": event_id,
            "source": source,
            "type": event_type,
            "type_label": EVENT_TYPE_LABELS[event_type],
            "icon": EVENT_TYPE_ICONS[event_type],
            "color": EVENT_TYPE_COLORS[event_type],
            "occurred_at": occurred_at,
            "performer_id": performer_id,
            "performer": performer,
            "title": title,
            "summary": summary,
            "details": details or [],
        }
        if extra:
            event.update(extra)
        return event

    def _activity_events(self, customer_id):
        for act in self.activities:
            if act["customer_id"] != customer_id:
                continue
            details = []
            if act.get("outcome"):
                details.append(("Kết quả", act["outcome"]))
            if act.get("duration_min"):
                details.append(("Thời lượng", f"{act['duration_min']} phút"))
            follow_up = act.get("follow_up")
            if follow_up:
                status = "✅ Đã xong" if follow_up.get("done") else f"⏳ Hạn {format_datetime(follow_up['due'])}"
                details.append(("Việc tiếp theo", f"{follow_up['text']} ({status})"))
            yield self._make_event(
                event_id=act["id"],
                source=SOURCE_ACTIVITY,
                event_type=act["type"],
                occurred_at=act["occurred_at"],
                performer_id=act["performed_by"],
                title=act["subject"],
                summary=act.get("content", ""),
                details=details,
                extra={"pinned": bool(act.get("pinned"))},
            )

    def _opportunity_events(self, customer_id):
        for change in self.opportunity_changes:
            opp = self.opportunities.get(change["opportunity_id"])
            if not opp or opp["customer_id"] != customer_id:
                continue
            field = change["field"]
            if field == OPP_FIELD_CREATED:
                title = f"Tạo cơ hội: {opp['name']}"
                summary = f"Giai đoạn khởi tạo: {_format_opp_value(OPP_FIELD_STAGE, change['new_value'])}"
            else:
                label = OPP_FIELD_LABELS.get(field, field)
                old_v = _format_opp_value(field, change["old_value"])
                new_v = _format_opp_value(field, change["new_value"])
                title = f"{label}: {old_v} → {new_v}"
                summary = f"Cơ hội “{opp['name']}”"
            yield self._make_event(
                event_id=change["id"],
                source=SOURCE_OPPORTUNITY,
                event_type=TYPE_OPPORTUNITY,
                occurred_at=change["changed_at"],
                performer_id=change["changed_by"],
                title=title,
                summary=summary,
                details=[("Mã cơ hội", opp["id"]), ("Trường thay đổi", OPP_FIELD_LABELS.get(field, field))],
                extra={
                    "opportunity_id": opp["id"],
                    "field": field,
                    "old_value": change["old_value"],
                    "new_value": change["new_value"],
                    "is_won": field == OPP_FIELD_STAGE and change["new_value"] == "CLOSED_WON",
                },
            )

    def _quote_events(self, customer_id):
        for quote in self.quotes:
            if quote["customer_id"] != customer_id:
                continue
            details = [
                ("Mã báo giá", quote["code"]),
                ("Giá trị", format_currency(quote["amount"])),
                ("Gửi tới", quote["sent_to"]),
                ("Hiệu lực đến", format_date(quote.get("valid_until"))),
                ("Trạng thái", QUOTE_STATUS_LABELS.get(quote["status"], quote["status"])),
            ]
            yield self._make_event(
                event_id=quote["id"],
                source=SOURCE_QUOTE,
                event_type=TYPE_QUOTE,
                occurred_at=quote["sent_at"],
                performer_id=quote["sent_by"],
                title=f"Gửi báo giá {quote['code']}: {quote['title']}",
                summary=quote.get("note") or "",
                details=details,
                extra={
                    "quote_code": quote["code"],
                    "amount": quote["amount"],
                    "quote_status": quote["status"],
                    "quote_status_label": QUOTE_STATUS_LABELS.get(quote["status"], quote["status"]),
                },
            )

    def _all_events(self, customer_id):
        self._require_customer(customer_id)
        events = []
        events.extend(self._activity_events(customer_id))
        events.extend(self._opportunity_events(customer_id))
        events.extend(self._quote_events(customer_id))
        return events

    # -------------------------------------------------------------------------
    # BỘ LỌC
    # -------------------------------------------------------------------------
    def normalize_filters(self, types=None, performers=None):
        """Chuẩn hóa & kiểm tra giá trị bộ lọc. Ném ValueError nếu giá trị không hợp lệ."""
        type_list = [t.upper() for t in _parse_multi(types)]
        performer_list = _parse_multi(performers)

        invalid_types = [t for t in type_list if t not in EVENT_TYPES]
        if invalid_types:
            raise ValueError(f"Loại hoạt động không hợp lệ: {', '.join(invalid_types)}")

        invalid_users = [p for p in performer_list if p not in self.users]
        if invalid_users:
            raise ValueError(f"Người thực hiện không hợp lệ: {', '.join(invalid_users)}")

        return type_list, performer_list

    # -------------------------------------------------------------------------
    # TIÊU CHÍ 1 + 2: DÒNG THỜI GIAN GỘP, SẮP XẾP & LỌC
    # -------------------------------------------------------------------------
    def build_timeline(self, customer_id, types=None, performers=None, order=ORDER_DESC):
        """
        Gộp hoạt động + thay đổi cơ hội + báo giá đã gửi của một khách hàng
        thành một danh sách sự kiện, sắp xếp theo thời gian.

        - types: lọc theo loại hoạt động (một hoặc nhiều giá trị trong EVENT_TYPES).
        - performers: lọc theo người thực hiện (một hoặc nhiều user id).
        - order: 'desc' (mới nhất trước, mặc định) hoặc 'asc' (cũ nhất trước).
        """
        if order not in (ORDER_ASC, ORDER_DESC):
            raise ValueError(f"Thứ tự sắp xếp không hợp lệ: {order}")

        type_list, performer_list = self.normalize_filters(types, performers)
        events = self._all_events(customer_id)

        if type_list:
            events = [e for e in events if e["type"] in type_list]
        if performer_list:
            events = [e for e in events if e["performer_id"] in performer_list]

        events.sort(
            key=lambda e: (e["occurred_at"], _SOURCE_PRIORITY[e["source"]], e["id"]),
            reverse=(order == ORDER_DESC),
        )
        return events

    def group_by_day(self, events):
        """Nhóm sự kiện theo ngày (giữ nguyên thứ tự đã sắp xếp) để hiển thị."""
        groups = []
        for event in events:
            day = event["occurred_at"].date()
            if not groups or groups[-1]["date"] != day:
                groups.append({"date": day, "events": []})
            groups[-1]["events"].append(event)
        return groups

    def get_performers(self, customer_id):
        """Danh sách người đã từng tương tác với khách (cho dropdown lọc)."""
        counts = {}
        for e in self._all_events(customer_id):
            counts[e["performer_id"]] = counts.get(e["performer_id"], 0) + 1
        result = []
        for uid, count in counts.items():
            brief = self._user_brief(uid)
            brief["count"] = count
            result.append(brief)
        result.sort(key=lambda u: (-u["count"], u["name"]))
        return result

    def get_type_counts(self, customer_id, performers=None):
        """Đếm số sự kiện theo từng loại (tôn trọng bộ lọc người thực hiện)."""
        events = self.build_timeline(customer_id, performers=performers)
        counts = {t: 0 for t in EVENT_TYPES}
        for e in events:
            counts[e["type"]] += 1
        return counts

    # -------------------------------------------------------------------------
    # TÓM TẮT BÀN GIAO - NẮM BỐI CẢNH TRONG 5 PHÚT
    # -------------------------------------------------------------------------
    def get_handover_summary(self, customer_id):
        customer = self._require_customer(customer_id)
        events = self.build_timeline(customer_id)  # mới nhất trước

        last_event = events[0] if events else None
        last_contact = next((e for e in events if e["type"] in _CONTACT_TYPES), None)
        pinned_notes = [e for e in events if e.get("pinned")]

        open_opps = []
        for opp in self.opportunities.values():
            if opp["customer_id"] == customer_id and not opp["stage"].startswith("CLOSED"):
                open_opps.append({
                    **opp,
                    "stage_label": OPP_STAGE_LABELS.get(opp["stage"], opp["stage"]),
                    "owner": self._user_brief(opp["owner_id"]),
                })
        won_value = sum(
            o["amount"] for o in self.opportunities.values()
            if o["customer_id"] == customer_id and o["stage"] == "CLOSED_WON"
        )

        customer_quotes = sorted(
            (q for q in self.quotes if q["customer_id"] == customer_id),
            key=lambda q: q["sent_at"], reverse=True,
        )
        latest_quote = None
        if customer_quotes:
            q = customer_quotes[0]
            latest_quote = {**q, "status_label": QUOTE_STATUS_LABELS.get(q["status"], q["status"])}

        pending = []
        for act in self.activities:
            fu = act.get("follow_up")
            if act["customer_id"] == customer_id and fu and not fu.get("done"):
                pending.append({
                    "activity_id": act["id"],
                    "text": fu["text"],
                    "due": fu["due"],
                    "is_overdue": fu["due"] < self._current_time(),
                    "owner": self._user_brief(act["performed_by"]),
                })
        pending.sort(key=lambda p: p["due"])

        first_at = events[-1]["occurred_at"] if events else None

        return {
            "customer": customer,
            "cs_owner": self._user_brief(customer["cs_owner_id"]),
            "sales_owner": self._user_brief(customer["sales_owner_id"]),
            "total_events": len(events),
            "first_interaction_at": first_at,
            "last_event": last_event,
            "last_contact": last_contact,
            "pinned_notes": pinned_notes,
            "open_opportunities": open_opps,
            "won_value": won_value,
            "latest_quote": latest_quote,
            "pending_follow_ups": pending,
        }

    def _current_time(self):
        return datetime.now()

    # -------------------------------------------------------------------------
    # DANH SÁCH KHÁCH HÀNG
    # -------------------------------------------------------------------------
    def list_customers(self, search=None):
        keyword = (search or "").strip().lower()
        result = []
        for c in self.customers.values():
            haystack = " ".join([c["id"], c["name"], c["contact_name"], c["phone"], c["email"]]).lower()
            if keyword and keyword not in haystack:
                continue
            events = self.build_timeline(c["id"])
            item = copy.copy(c)
            item["cs_owner"] = self._user_brief(c["cs_owner_id"])
            item["total_events"] = len(events)
            item["last_event"] = events[0] if events else None
            result.append(item)
        result.sort(
            key=lambda c: c["last_event"]["occurred_at"] if c["last_event"] else datetime.min,
            reverse=True,
        )
        return result

    # -------------------------------------------------------------------------
    # GHI NHẬN HOẠT ĐỘNG MỚI (VD: CSKH ghi chú khi tiếp nhận)
    # -------------------------------------------------------------------------
    def add_activity(self, customer_id, activity_type, subject, content, user_id, occurred_at=None):
        self._require_customer(customer_id)
        activity_type = (activity_type or "").upper()
        if activity_type not in ACTIVITY_TYPES:
            raise ValueError(f"Loại hoạt động không hợp lệ: {activity_type}")
        if user_id not in self.users:
            raise ValueError(f"Người thực hiện không hợp lệ: {user_id}")
        subject = (subject or "").strip()
        content = (content or "").strip()
        if not subject:
            raise ValueError("Vui lòng nhập tiêu đề hoạt động")

        self._next_activity_seq += 1
        activity = {
            "id": f"ACT-{self._next_activity_seq}",
            "customer_id": customer_id,
            "type": activity_type,
            "performed_by": user_id,
            "occurred_at": occurred_at or datetime.now().replace(microsecond=0),
            "subject": subject,
            "content": content,
        }
        self.activities.append(activity)
        return activity


# =============================================================================
# CHUYỂN SỰ KIỆN SANG JSON
# =============================================================================
def event_to_json(event):
    data = {}
    for key, value in event.items():
        if isinstance(value, datetime):
            data[key] = value.isoformat()
        elif key == "details":
            data[key] = [{"label": label, "value": val} for label, val in value]
        else:
            data[key] = value
    return data


db = CRMDatabase()

    def sort_timeline_events_chronological(self, events: list) -> list:
        """Sắp xếp các sự kiện tương tác theo thứ tự thời gian giảm dần"""
        return sorted(events, key=lambda x: x.get('timestamp', ''), reverse=True)

    def attach_file_to_interaction(self, event_id: str, file_url: str):
        """Đính kèm tệp âm thanh cuộc gọi hoặc tài liệu cuộc họp"""
        pass

    def toggle_pin_interaction(self, event_id: str) -> bool:
        """Ghim sự kiện quan trọng lên đầu timeline"""
        return True

    def optimize_activity_notes_join(self):
        """Tối ưu hóa câu truy vấn kết hợp bảng activities và bảng notes"""
        pass
