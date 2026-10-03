"""
MODULE QUẢN LÝ CƠ CẤU TỔ CHỨC KINH DOANH & PHẠM VI DỮ LIỆU (SCRUM-85)
=====================================================================
Mã Nhiệm Vụ: SCRUM-83 / SCRUM-85
User Story:
  "Là Giám đốc kinh doanh, tôi muốn khai báo cơ cấu tổ chức kinh doanh,
   để phạm vi dữ liệu của trưởng nhóm bám đúng cây tổ chức thật."

Đáp ứng 100% 4 Tiêu chí chấp nhận (Description):
  1. Nhóm kinh doanh có cấu trúc cây, mỗi nhóm có một trưởng nhóm.
  2. Mỗi nhân viên thuộc đúng một nhóm tại một thời điểm.
  3. Cây tổ chức này quyết định phạm vi dữ liệu mà Trưởng nhóm nhìn thấy.
  4. Khai báo khu vực địa lý và gán khu vực cho nhóm.
=====================================================================
"""

import copy
from typing import Dict, List, Optional, Set, Tuple, Any

# ==============================================================================
# 1. KHỞI TẠO DỮ LIỆU BAN ĐẦU (SEED DATA)
# ==============================================================================

# Danh mục khu vực địa lý ban đầu (Tiêu chí 4)
INITIAL_REGIONS: Dict[str, Dict[str, Any]] = {
    "REG_MB": {
        "id": "REG_MB",
        "name": "Khu vực Miền Bắc (Northern Region)",
        "code": "MB",
        "provinces": "Hà Nội, Hải Phòng, Quảng Ninh, Bắc Ninh, Hải Dương",
        "description": "Vùng kinh tế trọng điểm phía Bắc và đồng bằng sông Hồng.",
        "badge_color": "#2563eb"  # Blue
    },
    "REG_MN": {
        "id": "REG_MN",
        "name": "Khu vực Miền Nam (Southern Region)",
        "code": "MN",
        "provinces": "TP. Hồ Chí Minh, Bình Dương, Đồng Nai, Long An, Cần Thơ",
        "description": "Trung tâm kinh tế năng động phía Nam và ĐBSCL.",
        "badge_color": "#16a34a"  # Green
    },
    "REG_MT": {
        "id": "REG_MT",
        "name": "Khu vực Miền Trung (Central Region)",
        "code": "MT",
        "provinces": "Đà Nẵng, Thừa Thiên Huế, Quảng Nam, Khánh Hòa",
        "description": "Khu vực duyên hải miền Trung và các thành phố ven biển.",
        "badge_color": "#d97706"  # Amber
    },
    "REG_TOAN_QUOC": {
        "id": "REG_TOAN_QUOC",
        "name": "Toàn Quốc (Nationwide)",
        "code": "HQ",
        "provinces": "Toàn bộ 63 tỉnh thành cả nước",
        "description": "Trụ sở chính quản lý và điều phối hoạt động kinh doanh toàn quốc.",
        "badge_color": "#7c3aed"  # Purple
    }
}

