"""
Ứng Dụng Web Flask - Quản Lý Quy Tắc Phân Bổ Lead Tự Động
User Story: SCRUM-30 / SCRUM-49
Vai trò: Giám đốc kinh doanh
Đáp ứng:
1. Phân bổ theo khu vực, theo ngành nghề, hoặc xoay vòng đều trong nhóm (Round-Robin).
2. Nhiều quy tắc xếp theo thứ tự ưu tiên, quy tắc đầu tiên khớp sẽ thắng (First-Match-Wins).
3. Lead không khớp quy tắc nào rơi vào hàng chờ để trưởng nhóm phân tay (Manual Queue).
4. Phân bổ chạy nền, hoàn tất trong vòng 5 phút kể từ khi lead vào (Background Worker).
"""

import os
import sys
import random

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
    REGIONS,
    INDUSTRIES,
    LEAD_SOURCES,
    CITIES_BY_REGION,
    LEAD_STATUS_PENDING,
    LEAD_STATUS_ASSIGNED,
    LEAD_STATUS_MANUAL_QUEUE,
    ASSIGNMENT_TYPE_ROUND_ROBIN,
    ASSIGNMENT_TYPE_DIRECT,
    SLA_LIMIT_SECONDS
)
from database import db, get_current_time, format_datetime
from engine import LeadAllocationEngine, allocation_worker

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "scrum-49-lead-allocation-secret-2026")

# Khởi động Background Worker ngay khi app chạy
allocation_worker.start()


# Helper lấy thông tin người dùng đang giả lập (Persona)
@app.context_processor
def inject_globals():
    current_user_id = session.get("user_id", "usr-01")  # Mặc định: Giám đốc kinh doanh
    current_user = db.users.get(current_user_id, db.users["usr-01"])
    metrics = db.get_metrics()
    worker_status = allocation_worker.get_status()
    return {
        "db": db,
        "all_teams": db.teams,
        "current_user": current_user,
        "all_users": db.users,
        "metrics": metrics,
        "worker_status": worker_status,
        "REGIONS": REGIONS,
        "INDUSTRIES": INDUSTRIES,
        "LEAD_SOURCES": LEAD_SOURCES,
        "SLA_LIMIT_SECONDS": SLA_LIMIT_SECONDS
    }


# ==========================================
# 1. TRANG DASHBOARD TỔNG QUAN
# ==========================================
@app.route("/")
@app.route("/dashboard")
def dashboard():
    metrics = db.get_metrics()
    recent_leads = db.get_leads()[:8]
    recent_logs = db.get_worker_logs(limit=8)
    rules = db.get_rules()
    return render_template(
        "dashboard.html",
        metrics=metrics,
        recent_leads=recent_leads,
        recent_logs=recent_logs,
        rules=rules
    )


# ==========================================
# 2. QUẢN LÝ QUY TẮC PHÂN BỔ (RULES)
# TIÊU CHÍ: Phân bổ theo khu vực, ngành nghề, xoay vòng đều
# TIÊU CHÍ: Thứ tự ưu tiên, quy tắc đầu tiên khớp sẽ thắng
# ==========================================
@app.route("/rules")
def rules_list():
    rules = db.get_rules()
    teams = list(db.teams.values())
    sales_reps = [u for u in db.users.values() if u.get("role") == "SALES_EXECUTIVE"]
    return render_template(
        "rules.html",
        rules=rules,
        teams=teams,
        sales_reps=sales_reps
    )


