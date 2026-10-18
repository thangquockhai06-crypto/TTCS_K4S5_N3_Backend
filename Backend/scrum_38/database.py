"""
Cơ sở dữ liệu In-Memory Thread-Safe & Động cơ Chuyển Báo Giá thành Hợp Đồng (SCRUM-35 / SCRUM-38)
Subtasks: SCRUM-236 (FE) & SCRUM-237 (BE)

Đáp ứng đầy đủ 4 Tiêu chí chấp nhận (Acceptance Criteria):
1. Hợp đồng kế thừa toàn bộ dòng sản phẩm và giá đã chốt, không nhập lại.
2. Khai báo số hợp đồng, ngày ký, ngày hiệu lực, ngày hết hạn, điều khoản thanh toán.
3. Cơ hội tương ứng tự động chuyển sang Đóng thắng với giá trị đúng bằng giá trị hợp đồng.
4. Số hợp đồng là duy nhất.
"""

import threading
import copy
import re
from datetime import datetime, date, timedelta

from config import (
    ROLE_ACCOUNTANT,
    ROLE_SALES_REP,
    ROLE_SALES_LEAD,
    ROLE_DIRECTOR,
    QUOTE_STATUS_DRAFT,
    QUOTE_STATUS_SENT,
    QUOTE_STATUS_ACCEPTED,
    QUOTE_STATUS_CONVERTED,
    QUOTE_STATUS_REJECTED,
    OPP_STAGE_QUALIFIED,
    OPP_STAGE_PROPOSAL,
    OPP_STAGE_NEGOTIATION,
    OPP_STAGE_CLOSED_WON,
    OPP_STAGE_CLOSED_LOST,
    CONTRACT_STATUS_ACTIVE,
    CONTRACT_STATUS_EXPIRED,
    CONTRACT_STATUS_TERMINATED,
    PAYMENT_TERMS_OPTIONS,
    SELLER_INFO,
    DEFAULT_VAT_PERCENT
)


class DuplicateContractNumberError(Exception):
    """Ngoại lệ khi số hợp đồng bị trùng lặp trong hệ thống (Vi phạm Tiêu chí 4)"""
    pass


class InvalidQuoteStatusError(Exception):
    """Ngoại lệ khi chuyển đổi báo giá chưa được chấp nhận thành hợp đồng"""
    pass


class ContractValidationError(Exception):
    """Ngoại lệ khi thông tin khai báo hợp đồng không hợp lệ (Vi phạm Tiêu chí 2)"""
    pass


def get_current_time():
    """Lấy thời gian hiện tại"""
    return datetime.now()


def format_currency(amount):
    """Định dạng tiền tệ VND chuyên nghiệp (Ví dụ: 83.710.000 đ)"""
    try:
        val = float(amount or 0)
        return f"{val:,.0f} đ".replace(",", ".")
    except Exception:
        return f"{amount} đ"


def format_date(dt):
    """Định dạng ngày tháng chuẩn hiển thị DD/MM/YYYY"""
    if not dt:
        return ""
    if isinstance(dt, str):
        try:
            # Thử parse định dạng YYYY-MM-DD
            d = datetime.strptime(dt[:10], "%Y-%m-%d")
            return d.strftime("%d/%m/%Y")
        except Exception:
            return dt
    if isinstance(dt, (datetime, date)):
        return dt.strftime("%d/%m/%Y")
    return str(dt)


def format_datetime(dt):
    """Định dạng ngày giờ hiển thị HH:MM:SS DD/MM/YYYY"""
    if not dt:
        return ""
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except Exception:
            return dt
    if isinstance(dt, (datetime, date)):
        return dt.strftime("%H:%M:%S %d/%m/%Y")
    return str(dt)