# Danh mục nhân viên ban đầu (Tiêu chí 2: Mỗi nhân viên thuộc đúng 1 nhóm)
INITIAL_EMPLOYEES: Dict[str, Dict[str, Any]] = {
    "EMP001": {
        "id": "EMP001",
        "name": "Trần Hải Đăng",
        "role_title": "Giám Đốc Kinh Doanh Toàn Quốc",
        "team_id": "TEAM_HQ",
        "email": "dang.tran@corp.vn",
        "phone": "0981 234 567",
        "is_director": True,
        "avatar": "👨‍💼"
    },
    "EMP002": {
        "id": "EMP002",
        "name": "Nguyễn Minh Tuấn",
        "role_title": "Giám Đốc Chi Nhánh Miền Bắc",
        "team_id": "TEAM_NORTH",
        "email": "tuan.nguyen@corp.vn",
        "phone": "0912 345 678",
        "is_director": False,
        "avatar": "👨‍💼"
    },
    "EMP003": {
        "id": "EMP003",
        "name": "Lê Thị Bích Hạnh",
        "role_title": "Giám Đốc Chi Nhánh Miền Nam",
        "team_id": "TEAM_SOUTH",
        "email": "hanh.le@corp.vn",
        "phone": "0903 456 789",
        "is_director": False,
        "avatar": "👩‍💼"
    },
    "EMP004": {
        "id": "EMP004",
        "name": "Phạm Quốc Dũng",
        "role_title": "Trưởng Nhóm Bán Lẻ Hà Nội",
        "team_id": "TEAM_HN_RETAIL",
        "email": "dung.pham@corp.vn",
        "phone": "0978 123 456",
        "is_director": False,
        "avatar": "👨‍💻"
    },
    "EMP005": {
        "id": "EMP005",
        "name": "Hoàng Thu Thảo",
        "role_title": "Trưởng Nhóm Doanh Nghiệp Hà Nội",
        "team_id": "TEAM_HN_CORP",
        "email": "thao.hoang@corp.vn",
        "phone": "0936 987 654",
        "is_director": False,
        "avatar": "👩‍💻"
    },
    "EMP006": {
        "id": "EMP006",
        "name": "Đặng Văn Lâm",
        "role_title": "Trưởng Nhóm Kinh Doanh TP.HCM 1",
        "team_id": "TEAM_SG_TEAM1",
        "email": "lam.dang@corp.vn",
        "phone": "0989 654 321",
        "is_director": False,
        "avatar": "👨‍💼"
    },
    "EMP007": {
        "id": "EMP007",
        "name": "Vũ Anh Tú",
        "role_title": "Chuyên Viên Kinh Doanh",
        "team_id": "TEAM_HN_RETAIL",
        "email": "tu.vu@corp.vn",
        "phone": "0915 111 222",
        "is_director": False,
        "avatar": "🧑‍💼"
    },
    "EMP008": {
        "id": "EMP008",
        "name": "Nguyễn Lan Anh",
        "role_title": "Chuyên Viên Khách Hàng Doanh Nghiệp",
        "team_id": "TEAM_HN_CORP",
        "email": "lananh.nguyen@corp.vn",
        "phone": "0963 222 333",
        "is_director": False,
        "avatar": "👩‍💼"
    },
    "EMP009": {
        "id": "EMP009",
        "name": "Trương Trọng Khang",
        "role_title": "Chuyên Viên Kinh Doanh Miền Nam",
        "team_id": "TEAM_SG_TEAM1",
        "email": "khang.truong@corp.vn",
        "phone": "0908 333 444",
        "is_director": False,
        "avatar": "🧑‍💼"
    },
    "EMP010": {
        "id": "EMP010",
        "name": "Mai Ngọc Mai",
        "role_title": "Chuyên Viên Bán Hàng Trực Tiếp",
        "team_id": "TEAM_HN_RETAIL",
        "email": "mai.mai@corp.vn",
        "phone": "0984 555 666",
        "is_director": False,
        "avatar": "👩‍💼"
    }
}

# Cơ cấu cây nhóm kinh doanh ban đầu (Tiêu chí 1: Cấu trúc cây, mỗi nhóm 1 trưởng nhóm)
INITIAL_TEAMS: Dict[str, Dict[str, Any]] = {
    "TEAM_HQ": {
        "id": "TEAM_HQ",
        "name": "Khối Kinh Doanh Toàn Quốc (HQ)",
        "parent_id": None,               # Node gốc (Root)
        "leader_id": "EMP001",           # Trưởng nhóm: Trần Hải Đăng (GĐKD)
        "region_id": "REG_TOAN_QUOC",
        "description": "Ban Lãnh đạo Khối Kinh doanh quản lý chiến lược toàn quốc."
    },
    "TEAM_NORTH": {
        "id": "TEAM_NORTH",
        "name": "Chi Nhánh Miền Bắc",
        "parent_id": "TEAM_HQ",
        "leader_id": "EMP002",           # Trưởng nhóm: Nguyễn Minh Tuấn
        "region_id": "REG_MB",
        "description": "Quản lý thị trường phía Bắc từ Ninh Bình trở ra."
    },
    "TEAM_SOUTH": {
        "id": "TEAM_SOUTH",
        "name": "Chi Nhánh Miền Nam",
        "parent_id": "TEAM_HQ",
        "leader_id": "EMP003",           # Trưởng nhóm: Lê Thị Bích Hạnh
        "region_id": "REG_MN",
        "description": "Quản lý thị trường Đông Nam Bộ và Tây Nam Bộ."
    },
    "TEAM_HN_RETAIL": {
        "id": "TEAM_HN_RETAIL",
        "name": "Đội Bán Lẻ & Dịch Vụ Hà Nội",
        "parent_id": "TEAM_NORTH",
        "leader_id": "EMP004",           # Trưởng nhóm: Phạm Quốc Dũng
        "region_id": "REG_MB",
        "description": "Phụ trách mạng lưới khách hàng bán lẻ khu vực Hà Nội."
    },
    "TEAM_HN_CORP": {
        "id": "TEAM_HN_CORP",
        "name": "Đội Khách Hàng Doanh Nghiệp (B2B) Hà Nội",
        "parent_id": "TEAM_NORTH",
        "leader_id": "EMP005",           # Trưởng nhóm: Hoàng Thu Thảo
        "region_id": "REG_MB",
        "description": "Phụ trách các tập đoàn và doanh nghiệp lớn tại Hà Nội."
    },
    "TEAM_SG_TEAM1": {
        "id": "TEAM_SG_TEAM1",
        "name": "Đội Kinh Doanh Trung Tâm TP.HCM",
        "parent_id": "TEAM_SOUTH",
        "leader_id": "EMP006",           # Trưởng nhóm: Đặng Văn Lâm
        "region_id": "REG_MN",
        "description": "Khai thác thị trường Quận 1, Quận 3, Thủ Đức và khu lân cận."
    }
}

