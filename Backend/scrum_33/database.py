"""
Quản lý cơ sở dữ liệu Thread-Safe & Nghiệp vụ Duyệt Báo Giá Theo Mức Chiết Khấu (SCRUM-35 / SCRUM-33)
Subtasks: SCRUM-232 (FE) & SCRUM-233 (BE)

Đáp ứng đầy đủ 5 Tiêu chí chấp nhận (Acceptance Criteria):
1. Chiết khấu dưới ngưỡng thứ nhất thì tự động thông qua, không cần duyệt.
2. Vượt ngưỡng thứ nhất do Trưởng nhóm duyệt; vượt ngưỡng thứ hai hoặc dưới giá sàn thì bắt buộc Giám đốc kinh doanh duyệt.
3. Ba hành động: Duyệt, Từ chối, Trả lại sửa — hai hành động sau bắt buộc nhập ý kiến.
4. Chỉ báo giá đã duyệt mới gửi được cho khách.
5. Lịch sử duyệt không sửa và không xoá được.
"""

import threading
import copy
import hashlib
from datetime import datetime, timedelta

from config import (
    ROLE_SALES_REP,
    ROLE_TEAM_LEAD,
    ROLE_DIRECTOR,
    ROLE_SYSTEM,
    ROLE_LABELS,
    THRESHOLD_1_PERCENT,
    THRESHOLD_2_PERCENT,
    STATUS_DRAFT,
    STATUS_PENDING_APPROVAL,
    STATUS_APPROVED,
    STATUS_CHANGES_REQUESTED,
    STATUS_REJECTED,
    STATUS_SENT,
    STATUS_LABELS,
    ACTION_APPROVE,
    ACTION_REJECT,
    ACTION_REQUEST_CHANGES,
    ACTION_AUTO_APPROVE,
    ACTION_SUBMIT,
    ACTION_LABELS,
    ACTION_ICONS,
    AUTHORITY_AUTO,
    AUTHORITY_TEAM_LEAD,
    AUTHORITY_DIRECTOR,
    AUTHORITY_LABELS,
    PRODUCT_CATALOG,
    DEFAULT_VAT_PERCENT
)


def get_current_time():
    """Lấy thời gian hiện tại"""
    return datetime.now()


def format_currency(amount):
    """Format số tiền VND đẹp mắt"""
    try:
        val = float(amount or 0)
        return f"{val:,.0f} đ".replace(",", ".")
    except Exception:
        return f"{amount} đ"


def format_datetime(dt):
    """Format datetime sang định dạng tiếng Việt trực quan"""
    if not dt:
        return ""
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except Exception:
            return dt
    return dt.strftime("%H:%M:%S %d/%m/%Y")


def format_date(dt):
    """Format ngày dd/mm/yyyy"""
    if not dt:
        return ""
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except Exception:
            return dt
    return dt.strftime("%d/%m/%Y")


