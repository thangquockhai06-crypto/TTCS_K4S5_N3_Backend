"""
ỨNG DỤNG KHAI BÁO CƠ CẤU TỔ CHỨC KINH DOANH & PHẠM VI DỮ LIỆU
============================================================
Mã Nhiệm Vụ: SCRUM-83 / SCRUM-85
User Story:
  "Là Giám đốc kinh doanh, tôi muốn khai báo cơ cấu tổ chức kinh doanh,
   để phạm vi dữ liệu của trưởng nhóm bám đúng cây tổ chức thật."

Đáp ứng 100% 4 Tiêu chí chấp nhận (Description):
  1. Nhóm kinh doanh có cấu trúc cây, mỗi nhóm có một trưởng nhóm.
  2. Mỗi nhân viên thuộc đúng một nhóm tại một thời điểm.
  3. Cây tổ chức này quyết định phạm vi dữ liệu mà Trưởng nhóm nhìn thấy.
  4. Khai báo khu vực địa lý và gán khu vực cho nhóm.
============================================================
"""

import os
import sys

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
    get_all_teams,
    get_team,
    create_team,
    update_team,
    delete_team,
    build_org_tree_hierarchy,
    get_team_summary_metrics,
    get_sub_tree_team_ids,
    get_all_employees,
    get_employee,
    assign_employee_to_team,
    add_employee,
    get_all_regions,
    get_region,
    create_region,
    update_region,
    delete_region,
    get_visible_deals_for_user,
    reset_database,
    DB_EMPLOYEES,
    DB_TEAMS,
    DB_REGIONS,
    DB_DEALS
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "scrum-85-business-org-tree-secret-key-2026")


# ==============================================================================
# HÀM BỔ TRỢ: XÁC ĐỊNH NGƯỜI DÙNG & GÓC NHÌN ĐANG KIỂM THỬ
# ==============================================================================
def get_current_user():
    """
    Lấy thông tin người dùng đang trong phiên làm việc.
    Mặc định ban đầu là 'EMP001' (Trần Hải Đăng - Giám Đốc Kinh Doanh Toàn Quốc).
    """
    current_emp_id = session.get("current_emp_id", "EMP001")
    user = get_employee(current_emp_id)
    if not user:
        session["current_emp_id"] = "EMP001"
        user = get_employee("EMP001")
    return user


@app.context_processor
def inject_global_context():
    """Truyền các thông tin toàn cục vào mọi template giao diện."""
    current_user = get_current_user()
    all_employees = get_all_employees()
    all_regions = get_all_regions()
    all_teams = get_all_teams()
    
    # Danh sách các tài khoản tiêu biểu dùng cho thanh thử nghiệm (Testing Bar)
    key_actors = [
        {"id": "EMP001", "name": "Trần Hải Đăng", "role": "Giám Đốc Kinh Doanh (Toàn Quốc)", "tag": "Root / Full Scope"},
        {"id": "EMP002", "name": "Nguyễn Minh Tuấn", "role": "GĐ Chi Nhánh Miền Bắc", "tag": "Trưởng Nhóm Cấp 1"},
        {"id": "EMP003", "name": "Lê Thị Bích Hạnh", "role": "GĐ Chi Nhánh Miền Nam", "tag": "Trưởng Nhóm Cấp 1"},
        {"id": "EMP004", "name": "Phạm Quốc Dũng", "role": "Trưởng Nhóm Bán Lẻ Hà Nội", "tag": "Trưởng Nhóm Cấp 2"},
        {"id": "EMP007", "name": "Vũ Anh Tú", "role": "Chuyên Viên Kinh Doanh", "tag": "Chuyên Viên (Cá nhân)"}
    ]
    
    return {
        "current_user": current_user,
        "all_employees": all_employees,
        "all_regions": all_regions,
        "all_teams": all_teams,
        "key_actors": key_actors
    }


# ==============================================================================
# 1. TRANG CHÍNH: SƠ ĐỒ CÂY CƠ CẤU TỔ CHỨC (TIÊU CHÍ 1 & 4)
# ==============================================================================
@app.route("/")
def index():
    return redirect(url_for("org_tree_view"))


@app.route("/org-tree")
def org_tree_view():
    """
    Hiển thị sơ đồ cây cơ cấu tổ chức kinh doanh trực quan (Interactive Org Tree).
    Cho phép Giám đốc kinh doanh khai báo, chỉnh sửa, gán khu vực và bổ nhiệm trưởng nhóm.
    """
    tree_roots = build_org_tree_hierarchy()
    flat_teams = get_all_teams()
    regions = get_all_regions()
    employees = get_all_employees()
    
    # Tính toán số liệu thống kê tổng quan
    total_revenue_nationwide = sum(d["value_vnd"] for d in DB_DEALS)
    
    return render_template(
        "org_tree.html",
        tree_roots=tree_roots,
        flat_teams=flat_teams,
        regions=regions,
        employees=employees,
        total_revenue_nationwide=total_revenue_nationwide
    )