# Dữ liệu khách hàng và cơ hội bán hàng mẫu (Tiêu chí 3: Phạm vi dữ liệu phân cấp)
INITIAL_DEALS: List[Dict[str, Any]] = [
    {
        "id": "DEAL-001",
        "customer_name": "Tập đoàn Công nghệ FPT Smart",
        "team_id": "TEAM_HN_CORP",
        "assignee_id": "EMP008",         # Nguyễn Lan Anh
        "value_vnd": 450_000_000,
        "status": "Đang Đàm Phán",
        "region_id": "REG_MB",
        "stage": "Báo Giá",
        "updated_at": "02/10/2026"
    },
    {
        "id": "DEAL-002",
        "customer_name": "Công ty Cổ phần Bán lẻ Thăng Long",
        "team_id": "TEAM_HN_RETAIL",
        "assignee_id": "EMP007",         # Vũ Anh Tú
        "value_vnd": 85_000_000,
        "status": "Đã Ký Hợp Đồng",
        "region_id": "REG_MB",
        "stage": "Thành Công",
        "updated_at": "01/10/2026"
    },
    {
        "id": "DEAL-003",
        "customer_name": "Chuỗi Cửa hàng Trà Sữa Hà Nội",
        "team_id": "TEAM_HN_RETAIL",
        "assignee_id": "EMP010",         # Mai Ngọc Mai
        "value_vnd": 42_000_000,
        "status": "Tiếp Cận Mới",
        "region_id": "REG_MB",
        "stage": "Tư Vấn",
        "updated_at": "02/10/2026"
    },
    {
        "id": "DEAL-004",
        "customer_name": "Tập đoàn Vận tải & Logistics Sài Gòn",
        "team_id": "TEAM_SG_TEAM1",
        "assignee_id": "EMP009",         # Trương Trọng Khang
        "value_vnd": 320_000_000,
        "status": "Đang Đàm Phán",
        "region_id": "REG_MN",
        "stage": "Báo Giá",
        "updated_at": "02/10/2026"
    },
    {
        "id": "DEAL-005",
        "customer_name": "Công ty TNHH May Mặc Chợ Lớn",
        "team_id": "TEAM_SG_TEAM1",
        "assignee_id": "EMP006",         # Đặng Văn Lâm (Trưởng nhóm SG1 phụ trách trực tiếp deal lớn)
        "value_vnd": 190_000_000,
        "status": "Đã Ký Hợp Đồng",
        "region_id": "REG_MN",
        "stage": "Thành Công",
        "updated_at": "30/09/2026"
    },
    {
        "id": "DEAL-006",
        "customer_name": "Bộ Nông nghiệp & Phát triển Nông thôn (Dự án Khối HQ)",
        "team_id": "TEAM_HQ",
        "assignee_id": "EMP001",         # Trần Hải Đăng (GĐKD trực tiếp)
        "value_vnd": 1_200_000_000,
        "status": "Đang Đàm Phán",
        "region_id": "REG_TOAN_QUOC",
        "stage": "Trình Dự Thảo",
        "updated_at": "02/10/2026"
    }
]

# In-memory working database
DB_REGIONS = copy.deepcopy(INITIAL_REGIONS)
DB_EMPLOYEES = copy.deepcopy(INITIAL_EMPLOYEES)
DB_TEAMS = copy.deepcopy(INITIAL_TEAMS)
DB_DEALS = copy.deepcopy(INITIAL_DEALS)


def reset_database():
    """Khôi phục toàn bộ cơ sở dữ liệu về trạng thái mẫu chuẩn ban đầu."""
    DB_REGIONS.clear()
    DB_REGIONS.update(copy.deepcopy(INITIAL_REGIONS))
    
    DB_EMPLOYEES.clear()
    DB_EMPLOYEES.update(copy.deepcopy(INITIAL_EMPLOYEES))
    
    DB_TEAMS.clear()
    DB_TEAMS.update(copy.deepcopy(INITIAL_TEAMS))
    
    DB_DEALS.clear()
    DB_DEALS.extend(copy.deepcopy(INITIAL_DEALS))