class Database:
    """
    Cơ sở dữ liệu In-Memory Thread-Safe quản lý chuyển Báo giá thành Hợp đồng & Đồng bộ Cơ hội CRM.
    Đảm bảo tính nhất quán (AC1), tính toàn vẹn pháp lý (AC2), đồng bộ Đóng thắng (AC3) và tính duy nhất (AC4).
    """

    def __init__(self):
        self.lock = threading.RLock()
        self.quotations = {}
        self.opportunities = {}
        self.contracts = {}
        # Chỉ mục kiểm tra duy nhất: normalized_contract_number (lowercase, trimmed) -> contract_id
        self.contract_number_index = {}
        self.audit_logs = []
        self._contract_id_counter = 100

        self._seed_sample_data()

    def _normalize_contract_number(self, contract_number):
        """Chuẩn hóa số hợp đồng để so sánh không phân biệt hoa thường và khoảng trắng"""
        if not contract_number:
            return ""
        return re.sub(r"\s+", " ", str(contract_number).strip().lower())

    def _seed_sample_data(self):
        """Khởi tạo dữ liệu mẫu chuẩn cho hệ thống AutoLead CRM CPQ"""
        # 1. Cơ hội kinh doanh mẫu (Opportunities)
        self.opportunities = {
            "OPP-2026-101": {
                "opp_id": "OPP-2026-101",
                "name": "Dự án Triển khai CRM Enterprise cho VinaTech Group",
                "customer_name": "Công ty Cổ phần Tập đoàn Công nghệ VinaTech",
                "stage": OPP_STAGE_NEGOTIATION,  # Đang đàm phán hợp đồng
                "value": 80000000,                # Giá trị dự kiến ban đầu trước khi chốt hợp đồng
                "assigned_sales_rep": "Trần Văn Nam",
                "expected_close_date": "2026-10-31",
                "quote_id": "BG-2026-001",
                "contract_id": None,
                "win_date": None,
                "created_at": "2026-10-01 09:00:00",
                "notes": "Khách hàng đã đồng ý phương án kỹ thuật và báo giá, chờ Kế toán lập hợp đồng."
            },
            "OPP-2026-102": {
                "opp_id": "OPP-2026-102",
                "name": "Nâng cấp Module CPQ & Cổng thanh toán OCB Bank",
                "customer_name": "Ngân hàng TMCP Phương Đông (OCB)",
                "stage": OPP_STAGE_NEGOTIATION,
                "value": 50000000,
                "assigned_sales_rep": "Lê Thị Bích Ngọc",
                "expected_close_date": "2026-11-15",
                "quote_id": "BG-2026-002",
                "contract_id": None,
                "win_date": None,
                "created_at": "2026-10-05 14:30:00",
                "notes": "Đã thương thảo xong điều khoản thanh toán Net 30, báo giá đã được duyệt chấp thuận."
            },
            "OPP-2026-103": {
                "opp_id": "OPP-2026-103",
                "name": "Bản quyền AutoLead CRM Cloud - FPT Software Sài Gòn",
                "customer_name": "Công ty TNHH Phần mềm FPT Miền Nam",
                "stage": OPP_STAGE_CLOSED_WON,   # Đã đóng thắng do hợp đồng trước đó đã ký
                "value": 125000000,              # Giá trị khớp 100% hợp đồng đã lập
                "assigned_sales_rep": "Trần Văn Nam",
                "expected_close_date": "2026-10-05",
                "quote_id": "BG-2026-003",
                "contract_id": "CTR-2026-001",
                "win_date": "2026-10-05",
                "created_at": "2026-09-20 08:30:00",
                "notes": "Hợp đồng đã hoàn tất và đóng thắng thành công."
            },
            "OPP-2026-104": {
                "opp_id": "OPP-2026-104",
                "name": "Hệ thống Báo giá tự động Logistics Viettel Post",
                "customer_name": "Tổng Công ty Cổ phần Bưu chính Viettel",
                "stage": OPP_STAGE_PROPOSAL,
                "value": 65000000,
                "assigned_sales_rep": "Vũ Đình Trọng",
                "expected_close_date": "2026-11-20",
                "quote_id": "BG-2026-004",
                "contract_id": None,
                "win_date": None,
                "created_at": "2026-10-10 11:00:00",
                "notes": "Báo giá mới gửi cho khách, khách chưa phản hồi chấp nhận."
            }
        }

        # 2. Báo giá mẫu (Quotations)
        self.quotations = {
            # Báo giá 1: Đã chấp nhận, ĐỦ ĐIỀU KIỆN chuyển thành Hợp đồng
            "BG-2026-001": {
                "quote_id": "BG-2026-001",
                "title": "Báo giá Phần mềm AutoLead CRM Enterprise & Dịch vụ Triển khai",
                "customer_name": "Công ty Cổ phần Tập đoàn Công nghệ VinaTech",
                "customer_tax_code": "0108999888",
                "customer_address": "Tòa nhà VinaTech Tower, Phố Duy Tân, Q. Cầu Giấy, TP. Hà Nội",
                "customer_contact": "Bà Lê Hoàng Mai",
                "customer_position": "Giám đốc Vận hành",
                "customer_phone": "0912.888.999",
                "customer_email": "mai.le@vinatech.vn",
                "opportunity_id": "OPP-2026-101",
                "opportunity_name": "Dự án Triển khai CRM Enterprise cho VinaTech Group",
                "status": QUOTE_STATUS_ACCEPTED,  # ĐÃ CHẤP NHẬN
                "contract_id": None,
                "contract_number": None,
                "payment_terms": "Đợt 1: 50% khi ký hợp đồng - Đợt 2: 50% khi bàn giao nghiệm thu",
                "created_by": "Trần Văn Nam (NVKD)",
                "created_at": "2026-10-02 10:15:00",
                "accepted_at": "2026-10-15 16:45:00",
                # Dòng sản phẩm và giá đã chốt với khách hàng (Kế thừa nguyên vẹn vào Hợp đồng - AC1)
                "items": [
                    {
                        "item_id": 1,
                        "product_id": "PROD-CRM-ENT",
                        "product_name": "AutoLead CRM Enterprise (Gói Doanh Nghiệp)",
                        "unit": "Gói/Năm",
                        "quantity": 2,
                        "unit_price": 24000000,
                        "discount_percent": 5.0,
                        "discount_amount": 2400000,
                        "line_total": 45600000
                    },
                    {
                        "item_id": 2,
                        "product_id": "PROD-CPQ-MOD",
                        "product_name": "Module CPQ Nâng Cao & Quản Lý Phiên Bản Báo Giá",
                        "unit": "Module",
                        "quantity": 2,
                        "unit_price": 8500000,
                        "discount_percent": 0.0,
                        "discount_amount": 0,
                        "line_total": 17000000
                    },
                    {
                        "item_id": 3,
                        "product_id": "PROD-SRV-TRAIN",
                        "product_name": "Gói Dịch Vụ Đào Tạo & Triển Khai Onsite Toàn Diện",
                        "unit": "Gói",
                        "quantity": 1,
                        "unit_price": 15000000,
                        "discount_percent": 10.0,
                        "discount_amount": 1500000,
                        "line_total": 13500000
                    }
                ],
                "subtotal": 80000000,           # Tổng tiền trước chiết khấu
                "discount_total": 3900000,      # Tổng chiết khấu đã duyệt
                "after_discount": 76100000,     # Tiền trước thuế
                "vat_percent": 10.0,            # Thuế VAT 10%
                "vat_amount": 7610000,          # Tiền thuế VAT
                "grand_total": 83710000         # TỔNG GIÁ TRỊ ĐÃ CHỐT = 83.710.000 đ
            },
            # Báo giá 2: Đã chấp nhận, ĐỦ ĐIỀU KIỆN chuyển thành Hợp đồng
            "BG-2026-002": {
                "quote_id": "BG-2026-002",
                "title": "Báo giá Cung cấp Module CPQ & Cổng thanh toán OCB",
                "customer_name": "Ngân hàng TMCP Phương Đông (OCB)",
                "customer_tax_code": "0300852233",
                "customer_address": "41-45 Lê Duẩn, Bến Nghé, Quận 1, TP. Hồ Chí Minh",
                "customer_contact": "Ông Đặng Quốc Toàn",
                "customer_position": "Phó Giám đốc Khối CNTT",
                "customer_phone": "0903.666.777",
                "customer_email": "toan.dq@ocb.com.vn",
                "opportunity_id": "OPP-2026-102",
                "opportunity_name": "Nâng cấp Module CPQ & Cổng thanh toán OCB Bank",
                "status": QUOTE_STATUS_ACCEPTED,  # ĐÃ CHẤP NHẬN
                "contract_id": None,
                "contract_number": None,
                "payment_terms": "Trả chậm trong vòng 30 ngày kể từ ngày xuất hóa đơn VAT (Net 30)",
                "created_by": "Lê Thị Bích Ngọc (NVKD)",
                "created_at": "2026-10-06 09:30:00",
                "accepted_at": "2026-10-16 11:20:00",
                "items": [
                    {
                        "item_id": 1,
                        "product_id": "PROD-CPQ-MOD",
                        "product_name": "Module CPQ Nâng Cao & Quản Lý Phiên Bản Báo Giá",
                        "unit": "Module",
                        "quantity": 4,
                        "unit_price": 8500000,
                        "discount_percent": 10.0,
                        "discount_amount": 3400000,
                        "line_total": 30600000
                    },
                    {
                        "item_id": 2,
                        "product_id": "PROD-INT-PAY",
                        "product_name": "Gói Tích Hợp Cổng Thanh Toán & Core Banking",
                        "unit": "Gói",
                        "quantity": 1,
                        "unit_price": 18000000,
                        "discount_percent": 5.0,
                        "discount_amount": 900000,
                        "line_total": 17100000
                    }
                ],
                "subtotal": 52000000,
                "discount_total": 4300000,
                "after_discount": 47700000,
                "vat_percent": 10.0,
                "vat_amount": 4770000,
                "grand_total": 52470000         # TỔNG GIÁ TRỊ ĐÃ CHỐT = 52.470.000 đ
            },
            # Báo giá 3: ĐÃ CHUYỂN THÀNH HỢP ĐỒNG (Contract HD-2026/001)
            "BG-2026-003": {
                "quote_id": "BG-2026-003",
                "title": "Báo giá Bản quyền CRM Cloud FPT Software",
                "customer_name": "Công ty TNHH Phần mềm FPT Miền Nam",
                "customer_tax_code": "0302588999",
                "customer_address": "Khu Công Nghệ Cao, TP. Thủ Đức, TP. Hồ Chí Minh",
                "customer_contact": "Ông Hoàng Minh Tuấn",
                "customer_position": "Trưởng phòng Mua hàng",
                "customer_phone": "0988.123.456",
                "customer_email": "tuan.hm@fpt.com",
                "opportunity_id": "OPP-2026-103",
                "opportunity_name": "Bản quyền AutoLead CRM Cloud - FPT Software Sài Gòn",
                "status": QUOTE_STATUS_CONVERTED, # ĐÃ LẬP HỢP ĐỒNG
                "contract_id": "CTR-2026-001",
                "contract_number": "HD-2026/001",  # Số HĐ đã có sẵn để test Tiêu chí 4 (Trùng số HĐ)
                "payment_terms": "Thanh toán 100% trong vòng 7 ngày làm việc sau khi ký",
                "created_by": "Trần Văn Nam (NVKD)",
                "created_at": "2026-09-22 14:00:00",
                "accepted_at": "2026-09-30 17:00:00",
                "items": [
                    {
                        "item_id": 1,
                        "product_id": "PROD-CRM-ENT",
                        "product_name": "AutoLead CRM Enterprise (Gói Doanh Nghiệp)",
                        "unit": "Gói/Năm",
                        "quantity": 5,
                        "unit_price": 24000000,
                        "discount_percent": 10.0,
                        "discount_amount": 12000000,
                        "line_total": 108000000
                    },
                    {
                        "item_id": 2,
                        "product_id": "PROD-SRV-TRAIN",
                        "product_name": "Gói Dịch Vụ Đào Tạo & Triển Khai Onsite Toàn Diện",
                        "unit": "Gói",
                        "quantity": 1,
                        "unit_price": 15000000,
                        "discount_percent": 10.0,
                        "discount_amount": 1500000,
                        "line_total": 13500000
                    }
                ],
                "subtotal": 135000000,
                "discount_total": 13500000,
                "after_discount": 121500000,
                "vat_percent": 10.0,
                "vat_amount": 3500000,  # Thuế ưu đãi phần mềm
                "grand_total": 125000000
            },
            # Báo giá 4: Đã gửi khách hàng, chưa được chấp nhận (SENT)
            "BG-2026-004": {
                "quote_id": "BG-2026-004",
                "title": "Báo giá Hệ thống Tự động Báo giá Viettel Post",
                "customer_name": "Tổng Công ty Cổ phần Bưu chính Viettel",
                "customer_tax_code": "0104084041",
                "customer_address": "Tòa nhà Viettel, Số 1 Giang Văn Minh, Ba Đình, Hà Nội",
                "customer_contact": "Ông Nguyễn Hải Đăng",
                "customer_position": "Giám đốc Trung tâm Giải pháp",
                "customer_phone": "0977.555.888",
                "customer_email": "dang.nh@viettelpost.com.vn",
                "opportunity_id": "OPP-2026-104",
                "opportunity_name": "Hệ thống Báo giá tự động Logistics Viettel Post",
                "status": QUOTE_STATUS_SENT,      # Chưa chấp nhận -> KHÔNG ĐƯỢC CHUYỂN HỢP ĐỒNG
                "contract_id": None,
                "contract_number": None,
                "payment_terms": "Đợt 1: 50% khi ký hợp đồng - Đợt 2: 50% khi bàn giao nghiệm thu",
                "created_by": "Vũ Đình Trọng (NVKD)",
                "created_at": "2026-10-10 11:30:00",
                "accepted_at": None,
                "items": [
                    {
                        "item_id": 1,
                        "product_id": "PROD-CRM-PRO",
                        "product_name": "AutoLead CRM Professional (Gói Tiêu Chuẩn)",
                        "unit": "Gói/Năm",
                        "quantity": 3,
                        "unit_price": 12000000,
                        "discount_percent": 0.0,
                        "discount_amount": 0,
                        "line_total": 36000000
                    }
                ],
                "subtotal": 36000000,
                "discount_total": 0,
                "after_discount": 36000000,
                "vat_percent": 10.0,
                "vat_amount": 3600000,
                "grand_total": 39600000
            }
        }

        # 3. Hợp đồng mẫu đã tồn tại (Contracts)
        self.contracts = {
            "CTR-2026-001": {
                "contract_id": "CTR-2026-001",
                "contract_number": "HD-2026/001",   # ĐÃ TỒN TẠI TRONG HỆ THỐNG
                "quote_id": "BG-2026-003",
                "quote_title": "Báo giá Bản quyền CRM Cloud FPT Software",
                "opportunity_id": "OPP-2026-103",
                "opportunity_name": "Bản quyền AutoLead CRM Cloud - FPT Software Sài Gòn",
                "customer_name": "Công ty TNHH Phần mềm FPT Miền Nam",
                "tax_code": "0302588999",
                "address": "Khu Công Nghệ Cao, TP. Thủ Đức, TP. Hồ Chí Minh",
                "contact_person": "Ông Hoàng Minh Tuấn",
                "phone": "0988.123.456",
                "email": "tuan.hm@fpt.com",
                "signed_date": "2026-10-05",
                "effective_date": "2026-10-05",
                "expiration_date": "2027-10-04",
                "payment_terms": "Thanh toán 100% trong vòng 7 ngày làm việc sau khi ký",
                "payment_terms_notes": "Đã nhận thanh toán qua chuyển khoản Vietcombank.",
                # Dòng sản phẩm kế thừa 100% từ báo giá
                "items": copy.deepcopy(self.quotations["BG-2026-003"]["items"]),
                "subtotal": 135000000,
                "discount_total": 13500000,
                "after_discount": 121500000,
                "vat_percent": 10.0,
                "vat_amount": 3500000,
                "grand_total": 125000000,
                "status": CONTRACT_STATUS_ACTIVE,
                "seller_info": copy.deepcopy(SELLER_INFO),
                "created_by": "Nguyễn Thị Phương Thảo (Kế toán trưởng)",
                "created_at": "2026-10-05 10:30:00"
            }
        }

        # Cập nhật index số hợp đồng
        self.contract_number_index = {
            self._normalize_contract_number("HD-2026/001"): "CTR-2026-001"
        }

        # 4. Nhật ký kiểm toán mẫu
        self.audit_logs = [
            {
                "log_id": 1,
                "action": "CONVERT_CONTRACT",
                "message": "Chuyển thành công Báo giá [BG-2026-003] thành Hợp đồng số [HD-2026/001]. Cơ hội [OPP-2026-103] tự động chuyển Đóng Thắng với giá trị 125.000.000 đ.",
                "performed_by": "Nguyễn Thị Phương Thảo (Kế toán)",
                "timestamp": "2026-10-05 10:30:15",
                "details": {
                    "contract_id": "CTR-2026-001",
                    "contract_number": "HD-2026/001",
                    "grand_total": 125000000,
                    "opp_id": "OPP-2026-103"
                }
            }
        ]

    # =========================================================================
    # CÁC HÀM TRUY VẤN DỮ LIỆU (GETTERS)
    # =========================================================================

    def get_all_quotes(self, filter_status=None):
        """Lấy danh sách tất cả báo giá"""
        with self.lock:
            quotes = list(self.quotations.values())
            if filter_status:
                quotes = [q for q in quotes if q.get("status") == filter_status]
            # Sắp xếp báo giá mới nhất lên đầu
            return sorted(quotes, key=lambda x: x.get("created_at", ""), reverse=True)

    def get_ready_quotes(self):
        """Lấy danh sách các báo giá ĐÃ CHẤP NHẬN sẵn sàng chuyển thành hợp đồng"""
        with self.lock:
            quotes = [q for q in self.quotations.values() if q.get("status") == QUOTE_STATUS_ACCEPTED]
            return sorted(quotes, key=lambda x: x.get("accepted_at", ""), reverse=True)

    def get_quote(self, quote_id):
        """Lấy thông tin chi tiết một báo giá theo mã"""
        with self.lock:
            return copy.deepcopy(self.quotations.get(quote_id))

    def get_all_contracts(self, search=None):
        """Lấy danh sách tất cả hợp đồng"""
        with self.lock:
            contracts = list(self.contracts.values())
            if search:
                s = search.lower().strip()
                contracts = [
                    c for c in contracts
                    if s in c.get("contract_number", "").lower()
                    or s in c.get("customer_name", "").lower()
                    or s in c.get("quote_id", "").lower()
                ]
            return sorted(contracts, key=lambda x: x.get("created_at", ""), reverse=True)

    def get_contract(self, contract_id):
        """Lấy thông tin chi tiết hợp đồng theo ID nội bộ"""
        with self.lock:
            return copy.deepcopy(self.contracts.get(contract_id))

    def get_contract_by_number(self, contract_number):
        """Lấy hợp đồng theo số hợp đồng đã khai báo"""
        with self.lock:
            norm = self._normalize_contract_number(contract_number)
            contract_id = self.contract_number_index.get(norm)
            if contract_id:
                return copy.deepcopy(self.contracts.get(contract_id))
            return None

    def get_all_opportunities(self):
        """Lấy danh sách cơ hội kinh doanh CRM"""
        with self.lock:
            opps = list(self.opportunities.values())
            return sorted(opps, key=lambda x: x.get("created_at", ""), reverse=True)

    def get_opportunity(self, opp_id):
        """Lấy thông tin cơ hội theo mã"""
        with self.lock:
            return copy.deepcopy(self.opportunities.get(opp_id))

    def get_audit_logs(self, limit=20):
        """Lấy lịch sử sự kiện kiểm toán"""
        with self.lock:
            return sorted(self.audit_logs, key=lambda x: x.get("timestamp", ""), reverse=True)[:limit]

    # =========================================================================
    # TIÊU CHÍ 4: KIỂM TRA SỐ HỢP ĐỒNG DUY NHẤT (UNIQUE CHECK)
    # =========================================================================

    def check_contract_number_availability(self, contract_number, exclude_contract_id=None):
        """
        Kiểm tra số hợp đồng có khả dụng (chưa từng được sử dụng) hay không.
        Phục vụ kiểm tra trực tiếp qua API và validate form real-time.
        """
        if not contract_number or not str(contract_number).strip():
            return {
                "available": False,
                "message": "Số hợp đồng không được để trống."
            }

        norm = self._normalize_contract_number(contract_number)
        with self.lock:
            existing_id = self.contract_number_index.get(norm)
            if existing_id and existing_id != exclude_contract_id:
                existing_contract = self.contracts.get(existing_id, {})
                return {
                    "available": False,
                    "message": f"Số hợp đồng '{contract_number}' đã tồn tại (Hợp đồng cho: {existing_contract.get('customer_name', 'Chưa rõ')}). Vui lòng chọn số hợp đồng duy nhất.",
                    "existing_contract_id": existing_id
                }
            return {
                "available": True,
                "message": f"Số hợp đồng '{contract_number}' hợp lệ và sẵn sàng sử dụng."
            }

    # =========================================================================
    # NGHIỆP VỤ CHÍNH: CHUYỂN BÁO GIÁ THÀNH HỢP ĐỒNG (TIÊU CHÍ 1, 2, 3, 4)
    # =========================================================================

    def convert_quote_to_contract(self, quote_id, contract_data, performer_name="Kế toán viên"):
        """
        Chuyển một báo giá được chấp nhận thành Hợp đồng.
        
        Quy trình xử lý tuần tự và đảm bảo tính nguyên tử (Atomicity):
        - Kiểm tra điều kiện tiên quyết: Báo giá phải ở trạng thái ACCEPTED và chưa từng chuyển thành HĐ.
        - Tiêu chí 4: Kiểm tra số hợp đồng là DUY NHẤT (Không trùng lặp).
        - Tiêu chí 2: Kiểm tra tính hợp lệ của metadata (số HĐ, ngày ký, ngày hiệu lực, ngày hết hạn, điều khoản thanh toán).
        - Tiêu chí 1: Kế thừa 100% dòng sản phẩm và toàn bộ giá tiền đã chốt, tuyệt đối không nhập lại.
        - Tiêu chí 3: Tự động chuyển Cơ hội tương ứng sang Đóng Thắng (CLOSED_WON) với giá trị đúng bằng giá trị hợp đồng.
        """
        with self.lock:
            # 1. Kiểm tra tồn tại báo giá
            quote = self.quotations.get(quote_id)
            if not quote:
                raise ValueError(f"Không tìm thấy báo giá có mã [{quote_id}].")

            # 2. Kiểm tra trạng thái báo giá (Chỉ ACCEPTED mới được chuyển)
            if quote.get("status") != QUOTE_STATUS_ACCEPTED:
                status_label = quote.get("status", "Chưa rõ")
                if quote.get("status") == QUOTE_STATUS_CONVERTED:
                    raise InvalidQuoteStatusError(
                        f"Báo giá [{quote_id}] đã được chuyển thành hợp đồng trước đó (Số HĐ: {quote.get('contract_number')}). Không thể chuyển lại."
                    )
                raise InvalidQuoteStatusError(
                    f"Báo giá [{quote_id}] đang ở trạng thái '{status_label}'. Chỉ những báo giá đã được khách hàng CHẤP NHẬN mới được chuyển thành hợp đồng."
                )

            # 3. Kiểm tra TIÊU CHÍ 4: Số hợp đồng là duy nhất
            raw_number = contract_data.get("contract_number", "")
            contract_number = str(raw_number).strip()
            if not contract_number:
                raise ContractValidationError("Số hợp đồng là trường bắt buộc, không được để trống.")

            norm_number = self._normalize_contract_number(contract_number)
            if norm_number in self.contract_number_index:
                existing_cid = self.contract_number_index[norm_number]
                existing_c = self.contracts.get(existing_cid, {})
                raise DuplicateContractNumberError(
                    f"Số hợp đồng '{contract_number}' đã tồn tại trong hệ thống (gắn với khách hàng '{existing_c.get('customer_name')}'). Vui lòng nhập số hợp đồng duy nhất!"
                )

            # 4. Kiểm tra TIÊU CHÍ 2: Khai báo ngày ký, ngày hiệu lực, ngày hết hạn, điều khoản thanh toán
            signed_date = str(contract_data.get("signed_date", "")).strip()
            effective_date = str(contract_data.get("effective_date", "")).strip()
            expiration_date = str(contract_data.get("expiration_date", "")).strip()
            payment_terms = str(contract_data.get("payment_terms", "")).strip()
            payment_terms_notes = str(contract_data.get("payment_terms_notes", "")).strip()

            if not signed_date:
                raise ContractValidationError("Ngày ký hợp đồng là trường bắt buộc.")
            if not effective_date:
                raise ContractValidationError("Ngày hiệu lực hợp đồng là trường bắt buộc.")
            if not expiration_date:
                raise ContractValidationError("Ngày hết hạn hợp đồng là trường bắt buộc.")
            if not payment_terms:
                raise ContractValidationError("Điều khoản thanh toán là trường bắt buộc.")

            # Kiểm tra định dạng và logic ngày tháng
            try:
                d_signed = datetime.strptime(signed_date, "%Y-%m-%d").date()
                d_eff = datetime.strptime(effective_date, "%Y-%m-%d").date()
                d_exp = datetime.strptime(expiration_date, "%Y-%m-%d").date()
            except ValueError:
                raise ContractValidationError("Định dạng ngày tháng không hợp lệ (Bắt buộc định dạng YYYY-MM-DD).")

            if d_eff > d_exp:
                raise ContractValidationError(
                    f"Ngày hiệu lực ({format_date(d_eff)}) không được sau ngày hết hạn ({format_date(d_exp)})."
                )

            # 5. TIÊU CHÍ 1: KẾ THỪA TOÀN BỘ DÒNG SẢN PHẨM VÀ GIÁ ĐÃ CHỐT, KHÔNG NHẬP LẠI
            # Tạo deep copy để đảm bảo bảo toàn dữ liệu gốc
            inherited_items = copy.deepcopy(quote.get("items", []))
            inherited_subtotal = float(quote.get("subtotal", 0))
            inherited_discount_total = float(quote.get("discount_total", 0))
            inherited_after_discount = float(quote.get("after_discount", 0))
            inherited_vat_percent = float(quote.get("vat_percent", DEFAULT_VAT_PERCENT))
            inherited_vat_amount = float(quote.get("vat_amount", 0))
            inherited_grand_total = float(quote.get("grand_total", 0))

            if not inherited_items:
                raise ContractValidationError("Báo giá không có dòng sản phẩm nào để kế thừa sang hợp đồng.")

            # 6. Khởi tạo đối tượng Hợp đồng mới
            self._contract_id_counter += 1
            new_contract_id = f"CTR-2026-{self._contract_id_counter:03d}"
            now_str = get_current_time().strftime("%Y-%m-%d %H:%M:%S")

            new_contract = {
                "contract_id": new_contract_id,
                "contract_number": contract_number,              # TIÊU CHÍ 4 & 2
                "quote_id": quote_id,
                "quote_title": quote.get("title"),
                "opportunity_id": quote.get("opportunity_id"),
                "opportunity_name": quote.get("opportunity_name"),
                # Kế thừa thông tin khách hàng từ báo giá
                "customer_name": quote.get("customer_name"),
                "tax_code": quote.get("customer_tax_code", ""),
                "address": quote.get("customer_address", ""),
                "contact_person": quote.get("customer_contact", ""),
                "position": quote.get("customer_position", ""),
                "phone": quote.get("customer_phone", ""),
                "email": quote.get("customer_email", ""),
                # TIÊU CHÍ 2: Khai báo pháp lý
                "signed_date": signed_date,
                "effective_date": effective_date,
                "expiration_date": expiration_date,
                "payment_terms": payment_terms,
                "payment_terms_notes": payment_terms_notes,
                # TIÊU CHÍ 1: Dòng sản phẩm và giá kế thừa 100%
                "items": inherited_items,
                "subtotal": inherited_subtotal,
                "discount_total": inherited_discount_total,
                "after_discount": inherited_after_discount,
                "vat_percent": inherited_vat_percent,
                "vat_amount": inherited_vat_amount,
                "grand_total": inherited_grand_total,
                # Thông tin bổ sung
                "status": CONTRACT_STATUS_ACTIVE,
                "seller_info": copy.deepcopy(SELLER_INFO),
                "created_by": performer_name,
                "created_at": now_str
            }

            # 7. TIÊU CHÍ 3: CƠ HỘI TƯƠNG ỨNG TỰ ĐỘNG CHUYỂN SANG ĐÓNG THẮNG VỚI GIÁ TRỊ ĐÚNG BẰNG GIÁ TRỊ HỢP ĐỒNG
            opp_id = quote.get("opportunity_id")
            opp = self.opportunities.get(opp_id)
            old_opp_stage = None
            old_opp_value = None

            if opp:
                old_opp_stage = opp.get("stage")
                old_opp_value = opp.get("value")

                # Cập nhật chuyển trạng thái sang ĐÓNG THẮNG
                opp["stage"] = OPP_STAGE_CLOSED_WON
                # Đồng bộ giá trị cơ hội ĐÚNG BẰNG giá trị hợp đồng đã chốt
                opp["value"] = inherited_grand_total
                opp["contract_id"] = new_contract_id
                opp["win_date"] = signed_date
                opp["updated_at"] = now_str

                # Kiểm tra bất biến xác nhận (Invariant Verification)
                assert opp["stage"] == OPP_STAGE_CLOSED_WON, "Lỗi bất biến: Cơ hội chưa chuyển sang CLOSED_WON"
                assert opp["value"] == inherited_grand_total, "Lỗi bất biến: Giá trị cơ hội không khớp giá trị hợp đồng"

            # 8. Cập nhật trạng thái Báo giá sang ĐÃ LẬP HỢP ĐỒNG (CONVERTED)
            quote["status"] = QUOTE_STATUS_CONVERTED
            quote["contract_id"] = new_contract_id
            quote["contract_number"] = contract_number
            quote["converted_at"] = now_str

            # 9. Lưu trữ Hợp đồng và ghi nhận index Số Hợp Đồng
            self.contracts[new_contract_id] = new_contract
            self.contract_number_index[norm_number] = new_contract_id

            # 10. Ghi nhận Nhật ký kiểm toán (Audit Trail)
            audit_entry = {
                "log_id": len(self.audit_logs) + 1,
                "action": "CONVERT_QUOTE_TO_CONTRACT",
                "message": (
                    f"Kế toán đã chuyển thành công Báo giá [{quote_id}] thành Hợp đồng số [{contract_number}]. "
                    f"Kế thừa toàn bộ {len(inherited_items)} dòng sản phẩm với giá chốt {format_currency(inherited_grand_total)}. "
                    f"Cơ hội [{opp_id or 'N/A'}] tự động chuyển sang ĐÓNG THẮNG với giá trị {format_currency(inherited_grand_total)}."
                ),
                "performed_by": performer_name,
                "timestamp": now_str,
                "details": {
                    "contract_id": new_contract_id,
                    "contract_number": contract_number,
                    "quote_id": quote_id,
                    "opp_id": opp_id,
                    "grand_total": inherited_grand_total,
                    "old_opp_stage": old_opp_stage,
                    "new_opp_stage": OPP_STAGE_CLOSED_WON,
                    "old_opp_value": old_opp_value,
                    "new_opp_value": inherited_grand_total,
                    "effective_date": effective_date,
                    "expiration_date": expiration_date,
                    "payment_terms": payment_terms
                }
            }
            self.audit_logs.append(audit_entry)

            return copy.deepcopy(new_contract)

    # =========================================================================
    # HÀM THỐNG KÊ DASHBOARD (KPIs CHO KẾ TOÁN)
    # =========================================================================

    def get_dashboard_stats(self):
        """Tính toán các chỉ số thống kê phục vụ bàn làm việc của Kế toán"""
        with self.lock:
            total_contracts = len(self.contracts)
            active_contracts = sum(1 for c in self.contracts.values() if c.get("status") == CONTRACT_STATUS_ACTIVE)
            total_contract_value = sum(c.get("grand_total", 0) for c in self.contracts.values())

            # Báo giá đã chấp thuận đang chờ kế toán chuyển thành hợp đồng
            ready_quotes = [q for q in self.quotations.values() if q.get("status") == QUOTE_STATUS_ACCEPTED]
            ready_quotes_count = len(ready_quotes)
            ready_quotes_value = sum(q.get("grand_total", 0) for q in ready_quotes)

            # Cơ hội đóng thắng
            won_opps = [o for o in self.opportunities.values() if o.get("stage") == OPP_STAGE_CLOSED_WON]
            won_opps_count = len(won_opps)
            won_opps_value = sum(o.get("value", 0) for o in won_opps)

            # Tổng số cơ hội
            total_opps = len(self.opportunities)
            conversion_rate = (won_opps_count / total_opps * 100) if total_opps > 0 else 0.0

            return {
                "total_contracts": total_contracts,
                "active_contracts": active_contracts,
                "total_contract_value": total_contract_value,
                "ready_quotes_count": ready_quotes_count,
                "ready_quotes_value": ready_quotes_value,
                "won_opps_count": won_opps_count,
                "won_opps_value": won_opps_value,
                "total_opps": total_opps,
                "conversion_rate": round(conversion_rate, 1)
            }

    def reset_to_seed(self):
        """Khôi phục lại dữ liệu mẫu ban đầu phục vụ kiểm thử lặp lại"""
        with self.lock:
            self.quotations.clear()
            self.opportunities.clear()
            self.contracts.clear()
            self.contract_number_index.clear()
            self.audit_logs.clear()
            self._contract_id_counter = 100
            self._seed_sample_data()


# Khởi tạo singleton Database
db = Database()

    def append_payment_schedule_milestone(self, contract_id: str, milestone: dict):
        """Thêm một mốc thanh toán trong phụ lục tiến độ hợp đồng"""
        pass

    def validate_unique_contract_code(self, code: str) -> bool:
        """Kiểm tra tính duy nhất của mã số hợp đồng trong CSDL"""
        return self.get_contract_by_number(code) is None
