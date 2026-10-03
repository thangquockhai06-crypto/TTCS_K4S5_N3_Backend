"""
HỆ THỐNG MENU ĐIỀU HƯỚNG THEO PHÂN QUYỀN RBAC (FLASK WEB APP)
=============================================================
Mã Nhiệm Vụ: SCRUM-69 / SCRUM-74
Tiêu đề:
  "Là người dùng của hệ thống, tôi muốn thấy menu điều hướng đúng theo quyền của mình,
   để không bị rối bởi những chức năng mình không được dùng."

Đáp ứng 100% 3 Tiêu chí chấp nhận (Description):
  1. Mục menu không thuộc quyền thì không hiển thị (Lọc hoàn toàn khỏi DOM, bảo vệ backend 403)
  2. Hiển thị tên, vai trò và nhóm kinh doanh đang thuộc về (User Profile Card trực quan)
  3. Dùng được thuận tiện trên màn hình 360px (Responsive Mobile-First, Drawer cảm ứng, touch target >= 44px)
=============================================================
"""

import os
import sys
from functools import wraps

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
    abort,
    jsonify
)

from database import (
    ROLES,
    PERMISSION_LABELS,
    ALL_MENU_ITEMS,
    SAMPLE_USERS,
    SAMPLE_CUSTOMERS,
    SAMPLE_DEALS,
    SAMPLE_STAFF,
    get_user_menu,
    check_user_permission
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "scrum-74-rbac-menu-system-2026")

# ==============================================================================
# QUẢN LÝ PHIÊN LÀM VIỆC & NGƯỜI DÙNG HIỆN TẠI (CURRENT USER)
# ==============================================================================
def get_current_user():
    """
    Lấy thông tin người dùng đang đăng nhập từ Session.
    Mặc định ban đầu chọn 'sales_rep' (Chuyên viên kinh doanh - Lê Hoàng Phúc)
    để người dùng trải nghiệm ngay việc menu đã được lọc gọn gàng (chỉ có 3 mục)
    thay vì hiển thị tràn lan 7 mục.
    """
    username = session.get("current_username", "sales_rep")
    if username not in SAMPLE_USERS:
        username = "sales_rep"
        session["current_username"] = username
    return SAMPLE_USERS[username]

# Injected vào mọi template Jinja
@app.context_processor
def inject_global_template_context():
    current_user = get_current_user()
    user_menu = get_user_menu(current_user)
    return {
        "current_user": current_user,
        "user_menu": user_menu,
        "all_menu_items": ALL_MENU_ITEMS,
        "sample_users": SAMPLE_USERS,
        "roles": ROLES,
        "permission_labels": PERMISSION_LABELS,
        "active_endpoint": request.endpoint or ""
    }

