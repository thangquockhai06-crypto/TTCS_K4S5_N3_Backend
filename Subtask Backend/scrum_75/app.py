"""
ỨNG DỤNG QUẢN LÝ DOANH NGHIỆP & XỬ LÝ LỖI TRẢI NGHIỆM NGƯỜI DÙNG
================================================================
User Story: SCRUM-69 / SCRUM-75
Tiêu đề:
  "Là người dùng của hệ thống, tôi muốn nhận thông báo rõ ràng khi truy cập nhầm chỗ
   hoặc không đủ quyền, để biết mình nên làm gì tiếp thay vì gặp một trang trắng."

Tiêu chí chấp nhận (Description):
  1. Trang báo lỗi dùng chung giao diện ứng dụng (Thừa kế base.html, đồng bộ Header/Sidebar/CSS)
  2. Mỗi trang lỗi có một hành động gợi ý để quay lại luồng làm việc
================================================================
"""

import os
import sys
from datetime import datetime
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
    jsonify
)

from database import (
    ROLES,
    PERMISSION_LABELS,
    SAMPLE_USERS,
    SAMPLE_PROJECTS,
    FINANCIAL_DATA,
    ACCESS_REQUESTS,
    get_user,
    add_access_request
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "scrum-75-error-handling-secret-2026")

# ========================================================
# 1. HỆ THỐNG MENU ĐIỀU HƯỚNG CHUNG CỦA ỨNG DỤNG
# ========================================================
APP_MENU = [
    {
        "id": "dashboard",
        "title": "Bảng điều khiển",
        "icon": "layout-dashboard",
        "url": "/dashboard",
        "required_permission": "view_dashboard",
        "description": "Trung tâm chỉ huy & Báo cáo tổng quan",
        "public": True
    },
    {
        "id": "projects",
        "title": "Quản lý Dự án & Tiến độ",
        "icon": "folder-kanban",
        "url": "/projects",
        "required_permission": "view_projects",
        "description": "Theo dõi các dự án của phòng ban",
        "badge": f"{len(SAMPLE_PROJECTS)}"
    },
    {
        "id": "financial",
        "title": "Báo cáo Doanh số & Tài chính",
        "icon": "banknote",
        "url": "/financial-reports",
        "required_permission": "view_financial",
        "description": "Dữ liệu mật dành cho Trưởng phòng & Giám đốc",
        "badge": "Mật"
    },
    {
        "id": "settings",
        "title": "Cấu hình Bảo mật Hệ thống",
        "icon": "shield-check",
        "url": "/system-settings",
        "required_permission": "system_settings",
        "description": "Khu vực giới hạn chỉ dành riêng cho Giám đốc",
        "badge": "Admin"
    }
]

# ========================================================
# 2. XỬ LÝ USER HIỆN TẠI & PHÂN QUYỀN (RBAC)
# ========================================================
def get_current_user():
    """
    Lấy thông tin người dùng đang hoạt động trong phiên làm việc.
    Mặc định ban đầu đăng nhập vai trò 'staff' (Chuyên viên) để người kiểm thử
    dễ dàng trải nghiệm ngay tính năng chặn 403 khi vào menu Tài chính hoặc Cấu hình.
    """
    username = session.get("current_username", "staff")
    user = get_user(username)
    if not user:
        user = get_user("staff")
        session["current_username"] = "staff"
    return user

