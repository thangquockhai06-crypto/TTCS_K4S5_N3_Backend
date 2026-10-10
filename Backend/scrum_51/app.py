"""
Ứng Dụng Flask - Hệ Thống Tiếp Nhận Lead & Ràng Buộc SLA Phản Hồi
User Story: SCRUM-30 / SCRUM-51
Vai trò: Nhân viên kinh doanh (Sales Rep) & Trưởng nhóm (Team Lead)

Tiêu chí chấp nhận:
1. Nhân viên nhận lead thì lead chuyển sang "Đang chăm sóc"
2. Từ chối bắt buộc nhập lý do, lead quay lại hàng chờ phân bổ
3. Quá SLA phản hồi mà chưa liên hệ thì lead được gắn cờ và báo cho trưởng nhóm
"""

import os
import sys
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
    STATUS_PENDING_ALLOCATION,
    STATUS_ASSIGNED,
    STATUS_IN_CARE,
    STATUS_CONTACTED,
    STATUS_LABELS,
    STATUS_COLORS,
    ROLE_SALES_REP,
    ROLE_TEAM_LEAD,
    ROLE_DIRECTOR,
    DEFAULT_SLA_SECONDS,
    DEMO_FAST_SLA_SECONDS,
    PRODUCTION_SLA_SECONDS,
    DEFAULT_REJECTION_REASONS
)
from database import db, format_datetime, get_current_time
from sla_engine import sla_monitor

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "scrum-51-lead-sla-secret-key-2026")

# Khởi động SLA Monitor Worker chạy nền
sla_monitor.start()


# Filter Jinja2 format thời gian
@app.template_filter("vi_datetime")
def vi_datetime_filter(dt):
    return format_datetime(dt)


# Template globals
@app.context_processor
def inject_globals():
    # Giả lập người dùng hiện tại (mặc định usr-01: Nguyễn Văn Tuấn - Nhân viên kinh doanh)
    current_user_id = session.get("user_id", "usr-01")
    current_user = db.users.get(current_user_id, db.users["usr-01"])

    unread_notifs = len(db.get_notifications(recipient_id=current_user_id, unread_only=True))
    metrics = db.get_metrics()
    worker_status = sla_monitor.get_status()

    return {
        "db": db,
        "current_user": current_user,
        "all_users": db.users,
        "all_teams": db.teams,
        "unread_notifs": unread_notifs,
        "metrics": metrics,
        "worker_status": worker_status,
        "STATUS_LABELS": STATUS_LABELS,
        "STATUS_COLORS": STATUS_COLORS,
        "DEFAULT_REJECTION_REASONS": DEFAULT_REJECTION_REASONS,
        "ROLE_SALES_REP": ROLE_SALES_REP,
        "ROLE_TEAM_LEAD": ROLE_TEAM_LEAD,
        "ROLE_DIRECTOR": ROLE_DIRECTOR,
        "DEFAULT_SLA_SECONDS": DEFAULT_SLA_SECONDS,
        "now": get_current_time()
    }


# ==========================================
# 0. CHUYỂN ĐỔI NGƯỜI DÙNG GIẢ LẬP (PERSONA SWITCHER)
# ==========================================
@app.route("/switch-user/<user_id>")
def switch_user(user_id):
    if user_id in db.users:
        session["user_id"] = user_id
        user = db.users[user_id]
        flash(f"Đã chuyển sang vai trò: {user['name']} ({user['role_name']})", "info")
    return redirect(request.referrer or url_for("dashboard"))


# ==========================================
# 1. BẢNG ĐIỀU KHIỂN TỔNG QUAN (DASHBOARD)
# ==========================================
@app.route("/")
@app.route("/dashboard")
def dashboard():
    current_user_id = session.get("user_id", "usr-01")
    current_user = db.users.get(current_user_id, db.users["usr-01"])

    metrics = db.get_metrics()
    flagged_leads = db.get_leads(is_flagged=True)
    pending_alloc_leads = db.get_leads(filter_status=STATUS_PENDING_ALLOCATION)
    recent_leads = db.get_leads()[:6]
    recent_logs = db.get_audit_logs(limit=8)

    return render_template(
        "dashboard.html",
        metrics=metrics,
        flagged_leads=flagged_leads,
        pending_alloc_leads=pending_alloc_leads,
        recent_leads=recent_leads,
        recent_logs=recent_logs
    )


