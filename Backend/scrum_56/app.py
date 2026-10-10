"""
Ứng Dụng Flask - Hệ Thống Danh Sách Lead Với Bộ Lọc Đa Chiều & Bộ Lọc Lưu Sẵn
Ticket: SCRUM-30 / SCRUM-56
Vai trò: Nhân viên kinh doanh (Sales Representative)

Tiêu chí chấp nhận:
1. Lọc theo trạng thái, nguồn, phân loại nóng ấm lạnh, người phụ trách, khoảng thời gian.
2. Lead quá SLA hiển thị nổi bật.
3. Lưu và đặt tên cho bộ lọc hay dùng.
"""

import os
import sys
import json
import copy
from datetime import datetime

if sys.platform == "win32":
    try:
        import io
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
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

from config import (
    TICKET_ID,
    PARENT_EPIC,
    STATUS_NEW,
    STATUS_ASSIGNED,
    STATUS_IN_CARE,
    STATUS_CONTACTED,
    STATUS_QUALIFIED,
    STATUS_CONVERTED,
    STATUS_LOST,
    STATUS_LABELS,
    STATUS_BADGE_CLASSES,
    SOURCES,
    SOURCE_ICONS,
    TEMP_HOT,
    TEMP_WARM,
    TEMP_COLD,
    TEMPERATURES,
    TEMP_LABELS,
    TEMP_BADGE_CLASSES,
    SLA_ON_TIME,
    SLA_NEAR_DUE,
    SLA_OVERDUE,
    ROLE_SALES_REP,
    ROLE_TEAM_LEAD,
    ROLE_DIRECTOR,
    ROLE_LABELS,
    DEFAULT_PORT
)
from database import (
    db,
    format_currency,
    format_datetime,
    format_date
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "scrum-56-smart-lead-filters-key-2026")


# Jinja2 Template Filters
@app.template_filter("vi_currency")
def vi_currency_filter(amount):
    return format_currency(amount)


@app.template_filter("vi_datetime")
def vi_datetime_filter(dt):
    return format_datetime(dt)


@app.template_filter("vi_date")
def vi_date_filter(dt):
    return format_date(dt)


# Globals
@app.context_processor
def inject_globals():
    current_user_id = session.get("user_id", "usr-01")
    current_user = db.users.get(current_user_id, db.users["usr-01"])
    kpis = db.get_kpi_counts(current_user_id)

    return {
        "db": db,
        "current_user": current_user,
        "all_users": db.users,
        "kpis": kpis,
        "TICKET_ID": TICKET_ID,
        "PARENT_EPIC": PARENT_EPIC,
        "STATUS_LABELS": STATUS_LABELS,
        "STATUS_BADGE_CLASSES": STATUS_BADGE_CLASSES,
        "SOURCES": SOURCES,
        "SOURCE_ICONS": SOURCE_ICONS,
        "TEMPERATURES": TEMPERATURES,
        "TEMP_LABELS": TEMP_LABELS,
        "TEMP_BADGE_CLASSES": TEMP_BADGE_CLASSES,
        "TEMP_HOT": TEMP_HOT,
        "TEMP_WARM": TEMP_WARM,
        "TEMP_COLD": TEMP_COLD,
        "SLA_OVERDUE": SLA_OVERDUE,
        "now": datetime.now()
    }


# =============================================================================
# 0. CHUYỂN ĐỔI NGƯỜI DÙNG GIẢ LẬP (PERSONA SWITCHER)
# =============================================================================
@app.route("/switch-user/<user_id>")
def switch_user(user_id):
    if user_id in db.users:
        session["user_id"] = user_id
        flash(f"Đã chuyển sang tài khoản: {db.users[user_id]['name']} ({db.users[user_id]['role_name']})", "info")
    return redirect(request.referrer or url_for("leads_list_view"))


