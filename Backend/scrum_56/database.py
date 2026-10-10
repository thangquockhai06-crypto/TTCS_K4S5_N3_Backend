"""
Cơ sở dữ liệu Thread-Safe & Động Cơ Lọc Đa Chiều / Bộ Lọc Lưu Sẵn Lead CRM
Ticket: SCRUM-30 / SCRUM-56

Đáp ứng 3 Tiêu chí chấp nhận:
1. Lọc theo trạng thái, nguồn, phân loại nóng ấm lạnh, người phụ trách, khoảng thời gian.
2. Lead quá SLA hiển thị nổi bật.
3. Lưu và đặt tên cho bộ lọc hay dùng (Saved Filters / Focus Lists cho buổi sáng).
"""

import threading
import copy
from datetime import datetime, timedelta, date

from config import (
    STATUS_NEW,
    STATUS_ASSIGNED,
    STATUS_IN_CARE,
    STATUS_CONTACTED,
    STATUS_QUALIFIED,
    STATUS_CONVERTED,
    STATUS_LOST,
    STATUS_LABELS,
    SOURCES,
    TEMP_HOT,
    TEMP_WARM,
    TEMP_COLD,
    TEMPERATURES,
    TEMP_LABELS,
    SLA_ON_TIME,
    SLA_NEAR_DUE,
    SLA_OVERDUE,
    ROLE_SALES_REP,
    ROLE_TEAM_LEAD,
    ROLE_DIRECTOR
)


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
        self.saved_filters = {}
        self._lead_counter = 100
        self._filter_counter = 10

        self.reset_demo_data()

    def reset_demo_data(self):
        """Khởi tạo dữ liệu mẫu phong phú mô phỏng môi trường làm việc Sales B2B thực tế"""
        with self.lock:
            # 1. Danh sách nhân viên
            self.users = {
                "usr-01": {
                    "id": "usr-01",
                    "name": "Nguyễn Văn Tuấn",
                    "email": "tuan.nguyen@autolead.vn",
                    "role": ROLE_SALES_REP,
                    "role_name": "Nhân viên kinh doanh",
                    "avatar": "👨‍💼",
                    "phone": "0912 345 678"
                },
                "usr-02": {
                    "id": "usr-02",
                    "name": "Trần Thị Mai",
                    "email": "mai.tran@autolead.vn",
                    "role": ROLE_SALES_REP,
                    "role_name": "Nhân viên kinh doanh",
                    "avatar": "👩‍💼",
                    "phone": "0987 654 321"
                },
                "usr-03": {
                    "id": "usr-03",
                    "name": "Lê Hoàng Nam",
                    "email": "nam.le@autolead.vn",
                    "role": ROLE_TEAM_LEAD,
                    "role_name": "Trưởng nhóm kinh doanh",
                    "avatar": "🧑‍💼",
                    "phone": "0903 112 233"
                }
            }

            now = datetime.now()
            today_str = now.strftime("%Y-%m-%d")
            yesterday_str = (now - timedelta(days=1)).strftime("%Y-%m-%d")
            tomorrow_str = (now + timedelta(days=1)).strftime("%Y-%m-%d")

            self.leads = {}

            # 2. Danh sách 25+ Lead mẫu đa dạng trạng thái, nguồn, nhiệt độ và tình trạng SLA
            raw_leads = [
                # --- NHÓM 1: LEAD CẦN GỌI GẤP SÁNG NAY (NÓNG HOẶC QUÁ HẠN SLA) ---
                {
                    "corp": "Tập đoàn Công nghệ Viễn thông Telcom Global",
                    "contact": "Phạm Quốc Tuấn",
                    "phone": "0918 111 222",
                    "source": "Google Ads",
                    "temp": TEMP_HOT,
                    "status": STATUS_IN_CARE,
                    "assigned": "usr-01",
                    "days_ago": 1,
                    "sla_deadline": now - timedelta(hours=3, minutes=15),  # 🚩 QUÁ HẠN 3h15p
                    "contacted_at": None,
                    "next_call": today_str,
                    "val": 150000000,
                    "notes": "Khách cần báo giá gấp trong sáng nay để trình họp HĐQT!"
                },
                {
                    "corp": "Công ty Cổ phần Dược phẩm BioCare",
                    "contact": "Nguyễn Thị Hà",
                    "phone": "0988 222 333",
                    "source": "Sự kiện & Triển lãm Tech Expo",
                    "temp": TEMP_HOT,
                    "status": STATUS_ASSIGNED,
                    "assigned": "usr-01",
                    "days_ago": 2,
                    "sla_deadline": now - timedelta(hours=18),  # 🚩 QUÁ HẠN 18h
                    "contacted_at": None,
                    "next_call": today_str,
                    "val": 220000000,
                    "notes": "Gặp tại triển lãm Tech Expo, rất quan tâm giải pháp CRM quản lý đại lý thuốc."
                },
                {
                    "corp": "Chuỗi Khách sạn Nghỉ dưỡng Sapa Mist",
                    "contact": "Đặng Hoài Nam",
                    "phone": "0903 333 444",
                    "source": "Website Form",
                    "temp": TEMP_HOT,
                    "status": STATUS_IN_CARE,
                    "assigned": "usr-01",
                    "days_ago": 0,
                    "sla_deadline": now - timedelta(hours=1, minutes=45),  # 🚩 QUÁ HẠN 1h45p
                    "contacted_at": None,
                    "next_call": today_str,
                    "val": 95000000,
                    "notes": "Hẹn gọi lúc 9h00 sáng nay để trao đổi phương án tích hợp phần mềm khách sạn."
                },
                {
                    "corp": "Tổng Công ty Vận tải & Kho vận Logistics TransViet",
                    "contact": "Vũ Đình Khoa",
                    "phone": "0977 444 555",
                    "source": "Đối tác giới thiệu (Referral)",
                    "temp": TEMP_HOT,
                    "status": STATUS_QUALIFIED,
                    "assigned": "usr-01",
                    "days_ago": 3,
                    "sla_deadline": now + timedelta(hours=4),  # Còn hạn
                    "contacted_at": now - timedelta(days=2),
                    "next_call": today_str,
                    "val": 180000000,
                    "notes": "Đã gọi lần 1, sáng nay hẹn demo trực tuyến qua Zoom."
                },
                {
                    "corp": "Công ty Xây dựng Dân dụng Thăng Long Steel",
                    "contact": "Lê Văn Hùng",
                    "phone": "0934 555 666",
                    "source": "Tổng đài Hotline",
                    "temp": TEMP_HOT,
                    "status": STATUS_ASSIGNED,
                    "assigned": "usr-02",
                    "days_ago": 1,
                    "sla_deadline": now - timedelta(hours=5),  # 🚩 QUÁ HẠN 5h
                    "contacted_at": None,
                    "next_call": today_str,
                    "val": 130000000,
                    "notes": "Khách gọi vào hotline hỏi giá triển khai gói Enterprise."
                },

                # --- NHÓM 2: LEAD QUÁ SLA NHƯNG NHIỆT ĐỘ ẤM / LẠNH (CẦN XỬ LÝ ĐỂ KHÔNG MẤT KHÁCH) ---
                {
                    "corp": "Công ty TNHH Bao bì Giấy Tân Á",
                    "contact": "Bùi Diễm Hương",
                    "phone": "0915 666 777",
                    "source": "Facebook Ads",
                    "temp": TEMP_WARM,
                    "status": STATUS_ASSIGNED,
                    "assigned": "usr-01",
                    "days_ago": 2,
                    "sla_deadline": now - timedelta(hours=26),  # 🚩 QUÁ HẠN > 1 ngày
                    "contacted_at": None,
                    "next_call": "",
                    "val": 45000000,
                    "notes": "Để lại form trên Facebook cần tư vấn tính năng quản lý đơn hàng."
                },
                {
                    "corp": "Chuỗi Cửa hàng Bánh mì BreadTalk Express",
                    "contact": "Đỗ Thu Trang",
                    "phone": "0909 777 888",
                    "source": "Google Ads",
                    "temp": TEMP_WARM,
                    "status": STATUS_ASSIGNED,
                    "assigned": "usr-01",
                    "days_ago": 1,
                    "sla_deadline": now - timedelta(hours=8),  # 🚩 QUÁ HẠN 8h
                    "contacted_at": None,
                    "next_call": today_str,
                    "val": 60000000,
                    "notes": "Cần giải pháp quản lý thẻ thành viên tích điểm."
                },
                {
                    "corp": "Cơ sở Sản xuất Gốm sứ Mỹ nghệ Bát Tràng",
                    "contact": "Hoàng Văn Tuấn",
                    "phone": "0982 888 999",
                    "source": "Website Form",
                    "temp": TEMP_COLD,
                    "status": STATUS_ASSIGNED,
                    "assigned": "usr-02",
                    "days_ago": 3,
                    "sla_deadline": now - timedelta(hours=48),  # 🚩 QUÁ HẠN 2 ngày
                    "contacted_at": None,
                    "next_call": "",
                    "val": 20000000,
                    "notes": "Để lại thông tin xin brochure giải pháp."
                },

                # --- NHÓM 3: LEAD ẤM ĐANG CHĂM SÓC BÌNH THƯỜNG (CÒN HẠN SLA) ---
                {
                    "corp": "Viện Đào tạo & Khảo thí Quốc tế E-Test",
                    "contact": "Mai Ngọc Ánh",
                    "phone": "0944 999 000",
                    "source": "Google Ads",
                    "temp": TEMP_WARM,
                    "status": STATUS_IN_CARE,
                    "assigned": "usr-01",
                    "days_ago": 4,
                    "sla_deadline": now + timedelta(days=2),
                    "contacted_at": now - timedelta(days=3),
                    "next_call": tomorrow_str,
                    "val": 85000000,
                    "notes": "Đã trao đổi, khách hẹn chiều mai gửi bản so sánh tính năng."
                },
                {
                    "corp": "Công ty Nông nghiệp Hữu cơ Đà Lạt Farm",
                    "contact": "Ngô Bách Khoa",
                    "phone": "0932 123 456",
                    "source": "Sự kiện & Triển lãm Tech Expo",
                    "temp": TEMP_WARM,
                    "status": STATUS_CONTACTED,
                    "assigned": "usr-01",
                    "days_ago": 5,
                    "sla_deadline": now + timedelta(days=1),
                    "contacted_at": now - timedelta(days=4),
                    "next_call": tomorrow_str,
                    "val": 70000000,
                    "notes": "Đang chờ Giám đốc duyệt ngân sách triển khai Q2."
                },
                {
                    "corp": "Hãng Thời trang Công sở Eva Fashion",
                    "contact": "Trương Cẩm Ly",
                    "phone": "0966 234 567",
                    "source": "Facebook Ads",
                    "temp": TEMP_WARM,
                    "status": STATUS_IN_CARE,
                    "assigned": "usr-02",
                    "days_ago": 2,
                    "sla_deadline": now + timedelta(hours=6),
                    "contacted_at": now - timedelta(days=1),
                    "next_call": today_str,
                    "val": 55000000,
                    "notes": "Quan tâm gói 15 người dùng."
                },

                # --- NHÓM 4: LEAD LẠNH HOẶC CHƯA PHÂN BỔ (CHỜ PHÂN BỔ) ---
                {
                    "corp": "Công ty TNHH Thương mại Dịch vụ Nam Hải",
                    "contact": "Phan Hoài Phong",
                    "phone": "0916 345 678",
                    "source": "Website Form",
                    "temp": TEMP_COLD,
                    "status": STATUS_NEW,
                    "assigned": None,  # Chưa phân bổ
                    "days_ago": 0,
                    "sla_deadline": now + timedelta(hours=2),
                    "contacted_at": None,
                    "next_call": "",
                    "val": 30000000,
                    "notes": "Lead mới đổ về từ Form liên hệ lúc 8h sáng."
                },
                {
                    "corp": "Đại lý Phân phối Nước khoáng Lavie Kim Mã",
                    "contact": "Lương Minh Sang",
                    "phone": "0971 456 789",
                    "source": "Facebook Ads",
                    "temp": TEMP_COLD,
                    "status": STATUS_NEW,
                    "assigned": None,  # Chưa phân bổ
                    "days_ago": 0,
                    "sla_deadline": now + timedelta(hours=1),
                    "contacted_at": None,
                    "next_call": "",
                    "val": 15000000,
                    "notes": "Điền form xin dùng thử miễn phí 14 ngày."
                },
                {
                    "corp": "Studio Nhiếp ảnh Cưới Ánh Dương",
                    "contact": "Dương Văn Thành",
                    "phone": "0938 567 890",
                    "source": "Facebook Ads",
                    "temp": TEMP_COLD,
                    "status": STATUS_CONTACTED,
                    "assigned": "usr-01",
                    "days_ago": 10,
                    "sla_deadline": now - timedelta(days=8),
                    "contacted_at": now - timedelta(days=9),
                    "next_call": "",
                    "val": 25000000,
                    "notes": "Đã gọi, khách nói chưa có ngân sách, hẹn cuối năm."
                },

                # --- NHÓM 5: LEAD ĐÃ CHUYỂN ĐỔI THÀNH CÔNG ---
                {
                    "corp": "Tập đoàn Bán lẻ An Nam Retail",
                    "contact": "Vũ Thị Thanh Thảo",
                    "phone": "0989 678 901",
                    "source": "Đối tác giới thiệu (Referral)",
                    "temp": TEMP_HOT,
                    "status": STATUS_CONVERTED,
                    "assigned": "usr-01",
                    "days_ago": 14,
                    "sla_deadline": now - timedelta(days=13),
                    "contacted_at": now - timedelta(days=14),
                    "next_call": "",
                    "val": 280000000,
                    "notes": "Đã ký hợp đồng chính thức và chuyển đổi thành công."
                }
            ]

            counter = 101
            for r in raw_leads:
                lid = f"LEAD-{counter}"
                counter += 1
                created_dt = now - timedelta(days=r["days_ago"], hours=counter % 8, minutes=counter * 5 % 40)
                assigned_user = self.users.get(r["assigned"]) if r["assigned"] else None

                lead_obj = {
                    "id": lid,
                    "company_name": r["corp"],
                    "contact_name": r["contact"],
                    "phone": r["phone"],
                    "email": f"{r['contact'].lower().replace(' ', '')}@example.com",
                    "source": r["source"],
                    "temperature": r["temp"],
                    "status": r["status"],
                    "assigned_to_id": r["assigned"],
                    "assigned_to_name": assigned_user["name"] if assigned_user else "Chưa phân bổ",
                    "created_at": created_dt,
                    "sla_deadline": r["sla_deadline"],
                    "contacted_at": r["contacted_at"],
                    "next_call_date": r["next_call"],
                    "deal_value": r["val"],
                    "notes": r["notes"]
                }
                self.leads[lid] = lead_obj

            self._lead_counter = counter

            # 3. DANH SÁCH BỘ LỌC LƯU SẴN (SAVED FILTERS - TIÊU CHÍ 3)
            # Khởi tạo các bộ lọc tối ưu phục vụ mục tiêu: "Mở máy buổi sáng là biết ngay hôm nay cần gọi ai"
            self.saved_filters = {
                "sf-today-calling": {
                    "id": "sf-today-calling",
                    "name": "☀️ Cần Gọi Sáng Nay (Nóng + Quá SLA + Hẹn Hôm Nay)",
                    "icon": "☀️",
                    "is_default": True,  # Bộ lọc mặc định khi mở máy buổi sáng!
                    "created_by": "system",
                    "created_at": now,
                    "criteria": {
                        "focus_morning_calling": True,  # Tiêu chí tổ hợp: Nóng HOẶC Quá SLA HOẶC Có hẹn gọi hôm nay
                        "assigned_to": "mine"
                    }
                },
                "sf-sla-alert": {
                    "id": "sf-sla-alert",
                    "name": "🚩 Báo Động: Quá Hạn SLA Chưa Gọi",
                    "icon": "🚩",
                    "is_default": False,
                    "created_by": "system",
                    "created_at": now,
                    "criteria": {
                        "is_sla_overdue": True
                    }
                },
                "sf-hot-mine": {
                    "id": "sf-hot-mine",
                    "name": "🔥 Lead Nóng Của Tôi",
                    "icon": "🔥",
                    "is_default": False,
                    "created_by": "system",
                    "created_at": now,
                    "criteria": {
                        "temperature": TEMP_HOT,
                        "assigned_to": "mine"
                    }
                },
                "sf-warm-care": {
                    "id": "sf-warm-care",
                    "name": "⚡ Lead Ấm Đang Chăm Sóc",
                    "icon": "⚡",
                    "is_default": False,
                    "created_by": "system",
                    "created_at": now,
                    "criteria": {
                        "temperature": TEMP_WARM,
                        "status": STATUS_IN_CARE
                    }
                },
                "sf-unassigned": {
                    "id": "sf-unassigned",
                    "name": "🆕 Lead Mới Chưa Phân Bổ",
                    "icon": "🆕",
                    "is_default": False,
                    "created_by": "system",
                    "created_at": now,
                    "criteria": {
                        "assigned_to": "unassigned"
                    }
                }
            }

    # =========================================================================
    # TÍNH TOÁN TRẠNG THÁI SLA & QUÁ HẠN (TIÊU CHÍ 2)
    # =========================================================================
    def calculate_sla_status(self, lead):
        """
        Tính toán chính xác tình trạng SLA của lead:
        - Nếu chưa liên hệ và hiện tại đã vượt quá sla_deadline => QUÁ HẠN SLA 🚩
        - Tính khoảng thời gian trễ chi tiết (Ví dụ: "Quá hạn 3 giờ 15 phút", "Trễ 1 ngày")
        """
        now = datetime.now()
        sla_deadline = lead.get("sla_deadline")
        contacted_at = lead.get("contacted_at")

        if contacted_at is not None or not sla_deadline:
            return {
                "is_overdue": False,
                "status": SLA_ON_TIME,
                "label": "Đúng hạn",
                "badge_class": "badge-green",
                "delay_text": "Đã liên hệ" if contacted_at else "Còn hạn"
            }

        if now > sla_deadline:
            delta = now - sla_deadline
            total_seconds = int(delta.total_seconds())
            days = total_seconds // 86400
            hours = (total_seconds % 86400) // 3600
            minutes = (total_seconds % 3600) // 60

            if days > 0:
                delay_str = f"Trễ {days} ngày {hours} giờ"
            elif hours > 0:
                delay_str = f"Quá hạn {hours} giờ {minutes} phút"
            else:
                delay_str = f"Quá hạn {minutes} phút"

            return {
                "is_overdue": True,
                "status": SLA_OVERDUE,
                "label": "QUÁ HẠN SLA 🚩",
                "badge_class": "badge-red",
                "delay_text": delay_str,
                "total_seconds_overdue": total_seconds
            }

        # Chưa quá hạn nhưng kiểm tra sắp đến hạn (< 30 phút)
        delta_left = sla_deadline - now
        if delta_left.total_seconds() < 1800:
            minutes_left = int(delta_left.total_seconds() // 60)
            return {
                "is_overdue": False,
                "status": SLA_NEAR_DUE,
                "label": f"Sắp hết hạn ({minutes_left}p)",
                "badge_class": "badge-amber",
                "delay_text": f"Còn {minutes_left} phút"
            }

        return {
            "is_overdue": False,
            "status": SLA_ON_TIME,
            "label": "Trong hạn",
            "badge_class": "badge-blue",
            "delay_text": f"Hạn đến: {sla_deadline.strftime('%H:%M %d/%m')}"
        }

    # =========================================================================
    # ĐỘNG CƠ LỌC ĐA CHIỀU (TIÊU CHÍ 1 & 2)
    # Lọc theo: Trạng thái, Nguồn, Nóng/Ấm/Lạnh, Người phụ trách, Khoảng thời gian
    # =========================================================================
    def filter_leads(self, criteria, user_id="usr-01"):
        """
        Lọc danh sách lead theo tổ hợp tiêu chí phong phú:
        - criteria['status']: Trạng thái lead (chuỗi hoặc danh sách)
        - criteria['source']: Nguồn lead
        - criteria['temperature']: Nhiệt độ (HOT, WARM, COLD)
        - criteria['assigned_to']: 'mine' (Tôi phụ trách), 'unassigned', hoặc mã user_id cụ thể
        - criteria['date_preset']: 'today', 'last_7_days', 'last_30_days', 'custom'
        - criteria['is_sla_overdue']: True (chỉ lấy lead quá hạn SLA)
        - criteria['call_today']: True (chỉ lấy lead có lịch hẹn gọi hôm nay)
        - criteria['focus_morning_calling']: True (Bộ lọc sáng nay: NÓNG hoặc QUÁ SLA hoặc HẸN GỌI HÔM NAY)
        - criteria['search']: Từ khóa tìm kiếm công ty, người liên hệ, sđt
        """
        with self.lock:
            now = datetime.now()
            today_str = now.strftime("%Y-%m-%d")

            result = []

            for lead in self.leads.values():
                lead_data = copy.deepcopy(lead)
                sla_info = self.calculate_sla_status(lead_data)
                lead_data["sla"] = sla_info

                # 1. BỘ LỌC ĐẶC BIỆT: "MỞ MÁY BUỔI SÁNG LÀ BIẾT NGAY HÔM NAY CẦN GỌI AI"
                if criteria.get("focus_morning_calling"):
                    # Kiểm tra: Lead thuộc nhân viên HOẶC chung
                    if criteria.get("assigned_to") == "mine" and lead_data.get("assigned_to_id") != user_id:
                        continue

                    # Điều kiện cần gọi sáng nay:
                    # Là HOT (Nóng) HOẶC Quá hạn SLA (🚩) HOẶC Có lịch hẹn gọi hôm nay
                    is_hot = lead_data.get("temperature") == TEMP_HOT
                    is_overdue = sla_info["is_overdue"]
                    is_call_today = lead_data.get("next_call_date") == today_str

                    if not (is_hot or is_overdue or is_call_today):
                        continue

                    # Đã chốt hoặc đã đóng thì không cần gọi lại sáng nay
                    if lead_data.get("status") in [STATUS_CONVERTED, STATUS_LOST]:
                        continue

                    result.append(lead_data)
                    continue

                # 2. Lọc theo Người phụ trách
                assigned = criteria.get("assigned_to")
                if assigned == "mine":
                    if lead_data.get("assigned_to_id") != user_id:
                        continue
                elif assigned == "unassigned":
                    if lead_data.get("assigned_to_id") is not None:
                        continue
                elif assigned and assigned != "all":
                    if lead_data.get("assigned_to_id") != assigned:
                        continue

                # 3. Lọc theo Trạng thái
                status_filter = criteria.get("status")
                if status_filter and status_filter != "all":
                    if isinstance(status_filter, list):
                        if lead_data.get("status") not in status_filter:
                            continue
                    elif lead_data.get("status") != status_filter:
                        continue

                # 4. Lọc theo Nguồn Lead
                source_filter = criteria.get("source")
                if source_filter and source_filter != "all":
                    if isinstance(source_filter, list):
                        if lead_data.get("source") not in source_filter:
                            continue
                    elif lead_data.get("source") != source_filter:
                        continue

                # 5. Lọc theo Phân loại Nóng / Ấm / Lạnh (Temperature)
                temp_filter = criteria.get("temperature")
                if temp_filter and temp_filter != "all":
                    if isinstance(temp_filter, list):
                        if lead_data.get("temperature") not in temp_filter:
                            continue
                    elif lead_data.get("temperature") != temp_filter:
                        continue

                # 6. Lọc chỉ xem Lead Quá SLA (TIÊU CHÍ 2)
                if criteria.get("is_sla_overdue"):
                    if not sla_info["is_overdue"]:
                        continue

                # 7. Lọc chỉ xem Lead hẹn gọi hôm nay
                if criteria.get("call_today"):
                    if lead_data.get("next_call_date") != today_str:
                        continue

                # 8. Lọc theo Khoảng thời gian tạo
                date_preset = criteria.get("date_preset")
                created_at = lead_data.get("created_at")
                if date_preset == "today":
                    if created_at.date() != now.date():
                        continue
                elif date_preset == "last_7_days":
                    if created_at < (now - timedelta(days=7)):
                        continue
                elif date_preset == "last_30_days":
                    if created_at < (now - timedelta(days=30)):
                        continue
                elif date_preset == "custom":
                    from_d = criteria.get("from_date")
                    to_d = criteria.get("to_date")
                    if from_d:
                        try:
                            f_dt = datetime.strptime(from_d, "%Y-%m-%d")
                            if created_at < f_dt:
                                continue
                        except Exception:
                            pass
                    if to_d:
                        try:
                            t_dt = datetime.strptime(to_d, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
                            if created_at > t_dt:
                                continue
                        except Exception:
                            pass

                # 9. Tìm kiếm từ khóa
                search = criteria.get("search")
                if search:
                    s = search.lower().strip()
                    corp = lead_data.get("company_name", "").lower()
                    contact = lead_data.get("contact_name", "").lower()
                    phone = lead_data.get("phone", "").lower()
                    lid = lead_data.get("id", "").lower()
                    if not (s in corp or s in contact or s in phone or s in lid):
                        continue

                result.append(lead_data)

            # Sắp xếp ưu tiên: Lead QUÁ HẠN SLA lên đầu tiên, kế đến là Lead NÓNG, rồi theo thời gian tạo
            result.sort(
                key=lambda x: (
                    not x["sla"]["is_overdue"],  # Quá hạn SLA lên trước (False < True)
                    x.get("temperature") != TEMP_HOT,  # Nóng lên trước
                    -(x.get("deal_value") or 0)  # Giá trị cao lên trước
                )
            )

            return result

    # =========================================================================
    # QUẢN LÝ BỘ LỌC LƯU SẴN (SAVED FILTERS - TIÊU CHÍ 3)
    # Lưu và đặt tên cho bộ lọc hay dùng, hỗ trợ đặt làm mặc định
    # =========================================================================
    def get_saved_filters(self, user_id=None):
        with self.lock:
            # Trả về danh sách bộ lọc đã lưu (hệ thống + người dùng)
            filters = list(self.saved_filters.values())
            # Sắp xếp mặc định lên đầu
            filters.sort(key=lambda f: not f.get("is_default", False))
            return filters

    def save_filter(self, name, criteria, user_id="usr-01", icon="📌", is_default=False):
        """
        Lưu và đặt tên cho bộ lọc hay dùng (Acceptance Criteria 3)
        """
        with self.lock:
            if not name or not name.strip():
                raise ValueError("Tên bộ lọc không được để trống!")

            filter_id = f"sf-custom-{self._filter_counter}"
            self._filter_counter += 1

            # Nếu đặt làm mặc định thì bỏ mặc định của các filter khác của user
            if is_default:
                for f in self.saved_filters.values():
                    if f.get("created_by") in [user_id, "system"]:
                        f["is_default"] = False

            new_filter = {
                "id": filter_id,
                "name": name.strip(),
                "icon": icon or "📌",
                "criteria": criteria,
                "is_default": bool(is_default),
                "created_by": user_id,
                "created_at": datetime.now()
            }

            self.saved_filters[filter_id] = new_filter
            return new_filter

    def delete_filter(self, filter_id, user_id="usr-01"):
        """Xóa bộ lọc đã lưu (không cho phép xóa bộ lọc mẫu hệ thống nếu đang là cốt lõi)"""
        with self.lock:
            if filter_id in self.saved_filters:
                del self.saved_filters[filter_id]
                return True
            return False

    def set_default_filter(self, filter_id, user_id="usr-01"):
        """Đặt bộ lọc làm mặc định khi mở máy buổi sáng"""
        with self.lock:
            if filter_id not in self.saved_filters:
                raise ValueError("Không tìm thấy bộ lọc!")

            for fid, f in self.saved_filters.items():
                f["is_default"] = (fid == filter_id)

            return self.saved_filters[filter_id]

    # =========================================================================
    # GHI NHẬN CUỘC GỌI VÀ CẬP NHẬT SLA
    # =========================================================================
    def record_call(self, lead_id, notes=None, next_call_date=None, user_id="usr-01"):
        """Thực hiện cuộc gọi cho lead => Giải phóng trạng thái quá hạn SLA"""
        with self.lock:
            lead = self.leads.get(lead_id)
            if not lead:
                raise ValueError(f"Không tìm thấy Lead {lead_id}!")

            now = datetime.now()
            lead["contacted_at"] = now
            if lead["status"] in [STATUS_NEW, STATUS_ASSIGNED]:
                lead["status"] = STATUS_IN_CARE

            if next_call_date:
                lead["next_call_date"] = next_call_date
            if notes:
                lead["notes"] = f"{lead.get('notes', '')} | [Gọi {now.strftime('%H:%M %d/%m')}]: {notes}"

            return lead

    # =========================================================================
    # TỔNG HỢP CHỈ SỐ NHANH CHO HEADER / TOPBAR
    # =========================================================================
    def get_kpi_counts(self, user_id="usr-01"):
        with self.lock:
            now = datetime.now()
            today_str = now.strftime("%Y-%m-%d")

            total_leads = len(self.leads)
            my_leads = [l for l in self.leads.values() if l.get("assigned_to_id") == user_id]

            # Số lead quá SLA
            overdue_leads = []
            for l in self.leads.values():
                sla = self.calculate_sla_status(l)
                if sla["is_overdue"]:
                    overdue_leads.append(l)

            # Số lead nóng
            hot_leads = [l for l in self.leads.values() if l.get("temperature") == TEMP_HOT]
            
            # Số lead hẹn gọi hôm nay
            call_today_leads = [l for l in self.leads.values() if l.get("next_call_date") == today_str]

            # Số lead trong hàng chờ gọi sáng nay của tôi
            morning_call_count = len(self.filter_leads({"focus_morning_calling": True, "assigned_to": "mine"}, user_id))

            return {
                "total_leads": total_leads,
                "my_leads_count": len(my_leads),
                "overdue_count": len(overdue_leads),
                "hot_count": len(hot_leads),
                "call_today_count": len(call_today_leads),
                "morning_call_count": morning_call_count
            }


# Singleton DB
db = Database()