# ==========================================
# 2. GIAO DIỆN NHÂN VIÊN KINH DOANH (SALES REP VIEW)
# TIÊU CHÍ 1: Nhận lead -> Đang chăm sóc
# TIÊU CHÍ 2: Từ chối lead -> Bắt buộc nhập lý do -> Hàng chờ phân bổ
# ==========================================
@app.route("/my-leads")
def my_leads():
    current_user_id = session.get("user_id", "usr-01")
    user = db.users.get(current_user_id, db.users["usr-01"])

    # Lấy các lead thuộc về nhân viên này
    user_leads = db.get_leads(assigned_to_id=current_user_id)

    # Phân nhóm theo trạng thái
    leads_assigned = [l for l in user_leads if l["status"] == STATUS_ASSIGNED]
    leads_in_care = [l for l in user_leads if l["status"] == STATUS_IN_CARE]
    leads_contacted = [l for l in user_leads if l["status"] == STATUS_CONTACTED]

    return render_template(
        "sales_rep.html",
        user_leads=user_leads,
        leads_assigned=leads_assigned,
        leads_in_care=leads_in_care,
        leads_contacted=leads_contacted,
        user=user
    )


# -------------------------------------------------------------
# XỬ LÝ TIÊU CHÍ 1: NHẬN LEAD
# -------------------------------------------------------------
@app.route("/leads/<lead_id>/accept", methods=["POST"])
def accept_lead_route(lead_id):
    current_user_id = session.get("user_id", "usr-01")
    try:
        updated_lead = db.accept_lead(lead_id, current_user_id)
        flash(
            f"✅ Đã nhận lead '{updated_lead['name']}' thành công! Trạng thái đã chuyển sang: 'Đang chăm sóc'. Hãy khẩn trương liên hệ khách hàng trước hạn SLA!",
            "success"
        )
    except Exception as e:
        flash(f"❌ Lỗi khi nhận lead: {str(e)}", "danger")

    return redirect(request.referrer or url_for("my_leads"))


# -------------------------------------------------------------
# XỬ LÝ TIÊU CHÍ 2: TỪ CHỐI LEAD (BẮT BUỘC NHẬP LÝ DO)
# -------------------------------------------------------------
@app.route("/leads/<lead_id>/reject", methods=["POST"])
def reject_lead_route(lead_id):
    current_user_id = session.get("user_id", "usr-01")
    reason = request.form.get("reason", "").strip()

    # Ràng buộc chặt chẽ từ đề bài
    if not reason:
        flash(
            "⚠️ BẮT BUỘC NHẬP LÝ DO! Bạn không thể từ chối lead nếu không cung cấp lý do cụ thể.",
            "danger"
        )
        return redirect(request.referrer or url_for("my_leads"))

    try:
        updated_lead = db.reject_lead(lead_id, current_user_id, reason)
        flash(
            f"↩️ Đã từ chối lead '{updated_lead['name']}'. Lý do: '{reason}'. Lead đã được chuyển về 'Hàng chờ phân bổ' để Trưởng nhóm phân công lại.",
            "warning"
        )
    except Exception as e:
        flash(f"❌ Lỗi khi từ chối lead: {str(e)}", "danger")

    return redirect(request.referrer or url_for("my_leads"))


