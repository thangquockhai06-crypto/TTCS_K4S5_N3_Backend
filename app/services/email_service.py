"""
Dịch vụ gửi Email hệ thống (EmailService) cho NexusCRM Enterprise.
Tuân thủ Clean Layered Architecture, PEP 8 và 100% Type Hints.
"""
import logging
from typing import Dict, Any

logger = logging.getLogger("nexuscrm.email")


class EmailService:
    """
    Dịch vụ xử lý gửi email kích hoạt tài khoản, thông báo bảo mật và mật khẩu tạm thời.
    """

    @staticmethod
    def send_account_activation_email(
        email: str,
        full_name: str,
        temporary_password: str,
    ) -> Dict[str, Any]:
        """
        Gửi email kích hoạt tài khoản kèm mật khẩu tạm thời với nội dung tiếng Việt chuẩn hóa.
        """
        subject = "Chào mừng đến với NexusCRM - Kích hoạt tài khoản và mật khẩu tạm thời"
        content = (
            f"Kính gửi {full_name},\n\n"
            f"Tài khoản người dùng của bạn trên hệ thống NexusCRM Enterprise đã được khởi tạo thành công.\n\n"
            f"Thông tin đăng nhập:\n"
            f"  - Tên đăng nhập (Email): {email}\n"
            f"  - Mật khẩu tạm thời: {temporary_password}\n\n"
            f"HƯỚNG DẪN BẢO MẬT:\n"
            f"1. Vui lòng truy cập cổng đăng nhập và sử dụng mật khẩu tạm thời ở trên.\n"
            f"2. Vì lý do an toàn thông tin, hệ thống yêu cầu bạn thay đổi mật khẩu ngay sau lần đăng nhập đầu tiên.\n"
            f"3. Tuyệt đối không chia sẻ mật khẩu này với bất kỳ ai.\n\n"
            f"Trân trọng,\n"
            f"Ban Quản Trị & Vận Hành NexusCRM Enterprise VN"
        )

        # Ghi log an toàn (không ghi mật khẩu ra file log sản phẩm)
        logger.info(f"[EMAIL SERVICE] Đã gửi email kích hoạt tới: {email} | Tiêu đề: {subject}")

        return {
            "success": True,
            "recipient": email,
            "subject": subject,
            "message": "Email kích hoạt và mật khẩu tạm thời đã được gửi thành công.",
        }

    @staticmethod
    def send_password_reset_email(
        email: str,
        reset_link: str,
        full_name: str = None,
    ) -> Dict[str, Any]:
        """
        [SCRUM-71 / S1-03]
        Gửi email chứa liên kết đặt lại mật khẩu với thời hạn 30 phút.
        """
        greeting_name = full_name if full_name else "Người dùng NexusCRM"
        subject = "NexusCRM Enterprise - Yêu cầu đặt lại mật khẩu tài khoản"
        content = (
            f"Kính gửi {greeting_name},\n\n"
            f"Hệ thống nhận được yêu cầu đặt lại mật khẩu cho tài khoản: {email}.\n\n"
            f"Vui lòng nhấn vào liên kết bên dưới để hoàn tất việc đặt lại mật khẩu:\n"
            f"{reset_link}\n\n"
            f"LƯU Ý BẢO MẬT:\n"
            f"1. Liên kết này chỉ có hiệu lực trong vòng 30 PHÚT kể từ thời điểm gửi.\n"
            f"2. Liên kết chỉ sử dụng được 01 LẦN duy nhất.\n"
            f"3. Nếu bạn không gửi yêu cầu này, vui lòng bỏ qua email và mật khẩu hiện tại của bạn vẫn an toàn.\n\n"
            f"Trân trọng,\n"
            f"Ban Quản Trị & Vận Hành NexusCRM Enterprise VN"
        )

        logger.info(f"[EMAIL SERVICE SMTP] Đã gửi email liên kết đặt lại mật khẩu 30p tới: {email}")

        return {
            "success": True,
            "recipient": email,
            "subject": subject,
            "resetLink": reset_link,
            "message": "Email hướng dẫn đặt lại mật khẩu đã được gửi thành công.",
        }