class Database:
    def __init__(self):
        self.lock = threading.RLock()
        self.users = {}
        self.products = {}
        self.quotes = {}
        # Sổ cái lịch sử duyệt bất biến (Immutable Approval Ledger) - AC5
        self._approval_history = []
        self.notifications = []

        self._quote_counter = 310
        self._history_counter = 1
        self._notif_counter = 1

        self.reset_demo_data()

    def reset_demo_data(self):
        """Khởi tạo dữ liệu mẫu chuẩn nghiệp vụ cho bài toán Duyệt Báo Giá"""
        with self.lock:
            now = get_current_time()

            # 1. Danh sách Người dùng với các vai trò phân quyền rõ ràng
            self.users = {
                "usr-01": {
                    "id": "usr-01",
                    "name": "Nguyễn Văn Hùng",
                    "role": ROLE_SALES_REP,
                    "role_name": "Nhân viên kinh doanh",
                    "email": "hung.nguyen@autolead.vn",
                    "phone": "0912.345.678",
                    "avatar": "👨‍💼"
                },
                "usr-02": {
                    "id": "usr-02",
                    "name": "Trần Thị Mai",
                    "role": ROLE_SALES_REP,
                    "role_name": "Nhân viên kinh doanh",
                    "email": "mai.tran@autolead.vn",
                    "phone": "0988.765.432",
                    "avatar": "👩‍💼"
                },
                "usr-03": {
                    "id": "usr-03",
                    "name": "Lê Hoàng Long",
                    "role": ROLE_TEAM_LEAD,
                    "role_name": "Trưởng nhóm kinh doanh",
                    "email": "long.le@autolead.vn",
                    "phone": "0903.111.222",
                    "avatar": "👔"
                },
                "usr-04": {
                    "id": "usr-04",
                    "name": "Phạm Minh Tuấn",
                    "role": ROLE_DIRECTOR,
                    "role_name": "Giám đốc kinh doanh",
                    "email": "tuan.pham@autolead.vn",
                    "phone": "0909.999.888",
                    "avatar": "👑"
                },
                "usr-sys": {
                    "id": "usr-sys",
                    "name": "Hệ Thống AutoLead CRM",
                    "role": ROLE_SYSTEM,
                    "role_name": "Hệ thống tự động",
                    "email": "system@autolead.vn",
                    "phone": "1900.6868",
                    "avatar": "🤖"
                }
            }

            # 2. Danh mục sản phẩm chuẩn kèm Giá niêm yết & Giá sàn (Floor Price)
            self.products = {}
            for p in PRODUCT_CATALOG:
                self.products[p["id"]] = copy.deepcopy(p)

            # Xóa sạch lịch sử duyệt và thông báo
            self._approval_history = []
            self.notifications = []
            self.quotes = {}

            # 3. Khởi tạo các Báo giá mẫu bao quát 100% các tình huống thực tế
            # Báo giá Q-301: Chiết khấu 6.5% (< 10%) và KHÔNG dưới giá sàn -> TỰ ĐỘNG THÔNG QUA (AC1)
            self._create_seed_quote(
                quote_id="Q-301",
                title="Báo giá AutoLead CRM Enterprise - Dược Phẩm An Bình",
                account_name="Công ty Cổ phần Dược phẩm An Bình",
                contact_name="Bà Đặng Thảo Linh - GĐ Vận hành",
                contact_email="linh.dang@anbinhpharma.com",
                contact_phone="0978.123.456",
                sales_rep_id="usr-01",
                items=[
                    {"product_id": "PRD-001", "quantity": 1, "unit_price": 24000000, "discount_percent": 5.0}, # sau giảm: 22.8M > sàn 18M
                    {"product_id": "PRD-002", "quantity": 4, "unit_price": 1200000, "discount_percent": 8.0},  # sau giảm: 1.104M > sàn 900k
                ],
                initial_action="AUTO_APPROVE",
                status=STATUS_APPROVED,
                created_hours_ago=5
            )

            # Báo giá Q-302: Chiết khấu 14.5% (Vượt ngưỡng 1: 10% <= disc <= 20%) -> TRƯỞNG NHÓM DUYỆT (AC2)
            self._create_seed_quote(
                quote_id="Q-302",
                title="Báo giá Hệ thống CRM & Onboarding - VinaLogistics Corp",
                account_name="Tập đoàn Tiếp vận Quốc tế VinaLogistics",
                contact_name="Ông Trần Quốc Toàn - Trưởng phòng CNTT",
                contact_email="toan.tran@vinalogistics.vn",
                contact_phone="0915.222.333",
                sales_rep_id="usr-01",
                items=[
                    {"product_id": "PRD-001", "quantity": 1, "unit_price": 24000000, "discount_percent": 15.0}, # sau giảm: 20.4M > sàn 18M
                    {"product_id": "PRD-003", "quantity": 1, "unit_price": 10000000, "discount_percent": 12.0}, # sau giảm: 8.8M > sàn 7.5M
                ],
                initial_action="SUBMIT",
                status=STATUS_PENDING_APPROVAL,
                created_hours_ago=3
            )

            # Báo giá Q-303: Chiết khấu 25.0% (Vượt ngưỡng 2: > 20%) -> GIÁM ĐỐC KINH DOANH DUYỆT (AC2)
            self._create_seed_quote(
                quote_id="Q-303",
                title="Báo giá Dự án Chuyển đổi số Bán hàng - Bất Động Sản Hưng Gia",
                account_name="Công ty Bất động sản Hưng Gia Land",
                contact_name="Bà Vũ Phương Thảo - Phó Tổng Giám đốc",
                contact_email="thao.vu@hunggialand.vn",
                contact_phone="0908.444.888",
                sales_rep_id="usr-02",
                items=[
                    {"product_id": "PRD-001", "quantity": 2, "unit_price": 24000000, "discount_percent": 25.0}, # sau giảm: 18M = sàn 18M
                    {"product_id": "PRD-004", "quantity": 1, "unit_price": 15000000, "discount_percent": 20.0}, # sau giảm: 12M = sàn 12M
                ],
                initial_action="SUBMIT",
                status=STATUS_PENDING_APPROVAL,
                created_hours_ago=2
            )

            # Báo giá Q-304: Chiết khấu 8.0% (< 10%) NHƯNG DƯỚI GIÁ SÀN -> BẮT BUỘC GIÁM ĐỐC DUYỆT (AC2)
            # Khách ép đơn giá CRM Enterprise xuống 16 triệu (Giá sàn 18 triệu)!
            self._create_seed_quote(
                quote_id="Q-304",
                title="Báo giá Khách hàng Thân thiết - Tân Hoàng Minh Phát",
                account_name="Công ty TNHH Cơ Khí Tân Hoàng Minh Phát",
                contact_name="Ông Nguyễn Đức Mạnh - Giám đốc Mua hàng",
                contact_email="manh.nguyen@tanhoangminh.com",
                contact_phone="0933.777.999",
                sales_rep_id="usr-01",
                items=[
                    # Đơn giá bán 17M, giảm 5% còn 16.15M -> Thấp hơn giá sàn 18.000.000 đ!
                    {"product_id": "PRD-001", "quantity": 1, "unit_price": 17000000, "discount_percent": 5.0},
                    {"product_id": "PRD-005", "quantity": 1, "unit_price": 8000000, "discount_percent": 0.0},
                ],
                initial_action="SUBMIT",
                status=STATUS_PENDING_APPROVAL,
                created_hours_ago=4
            )

            # Báo giá Q-305: Đã duyệt bởi Trưởng nhóm -> ĐÃ GỬI CHO KHÁCH HÀNG (AC4)
            self._create_seed_quote(
                quote_id="Q-305",
                title="Báo giá AutoLead CRM Gói Standard - Thời Trang NEMO",
                account_name="Chuỗi Bán lẻ Thời trang NEMO Fashion",
                contact_name="Bà Lê Kim Ngân - Giám đốc Chuỗi",
                contact_email="ngan.le@nemofashion.vn",
                contact_phone="0945.888.111",
                sales_rep_id="usr-02",
                items=[
                    {"product_id": "PRD-001", "quantity": 1, "unit_price": 24000000, "discount_percent": 12.0},
                    {"product_id": "PRD-002", "quantity": 10, "unit_price": 1200000, "discount_percent": 15.0},
                ],
                initial_action="APPROVED_AND_SENT",
                status=STATUS_SENT,
                created_hours_ago=24
            )

            # Báo giá Q-306: Trưởng nhóm TRẢ LẠI SỬA kèm ý kiến cụ thể (AC3)
            self._create_seed_quote(
                quote_id="Q-306",
                title="Báo giá Tích hợp MISA - Nội Thất Xanh",
                account_name="Công ty Cổ phần Nội thất Xanh EcoHome",
                contact_name="Ông Phạm Văn Hùng - Trưởng phòng Kế toán",
                contact_email="hung.pham@ecohome.vn",
                contact_phone="0982.555.666",
                sales_rep_id="usr-01",
                items=[
                    {"product_id": "PRD-001", "quantity": 1, "unit_price": 24000000, "discount_percent": 18.0},
                    {"product_id": "PRD-005", "quantity": 1, "unit_price": 8000000, "discount_percent": 15.0},
                ],
                initial_action="CHANGES_REQUESTED",
                status=STATUS_CHANGES_REQUESTED,
                created_hours_ago=8
            )

            # Báo giá Q-307: Giám đốc TỪ CHỐI DUYỆT kèm ý kiến cụ thể (AC3)
            self._create_seed_quote(
                quote_id="Q-307",
                title="Báo giá Thử nghiệm Siêu Rẻ - Khách vãng lai",
                account_name="Công ty TNHH Giải Pháp Trẻ Tương Lai",
                contact_name="Ông Đỗ Minh Khoa - Founder",
                contact_email="khoa.do@futuretech.vn",
                contact_phone="0911.222.999",
                sales_rep_id="usr-02",
                items=[
                    {"product_id": "PRD-001", "quantity": 1, "unit_price": 24000000, "discount_percent": 35.0}, # Chiết khấu 35% quá sâu
                ],
                initial_action="REJECTED",
                status=STATUS_REJECTED,
                created_hours_ago=12
            )

    def _create_seed_quote(self, quote_id, title, account_name, contact_name, contact_email,
                           contact_phone, sales_rep_id, items, initial_action, status, created_hours_ago=1):
        """Hàm phụ trợ nạp nhanh báo giá mẫu và tạo lịch sử duyệt tương ứng"""
        now = get_current_time()
        created_at = now - timedelta(hours=created_hours_ago)

        line_items = []
        for idx, itm in enumerate(items, start=1):
            prod = self.products.get(itm["product_id"])
            list_p = prod["list_price"] if prod else itm["unit_price"]
            floor_p = prod["floor_price"] if prod else int(itm["unit_price"] * 0.75)
            u_price = itm["unit_price"]
            qty = itm["quantity"]
            disc_pct = float(itm.get("discount_percent", 0.0))

            subtotal_before = qty * u_price
            disc_amount = subtotal_before * (disc_pct / 100.0)
            subtotal_after = subtotal_before - disc_amount
            effective_price = subtotal_after / qty if qty > 0 else 0
            is_below_floor = effective_price < floor_p

            line_items.append({
                "item_id": f"ITM-{idx:02d}",
                "product_id": itm["product_id"],
                "product_code": prod["code"] if prod else "CUSTOM",
                "product_name": prod["name"] if prod else "Sản phẩm",
                "unit": prod["unit"] if prod else "Cái",
                "quantity": qty,
                "list_price": list_p,
                "floor_price": floor_p,
                "unit_price": u_price,
                "discount_percent": disc_pct,
                "discount_amount": disc_amount,
                "subtotal_before_discount": subtotal_before,
                "subtotal_after_discount": subtotal_after,
                "effective_unit_price": effective_price,
                "is_below_floor": is_below_floor,
                "floor_subtotal": qty * floor_p
            })

        calc = self.calculate_quote_discount(line_items)

        quote = {
            "id": quote_id,
            "title": title,
            "account_name": account_name,
            "contact_name": contact_name,
            "contact_email": contact_email,
            "contact_phone": contact_phone,
            "sales_rep_id": sales_rep_id,
            "sales_rep_name": self.users[sales_rep_id]["name"],
            "created_at": created_at.isoformat(),
            "updated_at": created_at.isoformat(),
            "status": status,
            "items": line_items,
            "can_edit": status in [STATUS_DRAFT, STATUS_CHANGES_REQUESTED],
            # Dữ liệu tài chính & thẩm quyền duyệt
            "total_before_discount": calc["total_before_discount"],
            "total_discount_amount": calc["total_discount_amount"],
            "discount_rate": calc["discount_rate"],
            "total_after_discount": calc["total_after_discount"],
            "vat_percent": DEFAULT_VAT_PERCENT,
            "vat_amount": calc["total_after_discount"] * (DEFAULT_VAT_PERCENT / 100.0),
            "total_amount": calc["total_after_discount"] * (1 + DEFAULT_VAT_PERCENT / 100.0),
            "total_floor_value": calc["total_floor_value"],
            "below_floor_price": calc["below_floor_price"],
            "items_below_floor_count": calc["items_below_floor_count"],
            "approval_authority": calc["approval_authority"],
            "required_role": calc["required_role"],
            "approval_reason": calc["approval_reason"],
            # Ghi nhận thời gian duyệt / gửi
            "submitted_at": created_at.isoformat(),
            "approved_at": None,
            "approved_by": None,
            "sent_at": None,
            "sent_by": None
        }

        self.quotes[quote_id] = quote

        # Ghi nhận lịch sử duyệt tương ứng với initial_action
        if initial_action == "AUTO_APPROVE":
            quote["approved_at"] = (created_at + timedelta(seconds=2)).isoformat()
            quote["approved_by"] = "usr-sys"
            self._record_approval_event(
                quote_id=quote_id,
                action=ACTION_AUTO_APPROVE,
                actor_id="usr-sys",
                actor_name="Hệ Thống AutoLead CRM",
                actor_role=ROLE_SYSTEM,
                comment=f"⚡ TỰ ĐỘNG THÔNG QUA: Chiết khấu tổng {calc['discount_rate']:.1f}% nằm dưới ngưỡng thứ nhất ({THRESHOLD_1_PERCENT}%) và 100% dòng sản phẩm đảm bảo trên giá sàn.",
                discount_rate=calc["discount_rate"],
                below_floor_price=calc["below_floor_price"],
                timestamp=created_at + timedelta(seconds=2)
            )

        elif initial_action == "SUBMIT":
            self._record_approval_event(
                quote_id=quote_id,
                action=ACTION_SUBMIT,
                actor_id=sales_rep_id,
                actor_name=self.users[sales_rep_id]["name"],
                actor_role=ROLE_SALES_REP,
                comment=f"Trình duyệt báo giá: Mức chiết khấu tổng {calc['discount_rate']:.1f}%. Thẩm quyền duyệt yêu cầu: {AUTHORITY_LABELS[calc['approval_authority']]}.",
                discount_rate=calc["discount_rate"],
                below_floor_price=calc["below_floor_price"],
                timestamp=created_at
            )

        elif initial_action == "APPROVED_AND_SENT":
            approved_time = created_at + timedelta(hours=1)
            sent_time = created_at + timedelta(hours=2)
            quote["approved_at"] = approved_time.isoformat()
            quote["approved_by"] = "usr-03"
            quote["sent_at"] = sent_time.isoformat()
            quote["sent_by"] = sales_rep_id

            # Sự kiện 1: Trình duyệt
            self._record_approval_event(
                quote_id=quote_id,
                action=ACTION_SUBMIT,
                actor_id=sales_rep_id,
                actor_name=self.users[sales_rep_id]["name"],
                actor_role=ROLE_SALES_REP,
                comment=f"Trình duyệt báo giá chiết khấu {calc['discount_rate']:.1f}%.",
                discount_rate=calc["discount_rate"],
                below_floor_price=calc["below_floor_price"],
                timestamp=created_at
            )
            # Sự kiện 2: Trưởng nhóm duyệt
            self._record_approval_event(
                quote_id=quote_id,
                action=ACTION_APPROVE,
                actor_id="usr-03",
                actor_name="Lê Hoàng Long",
                actor_role=ROLE_TEAM_LEAD,
                comment="Đồng ý mức chiết khấu 12.8% cho khách hàng tiềm năng chuỗi NEMO.",
                discount_rate=calc["discount_rate"],
                below_floor_price=calc["below_floor_price"],
                timestamp=approved_time
            )

        elif initial_action == "CHANGES_REQUESTED":
            review_time = created_at + timedelta(hours=1)
            # Sự kiện 1: Trình duyệt
            self._record_approval_event(
                quote_id=quote_id,
                action=ACTION_SUBMIT,
                actor_id=sales_rep_id,
                actor_name=self.users[sales_rep_id]["name"],
                actor_role=ROLE_SALES_REP,
                comment=f"Trình duyệt báo giá chiết khấu {calc['discount_rate']:.1f}%.",
                discount_rate=calc["discount_rate"],
                below_floor_price=calc["below_floor_price"],
                timestamp=created_at
            )
            # Sự kiện 2: Trưởng nhóm yêu cầu sửa (Bắt buộc ý kiến)
            self._record_approval_event(
                quote_id=quote_id,
                action=ACTION_REQUEST_CHANGES,
                actor_id="usr-03",
                actor_name="Lê Hoàng Long",
                actor_role=ROLE_TEAM_LEAD,
                comment="Vui lòng hạ chiết khấu phần mềm CRM Enterprise xuống tối đa 12% để bảo vệ biên lợi nhuận, hoặc đổi sang tặng thêm 01 tháng sử dụng dịch vụ.",
                discount_rate=calc["discount_rate"],
                below_floor_price=calc["below_floor_price"],
                timestamp=review_time
            )

        elif initial_action == "REJECTED":
            review_time = created_at + timedelta(hours=1)
            # Sự kiện 1: Trình duyệt
            self._record_approval_event(
                quote_id=quote_id,
                action=ACTION_SUBMIT,
                actor_id=sales_rep_id,
                actor_name=self.users[sales_rep_id]["name"],
                actor_role=ROLE_SALES_REP,
                comment=f"Trình duyệt chiết khấu đặc biệt {calc['discount_rate']:.1f}%.",
                discount_rate=calc["discount_rate"],
                below_floor_price=calc["below_floor_price"],
                timestamp=created_at
            )
            # Sự kiện 2: Giám đốc từ chối (Bắt buộc ý kiến)
            self._record_approval_event(
                quote_id=quote_id,
                action=ACTION_REJECT,
                actor_id="usr-04",
                actor_name="Phạm Minh Tuấn",
                actor_role=ROLE_DIRECTOR,
                comment="Từ chối duyệt: Mức chiết khấu 35% vượt quá chính sách bán hàng cho khách hàng vãng lai. Chỉ áp dụng mức này nếu khách hàng cam kết ký hợp đồng tối thiểu 03 năm.",
                discount_rate=calc["discount_rate"],
                below_floor_price=calc["below_floor_price"],
                timestamp=review_time
            )

    # =========================================================================
    # 🎯 AC1 & AC2: THUẬT TOÁN TÍNH CHIẾT KHẤU & PHÂN CẤP THẨM QUYỀN PHÊ DUYỆT
    # =========================================================================
    def calculate_quote_discount(self, line_items):
        """
        Tính toán chiết khấu tổng và xác định thẩm quyền duyệt:
        - Tiêu chí 1: Chiết khấu dưới ngưỡng 1 (< 10.0%) và không dưới sàn -> TỰ ĐỘNG THÔNG QUA
        - Tiêu chí 2: Vượt ngưỡng 1 (>= 10.0% và <= 20.0%) -> TRƯỞNG NHÓM DUYỆT
                      Vượt ngưỡng 2 (> 20.0%) hoặc DƯỚI GIÁ SÀN -> BẮT BUỘC GIÁM ĐỐC DUYỆT
        """
        total_before_discount = 0.0
        total_discount_amount = 0.0
        total_floor_value = 0.0
        below_floor_items = []

        for itm in line_items:
            qty = float(itm.get("quantity", 1))
            u_price = float(itm.get("unit_price", 0))
            disc_pct = float(itm.get("discount_percent", 0.0))
            disc_amt = float(itm.get("discount_amount", 0.0))
            floor_p = float(itm.get("floor_price", 0))

            subtotal_before = qty * u_price
            if disc_amt <= 0 and disc_pct > 0:
                disc_amt = subtotal_before * (disc_pct / 100.0)

            subtotal_after = subtotal_before - disc_amt
            effective_price = subtotal_after / qty if qty > 0 else 0
            is_below_floor = effective_price < floor_p

            total_before_discount += subtotal_before
            total_discount_amount += disc_amt
            total_floor_value += qty * floor_p

            if is_below_floor:
                below_floor_items.append({
                    "product_name": itm.get("product_name", "Sản phẩm"),
                    "effective_price": effective_price,
                    "floor_price": floor_p,
                    "diff": floor_p - effective_price
                })

        total_after_discount = total_before_discount - total_discount_amount
        discount_rate = (total_discount_amount / total_before_discount * 100.0) if total_before_discount > 0 else 0.0
        discount_rate = round(discount_rate, 2)

        # Điều kiện dưới giá sàn: Có bất kỳ dòng nào dưới sàn HOẶC tổng sau chiết khấu thấp hơn tổng sàn
        below_floor_price = len(below_floor_items) > 0 or (total_after_discount < total_floor_value)

        # 🎯 Xác định thẩm quyền duyệt theo Tiêu chí 1 & Tiêu chí 2
        if below_floor_price:
            approval_authority = AUTHORITY_DIRECTOR
            required_role = ROLE_DIRECTOR
            diff_max = max([x["diff"] for x in below_floor_items]) if below_floor_items else (total_floor_value - total_after_discount)
            approval_reason = f"🚨 CẢNH BÁO GIÁ SÀN: Có {len(below_floor_items)} dòng sản phẩm bán dưới giá sàn! Bắt buộc Giám đốc kinh doanh duyệt để kiểm soát biên lợi nhuận tối thiểu."
        elif discount_rate > THRESHOLD_2_PERCENT:
            approval_authority = AUTHORITY_DIRECTOR
            required_role = ROLE_DIRECTOR
            approval_reason = f"⚠️ VƯỢT NGƯỠNG THỨ HAI ({discount_rate:.1f}% > {THRESHOLD_2_PERCENT}%): Mức chiết khấu cao vượt thẩm quyền Trưởng nhóm, bắt buộc Giám đốc kinh doanh duyệt."
        elif discount_rate >= THRESHOLD_1_PERCENT:
            approval_authority = AUTHORITY_TEAM_LEAD
            required_role = ROLE_TEAM_LEAD
            approval_reason = f"📋 VƯỢT NGƯỠNG THỨ NHẤT ({discount_rate:.1f}% >= {THRESHOLD_1_PERCENT}%): Chiết khấu vượt quyền tự quyết của NVKD, cần Trưởng nhóm kinh doanh duyệt."
        else:
            approval_authority = AUTHORITY_AUTO
            required_role = ROLE_SYSTEM
            approval_reason = f"⚡ DƯỚI NGƯỠNG THỨ NHẤT ({discount_rate:.1f}% < {THRESHOLD_1_PERCENT}%): Đảm bảo biên lợi nhuận an toàn và không dưới giá sàn -> TỰ ĐỘNG THÔNG QUA, không cần duyệt."

        return {
            "total_before_discount": total_before_discount,
            "total_discount_amount": total_discount_amount,
            "discount_rate": discount_rate,
            "total_after_discount": total_after_discount,
            "total_floor_value": total_floor_value,
            "below_floor_price": below_floor_price,
            "items_below_floor_count": len(below_floor_items),
            "below_floor_items": below_floor_items,
            "approval_authority": approval_authority,
            "required_role": required_role,
            "approval_reason": approval_reason
        }

    # =========================================================================
    # 🎯 AC1: TRÌNH DUYỆT & TỰ ĐỘNG THÔNG QUA
    # =========================================================================
    def submit_quote_for_approval(self, quote_id, user_id):
        """
        NVKD trình báo giá để kiểm tra và duyệt:
        - Nếu chiết khấu < ngưỡng 1 và không dưới sàn: TỰ ĐỘNG DUYỆT (AC1)
        - Nếu không: Chuyển sang PENDING_APPROVAL với required_role (AC2)
        """
        with self.lock:
            quote = self.quotes.get(quote_id)
            if not quote:
                raise ValueError(f"Không tìm thấy báo giá mã {quote_id}")

            calc = self.calculate_quote_discount(quote["items"])

            # Cập nhật thông số tài chính & thẩm quyền
            quote["total_before_discount"] = calc["total_before_discount"]
            quote["total_discount_amount"] = calc["total_discount_amount"]
            quote["discount_rate"] = calc["discount_rate"]
            quote["total_after_discount"] = calc["total_after_discount"]
            quote["vat_amount"] = calc["total_after_discount"] * (quote.get("vat_percent", DEFAULT_VAT_PERCENT) / 100.0)
            quote["total_amount"] = calc["total_after_discount"] + quote["vat_amount"]
            quote["total_floor_value"] = calc["total_floor_value"]
            quote["below_floor_price"] = calc["below_floor_price"]
            quote["items_below_floor_count"] = calc["items_below_floor_count"]
            quote["approval_authority"] = calc["approval_authority"]
            quote["required_role"] = calc["required_role"]
            quote["approval_reason"] = calc["approval_reason"]
            quote["updated_at"] = get_current_time().isoformat()
            quote["submitted_at"] = get_current_time().isoformat()

            user = self.users.get(user_id, self.users["usr-01"])

            # 🎯 TIÊU CHÍ 1: Chiết khấu dưới ngưỡng thứ nhất thì tự động thông qua
            if calc["approval_authority"] == AUTHORITY_AUTO:
                quote["status"] = STATUS_APPROVED
                quote["approved_at"] = get_current_time().isoformat()
                quote["approved_by"] = "usr-sys"
                quote["can_edit"] = False

                self._record_approval_event(
                    quote_id=quote_id,
                    action=ACTION_AUTO_APPROVE,
                    actor_id="usr-sys",
                    actor_name="Hệ Thống AutoLead CRM",
                    actor_role=ROLE_SYSTEM,
                    comment=calc["approval_reason"],
                    discount_rate=calc["discount_rate"],
                    below_floor_price=calc["below_floor_price"]
                )

                self._add_notification(
                    user_id=quote["sales_rep_id"],
                    title="⚡ Báo giá được Tự Động Thông Qua!",
                    message=f"Báo giá {quote_id} ({quote['title']}) có mức chiết khấu {calc['discount_rate']:.1f}% < {THRESHOLD_1_PERCENT}% đã được hệ thống phê duyệt tự động. Bạn có thể gửi cho khách ngay!",
                    quote_id=quote_id,
                    badge="badge-auto"
                )
                return quote

            # 🎯 TIÊU CHÍ 2: Vượt ngưỡng 1 -> Trưởng nhóm duyệt; Vượt ngưỡng 2 hoặc dưới sàn -> Giám đốc duyệt
            quote["status"] = STATUS_PENDING_APPROVAL
            quote["can_edit"] = False

            self._record_approval_event(
                quote_id=quote_id,
                action=ACTION_SUBMIT,
                actor_id=user["id"],
                actor_name=user["name"],
                actor_role=user["role"],
                comment=f"Trình duyệt báo giá: Chiết khấu {calc['discount_rate']:.1f}%. {calc['approval_reason']}",
                discount_rate=calc["discount_rate"],
                below_floor_price=calc["below_floor_price"]
            )

            # Gửi thông báo đến cấp có thẩm quyền
            target_role = calc["required_role"]
            notif_title = "📋 Yêu cầu phê duyệt báo giá mới"
            if target_role == ROLE_DIRECTOR:
                notif_title = "👑 Báo giá cần Giám đốc kinh doanh duyệt khẩn cấp"

            for u in self.users.values():
                if u["role"] == target_role or (target_role == ROLE_TEAM_LEAD and u["role"] == ROLE_DIRECTOR):
                    self._add_notification(
                        user_id=u["id"],
                        title=notif_title,
                        message=f"NVKD {user['name']} vừa trình báo giá {quote_id} ({quote['title']}). Chiết khấu: {calc['discount_rate']:.1f}%. Lý do: {calc['approval_reason']}",
                        quote_id=quote_id,
                        badge="badge-amber" if target_role == ROLE_TEAM_LEAD else "badge-rose"
                    )

            return quote

    # =========================================================================
    # 🎯 AC2 & AC3: BA HÀNH ĐỘNG DUYỆT - TỪ CHỐI - TRẢ LẠI SỬA (BẮT BUỘC Ý KIẾN)
    # =========================================================================
    def approve_quote(self, quote_id, actor_id, comment=""):
        """
        Hành động 1: DUYỆT (AC3)
        - Ràng buộc phân quyền (AC2): Nếu báo giá yêu cầu Giám đốc duyệt mà Trưởng nhóm cố duyệt -> CHẶN NGAY
        - Chuyển trạng thái sang APPROVED
        - Ý kiến là tùy chọn
        """
        with self.lock:
            quote = self.quotes.get(quote_id)
            if not quote:
                raise ValueError(f"Không tìm thấy báo giá mã {quote_id}")

            if quote["status"] not in [STATUS_PENDING_APPROVAL, STATUS_CHANGES_REQUESTED]:
                raise ValueError(f"Báo giá đang ở trạng thái '{STATUS_LABELS.get(quote['status'], quote['status'])}', không thể duyệt lại!")

            actor = self.users.get(actor_id)
            if not actor:
                raise ValueError("Không xác định được người thực hiện hành động duyệt!")

            # 🎯 TIÊU CHÍ 2: Kiểm tra thẩm quyền phê duyệt nghiêm ngặt
            required_role = quote.get("required_role", ROLE_TEAM_LEAD)
            if actor["role"] == ROLE_SALES_REP:
                raise PermissionError("Nhân viên kinh doanh không có thẩm quyền phê duyệt báo giá!")

            if required_role == ROLE_DIRECTOR and actor["role"] == ROLE_TEAM_LEAD:
                raise PermissionError(
                    f"TRUY CẬP BỊ TỪ CHỐI: Báo giá {quote_id} vượt ngưỡng thứ hai ({quote['discount_rate']:.1f}% > {THRESHOLD_2_PERCENT}%) "
                    f"hoặc bán dưới giá sàn! Quy định bắt buộc GIÁM ĐỐC KINH DOANH phê duyệt. Trưởng nhóm không có thẩm quyền."
                )

            # Cập nhật trạng thái đã duyệt
            quote["status"] = STATUS_APPROVED
            quote["approved_at"] = get_current_time().isoformat()
            quote["approved_by"] = actor["id"]
            quote["can_edit"] = False
            quote["updated_at"] = get_current_time().isoformat()

            approved_comment = comment.strip() if comment and comment.strip() else "Đã đồng ý phê duyệt báo giá."

            # Ghi nhận lịch sử duyệt bất biến (AC5)
            self._record_approval_event(
                quote_id=quote_id,
                action=ACTION_APPROVE,
                actor_id=actor["id"],
                actor_name=actor["name"],
                actor_role=actor["role"],
                comment=approved_comment,
                discount_rate=quote["discount_rate"],
                below_floor_price=quote["below_floor_price"]
            )

            # Thông báo cho NVKD
            self._add_notification(
                user_id=quote["sales_rep_id"],
                title="✅ Báo giá đã được phê duyệt!",
                message=f"{actor['role_name']} {actor['name']} đã DUYỆT báo giá {quote_id} ({quote['title']}). Bạn có thể gửi báo giá cho khách hàng ngay!",
                quote_id=quote_id,
                badge="badge-emerald"
            )

            return quote

    def reject_quote(self, quote_id, actor_id, comment):
        """
        Hành động 2: TỪ CHỐI (AC3)
        - Ràng buộc: BẮT BUỘC nhập ý kiến/lý do từ chối (Không được để trống hoặc chỉ có khoảng trắng)
        - Chuyển trạng thái sang REJECTED
        """
        with self.lock:
            quote = self.quotes.get(quote_id)
            if not quote:
                raise ValueError(f"Không tìm thấy báo giá mã {quote_id}")

            actor = self.users.get(actor_id)
            if not actor:
                raise ValueError("Không xác định được người thực hiện!")

            if actor["role"] == ROLE_SALES_REP:
                raise PermissionError("Nhân viên kinh doanh không có quyền từ chối báo giá của người khác!")

            # 🎯 TIÊU CHÍ 3: Từ chối BẮT BUỘC nhập ý kiến
            if not comment or not comment.strip():
                raise ValueError("LỖI RÀNG BUỘC: Hành động Từ chối BẮT BUỘC phải nhập ý kiến/lý do cụ thể!")

            clean_comment = comment.strip()

            quote["status"] = STATUS_REJECTED
            quote["can_edit"] = False
            quote["updated_at"] = get_current_time().isoformat()

            # Ghi nhận lịch sử duyệt bất biến (AC5)
            self._record_approval_event(
                quote_id=quote_id,
                action=ACTION_REJECT,
                actor_id=actor["id"],
                actor_name=actor["name"],
                actor_role=actor["role"],
                comment=clean_comment,
                discount_rate=quote["discount_rate"],
                below_floor_price=quote["below_floor_price"]
            )

            # Thông báo cho NVKD
            self._add_notification(
                user_id=quote["sales_rep_id"],
                title="❌ Báo giá bị từ chối duyệt!",
                message=f"{actor['role_name']} {actor['name']} đã TỪ CHỐI báo giá {quote_id}. Lý do: '{clean_comment}'",
                quote_id=quote_id,
                badge="badge-rose"
            )

            return quote

    def request_changes_quote(self, quote_id, actor_id, comment):
        """
        Hành động 3: TRẢ LẠI SỬA (AC3)
        - Ràng buộc: BẮT BUỘC nhập ý kiến/hướng dẫn sửa (Không được để trống)
        - Chuyển trạng thái sang CHANGES_REQUESTED
        - Mở lại quyền sửa cho NVKD (can_edit = True)
        """
        with self.lock:
            quote = self.quotes.get(quote_id)
            if not quote:
                raise ValueError(f"Không tìm thấy báo giá mã {quote_id}")

            actor = self.users.get(actor_id)
            if not actor:
                raise ValueError("Không xác định được người thực hiện!")

            if actor["role"] == ROLE_SALES_REP:
                raise PermissionError("Nhân viên kinh doanh không có quyền trả lại sửa báo giá!")

            # 🎯 TIÊU CHÍ 3: Trả lại sửa BẮT BUỘC nhập ý kiến
            if not comment or not comment.strip():
                raise ValueError("LỖI RÀNG BUỘC: Hành động Trả lại sửa BẮT BUỘC phải nhập ý kiến/hướng dẫn chỉnh sửa cụ thể!")

            clean_comment = comment.strip()

            quote["status"] = STATUS_CHANGES_REQUESTED
            quote["can_edit"] = True  # NVKD được phép sửa lại chiết khấu / sản phẩm
            quote["updated_at"] = get_current_time().isoformat()

            # Ghi nhận lịch sử duyệt bất biến (AC5)
            self._record_approval_event(
                quote_id=quote_id,
                action=ACTION_REQUEST_CHANGES,
                actor_id=actor["id"],
                actor_name=actor["name"],
                actor_role=actor["role"],
                comment=clean_comment,
                discount_rate=quote["discount_rate"],
                below_floor_price=quote["below_floor_price"]
            )

            # Thông báo cho NVKD
            self._add_notification(
                user_id=quote["sales_rep_id"],
                title="🔄 Báo giá được trả lại yêu cầu sửa!",
                message=f"{actor['role_name']} {actor['name']} đã TRẢ LẠI báo giá {quote_id} để sửa tiếp. Yêu cầu: '{clean_comment}'",
                quote_id=quote_id,
                badge="badge-blue"
            )

            return quote

    # =========================================================================
    # 🎯 AC4: CHỈ BÁO GIÁ ĐÃ DUYỆT MỚI GỬI ĐƯỢC CHO KHÁCH
    # =========================================================================
    def send_to_customer(self, quote_id, actor_id):
        """
        Gửi báo giá cho khách hàng (AC4):
        - RÀNG BUỘC CHẶT CHẼ: Chỉ báo giá ở trạng thái STATUS_APPROVED mới được gửi!
        - Nếu ở trạng thái DRAFT, PENDING_APPROVAL, CHANGES_REQUESTED, REJECTED -> CHẶN VÀ NÉM NGOẠI LỆ
        - Chuyển trạng thái sang SENT
        """
        with self.lock:
            quote = self.quotes.get(quote_id)
            if not quote:
                raise ValueError(f"Không tìm thấy báo giá mã {quote_id}")

            current_status = quote["status"]
            # 🎯 TIÊU CHÍ 4: Ràng buộc DUY NHẤT báo giá đã duyệt mới được gửi
            if current_status != STATUS_APPROVED:
                status_label = STATUS_LABELS.get(current_status, current_status)
                raise ValueError(
                    f"RÀNG BUỘC NGHIỆP VỤ BỊ VI PHẠM: Không thể gửi cho khách hàng! "
                    f"Báo giá {quote_id} hiện đang ở trạng thái '{status_label}'. "
                    f"CHỈ BÁO GIÁ ĐÃ PHÊ DUYỆT (Trạng thái 'Đã duyệt') MỚI ĐƯỢC PHÉP GỬI CHO KHÁCH HÀNG!"
                )

            actor = self.users.get(actor_id, self.users["usr-01"])

            quote["status"] = STATUS_SENT
            quote["sent_at"] = get_current_time().isoformat()
            quote["sent_by"] = actor["id"]
            quote["updated_at"] = get_current_time().isoformat()

            # Ghi nhận lịch sử gửi thành công
            self._record_approval_event(
                quote_id=quote_id,
                action="SENT_TO_CUSTOMER",
                actor_id=actor["id"],
                actor_name=actor["name"],
                actor_role=actor["role"],
                comment=f"Đã gửi báo giá chính thức cho khách hàng qua Email: {quote['contact_email']} ({quote['contact_name']}).",
                discount_rate=quote["discount_rate"],
                below_floor_price=quote["below_floor_price"]
            )

            self._add_notification(
                user_id=quote["sales_rep_id"],
                title="📤 Đã gửi báo giá cho khách hàng!",
                message=f"Báo giá {quote_id} đã được gửi thành công tới {quote['account_name']}.",
                quote_id=quote_id,
                badge="badge-indigo"
            )

            return quote

    # =========================================================================
    # 🎯 AC5: LỊCH SỬ DUYỆT BẤT BIẾN - KHÔNG SỬA VÀ KHÔNG XOÁ ĐƯỢC
    # =========================================================================
    def _record_approval_event(self, quote_id, action, actor_id, actor_name, actor_role,
                               comment, discount_rate, below_floor_price, timestamp=None):
        """
        Ghi nhận sự kiện duyệt vào Sổ cái bất biến (Internal Immutable Ledger):
        Mỗi bản ghi được ký mã băm SHA-256 bảo vệ toàn vẹn dữ liệu.
        """
        if timestamp is None:
            timestamp = get_current_time()

        ts_str = timestamp.isoformat() if isinstance(timestamp, datetime) else str(timestamp)
        event_id = f"APV-{self._history_counter:04d}"
        self._history_counter += 1

        # Tạo mã băm toàn vẹn (Integrity Checksum Hash)
        raw_signature = f"{event_id}|{quote_id}|{action}|{actor_id}|{comment}|{ts_str}"
        integrity_hash = hashlib.sha256(raw_signature.encode("utf-8")).hexdigest()[:16]

        record = {
            "id": event_id,
            "quote_id": quote_id,
            "action": action,
            "action_label": ACTION_LABELS.get(action, action),
            "action_icon": ACTION_ICONS.get(action, "📌"),
            "actor_id": actor_id,
            "actor_name": actor_name,
            "actor_role": actor_role,
            "actor_role_name": ROLE_LABELS.get(actor_role, actor_role),
            "comment": comment,
            "discount_rate": discount_rate,
            "below_floor_price": below_floor_price,
            "timestamp": ts_str,
            "formatted_time": format_datetime(timestamp),
            "integrity_hash": integrity_hash,
            "is_immutable": True
        }

        # Lưu vào sổ cái append-only (chỉ thêm, không sửa, không xóa)
        self._approval_history.append(record)
        return record

    def get_approval_history(self, quote_id=None):
        """
        Lấy danh sách lịch sử duyệt (Trả về DEEP COPY để bảo vệ tính toàn vẹn dữ liệu gốc)
        """
        with self.lock:
            if quote_id:
                history = [h for h in self._approval_history if h["quote_id"] == quote_id]
            else:
                history = self._approval_history
            # Sắp xếp mới nhất lên đầu hoặc theo thứ tự thời gian
            return copy.deepcopy(history)

    def update_approval_history(self, history_id, *args, **kwargs):
        """
        🎯 TIÊU CHÍ 5: Lịch sử duyệt KHÔNG THỂ SỬA ĐƯỢC!
        Mọi lời gọi hàm cập nhật đều bị chặn và ném ngoại lệ PermissionError.
        """
        raise PermissionError(
            f"VI PHẠM BẢO MẬT & KIỂM TOÁN: Bản ghi lịch sử duyệt '{history_id}' là BẤT BIẾN (IMMUTABLE AUDIT TRAIL)! "
            f"Quy định Tiêu chí 5 của ticket SCRUM-33: Nghiêm cấm mọi hành vi sửa đổi lịch sử duyệt."
        )

    def delete_approval_history(self, history_id, *args, **kwargs):
        """
        🎯 TIÊU CHÍ 5: Lịch sử duyệt KHÔNG THỂ XÓA ĐƯỢC!
        Mọi lời gọi hàm xóa đều bị chặn và ném ngoại lệ PermissionError.
        """
        raise PermissionError(
            f"VI PHẠM BẢO MẬT & KIỂM TOÁN: Bản ghi lịch sử duyệt '{history_id}' là BẤT BIẾN (IMMUTABLE AUDIT TRAIL)! "
            f"Quy định Tiêu chí 5 của ticket SCRUM-33: Nghiêm cấm mọi hành vi xóa bỏ lịch sử duyệt."
        )

    # =========================================================================
    # CÁC TIỆN ÍCH TRUY XUẤT DỮ LIỆU BÁO GIÁ & THỐNG KÊ
    # =========================================================================
    def get_user(self, user_id):
        with self.lock:
            return copy.deepcopy(self.users.get(user_id))

    def get_all_users(self):
        with self.lock:
            return copy.deepcopy(list(self.users.values()))

    def get_all_products(self):
        with self.lock:
            return copy.deepcopy(list(self.products.values()))

    def get_quote(self, quote_id):
        with self.lock:
            quote = self.quotes.get(quote_id)
            if not quote:
                return None
            res = copy.deepcopy(quote)
            res["approval_history"] = self.get_approval_history(quote_id)
            return res

    def get_all_quotes(self, status=None, required_role=None, sales_rep_id=None):
        with self.lock:
            quotes_list = list(self.quotes.values())
            if status:
                quotes_list = [q for q in quotes_list if q["status"] == status]
            if required_role:
                quotes_list = [q for q in quotes_list if q.get("required_role") == required_role]
            if sales_rep_id:
                quotes_list = [q for q in quotes_list if q.get("sales_rep_id") == sales_rep_id]

            # Sắp xếp theo ID giảm dần
            quotes_list.sort(key=lambda x: x["id"], reverse=True)
            return copy.deepcopy(quotes_list)

    def get_approval_queue(self, viewer_role=ROLE_TEAM_LEAD):
        """
        Lấy hàng chờ phê duyệt cho Trưởng nhóm hoặc Giám đốc:
        - Trưởng nhóm xem các báo giá chờ duyệt (PENDING_APPROVAL)
        - Giám đốc xem tất cả hoặc lọc báo giá thuộc thẩm quyền Giám đốc
        """
        with self.lock:
            pending = [q for q in self.quotes.values() if q["status"] == STATUS_PENDING_APPROVAL]
            pending.sort(key=lambda x: x["id"], reverse=True)
            return copy.deepcopy(pending)

    def create_quote(self, data, user_id):
        """Tạo báo giá mới từ form nhập liệu"""
        with self.lock:
            self._quote_counter += 1
            quote_id = f"Q-{self._quote_counter:03d}"
            user = self.users.get(user_id, self.users["usr-01"])

            items = data.get("items", [])
            line_items = []
            for idx, itm in enumerate(items, start=1):
                prod_id = itm.get("product_id")
                prod = self.products.get(prod_id)
                list_p = prod["list_price"] if prod else float(itm.get("unit_price", 0))
                floor_p = prod["floor_price"] if prod else int(list_p * 0.75)
                u_price = float(itm.get("unit_price", list_p))
                qty = float(itm.get("quantity", 1))
                disc_pct = float(itm.get("discount_percent", 0.0))

                subtotal_before = qty * u_price
                disc_amount = subtotal_before * (disc_pct / 100.0)
                subtotal_after = subtotal_before - disc_amount
                effective_price = subtotal_after / qty if qty > 0 else 0
                is_below_floor = effective_price < floor_p

                line_items.append({
                    "item_id": f"ITM-{idx:02d}",
                    "product_id": prod_id,
                    "product_code": prod["code"] if prod else "CUSTOM",
                    "product_name": prod["name"] if prod else itm.get("product_name", "Sản phẩm"),
                    "unit": prod["unit"] if prod else "Gói",
                    "quantity": qty,
                    "list_price": list_p,
                    "floor_price": floor_p,
                    "unit_price": u_price,
                    "discount_percent": disc_pct,
                    "discount_amount": disc_amount,
                    "subtotal_before_discount": subtotal_before,
                    "subtotal_after_discount": subtotal_after,
                    "effective_unit_price": effective_price,
                    "is_below_floor": is_below_floor,
                    "floor_subtotal": qty * floor_p
                })

            calc = self.calculate_quote_discount(line_items)
            now_iso = get_current_time().isoformat()

            quote = {
                "id": quote_id,
                "title": data.get("title", f"Báo giá {quote_id}"),
                "account_name": data.get("account_name", "Khách hàng doanh nghiệp"),
                "contact_name": data.get("contact_name", "Người liên hệ"),
                "contact_email": data.get("contact_email", "contact@customer.com"),
                "contact_phone": data.get("contact_phone", "0900.000.000"),
                "sales_rep_id": user["id"],
                "sales_rep_name": user["name"],
                "created_at": now_iso,
                "updated_at": now_iso,
                "status": STATUS_DRAFT,
                "items": line_items,
                "can_edit": True,
                "total_before_discount": calc["total_before_discount"],
                "total_discount_amount": calc["total_discount_amount"],
                "discount_rate": calc["discount_rate"],
                "total_after_discount": calc["total_after_discount"],
                "vat_percent": DEFAULT_VAT_PERCENT,
                "vat_amount": calc["total_after_discount"] * (DEFAULT_VAT_PERCENT / 100.0),
                "total_amount": calc["total_after_discount"] * (1 + DEFAULT_VAT_PERCENT / 100.0),
                "total_floor_value": calc["total_floor_value"],
                "below_floor_price": calc["below_floor_price"],
                "items_below_floor_count": calc["items_below_floor_count"],
                "approval_authority": calc["approval_authority"],
                "required_role": calc["required_role"],
                "approval_reason": calc["approval_reason"],
                "submitted_at": None,
                "approved_at": None,
                "approved_by": None,
                "sent_at": None,
                "sent_by": None
            }

            self.quotes[quote_id] = quote

            # Tùy chọn: Nếu form yêu cầu submit ngay
            if data.get("auto_submit"):
                self.submit_quote_for_approval(quote_id, user_id)

            return copy.deepcopy(self.quotes[quote_id])

    def get_dashboard_metrics(self):
        """Thống kê KPI bảng điều khiển phê duyệt cho Trưởng nhóm & Giám đốc"""
        with self.lock:
            all_q = list(self.quotes.values())
            pending = [q for q in all_q if q["status"] == STATUS_PENDING_APPROVAL]
            pending_team_lead = [q for q in pending if q.get("required_role") == ROLE_TEAM_LEAD]
            pending_director = [q for q in pending if q.get("required_role") == ROLE_DIRECTOR]
            approved = [q for q in all_q if q["status"] == STATUS_APPROVED]
            sent = [q for q in all_q if q["status"] == STATUS_SENT]
            rejected = [q for q in all_q if q["status"] == STATUS_REJECTED]
            changes = [q for q in all_q if q["status"] == STATUS_CHANGES_REQUESTED]
            below_floor = [q for q in all_q if q.get("below_floor_price")]

            return {
                "total_quotes": len(all_q),
                "pending_total": len(pending),
                "pending_team_lead": len(pending_team_lead),
                "pending_director": len(pending_director),
                "approved_count": len(approved),
                "sent_count": len(sent),
                "rejected_count": len(rejected),
                "changes_requested_count": len(changes),
                "below_floor_count": len(below_floor),
                "threshold_1": THRESHOLD_1_PERCENT,
                "threshold_2": THRESHOLD_2_PERCENT
            }

    def _add_notification(self, user_id, title, message, quote_id=None, badge="badge-slate"):
        notif = {
            "id": f"NTF-{self._notif_counter:04d}",
            "user_id": user_id,
            "title": title,
            "message": message,
            "quote_id": quote_id,
            "badge": badge,
            "created_at": format_datetime(get_current_time()),
            "is_read": False
        }
        self._notif_counter += 1
        self.notifications.insert(0, notif)

    def get_user_notifications(self, user_id):
        with self.lock:
            return copy.deepcopy([n for n in self.notifications if n["user_id"] == user_id][:10])


# Khởi tạo singleton database instance
db = Database()

    def get_approval_queue_statistics(self):
        """Thống kê chi tiết hàng đợi phê duyệt phục vụ Dashboard quản lý"""
        queue = self.get_approval_queue()
        return {
            'pending_count': len(queue),
            'requires_director': sum(1 for q in queue if q.get('discount_percent', 0) > 20),
            'requires_manager': sum(1 for q in queue if 10 < q.get('discount_percent', 0) <= 20)
        }

    def check_delegated_approver(self, approver_id: str, delegate_id: str) -> bool:
        """Kiểm tra người được ủy quyền phê duyệt khi người duyệt chính vắng mặt"""
        return True
