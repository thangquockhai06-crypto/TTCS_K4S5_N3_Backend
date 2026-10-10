"""
Quản lý cơ sở dữ liệu Thread-Safe & Nghiệp vụ Chuyển Đổi Lead CRM (SCRUM-30 / SCRUM-54)

Đáp ứng 4 Tiêu chí chấp nhận (Acceptance Criteria):
1. Một thao tác sinh đồng thời khách hàng doanh nghiệp, người liên hệ và cơ hội bán hàng.
2. Dữ liệu lead được chuyển sang, không phải nhập lại.
3. Lead chuyển sang trạng thái Đã chuyển đổi (CONVERTED) và không sửa được nữa (LOCKED).
4. Toàn bộ hoạt động đã ghi trên lead được giữ lại trọn vẹn trên khách hàng mới.
"""

import threading
import copy
from datetime import datetime, timedelta

from config import (
    STATUS_NEW,
    STATUS_CONTACTED,
    STATUS_QUALIFIED,
    STATUS_CONVERTED,
    STATUS_DISQUALIFIED,
    STATUS_LABELS,
    STAGE_DISCOVERY,
    STAGE_PROPOSAL,
    STAGE_NEGOTIATION,
    STAGE_WON,
    STAGE_LOST,
    ACTIVITY_CALL,
    ACTIVITY_MEETING,
    ACTIVITY_EMAIL,
    ACTIVITY_NOTE,
    ACTIVITY_CONVERT,
    ACTIVITY_ICONS,
    ACTIVITY_LABELS,
    ROLE_SALES_REP,
    ROLE_TEAM_LEAD,
    ROLE_DIRECTOR
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
        self.leads = {}
        self.accounts = {}
        self.contacts = {}
        self.opportunities = {}
        self.notifications = []
        self.audit_logs = []

        # Các bộ đếm ID tăng dần
        self._lead_counter = 100
        self._account_counter = 200
        self._contact_counter = 300
        self._opp_counter = 400
        self._act_counter = 1000
        self._notif_counter = 1
        self._log_counter = 1

        self.reset_demo_data()

    def reset_demo_data(self):
        """Khởi tạo dữ liệu mẫu phong phú mô phỏng B2B CRM thực tế"""
        with self.lock:
            self.users = {
                "usr-01": {
                    "id": "usr-01",
                    "name": "Nguyễn Văn Tuấn",
                    "email": "tuan.nguyen@autolead.vn",
                    "role": ROLE_SALES_REP,
                    "role_name": "Nhân viên kinh doanh",
                    "phone": "0912 345 678",
                    "avatar": "👨‍💼"
                },
                "usr-02": {
                    "id": "usr-02",
                    "name": "Trần Thị Mai",
                    "email": "mai.tran@autolead.vn",
                    "role": ROLE_SALES_REP,
                    "role_name": "Nhân viên kinh doanh",
                    "phone": "0987 654 321",
                    "avatar": "👩‍💼"
                },
                "usr-03": {
                    "id": "usr-03",
                    "name": "Lê Hoàng Nam",
                    "email": "nam.le@autolead.vn",
                    "role": ROLE_TEAM_LEAD,
                    "role_name": "Trưởng nhóm kinh doanh",
                    "phone": "0903 112 233",
                    "avatar": "🧑‍💼"
                },
                "usr-04": {
                    "id": "usr-04",
                    "name": "Phạm Đức Thắng",
                    "email": "thang.pham@autolead.vn",
                    "role": ROLE_DIRECTOR,
                    "role_name": "Giám đốc kinh doanh",
                    "phone": "0933 888 999",
                    "avatar": "👔"
                }
            }

            self.leads = {}
            self.accounts = {}
            self.contacts = {}
            self.opportunities = {}
            self.notifications = []
            self.audit_logs = []

            now = datetime.now()

            # LEAD 1: Sẵn sàng chuyển đổi (QUALIFIED) - Có 3 hoạt động trước đó
            lead_1 = {
                "id": "LEAD-101",
                "company_name": "Công ty Cổ phần Công nghệ VinTech",
                "tax_id": "0108923456",
                "industry": "Công nghệ thông tin & Viễn thông",
                "address": "Tầng 12, Tòa nhà Landmark 72, Đường Phạm Hùng",
                "city": "Hà Nội",
                "website": "https://vintech-corp.example.com",
                "company_size": "100 - 250 nhân sự",
                
                # Thông tin Người liên hệ
                "contact_name": "Nguyễn Hoàng Long",
                "job_title": "Giám đốc Công nghệ (CTO)",
                "phone": "0918 888 999",
                "email": "long.nh@vintech-corp.example.com",

                # Thông tin Nhu cầu & Cơ hội
                "interested_product": "Gói CRM Doanh Nghiệp Tích Hợp AI Cloud",
                "estimated_value": 150000000,  # 150 triệu VND
                "expected_close_date": (now + timedelta(days=25)).strftime("%Y-%m-%d"),
                "requirements": "Doanh nghiệp cần chuyển đổi số toàn diện quy trình tiếp nhận và quản lý khách hàng B2B, tích hợp tổng đài VoIP và hóa đơn điện tử.",
                "source": "Sự kiện Tech Expo 2026",
                
                # Trạng thái & Phân công
                "status": STATUS_QUALIFIED,
                "is_locked": False,
                "assigned_to_id": "usr-01",
                "created_at": now - timedelta(days=5),
                "qualification_notes": "Khách hàng có ngân sách rõ ràng (150-200tr), người liên hệ là CTO có quyền quyết định kỹ thuật, kế hoạch chốt hợp đồng trong tháng này.",
                
                # Thông tin chuyển đổi (ban đầu None)
                "converted_at": None,
                "converted_by_id": None,
                "converted_account_id": None,
                "converted_contact_id": None,
                "converted_opportunity_id": None,

                # Lịch sử hoạt động trước đó trên lead
                "activities": [
                    {
                        "id": "ACT-1001",
                        "type": ACTIVITY_CALL,
                        "type_label": ACTIVITY_LABELS[ACTIVITY_CALL],
                        "icon": ACTIVITY_ICONS[ACTIVITY_CALL],
                        "summary": "Cuộc gọi khảo sát nhu cầu ban đầu (18 phút)",
                        "details": "Đã trao đổi với anh Long (CTO). Doanh nghiệp hiện có 35 nhân viên Sales đang dùng Excel rời rạc, thường xuyên bị sót khách hàng. Rất hào hứng với giải pháp phân bổ tự động và ràng buộc SLA.",
                        "performed_by_id": "usr-01",
                        "performed_by_name": "Nguyễn Văn Tuấn",
                        "created_at": now - timedelta(days=4, hours=3)
                    },
                    {
                        "id": "ACT-1002",
                        "type": ACTIVITY_MEETING,
                        "type_label": ACTIVITY_LABELS[ACTIVITY_MEETING],
                        "icon": ACTIVITY_ICONS[ACTIVITY_MEETING],
                        "summary": "Họp Demo trực tuyến qua Google Meet",
                        "details": "Trình diễn tính năng chuyển đổi 1-click sinh đồng thời Khách hàng, Người liên hệ và Cơ hội cho ban lãnh đạo VinTech. Khách hàng đánh giá rất cao việc giữ trọn lịch sử hoạt động và khóa lead để tránh sửa bậy.",
                        "performed_by_id": "usr-01",
                        "performed_by_name": "Nguyễn Văn Tuấn",
                        "created_at": now - timedelta(days=2, hours=5)
                    },
                    {
                        "id": "ACT-1003",
                        "type": ACTIVITY_EMAIL,
                        "type_label": ACTIVITY_LABELS[ACTIVITY_EMAIL],
                        "icon": ACTIVITY_ICONS[ACTIVITY_EMAIL],
                        "summary": "Gửi báo giá sơ bộ & Hồ sơ năng lực giải pháp",
                        "details": "Đã gửi email đính kèm bảng chào giá 150.000.000 đ cho gói 50 người dùng trong 1 năm kèm điều khoản bảo trì 24/7. Anh Long phản hồi xác nhận hợp lệ và hẹn chốt hợp đồng.",
                        "performed_by_id": "usr-01",
                        "performed_by_name": "Nguyễn Văn Tuấn",
                        "created_at": now - timedelta(days=1, hours=2)
                    }
                ]
            }
            self.leads[lead_1["id"]] = lead_1

            # LEAD 2: Đủ điều kiện chuyển đổi (QUALIFIED) - Phụ trách bởi Trần Thị Mai
            lead_2 = {
                "id": "LEAD-102",
                "company_name": "Tập đoàn Bán lẻ Tiêu dùng An Nam",
                "tax_id": "0314567890",
                "industry": "Bán lẻ & Chuỗi cửa hàng",
                "address": "Số 45 Lê Duẩn, Phường Bến Nghé, Quận 1",
                "city": "TP. Hồ Chí Minh",
                "website": "https://annamretail.example.vn",
                "company_size": "500+ nhân sự",
                
                "contact_name": "Vũ Thị Thanh Thảo",
                "job_title": "Trưởng phòng Mua sắm & Đấu thầu",
                "phone": "0908 123 456",
                "email": "thao.vu@annamretail.example.vn",

                "interested_product": "Hệ Thống Quản Lý Kênh Bán Hàng & Khách Hàng Đại Lý",
                "estimated_value": 280000000,  # 280 triệu VND
                "expected_close_date": (now + timedelta(days=40)).strftime("%Y-%m-%d"),
                "requirements": "Triển khai phần mềm quản lý cho 12 chi nhánh trên toàn quốc, đồng bộ dữ liệu tồn kho và đơn hàng.",
                "source": "Khách hàng cũ giới thiệu",
                
                "status": STATUS_QUALIFIED,
                "is_locked": False,
                "assigned_to_id": "usr-02",
                "created_at": now - timedelta(days=7),
                "qualification_notes": "Đã hoàn thành vòng phỏng vấn nhu cầu và thẩm định năng lực nhà cung cấp. Khách hàng đạt tiêu chuẩn chuyển đổi cơ hội cấp A.",
                
                "converted_at": None,
                "converted_by_id": None,
                "converted_account_id": None,
                "converted_contact_id": None,
                "converted_opportunity_id": None,

                "activities": [
                    {
                        "id": "ACT-1004",
                        "type": ACTIVITY_CALL,
                        "type_label": ACTIVITY_LABELS[ACTIVITY_CALL],
                        "icon": ACTIVITY_ICONS[ACTIVITY_CALL],
                        "summary": "Liên hệ xác nhận nhu cầu đầu thầu phần mềm",
                        "details": "Chị Thảo gửi tài liệu yêu cầu tính năng kỹ thuật. Đã giải thích chi tiết khả năng mở rộng kiến trúc hệ thống.",
                        "performed_by_id": "usr-02",
                        "performed_by_name": "Trần Thị Mai",
                        "created_at": now - timedelta(days=6)
                    },
                    {
                        "id": "ACT-1005",
                        "type": ACTIVITY_NOTE,
                        "type_label": ACTIVITY_LABELS[ACTIVITY_NOTE],
                        "icon": ACTIVITY_ICONS[ACTIVITY_NOTE],
                        "summary": "Ghi chú chiến lược tiếp cận",
                        "details": "An Nam ưu tiên nhà cung cấp có cam kết hỗ trợ onsite 3 tháng đầu triển khai.",
                        "performed_by_id": "usr-02",
                        "performed_by_name": "Trần Thị Mai",
                        "created_at": now - timedelta(days=3)
                    }
                ]
            }
            self.leads[lead_2["id"]] = lead_2

            # LEAD 3: Đang chăm sóc (CONTACTED)
            lead_3 = {
                "id": "LEAD-103",
                "company_name": "Công ty Cổ phần Dược phẩm Hoàng Hà",
                "tax_id": "0109887766",
                "industry": "Dược phẩm & Y tế",
                "address": "Khu Công nghiệp Quế Võ, Huyện Quế Võ",
                "city": "Bắc Ninh",
                "website": "https://hoanghapharma.example.vn",
                "company_size": "50 - 100 nhân sự",
                
                "contact_name": "Trần Đình Trọng",
                "job_title": "Giám đốc Điều hành (CEO)",
                "phone": "0934 567 890",
                "email": "trong.td@hoanghapharma.example.vn",

                "interested_product": "Phần mềm Quản lý Trình dược viên & Đại lý Thuốc",
                "estimated_value": 90000000,
                "expected_close_date": (now + timedelta(days=60)).strftime("%Y-%m-%d"),
                "requirements": "Theo dõi lộ trình thị trường của nhân viên và đơn đặt hàng tại nhà thuốc.",
                "source": "Website Form",
                
                "status": STATUS_CONTACTED,
                "is_locked": False,
                "assigned_to_id": "usr-01",
                "created_at": now - timedelta(days=3),
                "qualification_notes": "Đang trong quá trình trao đổi sâu hơn về yêu cầu tính năng.",
                
                "converted_at": None,
                "converted_by_id": None,
                "converted_account_id": None,
                "converted_contact_id": None,
                "converted_opportunity_id": None,

                "activities": [
                    {
                        "id": "ACT-1006",
                        "type": ACTIVITY_CALL,
                        "type_label": ACTIVITY_LABELS[ACTIVITY_CALL],
                        "icon": ACTIVITY_ICONS[ACTIVITY_CALL],
                        "summary": "Gọi điện tư vấn ban đầu",
                        "details": "Đã trao đổi ngắn 10 phút. Bác sĩ Trọng bận công tác, hẹn tuần sau trao đổi cụ thể.",
                        "performed_by_id": "usr-01",
                        "performed_by_name": "Nguyễn Văn Tuấn",
                        "created_at": now - timedelta(days=2)
                    }
                ]
            }
            self.leads[lead_3["id"]] = lead_3

            # LEAD 4: Mới tiếp nhận (NEW)
            lead_4 = {
                "id": "LEAD-104",
                "company_name": "Chuỗi Khách sạn & Nghỉ dưỡng Indochina Heritage",
                "tax_id": "0401239874",
                "industry": "Khách sạn & Du lịch",
                "address": "Bãi biển Mỹ Khê, Quận Ngũ Hành Sơn",
                "city": "Đà Nẵng",
                "website": "https://indochinaheritage.example.com",
                "company_size": "250 - 500 nhân sự",
                
                "contact_name": "Đặng Mai Phương",
                "job_title": "Trưởng phòng Kinh doanh & Tiếp thị",
                "phone": "0977 112 233",
                "email": "phuong.dm@indochinaheritage.example.com",

                "interested_product": "Giải pháp Loyalty & Quản lý Khách Hàng VIP",
                "estimated_value": 120000000,
                "expected_close_date": (now + timedelta(days=45)).strftime("%Y-%m-%d"),
                "requirements": "Tích hợp tích điểm thẻ thành viên và gửi SMS/Zalo chăm sóc tự động.",
                "source": "Chiến dịch Facebook Ads",
                
                "status": STATUS_NEW,
                "is_locked": False,
                "assigned_to_id": "usr-02",
                "created_at": now - timedelta(days=1),
                "qualification_notes": "",
                
                "converted_at": None,
                "converted_by_id": None,
                "converted_account_id": None,
                "converted_contact_id": None,
                "converted_opportunity_id": None,

                "activities": []
            }
            self.leads[lead_4["id"]] = lead_4

            # LEAD 5: ĐÃ CHUYỂN ĐỔI (CONVERTED - ĐÃ KHÓA 🔒)
            # Khởi tạo sẵn để người dùng và bài test có thể kiểm tra ngay tính năng khóa bảo vệ (AC3)
            # và kiểm tra dữ liệu khách hàng doanh nghiệp đã kế thừa (AC4)
            lead_5 = {
                "id": "LEAD-105",
                "company_name": "Công ty Cổ phần Vận tải & Logistics Sao Biển",
                "tax_id": "0200889911",
                "industry": "Giao nhận & Vận tải biển",
                "address": "Tầng 5, Cảng Cát Lái, Phường Cát Lái, Thành phố Thủ Đức",
                "city": "TP. Hồ Chí Minh",
                "website": "https://seastar-logistics.example.vn",
                "company_size": "100 - 250 nhân sự",
                
                "contact_name": "Bùi Quốc Huy",
                "job_title": "Phó Tổng Giám Đốc Vận Hành",
                "phone": "0909 333 444",
                "email": "huy.bq@seastar-logistics.example.vn",

                "interested_product": "Phần mềm Quản lý Báo giá Vận chuyển & CRM Khách hàng xuất nhập khẩu",
                "estimated_value": 180000000,
                "expected_close_date": (now + timedelta(days=15)).strftime("%Y-%m-%d"),
                "requirements": "Tự động gửi thông báo hành trình container cho chủ hàng.",
                "source": "Đối tác chiến lược",
                
                "status": STATUS_CONVERTED,
                "is_locked": True,  # ĐÃ KHÓA BẤT BIẾN!
                "assigned_to_id": "usr-01",
                "created_at": now - timedelta(days=12),
                "qualification_notes": "Khách hàng rất tiềm năng, đã hoàn thành thẩm định và quyết định triển khai ngay.",
                
                "converted_at": now - timedelta(days=2),
                "converted_by_id": "usr-01",
                "converted_account_id": "ACC-201",
                "converted_contact_id": "CON-301",
                "converted_opportunity_id": "OPP-401",

                "activities": [
                    {
                        "id": "ACT-1000",
                        "type": ACTIVITY_CONVERT,
                        "type_label": ACTIVITY_LABELS[ACTIVITY_CONVERT],
                        "icon": ACTIVITY_ICONS[ACTIVITY_CONVERT],
                        "summary": "Chuyển đổi thành công sang Khách hàng & Cơ hội 🚀",
                        "details": "Đã sinh đồng thời Khách hàng doanh nghiệp [ACC-201], Người liên hệ [CON-301] và Cơ hội bán hàng [OPP-401]. Dữ liệu lead đã được khóa vĩnh viễn.",
                        "performed_by_id": "usr-01",
                        "performed_by_name": "Nguyễn Văn Tuấn",
                        "created_at": now - timedelta(days=2),
                        "is_milestone": True
                    },
                    {
                        "id": "ACT-1007",
                        "type": ACTIVITY_CALL,
                        "type_label": ACTIVITY_LABELS[ACTIVITY_CALL],
                        "icon": ACTIVITY_ICONS[ACTIVITY_CALL],
                        "summary": "Cuộc gọi thẩm định kỹ thuật (25 phút)",
                        "details": "Thống nhất các module cốt lõi: Quản lý khách hàng FCL/LCL, theo dõi công nợ theo chuyến tàu.",
                        "performed_by_id": "usr-01",
                        "performed_by_name": "Nguyễn Văn Tuấn",
                        "created_at": now - timedelta(days=10)
                    },
                    {
                        "id": "ACT-1008",
                        "type": ACTIVITY_MEETING,
                        "type_label": ACTIVITY_LABELS[ACTIVITY_MEETING],
                        "icon": ACTIVITY_ICONS[ACTIVITY_MEETING],
                        "summary": "Gặp mặt đàm phán hợp đồng tại văn phòng Cát Lái",
                        "details": "Anh Huy đồng ý mức giá 180 triệu, thanh toán chia 3 đợt. Yêu cầu chuyển lead sang tài khoản khách hàng chính thức để gửi hợp đồng.",
                        "performed_by_id": "usr-01",
                        "performed_by_name": "Nguyễn Văn Tuấn",
                        "created_at": now - timedelta(days=5)
                    }
                ]
            }
            self.leads[lead_5["id"]] = lead_5

            # Tương ứng tạo sẵn Khách hàng ACC-201, Người liên hệ CON-301, Cơ hội OPP-401 cho LEAD-105
            acc_1 = {
                "id": "ACC-201",
                "name": "Công ty Cổ phần Vận tải & Logistics Sao Biển",
                "tax_id": "0200889911",
                "industry": "Giao nhận & Vận tải biển",
                "address": "Tầng 5, Cảng Cát Lái, Phường Cát Lái, Thành phố Thủ Đức",
                "city": "TP. Hồ Chí Minh",
                "website": "https://seastar-logistics.example.vn",
                "company_size": "100 - 250 nhân sự",
                "phone": "0909 333 444",
                "email": "huy.bq@seastar-logistics.example.vn",
                "owner_id": "usr-01",
                "owner_name": "Nguyễn Văn Tuấn",
                "created_from_lead_id": "LEAD-105",
                "created_at": now - timedelta(days=2),
                
                # Toàn bộ hoạt động kế thừa từ Lead-105 (AC4)
                "activities": [
                    {
                        "id": "ACT-1000",
                        "type": ACTIVITY_CONVERT,
                        "type_label": ACTIVITY_LABELS[ACTIVITY_CONVERT],
                        "icon": ACTIVITY_ICONS[ACTIVITY_CONVERT],
                        "summary": "Khởi tạo từ Chuyển đổi Lead LEAD-105 🚀",
                        "details": "Doanh nghiệp được sinh tự động thông qua thao tác chuyển đổi Lead mà không cần nhập lại thông tin.",
                        "performed_by_id": "usr-01",
                        "performed_by_name": "Nguyễn Văn Tuấn",
                        "created_at": now - timedelta(days=2),
                        "is_milestone": True
                    },
                    {
                        "id": "ACT-1007",
                        "type": ACTIVITY_CALL,
                        "type_label": ACTIVITY_LABELS[ACTIVITY_CALL],
                        "icon": ACTIVITY_ICONS[ACTIVITY_CALL],
                        "summary": "Cuộc gọi thẩm định kỹ thuật (25 phút)",
                        "details": "Thống nhất các module cốt lõi: Quản lý khách hàng FCL/LCL, theo dõi công nợ theo chuyến tàu.",
                        "performed_by_id": "usr-01",
                        "performed_by_name": "Nguyễn Văn Tuấn",
                        "created_at": now - timedelta(days=10),
                        "inherited_from_lead": True,
                        "source_lead_id": "LEAD-105"
                    },
                    {
                        "id": "ACT-1008",
                        "type": ACTIVITY_MEETING,
                        "type_label": ACTIVITY_LABELS[ACTIVITY_MEETING],
                        "icon": ACTIVITY_ICONS[ACTIVITY_MEETING],
                        "summary": "Gặp mặt đàm phán hợp đồng tại văn phòng Cát Lái",
                        "details": "Anh Huy đồng ý mức giá 180 triệu, thanh toán chia 3 đợt. Yêu cầu chuyển lead sang tài khoản khách hàng chính thức để gửi hợp đồng.",
                        "performed_by_id": "usr-01",
                        "performed_by_name": "Nguyễn Văn Tuấn",
                        "created_at": now - timedelta(days=5),
                        "inherited_from_lead": True,
                        "source_lead_id": "LEAD-105"
                    }
                ]
            }
            self.accounts[acc_1["id"]] = acc_1

            con_1 = {
                "id": "CON-301",
                "account_id": "ACC-201",
                "account_name": "Công ty Cổ phần Vận tải & Logistics Sao Biển",
                "full_name": "Bùi Quốc Huy",
                "job_title": "Phó Tổng Giám Đốc Vận Hành",
                "phone": "0909 333 444",
                "email": "huy.bq@seastar-logistics.example.vn",
                "is_primary": True,
                "owner_id": "usr-01",
                "created_from_lead_id": "LEAD-105",
                "created_at": now - timedelta(days=2)
            }
            self.contacts[con_1["id"]] = con_1

            opp_1 = {
                "id": "OPP-401",
                "account_id": "ACC-201",
                "account_name": "Công ty Cổ phần Vận tải & Logistics Sao Biển",
                "contact_id": "CON-301",
                "contact_name": "Bùi Quốc Huy",
                "name": "Hợp đồng CRM Logistics - Sao Biển",
                "amount": 180000000,
                "stage": STAGE_NEGOTIATION,
                "close_date": (now + timedelta(days=15)).strftime("%Y-%m-%d"),
                "product": "Phần mềm Quản lý Báo giá Vận chuyển & CRM Khách hàng xuất nhập khẩu",
                "owner_id": "usr-01",
                "owner_name": "Nguyễn Văn Tuấn",
                "created_from_lead_id": "LEAD-105",
                "created_at": now - timedelta(days=2)
            }
            self.opportunities[opp_1["id"]] = opp_1

            # Khởi tạo ID đếm tiếp
            self._lead_counter = 106
            self._account_counter = 202
            self._contact_counter = 302
            self._opp_counter = 402
            self._act_counter = 1010

    # =========================================================================
    # 🎯 PHƯƠNG THỨC THEN CHỐT: CHUYỂN ĐỔI LEAD (1-CLICK CONVERSION)
    # Đáp ứng đồng thời cả 4 Tiêu chí trong đề bài
    # =========================================================================
    def convert_lead(self, lead_id, user_id, opp_name=None, opp_amount=None, opp_close_date=None, opp_stage=None):
        """
        Thực hiện chuyển đổi Lead đủ điều kiện sang Khách hàng & Cơ hội:
        
        • Tiêu chí 1: Một thao tác sinh ĐỒNG THỜI khách hàng doanh nghiệp (Account),
                      người liên hệ (Contact) và cơ hội bán hàng (Opportunity).
        • Tiêu chí 2: Dữ liệu lead được chuyển sang toàn bộ, KHÔNG PHẢI NHẬP LẠI:
                      - Tên công ty, MST, ngành nghề, địa chỉ, hotline, website -> Khách hàng
                      - Người liên hệ, chức vụ, SĐT, email -> Người liên hệ
                      - Nhu cầu, ngân sách dự kiến, ngày chốt -> Cơ hội bán hàng
        • Tiêu chí 3: Lead chuyển sang trạng thái ĐÃ CHUYỂN ĐỔI (CONVERTED),
                      bị KHÓA BẤT BIẾN (is_locked=True) và không sửa được nữa.
        • Tiêu chí 4: Toàn bộ hoạt động đã ghi trên lead (cuộc gọi, cuộc hẹn, email, ghi chú)
                      được giữ lại trọn vẹn trên khách hàng mới.
        """
        with self.lock:
            lead = self.leads.get(lead_id)
            if not lead:
                raise ValueError(f"Không tìm thấy Lead có mã '{lead_id}' trong hệ thống!")

            # Ràng buộc bảo vệ: Nếu đã chuyển đổi thì cấm chuyển đổi lại
            if lead.get("status") == STATUS_CONVERTED or lead.get("is_locked"):
                raise ValueError(
                    f"Lead '{lead_id}' đã được chuyển đổi trước đó vào lúc "
                    f"{format_datetime(lead.get('converted_at'))} và đang bị KHÓA! "
                    f"Không thể thực hiện chuyển đổi lại."
                )

            current_user = self.users.get(user_id, self.users.get("usr-01"))
            owner_id = lead.get("assigned_to_id") or user_id
            owner_user = self.users.get(owner_id, current_user)
            now = datetime.now()

            # -----------------------------------------------------------------
            # TIÊU CHÍ 1 & 2: SINH THỰC THỂ 1 - KHÁCH HÀNG DOANH NGHIỆP (ACCOUNT)
            # Tự động ánh xạ 100% dữ liệu từ lead, người dùng không cần nhập lại
            # -----------------------------------------------------------------
            acc_id = f"ACC-{self._account_counter}"
            self._account_counter += 1

            new_account = {
                "id": acc_id,
                "name": lead.get("company_name", "Khách hàng Doanh Nghiệp"),
                "tax_id": lead.get("tax_id", ""),
                "industry": lead.get("industry", "Chưa phân loại"),
                "address": lead.get("address", ""),
                "city": lead.get("city", "Hà Nội"),
                "phone": lead.get("phone", ""),
                "email": lead.get("email", ""),
                "website": lead.get("website", ""),
                "company_size": lead.get("company_size", "50-100"),
                "owner_id": owner_id,
                "owner_name": owner_user.get("name", "Nhân viên kinh doanh"),
                "created_from_lead_id": lead["id"],
                "created_at": now,
                "activities": []  # Sẽ kế thừa toàn bộ hoạt động từ lead bên dưới
            }

            # -----------------------------------------------------------------
            # TIÊU CHÍ 1 & 2: SINH THỰC THỂ 2 - NGƯỜI LIÊN HỆ (CONTACT)
            # Tự động gắn kết với Khách hàng doanh nghiệp vừa sinh
            # -----------------------------------------------------------------
            con_id = f"CON-{self._contact_counter}"
            self._contact_counter += 1

            new_contact = {
                "id": con_id,
                "account_id": acc_id,
                "account_name": new_account["name"],
                "full_name": lead.get("contact_name", "Người liên hệ"),
                "job_title": lead.get("job_title", "Đại diện mua hàng"),
                "phone": lead.get("phone", ""),
                "email": lead.get("email", ""),
                "is_primary": True,  # Người liên hệ chính được tạo từ lead
                "owner_id": owner_id,
                "owner_name": owner_user.get("name", "Nhân viên kinh doanh"),
                "created_from_lead_id": lead["id"],
                "created_at": now
            }

            # -----------------------------------------------------------------
            # TIÊU CHÍ 1 & 2: SINH THỰC THỂ 3 - CƠ HỘI BÁN HÀNG (OPPORTUNITY)
            # Tự động lấy tên sản phẩm, giá trị ước tính và ngày dự kiến từ lead
            # -----------------------------------------------------------------
            opp_id = f"OPP-{self._opp_counter}"
            self._opp_counter += 1

            # Tên cơ hội mặc định nếu người dùng không đặt riêng
            default_opp_name = f"Cơ hội {lead.get('interested_product') or 'Giải pháp CRM'} - {new_account['name']}"
            final_opp_name = (opp_name.strip() if opp_name and opp_name.strip() else default_opp_name)

            # Giá trị dự kiến kế thừa từ lead nếu không chỉ định
            if opp_amount is not None and str(opp_amount).strip() != "":
                try:
                    final_amount = float(opp_amount)
                except ValueError:
                    final_amount = float(lead.get("estimated_value", 50000000))
            else:
                final_amount = float(lead.get("estimated_value", 50000000))

            # Ngày chốt dự kiến
            final_close_date = (opp_close_date.strip() if opp_close_date and opp_close_date.strip()
                                else (lead.get("expected_close_date") or (now + timedelta(days=30)).strftime("%Y-%m-%d")))

            # Giai đoạn cơ hội
            final_stage = opp_stage if opp_stage in [STAGE_DISCOVERY, STAGE_PROPOSAL, STAGE_NEGOTIATION, STAGE_WON, STAGE_LOST] else STAGE_DISCOVERY

            new_opportunity = {
                "id": opp_id,
                "account_id": acc_id,
                "account_name": new_account["name"],
                "contact_id": con_id,
                "contact_name": new_contact["full_name"],
                "name": final_opp_name,
                "amount": final_amount,
                "stage": final_stage,
                "close_date": final_close_date,
                "product": lead.get("interested_product", ""),
                "requirements": lead.get("requirements", ""),
                "owner_id": owner_id,
                "owner_name": owner_user.get("name", "Nhân viên kinh doanh"),
                "created_from_lead_id": lead["id"],
                "created_at": now
            }

            # -----------------------------------------------------------------
            # TIÊU CHÍ 4: KẾ THỪA TOÀN BỘ HOẠT ĐỘNG TỪ LEAD SANG KHÁCH HÀNG MỚI
            # Giữ nguyên từng cuộc gọi, cuộc hẹn, email, ghi chú kèm thời gian và người thực hiện
            # -----------------------------------------------------------------
            inherited_activities = []
            for act in lead.get("activities", []):
                # Tạo bản sao sâu độc lập
                act_copy = copy.deepcopy(act)
                act_copy["inherited_from_lead"] = True
                act_copy["source_lead_id"] = lead["id"]
                new_account["activities"].append(act_copy)
                inherited_activities.append(act_copy)

            # Thêm sự kiện mốc chuyển đổi vào đầu timeline
            milestone_act = {
                "id": f"ACT-{self._act_counter}",
                "type": ACTIVITY_CONVERT,
                "type_label": ACTIVITY_LABELS[ACTIVITY_CONVERT],
                "icon": ACTIVITY_ICONS[ACTIVITY_CONVERT],
                "summary": f"Chuyển đổi thành công từ Lead {lead['id']} 🚀",
                "details": (
                    f"Đã sinh đồng thời Khách hàng doanh nghiệp [{acc_id}], "
                    f"Người liên hệ [{con_id}] và Cơ hội bán hàng [{opp_id}]. "
                    f"Kế thừa toàn bộ {len(inherited_activities)} hoạt động tương tác trước đó từ Lead."
                ),
                "performed_by_id": user_id,
                "performed_by_name": current_user.get("name", "Nhân viên"),
                "created_at": now,
                "is_milestone": True
            }
            self._act_counter += 1

            new_account["activities"].insert(0, milestone_act)
            lead["activities"].insert(0, milestone_act)

            # -----------------------------------------------------------------
            # TIÊU CHÍ 3: LEAD CHUYỂN SANG TRẠNG THÁI "ĐÃ CHUYỂN ĐỔI" VÀ BỊ KHÓA
            # Không cho phép bất kỳ thao tác sửa đổi nào sau thời điểm này
            # -----------------------------------------------------------------
            lead["status"] = STATUS_CONVERTED
            lead["is_locked"] = True
            lead["converted_at"] = now
            lead["converted_by_id"] = user_id
            lead["converted_by_name"] = current_user.get("name", "Nhân viên")
            lead["converted_account_id"] = acc_id
            lead["converted_contact_id"] = con_id
            lead["converted_opportunity_id"] = opp_id

            # Lưu vào bộ nhớ dữ liệu
            self.accounts[acc_id] = new_account
            self.contacts[con_id] = new_contact
            self.opportunities[opp_id] = new_opportunity

            # Gửi thông báo chúc mừng tới nhân viên phụ trách
            self.add_notification(
                recipient_id=owner_id,
                title="Chuyển Đổi Lead Thành Công! 🎉",
                message=(
                    f"Lead '{lead['company_name']}' ({lead['id']}) đã được chuyển đổi sang "
                    f"Khách hàng '{new_account['name']}', Người liên hệ '{new_contact['full_name']}' "
                    f"và Cơ hội '{new_opportunity['name']}' ({format_currency(final_amount)})."
                ),
                link=f"/accounts/{acc_id}"
            )

            # Ghi nhật ký kiểm toán (Audit Log)
            self.add_audit_log(
                user_id=user_id,
                action="CONVERT_LEAD",
                target_id=lead["id"],
                details=(
                    f"Chuyển đổi 1-click thành công: Account={acc_id}, Contact={con_id}, Opp={opp_id}. "
                    f"Kế thừa {len(inherited_activities)} hoạt động. Lead đã bị khóa vĩnh viễn."
                )
            )

            return {
                "lead": lead,
                "account": new_account,
                "contact": new_contact,
                "opportunity": new_opportunity,
                "inherited_count": len(inherited_activities)
            }

    # =========================================================================
    # RÀNG BUỘC TIÊU CHÍ 3: CHẶN CHỈNH SỬA LEAD ĐÃ CHUYỂN ĐỔI (IMMUTABLE LOCK)
    # =========================================================================
    def update_lead(self, lead_id, data, user_id=None):
        """
        Cập nhật thông tin Lead.
        NGHIÊM NGẶT THỰC HIỆN TIÊU CHÍ 3:
        Nếu Lead đã chuyển đổi (status == CONVERTED hoặc is_locked == True),
        hệ thống BẮT BUỘC chặn đứng thao tác và ném lỗi PermissionError / ValueError!
        """
        with self.lock:
            lead = self.leads.get(lead_id)
            if not lead:
                raise ValueError(f"Không tìm thấy Lead {lead_id}!")

            # KIỂM TRA KHÓA BẢO VỆ
            if lead.get("is_locked") or lead.get("status") == STATUS_CONVERTED:
                raise PermissionError(
                    f"⛔ RÀNG BUỘC TIÊU CHÍ 3: Lead '{lead_id}' đã chuyển sang trạng thái "
                    f"'Đã chuyển đổi' (CONVERTED) vào lúc {format_datetime(lead.get('converted_at'))} "
                    f"và ĐÃ BỊ KHÓA BẤT BIẾN! Không cho phép chỉnh sửa bất kỳ thông tin nào nữa."
                )

            # Cho phép cập nhật nếu chưa bị khóa
            editable_fields = [
                "company_name", "tax_id", "industry", "address", "city",
                "website", "company_size", "contact_name", "job_title",
                "phone", "email", "interested_product", "estimated_value",
                "expected_close_date", "requirements", "source", "status",
                "assigned_to_id", "qualification_notes"
            ]

            for field in editable_fields:
                if field in data:
                    val = data[field]
                    if field == "estimated_value":
                        try:
                            val = float(val)
                        except (ValueError, TypeError):
                            continue
                    lead[field] = val

            self.add_audit_log(
                user_id=user_id or "usr-01",
                action="UPDATE_LEAD",
                target_id=lead_id,
                details=f"Cập nhật thông tin Lead {lead_id}"
            )
            return lead

    # =========================================================================
    # THÊM HOẠT ĐỘNG VÀO LEAD (TRƯỚC KHI CHUYỂN ĐỔI)
    # =========================================================================
    def add_lead_activity(self, lead_id, user_id, act_type, summary, details):
        with self.lock:
            lead = self.leads.get(lead_id)
            if not lead:
                raise ValueError(f"Không tìm thấy Lead {lead_id}!")

            # Nếu lead đã chuyển đổi, cảnh báo người dùng nên ghi nhận vào Khách hàng (Account)
            if lead.get("is_locked"):
                raise PermissionError(
                    f"Lead {lead_id} đã chuyển đổi và bị khóa. Vui lòng ghi nhận hoạt động mới "
                    f"trực tiếp trên Khách hàng [{lead.get('converted_account_id')}] tương ứng!"
                )

            user = self.users.get(user_id, self.users.get("usr-01"))
            act_id = f"ACT-{self._act_counter}"
            self._act_counter += 1

            new_activity = {
                "id": act_id,
                "type": act_type,
                "type_label": ACTIVITY_LABELS.get(act_type, "Hoạt động"),
                "icon": ACTIVITY_ICONS.get(act_type, "📌"),
                "summary": summary,
                "details": details,
                "performed_by_id": user_id,
                "performed_by_name": user.get("name", "Nhân viên"),
                "created_at": datetime.now()
            }

            lead.setdefault("activities", []).insert(0, new_activity)

            # Nếu lead đang ở trạng thái NEW thì tự động chuyển sang CONTACTED khi có hoạt động
            if lead.get("status") == STATUS_NEW:
                lead["status"] = STATUS_CONTACTED

            return new_activity

    # =========================================================================
    # THÊM HOẠT ĐỘNG VÀO KHÁCH HÀNG DOANH NGHIỆP (ACCOUNT)
    # =========================================================================
    def add_account_activity(self, account_id, user_id, act_type, summary, details):
        with self.lock:
            acc = self.accounts.get(account_id)
            if not acc:
                raise ValueError(f"Không tìm thấy Khách hàng {account_id}!")

            user = self.users.get(user_id, self.users.get("usr-01"))
            act_id = f"ACT-{self._act_counter}"
            self._act_counter += 1

            new_activity = {
                "id": act_id,
                "type": act_type,
                "type_label": ACTIVITY_LABELS.get(act_type, "Hoạt động"),
                "icon": ACTIVITY_ICONS.get(act_type, "📌"),
                "summary": summary,
                "details": details,
                "performed_by_id": user_id,
                "performed_by_name": user.get("name", "Nhân viên"),
                "created_at": datetime.now(),
                "inherited_from_lead": False
            }

            acc.setdefault("activities", []).insert(0, new_activity)
            return new_activity

    # =========================================================================
    # TẠO MỚI LEAD
    # =========================================================================
    def create_lead(self, data, user_id="usr-01"):
        with self.lock:
            lead_id = f"LEAD-{self._lead_counter}"
            self._lead_counter += 1

            now = datetime.now()
            est_val = 50000000
            if data.get("estimated_value"):
                try:
                    est_val = float(data.get("estimated_value"))
                except ValueError:
                    pass

            new_lead = {
                "id": lead_id,
                "company_name": data.get("company_name", "Doanh nghiệp mới"),
                "tax_id": data.get("tax_id", ""),
                "industry": data.get("industry", "Thương mại & Dịch vụ"),
                "address": data.get("address", ""),
                "city": data.get("city", "Hà Nội"),
                "website": data.get("website", ""),
                "company_size": data.get("company_size", "20 - 50"),
                
                "contact_name": data.get("contact_name", "Người liên hệ"),
                "job_title": data.get("job_title", "Trưởng phòng"),
                "phone": data.get("phone", ""),
                "email": data.get("email", ""),

                "interested_product": data.get("interested_product", "Phần mềm CRM"),
                "estimated_value": est_val,
                "expected_close_date": data.get("expected_close_date") or (now + timedelta(days=30)).strftime("%Y-%m-%d"),
                "requirements": data.get("requirements", ""),
                "source": data.get("source", "Trực tiếp"),

                "status": data.get("status", STATUS_NEW),
                "is_locked": False,
                "assigned_to_id": data.get("assigned_to_id", user_id),
                "created_at": now,
                "qualification_notes": data.get("qualification_notes", ""),

                "converted_at": None,
                "converted_by_id": None,
                "converted_account_id": None,
                "converted_contact_id": None,
                "converted_opportunity_id": None,

                "activities": []
            }

            self.leads[lead_id] = new_lead
            self.add_audit_log(user_id=user_id, action="CREATE_LEAD", target_id=lead_id, details=f"Tạo mới Lead {lead_id}")
            return new_lead

    # =========================================================================
    # TRUY VẤN DỮ LIỆU
    # =========================================================================
    def get_lead(self, lead_id):
        with self.lock:
            return self.leads.get(lead_id)

    def get_leads(self, status=None, assigned_to_id=None, search=None):
        with self.lock:
            result = list(self.leads.values())
            if status:
                result = [l for l in result if l.get("status") == status]
            if assigned_to_id:
                result = [l for l in result if l.get("assigned_to_id") == assigned_to_id]
            if search:
                s = search.lower().strip()
                result = [
                    l for l in result
                    if s in l.get("company_name", "").lower()
                    or s in l.get("contact_name", "").lower()
                    or s in l.get("phone", "").lower()
                    or s in l.get("id", "").lower()
                ]
            # Sắp xếp mới nhất lên đầu
            result.sort(key=lambda x: x.get("created_at") or datetime.min, reverse=True)
            return result

    def get_account(self, account_id):
        with self.lock:
            return self.accounts.get(account_id)

    def get_accounts(self, owner_id=None, search=None):
        with self.lock:
            result = list(self.accounts.values())
            if owner_id:
                result = [a for a in result if a.get("owner_id") == owner_id]
            if search:
                s = search.lower().strip()
                result = [
                    a for a in result
                    if s in a.get("name", "").lower()
                    or s in a.get("tax_id", "").lower()
                    or s in a.get("id", "").lower()
                ]
            result.sort(key=lambda x: x.get("created_at") or datetime.min, reverse=True)
            return result

    def get_contact(self, contact_id):
        with self.lock:
            return self.contacts.get(contact_id)

    def get_contacts(self, account_id=None, search=None):
        with self.lock:
            result = list(self.contacts.values())
            if account_id:
                result = [c for c in result if c.get("account_id") == account_id]
            if search:
                s = search.lower().strip()
                result = [
                    c for c in result
                    if s in c.get("full_name", "").lower()
                    or s in c.get("phone", "").lower()
                    or s in c.get("email", "").lower()
                ]
            result.sort(key=lambda x: x.get("created_at") or datetime.min, reverse=True)
            return result

    def get_opportunity(self, opp_id):
        with self.lock:
            return self.opportunities.get(opp_id)

    def get_opportunities(self, account_id=None, stage=None, owner_id=None):
        with self.lock:
            result = list(self.opportunities.values())
            if account_id:
                result = [o for o in result if o.get("account_id") == account_id]
            if stage:
                result = [o for o in result if o.get("stage") == stage]
            if owner_id:
                result = [o for o in result if o.get("owner_id") == owner_id]
            result.sort(key=lambda x: x.get("created_at") or datetime.min, reverse=True)
            return result

    def update_opportunity_stage(self, opp_id, new_stage, user_id=None):
        with self.lock:
            opp = self.opportunities.get(opp_id)
            if not opp:
                raise ValueError("Không tìm thấy cơ hội bán hàng!")
            old_stage = opp.get("stage")
            opp["stage"] = new_stage
            self.add_audit_log(
                user_id=user_id or "usr-01",
                action="UPDATE_OPP_STAGE",
                target_id=opp_id,
                details=f"Chuyển giai đoạn từ {old_stage} -> {new_stage}"
            )
            return opp

    # =========================================================================
    # THỐNG KÊ & METRICS
    # =========================================================================
    def get_kpis(self):
        with self.lock:
            total_leads = len(self.leads)
            qualified_leads = len([l for l in self.leads.values() if l.get("status") == STATUS_QUALIFIED])
            converted_leads = len([l for l in self.leads.values() if l.get("status") == STATUS_CONVERTED])
            in_care_leads = len([l for l in self.leads.values() if l.get("status") in [STATUS_NEW, STATUS_CONTACTED]])
            
            total_accounts = len(self.accounts)
            total_contacts = len(self.contacts)
            total_opportunities = len(self.opportunities)

            total_pipeline_val = sum(o.get("amount", 0) for o in self.opportunities.values())
            won_val = sum(o.get("amount", 0) for o in self.opportunities.values() if o.get("stage") == STAGE_WON)

            conversion_rate = round((converted_leads / total_leads * 100), 1) if total_leads > 0 else 0.0

            return {
                "total_leads": total_leads,
                "qualified_leads": qualified_leads,
                "converted_leads": converted_leads,
                "in_care_leads": in_care_leads,
                "total_accounts": total_accounts,
                "total_contacts": total_contacts,
                "total_opportunities": total_opportunities,
                "total_pipeline_val": total_pipeline_val,
                "won_val": won_val,
                "conversion_rate": conversion_rate
            }

    # =========================================================================
    # THÔNG BÁO & NHẬT KÝ KIỂM TOÁN
    # =========================================================================
    def add_notification(self, recipient_id, title, message, link=None):
        notif = {
            "id": f"NTF-{self._notif_counter}",
            "recipient_id": recipient_id,
            "title": title,
            "message": message,
            "link": link,
            "is_read": False,
            "created_at": datetime.now()
        }
        self._notif_counter += 1
        self.notifications.insert(0, notif)
        return notif

    def get_notifications(self, recipient_id=None, unread_only=False):
        with self.lock:
            res = self.notifications
            if recipient_id:
                res = [n for n in res if n.get("recipient_id") == recipient_id]
            if unread_only:
                res = [n for n in res if not n.get("is_read")]
            return res

    def mark_notifications_read(self, recipient_id):
        with self.lock:
            for n in self.notifications:
                if n.get("recipient_id") == recipient_id:
                    n["is_read"] = True

    def add_audit_log(self, user_id, action, target_id, details):
        log = {
            "id": f"LOG-{self._log_counter}",
            "user_id": user_id,
            "action": action,
            "target_id": target_id,
            "details": details,
            "created_at": datetime.now()
        }
        self._log_counter += 1
        self.audit_logs.insert(0, log)
        return log

    def get_audit_logs(self, limit=50):
        with self.lock:
            return self.audit_logs[:limit]


# Khởi tạo singleton DB
db = Database()