# ==============================================================================
# 2. XỬ LÝ KHU VỰC ĐỊA LÝ (TIÊU CHÍ 4)
# ==============================================================================

def get_all_regions() -> List[Dict[str, Any]]:
    """Lấy danh sách tất cả các khu vực địa lý."""
    return list(DB_REGIONS.values())

def get_region(region_id: str) -> Optional[Dict[str, Any]]:
    """Lấy thông tin một khu vực địa lý theo ID."""
    return DB_REGIONS.get(region_id)

def create_region(region_id: str, name: str, code: str, provinces: str, description: str = "", badge_color: str = "#3b82f6") -> Tuple[bool, str]:
    """
    Khai báo khu vực địa lý mới.
    """
    clean_id = (region_id or "").strip().upper()
    if not clean_id:
        return False, "Mã khu vực không được để trống."
    if clean_id in DB_REGIONS:
        return False, f"Mã khu vực '{clean_id}' đã tồn tại trong hệ thống."
    if not name or not name.strip():
        return False, "Tên khu vực địa lý không được để trống."
    
    DB_REGIONS[clean_id] = {
        "id": clean_id,
        "name": name.strip(),
        "code": (code or clean_id).strip().upper(),
        "provinces": provinces.strip() if provinces else "Chưa cập nhật",
        "description": description.strip() if description else "",
        "badge_color": badge_color or "#3b82f6"
    }
    return True, f"Khai báo khu vực '{name}' thành công."

def update_region(region_id: str, name: str, code: str, provinces: str, description: str = "", badge_color: str = "") -> Tuple[bool, str]:
    """Cập nhật thông tin khu vực địa lý."""
    if region_id not in DB_REGIONS:
        return False, "Khu vực không tồn tại."
    if not name or not name.strip():
        return False, "Tên khu vực không được để trống."
    
    DB_REGIONS[region_id]["name"] = name.strip()
    if code:
        DB_REGIONS[region_id]["code"] = code.strip().upper()
    if provinces:
        DB_REGIONS[region_id]["provinces"] = provinces.strip()
    DB_REGIONS[region_id]["description"] = description.strip()
    if badge_color:
        DB_REGIONS[region_id]["badge_color"] = badge_color
    return True, "Cập nhật khu vực thành công."

def delete_region(region_id: str) -> Tuple[bool, str]:
    """
    Xóa khu vực địa lý (Có kiểm tra ràng buộc xem có nhóm nào đang sử dụng không).
    """
    if region_id not in DB_REGIONS:
        return False, "Khu vực không tồn tại."
    
    # Kiểm tra xem có nhóm kinh doanh nào đang gán khu vực này không
    used_teams = [t["name"] for t in DB_TEAMS.values() if t.get("region_id") == region_id]
    if used_teams:
        return False, f"Không thể xóa khu vực này vì đang được gán cho nhóm: {', '.join(used_teams)}."
    
    del DB_REGIONS[region_id]
    return True, "Đã xóa khu vực địa lý thành công."


# ==============================================================================
# 3. QUẢN LÝ NHÂN VIÊN & RÀNG BUỘC DUY NHẤT 1 NHÓM (TIÊU CHÍ 2)
# ==============================================================================

def get_all_employees() -> List[Dict[str, Any]]:
    """Lấy danh sách tất cả nhân viên kèm thông tin nhóm trực thuộc."""
    employees = []
    for emp_id, emp in DB_EMPLOYEES.items():
        emp_copy = copy.deepcopy(emp)
        team = DB_TEAMS.get(emp["team_id"])
        emp_copy["team_name"] = team["name"] if team else "Chưa gán nhóm"
        # Kiểm tra xem nhân viên này có đang là trưởng nhóm nào không
        led_teams = [t["name"] for t in DB_TEAMS.values() if t.get("leader_id") == emp_id]
        emp_copy["led_teams"] = led_teams
        emp_copy["is_leader"] = len(led_teams) > 0
        employees.append(emp_copy)
    return employees

def get_employee(emp_id: str) -> Optional[Dict[str, Any]]:
    """Lấy thông tin chi tiết một nhân viên."""
    if emp_id not in DB_EMPLOYEES:
        return None
    emp = copy.deepcopy(DB_EMPLOYEES[emp_id])
    team = DB_TEAMS.get(emp["team_id"])
    emp["team_name"] = team["name"] if team else "Chưa gán nhóm"
    return emp