# ==============================================================================
# 2. TRANG KIỂM TRA PHẠM VI DỮ LIỆU CÂY TỔ CHỨC (TIÊU CHÍ 3)
# ==============================================================================
@app.route("/data-scope")
def data_scope_view():
    """
    TIÊU CHÍ 3: Cây tổ chức quyết định phạm vi dữ liệu mà Trưởng nhóm nhìn thấy.
    Trực quan hóa ma trận phân quyền và danh sách hợp đồng/deals nhìn thấy được theo từng vị trí.
    """
    current_user = get_current_user()
    visible_deals, scope_meta = get_visible_deals_for_user(current_user["id"])
    
    # Thống kê tổng doanh số nhìn thấy được
    visible_revenue = sum(d["value_vnd"] for d in visible_deals)
    
    # Lấy thông tin chi tiết các nhóm nằm trong phạm vi vs ngoài phạm vi
    all_teams = get_all_teams()
    in_scope_team_ids = set(scope_meta.get("scope_teams", []))
    
    # Bổ sung thông tin nhóm và nhân viên cho từng deal để hiển thị đẹp mắt
    enriched_deals = []
    for d in visible_deals:
        d_copy = dict(d)
        team = get_team(d["team_id"])
        d_copy["team_name"] = team["name"] if team else d["team_id"]
        assignee = get_employee(d["assignee_id"])
        d_copy["assignee_name"] = assignee["name"] if assignee else d["assignee_id"]
        region = get_region(d.get("region_id", ""))
        d_copy["region_name"] = region["name"] if region else "Chưa gán"
        d_copy["region_code"] = region["code"] if region else "N/A"
        d_copy["region_badge_color"] = region["badge_color"] if region else "#64748b"
        enriched_deals.append(d_copy)
        
    return render_template(
        "data_scope.html",
        deals=enriched_deals,
        scope_meta=scope_meta,
        visible_revenue=visible_revenue,
        all_teams=all_teams,
        in_scope_team_ids=in_scope_team_ids
    )


# ==============================================================================
# 3. TRANG QUẢN LÝ NHÂN SỰ & RÀNG BUỘC 1 NHÓM (TIÊU CHÍ 2)
# ==============================================================================
@app.route("/employees")
def employees_view():
    """
    TIÊU CHÍ 2: Mỗi nhân viên thuộc đúng một nhóm tại một thời điểm.
    Danh sách nhân viên, thông tin nhóm hiện tại và chức năng điều chuyển nhóm nhanh.
    """
    employees = get_all_employees()
    teams = get_all_teams()
    return render_template("employees.html", employees=employees, teams=teams)


@app.route("/employee/transfer", methods=["POST"])
def transfer_employee_action():
    """Xử lý điều chuyển nhân viên sang nhóm mới (tự động rời nhóm cũ)."""
    emp_id = request.form.get("emp_id")
    new_team_id = request.form.get("new_team_id")
    
    success, msg = assign_employee_to_team(emp_id, new_team_id)
    if success:
        flash(msg, "success")
    else:
        flash(msg, "danger")
    return redirect(url_for("employees_view"))


@app.route("/employee/add", methods=["POST"])
def add_employee_action():
    """Thêm nhân sự mới và gán vào đúng một nhóm."""
    emp_id = request.form.get("emp_id")
    name = request.form.get("name")
    role_title = request.form.get("role_title")
    team_id = request.form.get("team_id")
    email = request.form.get("email")
    phone = request.form.get("phone")
    
    success, msg = add_employee(emp_id, name, role_title, team_id, email, phone)
    if success:
        flash(msg, "success")
    else:
        flash(msg, "danger")
    return redirect(url_for("employees_view"))


# ==============================================================================
# 4. TRANG QUẢN LÝ KHU VỰC ĐỊA LÝ (TIÊU CHÍ 4)
# ==============================================================================
@app.route("/regions")
def regions_view():
    """
    TIÊU CHÍ 4: Khai báo khu vực địa lý và gán khu vực cho nhóm.
    Hiển thị danh sách khu vực và các nhóm kinh doanh đang phụ trách từng khu vực.
    """
    regions = get_all_regions()
    teams = get_all_teams()
    
    # Đếm số lượng nhóm và tính doanh số phụ trách theo từng khu vực
    for r in regions:
        assigned_teams = [t for t in teams if t.get("region_id") == r["id"]]
        r["assigned_teams"] = assigned_teams
        r["team_count"] = len(assigned_teams)
        
        # Doanh số tại khu vực
        region_deals = [d for d in DB_DEALS if d.get("region_id") == r["id"]]
        r["total_revenue"] = sum(d["value_vnd"] for d in region_deals)
        
    return render_template("regions.html", regions=regions)


@app.route("/region/create", methods=["POST"])
def create_region_action():
    """Khai báo khu vực địa lý mới."""
    region_id = request.form.get("region_id")
    name = request.form.get("name")
    code = request.form.get("code")
    provinces = request.form.get("provinces")
    description = request.form.get("description", "")
    badge_color = request.form.get("badge_color", "#2563eb")
    
    success, msg = create_region(region_id, name, code, provinces, description, badge_color)
    if success:
        flash(msg, "success")
    else:
        flash(msg, "danger")
    return redirect(url_for("regions_view"))