def require_permission(perm_code):
    """
    Decorator kiểm tra quyền hạn của Route:
    - Nếu đủ quyền: Cho phép thực thi view bình thường.
    - Nếu KHÔNG đủ quyền: Trả về trang lỗi 403 với status HTTP 403,
      DÙNG CHUNG GIAO DIỆN ỨNG DỤNG, chỉ rõ lý do và hành động khắc phục,
      hoàn toàn KHÔNG BAO GIỜ bị trang trắng.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if perm_code not in user.get("permissions", []):
                perm_title = PERMISSION_LABELS.get(perm_code, perm_code)
                return render_template(
                    "errors/403.html",
                    missing_permission_code=perm_code,
                    missing_permission_title=perm_title,
                    target_url=request.path,
                    current_user=user,
                    timestamp=datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                ), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.context_processor
def inject_app_globals():
    """Tự động truyền dữ liệu ứng dụng vào tất cả các template giao diện."""
    user = get_current_user()
    user_perms = set(user.get("permissions", []))
    
    # Đánh dấu các menu mà người dùng có quyền hoặc chưa đủ quyền
    processed_menu = []
    for item in APP_MENU:
        m = dict(item)
        m["has_access"] = item["required_permission"] in user_perms
        m["is_active"] = request.path == item["url"]
        processed_menu.append(m)

    return {
        "current_user": user,
        "app_menu": processed_menu,
        "sample_users": SAMPLE_USERS,
        "roles": ROLES,
        "current_year": datetime.now().year,
        "access_requests_count": len(ACCESS_REQUESTS)
    }

# ========================================================
# 3. BỘ BẮT LỖI TẬP TRUNG (ERROR HANDLERS) - ĐÁP ỨNG SCRUM-75
# ========================================================

@app.errorhandler(404)
def handle_404_error(error):
    """
    XỬ LÝ LỖI 404: TRUY CẬP NHẦM CHỖ (NOT FOUND)
    - Kế thừa giao diện chung của ứng dụng (base.html).
    - Cung cấp hành động gợi ý để quay lại luồng làm việc.
    - Không để người dùng bị trang trắng hoặc thông báo mặc định của trình duyệt.
    """
    user = get_current_user()
    return render_template(
        "errors/404.html",
        attempted_url=request.path,
        current_user=user,
        timestamp=datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        suggested_destinations=[
            {"title": "Bảng điều khiển chính", "url": "/dashboard", "icon": "layout-dashboard", "desc": "Trang chủ tác nghiệp chung"},
            {"title": "Danh sách Dự án", "url": "/projects", "icon": "folder-kanban", "desc": "Khu vực quản lý dự án & công việc"},
        ]
    ), 404

@app.errorhandler(403)
def handle_403_error(error):
    """
    XỬ LÝ LỖI 403: KHÔNG ĐỦ QUYỀN TRUY CẬP (FORBIDDEN)
    - Kế thừa giao diện chung của ứng dụng.
    - Hiển thị rõ: tên tài khoản, vai trò hiện tại, quyền còn thiếu.
    - Cung cấp hành động gợi ý: Đổi sang Giám đốc (test), Về Dashboard, Xin cấp quyền.
    """
    user = get_current_user()
    return render_template(
        "errors/403.html",
        missing_permission_code="system_access",
        missing_permission_title="Hạn chế quyền truy cập khu vực",
        target_url=request.path,
        current_user=user,
        timestamp=datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    ), 403

@app.errorhandler(500)
def handle_500_error(error):
    """
    XỬ LÝ LỖI 500: LỖI HỆ THỐNG MÁY CHỦ (INTERNAL SERVER ERROR)
    - Vẫn giữ nguyên layout chung của ứng dụng, không rơi vào trang trắng.
    - Có nút Thử lại (Reload) hoặc Về Bảng điều khiển an toàn.
    """
    user = get_current_user()
    return render_template(
        "errors/500.html",
        current_user=user,
        timestamp=datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    ), 500

# ========================================================
# 4. CÁC ROUTE CHỨC NĂNG CỦA HỆ THỐNG
# ========================================================

@app.route("/")
def index():
    """Điều hướng trang chủ đến Bảng điều khiển."""
    return redirect(url_for("dashboard"))

@app.route("/dashboard")
def dashboard():
    """
    Bảng điều khiển - Trang làm việc chung cho mọi người dùng.
    Tích hợp bộ hộp công cụ kiểm thử SCRUM-75 trực quan.
    """
    return render_template("pages/dashboard.html", projects=SAMPLE_PROJECTS[:2])

@app.route("/projects")
@require_permission("view_projects")
def projects():
    """
    Trang Quản lý Dự án & Tiến độ.
    Yêu cầu quyền: view_projects (Admin, Manager, Staff có quyền; Intern bị 403).
    """
    return render_template("pages/projects.html", projects=SAMPLE_PROJECTS)

@app.route("/financial-reports")
@require_permission("view_financial")
def financial_reports():
    """
    Trang Báo cáo Doanh số & Tài chính.
    Yêu cầu quyền: view_financial (Admin, Manager có quyền; Staff và Intern bị 403).
    """
    return render_template("pages/financial_reports.html", financial=FINANCIAL_DATA)

@app.route("/system-settings")
@require_permission("system_settings")
def system_settings():
    """
    Trang Cấu hình Bảo mật Hệ thống.
    Yêu cầu quyền: system_settings (Chỉ duy nhất Admin có quyền; Manager, Staff, Intern bị 403).
    """
    return render_template("pages/settings.html", access_requests=ACCESS_REQUESTS)

# ========================================================
# 5. CÁC ROUTE HỖ TRỢ KIỂM THỬ TỨC THÌ (TEST SUITE)
# ========================================================

@app.route("/switch-role/<username>")
def switch_role(username):
    """Đổi nhanh người dùng để kiểm thử các cấp độ phân quyền."""
    if username in SAMPLE_USERS:
        session["current_username"] = username
        flash(f"Đã chuyển sang tài khoản: {SAMPLE_USERS[username]['name']} ({SAMPLE_USERS[username]['role_code'].upper()})", "success")
    else:
        flash("Tài khoản không hợp lệ!", "error")
    
    # Quay lại trang hiện tại hoặc về Dashboard
    referrer = request.referrer or url_for("dashboard")
    return redirect(referrer)

@app.route("/trigger-test-404")
def trigger_test_404():
    """Chủ động chuyển hướng đến một URL không tồn tại để kiểm thử lỗi 404."""
    return redirect("/duong-dan-nay-chac-chan-khong-ton-tai-12345")

@app.route("/trigger-test-403")
def trigger_test_403():
    """Chủ động truy cập trang Cấu hình để thử lỗi 403 nếu tài khoản không phải Admin."""
    return redirect(url_for("system_settings"))

@app.route("/trigger-test-500")
def trigger_test_500():
    """Chủ động kích hoạt lỗi 500 để chứng minh không bị trang trắng."""
    raise Exception("Lỗi mô phỏng kiểm thử Exception 500!")

@app.route("/api/request-access", methods=["POST"])
def api_request_access():
    """API tiếp nhận yêu cầu xin cấp quyền khi người dùng gặp 403."""
    target_url = request.form.get("target_url", "/system-settings")
    reason = request.form.get("reason", "")
    user = get_current_user()
    
    req = add_access_request(user["username"], target_url, reason)
    return jsonify({
        "success": True,
        "message": f"Yêu cầu {req['id']} đã được gửi tới Giám đốc phê duyệt thành công!",
        "request": req
    })

# ========================================================
# 6. KHỞI CHẠY MÁY CHỦ PHÁT TRIỂN
# ========================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("\n" + "=" * 65)
    print(" HỆ THỐNG QUẢN LÝ DOANH NGHIỆP - USER STORY SCRUM-75")
    print(" Báo lỗi 404 & 403 dùng chung giao diện - Không bị trang trắng")
    print(f" Địa chỉ truy cập: http://127.0.0.1:{port}")
    print("=" * 65 + "\n")
    app.run(host="127.0.0.1", port=port, debug=True)
