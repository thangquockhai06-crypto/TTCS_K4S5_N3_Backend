"""
Module Quản Lý Dữ Liệu & Bộ Nhớ Hệ Thống - Ticket SCRUM-30 / SCRUM-49
Lưu trữ và quản lý:
1. Nhóm kinh doanh (Teams) & Nhân viên (Sales Reps)
2. Cấu hình Quy tắc phân bổ (Rules) có thứ tự ưu tiên (Priority)
3. Danh sách Lead: Trạng thái (PENDING, ASSIGNED, MANUAL_QUEUE), SLA, thời gian xử lý
4. Nhật ký xử lý của Background Worker (Worker Logs)
Hỗ trợ đa luồng an toàn (Thread-safe) bằng RLock cho Background Worker và Flask Web Server.
"""

import threading
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Any
from config import (
    REGIONS,
    INDUSTRIES,
    LEAD_SOURCES,
    LEAD_STATUS_PENDING,
    LEAD_STATUS_ASSIGNED,
    LEAD_STATUS_MANUAL_QUEUE,
    ASSIGNMENT_TYPE_ROUND_ROBIN,
    ASSIGNMENT_TYPE_DIRECT,
    SLA_LIMIT_SECONDS
)

# Timezone Việt Nam (UTC+7)
VN_TZ = timezone(timedelta(hours=7))

def get_current_time() -> datetime:
    return datetime.now(VN_TZ)

def format_datetime(dt: Optional[datetime]) -> str:
    if not dt:
        return ""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