# ==============================================================================
# DECORATOR BẢO VỆ ROUTE Ở BACKEND (@require_permission)
# ==============================================================================
def require_permission(permission_code):
    """
    Decorator kiểm tra quyền hạn ở tầng server.
    Nếu người dùng cố tình nhập trực tiếp URL trên trình duyệt mà không có quyền,
    hệ thống sẽ từ chối truy cập và kích hoạt mã lỗi HTTP 403 Forbidden.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not check_user_permission(user, permission_code):
                # Lưu thông tin quyền còn thiếu để trang 403 hiển thị chi tiết
                return render_template(
                    "errors/403.html",
                    missing_permission=permission_code,
                    missing_permission_label=PERMISSION_LABELS.get(permission_code, permission_code),
                    attempted_url=request.path
                ), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ==============================================================================
# CÁC ROUTE ĐIỀU HƯỚNG CHÍNH
# ==============================================================================
@app.route("/")
def index():
    return redirect(url_for("dashboard"))

@app.route("/dashboard")
@require_permission("view_dashboard")
def dashboard():
    user = get_current_user()
    user_menu = get_user_menu(user)
    
    # Tính toán ma trận đối chiếu quyền để hiển thị trực quan cho người kiểm thử
    matrix_data = []
    for item in ALL_MENU_ITEMS:
        perm = item["required_permission"]
        row = {
            "title": item["title"],
            "url": item["url"],
            "perm": perm,
            "roles_allowed": {
                r_key: perm in r_val["permissions"] for r_key, r_val in ROLES.items()
            },
            "is_visible_now": any(m["id"] == item["id"] for m in user_menu)
        }
        matrix_data.append(row)

    return render_template(
        "pages/dashboard.html",
        matrix_data=matrix_data,
        sample_deals=SAMPLE_DEALS[:3]
    )

@app.route("/customers")
@require_permission("manage_customers")
def customers():
    user = get_current_user()
    # Nếu là chuyên viên thì ưu tiên danh sách được phân công
    if user["role_code"] == "sales_rep":
        my_customers = [c for c in SAMPLE_CUSTOMERS if c["assigned_to"] == user["name"]]
    else:
        my_customers = SAMPLE_CUSTOMERS
    return render_template("pages/customers.html", customers=my_customers)

@app.route("/deals")
@require_permission("manage_deals")
def deals():
    return render_template("pages/deals.html", deals=SAMPLE_DEALS)

@app.route("/team-reports")
@require_permission("view_team_reports")
def team_reports():
    return render_template("pages/team_reports.html")

@app.route("/team-targets")
@require_permission("manage_team_targets")
def team_targets():
    return render_template("pages/team_targets.html")

@app.route("/staff-management")
@require_permission("manage_sales_staff")
def staff_management():
    return render_template("pages/staff_management.html", staff=SAMPLE_STAFF)

@app.route("/settings")
@require_permission("system_settings")
def settings():
    return render_template("pages/settings.html")

# ==============================================================================
# TÍNH NĂNG CHUYỂN ĐỔI VAI TRÒ NHANH (ROLE SWITCHER)
# ==============================================================================
@app.route("/switch-user/<username>")
def switch_user(username):
    """
    Chuyển đổi tức thì tài khoản/vai trò để kiểm tra tính động của Menu điều hướng
    và Thẻ thông tin cá nhân (Tên, vai trò, nhóm kinh doanh).
    """
    if username in SAMPLE_USERS:
        session["current_username"] = username
        user = SAMPLE_USERS[username]
        flash(f"Đã chuyển sang tài khoản: {user['name']} ({user['role_name']})", "success")
    else:
        flash("Tài khoản không hợp lệ!", "danger")
        
    next_page = request.args.get("next")
    # Nếu trang hiện tại bị mất quyền truy cập sau khi đổi vai trò thì về Dashboard
    if next_page:
        user = get_current_user()
        for item in ALL_MENU_ITEMS:
            if item["url"] == next_page and not check_user_permission(user, item["required_permission"]):
                return redirect(url_for("dashboard"))
        return redirect(next_page)
        
    return redirect(url_for("dashboard"))

# ==============================================================================
# API TRẢ VỀ DỮ LIỆU MENU ĐÃ ĐƯỢC LỌC (PHỤC VỤ TEST & DEBUG)
# ==============================================================================
@app.route("/api/menu")
def api_menu():
    """API JSON trả về danh sách các mục menu được phép nhìn thấy của người dùng hiện tại."""
    user = get_current_user()
    filtered_menu = get_user_menu(user)
    return jsonify({
        "user": {
            "username": user["username"],
            "name": user["name"],
            "role_name": user["role_name"],
            "role_code": user["role_code"],
            "business_group": user["business_group"]
        },
        "menu_items_count": len(filtered_menu),
        "menu_items": [
            {
                "id": item["id"],
                "title": item["title"],
                "url": item["url"],
                "required_permission": item["required_permission"]
            }
            for item in filtered_menu
        ]
    })

# ==============================================================================
# XỬ LÝ LỖI (ERROR HANDLERS) - DÙNG CHUNG GIAO DIỆN
# ==============================================================================
@app.errorhandler(403)
def forbidden_error(error):
    return render_template(
        "errors/403.html",
        missing_permission="custom_check",
        missing_permission_label="Quyền bị giới hạn",
        attempted_url=request.path
    ), 403

@app.errorhandler(404)
def not_found_error(error):
    return render_template("errors/404.html", attempted_url=request.path), 404

# ==============================================================================
# KHỞI CHẠY MÁY CHỦ
# ==============================================================================
if __name__ == "__main__":
    print("=" * 68)
    print(" HỆ THỐNG MENU ĐIỀU HƯỚNG THEO PHÂN QUYỀN RBAC - SCRUM-74")
    print(" Tiêu chí: Lọc sạch menu DOM + Tên/Vai trò/Nhóm + Chuẩn 360px mobile")
    print(" Đang chạy tại địa chỉ: http://127.0.0.1:5000")
    print("=" * 68)
    app.run(host="127.0.0.1", port=5000, debug=True)
