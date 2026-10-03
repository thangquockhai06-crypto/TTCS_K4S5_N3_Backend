"""
Cơ sở dữ liệu mẫu và Quản lý Redis Token TTL 30 phút cho Subtask SCRUM-71 (Đặt lại mật khẩu)
Tuân thủ PEP 8 & Clean Architecture.
"""

import time
import secrets
from datetime import datetime
from typing import Optional, Dict, Any

# Hằng số chuẩn PEP 8 (UPPER_CASE_SNAKE)
TOKEN_EXPIRE_MINUTES: int = 30
TOKEN_EXPIRE_SECONDS: int = TOKEN_EXPIRE_MINUTES * 60  # 1800 giây

# Dữ liệu người dùng mẫu trong CSDL
SAMPLE_USERS: Dict[str, Dict[str, Any]] = {
    "admin@nexuscrm.vn": {
        "id": "USR-001",
        "full_name": "Nguyễn Văn Admin",
        "email": "admin@nexuscrm.vn",
        "password_hash": "$2b$12$eImiTXuWVxfM37uY4JANjOL.81F8R/Hj3Qy3B4fJmXz9m9x9x9x9x",  # Admin@123
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

# Giả lập Redis Store cho token đặt lại mật khẩu với TTL 30 phút
REDIS_TOKEN_STORE: Dict[str, Dict[str, Any]] = {}

# Nhật ký gửi email Celery Task / SMTP
SENT_EMAIL_LOGS = []


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Lấy thông tin người dùng theo email (chuẩn hóa chữ thường)."""
    if not email:
        return None
    return SAMPLE_USERS.get(email.strip().lower())


def save_reset_token(token: str, email: str, ttl_minutes: int = TOKEN_EXPIRE_MINUTES) -> str:
    """
    Sinh token secrets.token_urlsafe() và lưu vào Redis Store với TTL 30 phút.
    """
    expires_at = time.time() + (ttl_minutes * 60)
    REDIS_TOKEN_STORE[token] = {
        "email": email.strip().lower(),
        "created_at": datetime.now().isoformat(),
        "expires_at": expires_at
    }
    return token


def get_reset_token(token: str) -> Optional[str]:
    """
    Lấy email gắn liền với token. Trả về None nếu token không tồn tại hoặc đã hết hạn 30 phút.
    """
    if not token or token not in REDIS_TOKEN_STORE:
        return None

    entry = REDIS_TOKEN_STORE[token]
    if time.time() > entry["expires_at"]:
        # Đã hết hạn 30 phút -> tự động hủy token
        del REDIS_TOKEN_STORE[token]
        return None

    return entry["email"]


def delete_reset_token(token: str) -> bool:
    """
    Xóa token khỏi Redis sau khi dùng xong (Đảm bảo liên kết chỉ dùng 1 lần).
    """
    if token in REDIS_TOKEN_STORE:
        del REDIS_TOKEN_STORE[token]
        return True
    return False


def update_user_password(email: str, new_password_hash: str) -> bool:
    """Cập nhật mật khẩu mới cho người dùng."""
    user = get_user_by_email(email)
    if user:
        user["password_hash"] = new_password_hash
        return True
    return False