class Database:
    def __init__(self):
        self.lock = threading.RLock()
        self.teams: Dict[str, Dict[str, Any]] = {}
        self.users: Dict[str, Dict[str, Any]] = {}
        self.rules: List[Dict[str, Any]] = []
        self.leads: List[Dict[str, Any]] = []
        self.worker_logs: List[Dict[str, Any]] = []
        self.lead_seq = 1000

        # Khởi tạo dữ liệu mẫu phong phú
        self._seed_data()

    def _seed_data(self):
        with self.lock:
            # 1. Khởi tạo danh sách nhân sự (Users / Sales Reps)
            users_data = [
                # Giám đốc & Trưởng nhóm
                {
                    "id": "usr-01",
                    "name": "Hoàng Minh Trí",
                    "role": "DIRECTOR",
                    "role_name": "Giám đốc kinh doanh",
                    "email": "tri.hoang@crm-auto.vn",
                    "phone": "0908 123 456",
                    "team_id": None,
                    "status": "ACTIVE",
                    "assigned_count": 0,
                    "avatar": "HT"
                },
                {
                    "id": "usr-02",
                    "name": "Trần Văn Hùng",
                    "role": "TEAM_LEAD",
                    "role_name": "Trưởng nhóm Miền Bắc",
                    "email": "hung.tran@crm-auto.vn",
                    "phone": "0912 345 678",
                    "team_id": "team-bac",
                    "status": "ACTIVE",
                    "assigned_count": 4,
                    "avatar": "TH"
                },
                {
                    "id": "usr-03",
                    "name": "Nguyễn Thị Bích",
                    "role": "TEAM_LEAD",
                    "role_name": "Trưởng nhóm Miền Nam",
                    "email": "bich.nguyen@crm-auto.vn",
                    "phone": "0933 456 789",
                    "team_id": "team-nam",
                    "status": "ACTIVE",
                    "assigned_count": 5,
                    "avatar": "NB"
                },
                {
                    "id": "usr-04",
                    "name": "Bùi Thanh Tùng",
                    "role": "TEAM_LEAD",
                    "role_name": "Trưởng nhóm Bất Động Sản",
                    "email": "tung.bui@crm-auto.vn",
                    "phone": "0977 888 999",
                    "team_id": "team-bds",
                    "status": "ACTIVE",
                    "assigned_count": 3,
                    "avatar": "BT"
                },

                # Team Miền Bắc
                {
                    "id": "usr-05",
                    "name": "Nguyễn Anh Tuấn",
                    "role": "SALES_EXECUTIVE",
                    "role_name": "Chuyên viên Khách hàng Doanh nghiệp",
                    "email": "tuan.nguyen@crm-auto.vn",
                    "phone": "0981 112 233",
                    "team_id": "team-bac",
                    "status": "ACTIVE",
                    "assigned_count": 12,
                    "avatar": "NT"
                },
                {
                    "id": "usr-06",
                    "name": "Lê Thị Mai",
                    "role": "SALES_EXECUTIVE",
                    "role_name": "Chuyên viên Tài chính - Ngân hàng",
                    "email": "mai.le@crm-auto.vn",
                    "phone": "0982 223 344",
                    "team_id": "team-bac",
                    "status": "ACTIVE",
                    "assigned_count": 11,
                    "avatar": "LM"
                },
                {
                    "id": "usr-07",
                    "name": "Phạm Hoàng Nam",
                    "role": "SALES_EXECUTIVE",
                    "role_name": "Chuyên viên Công nghệ cao",
                    "email": "nam.pham@crm-auto.vn",
                    "phone": "0983 334 455",
                    "team_id": "team-bac",
                    "status": "ACTIVE",
                    "assigned_count": 11,
                    "avatar": "PN"
                },

                # Team Miền Nam
                {
                    "id": "usr-08",
                    "name": "Đặng Quốc Bảo",
                    "role": "SALES_EXECUTIVE",
                    "role_name": "Chuyên viên Bán lẻ & Fintech",
                    "email": "bao.dang@crm-auto.vn",
                    "phone": "0903 556 677",
                    "team_id": "team-nam",
                    "status": "ACTIVE",
                    "assigned_count": 9,
                    "avatar": "DB"
                },
                {
                    "id": "usr-09",
                    "name": "Vũ Thu Trang",
                    "role": "SALES_EXECUTIVE",
                    "role_name": "Chuyên viên E-commerce & SMB",
                    "email": "trang.vu@crm-auto.vn",
                    "phone": "0904 667 788",
                    "team_id": "team-nam",
                    "status": "ACTIVE",
                    "assigned_count": 9,
                    "avatar": "VT"
                },
                {
                    "id": "usr-10",
                    "name": "Lý Gia Hưng",
                    "role": "SALES_EXECUTIVE",
                    "role_name": "Chuyên viên Sản xuất & Logistics",
                    "email": "hung.ly@crm-auto.vn",
                    "phone": "0905 778 899",
                    "team_id": "team-nam",
                    "status": "ACTIVE",
                    "assigned_count": 8,
                    "avatar": "LH"
                },

                # Team Bất Động Sản Toàn Quốc
                {
                    "id": "usr-11",
                    "name": "Đỗ Mỹ Linh",
                    "role": "SALES_EXECUTIVE",
                    "role_name": "Chuyên viên BĐS Cao cấp",
                    "email": "linh.do@crm-auto.vn",
                    "phone": "0915 889 900",
                    "team_id": "team-bds",
                    "status": "ACTIVE",
                    "assigned_count": 14,
                    "avatar": "ML"
                },
                {
                    "id": "usr-12",
                    "name": "Phan Văn Đạt",
                    "role": "SALES_EXECUTIVE",
                    "role_name": "Chuyên viên BĐS Công nghiệp",
                    "email": "dat.phan@crm-auto.vn",
                    "phone": "0916 990 011",
                    "team_id": "team-bds",
                    "status": "ACTIVE",
                    "assigned_count": 13,
                    "avatar": "PD"
                },
                {
                    "id": "usr-13",
                    "name": "Trịnh Thu Hà",
                    "role": "SALES_EXECUTIVE",
                    "role_name": "Chuyên viên BĐS Dự án",
                    "email": "ha.trinh@crm-auto.vn",
                    "phone": "0917 001 122",
                    "team_id": "team-bds",
                    "status": "ACTIVE",
                    "assigned_count": 13,
                    "avatar": "TH"
                }
            ]

            for u in users_data:
                self.users[u["id"]] = u

            # 2. Khởi tạo Nhóm kinh doanh (Teams)
            teams_data = [
                {
                    "id": "team-bac",
                    "name": "Nhóm Kinh Doanh Miền Bắc (Enterprise)",
                    "leader_id": "usr-02",
                    "members": ["usr-05", "usr-06", "usr-07"],
                    "rr_index": 0,  # Con trỏ xoay vòng Round-Robin ban đầu
                    "description": "Phụ trách các khách hàng doanh nghiệp, tài chính ngân hàng tại Hà Nội và phía Bắc"
                },
                {
                    "id": "team-nam",
                    "name": "Nhóm Kinh Doanh Miền Nam (Retail & SMB)",
                    "leader_id": "usr-03",
                    "members": ["usr-08", "usr-09", "usr-10"],
                    "rr_index": 0,
                    "description": "Phụ trách khách hàng thương mại điện tử, bán lẻ và sản xuất tại TP.HCM và Nam Bộ"
                },
                {
                    "id": "team-bds",
                    "name": "Nhóm Chuyên Sâu Bất Động Sản Toàn Quốc",
                    "leader_id": "usr-04",
                    "members": ["usr-11", "usr-12", "usr-13"],
                    "rr_index": 0,
                    "description": "Chuyên môn hóa thị trường bất động sản nghỉ dưỡng, dự án và công nghiệp trên cả nước"
                }
            ]

            for t in teams_data:
                self.teams[t["id"]] = t

            # 3. Khởi tạo Quy tắc phân bổ tự động (Rules) với thứ tự ưu tiên rõ ràng
            # TIÊU CHÍ: Phân bổ theo khu vực, theo ngành nghề, hoặc xoay vòng đều trong nhóm
            # TIÊU CHÍ: Nhiều quy tắc xếp theo thứ tự ưu tiên, quy tắc đầu tiên khớp sẽ thắng (First-Match-Wins)
            rules_data = [
                {
                    "id": "rule-01",
                    "name": "Quy tắc 1: Khách VIP Tài chính - Ngân hàng Miền Bắc",
                    "priority": 1,
                    "is_active": True,
                    "region": "Miền Bắc",
                    "industry": "Tài chính - Ngân hàng",
                    "assignment_type": ASSIGNMENT_TYPE_ROUND_ROBIN,
                    "target_team_id": "team-bac",
                    "target_user_id": None,
                    "description": "Khách hàng tài chính, ngân hàng phía Bắc -> Xoay vòng đều cho Team Miền Bắc",
                    "matches_count": 8,
                    "created_at": "2026-10-01 08:00:00"
                },
                {
                    "id": "rule-02",
                    "name": "Quy tắc 2: Khách ngành Bất động sản Toàn quốc",
                    "priority": 2,
                    "is_active": True,
                    "region": "Toàn quốc",
                    "industry": "Bất động sản",
                    "assignment_type": ASSIGNMENT_TYPE_ROUND_ROBIN,
                    "target_team_id": "team-bds",
                    "target_user_id": None,
                    "description": "Tất cả lead thuộc ngành Bất động sản -> Xoay vòng đều cho Nhóm Chuyên Sâu BĐS",
                    "matches_count": 15,
                    "created_at": "2026-10-01 08:30:00"
                },
                {
                    "id": "rule-03",
                    "name": "Quy tắc 3: Khách Bán lẻ & E-commerce Miền Nam",
                    "priority": 3,
                    "is_active": True,
                    "region": "Miền Nam",
                    "industry": "Bán lẻ & Thương mại điện tử",
                    "assignment_type": ASSIGNMENT_TYPE_ROUND_ROBIN,
                    "target_team_id": "team-nam",
                    "target_user_id": None,
                    "description": "Khách hàng bán lẻ, thương mại điện tử phía Nam -> Xoay vòng đều cho Team Miền Nam",
                    "matches_count": 10,
                    "created_at": "2026-10-01 09:00:00"
                },
                {
                    "id": "rule-04",
                    "name": "Quy tắc 4: Dự án Công nghệ thông tin cao cấp",
                    "priority": 4,
                    "is_active": True,
                    "region": "Toàn quốc",
                    "industry": "Công nghệ thông tin",
                    "assignment_type": ASSIGNMENT_TYPE_DIRECT,
                    "target_team_id": None,
                    "target_user_id": "usr-07",  # Phạm Hoàng Nam - Chuyên gia Công nghệ
                    "description": "Mọi lead thuộc ngành Công nghệ thông tin -> Gán trực tiếp cho Chuyên viên Phạm Hoàng Nam",
                    "matches_count": 6,
                    "created_at": "2026-10-01 09:30:00"
                },
                {
                    "id": "rule-05",
                    "name": "Quy tắc 5: Lead Sản xuất & Chế biến Miền Nam",
                    "priority": 5,
                    "is_active": True,
                    "region": "Miền Nam",
                    "industry": "Sản xuất & Chế biến",
                    "assignment_type": ASSIGNMENT_TYPE_ROUND_ROBIN,
                    "target_team_id": "team-nam",
                    "target_user_id": None,
                    "description": "Nhà máy, xưởng chế biến khu công nghiệp phía Nam -> Xoay vòng Team Miền Nam",
                    "matches_count": 5,
                    "created_at": "2026-10-01 10:00:00"
                }
            ]
            self.rules = rules_data

            # 4. Khởi tạo Leads mẫu
            # Gồm: Lead đã phân bổ tự động, Lead trong Hàng chờ phân tay, và sẵn sàng nạp mới
            now = get_current_time()
            base_time = now - timedelta(minutes=45)

            seed_leads = [
                {
                    "id": "lead-1001",
                    "code": "LD-1001",
                    "name": "Công ty CP Chứng khoán Thăng Long",
                    "contact_person": "Ông Lê Minh Trí",
                    "phone": "0988 123 456",
                    "email": "contact@thanglongsec.com.vn",
                    "region": "Miền Bắc",
                    "city": "Hà Nội",
                    "industry": "Tài chính - Ngân hàng",
                    "estimated_value": 350000000,
                    "source": "Website Form",
                    "status": LEAD_STATUS_ASSIGNED,
                    "assigned_to_user_id": "usr-05",  # Nguyễn Anh Tuấn
                    "assigned_team_id": "team-bac",
                    "matched_rule_id": "rule-01",
                    "matched_rule_name": "Quy tắc 1: Khách VIP Tài chính - Ngân hàng Miền Bắc",
                    "created_at": format_datetime(base_time),
                    "processed_at": format_datetime(base_time + timedelta(seconds=2)),
                    "elapsed_seconds": 2.1,
                    "sla_status": "MET",
                    "unmatched_reason": None,
                    "notes": "Phân bổ tự động qua Quy tắc #1. Xoay vòng Round-Robin hoàn tất trong 2.1s."
                },
                {
                    "id": "lead-1002",
                    "code": "LD-1002",
                    "name": "Tập đoàn Địa Ốc Sài Gòn Star",
                    "contact_person": "Bà Đặng Phương Thảo",
                    "phone": "0912 888 777",
                    "email": "thao.dp@saigonstarland.vn",
                    "region": "Miền Nam",
                    "city": "TP. Hồ Chí Minh",
                    "industry": "Bất động sản",
                    "estimated_value": 850000000,
                    "source": "Facebook Ads",
                    "status": LEAD_STATUS_ASSIGNED,
                    "assigned_to_user_id": "usr-11",  # Đỗ Mỹ Linh
                    "assigned_team_id": "team-bds",
                    "matched_rule_id": "rule-02",
                    "matched_rule_name": "Quy tắc 2: Khách ngành Bất động sản Toàn quốc",
                    "created_at": format_datetime(base_time + timedelta(minutes=5)),
                    "processed_at": format_datetime(base_time + timedelta(minutes=5, seconds=1)),
                    "elapsed_seconds": 1.4,
                    "sla_status": "MET",
                    "unmatched_reason": None,
                    "notes": "Phân bổ tự động qua Quy tắc #2. Xoay vòng Team BĐS hoàn tất trong 1.4s."
                },
                {
                    "id": "lead-1003",
                    "code": "LD-1003",
                    "name": "Chuỗi Cửa Hàng Bách Hóa Xanh Star",
                    "contact_person": "Ông Trần Hữu Phước",
                    "phone": "0909 333 444",
                    "email": "phuoc.th@xanhstar.vn",
                    "region": "Miền Nam",
                    "city": "Bình Dương",
                    "industry": "Bán lẻ & Thương mại điện tử",
                    "estimated_value": 220000000,
                    "source": "Hotline tư vấn",
                    "status": LEAD_STATUS_ASSIGNED,
                    "assigned_to_user_id": "usr-08",  # Đặng Quốc Bảo
                    "assigned_team_id": "team-nam",
                    "matched_rule_id": "rule-03",
                    "matched_rule_name": "Quy tắc 3: Khách Bán lẻ & E-commerce Miền Nam",
                    "created_at": format_datetime(base_time + timedelta(minutes=10)),
                    "processed_at": format_datetime(base_time + timedelta(minutes=10, seconds=3)),
                    "elapsed_seconds": 3.0,
                    "sla_status": "MET",
                    "unmatched_reason": None,
                    "notes": "Phân bổ tự động qua Quy tắc #3. Xoay vòng Team Miền Nam hoàn tất trong 3.0s."
                },
                {
                    "id": "lead-1004",
                    "code": "LD-1004",
                    "name": "Fintech Solutions Vietnam",
                    "contact_person": "Ông Vũ Hoàng Hải",
                    "phone": "0987 654 321",
                    "email": "hai.vh@fintechviet.io",
                    "region": "Miền Trung",
                    "city": "Đà Nẵng",
                    "industry": "Công nghệ thông tin",
                    "estimated_value": 500000000,
                    "source": "API Tích hợp bên ngoài",
                    "status": LEAD_STATUS_ASSIGNED,
                    "assigned_to_user_id": "usr-07",  # Gán trực tiếp Phạm Hoàng Nam
                    "assigned_team_id": None,
                    "matched_rule_id": "rule-04",
                    "matched_rule_name": "Quy tắc 4: Dự án Công nghệ thông tin cao cấp",
                    "created_at": format_datetime(base_time + timedelta(minutes=15)),
                    "processed_at": format_datetime(base_time + timedelta(minutes=15, seconds=1)),
                    "elapsed_seconds": 1.8,
                    "sla_status": "MET",
                    "unmatched_reason": None,
                    "notes": "Phân bổ trực tiếp theo Quy tắc #4 cho chuyên gia Phạm Hoàng Nam trong 1.8s."
                },
                # CÁC LEAD MẪU RƠI VÀO HÀNG CHỜ PHÂN TAY (MANUAL QUEUE)
                # Tiêu chí đề bài: "Lead không khớp quy tắc nào rơi vào hàng chờ để trưởng nhóm phân tay"
                {
                    "id": "lead-1005",
                    "code": "LD-1005",
                    "name": "Trường Quốc Tế Gateway Education",
                    "contact_person": "Bà Nguyễn Ngọc Lan",
                    "phone": "0938 111 222",
                    "email": "admissions@gateway.edu.vn",
                    "region": "Miền Trung",
                    "city": "Huế",
                    "industry": "Giáo dục & Đào tạo",
                    "estimated_value": 180000000,
                    "source": "Website Form",
                    "status": LEAD_STATUS_MANUAL_QUEUE,
                    "assigned_to_user_id": None,
                    "assigned_team_id": None,
                    "matched_rule_id": None,
                    "matched_rule_name": None,
                    "created_at": format_datetime(base_time + timedelta(minutes=20)),
                    "processed_at": format_datetime(base_time + timedelta(minutes=20, seconds=2)),
                    "elapsed_seconds": 2.0,
                    "sla_status": "MET",
                    "unmatched_reason": "Không khớp bất kỳ quy tắc nào trong 5 quy tắc đang kích hoạt (Khu vực: Miền Trung, Ngành: Giáo dục & Đào tạo)",
                    "notes": "Chuyển vào hàng chờ phân tay của Trưởng nhóm theo đúng quy định SCRUM-49."
                },
                {
                    "id": "lead-1006",
                    "code": "LD-1006",
                    "name": "Bệnh Viện Đa Khoa An Sinh Phúc",
                    "contact_person": "Bác sĩ Phạm Quốc Tuấn",
                    "phone": "0944 555 666",
                    "email": "info@ansinhphuc.com",
                    "region": "Miền Bắc",
                    "city": "Hải Phòng",
                    "industry": "Y tế & Chăm sóc sức khỏe",
                    "estimated_value": 420000000,
                    "source": "Đối tác giới thiệu (Referral)",
                    "status": LEAD_STATUS_MANUAL_QUEUE,
                    "assigned_to_user_id": None,
                    "assigned_team_id": None,
                    "matched_rule_id": None,
                    "matched_rule_name": None,
                    "created_at": format_datetime(base_time + timedelta(minutes=25)),
                    "processed_at": format_datetime(base_time + timedelta(minutes=25, seconds=2)),
                    "elapsed_seconds": 2.2,
                    "sla_status": "MET",
                    "unmatched_reason": "Không khớp bất kỳ quy tắc nào (Khu vực: Miền Bắc, Ngành: Y tế & Chăm sóc sức khỏe chưa cấu hình quy tắc riêng)",
                    "notes": "Chờ Trưởng nhóm chỉ định nhân sự phụ trách."
                }
            ]

            self.leads = seed_leads
            self.lead_seq = 1006

            # Khởi tạo một số log lịch sử của worker
            self.worker_logs.append({
                "id": str(uuid.uuid4())[:8],
                "timestamp": format_datetime(base_time + timedelta(minutes=20, seconds=2)),
                "lead_id": "lead-1005",
                "lead_code": "LD-1005",
                "action": "FALLBACK_MANUAL_QUEUE",
                "status": "WARNING",
                "details": "Lead LD-1005 không khớp quy tắc nào -> Tự động chuyển vào Hàng chờ phân tay của Trưởng nhóm.",
                "elapsed_ms": 15
            })
            self.worker_logs.append({
                "id": str(uuid.uuid4())[:8],
                "timestamp": format_datetime(base_time + timedelta(minutes=15, seconds=1)),
                "lead_id": "lead-1004",
                "lead_code": "LD-1004",
                "action": "AUTO_ASSIGNED",
                "status": "SUCCESS",
                "details": "Lead LD-1004 khớp Quy tắc #4 (Ưu tiên 4). Gán trực tiếp cho Phạm Hoàng Nam (Công nghệ). Hoàn tất trong 1.8s.",
                "elapsed_ms": 12
            })

    # ==========================================
    # CÁC PHƯƠNG THỨC XỬ LÝ QUY TẮC (RULES)
    # ==========================================
    def get_rules(self, active_only: bool = False) -> List[Dict[str, Any]]:
        with self.lock:
            # Sắp xếp theo thứ tự ưu tiên tăng dần (Priority 1 -> 2 -> 3...)
            sorted_rules = sorted(self.rules, key=lambda r: r.get("priority", 999))
            if active_only:
                return [r for r in sorted_rules if r.get("is_active", True)]
            return list(sorted_rules)

    def get_rule_by_id(self, rule_id: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            for r in self.rules:
                if r["id"] == rule_id:
                    return dict(r)
            return None

    def add_rule(self, rule_data: Dict[str, Any]) -> Dict[str, Any]:
        with self.lock:
            new_id = f"rule-{len(self.rules) + 1:02d}"
            rule_data["id"] = new_id
            rule_data["matches_count"] = 0
            rule_data["created_at"] = format_datetime(get_current_time())
            rule_data.setdefault("min_deal_value", 0)
            rule_data.setdefault("description", "")
            rule_data.setdefault("is_active", True)
            
            # Nếu priority không được truyền hoặc trùng, đặt vào vị trí tương ứng
            if "priority" not in rule_data or not rule_data["priority"]:
                rule_data["priority"] = len(self.rules) + 1
            else:
                rule_data["priority"] = int(rule_data["priority"])
                # Đẩy các rule có priority >= giá trị này lên 1 bậc
                for r in self.rules:
                    if r["priority"] >= rule_data["priority"]:
                        r["priority"] += 1

            self.rules.append(rule_data)
            self._normalize_priorities()
            return rule_data

    def update_rule(self, rule_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        with self.lock:
            target = None
            for r in self.rules:
                if r["id"] == rule_id:
                    target = r
                    break
            if not target:
                return None

            new_priority = update_data.get("priority")
            if new_priority and int(new_priority) != target["priority"]:
                new_p = int(new_priority)
                old_p = target["priority"]
                target["priority"] = new_p
                for r in self.rules:
                    if r["id"] == rule_id:
                        continue
                    if new_p < old_p and new_p <= r["priority"] < old_p:
                        r["priority"] += 1
                    elif new_p > old_p and old_p < r["priority"] <= new_p:
                        r["priority"] -= 1

            for key, val in update_data.items():
                if key != "priority":
                    target[key] = val

            self._normalize_priorities()
            return dict(target)

    def delete_rule(self, rule_id: str) -> bool:
        with self.lock:
            initial_len = len(self.rules)
            self.rules = [r for r in self.rules if r["id"] != rule_id]
            if len(self.rules) < initial_len:
                self._normalize_priorities()
                return True
            return False

    def toggle_rule_status(self, rule_id: str) -> Optional[bool]:
        with self.lock:
            for r in self.rules:
                if r["id"] == rule_id:
                    r["is_active"] = not r.get("is_active", True)
                    return r["is_active"]
            return None

    def move_rule_priority(self, rule_id: str, direction: str) -> bool:
        """Di chuyển độ ưu tiên của quy tắc: 'up' (tăng ưu tiên) hoặc 'down' (giảm ưu tiên)"""
        with self.lock:
            self._normalize_priorities()
            rules_sorted = sorted(self.rules, key=lambda r: r["priority"])
            index = -1
            for i, r in enumerate(rules_sorted):
                if r["id"] == rule_id:
                    index = i
                    break
            if index == -1:
                return False

            if direction == "up" and index > 0:
                # Đổi chỗ với rule phía trên
                prev_rule = rules_sorted[index - 1]
                curr_rule = rules_sorted[index]
                prev_rule["priority"], curr_rule["priority"] = curr_rule["priority"], prev_rule["priority"]
                self._normalize_priorities()
                return True
            elif direction == "down" and index < len(rules_sorted) - 1:
                # Đổi chỗ với rule phía dưới
                next_rule = rules_sorted[index + 1]
                curr_rule = rules_sorted[index]
                next_rule["priority"], curr_rule["priority"] = curr_rule["priority"], next_rule["priority"]
                self._normalize_priorities()
                return True
            return False

    def _normalize_priorities(self):
        """Chuẩn hóa lại thứ tự ưu tiên thành 1, 2, 3... liên tục"""
        sorted_rules = sorted(self.rules, key=lambda r: r.get("priority", 999))
        for idx, rule in enumerate(sorted_rules, start=1):
            rule["priority"] = idx

    # ==========================================
    # CÁC PHƯƠNG THỨC XỬ LÝ LEAD
    # ==========================================
    def get_leads(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        with self.lock:
            leads = sorted(self.leads, key=lambda x: x.get("created_at", ""), reverse=True)
            if status:
                return [l for l in leads if l.get("status") == status]
            return list(leads)

    def get_lead_by_id(self, lead_id: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            for l in self.leads:
                if l["id"] == lead_id:
                    return dict(l)
            return None

    def add_lead(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Tiếp nhận Lead mới vào hệ thống (ở trạng thái PENDING để background worker xử lý)"""
        with self.lock:
            self.lead_seq += 1
            lead_id = f"lead-{self.lead_seq}"
            code = f"LD-{self.lead_seq}"
            
            now = get_current_time()
            new_lead = {
                "id": lead_id,
                "code": code,
                "name": lead_data.get("name", "Khách hàng mới"),
                "contact_person": lead_data.get("contact_person", ""),
                "phone": lead_data.get("phone", ""),
                "email": lead_data.get("email", ""),
                "region": lead_data.get("region", "Toàn quốc"),
                "city": lead_data.get("city", ""),
                "industry": lead_data.get("industry", "Tất cả ngành nghề"),
                "estimated_value": float(lead_data.get("estimated_value", 0)),
                "source": lead_data.get("source", "Website Form"),
                "status": LEAD_STATUS_PENDING,
                "assigned_to_user_id": None,
                "assigned_team_id": None,
                "matched_rule_id": None,
                "matched_rule_name": None,
                "created_at": format_datetime(now),
                "processed_at": None,
                "elapsed_seconds": None,
                "sla_status": "PENDING",
                "unmatched_reason": None,
                "notes": lead_data.get("notes", "Đang chờ luồng chạy nền phân bổ theo quy tắc...")
            }
            self.leads.insert(0, new_lead)
            return new_lead

    def get_pending_leads(self) -> List[Dict[str, Any]]:
        """Lấy danh sách các Lead đang chờ xử lý nền"""
        with self.lock:
            return [l for l in self.leads if l.get("status") == LEAD_STATUS_PENDING]

    def get_manual_queue_leads(self) -> List[Dict[str, Any]]:
        """Lấy danh sách Lead không khớp quy tắc, rơi vào hàng chờ để trưởng nhóm phân tay"""
        with self.lock:
            return [l for l in self.leads if l.get("status") == LEAD_STATUS_MANUAL_QUEUE]

    def manual_assign_lead(self, lead_id: str, target_user_id: str, assigner_name: str, notes: str = "") -> Optional[Dict[str, Any]]:
        """Trưởng nhóm phân công tay cho nhân viên từ hàng chờ"""
        with self.lock:
            lead = None
            for l in self.leads:
                if l["id"] == lead_id:
                    lead = l
                    break
            if not lead:
                return None

            user = self.users.get(target_user_id)
            if not user:
                return None

            now = get_current_time()
            lead["status"] = LEAD_STATUS_ASSIGNED
            lead["assigned_to_user_id"] = target_user_id
            lead["assigned_team_id"] = user.get("team_id")
            lead["processed_at"] = format_datetime(now)
            lead["manual_assigned_by"] = assigner_name
            lead["manual_notes"] = notes or f"Được {assigner_name} phân công thủ công"
            lead["notes"] = f"Phân công tay: Đã gán cho {user['name']} bởi {assigner_name}. {notes}".strip()

            # Tăng số lượng lead đã nhận cho user
            user["assigned_count"] = user.get("assigned_count", 0) + 1

            # Ghi log
            self.add_worker_log({
                "lead_id": lead_id,
                "lead_code": lead.get("code"),
                "action": "MANUAL_ASSIGN",
                "status": "INFO",
                "details": f"Trưởng nhóm ({assigner_name}) đã phân tay lead {lead.get('code')} cho {user['name']}.",
                "elapsed_ms": 5
            })
            return dict(lead)

    # ==========================================
    # CƠ CHẾ XOAY VÒNG ĐỀU TRONG NHÓM (ROUND-ROBIN)
    # ==========================================
    def get_next_round_robin_user(self, team_id: str) -> Optional[Dict[str, Any]]:
        """
        Thuật toán Round-Robin:
        Lấy nhân viên kế tiếp trong nhóm đang hoạt động (ACTIVE),
        cập nhật chỉ số xoay vòng (rr_index) của nhóm và tăng bộ đếm lead.
        """
        with self.lock:
            team = self.teams.get(team_id)
            if not team:
                return None

            member_ids = team.get("members", [])
            if not member_ids:
                return None

            # Lọc các thành viên đang ACTIVE
            active_members = [
                self.users[uid] for uid in member_ids 
                if uid in self.users and self.users[uid].get("status") == "ACTIVE"
            ]

            if not active_members:
                return None

            # Lấy theo chỉ số xoay vòng
            current_index = team.get("rr_index", 0) % len(active_members)
            selected_user = active_members[current_index]

            # Cập nhật con trỏ xoay vòng kế tiếp
            team["rr_index"] = (current_index + 1) % len(active_members)

            # Tăng số lượng lead của nhân sự này
            selected_user["assigned_count"] = selected_user.get("assigned_count", 0) + 1

            return selected_user

    # ==========================================
    # NHẬT KÝ LUỒNG NỀN (WORKER LOGS)
    # ==========================================
    def add_worker_log(self, log_entry: Dict[str, Any]):
        with self.lock:
            log_entry["id"] = str(uuid.uuid4())[:8]
            if "timestamp" not in log_entry:
                log_entry["timestamp"] = format_datetime(get_current_time())
            self.worker_logs.insert(0, log_entry)
            # Giới hạn 200 logs gần nhất để tối ưu bộ nhớ
            if len(self.worker_logs) > 200:
                self.worker_logs.pop()

    def get_worker_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self.lock:
            return list(self.worker_logs[:limit])

    # ==========================================
    # THỐNG KÊ TỔNG HỢP (DASHBOARD METRICS)
    # ==========================================
    def get_metrics(self) -> Dict[str, Any]:
        with self.lock:
            total_leads = len(self.leads)
            assigned_leads = [l for l in self.leads if l.get("status") == LEAD_STATUS_ASSIGNED]
            manual_queue_leads = [l for l in self.leads if l.get("status") == LEAD_STATUS_MANUAL_QUEUE]
            pending_leads = [l for l in self.leads if l.get("status") == LEAD_STATUS_PENDING]

            # Đánh giá SLA 5 phút (300 giây)
            met_sla_count = sum(1 for l in assigned_leads if l.get("sla_status") == "MET")
            sla_rate = (met_sla_count / len(assigned_leads) * 100) if assigned_leads else 100.0

            # Phân bố lead theo nhóm
            team_distribution = {}
            for t_id, t in self.teams.items():
                count = sum(1 for l in assigned_leads if l.get("assigned_team_id") == t_id)
                team_distribution[t["name"]] = count

            return {
                "total_leads": total_leads,
                "assigned_count": len(assigned_leads),
                "manual_queue_count": len(manual_queue_leads),
                "pending_count": len(pending_leads),
                "active_rules_count": sum(1 for r in self.rules if r.get("is_active", True)),
                "total_rules_count": len(self.rules),
                "sla_rate": round(sla_rate, 1),
                "sla_limit_seconds": SLA_LIMIT_SECONDS,
                "team_distribution": team_distribution
            }


# Khởi tạo singleton instance toàn cục
db = Database()