@app.route("/rules/add", methods=["POST"])
def rule_add():
    name = request.form.get("name", "").strip()
    priority = request.form.get("priority", type=int) or (len(db.rules) + 1)
    region = request.form.get("region", "Toàn quốc")
    industry = request.form.get("industry", "Tất cả ngành nghề")
    assignment_type = request.form.get("assignment_type", ASSIGNMENT_TYPE_ROUND_ROBIN)
    target_team_id = request.form.get("target_team_id")
    target_user_id = request.form.get("target_user_id")
    min_deal_value = float(request.form.get("min_deal_value") or 0)
    description = request.form.get("description", "").strip()

    if not name:
        flash("Vui lòng nhập tên quy tắc phân bổ!", "danger")
        return redirect(url_for("rules_list"))

    if assignment_type == ASSIGNMENT_TYPE_ROUND_ROBIN and not target_team_id:
        flash("Vui lòng chọn Nhóm kinh doanh để áp dụng xoay vòng Round-Robin!", "danger")
        return redirect(url_for("rules_list"))

    if assignment_type == ASSIGNMENT_TYPE_DIRECT and not target_user_id:
        flash("Vui lòng chọn Nhân viên kinh doanh để gán trực tiếp!", "danger")
        return redirect(url_for("rules_list"))

    new_rule = {
        "name": name,
        "priority": priority,
        "is_active": True,
        "region": region,
        "industry": industry,
        "assignment_type": assignment_type,
        "target_team_id": target_team_id if assignment_type == ASSIGNMENT_TYPE_ROUND_ROBIN else None,
        "target_user_id": target_user_id if assignment_type == ASSIGNMENT_TYPE_DIRECT else None,
        "min_deal_value": min_deal_value,
        "description": description or f"Phân bổ {region} - {industry}"
    }

    added = db.add_rule(new_rule)
    flash(f"Đã tạo thành công '{added['name']}' với Độ ưu tiên #{added['priority']}.", "success")
    return redirect(url_for("rules_list"))


@app.route("/rules/<rule_id>/edit", methods=["POST"])
def rule_edit(rule_id):
    name = request.form.get("name", "").strip()
    priority = request.form.get("priority", type=int)
    region = request.form.get("region")
    industry = request.form.get("industry")
    assignment_type = request.form.get("assignment_type")
    target_team_id = request.form.get("target_team_id")
    target_user_id = request.form.get("target_user_id")
    min_deal_value = float(request.form.get("min_deal_value") or 0)
    description = request.form.get("description", "").strip()

    update_payload = {
        "name": name,
        "priority": priority,
        "region": region,
        "industry": industry,
        "assignment_type": assignment_type,
        "target_team_id": target_team_id if assignment_type == ASSIGNMENT_TYPE_ROUND_ROBIN else None,
        "target_user_id": target_user_id if assignment_type == ASSIGNMENT_TYPE_DIRECT else None,
        "min_deal_value": min_deal_value,
        "description": description
    }
    db.update_rule(rule_id, update_payload)
    flash(f"Đã cập nhật cấu hình quy tắc {rule_id}.", "success")
    return redirect(url_for("rules_list"))


@app.route("/rules/<rule_id>/move", methods=["POST"])
def rule_move(rule_id):
    direction = request.form.get("direction", "up")
    success = db.move_rule_priority(rule_id, direction)
    if success:
        flash(f"Đã thay đổi thứ tự ưu tiên của quy tắc ({'Lên' if direction == 'up' else 'Xuống'}).", "info")
    return redirect(url_for("rules_list"))


@app.route("/rules/<rule_id>/toggle", methods=["POST"])
def rule_toggle(rule_id):
    new_state = db.toggle_rule_status(rule_id)
    state_str = "KÍCH HOẠT" if new_state else "TẠM TẮT"
    flash(f"Đã chuyển trạng thái quy tắc thành: {state_str}.", "info")
    return redirect(url_for("rules_list"))


@app.route("/rules/<rule_id>/delete", methods=["POST"])
def rule_delete(rule_id):
    db.delete_rule(rule_id)
    flash("Đã xóa quy tắc phân bổ khỏi hệ thống.", "warning")
    return redirect(url_for("rules_list"))