@app.route("/region/update/<region_id>", methods=["POST"])
def update_region_action(region_id):
    """Cập nhật thông tin khu vực địa lý."""
    name = request.form.get("name")
    code = request.form.get("code")
    provinces = request.form.get("provinces")
    description = request.form.get("description", "")
    badge_color = request.form.get("badge_color", "")
    
    success, msg = update_region(region_id, name, code, provinces, description, badge_color)
    if success:
        flash(msg, "success")
    else:
        flash(msg, "danger")
    return redirect(url_for("regions_view"))


@app.route("/region/delete/<region_id>", methods=["POST"])
def delete_region_action(region_id):
    """Xóa khu vực địa lý (chỉ xóa được nếu chưa gán cho nhóm nào)."""
    success, msg = delete_region(region_id)
    if success:
        flash(msg, "success")
    else:
        flash(msg, "danger")
    return redirect(url_for("regions_view"))


# ==============================================================================
# 5. CÁC HÀNH ĐỘNG QUẢN LÝ NHÓM KINH DOANH (TIÊU CHÍ 1 & 4)
# ==============================================================================
@app.route("/team/create", methods=["POST"])
def create_team_action():
    """Khai báo nhóm kinh doanh mới."""
    team_id = request.form.get("team_id")
    name = request.form.get("name")
    parent_id = request.form.get("parent_id")
    leader_id = request.form.get("leader_id")
    region_id = request.form.get("region_id")
    description = request.form.get("description", "")
    
    parent_val = parent_id if parent_id and parent_id.strip() else None
    
    success, msg = create_team(team_id, name, parent_val, leader_id, region_id, description)
    if success:
        flash(msg, "success")
    else:
        flash(msg, "danger")
    return redirect(url_for("org_tree_view"))


@app.route("/team/update/<team_id>", methods=["POST"])
def update_team_action(team_id):
    """Cập nhật nhóm kinh doanh (Kiểm tra chu trình và cập nhật trưởng nhóm, khu vực)."""
    name = request.form.get("name")
    parent_id = request.form.get("parent_id")
    leader_id = request.form.get("leader_id")
    region_id = request.form.get("region_id")
    description = request.form.get("description", "")
    
    parent_val = parent_id if parent_id and parent_id.strip() else None
    
    success, msg = update_team(team_id, name, parent_val, leader_id, region_id, description)
    if success:
        flash(msg, "success")
    else:
        flash(msg, "danger")
    return redirect(url_for("org_tree_view"))


@app.route("/team/delete/<team_id>", methods=["POST"])
def delete_team_action(team_id):
    """Xóa nhóm kinh doanh an toàn."""
    success, msg = delete_team(team_id)
    if success:
        flash(msg, "success")
    else:
        flash(msg, "danger")
    return redirect(url_for("org_tree_view"))


# ==============================================================================
# 6. TIỆN ÍCH CHUYỂN ĐỔI NGƯỜI DÙNG & RESET DỮ LIỆU
# ==============================================================================
@app.route("/switch-user/<emp_id>")
def switch_user_action(emp_id):
    """Chuyển đổi nhanh tài khoản đang kiểm thử để xem phạm vi dữ liệu tương ứng."""
    if emp_id in DB_EMPLOYEES:
        session["current_emp_id"] = emp_id
        flash(f"Đã chuyển sang góc nhìn của: {DB_EMPLOYEES[emp_id]['name']} ({DB_EMPLOYEES[emp_id]['role_title']})", "info")
    return redirect(request.referrer or url_for("data_scope_view"))


@app.route("/reset-data", methods=["POST"])
def reset_data_action():
    """Khôi phục dữ liệu mẫu ban đầu."""
    reset_database()
    flash("Đã khôi phục toàn bộ cơ cấu tổ chức và dữ liệu mẫu về trạng thái ban đầu.", "success")
    return redirect(url_for("org_tree_view"))


# ==============================================================================
# 7. XỬ LÝ LỖI (ERROR HANDLERS)
# ==============================================================================
@app.errorhandler(404)
def page_not_found(e):
    return render_template("errors/404.html"), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template("errors/500.html"), 500


# ==============================================================================
# KHỞI CHẠY MÁY CHỦ
# ==============================================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("=" * 72)
    print(" HỆ THỐNG KHAI BÁO CƠ CẤU TỔ CHỨC KINH DOANH & PHẠM VI DỮ LIỆU - SCRUM-85")
    print(" User Story: Khai báo cơ cấu tổ chức để phạm vi dữ liệu bám đúng cây tổ chức")
    print(" Tiêu chí: Cây tổ chức + Trưởng nhóm + 1 nhân viên 1 nhóm + Phạm vi dữ liệu + Khu vực")
    print(f" Máy chủ đang hoạt động tại: http://127.0.0.1:{port}")
    print("=" * 72)
    app.run(host="127.0.0.1", port=port, debug=True)
