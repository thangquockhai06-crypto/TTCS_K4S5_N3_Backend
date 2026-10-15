"""
Quản lý cơ sở dữ liệu Thread-Safe & Nghiệp vụ Soạn Báo Giá Từ Cơ Hội (SCRUM-35 / SCRUM-31)

Đáp ứng 5 Tiêu chí chấp nhận (Acceptance Criteria):
1. Dòng sản phẩm được kế thừa từ cơ hội, sửa lại được.
2. Mỗi dòng nhập chiết khấu theo phần trăm hoặc số tiền, hệ thống tính lại thành tiền ngay.
3. Hiển thị mức chiết khấu tổng và cảnh báo khi chạm ngưỡng cần duyệt.
4. Khai báo hiệu lực báo giá, điều khoản thanh toán và điều khoản giao hàng.
5. Lưu nháp và sửa tiếp được.
"""

import threading
import copy
from datetime import datetime, timedelta

from config import (
    STATUS_DRAFT,
    STATUS_PENDING_APPROVAL,
    STATUS_APPROVED,
    STATUS_SENT,
    STATUS_ACCEPTED,
    STATUS_REJECTED,
    STATUS_EXPIRED,
    STATUS_LABELS,
    STATUS_COLORS,
    STATUS_BADGE_CLASSES,
    DISCOUNT_APPROVAL_THRESHOLD_PERCENT,
    DISCOUNT_WARNING_THRESHOLD_PERCENT,
    DISCOUNT_TYPE_PERCENT,
    DISCOUNT_TYPE_AMOUNT,
    DISCOUNT_TYPE_LABELS,
    DEFAULT_VAT_PERCENT,
    VALIDITY_PRESETS,
    PAYMENT_TERMS_PRESETS,
    DELIVERY_TERMS_PRESETS,
    ROLE_SALES_REP,
    ROLE_TEAM_LEAD,
    ROLE_DIRECTOR,
    ROLE_LABELS,
    PRODUCT_CATALOG
)


def get_current_time():
    """Lấy thời gian hiện tại"""
    return datetime.now()