def assign_employee_to_team(emp_id: str, new_team_id: str) -> Tuple[bool, str]:
    """
    TIÊU CHÍ 2: Mỗi nhân viên thuộc đúng một nhóm tại một thời điểm.
    Khi gán vào nhóm mới, tự động hủy trực thuộc nhóm cũ.
    """
    if emp_id not in DB_EMPLOYEES:
        return False, f"Nhân viên '{emp_id}' không tồn tại."
    if new_team_id not in DB_TEAMS:
        return False, f"Nhóm kinh doanh '{new_team_id}' không tồn tại."
    
    current_team_id = DB_EMPLOYEES[emp_id].get("team_id")
    if current_team_id == new_team_id:
        return True, f"Nhân viên đã thuộc nhóm '{DB_TEAMS[new_team_id]['name']}' rồi."
    
    old_team_name = DB_TEAMS[current_team_id]["name"] if current_team_id in DB_TEAMS else "Chưa gán"
    new_team_name = DB_TEAMS[new_team_id]["name"]
    
    # Cập nhật duy nhất trường team_id của nhân viên -> Đảm bảo tại một thời điểm chỉ thuộc 1 nhóm
    DB_EMPLOYEES[emp_id]["team_id"] = new_team_id
    
    return True, f"Đã chuyển nhân viên '{DB_EMPLOYEES[emp_id]['name']}' từ nhóm '{old_team_name}' sang nhóm '{new_team_name}'."

def add_employee(emp_id: str, name: str, role_title: str, team_id: str, email: str, phone: str) -> Tuple[bool, str]:
    """Thêm mới một nhân viên vào hệ thống và gán vào đúng một nhóm."""
    clean_id = (emp_id or "").strip().upper()
    if not clean_id:
        return False, "Mã nhân viên không được để trống."
    if clean_id in DB_EMPLOYEES:
        return False, f"Mã nhân viên '{clean_id}' đã tồn tại."
    if not name or not name.strip():
        return False, "Tên nhân viên không được để trống."
    if team_id not in DB_TEAMS:
        return False, "Nhóm kinh doanh được chọn không tồn tại."
    
    DB_EMPLOYEES[clean_id] = {
        "id": clean_id,
        "name": name.strip(),
        "role_title": role_title.strip() if role_title else "Chuyên Viên Kinh Doanh",
        "team_id": team_id,
        "email": email.strip() if email else f"{clean_id.lower()}@corp.vn",
        "phone": phone.strip() if phone else "0900 000 000",
        "is_director": False,
        "avatar": "🧑‍💼"
    }
    return True, f"Đã thêm nhân viên '{name}' vào nhóm '{DB_TEAMS[team_id]['name']}'."


# ==============================================================================
# 4. QUẢN LÝ CÂU TRÚC CÂY NHÓM KINH DOANH & TRƯỞNG NHÓM (TIÊU CHÍ 1 & 4)
# ==============================================================================

def get_all_teams() -> List[Dict[str, Any]]:
    """Lấy danh sách tất cả các nhóm kinh doanh kèm các thông tin chi tiết liên quan."""
    teams = []
    for team_id, team in DB_TEAMS.items():
        t_copy = copy.deepcopy(team)
        # Tên nhóm cha
        parent = DB_TEAMS.get(team["parent_id"]) if team["parent_id"] else None
        t_copy["parent_name"] = parent["name"] if parent else "Không có (Gốc / Root)"
        
        # Thông tin Trưởng nhóm (Tiêu chí 1: mỗi nhóm có một trưởng nhóm)
        leader = DB_EMPLOYEES.get(team["leader_id"])
        t_copy["leader_name"] = leader["name"] if leader else "Chưa bổ nhiệm"
        t_copy["leader_phone"] = leader["phone"] if leader else ""
        t_copy["leader_email"] = leader["email"] if leader else ""
        t_copy["leader_avatar"] = leader.get("avatar", "👤") if leader else "👤"
        
        # Thông tin Khu vực địa lý (Tiêu chí 4: gán khu vực cho nhóm)
        region = DB_REGIONS.get(team.get("region_id", ""))
        t_copy["region_name"] = region["name"] if region else "Chưa gán khu vực"
        t_copy["region_code"] = region["code"] if region else "N/A"
        t_copy["region_badge_color"] = region["badge_color"] if region else "#64748b"
        
        # Số lượng thành viên thuộc nhóm
        members = [emp for emp in DB_EMPLOYEES.values() if emp["team_id"] == team_id]
        t_copy["member_count"] = len(members)
        t_copy["members"] = members
        
        teams.append(t_copy)
    return teams

