"""
ỨNG DỤNG QUẢN LÝ HỒ SƠ CÁ NHÂN & CHỮ KÝ EMAIL BÁO GIÁ
=====================================================
Mã Nhiệm Vụ: SCRUM-69 / SCRUM-80
User Story:
  "Là người dùng của hệ thống, tôi muốn xem và cập nhật hồ sơ cá nhân,
   để chữ ký email của tôi luôn đúng khi gửi báo giá cho khách."

Tiêu chí chấp nhận:
  1. Sửa được họ tên, số điện thoại, chữ ký email.
  2. Không tự đổi được email, nhóm và vai trò.
  3. Kiểm tra định dạng số điện thoại Việt Nam.
=====================================================
"""

import os
import sys
from datetime import datetime

# Đảm bảo in tiếng Việt trên console Windows không bị UnicodeEncodeError
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify
)

from database import (
    USERS_DB,
    SAMPLE_QUOTES,
    get_user,
    update_user_profile,
    validate_vietnam_phone,
    reset_database
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "scrum-80-user-profile-secret-2026")

# ==============================================================================
# HÀM BỔ TRỢ: XÁC ĐỊNH NGƯỜI DÙNG ĐANG ĐĂNG NHẬP
# ==============================================================================
def get_current_user():
    """
    Lấy thông tin người dùng đang trong phiên làm việc (Session).
    Mặc định ban đầu là 'sales_rep' (Chuyên viên kinh doanh - người trực tiếp gửi báo giá).
    """
    username = session.get("current_username", "sales_rep")
    user = get_user(username)
    if not user:
        session["current_username"] = "sales_rep"
        user = get_user("sales_rep")
    return user

@app.context_processor
def inject_global_context():
    """Truyền người dùng hiện tại và danh sách tài khoản mẫu vào mọi template."""
    current_user = get_current_user()
    all_users = [get_user(u) for u in USERS_DB.keys()]
    return {
        "current_user": current_user,
        "all_users": all_users,
        "now_year": datetime.now().year
    }

# ==============================================================================
# ROUTES CHÍNH CỦA ỨNG DỤNG
# ==============================================================================

@app.route("/")
def index():
    """Trang chủ tự động điều hướng sang trang Hồ sơ cá nhân."""
    return redirect(url_for("profile"))

@app.route("/profile", methods=["GET", "POST"])
def profile():
    """
    TRANG XEM VÀ CẬP NHẬT HỒ SƠ CÁ NHÂN (USER STORY SCRUM-80)
    - GET: Hiển thị form hồ sơ cá nhân và khu vực xem trước chữ ký email.
    - POST: Tiếp nhận yêu cầu cập nhật, áp dụng quy tắc nghiệp vụ 3 Tiêu chí.
    """
    user = get_current_user()
    
    if request.method == "POST":
        # 1. Thu thập dữ liệu gửi lên từ form
        form_data = request.form.to_dict()
        
        # 2. Thực hiện cập nhật an toàn qua tầng database
        # (Tại đây thực hiện kiểm tra Tiêu chí 1, Tiêu chí 2 và Tiêu chí 3)
        success, message, updated_user = update_user_profile(user["username"], form_data)
        
        if success:
            flash(message, "success")
            return redirect(url_for("profile"))
        else:
            flash(message, "danger")
            # Nếu có lỗi, giữ lại thông tin người dùng đã nhập trên form để không bị mất dữ liệu
            form_preview = {
                "full_name": form_data.get("full_name", user["full_name"]),
                "phone": form_data.get("phone", user["phone"]),
                "email_signature": form_data.get("email_signature", user["email_signature"])
            }
            return render_template("profile.html", user=user, form_preview=form_preview), 400
            
    return render_template("profile.html", user=user)

