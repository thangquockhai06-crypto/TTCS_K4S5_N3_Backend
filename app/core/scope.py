"""
Module định nghĩa các phạm vi dữ liệu (Data Scope) và ánh xạ Vai trò (Role) -> Phạm vi.
Tuân thủ PEP 8, 100% Type Hints và Clean Layered Architecture.
"""
from enum import Enum
from typing import Optional, Dict


class DataScope(str, Enum):
    """
    3 Phạm vi truy cập dữ liệu theo yêu cầu:
    - OWN: Chỉ truy cập bản ghi do chính mình phụ trách / sở hữu.
    - TEAM: Truy cập bản ghi thuộc các thành viên trong cùng nhóm (team).
    - ALL: Truy cập toàn bộ bản ghi được phép trong hệ thống.
    """
    OWN = "OWN"
    TEAM = "TEAM"
    ALL = "ALL"


# Bảng ánh xạ vai trò người dùng -> Data Scope
# Nguồn chân lý duy nhất (Single Source of Truth)
ROLE_SCOPE_MAPPING: Dict[str, DataScope] = {
    # Phạm vi ALL: Quản trị viên, Giám đốc kinh doanh, Phó chủ tịch
    "super admin": DataScope.ALL,
    "admin": DataScope.ALL,
    "sales director": DataScope.ALL,
    "vp of sales": DataScope.ALL,
    "director": DataScope.ALL,
    "giám đốc kinh doanh": DataScope.ALL,
    "quản trị viên": DataScope.ALL,

    # Phạm vi TEAM: Trưởng nhóm kinh doanh, Trưởng bộ phận RevOps, Quản lý
    "team leader": DataScope.TEAM,
    "sales leader": DataScope.TEAM,
    "revops lead": DataScope.TEAM,
    "sales manager": DataScope.TEAM,
    "manager": DataScope.TEAM,
    "lead": DataScope.TEAM,
    "trưởng nhóm": DataScope.TEAM,
    "trưởng phòng": DataScope.TEAM,

    # Phạm vi OWN: Nhân viên kinh doanh, Account Executive, Sales Rep
    "employee": DataScope.OWN,
    "account executive": DataScope.OWN,
    "sales rep": DataScope.OWN,
    "sales representative": DataScope.OWN,
    "nhân viên": DataScope.OWN,
    "nhân viên kinh doanh": DataScope.OWN,
}


def get_user_data_scope(user: Optional[object]) -> DataScope:
    """
    Xác định Data Scope hiệu lực từ thông tin người dùng được xác thực.
    Bảo mật phòng thủ (Defense-in-Depth):
    - Không tin tưởng frontend, chỉ căn cứ server-side role/data_scope.
    - Nếu có cấu hình data_scope riêng biệt trên User -> ưu tiên sử dụng.
    - Ngược lại tra cứu theo role.
    - Nếu không xác định được vai trò -> mặc định là OWN (quyền tối thiểu, không fail open).
    """
    if not user:
        return DataScope.OWN

    # 1. Kiểm tra cấu hình data_scope trực tiếp trên user (nếu có)
    custom_scope = getattr(user, "data_scope", None)
    if custom_scope:
        scope_str = str(custom_scope).strip().upper()
        if scope_str in DataScope.__members__:
            return DataScope[scope_str]

    # 2. Ánh xạ từ role
    role = getattr(user, "role", None)
    if not role:
        return DataScope.OWN

    normalized_role = str(role).strip().lower()
    return ROLE_SCOPE_MAPPING.get(normalized_role, DataScope.OWN)