# ==========================================
# 3. QUẢN LÝ TẤT CẢ LEAD (LEADS LIST & FILTER)
# ==========================================
@app.route("/leads")
def leads_list():
    status_filter = request.args.get("status")
    region_filter = request.args.get("region")
    industry_filter = request.args.get("industry")

    all_leads = db.get_leads(status=status_filter if status_filter else None)

    if region_filter:
        all_leads = [l for l in all_leads if l.get("region") == region_filter]
    if industry_filter:
        all_leads = [l for l in all_leads if l.get("industry") == industry_filter]

    return render_template(
        "leads.html",
        leads=all_leads,
        status_filter=status_filter,
        region_filter=region_filter,
        industry_filter=industry_filter
    )


@app.route("/leads/add", methods=["POST"])
def lead_add():
    """Tạo lead đơn lẻ qua form"""
    name = request.form.get("name", "").strip()
    contact_person = request.form.get("contact_person", "").strip()
    phone = request.form.get("phone", "").strip()
    email = request.form.get("email", "").strip()
    region = request.form.get("region", "Miền Bắc")
    city = request.form.get("city", "")
    industry = request.form.get("industry", "Tài chính - Ngân hàng")
    estimated_value = float(request.form.get("estimated_value") or 50000000)
    source = request.form.get("source", "Website Form")
    notes = request.form.get("notes", "")

    if not name:
        flash("Vui lòng nhập tên công ty / khách hàng tiềm năng!", "danger")
        return redirect(url_for("leads_list"))

    new_lead = db.add_lead({
        "name": name,
        "contact_person": contact_person,
        "phone": phone,
        "email": email,
        "region": region,
        "city": city,
        "industry": industry,
        "estimated_value": estimated_value,
        "source": source,
        "notes": notes
    })

    # Đánh thức worker xử lý ngay
    allocation_worker.trigger_now()
    flash(f"Đã tiếp nhận lead '{new_lead['name']}' ({new_lead['code']}). Luồng chạy nền đang xử lý phân bổ trong vài giây...", "success")
    return redirect(url_for("leads_list"))


# ==========================================
# 4. HÀNG CHỜ PHÂN TAY DÀNH CHO TRƯỞNG NHÓM
# TIÊU CHÍ: Lead không khớp quy tắc nào rơi vào hàng chờ để trưởng nhóm phân tay
# ==========================================
@app.route("/manual-queue")
def manual_queue():
    queue_leads = db.get_manual_queue_leads()
    active_sales_reps = [
        u for u in db.users.values()
        if u.get("role") in ["SALES_EXECUTIVE", "TEAM_LEAD"] and u.get("status") == "ACTIVE"
    ]
    return render_template(
        "manual_queue.html",
        leads=queue_leads,
        sales_reps=active_sales_reps
    )


@app.route("/manual-queue/<lead_id>/assign", methods=["POST"])
def manual_assign(lead_id):
    target_user_id = request.form.get("target_user_id")
    notes = request.form.get("notes", "").strip()
    current_user_name = db.users.get(session.get("user_id", "usr-02"), {}).get("name", "Trưởng nhóm")

    if not target_user_id:
        flash("Vui lòng chọn nhân viên kinh doanh để phân công!", "danger")
        return redirect(url_for("manual_queue"))

    assigned = db.manual_assign_lead(
        lead_id=lead_id,
        target_user_id=target_user_id,
        assigner_name=current_user_name,
        notes=notes
    )

    if assigned:
        user_name = db.users[target_user_id]["name"]
        flash(f"Đã phân công thành công lead '{assigned['name']}' cho {user_name}.", "success")
    else:
        flash("Có lỗi khi phân công lead!", "danger")

    return redirect(url_for("manual_queue"))


@app.route("/manual-queue/re-evaluate", methods=["POST"])
def re_evaluate_queue():
    """Nút 'Thử khớp lại quy tắc' cho hàng chờ"""
    res = allocation_worker.re_evaluate_manual_queue()
    flash(
        f"Kết quả quét lại: {res['reassigned']} lead đã khớp quy tắc mới và được tự động phân bổ. "
        f"{res['still_manual']} lead vẫn ở hàng chờ.",
        "info"
    )
    return redirect(url_for("manual_queue"))