# -------------------------------------------------------------
# XỬ LÝ GHI NHẬN LIÊN HỆ (HOÀN THÀNH SLA PHẢN HỒI)
# -------------------------------------------------------------
@app.route("/leads/<lead_id>/contact", methods=["POST"])
def contact_lead_route(lead_id):
    current_user_id = session.get("user_id", "usr-01")
    channel = request.form.get("channel", "Điện thoại")
    notes = request.form.get("notes", "").strip()

    if not notes:
        flash("⚠️ Vui lòng nhập ghi chú tóm tắt nội dung cuộc trao đổi với khách hàng!", "danger")
        return redirect(request.referrer or url_for("my_leads"))

    try:
        updated_lead = db.log_contact(lead_id, current_user_id, channel, notes)
        flash(
            f"🎉 Đã ghi nhận liên hệ khách hàng '{updated_lead['name']}' qua kênh {channel}! Hoàn thành cam kết SLA phản hồi.",
            "success"
        )
    except Exception as e:
        flash(f"❌ Lỗi khi ghi nhận liên hệ: {str(e)}", "danger")

    return redirect(request.referrer or url_for("my_leads"))


# ==========================================
# 3. GIAO DIỆN TRƯỞNG NHÓM KINH DOANH (TEAM LEAD VIEW)
# TIÊU CHÍ 2: Lead từ chối nằm ở Hàng chờ phân bổ
# TIÊU CHÍ 3: Quá SLA phản hồi chưa liên hệ -> Gắn cờ và báo Trưởng nhóm
# ==========================================
@app.route("/team-lead")
def team_lead_view():
    current_user_id = session.get("user_id", "usr-03")
    user = db.users.get(current_user_id, db.users["usr-03"])

    # Hàng chờ phân bổ (gồm lead chưa ai nhận hoặc bị nhân viên từ chối quay lại)
    pending_alloc_leads = db.get_leads(filter_status=STATUS_PENDING_ALLOCATION)

    # Danh sách các lead bị gắn cờ quá hạn SLA
    flagged_leads = db.get_leads(is_flagged=True)

    # Toàn bộ thành viên trong nhóm để phân công
    team_members = [
        u for u in db.users.values()
        if u["role"] == ROLE_SALES_REP and u["team_id"] == user.get("team_id", "team-01")
    ]

    return render_template(
        "team_lead.html",
        pending_alloc_leads=pending_alloc_leads,
        flagged_leads=flagged_leads,
        team_members=team_members,
        user=user
    )


# Trưởng nhóm phân bổ lại lead
@app.route("/leads/<lead_id>/reassign", methods=["POST"])
def reassign_lead_route(lead_id):
    current_user_id = session.get("user_id", "usr-03")
    target_user_id = request.form.get("target_user_id")
    sla_seconds = request.form.get("sla_seconds", type=int) or DEFAULT_SLA_SECONDS

    if not target_user_id or target_user_id not in db.users:
        flash("⚠️ Vui lòng chọn nhân viên kinh doanh nhận phân bổ!", "danger")
        return redirect(request.referrer or url_for("team_lead_view"))

    try:
        updated_lead = db.reassign_lead(lead_id, target_user_id, current_user_id, sla_seconds)
        target_name = updated_lead["assigned_to_name"]
        flash(
            f"✅ Đã phân bổ lead '{updated_lead['name']}' cho nhân viên {target_name}. SLA phản hồi mới: {sla_seconds} giây.",
            "success"
        )
    except Exception as e:
        flash(f"❌ Lỗi khi phân bổ lại lead: {str(e)}", "danger")

    return redirect(request.referrer or url_for("team_lead_view"))


# ==========================================
# 4. TRUNG TÂM THÔNG BÁO CỦA TRƯỞNG NHÓM (NOTIFICATIONS)
# TIÊU CHÍ 3: Báo cho trưởng nhóm khi quá SLA hoặc từ chối
# ==========================================
@app.route("/notifications")
def notifications_view():
    current_user_id = session.get("user_id", "usr-03")
    notifs = db.get_notifications(recipient_id=current_user_id)
    return render_template("notifications.html", notifs=notifs)


@app.route("/notifications/mark-read", methods=["POST"])
def mark_read_route():
    current_user_id = session.get("user_id", "usr-03")
    db.mark_notifications_as_read(current_user_id)
    flash("Đã đánh dấu tất cả thông báo là đã đọc.", "info")
    return redirect(request.referrer or url_for("notifications_view"))