def get_team(team_id: str) -> Optional[Dict[str, Any]]:
    """Lấy thông tin chi tiết của một nhóm kinh doanh."""
    if team_id not in DB_TEAMS:
        return None
    team = copy.deepcopy(DB_TEAMS[team_id])
    parent = DB_TEAMS.get(team["parent_id"]) if team["parent_id"] else None
    team["parent_name"] = parent["name"] if parent else "Không có (Root)"
    leader = DB_EMPLOYEES.get(team["leader_id"])
    team["leader_name"] = leader["name"] if leader else "Chưa bổ nhiệm"
    region = DB_REGIONS.get(team.get("region_id", ""))
    team["region_name"] = region["name"] if region else "Chưa gán khu vực"
    return team

def is_circular_dependency(team_id: str, new_parent_id: Optional[str]) -> bool:
    """
    Kiểm tra xem việc gán new_parent_id cho team_id có tạo thành chu trình lặp trong cây không.
    Trả về True nếu vi phạm (tạo chu trình).
    Ví dụ:
      - Không thể gán chính nó làm cha của nó (team_id == new_parent_id).
      - Không thể gán một con cháu (descendant) của team_id làm cha của team_id.
    """
    if not new_parent_id:
        return False
    if team_id == new_parent_id:
        return True
    
    # Duyệt ngược từ new_parent_id lên trên gốc
    curr = new_parent_id
    visited = set()
    while curr:
        if curr == team_id:
            return True
        if curr in visited:
            # Phát hiện chu trình đã có từ trước
            return True
        visited.add(curr)
        parent_obj = DB_TEAMS.get(curr)
        curr = parent_obj.get("parent_id") if parent_obj else None
    return False

def create_team(team_id: str, name: str, parent_id: Optional[str], leader_id: str, region_id: str, description: str = "") -> Tuple[bool, str]:
    """
    Khai báo nhóm kinh doanh mới trong cây tổ chức.
    Yêu cầu:
      - Mỗi nhóm có đúng một trưởng nhóm.
      - Gán khu vực địa lý cho nhóm.
      - Có nhóm cha hợp lệ hoặc là Root.
    """
    clean_id = (team_id or "").strip().upper()
    if not clean_id:
        return False, "Mã nhóm không được để trống."
    if clean_id in DB_TEAMS:
        return False, f"Mã nhóm '{clean_id}' đã tồn tại."
    if not name or not name.strip():
        return False, "Tên nhóm kinh doanh không được để trống."
    if not leader_id or leader_id not in DB_EMPLOYEES:
        return False, "Vui lòng chỉ định một Trưởng nhóm hợp lệ từ danh sách nhân sự."
    if not region_id or region_id not in DB_REGIONS:
        return False, "Vui lòng gán khu vực địa lý hợp lệ cho nhóm."
    
    if parent_id and parent_id not in DB_TEAMS:
        return False, f"Nhóm cha '{parent_id}' không tồn tại."
    
    # Tạo nhóm mới
    DB_TEAMS[clean_id] = {
        "id": clean_id,
        "name": name.strip(),
        "parent_id": parent_id if parent_id else None,
        "leader_id": leader_id,
        "region_id": region_id,
        "description": description.strip() if description else ""
    }
    
    # Tự động đồng bộ: Trưởng nhóm phải thuộc nhóm mà mình làm trưởng
    # (Tuân thủ Tiêu chí 2: Mỗi nhân viên thuộc đúng một nhóm tại một thời điểm)
    DB_EMPLOYEES[leader_id]["team_id"] = clean_id
    
    return True, f"Khai báo nhóm '{name}' thành công."

def update_team(team_id: str, name: str, parent_id: Optional[str], leader_id: str, region_id: str, description: str = "") -> Tuple[bool, str]:
    """
    Cập nhật cơ cấu nhóm kinh doanh.
    Kiểm tra nghiêm ngặt không được tạo chu trình cây (circular dependency).
    """
    if team_id not in DB_TEAMS:
        return False, "Nhóm kinh doanh không tồn tại."
    if not name or not name.strip():
        return False, "Tên nhóm không được để trống."
    if not leader_id or leader_id not in DB_EMPLOYEES:
        return False, "Trưởng nhóm được chọn không hợp lệ."
    if not region_id or region_id not in DB_REGIONS:
        return False, "Khu vực địa lý được chọn không hợp lệ."
    
    # Kiểm tra chu trình lặp
    target_parent = parent_id if (parent_id and parent_id.strip()) else None
    if is_circular_dependency(team_id, target_parent):
        return False, "Lỗi chu trình: Không thể chọn chính nhóm này hoặc con cháu của nó làm nhóm cha!"
    
    DB_TEAMS[team_id]["name"] = name.strip()
    DB_TEAMS[team_id]["parent_id"] = target_parent
    DB_TEAMS[team_id]["leader_id"] = leader_id
    DB_TEAMS[team_id]["region_id"] = region_id
    DB_TEAMS[team_id]["description"] = description.strip()
    
    # Đồng bộ trưởng nhóm vào nhóm này
    DB_EMPLOYEES[leader_id]["team_id"] = team_id
    
    return True, f"Cập nhật thông tin nhóm '{name}' thành công."