@app.route("/api/validate-phone", methods=["POST"])
def api_validate_phone():
    """API hỗ trợ kiểm tra định dạng số điện thoại Việt Nam nhanh cho phía client."""
    data = request.get_json(silent=True) or {}
    phone = data.get("phone", "")
    is_valid, formatted, error = validate_vietnam_phone(phone)
    return jsonify({
        "valid": is_valid,
        "formatted": formatted,
        "error": error
    })

@app.route("/quotes")
def quotes():
    """
    DANH SÁCH BÁO GIÁ GỬI KHÁCH HÀNG
    Nơi thể hiện giá trị cốt lõi của User Story:
    Chữ ký email cá nhân luôn đúng khi gửi báo giá cho khách hàng.
    """
    user = get_current_user()
    return render_template("quotes.html", quotes=SAMPLE_QUOTES, user=user)

@app.route("/quotes/<quote_id>/preview")
def quote_email_preview(quote_id):
    """
    XEM TRƯỚC BỨC THƯ EMAIL BÁO GIÁ KÈM CHỮ KÝ HIỆN TẠI
    Minh họa trực tiếp chữ ký email người dùng vừa cập nhật được chèn vào bức thư.
    """
    user = get_current_user()
    quote = next((q for q in SAMPLE_QUOTES if q["id"] == quote_id), None)
    if not quote:
        flash(f"Không tìm thấy báo giá mã {quote_id}.", "warning")
        return redirect(url_for("quotes"))
        
    return render_template("quote_preview.html", quote=quote, user=user)

@app.route("/quotes/<quote_id>/send", methods=["POST"])
def send_quote(quote_id):
    """Giả lập hành động gửi báo giá qua email kèm chữ ký mới nhất."""
    user = get_current_user()
    quote = next((q for q in SAMPLE_QUOTES if q["id"] == quote_id), None)
    if quote:
        quote["status"] = "Đã gửi thành công"
        flash(
            f"Đã gửi báo giá {quote['id']} tới {quote['customer_name']} ({quote['customer_email']}) "
            f"thành công kèm theo chữ ký email chuẩn xác của {user['full_name']}!",
            "success"
        )
    return redirect(url_for("quotes"))

@app.route("/switch-user/<username>")
def switch_user(username):
    """Chuyển đổi linh hoạt giữa các tài khoản mẫu để kiểm thử."""
    if username in USERS_DB:
        session["current_username"] = username
        flash(f"Đã chuyển sang phiên làm việc của: {USERS_DB[username]['full_name']} ({USERS_DB[username]['role_name']})", "info")
    else:
        flash("Người dùng không hợp lệ.", "danger")
    return redirect(url_for("profile"))

# ==============================================================================
# BỘ XỬ LÝ LỖI TRẢI NGHIỆM NGƯỜI DÙNG (HTTP 404 & HTTP 500)
# ==============================================================================

@app.errorhandler(404)
def page_not_found(error):
    """Xử lý lỗi 404 với giao diện ứng dụng đồng bộ."""
    return render_template("errors/404.html", requested_path=request.path), 404

@app.errorhandler(500)
def internal_server_error(error):
    """Xử lý lỗi 500 với giao diện ứng dụng đồng bộ."""
    return render_template("errors/500.html", error=error), 500

# ==============================================================================
# ĐIỂM KHỞI CHẠY MÁY CHỦ
# ==============================================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("=" * 70)
    print(" HỆ THỐNG QUẢN LÝ HỒ SƠ & CHỮ KÝ EMAIL BÁO GIÁ - SCRUM-80")
    print(" User Story: Xem & Cập nhật hồ sơ để chữ ký email luôn đúng khi gửi báo giá")
    print(" Tiêu chí: Sửa Tên/SĐT/Chữ ký + Khóa Email/Nhóm/Vai trò + Validate SĐT VN")
    print(f" Máy chủ đang hoạt động tại: http://127.0.0.1:{port}")
    print("=" * 70)
    app.run(host="0.0.0.0", port=port, debug=True)
