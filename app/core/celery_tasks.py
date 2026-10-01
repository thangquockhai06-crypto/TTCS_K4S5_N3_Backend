"""
Nhiệm vụ Celery Asynchronous Task xử lý gửi Email SMTP (SCRUM-71 / S1-03).
"""
import logging
from typing import Dict, Any, Optional
from app.services.email_service import EmailService

logger = logging.getLogger("nexuscrm.celery")

try:
    from celery import Celery
    celery_app = Celery("nexuscrm_tasks", broker="redis://localhost:6379/0", backend="redis://localhost:6379/0")
except Exception:
    celery_app = None


def send_password_reset_email_task(
    email: str,
    reset_link: str,
    full_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Celery task wrapper gửi email đặt lại mật khẩu SMTP.
    """
    logger.info(f"[CELERY TASK] Đang kích hoạt tiến trình gửi email SMTP tới: {email}")
    return EmailService.send_password_reset_email(
        email=email,
        reset_link=reset_link,
        full_name=full_name
    )


# Đăng ký Celery task nếu celery khả dụng
if celery_app:
    send_password_reset_email_task = celery_app.task(send_password_reset_email_task)