def delete_team(team_id: str) -> Tuple[bool, str]:
    """
    Xóa nhóm kinh doanh.
    Quy tắc an toàn: Không thể xóa nhóm nếu đang có nhóm con hoặc còn thành viên.
    """
    if team_id not in DB_TEAMS:
        return False, "Nhóm không tồn tại."
    
    # Kiểm tra nhóm con
    children = [t["name"] for t in DB_TEAMS.values() if t.get("parent_id") == team_id]
    if children:
        return False, f"Không thể xóa nhóm này vì đang có các nhóm con trực thuộc: {', '.join(children)}. Hãy chuyển các nhóm con trước."
    
    # Kiểm tra nhân viên thuộc nhóm (ngoại trừ trường hợp chuyển hết)
    members = [emp["name"] for emp in DB_EMPLOYEES.values() if emp["team_id"] == team_id]
    if members:
        return False, f"Không thể xóa nhóm này vì vẫn còn {len(members)} nhân viên ({', '.join(members[:3])}...). Hãy điều chuyển nhân viên sang nhóm khác trước."
    
    del DB_TEAMS[team_id]
    return True, "Đã xóa nhóm kinh doanh thành công."


# ==============================================================================
# 5. THUẬT TOÁN DUYỆT CÂY & XÁC ĐỊNH PHẠM VI DỮ LIỆU (TIÊU CHÍ 3)
# ==============================================================================

def get_sub_tree_team_ids(root_team_id: str) -> Set[str]:
    """
    TIÊU CHÍ 3: Lấy danh sách ID của nhóm hiện tại và TOÀN BỘ các nhóm con cháu (Subtree).
    Sử dụng thuật toán DFS/BFS duyệt cây tổ chức.
    """
    if root_team_id not in DB_TEAMS:
        return set()
    
    result = {root_team_id}
    queue = [root_team_id]
    
    while queue:
        current_id = queue.pop(0)
        # Tìm tất cả nhóm con trực tiếp có parent_id là current_id
        for t_id, t_info in DB_TEAMS.items():
            if t_info.get("parent_id") == current_id and t_id not in result:
                result.add(t_id)
                queue.append(t_id)
                
    return result

