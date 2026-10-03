"""
Cơ sở dữ liệu mẫu và Quản lý phiên đăng nhập cho Subtask SCRUM-72 (Đổi mật khẩu)
Tuân thủ PEP 8 & Clean Architecture.
"""

from typing import Optional, Dict, Any, List

# Dữ liệu người dùng mẫu trong CSDL
SAMPLE_USERS: Dict[str, Dict[str, Any]] = {
    "admin@nexuscrm.vn": {
        "id": "USR-001",
        "full_name": "Nguyễn Văn Admin",
        "email": "admin@nexuscrm.vn",
        "password_hash": "$2b$12$eImiTXuWVxfM37uY4JANjOL.81F8R/Hj3Qy3B4fJmXz9m9x9x9x9x",
        "role": "admin",
        "status": "active"
    },
    "sales.lead@nexuscrm.vn": {
        "id": "USR-002",
        "full_name": "Lê Thị Trưởng Nhóm",
        "email": "sales.lead@nexuscrm.vn",
        "password_hash": "$2b$12$eImiTXuWVxfM37uY4JANjOL.81F8R/Hj3Qy3B4fJmXz9m9x9x9x9x",
        "role": "manager",
        "status": "active"
    },
    "saleman@nexuscrm.vn": {
        "id": "USR-003",
        "full_name": "Trần Văn Sales",
        "email": "saleman@nexuscrm.vn",
        "password_hash": "$2b$12$eImiTXuWVxfM37uY4JANjOL.81F8R/Hj3Qy3B4fJmXz9m9x9x9x9x",
        "role": "staff",
        "status": "active"
    }
}

# Danh sách các phiên đăng nhập (Refresh Tokens / Sessions) lưu trên Redis/CSDL
ACTIVE_SESSIONS: List[Dict[str, Any]] = [
    {"user_id": "USR-003", "session_id": "SESS-101", "device": "Chrome Windows", "is_revoked": False},
    {"user_id": "USR-003", "session_id": "SESS-102", "device": "iPhone iOS App", "is_revoked": False},
    {"user_id": "USR-003", "session_id": "SESS-103", "device": "iPad Safari", "is_revoked": False},
]


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Lấy thông tin người dùng theo email."""
    if not email:
        return None
    return SAMPLE_USERS.get(email.strip().lower())


def update_user_password(email: str, new_password_hash: str) -> bool:
    """Cập nhật mật khẩu mới cho người dùng."""
    user = get_user_by_email(email)
    if user:
        user["password_hash"] = new_password_hash
        return True
    return False


def revoke_other_sessions(user_id: str, keep_session_id: Optional[str] = None) -> int:
    """
    Thu hồi tất cả các phiên đăng nhập khác của người dùng ngoại trừ phiên hiện tại.
    """
    revoked_count = 0
    for sess in ACTIVE_SESSIONS:
        if sess["user_id"] == user_id:
            if keep_session_id and sess["session_id"] == keep_session_id:
                continue
            if not sess["is_revoked"]:
                sess["is_revoked"] = True
                revoked_count += 1
    return revoked_count
