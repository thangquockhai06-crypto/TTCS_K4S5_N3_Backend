"""Tiện ích làm sạch chuỗi nhập chống tấn công XSS và ký tự độc hại."""
import html
import re

def sanitize_text(value: str) -> str:
    if not value or not isinstance(value, str):
        return value
    # Escape HTML tags
    escaped = html.escape(value.strip())
    # Chặn các script protocols
    cleaned = re.sub(r'javascript:', '', escaped, flags=re.IGNORECASE)
    return cleaned

def clean_phone_number(phone: str) -> str:
    if not phone:
        return ""
    # Giữ lại chỉ số và dấu +
    return re.sub(r'[^0-9+]', '', phone.strip())