# ==========================================
# 5. QUẢN LÝ NHÂN SỰ & GIÁM SÁT XOAY VÒNG (ROUND-ROBIN)
# ==========================================
@app.route("/team-reps")
def team_reps():
    teams = list(db.teams.values())
    users_by_team = {}
    for t in teams:
        members = [db.users[uid] for uid in t["members"] if uid in db.users]
        leader = db.users.get(t["leader_id"])
        users_by_team[t["id"]] = {
            "team": t,
            "leader": leader,
            "members": members
        }
    return render_template(
        "team_reps.html",
        teams_data=users_by_team
    )


# ==========================================
# 6. NHẬT KÝ LUỒNG NỀN & ĐIỀU KHIỂN WORKER
# TIÊU CHÍ: Phân bổ chạy nền, hoàn tất trong 5 phút
# ==========================================
@app.route("/worker-monitor")
def worker_monitor():
    logs = db.get_worker_logs(limit=50)
    status = allocation_worker.get_status()
    return render_template(
        "worker_logs.html",
        logs=logs,
        status=status
    )


@app.route("/worker-action", methods=["POST"])
def worker_action():
    action = request.form.get("action")
    if action == "pause":
        allocation_worker.pause()
        flash("Đã tạm dừng luồng chạy nền.", "warning")
    elif action == "resume":
        allocation_worker.resume()
        flash("Đã tiếp tục luồng chạy nền.", "success")
    elif action == "trigger":
        count = allocation_worker.process_pending_leads()
        flash(f"Đã kích hoạt quét ngay lập tức. Đã phân bổ {count} lead đang chờ.", "info")
    return redirect(request.referrer or url_for("worker_monitor"))


# ==========================================
# 7. MÔ PHỎNG NẠP LEAD (SIMULATION TOOLS)
# Giúp Giám đốc kinh doanh và Tester kiểm tra trực quan
# ==========================================
@app.route("/simulate/single", methods=["POST"])
def simulate_single():
    """Mô phỏng 1 lead ngẫu nhiên đến từ website hoặc chiến dịch quảng cáo"""
    sample_companies = [
        ("Tập Đoàn FPT Software Đà Nẵng", "Miền Trung", "Đà Nẵng", "Công nghệ thông tin", 600000000),
        ("Ngân Hàng TMCP Quân Đội MB Bank", "Miền Bắc", "Hà Nội", "Tài chính - Ngân hàng", 450000000),
        ("Bất Động Sản Đất Xanh Miền Nam", "Miền Nam", "TP. Hồ Chí Minh", "Bất động sản", 800000000),
        ("Chuỗi Siêu Thị Co.op Mart Cần Thơ", "Miền Nam", "Cần Thơ", "Bán lẻ & Thương mại điện tử", 280000000),
        ("Nhà Máy Sản Xuất Dệt May Bình Dương", "Miền Nam", "Bình Dương", "Sản xuất & Chế biến", 320000000),
        ("Đại Học Quốc Tế RMIT Sài Gòn", "Miền Nam", "TP. Hồ Chí Minh", "Giáo dục & Đào tạo", 150000000),  # Không có rule -> Rơi vào hàng chờ
        ("Phòng Khám Đa Khoa Pasteur Đà Nẵng", "Miền Trung", "Đà Nẵng", "Y tế & Chăm sóc sức khỏe", 190000000) # Rơi vào hàng chờ
    ]

    comp_name, region, city, industry, est_val = random.choice(sample_companies)
    phone_rand = f"09{random.randint(10, 99)} {random.randint(100, 999)} {random.randint(100, 999)}"
    lead_source = random.choice(LEAD_SOURCES)

    new_lead = db.add_lead({
        "name": comp_name,
        "contact_person": "Đại diện mua hàng",
        "phone": phone_rand,
        "email": f"contact@{comp_name.lower().replace(' ', '')[:10]}.vn",
        "region": region,
        "city": city,
        "industry": industry,
        "estimated_value": est_val,
        "source": lead_source,
        "notes": "Lead mô phỏng tự động để kiểm thử luồng nền."
    })

    allocation_worker.trigger_now()
    flash(f"Đã mô phỏng nạp Lead '{new_lead['name']}' ({new_lead['code']}). Worker đang phân bổ tự động...", "success")
    return redirect(request.referrer or url_for("dashboard"))