# =============================================================================
# 1. TRANG DANH SÁCH LEAD CHÍNH (VỚI BỘ LỌC ĐA CHIỀU & BỘ LỌC LƯU SẴN)
# =============================================================================
@app.route("/")
@app.route("/leads")
def leads_list_view():
    current_user_id = session.get("user_id", "usr-01")
    saved_filters = db.get_saved_filters(current_user_id)

    # 1. Kiểm tra xem người dùng có đang chọn một bộ lọc lưu sẵn (Saved Filter) không
    selected_filter_id = request.args.get("filter_id")
    active_filter = None

    criteria = {}

    # Nếu người dùng bấm vào một Saved Filter
    if selected_filter_id:
        active_filter = db.saved_filters.get(selected_filter_id)
        if active_filter:
            criteria = copy.deepcopy(active_filter.get("criteria", {}))
    # Nếu lần đầu mở trang mà không truyền tham số, kích hoạt bộ lọc mặc định (Default View on Login)
    elif not request.args:
        default_filter = next((f for f in saved_filters if f.get("is_default")), None)
        if default_filter:
            selected_filter_id = default_filter["id"]
            active_filter = default_filter
            criteria = copy.deepcopy(default_filter.get("criteria", {}))

    # 2. Hoặc nhận các tham số lọc tự do từ thanh công cụ đa chiều
    if not selected_filter_id:
        if request.args.get("status"):
            criteria["status"] = request.args.get("status")
        if request.args.get("source"):
            criteria["source"] = request.args.get("source")
        if request.args.get("temperature"):
            criteria["temperature"] = request.args.get("temperature")
        if request.args.get("assigned_to"):
            criteria["assigned_to"] = request.args.get("assigned_to")
        if request.args.get("date_preset"):
            criteria["date_preset"] = request.args.get("date_preset")
        if request.args.get("from_date"):
            criteria["from_date"] = request.args.get("from_date")
        if request.args.get("to_date"):
            criteria["to_date"] = request.args.get("to_date")
        if request.args.get("is_sla_overdue") == "true":
            criteria["is_sla_overdue"] = True
        if request.args.get("call_today") == "true":
            criteria["call_today"] = True
        if request.args.get("search"):
            criteria["search"] = request.args.get("search")

    # 3. Thực thi động cơ lọc
    leads = db.filter_leads(criteria, user_id=current_user_id)

    return render_template(
        "leads_list.html",
        leads=leads,
        saved_filters=saved_filters,
        selected_filter_id=selected_filter_id,
        active_filter=active_filter,
        criteria=criteria
    )


# =============================================================================
# 2. QUẢN LÝ BỘ LỌC LƯU SẴN (TIÊU CHÍ 3: LƯU VÀ ĐẶT TÊN CHO BỘ LỌC HAY DÙNG)
# =============================================================================
@app.route("/saved-filters/create", methods=["POST"])
def saved_filter_create():
    current_user_id = session.get("user_id", "usr-01")
    filter_name = request.form.get("name", "").strip()
    filter_icon = request.form.get("icon", "📌")
    is_default = request.form.get("is_default") == "true"

    if not filter_name:
        flash("Vui lòng nhập tên cho bộ lọc!", "danger")
        return redirect(request.referrer or url_for("leads_list_view"))

    # Đóng gói các tiêu chí lọc hiện tại
    criteria = {}
    if request.form.get("status"):
        criteria["status"] = request.form.get("status")
    if request.form.get("source"):
        criteria["source"] = request.form.get("source")
    if request.form.get("temperature"):
        criteria["temperature"] = request.form.get("temperature")
    if request.form.get("assigned_to"):
        criteria["assigned_to"] = request.form.get("assigned_to")
    if request.form.get("date_preset"):
        criteria["date_preset"] = request.form.get("date_preset")
    if request.form.get("from_date"):
        criteria["from_date"] = request.form.get("from_date")
    if request.form.get("to_date"):
        criteria["to_date"] = request.form.get("to_date")
    if request.form.get("is_sla_overdue") == "true":
        criteria["is_sla_overdue"] = True
    if request.form.get("call_today") == "true":
        criteria["call_today"] = True
    if request.form.get("focus_morning_calling") == "true":
        criteria["focus_morning_calling"] = True

    try:
        new_filter = db.save_filter(
            name=filter_name,
            criteria=criteria,
            user_id=current_user_id,
            icon=filter_icon,
            is_default=is_default
        )
        flash(f"🎉 Đã lưu bộ lọc thành công: '{new_filter['name']}'!", "success")
        return redirect(url_for("leads_list_view", filter_id=new_filter["id"]))
    except Exception as e:
        flash(f"Lỗi khi lưu bộ lọc: {str(e)}", "danger")
        return redirect(request.referrer or url_for("leads_list_view"))