def format_currency(amount):
    """Format tiền tệ VND đẹp mắt"""
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
        self.opportunities = {}
        self.quotes = {}
        self.products = {}
        self.notifications = []
        self.audit_logs = []

        # Các bộ đếm ID tăng dần
        self._quote_counter = 500
        self._item_counter = 1000
        self._notif_counter = 1
        self._log_counter = 1

        self.reset_demo_data()

    def reset_demo_data(self):
        """Khởi tạo dữ liệu mẫu chuẩn nghiệp vụ B2B cho bài toán Báo giá từ Cơ hội"""
        with self.lock:
            now = get_current_time()

            # 1. Người dùng hệ thống (Users)
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
                }
            }

            # 2. Danh mục sản phẩm (Product Catalog)
            self.products = {}
            for p in PRODUCT_CATALOG:
                self.products[p["id"]] = copy.deepcopy(p)

            # 3. Cơ hội bán hàng mẫu (Opportunities với dòng sản phẩm dự kiến)
            # Khách hỏi trong buổi sáng, NVKD cần soạn báo giá gửi trong buổi chiều cùng ngày!
            self.opportunities = {
                "OPP-401": {
                    "id": "OPP-401",
                    "title": "Cung cấp Hệ thống AutoLead CRM cho Công ty CP Dược Phẩm An Bình",
                    "account_name": "Công ty Cổ phần Dược phẩm An Bình",
                    "tax_id": "0108923456",
                    "contact_name": "Bà Đặng Thảo Linh",
                    "contact_title": "Giám đốc Vận hành",
                    "contact_phone": "0978.123.456",
                    "contact_email": "linh.dang@anbinhpharma.com",
                    "address": "Tầng 8, Tòa nhà Dược Phẩm, 185 Giảng Võ, Ba Đình, Hà Nội",
                    "sales_rep_id": "usr-01",
                    "sales_rep_name": "Nguyễn Văn Hùng",
                    "inquiry_time": (now - timedelta(hours=3)).strftime("%H:%M %d/%m/%Y"), # Khách hỏi sáng nay
                    "expected_closing": (now + timedelta(days=14)).strftime("%d/%m/%Y"),
                    "stage": "Báo giá & Đề xuất",
                    "notes": "Khách hàng yêu cầu gửi báo giá gấp trong buổi chiều cùng ngày để trình Ban Giám đốc duyệt ngân sách thứ Hai.",
                    # Dòng sản phẩm kế thừa từ cơ hội (AC1)
                    "line_items": [
                        {
                            "item_id": "ITM-01",
                            "product_id": "PRD-001",
                            "product_code": "CRM-ENTERPRISE",
                            "product_name": "Bản quyền AutoLead CRM Enterprise (Gói 1 năm / 20 users)",
                            "unit": "Gói / Năm",
                            "quantity": 1,
                            "unit_price": 24000000,
                            "discount_type": DISCOUNT_TYPE_PERCENT,
                            "discount_value": 0,
                            "description": "Quản lý Lead, Cơ hội, Báo giá, Hợp đồng & Tự động hóa bán hàng"
                        },
                        {
                            "item_id": "ITM-02",
                            "product_id": "PRD-002",
                            "product_code": "CRM-USER-ADD",
                            "product_name": "Tài khoản người dùng bổ sung (Add-on User License)",
                            "unit": "User / Năm",
                            "quantity": 5,
                            "unit_price": 1200000,
                            "discount_type": DISCOUNT_TYPE_PERCENT,
                            "discount_value": 0,
                            "description": "5 tài khoản cho đội ngũ Trình dược viên & Quản trị"
                        },
                        {
                            "item_id": "ITM-03",
                            "product_id": "PRD-003",
                            "product_code": "SRV-IMPL-ONBOARD",
                            "product_name": "Dịch vụ Thiết lập Quy trình & Onboarding Chuyên sâu",
                            "unit": "Gói",
                            "quantity": 1,
                            "unit_price": 15000000,
                            "discount_type": DISCOUNT_TYPE_PERCENT,
                            "discount_value": 0,
                            "description": "Khảo sát và chuẩn hóa luồng phê duyệt đặc thù ngành Dược"
                        }
                    ]
                },
                "OPP-402": {
                    "id": "OPP-402",
                    "title": "Nâng cấp Hạ tầng Cloud & Tích hợp CRM cho Tập đoàn Logistics Đại Nam",
                    "account_name": "Tập đoàn Giao vận Logistics Đại Nam",
                    "tax_id": "0305889922",
                    "contact_name": "Ông Trần Quang Minh",
                    "contact_title": "Giám đốc Công nghệ thông tin (CIO)",
                    "contact_phone": "0903.888.777",
                    "contact_email": "minh.tran@dainamlogistics.vn",
                    "address": "Số 45 Nguyễn Thị Minh Khai, Quận 1, TP. Hồ Chí Minh",
                    "sales_rep_id": "usr-01",
                    "sales_rep_name": "Nguyễn Văn Hùng",
                    "inquiry_time": (now - timedelta(hours=2)).strftime("%H:%M %d/%m/%Y"),
                    "expected_closing": (now + timedelta(days=21)).strftime("%d/%m/%Y"),
                    "stage": "Khảo sát nhu cầu",
                    "notes": "Cần báo giá hạ tầng cloud tốc độ cao kết hợp cổng tích hợp API webhook.",
                    "line_items": [
                        {
                            "item_id": "ITM-04",
                            "product_id": "PRD-004",
                            "product_code": "SRV-INTEGRATION",
                            "product_name": "Gói Tích Hợp API Đa Kênh (Facebook Ads + Zalo OA + Website)",
                            "unit": "Hệ thống",
                            "quantity": 2,
                            "unit_price": 8000000,
                            "discount_type": DISCOUNT_TYPE_PERCENT,
                            "discount_value": 0,
                            "description": "Kết nối Webhook đồng bộ đơn hàng & vận đơn đa kênh"
                        },
                        {
                            "item_id": "ITM-05",
                            "product_id": "PRD-005",
                            "product_code": "SRV-CLOUD-BACKUP",
                            "product_name": "Hạ tầng Cloud Dedicated Server & Sao lưu tự động hàng ngày",
                            "unit": "Năm",
                            "quantity": 1,
                            "unit_price": 18000000,
                            "discount_type": DISCOUNT_TYPE_PERCENT,
                            "discount_value": 0,
                            "description": "Máy chủ đám mây hiệu năng cao tải 50.000 vận đơn/ngày"
                        }
                    ]
                },
                "OPP-403": {
                    "id": "OPP-403",
                    "title": "Bản quyền & Triển khai CRM cho Chuỗi Bán lẻ Thời trang Nova Chic",
                    "account_name": "Công ty TNHH Bán lẻ & Thời trang Nova Chic",
                    "tax_id": "0109556677",
                    "contact_name": "Bà Vũ Mai Phương",
                    "contact_title": "Trưởng phòng Bán lẻ",
                    "contact_phone": "0966.333.222",
                    "contact_email": "phuong.vu@novachic.vn",
                    "address": "Tầng 3, Vincom Center, 191 Bà Triệu, Hai Bà Trưng, Hà Nội",
                    "sales_rep_id": "usr-02",
                    "sales_rep_name": "Trần Thị Mai",
                    "inquiry_time": (now - timedelta(hours=4)).strftime("%H:%M %d/%m/%Y"),
                    "expected_closing": (now + timedelta(days=10)).strftime("%d/%m/%Y"),
                    "stage": "Báo giá & Đề xuất",
                    "notes": "Khách muốn chiết khấu đặc biệt dịp khai trương thêm 3 chi nhánh mới.",
                    "line_items": [
                        {
                            "item_id": "ITM-06",
                            "product_id": "PRD-001",
                            "product_code": "CRM-ENTERPRISE",
                            "product_name": "Bản quyền AutoLead CRM Enterprise (Gói 1 năm / 20 users)",
                            "unit": "Gói / Năm",
                            "quantity": 1,
                            "unit_price": 24000000,
                            "discount_type": DISCOUNT_TYPE_PERCENT,
                            "discount_value": 0,
                            "description": "Hệ thống quản lý khách hàng VIP và thẻ thành viên tích điểm"
                        }
                    ]
                }
            }

            # 4. Danh sách Báo giá ban đầu (Quotes)
            # Khởi tạo một số báo giá ở trạng thái khác nhau để demo trực quan:
            # - QUOTE-501: Bản nháp lưu dở (AC5: Lưu nháp và sửa tiếp được)
            # - QUOTE-502: Báo giá chờ duyệt do chiết khấu 15% >= 10% (AC3: Cảnh báo & duyệt)
            # - QUOTE-503: Báo giá đã hoàn tất và gửi khách hàng thành công
            self.quotes = {}

            # Tạo Quote 501 mẫu: Bản nháp lưu dở từ OPP-402
            draft_items = [
                {
                    "item_id": "QITM-101",
                    "product_id": "PRD-004",
                    "product_code": "SRV-INTEGRATION",
                    "product_name": "Gói Tích Hợp API Đa Kênh (Facebook Ads + Zalo OA + Website)",
                    "unit": "Hệ thống",
                    "quantity": 2,
                    "unit_price": 8000000,
                    "discount_type": DISCOUNT_TYPE_PERCENT,
                    "discount_value": 5.0,  # Chiết khấu 5%
                    "description": "Kết nối Webhook đồng bộ đơn hàng"
                },
                {
                    "item_id": "QITM-102",
                    "product_id": "PRD-005",
                    "product_code": "SRV-CLOUD-BACKUP",
                    "product_name": "Hạ tầng Cloud Dedicated Server & Sao lưu tự động hàng ngày",
                    "unit": "Năm",
                    "quantity": 1,
                    "unit_price": 18000000,
                    "discount_type": DISCOUNT_TYPE_AMOUNT,
                    "discount_value": 1000000,  # Giảm 1.000.000 đ
                    "description": "Dedicated Cloud Server chuẩn SLA 99.9%"
                }
            ]
            self._insert_demo_quote(
                quote_id="QUOTE-501",
                quote_number="BG-2026-0501",
                title="Báo giá Hệ thống Cloud & API Tích hợp - Logistics Đại Nam",
                opp_id="OPP-402",
                status=STATUS_DRAFT,
                items=draft_items,
                sales_rep_id="usr-01",
                validity_days=15,
                payment_terms=PAYMENT_TERMS_PRESETS[0],
                delivery_terms=DELIVERY_TERMS_PRESETS[0],
                notes="Bản nháp đang soạn dở lúc 11:30 sáng, đợi buổi chiều chốt thêm điều khoản giao hàng.",
                draft_version=2
            )

            # Tạo Quote 502 mẫu: Chờ duyệt chiết khấu 15% (Chạm ngưỡng duyệt AC3)
            high_discount_items = [
                {
                    "item_id": "QITM-103",
                    "product_id": "PRD-001",
                    "product_code": "CRM-ENTERPRISE",
                    "product_name": "Bản quyền AutoLead CRM Enterprise (Gói 1 năm / 20 users)",
                    "unit": "Gói / Năm",
                    "quantity": 1,
                    "unit_price": 24000000,
                    "discount_type": DISCOUNT_TYPE_PERCENT,
                    "discount_value": 15.0,  # Chiết khấu dòng 15%
                    "description": "Gói CRM doanh nghiệp"
                },
                {
                    "item_id": "QITM-104",
                    "product_id": "PRD-003",
                    "product_code": "SRV-IMPL-ONBOARD",
                    "product_name": "Dịch vụ Thiết lập Quy trình & Onboarding Chuyên sâu",
                    "unit": "Gói",
                    "quantity": 1,
                    "unit_price": 15000000,
                    "discount_type": DISCOUNT_TYPE_PERCENT,
                    "discount_value": 15.0,  # Chiết khấu dòng 15%
                    "description": "Onboarding chuyên sâu"
                }
            ]
            self._insert_demo_quote(
                quote_id="QUOTE-502",
                quote_number="BG-2026-0502",
                title="Báo giá Gói Ưu Đãi Đặc Biệt Dịp Khai Trương - Chuỗi Nova Chic",
                opp_id="OPP-403",
                status=STATUS_PENDING_APPROVAL,
                items=high_discount_items,
                sales_rep_id="usr-02",
                validity_days=7,
                payment_terms=PAYMENT_TERMS_PRESETS[1],
                delivery_terms=DELIVERY_TERMS_PRESETS[1],
                notes="Đề xuất chiết khấu 15% do khách hàng cam kết mở thêm 3 chi nhánh trong quý 3.",
                draft_version=1
            )

            # 5. Thông báo ban đầu
            self.notifications = [
                {
                    "id": "NOTIF-01",
                    "user_id": "usr-03",
                    "title": "Báo giá chờ phê duyệt chiết khấu",
                    "content": "Báo giá BG-2026-0502 (Nova Chic) có mức chiết khấu 15.0% (vượt ngưỡng 10.0%), đang chờ Trưởng nhóm phê duyệt.",
                    "quote_id": "QUOTE-502",
                    "type": "WARNING",
                    "created_at": (now - timedelta(minutes=45)).strftime("%H:%M:%S %d/%m/%Y"),
                    "is_read": False
                },
                {
                    "id": "NOTIF-02",
                    "user_id": "usr-01",
                    "title": "Cơ hội mới cần gửi báo giá trong ngày",
                    "content": "Cơ hội OPP-401 (Dược phẩm An Bình) vừa nhận câu hỏi sáng nay. Hãy chuẩn bị báo giá gửi trong buổi chiều!",
                    "quote_id": None,
                    "type": "INFO",
                    "created_at": (now - timedelta(hours=2)).strftime("%H:%M:%S %d/%m/%Y"),
                    "is_read": True
                }
            ]

            # 6. Nhật ký hệ thống (Audit Logs)
            self.audit_logs = [
                {
                    "id": "LOG-01",
                    "timestamp": (now - timedelta(minutes=45)).strftime("%H:%M:%S %d/%m/%Y"),
                    "user_name": "Trần Thị Mai",
                    "action": "GỬI DUYỆT BÁO GIÁ",
                    "details": "Báo giá BG-2026-0502 gửi phê duyệt do chiết khấu tổng đạt 15.0% >= ngưỡng 10.0%."
                },
                {
                    "id": "LOG-02",
                    "timestamp": (now - timedelta(hours=1)).strftime("%H:%M:%S %d/%m/%Y"),
                    "user_name": "Nguyễn Văn Hùng",
                    "action": "LƯU NHÁP BÁO GIÁ",
                    "details": "Lưu bản nháp v2 cho Báo giá BG-2026-0501 (Logistics Đại Nam)."
                }
            ]

    def _insert_demo_quote(self, quote_id, quote_number, title, opp_id, status, items,
                           sales_rep_id, validity_days=15, payment_terms="",
                           delivery_terms="", notes="", draft_version=1):
        """Hàm trợ giúp nội bộ để tính toán và chèn báo giá mẫu"""
        opp = self.opportunities.get(opp_id, {})
        now = get_current_time()
        expiry_date = now + timedelta(days=validity_days)

        # Tính toán dòng sản phẩm (AC2)
        processed_items = []
        for itm in items:
            p_itm = self.calculate_line_item(itm)
            processed_items.append(p_itm)

        # Tính toán tổng hợp tài chính (AC3)
        totals = self.calculate_quote_totals(processed_items)

        quote = {
            "id": quote_id,
            "quote_number": quote_number,
            "title": title,
            "opp_id": opp_id,
            "opportunity_title": opp.get("title", ""),
            "account_name": opp.get("account_name", ""),
            "tax_id": opp.get("tax_id", ""),
            "contact_name": opp.get("contact_name", ""),
            "contact_title": opp.get("contact_title", ""),
            "contact_phone": opp.get("contact_phone", ""),
            "contact_email": opp.get("contact_email", ""),
            "address": opp.get("address", ""),
            "sales_rep_id": sales_rep_id,
            "sales_rep_name": self.users.get(sales_rep_id, {}).get("name", "NVKD"),
            "status": status,
            "status_label": STATUS_LABELS.get(status, status),
            "status_color": STATUS_COLORS.get(status, "#64748b"),
            "status_badge_class": STATUS_BADGE_CLASSES.get(status, "badge-slate"),
            # AC1: Dòng sản phẩm kế thừa, sửa lại được
            "items": processed_items,
            "line_items": processed_items,
            # AC2 & AC3: Các chỉ số tài chính tính tự động
            "subtotal": totals["subtotal"],
            "total_line_discount": totals["total_line_discount"],
            "total_discount": totals["total_discount"],
            "overall_discount_percent": totals["overall_discount_percent"],
            "amount_after_discount": totals["amount_after_discount"],
            "vat_percent": totals["vat_percent"],
            "vat_amount": totals["vat_amount"],
            "grand_total": totals["grand_total"],
            "is_approval_required": totals["is_approval_required"],
            "is_warning": totals["is_warning"],
            "warning_message": totals["warning_message"],
            # AC4: Hiệu lực báo giá, điều khoản thanh toán & giao hàng
            "created_at": now.strftime("%H:%M:%S %d/%m/%Y"),
            "validity_days": validity_days,
            "valid_until": expiry_date.strftime("%d/%m/%Y"),
            "valid_until_iso": expiry_date.strftime("%Y-%m-%d"),
            "payment_terms": payment_terms,
            "delivery_terms": delivery_terms,
            "warranty_terms": "Cam kết bảo hành kỹ thuật 12 tháng, hỗ trợ trực tuyến 24/7 với SLA xử lý sự cố trong 2 giờ làm việc.",
            "notes": notes,
            # AC5: Lưu nháp và sửa tiếp được
            "is_draft": (status == STATUS_DRAFT),
            "can_edit": (status in [STATUS_DRAFT, STATUS_REJECTED]),
            "draft_version": draft_version,
            "last_saved_at": now.strftime("%H:%M:%S %d/%m/%Y"),
            "approved_by": None,
            "approved_at": None,
            "approval_note": None,
            "sent_at": None
        }

        self.quotes[quote_id] = quote
        return quote

    # =========================================================================
    # TIÊU CHÍ 1 (AC1): DÒNG SẢN PHẨM ĐƯỢC KẾ THỪA TỪ CƠ HỘI, SỬA LẠI ĐƯỢC
    # =========================================================================

    def create_quote_from_opportunity(self, opp_id, user_id):
        """
        Khởi tạo báo giá mới trực tiếp từ một Cơ hội bán hàng:
        1. Kế thừa toàn bộ thông tin khách hàng, người liên hệ, cơ hội bán hàng.
        2. Tự động sao chép (clone) toàn bộ danh sách dòng sản phẩm từ Cơ hội sang Báo giá.
        3. Cho phép nhân viên kinh doanh chỉnh sửa lại (thêm, sửa, xóa) sau đó.
        4. Trạng thái mặc định là DRAFT (Lưu nháp - AC5).
        """
        with self.lock:
            opp = self.opportunities.get(opp_id)
            if not opp:
                raise ValueError(f"Không tìm thấy Cơ hội bán hàng với mã: {opp_id}")

            self._quote_counter += 1
            quote_id = f"QUOTE-{self._quote_counter}"
            quote_number = f"BG-{datetime.now().year}-{self._quote_counter:04d}"

            user = self.users.get(user_id, {})
            sales_rep_name = user.get("name", opp.get("sales_rep_name", "NVKD"))

            # KẾ THỪA DANH SÁCH SẢN PHẨM TỪ CƠ HỘI (AC1)
            inherited_items = []
            for item in opp.get("line_items", []):
                self._item_counter += 1
                new_item = {
                    "item_id": f"QITM-{self._item_counter}",
                    "product_id": item.get("product_id"),
                    "product_code": item.get("product_code", "PRD-CUSTOM"),
                    "product_name": item.get("product_name", "Sản phẩm"),
                    "unit": item.get("unit", "Cái"),
                    "quantity": float(item.get("quantity", 1)),
                    "unit_price": float(item.get("unit_price", 0)),
                    "discount_type": item.get("discount_type", DISCOUNT_TYPE_PERCENT),
                    "discount_value": float(item.get("discount_value", 0)),
                    "description": item.get("description", "")
                }
                # Tính toán ngay thành tiền của dòng (AC2)
                processed_item = self.calculate_line_item(new_item)
                inherited_items.append(processed_item)

            # Tính toán tài chính tổng quan (AC3)
            totals = self.calculate_quote_totals(inherited_items)

            now = get_current_time()
            validity_days = 15  # Mặc định hiệu lực 15 ngày
            expiry_date = now + timedelta(days=validity_days)

            quote = {
                "id": quote_id,
                "quote_number": quote_number,
                "title": f"Báo giá: {opp.get('title')}",
                "opp_id": opp_id,
                "opportunity_title": opp.get("title", ""),
                "account_name": opp.get("account_name", ""),
                "tax_id": opp.get("tax_id", ""),
                "contact_name": opp.get("contact_name", ""),
                "contact_title": opp.get("contact_title", ""),
                "contact_phone": opp.get("contact_phone", ""),
                "contact_email": opp.get("contact_email", ""),
                "address": opp.get("address", ""),
                "sales_rep_id": user_id,
                "sales_rep_name": sales_rep_name,
                "status": STATUS_DRAFT,
                "status_label": STATUS_LABELS[STATUS_DRAFT],
                "status_color": STATUS_COLORS[STATUS_DRAFT],
                "status_badge_class": STATUS_BADGE_CLASSES[STATUS_DRAFT],
                # AC1: Danh sách sản phẩm kế thừa
                "items": inherited_items,
                "line_items": inherited_items,
                # AC2 & AC3: Chỉ số tài chính
                "subtotal": totals["subtotal"],
                "total_line_discount": totals["total_line_discount"],
                "total_discount": totals["total_discount"],
                "overall_discount_percent": totals["overall_discount_percent"],
                "amount_after_discount": totals["amount_after_discount"],
                "vat_percent": totals["vat_percent"],
                "vat_amount": totals["vat_amount"],
                "grand_total": totals["grand_total"],
                "is_approval_required": totals["is_approval_required"],
                "is_warning": totals["is_warning"],
                "warning_message": totals["warning_message"],
                # AC4: Hiệu lực báo giá, điều khoản thanh toán & giao hàng
                "created_at": now.strftime("%H:%M:%S %d/%m/%Y"),
                "validity_days": validity_days,
                "valid_until": expiry_date.strftime("%d/%m/%Y"),
                "valid_until_iso": expiry_date.strftime("%Y-%m-%d"),
                "payment_terms": PAYMENT_TERMS_PRESETS[0],
                "delivery_terms": DELIVERY_TERMS_PRESETS[0],
                "warranty_terms": "Bảo hành 12 tháng, hỗ trợ kỹ thuật trực tuyến 24/7.",
                "notes": f"Báo giá được tạo từ Cơ hội {opp_id} theo yêu cầu gửi trong buổi chiều.",
                # AC5: Lưu nháp và sửa tiếp được
                "is_draft": True,
                "can_edit": True,
                "draft_version": 1,
                "last_saved_at": now.strftime("%H:%M:%S %d/%m/%Y"),
                "approved_by": None,
                "approved_at": None,
                "approval_note": None,
                "sent_at": None
            }

            self.quotes[quote_id] = quote

            # Ghi nhật ký
            self._add_audit_log(
                user_name=sales_rep_name,
                action="SOẠN BÁO GIÁ MỚI TỪ CƠ HỘI",
                details=f"Tạo báo giá {quote_number} kế thừa {len(inherited_items)} dòng sản phẩm từ Cơ hội {opp_id}."
            )

            return quote

    # =========================================================================
    # TIÊU CHÍ 2 (AC2): NHẬP CHIẾT KHẤU THEO % HOẶC TIỀN, TÍNH LẠI THÀNH TIỀN NGAY
    # =========================================================================

    def calculate_line_item(self, item_dict):
        """
        Tính toán tài chính cho từng dòng sản phẩm:
        - Thành tiền gốc = Số lượng * Đơn giá
        - Nếu chiết khấu theo % (PERCENT):
            Tiền chiết khấu = Thành tiền gốc * (Giá trị % / 100)
        - Nếu chiết khấu theo số tiền (AMOUNT):
            Tiền chiết khấu = Giá trị tiền nhập vào
            (Không vượt quá thành tiền gốc)
        - Thành tiền sau chiết khấu = Thành tiền gốc - Tiền chiết khấu
        """
        item = copy.deepcopy(item_dict)

        try:
            quantity = float(item.get("quantity", 1))
            if quantity < 0:
                quantity = 1
        except (ValueError, TypeError):
            quantity = 1

        try:
            unit_price = float(item.get("unit_price", 0))
            if unit_price < 0:
                unit_price = 0
        except (ValueError, TypeError):
            unit_price = 0

        line_subtotal = quantity * unit_price

        discount_type = item.get("discount_type", DISCOUNT_TYPE_PERCENT)
        try:
            discount_value = float(item.get("discount_value", 0))
            if discount_value < 0:
                discount_value = 0
        except (ValueError, TypeError):
            discount_value = 0

        discount_amount = 0.0
        discount_percent_computed = 0.0

        if discount_type == DISCOUNT_TYPE_PERCENT:
            # Chiết khấu theo %
            if discount_value > 100.0:
                discount_value = 100.0
            discount_amount = line_subtotal * (discount_value / 100.0)
            discount_percent_computed = discount_value
        else:
            # Chiết khấu theo số tiền cố định (VNĐ)
            discount_type = DISCOUNT_TYPE_AMOUNT
            if discount_value > line_subtotal:
                discount_amount = line_subtotal  # Chiết khấu tối đa bằng thành tiền gốc
            else:
                discount_amount = discount_value

            if line_subtotal > 0:
                discount_percent_computed = round((discount_amount / line_subtotal) * 100.0, 2)
            else:
                discount_percent_computed = 0.0

        line_total = line_subtotal - discount_amount

        item["quantity"] = quantity
        item["unit_price"] = unit_price
        item["subtotal"] = line_subtotal
        item["discount_type"] = discount_type
        item["discount_value"] = discount_value
        item["discount_amount"] = discount_amount
        item["discount_percent_computed"] = discount_percent_computed
        item["total"] = line_total

        # Format hiển thị
        item["subtotal_formatted"] = format_currency(line_subtotal)
        item["discount_amount_formatted"] = format_currency(discount_amount)
        item["total_formatted"] = format_currency(line_total)

        return item

    # =========================================================================
    # TIÊU CHÍ 3 (AC3): HIỂN THỊ MỨC CHIẾT KHẤU TỔNG VÀ CẢNH BÁO NGƯỠNG CẦN DUYỆT
    # =========================================================================

    def calculate_quote_totals(self, items, vat_percent=DEFAULT_VAT_PERCENT):
        """
        Tính toán tổng hợp tài chính của báo giá:
        1. Tổng tiền trước chiết khấu (Subtotal)
        2. Tổng chiết khấu từng dòng (Total Line Discounts)
        3. Tỷ lệ chiết khấu tổng (%) = (Tổng chiết khấu / Tổng trước chiết khấu) * 100%
        4. Tiền sau chiết khấu = Subtotal - Total Discount
        5. Thuế VAT (8%)
        6. Tổng thanh toán cuối cùng (Grand Total)
        7. CẢNH BÁO KHI CHẠM NGƯỠNG CẦN DUYỆT:
           - Nếu Mức chiết khấu tổng >= 10.0%:
             Bật cờ is_approval_required = True kèm cảnh báo màu đỏ/vàng.
             Báo giá bắt buộc phải có Trưởng nhóm / Giám đốc duyệt mới được gửi.
           - Nếu Mức chiết khấu tổng >= 8.0%:
             Bật cờ cảnh báo cận kề is_warning = True.
        """
        subtotal = 0.0
        total_line_discount = 0.0

        for item in items:
            subtotal += float(item.get("subtotal", 0))
            total_line_discount += float(item.get("discount_amount", 0))

        total_discount = total_line_discount

        if subtotal > 0:
            overall_discount_percent = round((total_discount / subtotal) * 100.0, 2)
        else:
            overall_discount_percent = 0.0

        amount_after_discount = subtotal - total_discount
        vat_amount = round(amount_after_discount * (vat_percent / 100.0), 0)
        grand_total = amount_after_discount + vat_amount

        # Kiểm tra ngưỡng phê duyệt (AC3)
        is_approval_required = (overall_discount_percent >= DISCOUNT_APPROVAL_THRESHOLD_PERCENT)
        is_warning = (overall_discount_percent >= DISCOUNT_WARNING_THRESHOLD_PERCENT)

        warning_message = ""
        if is_approval_required:
            warning_message = (
                f"⚠️ CẢNH BÁO: Mức chiết khấu tổng đạt {overall_discount_percent}% "
                f"(đã chạm/vượt ngưỡng cho phép {DISCOUNT_APPROVAL_THRESHOLD_PERCENT}% của NVKD). "
                f"Báo giá này BẮT BUỘC PHẢI ĐƯỢC TRƯỞNG NHÓM / GIÁM ĐỐC DUYỆT trước khi gửi khách hàng!"
            )
        elif is_warning:
            warning_message = (
                f"⚡ LƯU Ý: Mức chiết khấu tổng đạt {overall_discount_percent}%, "
                f"tiệm cận ngưỡng cần duyệt ({DISCOUNT_APPROVAL_THRESHOLD_PERCENT}%). "
                f"Vui lòng cân nhắc kỹ trước khi tăng thêm chiết khấu."
            )

        return {
            "subtotal": subtotal,
            "subtotal_formatted": format_currency(subtotal),
            "total_line_discount": total_line_discount,
            "total_discount": total_discount,
            "total_discount_formatted": format_currency(total_discount),
            "overall_discount_percent": overall_discount_percent,
            "amount_after_discount": amount_after_discount,
            "amount_after_discount_formatted": format_currency(amount_after_discount),
            "vat_percent": vat_percent,
            "vat_amount": vat_amount,
            "vat_amount_formatted": format_currency(vat_amount),
            "grand_total": grand_total,
            "grand_total_formatted": format_currency(grand_total),
            "is_approval_required": is_approval_required,
            "is_warning": is_warning,
            "warning_message": warning_message,
            "approval_threshold_percent": DISCOUNT_APPROVAL_THRESHOLD_PERCENT
        }

    # =========================================================================
    # TIÊU CHÍ 4 & 5 (AC4 & AC5): HIỆU LỰC, ĐIỀU KHOẢN, LƯU NHÁP & SỬA TIẾP
    # =========================================================================

    def save_draft(self, quote_id, form_data, user_id):
        """
        Lưu nháp báo giá và cho phép sửa tiếp (AC5):
        - Cho phép chỉnh sửa danh sách sản phẩm (thêm/sửa/xóa).
        - Cập nhật chiết khấu từng dòng theo % hoặc tiền (AC2).
        - Cập nhật hiệu lực, điều khoản thanh toán, điều khoản giao hàng (AC4).
        - Tính lại chiết khấu tổng và cảnh báo nếu chạm ngưỡng duyệt (AC3).
        - Trạng thái được giữ nguyên là DRAFT (Bản nháp), tăng version nháp.
        """
        with self.lock:
            quote = self.quotes.get(quote_id)
            if not quote:
                raise ValueError(f"Không tìm thấy Báo giá với mã: {quote_id}")

            if not quote.get("can_edit", True):
                raise PermissionError(
                    f"Báo giá {quote_id} đang ở trạng thái '{quote.get('status_label')}' và không thể chỉnh sửa!"
                )

            # Xử lý các dòng sản phẩm từ form_data
            raw_items = form_data.get("items", [])
            processed_items = []
            for itm in raw_items:
                if not itm.get("product_name") and not itm.get("product_id"):
                    continue
                # Gán item_id nếu chưa có
                if not itm.get("item_id"):
                    self._item_counter += 1
                    itm["item_id"] = f"QITM-{self._item_counter}"
                p_item = self.calculate_line_item(itm)
                processed_items.append(p_item)

            if not processed_items:
                raise ValueError("Báo giá phải có ít nhất 01 dòng sản phẩm!")

            # Tính toán lại tài chính
            totals = self.calculate_quote_totals(processed_items)

            # Cập nhật thông tin tiêu đề và khách hàng
            if form_data.get("title"):
                quote["title"] = form_data.get("title").strip()
            if form_data.get("contact_name"):
                quote["contact_name"] = form_data.get("contact_name").strip()
            if form_data.get("contact_phone"):
                quote["contact_phone"] = form_data.get("contact_phone").strip()
            if form_data.get("contact_email"):
                quote["contact_email"] = form_data.get("contact_email").strip()
            if form_data.get("address"):
                quote["address"] = form_data.get("address").strip()

            # AC4: Cập nhật Hiệu lực báo giá, Điều khoản thanh toán, Điều khoản giao hàng
            try:
                validity_days = int(form_data.get("validity_days", quote.get("validity_days", 15)))
            except (ValueError, TypeError):
                validity_days = 15

            now = get_current_time()
            valid_until_custom = form_data.get("valid_until_custom")
            if valid_until_custom:
                try:
                    expiry_date = datetime.strptime(valid_until_custom, "%Y-%m-%d")
                    validity_days = (expiry_date - now).days
                    if validity_days < 1:
                        validity_days = 1
                except Exception:
                    expiry_date = now + timedelta(days=validity_days)
            else:
                expiry_date = now + timedelta(days=validity_days)

            quote["validity_days"] = validity_days
            quote["valid_until"] = expiry_date.strftime("%d/%m/%Y")
            quote["valid_until_iso"] = expiry_date.strftime("%Y-%m-%d")

            quote["payment_terms"] = form_data.get("payment_terms", quote.get("payment_terms", "")).strip()
            quote["delivery_terms"] = form_data.get("delivery_terms", quote.get("delivery_terms", "")).strip()
            quote["warranty_terms"] = form_data.get("warranty_terms", quote.get("warranty_terms", "")).strip()
            quote["notes"] = form_data.get("notes", quote.get("notes", "")).strip()

            # Cập nhật sản phẩm & tài chính
            quote["items"] = processed_items
            quote["line_items"] = processed_items
            quote["subtotal"] = totals["subtotal"]
            quote["total_line_discount"] = totals["total_line_discount"]
            quote["total_discount"] = totals["total_discount"]
            quote["overall_discount_percent"] = totals["overall_discount_percent"]
            quote["amount_after_discount"] = totals["amount_after_discount"]
            quote["vat_percent"] = totals["vat_percent"]
            quote["vat_amount"] = totals["vat_amount"]
            quote["grand_total"] = totals["grand_total"]
            quote["is_approval_required"] = totals["is_approval_required"]
            quote["is_warning"] = totals["is_warning"]
            quote["warning_message"] = totals["warning_message"]

            # AC5: Giữ trạng thái DRAFT, tăng version nháp
            quote["status"] = STATUS_DRAFT
            quote["status_label"] = STATUS_LABELS[STATUS_DRAFT]
            quote["status_color"] = STATUS_COLORS[STATUS_DRAFT]
            quote["status_badge_class"] = STATUS_BADGE_CLASSES[STATUS_DRAFT]
            quote["is_draft"] = True
            quote["can_edit"] = True
            quote["draft_version"] = quote.get("draft_version", 1) + 1
            quote["last_saved_at"] = now.strftime("%H:%M:%S %d/%m/%Y")

            user = self.users.get(user_id, {})
            self._add_audit_log(
                user_name=user.get("name", "NVKD"),
                action="LƯU NHÁP BÁO GIÁ",
                details=f"Đã lưu nháp phiên bản v{quote['draft_version']} cho {quote['quote_number']}. "
                        f"Tổng tiền: {format_currency(totals['grand_total'])}, Chiết khấu: {totals['overall_discount_percent']}%."
            )

            return quote

    def submit_quote(self, quote_id, user_id):
        """
        Hoàn tất báo giá để gửi khách hàng hoặc gửi duyệt:
        - Nếu mức chiết khấu tổng >= 10.0% (AC3):
          Chuyển sang trạng thái PENDING_APPROVAL (Chờ duyệt chiết khấu).
          Tự động sinh thông báo cảnh báo gửi tới Trưởng nhóm / Giám đốc.
        - Nếu mức chiết khấu tổng < 10.0%:
          Chuyển sang trạng thái SENT (Đã gửi khách hàng) - đáp ứng mục tiêu
          gửi báo giá ngay trong buổi chiều cùng ngày khách hỏi!
        """
        with self.lock:
            quote = self.quotes.get(quote_id)
            if not quote:
                raise ValueError(f"Không tìm thấy Báo giá: {quote_id}")

            now = get_current_time()
            user = self.users.get(user_id, {})

            if quote.get("is_approval_required"):
                # Chiết khấu chạm ngưỡng cần duyệt (AC3)
                quote["status"] = STATUS_PENDING_APPROVAL
                quote["status_label"] = STATUS_LABELS[STATUS_PENDING_APPROVAL]
                quote["status_color"] = STATUS_COLORS[STATUS_PENDING_APPROVAL]
                quote["status_badge_class"] = STATUS_BADGE_CLASSES[STATUS_PENDING_APPROVAL]
                quote["is_draft"] = False
                quote["can_edit"] = False

                # Sinh thông báo cho Trưởng nhóm (Team Lead)
                self._notif_counter += 1
                self.notifications.append({
                    "id": f"NOTIF-{self._notif_counter}",
                    "user_id": "usr-03", # Trưởng nhóm
                    "title": f"Báo giá {quote['quote_number']} cần phê duyệt chiết khấu",
                    "content": f"Báo giá cho {quote['account_name']} có chiết khấu {quote['overall_discount_percent']}% (vượt ngưỡng {DISCOUNT_APPROVAL_THRESHOLD_PERCENT}%).",
                    "quote_id": quote_id,
                    "type": "WARNING",
                    "created_at": now.strftime("%H:%M:%S %d/%m/%Y"),
                    "is_read": False
                })

                self._add_audit_log(
                    user_name=user.get("name", "NVKD"),
                    action="GỬI DUYỆT BÁO GIÁ",
                    details=f"Báo giá {quote['quote_number']} được gửi duyệt vì chiết khấu {quote['overall_discount_percent']}% >= 10.0%."
                )
            else:
                # Chiết khấu hợp lệ, gửi khách ngay trong buổi chiều!
                quote["status"] = STATUS_SENT
                quote["status_label"] = STATUS_LABELS[STATUS_SENT]
                quote["status_color"] = STATUS_COLORS[STATUS_SENT]
                quote["status_badge_class"] = STATUS_BADGE_CLASSES[STATUS_SENT]
                quote["is_draft"] = False
                quote["can_edit"] = False
                quote["sent_at"] = now.strftime("%H:%M:%S %d/%m/%Y")

                self._add_audit_log(
                    user_name=user.get("name", "NVKD"),
                    action="GỬI BÁO GIÁ CHO KHÁCH HÀNG",
                    details=f"Báo giá {quote['quote_number']} đã được gửi chính thức tới {quote['contact_name']} ({quote['account_name']}) trong buổi chiều."
                )

            return quote

    def approve_quote(self, quote_id, approver_id, note=""):
        """Trưởng nhóm hoặc Giám đốc duyệt chiết khấu báo giá (AC3)"""
        with self.lock:
            quote = self.quotes.get(quote_id)
            if not quote:
                raise ValueError(f"Không tìm thấy Báo giá: {quote_id}")

            approver = self.users.get(approver_id, {})
            if approver.get("role") not in [ROLE_TEAM_LEAD, ROLE_DIRECTOR]:
                raise PermissionError("Chỉ Trưởng nhóm hoặc Giám đốc kinh doanh mới có quyền duyệt chiết khấu!")

            now = get_current_time()
            quote["status"] = STATUS_APPROVED
            quote["status_label"] = STATUS_LABELS[STATUS_APPROVED]
            quote["status_color"] = STATUS_COLORS[STATUS_APPROVED]
            quote["status_badge_class"] = STATUS_BADGE_CLASSES[STATUS_APPROVED]
            quote["approved_by"] = approver.get("name")
            quote["approved_at"] = now.strftime("%H:%M:%S %d/%m/%Y")
            quote["approval_note"] = note.strip() if note else "Đã phê duyệt mức chiết khấu theo chính sách dự án."
            quote["can_edit"] = False

            # Thông báo lại cho NVKD
            self._notif_counter += 1
            self.notifications.append({
                "id": f"NOTIF-{self._notif_counter}",
                "user_id": quote.get("sales_rep_id"),
                "title": f"Báo giá {quote['quote_number']} ĐÃ ĐƯỢC DUYỆT 🎉",
                "content": f"{approver.get('name')} đã duyệt chiết khấu {quote['overall_discount_percent']}%. Bạn có thể gửi khách hàng ngay!",
                "quote_id": quote_id,
                "type": "SUCCESS",
                "created_at": now.strftime("%H:%M:%S %d/%m/%Y"),
                "is_read": False
            })

            self._add_audit_log(
                user_name=approver.get("name"),
                action="PHÊ DUYỆT CHIẾT KHẤU",
                details=f"Duyệt chiết khấu {quote['overall_discount_percent']}% cho Báo giá {quote['quote_number']}. Ghi chú: {quote['approval_note']}"
            )

            return quote

    def reject_quote(self, quote_id, rejecter_id, reason=""):
        """Trưởng nhóm từ chối duyệt chiết khấu, trả lại cho NVKD sửa tiếp (AC3 & AC5)"""
        with self.lock:
            quote = self.quotes.get(quote_id)
            if not quote:
                raise ValueError(f"Không tìm thấy Báo giá: {quote_id}")

            rejecter = self.users.get(rejecter_id, {})
            if rejecter.get("role") not in [ROLE_TEAM_LEAD, ROLE_DIRECTOR]:
                raise PermissionError("Chỉ Trưởng nhóm hoặc Giám đốc mới có quyền từ chối duyệt!")

            now = get_current_time()
            quote["status"] = STATUS_REJECTED
            quote["status_label"] = STATUS_LABELS[STATUS_REJECTED]
            quote["status_color"] = STATUS_COLORS[STATUS_REJECTED]
            quote["status_badge_class"] = STATUS_BADGE_CLASSES[STATUS_REJECTED]
            quote["can_edit"] = True  # Cho phép NVKD mở lại và sửa tiếp (AC5)
            quote["approval_note"] = reason.strip() if reason else "Mức chiết khấu quá cao, yêu cầu giảm chiết khấu xuống < 10%."

            # Thông báo cho NVKD
            self._notif_counter += 1
            self.notifications.append({
                "id": f"NOTIF-{self._notif_counter}",
                "user_id": quote.get("sales_rep_id"),
                "title": f"Báo giá {quote['quote_number']} bị từ chối duyệt ❌",
                "content": f"Lý do: {quote['approval_note']}. Vui lòng mở lại báo giá để điều chỉnh chiết khấu.",
                "quote_id": quote_id,
                "type": "DANGER",
                "created_at": now.strftime("%H:%M:%S %d/%m/%Y"),
                "is_read": False
            })

            self._add_audit_log(
                user_name=rejecter.get("name"),
                action="TỪ CHỐI DUYỆT CHIẾT KHẤU",
                details=f"Từ chối chiết khấu {quote['overall_discount_percent']}% cho Báo giá {quote['quote_number']}. Lý do: {quote['approval_note']}"
            )

            return quote

    # =========================================================================
    # CÁC HÀM TRỢ GIÚP TRUY VẤN DỮ LIỆU
    # =========================================================================

    def get_opportunity(self, opp_id):
        with self.lock:
            return copy.deepcopy(self.opportunities.get(opp_id))

    def get_all_opportunities(self):
        with self.lock:
            return copy.deepcopy(list(self.opportunities.values()))

    def get_quote(self, quote_id):
        with self.lock:
            quote = self.quotes.get(quote_id)
            if not quote:
                return None
            return copy.deepcopy(quote)

    def get_all_quotes(self, status=None, user_id=None):
        with self.lock:
            res = list(self.quotes.values())
            if status:
                res = [q for q in res if q.get("status") == status]
            if user_id:
                # Lọc theo nhân viên kinh doanh
                res = [q for q in res if q.get("sales_rep_id") == user_id]
            # Sắp xếp mới nhất lên đầu
            res.sort(key=lambda x: x.get("id", ""), reverse=True)
            return copy.deepcopy(res)

    def get_product(self, product_id):
        with self.lock:
            return copy.deepcopy(self.products.get(product_id))

    def get_all_products(self):
        with self.lock:
            return copy.deepcopy(list(self.products.values()))

    def get_user(self, user_id):
        with self.lock:
            return copy.deepcopy(self.users.get(user_id))

    def get_all_users(self):
        with self.lock:
            return copy.deepcopy(self.users)

    def get_kpis(self):
        """Thống kê KPI tổng quan cho Dashboard"""
        with self.lock:
            all_q = list(self.quotes.values())
            draft_count = sum(1 for q in all_q if q.get("status") == STATUS_DRAFT)
            pending_count = sum(1 for q in all_q if q.get("status") == STATUS_PENDING_APPROVAL)
            approved_count = sum(1 for q in all_q if q.get("status") == STATUS_APPROVED)
            sent_count = sum(1 for q in all_q if q.get("status") == STATUS_SENT)
            total_value = sum(q.get("grand_total", 0) for q in all_q if q.get("status") in [STATUS_SENT, STATUS_APPROVED, STATUS_ACCEPTED])

            return {
                "total_quotes": len(all_q),
                "draft_quotes": draft_count,
                "pending_approval": pending_count,
                "approved_quotes": approved_count,
                "sent_quotes": sent_count,
                "total_pipeline_value": total_value,
                "total_pipeline_value_formatted": format_currency(total_value),
                "opportunities_count": len(self.opportunities)
            }

    def _add_audit_log(self, user_name, action, details):
        """Ghi nhận nhật ký kiểm toán hệ thống"""
        self._log_counter += 1
        self.audit_logs.insert(0, {
            "id": f"LOG-{self._log_counter}",
            "timestamp": get_current_time().strftime("%H:%M:%S %d/%m/%Y"),
            "user_name": user_name,
            "action": action,
            "details": details
        })


# Biến instance singleton toàn cục
db = Database()

    def get_product_catalog_summary(self):
        """Thống kê tổng hợp danh mục sản phẩm và bảng giá tiêu chuẩn"""
        prods = self.get_products()
        return {
            'total_products': len(prods),
            'categories': sorted(list(set(p.get('category', 'General') for p in prods))),
            'active_catalog_version': '2026.Q4'
        }
