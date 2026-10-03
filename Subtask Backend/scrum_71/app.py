"""
ỨNG DỤNG QUẢN LÝ DOANH NGHIỆP - XỬ LÝ ĐẶT LẠI MẬT KHẨU QUA EMAIL (SCRUM-71)
========================================================================
User Story: SCRUM-71
Tiêu đề:
  "Là người dùng của hệ thống, tôi muốn đặt lại mật khẩu khi quên thông qua email,
   để tự lấy lại quyền truy cập khi đang đi gặp khách."

Tiêu chí chấp nhận (Description):
  1. Nhập email nhận được liên kết đặt lại có hiệu lực 30 phút
  2. Liên kết chỉ dùng được một lần
  3. Email không tồn tại vẫn hiển thị cùng một thông báo (Anti-Enumeration)

Quy chuẩn kỹ thuật (S1-03):
  POST /api/v1/auth/forgot-password: sinh token secrets.token_urlsafe(),
  lưu Redis TTL 30p; Celery task gửi email SMTP
========================================================================
"""

import os
import sys
import secrets
from typing import Dict, Any

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from flask import Flask, request, jsonify, render_template_string

from database import (
    get_user_by_email,
    save_reset_token,
    get_reset_token,
    delete_reset_token,
    update_user_password,
    SENT_EMAIL_LOGS,
    TOKEN_EXPIRE_MINUTES
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "scrum-71-password-reset-secret-2026")


GENERIC_FORGOT_PASSWORD_MESSAGE = (
    "Nếu email tồn tại trong hệ thống, chúng tôi đã gửi hướng dẫn đặt lại mật khẩu có hiệu lực trong 30 phút."
)


@app.route("/", methods=["GET"])
def index():
    """Trang thông tin tổng quan Subtask SCRUM-71."""
    html_content = """
    <!DOCTYPE html>
    <html lang="vi">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>SCRUM-71: Đặt lại mật khẩu qua Email</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 40px; background-color: #f8fafc; color: #1e293b; }
            .card { background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); max-width: 800px; margin: 0 auto; }
            h1 { color: #2563eb; margin-top: 0; }
            .badge { display: inline-block; background: #e0e7ff; color: #4338ca; padding: 4px 12px; border-radius: 20px; font-weight: 600; font-size: 14px; }
            ul { line-height: 1.8; }
            code { background: #f1f5f9; color: #0f172a; padding: 2px 6px; border-radius: 4px; font-family: monospace; }
            .endpoint { background: #ecfdf5; border-left: 4px solid #10b981; padding: 12px; margin: 12px 0; font-family: monospace; }
        </style>
    </head>
    <body>
        <div class="card">
            <span class="badge">SCRUM-71 / S1-03</span>
            <h1>Hệ thống Đặt lại mật khẩu qua Email (Password Reset)</h1>
            <p>User Story: <i>"Là người dùng của hệ thống, tôi muốn đặt lại mật khẩu khi quên thông qua email, để tự lấy lại quyền truy cập khi đang đi gặp khách."</i></p>
            <h3>Tiêu chí chấp nhận đã hoàn thành:</h3>
            <ul>
                <li>✅ Nhập email nhận được liên kết đặt lại có hiệu lực 30 phút.</li>
                <li>✅ Liên kết chỉ sử dụng được 01 lần duy nhất.</li>
                <li>✅ Email không tồn tại vẫn hiển thị cùng một thông báo (Anti-Enumeration).</li>
            </ul>
            <h3>API Endpoints:</h3>
            <div class="endpoint">POST /api/v1/auth/forgot-password</div>
            <div class="endpoint">POST /api/v1/auth/reset-password</div>
        </div>
    </body>
    </html>
    """
    return render_template_string(html_content)


@app.route("/api/v1/auth/forgot-password", methods=["POST"])
def forgot_password_api():
    """
    [SCRUM-71 / S1-03] Endpoint gửi email yêu cầu đặt lại mật khẩu.
    - Sinh token: secrets.token_urlsafe()
    - Lưu Redis TTL 30 phút
    - Celery Task gửi email SMTP
    - Anti-Enumeration: Trả về cùng thông báo chung
    """
    data = request.get_json() or {}
    email = data.get("email", "").strip()

    if not email:
        return jsonify({"message": "Vui lòng nhập địa chỉ email công ty."}), 400

    user = get_user_by_email(email)

    if user:
        # 1. Sinh token URL safe bằng secrets
        reset_token = secrets.token_urlsafe(32)

        # 2. Lưu Redis với TTL 30 phút (1800 giây)
        save_reset_token(reset_token, email, ttl_minutes=TOKEN_EXPIRE_MINUTES)

        # 3. Giả lập Celery Task gửi email SMTP
        reset_link = f"http://localhost:5000/reset-password?token={reset_token}"
        email_entry = {
            "recipient": user["email"],
            "full_name": user["full_name"],
            "reset_link": reset_link,
            "token": reset_token,
            "ttl_minutes": TOKEN_EXPIRE_MINUTES,
            "status": "SENT_VIA_CELERY_SMTP"
        }
        SENT_EMAIL_LOGS.append(email_entry)

    # Anti-Enumeration: Luôn trả về cùng một thông báo an toàn
    return jsonify({
        "message": GENERIC_FORGOT_PASSWORD_MESSAGE,
        "success": True
    }), 200


@app.route("/api/v1/auth/reset-password", methods=["POST"])
def reset_password_api():
    """
    [SCRUM-71 / S1-03] Endpoint xác nhận đặt lại mật khẩu với token.
    - Kiểm tra token còn hiệu lực trong Redis (30 phút)
    - Cập nhật mật khẩu mới
    - Hủy token ngay sau khi dùng (chỉ dùng 1 lần)
    """
    data = request.get_json() or {}
    token = data.get("token", "").strip()
    new_password = data.get("new_password") or data.get("newPassword")

    if not token:
        return jsonify({"message": "Mã đặt lại mật khẩu không hợp lệ."}), 400

    if not new_password or len(str(new_password)) < 6:
        return jsonify({"message": "Mật khẩu mới phải có tối thiểu 6 ký tự."}), 400

    email = get_reset_token(token)

    if not email:
        return jsonify({"message": "Liên kết đặt lại mật khẩu không hợp lệ hoặc đã hết hạn (30 phút)."}), 400

    # Cập nhật mật khẩu mới cho người dùng
    update_user_password(email, str(new_password))

    # Xóa token khỏi Redis -> Đảm bảo liên kết chỉ dùng được 01 lần
    delete_reset_token(token)

    return jsonify({
        "message": "Mật khẩu của bạn đã được đặt lại thành công. Vui lòng đăng nhập với mật khẩu mới.",
        "success": True
    }), 200


if __name__ == "__main__":
    print("[SCRUM-71 Backend Server] Đang khởi chạy tại http://127.0.0.1:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