@app.route("/saved-filters/<filter_id>/delete", methods=["POST"])
def saved_filter_delete(filter_id):
    current_user_id = session.get("user_id", "usr-01")
    if db.delete_filter(filter_id, user_id=current_user_id):
        flash("Đã xóa bộ lọc thành công!", "info")
    else:
        flash("Không tìm thấy bộ lọc cần xóa!", "warning")
    return redirect(url_for("leads_list_view"))


@app.route("/saved-filters/<filter_id>/set-default", methods=["POST"])
def saved_filter_set_default(filter_id):
    current_user_id = session.get("user_id", "usr-01")
    try:
        updated = db.set_default_filter(filter_id, user_id=current_user_id)
        flash(f"Đã đặt bộ lọc '{updated['name']}' làm mặc định khi mở máy buổi sáng!", "success")
    except Exception as e:
        flash(str(e), "danger")
    return redirect(url_for("leads_list_view", filter_id=filter_id))


# =============================================================================
# 3. GHI NHẬN CUỘC GỌI VÀ GIẢI PHÓNG QUÁ HẠN SLA
# =============================================================================
@app.route("/leads/<lead_id>/call", methods=["POST"])
def lead_record_call(lead_id):
    current_user_id = session.get("user_id", "usr-01")
    notes = request.form.get("notes", "").strip()
    next_call_date = request.form.get("next_call_date", "").strip()

    try:
        db.record_call(
            lead_id=lead_id,
            notes=notes,
            next_call_date=next_call_date,
            user_id=current_user_id
        )
        flash(f"📞 Đã ghi nhận cuộc gọi cho Lead {lead_id} và hoàn thành cam kết SLA!", "success")
    except Exception as e:
        flash(f"Lỗi: {str(e)}", "danger")

    return redirect(request.referrer or url_for("leads_list_view"))


# =============================================================================
# 4. CHI TIẾT LEAD
# =============================================================================
@app.route("/leads/<lead_id>")
def lead_detail_view(lead_id):
    lead = db.leads.get(lead_id)
    if not lead:
        flash(f"Không tìm thấy Lead {lead_id}!", "danger")
        return redirect(url_for("leads_list_view"))

    lead_data = copy.deepcopy(lead)
    sla_info = db.calculate_sla_status(lead_data)
    lead_data["sla"] = sla_info

    return render_template("lead_detail.html", lead=lead_data)


# =============================================================================
# 5. REST APIs
# =============================================================================
@app.route("/api/leads")
def api_leads():
    criteria = request.args.to_dict()
    leads = db.filter_leads(criteria)
    return jsonify({"success": True, "count": len(leads), "leads": leads})


@app.route("/api/saved-filters")
def api_saved_filters():
    current_user_id = session.get("user_id", "usr-01")
    filters = db.get_saved_filters(current_user_id)
    return jsonify({"success": True, "filters": filters})


# =============================================================================
# 6. RESET DATA
# =============================================================================
@app.route("/reset-data")
def reset_data():
    db.reset_demo_data()
    flash("Đã đặt lại dữ liệu ban đầu!", "info")
    return redirect(url_for("leads_list_view"))


if __name__ == "__main__":
    print("=" * 70)
    print("  HỆ THỐNG DANH SÁCH LEAD & BỘ LỌC LƯU SẴN - TICKET SCRUM-56")
    print(f"  Khởi chạy máy chủ tại: http://127.0.0.1:{DEFAULT_PORT}")
    print("=" * 70)
    app.run(host="127.0.0.1", port=DEFAULT_PORT, debug=True)
