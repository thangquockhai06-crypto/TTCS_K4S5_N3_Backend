"""
Quản lý dữ liệu bộ nhớ Thread-Safe & Xử lý nghiệp vụ Lead CRM
User Story: SCRUM-30 / SCRUM-51
Đáp ứng:
1. Nhân viên nhận lead thì lead chuyển sang "Đang chăm sóc" (IN_CARE).
2. Từ chối bắt buộc nhập lý do, lead quay lại hàng chờ phân bổ (PENDING_ALLOCATION).
3. Quá SLA phản hồi mà chưa liên hệ thì lead được gắn cờ (is_flagged=True) và báo cho trưởng nhóm.
"""

import threading
from datetime import datetime, timedelta
import copy

from config import (
    STATUS_PENDING_ALLOCATION,
    STATUS_ASSIGNED,
    STATUS_IN_CARE,
    STATUS_CONTACTED,
    ROLE_SALES_REP,
    ROLE_TEAM_LEAD,
    ROLE_DIRECTOR,
    DEFAULT_SLA_SECONDS,
    DEMO_FAST_SLA_SECONDS
)


def get_current_time():
    """Lấy thời gian hiện tại chuẩn ISO"""
    return datetime.now()


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


class Database:
    def __init__(self):
        self.lock = threading.RLock()
        self.users = {}
        self.teams = {}
        self.leads = {}
        self.notifications = []
        self.audit_logs = []
        self._lead_counter = 100
        self._notif_counter = 1
        self._log_counter = 1

        self.reset_demo_data()

    def reset_demo_data(self):
        """Khởi tạo dữ liệu mẫu phong phú mô phỏng môi trường làm việc thực tế"""
        with self.lock:
            self.users = {
                "usr-01": {
                    "id": "usr-01",
                    "name": "Nguyễn Văn Tuấn",
                    "email": "tuan.nguyen@autolead.vn",
                    "role": ROLE_SALES_REP,
                    "role_name": "Nhân viên kinh doanh",
                    "team_id": "team-01",
                    "team_name": "Đội Kinh Doanh Hà Nội (Team A)",
                    "avatar": "👨‍💼",
                    "phone": "0912 345 678"
                },
                "usr-02": {
                    "id": "usr-02",
                    "name": "Trần Thị Mai",
                    "email": "mai.tran@autolead.vn",
                    "role": ROLE_SALES_REP,
                    "role_name": "Nhân viên kinh doanh",
                    "team_id": "team-01",
                    "team_name": "Đội Kinh Doanh Hà Nội (Team A)",
                    "avatar": "👩‍💼",
                    "phone": "0987 654 321"
                },
                "usr-03": {
                    "id": "usr-03",
                    "name": "Lê Hoàng Nam",
                    "email": "nam.le@autolead.vn",
                    "role": ROLE_TEAM_LEAD,
                    "role_name": "Trưởng nhóm kinh doanh",
                    "team_id": "team-01",
                    "team_name": "Đội Kinh Doanh Hà Nội (Team A)",
                    "avatar": "🧑‍💼",
                    "phone": "0903 112 233"
                },
                "usr-04": {
                    "id": "usr-04",
                    "name": "Phạm Đức Thắng",
                    "email": "thang.pham@autolead.vn",
                    "role": ROLE_DIRECTOR,
                    "role_name": "Giám đốc kinh doanh",
                    "team_id": "team-all",
                    "team_name": "Ban Giám Đốc",
                    "avatar": "👔",
                    "phone": "0909 999 888"
                },
                "usr-05": {
                    "id": "usr-05",
                    "name": "Đặng Thu Hà",
                    "email": "ha.dang@autolead.vn",
                    "role": ROLE_SALES_REP,
                    "role_name": "Nhân viên kinh doanh",
                    "team_id": "team-02",
                    "team_name": "Đội Kinh Doanh TP.HCM (Team B)",
                    "avatar": "👩‍💻",
                    "phone": "0933 445 566"
                }
            }

            self.teams = {
                "team-01": {
                    "id": "team-01",
                    "name": "Đội Kinh Doanh Hà Nội (Team A)",
                    "lead_id": "usr-03",
                    "lead_name": "Lê Hoàng Nam",
                    "members": ["usr-01", "usr-02"]
                },
                "team-02": {
                    "id": "team-02",
                    "name": "Đội Kinh Doanh TP.HCM (Team B)",
                    "lead_id": "usr-03",  # hoặc lead khác
                    "lead_name": "Lê Hoàng Nam",
                    "members": ["usr-05"]
                }
            }

            self.leads = {}
            self.notifications = []
            self.audit_logs = []
            now = get_current_time()

            # 1. Lead 101: Chờ tiếp nhận bởi Nguyễn Văn Tuấn (Mới phân bổ, hạn SLA 120s)
            self._seed_lead({
                "id": "LEAD-101",
                "name": "Ông Hoàng Minh Đức",
                "company": "Tập đoàn Bất Động Sản An Gia",
                "phone": "0918 882 123",
                "email": "duc.hoang@angia.vn",
                "industry": "Bất động sản",
                "region": "Miền Bắc",
                "estimated_value": "450.000.000 đ",
                "status": STATUS_ASSIGNED,
                "assigned_to_id": "usr-01",
                "assigned_to_name": "Nguyễn Văn Tuấn",
                "team_id": "team-01",
                "assigned_at": now - timedelta(seconds=20),
                "accepted_at": None,
                "sla_seconds": 120,
                "sla_deadline": now + timedelta(seconds=100),
                "contacted_at": None,
                "contact_channel": None,
                "contact_notes": None,
                "is_flagged": False,
                "flagged_at": None,
                "flag_reason": None,
                "rejection_reason": None,
                "rejection_history": [],
                "created_at": now - timedelta(minutes=5)
            })

            # 2. Lead 102: Nguyễn Văn Tuấn ĐÃ NHẬN -> Đang chăm sóc (IN_CARE), còn 75s SLA
            self._seed_lead({
                "id": "LEAD-102",
                "name": "Bà Đỗ Thu Hương",
                "company": "Công ty Tài Chính VinaFin",
                "phone": "0972 345 999",
                "email": "huong.do@vinafin.com",
                "industry": "Tài chính - Ngân hàng",
                "region": "Miền Bắc",
                "estimated_value": "820.000.000 đ",
                "status": STATUS_IN_CARE,
                "assigned_to_id": "usr-01",
                "assigned_to_name": "Nguyễn Văn Tuấn",
                "team_id": "team-01",
                "assigned_at": now - timedelta(seconds=45),
                "accepted_at": now - timedelta(seconds=30),
                "sla_seconds": 120,
                "sla_deadline": now + timedelta(seconds=75),
                "contacted_at": None,
                "contact_channel": None,
                "contact_notes": None,
                "is_flagged": False,
                "flagged_at": None,
                "flag_reason": None,
                "rejection_reason": None,
                "rejection_history": [],
                "created_at": now - timedelta(minutes=10)
            })

            # 3. Lead 103: Bị từ chối bởi Nguyễn Văn Tuấn -> Quay lại "Hàng chờ phân bổ" kèm lý do
            self._seed_lead({
                "id": "LEAD-103",
                "name": "Ông Vũ Thanh Tùng",
                "company": "Chuỗi Bán Lẻ TechStore",
                "phone": "0934 567 890",
                "email": "tung.vu@techstore.vn",
                "industry": "Bán lẻ & TMĐT",
                "region": "Miền Bắc",
                "estimated_value": "210.000.000 đ",
                "status": STATUS_PENDING_ALLOCATION,
                "assigned_to_id": None,
                "assigned_to_name": None,
                "team_id": "team-01",
                "assigned_at": None,
                "accepted_at": None,
                "sla_seconds": 120,
                "sla_deadline": None,
                "contacted_at": None,
                "contact_channel": None,
                "contact_notes": None,
                "is_flagged": False,
                "flagged_at": None,
                "flag_reason": None,
                "rejection_reason": "Khách hàng thuộc mảng bán lẻ ngoài nhóm sản phẩm phụ trách chính",
                "rejection_history": [
                    {
                        "rejected_by_id": "usr-01",
                        "rejected_by_name": "Nguyễn Văn Tuấn",
                        "rejected_at": format_datetime(now - timedelta(minutes=15)),
                        "reason": "Khách hàng thuộc mảng bán lẻ ngoài nhóm sản phẩm phụ trách chính"
                    }
                ],
                "created_at": now - timedelta(minutes=30)
            })

            # 4. Lead 104: QUÁ SLA PHẢN HỒI MÀ CHƯA LIÊN HỆ -> ĐÃ BỊ GẮN CỜ 🚩 VÀ BÁO TRƯỞNG NHÓM
            lead104_assigned_at = now - timedelta(minutes=10)
            lead104_deadline = lead104_assigned_at + timedelta(seconds=60)
            self._seed_lead({
                "id": "LEAD-104",
                "name": "Bà Phan Kiều Trang",
                "company": "Công ty Cổ phần Dược Phẩm BioMed",
                "phone": "0988 123 777",
                "email": "trang.phan@biomed.com.vn",
                "industry": "Y tế & Dược phẩm",
                "region": "Miền Bắc",
                "estimated_value": "650.000.000 đ",
                "status": STATUS_IN_CARE,
                "assigned_to_id": "usr-02",
                "assigned_to_name": "Trần Thị Mai",
                "team_id": "team-01",
                "assigned_at": lead104_assigned_at,
                "accepted_at": lead104_assigned_at + timedelta(seconds=15),
                "sla_seconds": 60,
                "sla_deadline": lead104_deadline,
                "contacted_at": None,
                "contact_channel": None,
                "contact_notes": None,
                "is_flagged": True,
                "flagged_at": lead104_deadline,
                "flag_reason": "Quá hạn SLA phản hồi (60s) mà nhân viên chưa liên hệ khách hàng! Lead có nguy cơ nguội lạnh.",
                "rejection_reason": None,
                "rejection_history": [],
                "created_at": now - timedelta(minutes=25)
            })

            # Tạo thông báo báo động gửi cho Trưởng nhóm Lê Hoàng Nam về Lead 104
            self.create_notification(
                lead_id="LEAD-104",
                lead_name="Bà Phan Kiều Trang (BioMed)",
                recipient_id="usr-03",  # Trưởng nhóm Lê Hoàng Nam
                sales_rep_name="Trần Thị Mai",
                title="🚩 CẢNH BÁO QUÁ HẠN SLA PHẢN HỒI",
                message="Lead LEAD-104 (Bà Phan Kiều Trang - BioMed) phân bổ cho Trần Thị Mai đã quá thời hạn SLA phản hồi mà chưa liên hệ khách hàng! Lead đã bị hệ thống gắn cờ cảnh báo.",
                level="URGENT",
                created_at=lead104_deadline
            )

            # 5. Lead 105: ĐÃ LIÊN HỆ THÀNH CÔNG TRƯỚC HẠN SLA (Hoàn thành SLA)
            lead105_assigned_at = now - timedelta(minutes=40)
            self._seed_lead({
                "id": "LEAD-105",
                "name": "Ông Nguyễn Quang Dũng",
                "company": "Tập Đoàn Công Nghệ SunCloud",
                "phone": "0904 987 654",
                "email": "dung.nq@suncloud.io",
                "industry": "Công nghệ thông tin",
                "region": "Miền Bắc",
                "estimated_value": "1.200.000.000 đ",
                "status": STATUS_CONTACTED,
                "assigned_to_id": "usr-01",
                "assigned_to_name": "Nguyễn Văn Tuấn",
                "team_id": "team-01",
                "assigned_at": lead105_assigned_at,
                "accepted_at": lead105_assigned_at + timedelta(seconds=25),
                "sla_seconds": 120,
                "sla_deadline": lead105_assigned_at + timedelta(seconds=120),
                "contacted_at": lead105_assigned_at + timedelta(seconds=60),
                "contact_channel": "Điện thoại tư vấn trực tiếp",
                "contact_notes": "Đã trao đổi với anh Dũng qua điện thoại, khách hàng rất quan tâm gói giải pháp Doanh nghiệp Enterprise. Hẹn demo thứ Hai tuần tới.",
                "is_flagged": False,
                "flagged_at": None,
                "flag_reason": None,
                "rejection_reason": None,
                "rejection_history": [],
                "created_at": now - timedelta(hours=1)
            })

            # Thêm log khởi động
            self.add_audit_log(
                event_type="SYSTEM_INIT",
                lead_id="SYSTEM",
                user_id="SYSTEM",
                user_name="Hệ thống",
                details="Khởi tạo cơ sở dữ liệu mẫu thành công cho ticket SCRUM-51."
            )

    def _seed_lead(self, lead_dict):
        self.leads[lead_dict["id"]] = lead_dict

    # ==========================================
    # CÁC PHƯƠNG THỨC XỬ LÝ LEAD (CRITICAL BUSINESS LOGIC)
    # ==========================================

    def get_lead(self, lead_id):
        """Lấy thông tin chi tiết một lead"""
        with self.lock:
            lead = self.leads.get(lead_id)
            if not lead:
                return None
            return copy.deepcopy(lead)

    def get_leads(self, filter_status=None, assigned_to_id=None, is_flagged=None, search=None):
        """Lấy danh sách lead theo nhiều tiêu chí lọc"""
        with self.lock:
            result = list(self.leads.values())

            if filter_status:
                result = [l for l in result if l["status"] == filter_status]

            if assigned_to_id:
                result = [l for l in result if l["assigned_to_id"] == assigned_to_id]

            if is_flagged is not None:
                result = [l for l in result if l.get("is_flagged") == is_flagged]

            if search:
                s = search.lower()
                result = [
                    l for l in result
                    if s in l["name"].lower()
                    or s in l["company"].lower()
                    or s in l["phone"].lower()
                    or s in l["id"].lower()
                    or (l.get("assigned_to_name") and s in l["assigned_to_name"].lower())
                ]

            # Sắp xếp mới nhất lên đầu
            result.sort(key=lambda x: x.get("created_at") or datetime.min, reverse=True)
            return copy.deepcopy(result)

    def create_lead(self, name, company, phone, email, industry="Công nghệ thông tin",
                    region="Miền Bắc", estimated_value="100.000.000 đ",
                    assigned_to_id=None, sla_seconds=DEFAULT_SLA_SECONDS):
        """Tạo lead mới đưa vào hệ thống"""
        with self.lock:
            self._lead_counter += 1
            lead_id = f"LEAD-{self._lead_counter}"
            now = get_current_time()

            assigned_to_name = None
            team_id = "team-01"
            status = STATUS_PENDING_ALLOCATION
            assigned_at = None
            sla_deadline = None

            if assigned_to_id and assigned_to_id in self.users:
                user = self.users[assigned_to_id]
                assigned_to_name = user["name"]
                team_id = user["team_id"]
                status = STATUS_ASSIGNED
                assigned_at = now
                sla_deadline = now + timedelta(seconds=sla_seconds)

            new_lead = {
                "id": lead_id,
                "name": name.strip(),
                "company": company.strip(),
                "phone": phone.strip(),
                "email": email.strip(),
                "industry": industry,
                "region": region,
                "estimated_value": estimated_value,
                "status": status,
                "assigned_to_id": assigned_to_id,
                "assigned_to_name": assigned_to_name,
                "team_id": team_id,
                "assigned_at": assigned_at,
                "accepted_at": None,
                "sla_seconds": sla_seconds,
                "sla_deadline": sla_deadline,
                "contacted_at": None,
                "contact_channel": None,
                "contact_notes": None,
                "is_flagged": False,
                "flagged_at": None,
                "flag_reason": None,
                "rejection_reason": None,
                "rejection_history": [],
                "created_at": now
            }

            self.leads[lead_id] = new_lead

            self.add_audit_log(
                event_type="LEAD_CREATED",
                lead_id=lead_id,
                user_id=assigned_to_id or "SYSTEM",
                user_name=assigned_to_name or "Hệ thống",
                details=f"Tạo lead mới {name} ({company}). Trạng thái: {status}"
            )
            return copy.deepcopy(new_lead)

    # -------------------------------------------------------------
    # TIÊU CHÍ 1: Nhân viên nhận lead thì lead chuyển sang "Đang chăm sóc"
    # -------------------------------------------------------------
    def accept_lead(self, lead_id, user_id):
        """
        Nhân viên kinh doanh nhận lead được phân.
        Yêu cầu: Lead chuyển sang trạng thái "Đang chăm sóc" (IN_CARE).
        """
        with self.lock:
            lead = self.leads.get(lead_id)
            if not lead:
                raise ValueError(f"Không tìm thấy lead có mã '{lead_id}'.")

            user = self.users.get(user_id)
            if not user:
                raise ValueError(f"Không tìm thấy người dùng có mã '{user_id}'.")

            # Kiểm tra quyền: lead phải được phân cho nhân viên này hoặc trạng thái ASSIGNED
            if lead["assigned_to_id"] != user_id and user["role"] == ROLE_SALES_REP:
                raise PermissionError(f"Bạn không được phân bổ phụ trách lead {lead_id}.")

            if lead["status"] == STATUS_IN_CARE:
                return copy.deepcopy(lead)  # Đã nhận rồi

            now = get_current_time()
            lead["status"] = STATUS_IN_CARE
            lead["accepted_at"] = now
            # Đảm bảo người nhận là user này
            lead["assigned_to_id"] = user_id
            lead["assigned_to_name"] = user["name"]

            # Nếu chưa có SLA deadline, khởi tạo
            if not lead.get("sla_deadline"):
                sla_sec = lead.get("sla_seconds") or DEFAULT_SLA_SECONDS
                lead["sla_deadline"] = (lead.get("assigned_at") or now) + timedelta(seconds=sla_sec)

            self.add_audit_log(
                event_type="LEAD_ACCEPTED",
                lead_id=lead_id,
                user_id=user_id,
                user_name=user["name"],
                details=f"Nhân viên {user['name']} đã bấm NHẬN LEAD. Trạng thái chuyển sang 'Đang chăm sóc'."
            )
            return copy.deepcopy(lead)

    # -------------------------------------------------------------
    # TIÊU CHÍ 2: Từ chối bắt buộc nhập lý do, lead quay lại hàng chờ phân bổ
    # -------------------------------------------------------------
    def reject_lead(self, lead_id, user_id, reason):
        """
        Nhân viên từ chối lead được phân.
        Yêu cầu:
        - Bắt buộc nhập lý do (nếu rỗng hoặc toàn khoảng trắng -> bắn lỗi).
        - Lead chuyển sang trạng thái "Hàng chờ phân bổ" (PENDING_ALLOCATION).
        - Gỡ nhân viên phụ trách, lưu vào lịch sử từ chối để Trưởng nhóm nắm bắt.
        """
        with self.lock:
            lead = self.leads.get(lead_id)
            if not lead:
                raise ValueError(f"Không tìm thấy lead có mã '{lead_id}'.")

            user = self.users.get(user_id)
            if not user:
                raise ValueError(f"Không tìm thấy người dùng có mã '{user_id}'.")

            # RÀNG BUỘC CỐT LÕI CỦA ĐỀ BÀI: BẮT BUỘC NHẬP LÝ DO
            if not reason or not reason.strip():
                raise ValueError("Từ chối lead BẮT BUỘC phải nhập lý do cụ thể!")

            clean_reason = reason.strip()
            now = get_current_time()

            # Ghi nhận lịch sử từ chối
            rejection_entry = {
                "rejected_by_id": user_id,
                "rejected_by_name": user["name"],
                "rejected_at": format_datetime(now),
                "reason": clean_reason
            }
            lead["rejection_history"].append(rejection_entry)
            lead["rejection_reason"] = clean_reason

            # Chuyển trạng thái sang Hàng chờ phân bổ
            prev_status = lead["status"]
            lead["status"] = STATUS_PENDING_ALLOCATION
            lead["assigned_to_id"] = None
            lead["assigned_to_name"] = None
            lead["accepted_at"] = None
            lead["sla_deadline"] = None  # Tạm dừng tính SLA phản hồi khi ở hàng chờ

            # Tạo thông báo gửi Trưởng nhóm của nhân viên từ chối
            team = self.teams.get(user.get("team_id", "team-01"))
            team_lead_id = team["lead_id"] if team else "usr-03"

            self.create_notification(
                lead_id=lead_id,
                lead_name=f"{lead['name']} ({lead['company']})",
                recipient_id=team_lead_id,
                sales_rep_name=user["name"],
                title="⚠️ LEAD BỊ TỪ CHỐI - CẦN PHÂN BỔ LẠI",
                message=f"Nhân viên {user['name']} đã từ chối nhận lead {lead_id} ({lead['name']}). Lý do: '{clean_reason}'. Lead đã quay lại Hàng chờ phân bổ.",
                level="WARNING",
                created_at=now
            )

            self.add_audit_log(
                event_type="LEAD_REJECTED",
                lead_id=lead_id,
                user_id=user_id,
                user_name=user["name"],
                details=f"Nhân viên {user['name']} đã TỪ CHỐI lead. Lý do: '{clean_reason}'. Trạng thái quay lại '{STATUS_PENDING_ALLOCATION}' (Hàng chờ phân bổ)."
            )
            return copy.deepcopy(lead)

    # -------------------------------------------------------------
    # PHẢN HỒI LEAD / LIÊN HỆ KHÁCH HÀNG (Hoàn tất cam kết SLA)
    # -------------------------------------------------------------
    def log_contact(self, lead_id, user_id, channel, notes):
        """
        Nhân viên thực hiện liên hệ phản hồi khách hàng.
        Khi đã liên hệ -> Đạt cam kết SLA phản hồi, lead chuyển sang CONTACTED.
        """
        with self.lock:
            lead = self.leads.get(lead_id)
            if not lead:
                raise ValueError(f"Không tìm thấy lead có mã '{lead_id}'.")

            user = self.users.get(user_id)
            if not user:
                raise ValueError(f"Không tìm thấy người dùng có mã '{user_id}'.")

            if not notes or not notes.strip():
                raise ValueError("Vui lòng nhập ghi chú nội dung đã trao đổi với khách hàng.")

            now = get_current_time()
            lead["contacted_at"] = now
            lead["contact_channel"] = channel or "Điện thoại"
            lead["contact_notes"] = notes.strip()
            lead["status"] = STATUS_CONTACTED

            self.add_audit_log(
                event_type="LEAD_CONTACTED",
                lead_id=lead_id,
                user_id=user_id,
                user_name=user["name"],
                details=f"Đã liên hệ khách hàng qua '{lead['contact_channel']}'. Ghi chú: {lead['contact_notes'][:50]}... Đạt cam kết phản hồi!"
            )
            return copy.deepcopy(lead)

    # -------------------------------------------------------------
    # TIÊU CHÍ 3: Quá SLA phản hồi mà chưa liên hệ thì gắn cờ và báo cho trưởng nhóm
    # -------------------------------------------------------------
    def check_and_flag_sla_breaches(self, reference_time=None):
        """
        Bộ máy tự động quét kiểm tra vi phạm SLA phản hồi:
        Điều kiện vi phạm:
        - Lead đang được phân bổ (ASSIGNED) hoặc đang chăm sóc (IN_CARE).
        - Chưa liên hệ khách hàng (contacted_at is None).
        - Thời gian hiện tại đã vượt quá hạn chót SLA (now >= sla_deadline).
        - Lead chưa bị gắn cờ trước đó (is_flagged == False).

        Hành động khi vi phạm:
        - Lead được gắn cờ cảnh báo (is_flagged = True, flagged_at = now).
        - Bắn thông báo cảnh báo khẩn cấp (URGENT) gửi tới Trưởng nhóm.
        """
        with self.lock:
            now = reference_time or get_current_time()
            flagged_leads = []

            for lead_id, lead in self.leads.items():
                # Điều kiện kiểm tra
                if lead["status"] in [STATUS_ASSIGNED, STATUS_IN_CARE]:
                    if lead.get("contacted_at") is None and lead.get("sla_deadline"):
                        if now >= lead["sla_deadline"] and not lead.get("is_flagged"):
                            # VI PHẠM SLA PHẢN HỒI!
                            lead["is_flagged"] = True
                            lead["flagged_at"] = now

                            elapsed = int((now - lead["assigned_at"]).total_seconds()) if lead.get("assigned_at") else lead["sla_seconds"]
                            reason_msg = (
                                f"Quá SLA phản hồi ({lead['sla_seconds']}s, đã trôi qua {elapsed}s) "
                                f"mà nhân viên chưa liên hệ khách hàng! Lead có nguy cơ nguội lạnh."
                            )
                            lead["flag_reason"] = reason_msg

                            # Tìm Trưởng nhóm phụ trách
                            team_id = lead.get("team_id", "team-01")
                            team = self.teams.get(team_id)
                            team_lead_id = team["lead_id"] if team else "usr-03"
                            team_lead_name = team["lead_name"] if team else "Lê Hoàng Nam"

                            rep_name = lead.get("assigned_to_name") or "Chưa rõ"

                            # BÁO CHO TRƯỞNG NHÓM (Notification)
                            self.create_notification(
                                lead_id=lead_id,
                                lead_name=f"{lead['name']} ({lead['company']})",
                                recipient_id=team_lead_id,
                                sales_rep_name=rep_name,
                                title="🚩 CẢNH BÁO QUÁ HẠN SLA PHẢN HỒI",
                                message=(
                                    f"Lead {lead_id} ({lead['name']} - {lead['company']}) "
                                    f"phân cho nhân viên {rep_name} đã quá hạn SLA phản hồi mà chưa liên hệ! "
                                    f"Hệ thống đã gắn cờ cảnh báo, đề nghị Trưởng nhóm kiểm tra đôn đốc hoặc điều chuyển."
                                ),
                                level="URGENT",
                                created_at=now
                            )

                            self.add_audit_log(
                                event_type="SLA_BREACH_FLAGGED",
                                lead_id=lead_id,
                                user_id="SLA_MONITOR",
                                user_name="Bộ Giám Sát SLA",
                                details=f"🚩 GẮN CỜ VI PHẠM: Lead {lead_id} quá hạn SLA phản hồi ({elapsed}s). Đã gửi cảnh báo khẩn cấp tới Trưởng nhóm {team_lead_name}."
                            )

                            flagged_leads.append(copy.deepcopy(lead))

            return flagged_leads

    # -------------------------------------------------------------
    # HÀNH ĐỘNG CỦA TRƯỞNG NHÓM: Phân bổ lại từ hàng chờ hoặc gán lại lead
    # -------------------------------------------------------------
    def reassign_lead(self, lead_id, target_user_id, team_lead_id, sla_seconds=None):
        """
        Trưởng nhóm phân bổ lại lead (từ Hàng chờ phân bổ hoặc thu hồi lead bị gắn cờ quá hạn).
        """
        with self.lock:
            lead = self.leads.get(lead_id)
            if not lead:
                raise ValueError(f"Không tìm thấy lead có mã '{lead_id}'.")

            target_user = self.users.get(target_user_id)
            if not target_user:
                raise ValueError(f"Không tìm thấy nhân viên có mã '{target_user_id}'.")

            lead_user = self.users.get(team_lead_id)
            leader_name = lead_user["name"] if lead_user else "Trưởng nhóm"

            now = get_current_time()
            sla_sec = sla_seconds or lead.get("sla_seconds") or DEFAULT_SLA_SECONDS

            lead["status"] = STATUS_ASSIGNED
            lead["assigned_to_id"] = target_user_id
            lead["assigned_to_name"] = target_user["name"]
            lead["team_id"] = target_user["team_id"]
            lead["assigned_at"] = now
            lead["accepted_at"] = None
            lead["sla_seconds"] = sla_sec
            lead["sla_deadline"] = now + timedelta(seconds=sla_sec)
            # Giữ lịch sử gắn cờ nhưng reset cờ hoạt động để nhân viên mới xử lý
            lead["is_flagged"] = False
            lead["flag_reason"] = None

            self.add_audit_log(
                event_type="LEAD_REASSIGNED",
                lead_id=lead_id,
                user_id=team_lead_id,
                user_name=leader_name,
                details=f"Trưởng nhóm {leader_name} đã PHÂN BỔ LẠI lead cho {target_user['name']}. Thiết lập SLA mới: {sla_sec}s."
            )
            return copy.deepcopy(lead)

    # -------------------------------------------------------------
    # MÔ PHỎNG KIỂM THỬ: Tua nhanh thời gian SLA (Fast-Forward)
    # -------------------------------------------------------------
    def fast_forward_lead_sla(self, lead_id, forward_seconds=150):
        """
        Tua nhanh thời gian của một lead cụ thể để vượt quá hạn SLA nhằm kiểm tra tiêu chí 3 ngay lập tức.
        """
        with self.lock:
            lead = self.leads.get(lead_id)
            if not lead:
                raise ValueError(f"Không tìm thấy lead có mã '{lead_id}'.")

            # Đẩy assigned_at và deadline lùi về quá khứ
            if lead.get("assigned_at"):
                lead["assigned_at"] -= timedelta(seconds=forward_seconds)
            if lead.get("sla_deadline"):
                lead["sla_deadline"] -= timedelta(seconds=forward_seconds)
            else:
                now = get_current_time()
                lead["sla_deadline"] = now - timedelta(seconds=10)

            # Quét kiểm tra ngay
            self.check_and_flag_sla_breaches()
            return copy.deepcopy(self.leads[lead_id])

    # -------------------------------------------------------------
    # QUẢN LÝ THÔNG BÁO (NOTIFICATIONS)
    # -------------------------------------------------------------
    def create_notification(self, lead_id, lead_name, recipient_id, sales_rep_name, title, message, level="INFO", created_at=None):
        with self.lock:
            self._notif_counter += 1
            notif = {
                "id": f"NOTIF-{self._notif_counter}",
                "lead_id": lead_id,
                "lead_name": lead_name,
                "recipient_id": recipient_id,
                "sales_rep_name": sales_rep_name,
                "title": title,
                "message": message,
                "level": level,  # URGENT, WARNING, INFO
                "is_read": False,
                "created_at": created_at or get_current_time()
            }
            self.notifications.append(notif)
            return notif

    def get_notifications(self, recipient_id=None, unread_only=False):
        with self.lock:
            res = list(self.notifications)
            if recipient_id:
                res = [n for n in res if n["recipient_id"] == recipient_id]
            if unread_only:
                res = [n for n in res if not n["is_read"]]
            res.sort(key=lambda x: x["created_at"], reverse=True)
            return copy.deepcopy(res)

    def mark_notifications_as_read(self, recipient_id):
        with self.lock:
            for n in self.notifications:
                if n["recipient_id"] == recipient_id:
                    n["is_read"] = True

    # -------------------------------------------------------------
    # QUẢN LÝ NHẬT KÝ KIỂM TOÁN (AUDIT LOGS)
    # -------------------------------------------------------------
    def add_audit_log(self, event_type, lead_id, user_id, user_name, details):
        with self.lock:
            self._log_counter += 1
            log_item = {
                "id": f"LOG-{self._log_counter}",
                "event_type": event_type,
                "lead_id": lead_id,
                "user_id": user_id,
                "user_name": user_name,
                "details": details,
                "timestamp": get_current_time()
            }
            self.audit_logs.append(log_item)
            return log_item

    def get_audit_logs(self, limit=50):
        with self.lock:
            res = sorted(self.audit_logs, key=lambda x: x["timestamp"], reverse=True)
            return copy.deepcopy(res[:limit])

    # -------------------------------------------------------------
    # THỐNG KÊ DASHBOARD (METRICS)
    # -------------------------------------------------------------
    def get_metrics(self):
        with self.lock:
            all_leads = list(self.leads.values())
            total = len(all_leads)
            pending_alloc = sum(1 for l in all_leads if l["status"] == STATUS_PENDING_ALLOCATION)
            assigned = sum(1 for l in all_leads if l["status"] == STATUS_ASSIGNED)
            in_care = sum(1 for l in all_leads if l["status"] == STATUS_IN_CARE)
            contacted = sum(1 for l in all_leads if l["status"] == STATUS_CONTACTED)
            flagged = sum(1 for l in all_leads if l.get("is_flagged"))

            total_rejections = sum(len(l.get("rejection_history", [])) for l in all_leads)

            # Tính tỷ lệ đạt SLA
            # Leads cần phản hồi = in_care + contacted + assigned + flagged
            sla_rate = 100.0
            if (contacted + flagged) > 0:
                sla_rate = round((contacted / (contacted + flagged)) * 100, 1)

            return {
                "total_leads": total,
                "pending_allocation_count": pending_alloc,
                "assigned_count": assigned,
                "in_care_count": in_care,
                "contacted_count": contacted,
                "flagged_count": flagged,
                "total_rejections": total_rejections,
                "sla_rate": sla_rate
            }


# Khởi tạo singleton DB
db = Database()