def get_visible_deals_for_user(user_emp_id: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    TIÊU CHÍ 3: Cây tổ chức quyết định phạm vi dữ liệu mà Trưởng nhóm nhìn thấy.
    
    Quy tắc phân quyền phạm vi dữ liệu (Data Visibility Scope):
    1. Giám đốc kinh doanh (Director): Nhìn thấy 100% dữ liệu toàn quốc.
    2. Trưởng nhóm (Team Leader):
       - Tìm các nhóm mà người này đang làm Trưởng nhóm.
       - Tập hợp toàn bộ các nhóm con cháu (subtree) của tất cả các nhóm đó.
       - Trưởng nhóm nhìn thấy toàn bộ Deals và Khách hàng thuộc các nhóm trong subtree này.
    3. Nhân viên bình thường (Sales Rep - không phải Trưởng nhóm):
       - Chỉ nhìn thấy các Deals do chính mình phụ trách (`assignee_id == user_emp_id`).
    
    Trả về: (visible_deals, scope_metadata)
    """
    user = DB_EMPLOYEES.get(user_emp_id)
    if not user:
        return [], {"scope_type": "UNKNOWN", "scope_teams": [], "total_accessible": 0}
    
    # 1. Trường hợp là Giám Đốc Kinh Doanh (Toàn quốc)
    if user.get("is_director", False):
        all_team_ids = set(DB_TEAMS.keys())
        visible_deals = copy.deepcopy(DB_DEALS)
        metadata = {
            "scope_type": "DIRECTOR_ALL",
            "scope_label": "Toàn Quyền Giám Đốc (Toàn Quốc)",
            "scope_teams": list(all_team_ids),
            "accessible_team_count": len(all_team_ids),
            "total_deals": len(visible_deals),
            "description": "Bạn có quyền Giám đốc kinh doanh: Xem toàn bộ dữ liệu của tất cả các chi nhánh và đội nhóm trên toàn quốc."
        }
        return visible_deals, metadata
    
    # 2. Kiểm tra xem người này có làm Trưởng nhóm ở nhóm nào không
    led_team_ids = [t_id for t_id, t in DB_TEAMS.items() if t.get("leader_id") == user_emp_id]
    
    if led_team_ids:
        # Tập hợp tất cả các nhóm con cháu của mọi nhóm mà người này phụ trách
        allowed_team_ids = set()
        for t_id in led_team_ids:
            allowed_team_ids.update(get_sub_tree_team_ids(t_id))
            
        visible_deals = [d for d in DB_DEALS if d["team_id"] in allowed_team_ids]
        
        led_team_names = [DB_TEAMS[tid]["name"] for tid in led_team_ids]
        all_accessible_team_names = [DB_TEAMS[tid]["name"] for tid in allowed_team_ids]
        
        metadata = {
            "scope_type": "TEAM_LEADER_SUBTREE",
            "scope_label": f"Phạm Vi Cây Tổ Chức: {', '.join(led_team_names)}",
            "scope_teams": list(allowed_team_ids),
            "accessible_team_names": all_accessible_team_names,
            "accessible_team_count": len(allowed_team_ids),
            "total_deals": len(visible_deals),
            "description": f"Bạn là Trưởng nhóm của: {', '.join(led_team_names)}. Bạn nhìn thấy toàn bộ dữ liệu của nhóm mình và {len(allowed_team_ids) - len(led_team_ids)} nhóm con cấp dưới."
        }
        return visible_deals, metadata
        
    # 3. Nhân viên thông thường: Chỉ thấy Deal của chính mình
    visible_deals = [d for d in DB_DEALS if d["assignee_id"] == user_emp_id]
    user_team = DB_TEAMS.get(user["team_id"])
    team_name = user_team["name"] if user_team else "Chưa gán"
    
    metadata = {
        "scope_type": "INDIVIDUAL_REP",
        "scope_label": "Phạm Vi Cá Nhân (Chuyên viên)",
        "scope_teams": [user["team_id"]] if user.get("team_id") else [],
        "accessible_team_names": [team_name],
        "accessible_team_count": 1,
        "total_deals": len(visible_deals),
        "description": f"Bạn là Chuyên viên thuộc nhóm '{team_name}'. Bạn chỉ nhìn thấy các cơ hội/hợp đồng do chính bạn trực tiếp phụ trách."
    }
    return visible_deals, metadata


def build_org_tree_hierarchy() -> List[Dict[str, Any]]:
    """
    Xây dựng cấu trúc cây lồng nhau (Nested Tree) phục vụ hiển thị sơ đồ tổ chức trực quan trên giao diện.
    Trả về danh sách các Root Nodes (thường là Khối Kinh Doanh HQ).
    """
    all_teams = get_all_teams()
    team_dict = {t["id"]: t for t in all_teams}
    
    # Thêm trường children cho mỗi node
    for t in team_dict.values():
        t["children"] = []
    
    root_nodes = []
    for t in team_dict.values():
        parent_id = t.get("parent_id")
        if not parent_id or parent_id not in team_dict:
            root_nodes.append(t)
        else:
            team_dict[parent_id]["children"].append(t)
            
    return root_nodes


def get_team_summary_metrics(team_id: str) -> Dict[str, Any]:
    """
    Tính toán số liệu tổng hợp (Rollup Metrics) cho một nhóm dựa trên toàn bộ subtree của nó:
      - Tổng doanh số từ các deal thành công / đang chạy
      - Tổng số lượng nhân viên trong toàn subtree
      - Danh sách khu vực địa lý bao phủ
    """
    subtree_ids = get_sub_tree_team_ids(team_id)
    
    deals = [d for d in DB_DEALS if d["team_id"] in subtree_ids]
    total_revenue = sum(d["value_vnd"] for d in deals)
    
    members = [emp for emp in DB_EMPLOYEES.values() if emp["team_id"] in subtree_ids]
    
    region_ids = {DB_TEAMS[tid]["region_id"] for tid in subtree_ids if tid in DB_TEAMS and DB_TEAMS[tid].get("region_id")}
    regions = [DB_REGIONS[rid] for rid in region_ids if rid in DB_REGIONS]
    
    return {
        "team_id": team_id,
        "subtree_team_count": len(subtree_ids),
        "total_members": len(members),
        "total_deals": len(deals),
        "total_revenue_vnd": total_revenue,
        "regions": regions
    }