# ==========================================
# 5. CHI TIẾT LEAD & DANH SÁCH TOÀN BỘ LEADS
# ==========================================
@app.route("/leads")
def all_leads_view():
    status = request.args.get("status")
    assigned_to = request.args.get("assigned_to")
    is_flagged_param = request.args.get("is_flagged")
    search = request.args.get("q")

    is_flagged = None
    if is_flagged_param == "true":
        is_flagged = True
    elif is_flagged_param == "false":
        is_flagged = False

    leads = db.get_leads(
        filter_status=status or None,
        assigned_to_id=assigned_to or None,
        is_flagged=is_flagged,
        search=search or None
    )

    return render_template(
        "all_leads.html",
        leads=leads,
        current_status=status,
        current_assigned=assigned_to,
        current_flagged=is_flagged_param,
        search_query=search
    )


@app.route("/leads/<lead_id>")
def lead_detail(lead_id):
    lead = db.get_lead(lead_id)
    if not lead:
        flash(f"Không tìm thấy lead có mã '{lead_id}'.", "danger")
        return redirect(url_for("all_leads_view"))

    team_members = [
        u for u in db.users.values()
        if u["role"] == ROLE_SALES_REP
    ]

    return render_template("lead_detail.html", lead=lead, team_members=team_members)


@app.route("/leads/create", methods=["GET", "POST"])
def create_lead_route():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        company = request.form.get("company", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()
        industry = request.form.get("industry", "Công nghệ thông tin")
        region = request.form.get("region", "Miền Bắc")
        estimated_value = request.form.get("estimated_value", "100.000.000 đ")
        assigned_to_id = request.form.get("assigned_to_id") or None
        sla_seconds = request.form.get("sla_seconds", type=int) or DEFAULT_SLA_SECONDS

        if not name or not company or not phone:
            flash("Vui lòng nhập đầy đủ Tên, Tên Công ty và Số điện thoại!", "danger")
            return redirect(url_for("create_lead_route"))

        new_lead = db.create_lead(
            name=name,
            company=company,
            phone=phone,
            email=email,
            industry=industry,
            region=region,
            estimated_value=estimated_value,
            assigned_to_id=assigned_to_id,
            sla_seconds=sla_seconds
        )
        flash(f"Đã tạo thành công lead mới: {new_lead['id']} ({new_lead['name']})", "success")
        return redirect(url_for("lead_detail", lead_id=new_lead["id"]))

    team_members = [
        u for u in db.users.values()
        if u["role"] == ROLE_SALES_REP
    ]
    return render_template("create_lead.html", team_members=team_members)


# ==========================================
# 6. BỘ ĐIỀU KHIỂN MÔ PHỎNG & KIỂM THỬ NHANH (SIMULATOR)
# Phục vụ kiểm thử trực quan 3 tiêu chí đề bài mà không phải đợi lâu
# ==========================================
@app.route("/simulator")
def simulator_view():
    metrics = db.get_metrics()
    leads = db.get_leads()
    worker_status = sla_monitor.get_status()
    logs = db.get_audit_logs(limit=20)
    return render_template(
        "simulator.html",
        metrics=metrics,
        leads=leads,
        worker_status=worker_status,
        logs=logs
    )


# 1-Click tạo lead thử nghiệm siêu nhanh (SLA 30s)
@app.route("/simulator/create-fast-lead", methods=["POST"])
def sim_create_fast_lead():
    assigned_user = request.form.get("assigned_to_id", "usr-01")
    sla_sec = request.form.get("sla_seconds", type=int) or DEMO_FAST_SLA_SECONDS
    import random
    code = random.randint(100, 999)

    new_lead = db.create_lead(
        name=f"Khách hàng Test SLA #{code}",
        company=f"Công ty Cổ phần Thử Nghiệm #{code}",
        phone=f"0912 345 {code}",
        email=f"test{code}@example.com",
        industry="Công nghệ thông tin",
        region="Miền Bắc",
        estimated_value="350.000.000 đ",
        assigned_to_id=assigned_user,
        sla_seconds=sla_sec
    )
    flash(
        f"⚡ Đã tạo Lead thử nghiệm {new_lead['id']} gán cho {new_lead['assigned_to_name']} với thời hạn SLA siêu ngắn {sla_sec}s để bạn theo dõi đếm ngược!",
        "success"
    )
    return redirect(url_for("my_leads"))


# Tua nhanh thời gian để kích hoạt quá hạn SLA ngay lập tức
@app.route("/simulator/fast-forward/<lead_id>", methods=["POST"])
def sim_fast_forward_route(lead_id):
    try:
        updated = db.fast_forward_lead_sla(lead_id, forward_seconds=150)
        flash(
            f"⏩ Đã tua nhanh thời gian của lead {lead_id}! Lead đã quá hạn SLA, tự động BỊ GẮN CỜ 🚩 và gửi cảnh báo khẩn tới Trưởng nhóm.",
            "danger"
        )
    except Exception as e:
        flash(f"Lỗi tua nhanh: {str(e)}", "warning")
    return redirect(request.referrer or url_for("simulator_view"))


# Quét SLA thủ công ngay lập tức
@app.route("/simulator/scan-now", methods=["POST"])
def sim_scan_now():
    flagged = sla_monitor.scan_now()
    if flagged:
        flash(f"Đã phát hiện và gắn cờ {len(flagged)} lead vi phạm SLA phản hồi!", "danger")
    else:
        flash("Đã hoàn tất quét SLA. Không có lead mới nào bị quá hạn.", "info")
    return redirect(request.referrer or url_for("simulator_view"))


# Reset toàn bộ dữ liệu mẫu
@app.route("/simulator/reset-demo", methods=["POST"])
def sim_reset_demo():
    db.reset_demo_data()
    flash("🔄 Đã khôi phục toàn bộ dữ liệu kiểm thử mặc định ban đầu!", "info")
    return redirect(url_for("dashboard"))


# ==========================================
# 7. NHẬT KÝ KIỂM TOÁN (AUDIT LOGS)
# ==========================================
@app.route("/audit-logs")
def audit_logs_view():
    logs = db.get_audit_logs(limit=100)
    return render_template("audit_logs.html", logs=logs)


# ==========================================
# 8. REST APIS DÀNH CHO CLIENT AJAX POLLING
# ==========================================
@app.route("/api/leads/<lead_id>/sla-countdown")
def api_lead_sla_countdown(lead_id):
    lead = db.get_lead(lead_id)
    if not lead:
        return jsonify({"error": "Not found"}), 404

    now = get_current_time()
    deadline = lead.get("sla_deadline")
    is_flagged = lead.get("is_flagged", False)
    contacted = lead.get("contacted_at") is not None

    remaining_seconds = 0
    if deadline and not contacted:
        remaining_seconds = int((deadline - now).total_seconds())

    return jsonify({
        "lead_id": lead_id,
        "status": lead["status"],
        "is_flagged": is_flagged,
        "contacted": contacted,
        "remaining_seconds": remaining_seconds,
        "is_overdue": remaining_seconds < 0 if deadline else False
    })


@app.route("/api/notifications/unread-count")
def api_unread_notifications():
    current_user_id = session.get("user_id", "usr-03")
    count = len(db.get_notifications(recipient_id=current_user_id, unread_only=True))
    return jsonify({"unread_count": count})


if __name__ == "__main__":
    print("=" * 70)
    print(" HỆ THỐNG TIẾP NHẬN LEAD & GIÁM SÁT SLA PHẢN HỒI - SCRUM-51")
    print(" Khởi chạy tại: http://127.0.0.1:5000")
    print(" Luồng SLA Monitor Daemon: ĐANG CHẠY QUÉT TỰ ĐỘNG MỖI 2 GIÂY")
    print("=" * 70)
    app.run(host="0.0.0.0", port=5000, debug=True)