@app.route("/simulate/batch", methods=["POST"])
def simulate_batch():
    """Mô phỏng nạp đồng thời 5 lead đa dạng để quan sát luồng nền phân bổ tức thì"""
    samples = [
        ("Chứng Khoán SSI Hải Phòng", "Miền Bắc", "Hải Phòng", "Tài chính - Ngân hàng", 300000000),
        ("Khu Đô Thị Ecopark Hưng Yên", "Miền Bắc", "Hà Nội", "Bất động sản", 950000000),
        ("Chuỗi Cà Phê The Coffee House", "Miền Nam", "TP. Hồ Chí Minh", "Bán lẻ & Thương mại điện tử", 180000000),
        ("Cơ Khí Chế Tạo Máy Long An", "Miền Nam", "Long An", "Sản xuất & Chế biến", 400000000),
        ("Trung Tâm Anh Ngữ VUS Nha Trang", "Miền Trung", "Nha Trang (Khánh Hòa)", "Giáo dục & Đào tạo", 120000000) # Dự kiến vào hàng chờ phân tay
    ]

    created_codes = []
    for comp_name, region, city, industry, est_val in samples:
        phone_rand = f"09{random.randint(10, 99)} {random.randint(100, 999)} {random.randint(100, 999)}"
        lead = db.add_lead({
            "name": comp_name,
            "contact_person": "Phòng Mua Hàng / Giám Đốc",
            "phone": phone_rand,
            "email": f"info@{comp_name.lower().replace(' ', '')[:8]}.com",
            "region": region,
            "city": city,
            "industry": industry,
            "estimated_value": est_val,
            "source": random.choice(LEAD_SOURCES),
            "notes": "Batch mô phỏng 5 lead thử nghiệm SLA 5 phút."
        })
        created_codes.append(lead["code"])

    allocation_worker.trigger_now()
    flash(f"Đã nạp hàng loạt 5 Lead mới ({', '.join(created_codes)}). Luồng chạy nền đang xử lý phân bổ...", "success")
    return redirect(request.referrer or url_for("dashboard"))


# ==========================================
# 8. CHUYỂN ĐỔI TÀI KHOẢN GIẢ LẬP (PERSONA SWITCHER)
# ==========================================
@app.route("/switch-user/<user_id>")
def switch_user(user_id):
    if user_id in db.users:
        session["user_id"] = user_id
        user = db.users[user_id]
        flash(f"Đã chuyển đổi sang tài khoản: {user['name']} ({user['role_name']}).", "info")
    return redirect(request.referrer or url_for("dashboard"))


# ==========================================
# 9. REST API JSON (CHO REAL-TIME POLLING & TEST TỰ ĐỘNG)
# ==========================================
@app.route("/api/status")
def api_status():
    return jsonify({
        "metrics": db.get_metrics(),
        "worker": allocation_worker.get_status(),
        "recent_logs": db.get_worker_logs(limit=5)
    })


@app.route("/api/leads")
def api_leads():
    status = request.args.get("status")
    return jsonify(db.get_leads(status=status))


@app.route("/api/rules")
def api_rules():
    return jsonify(db.get_rules())


if __name__ == "__main__":
    print("=" * 65)
    print(" HỆ THỐNG PHÂN BỔ LEAD TỰ ĐỘNG - TICKET SCRUM-30 / SCRUM-49")
    print(" Dành cho: Giám đốc kinh doanh & Trưởng nhóm")
    print(" Chạy tại: http://127.0.0.1:5000")
    print(" Luồng nền tự động hoàn tất phân bổ trong vòng vài phút (SLA 5 phút)")
    print("=" * 65)
    app.run(debug=True, host="127.0.0.1", port=5000)
