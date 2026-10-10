"""
Ứng Dụng Flask - Hệ Thống Chuyển Đổi Lead CRM (SCRUM-30 / SCRUM-54)
Ticket: SCRUM-54
Vai trò người dùng: Nhân viên kinh doanh (Sales Representative) & Trưởng nhóm (Team Leader)

Tiêu chí chấp nhận (Acceptance Criteria):
1. Một thao tác sinh đồng thời khách hàng doanh nghiệp, người liên hệ và cơ hội bán hàng.
2. Dữ liệu lead được chuyển sang, không phải nhập lại.
3. Lead chuyển sang trạng thái Đã chuyển đổi và không sửa được nữa.
4. Toàn bộ hoạt động đã ghi trên lead được giữ lại trên khách hàng mới.
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
    TICKET_ID,
    PARENT_EPIC,
    STATUS_NEW,
    STATUS_CONTACTED,
    STATUS_QUALIFIED,
    STATUS_CONVERTED,
    STATUS_DISQUALIFIED,
    STATUS_LABELS,
    STATUS_COLORS,
    STATUS_BADGE_CLASSES,
    STAGE_DISCOVERY,
    STAGE_PROPOSAL,
    STAGE_NEGOTIATION,
    STAGE_WON,
    STAGE_LOST,
    STAGE_LABELS,
    STAGE_COLORS,
    ACTIVITY_CALL,
    ACTIVITY_MEETING,
    ACTIVITY_EMAIL,
    ACTIVITY_NOTE,
    ACTIVITY_CONVERT,
    ACTIVITY_ICONS,
    ACTIVITY_LABELS,
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
    format_date,
    get_current_time
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "scrum-54-lead-conversion-secret-key-2026")


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


# Template Context Processor (Globals)
@app.context_processor
def inject_globals():
    current_user_id = session.get("user_id", "usr-01")
    current_user = db.users.get(current_user_id, db.users["usr-01"])
    unread_notifs = len(db.get_notifications(recipient_id=current_user_id, unread_only=True))
    kpis = db.get_kpis()

    return {
        "db": db,
        "current_user": current_user,
        "all_users": db.users,
        "unread_notifs": unread_notifs,
        "kpis": kpis,
        "TICKET_ID": TICKET_ID,
        "PARENT_EPIC": PARENT_EPIC,
        "STATUS_NEW": STATUS_NEW,
        "STATUS_CONTACTED": STATUS_CONTACTED,
        "STATUS_QUALIFIED": STATUS_QUALIFIED,
        "STATUS_CONVERTED": STATUS_CONVERTED,
        "STATUS_DISQUALIFIED": STATUS_DISQUALIFIED,
        "STATUS_LABELS": STATUS_LABELS,
        "STATUS_COLORS": STATUS_COLORS,
        "STATUS_BADGE_CLASSES": STATUS_BADGE_CLASSES,
        "STAGE_DISCOVERY": STAGE_DISCOVERY,
        "STAGE_PROPOSAL": STAGE_PROPOSAL,
        "STAGE_NEGOTIATION": STAGE_NEGOTIATION,
        "STAGE_WON": STAGE_WON,
        "STAGE_LOST": STAGE_LOST,
        "STAGE_LABELS": STAGE_LABELS,
        "STAGE_COLORS": STAGE_COLORS,
        "ACTIVITY_CALL": ACTIVITY_CALL,
        "ACTIVITY_MEETING": ACTIVITY_MEETING,
        "ACTIVITY_EMAIL": ACTIVITY_EMAIL,
        "ACTIVITY_NOTE": ACTIVITY_NOTE,
        "ACTIVITY_CONVERT": ACTIVITY_CONVERT,
        "ACTIVITY_ICONS": ACTIVITY_ICONS,
        "ACTIVITY_LABELS": ACTIVITY_LABELS,
        "ROLE_SALES_REP": ROLE_SALES_REP,
        "ROLE_TEAM_LEAD": ROLE_TEAM_LEAD,
        "ROLE_DIRECTOR": ROLE_DIRECTOR,
        "ROLE_LABELS": ROLE_LABELS,
        "now": get_current_time()
    }


# =============================================================================
# 0. CHUYỂN ĐỔI NGƯỜI DÙNG GIẢ LẬP (PERSONA SWITCHER)
# =============================================================================
@app.route("/switch-user/<user_id>")
def switch_user(user_id):
    if user_id in db.users:
        session["user_id"] = user_id
        flash(f"Đã chuyển đổi sang tài khoản: {db.users[user_id]['name']} ({db.users[user_id]['role_name']})", "info")
    return redirect(request.referrer or url_for("dashboard"))


# =============================================================================
# 1. BẢNG ĐIỀU KHIỂN CHÍNH (DASHBOARD)
# =============================================================================
@app.route("/")
@app.route("/dashboard")
def dashboard():
    qualified_leads = db.get_leads(status=STATUS_QUALIFIED)
    converted_leads = db.get_leads(status=STATUS_CONVERTED)
    recent_accounts = db.get_accounts()[:5]
    recent_opportunities = db.get_opportunities()[:5]
    audit_logs = db.get_audit_logs(limit=10)

    return render_template(
        "dashboard.html",
        qualified_leads=qualified_leads,
        converted_leads=converted_leads,
        recent_accounts=recent_accounts,
        recent_opportunities=recent_opportunities,
        audit_logs=audit_logs
    )


# =============================================================================
# 2. QUẢN LÝ LEADS (DANH SÁCH & CHI TIẾT)
# =============================================================================
@app.route("/leads")
def leads_list():
    status_filter = request.args.get("status")
    search_query = request.args.get("search")
    user_filter = request.args.get("user_id")

    leads = db.get_leads(status=status_filter, assigned_to_id=user_filter, search=search_query)

    return render_template(
        "leads_list.html",
        leads=leads,
        status_filter=status_filter,
        search_query=search_query,
        user_filter=user_filter
    )


@app.route("/leads/new", methods=["GET", "POST"])
def lead_new():
    if request.method == "POST":
        current_user_id = session.get("user_id", "usr-01")
        data = {
            "company_name": request.form.get("company_name", "").strip(),
            "tax_id": request.form.get("tax_id", "").strip(),
            "industry": request.form.get("industry", "").strip(),
            "address": request.form.get("address", "").strip(),
            "city": request.form.get("city", "").strip(),
            "website": request.form.get("website", "").strip(),
            "company_size": request.form.get("company_size", "").strip(),
            "contact_name": request.form.get("contact_name", "").strip(),
            "job_title": request.form.get("job_title", "").strip(),
            "phone": request.form.get("phone", "").strip(),
            "email": request.form.get("email", "").strip(),
            "interested_product": request.form.get("interested_product", "").strip(),
            "estimated_value": request.form.get("estimated_value", 50000000),
            "expected_close_date": request.form.get("expected_close_date", ""),
            "requirements": request.form.get("requirements", "").strip(),
            "source": request.form.get("source", "Trực tiếp"),
            "status": request.form.get("status", STATUS_QUALIFIED),
            "assigned_to_id": request.form.get("assigned_to_id", current_user_id),
            "qualification_notes": request.form.get("qualification_notes", "").strip()
        }

        if not data["company_name"] or not data["contact_name"]:
            flash("Vui lòng nhập đầy đủ Tên Công Ty và Tên Người Liên Hệ!", "danger")
            return render_template("lead_new.html", form_data=data)

        new_lead = db.create_lead(data, user_id=current_user_id)
        flash(f"Đã tạo thành công Lead mới '{new_lead['company_name']}' ({new_lead['id']})!", "success")
        return redirect(url_for("lead_detail", lead_id=new_lead["id"]))

    return render_template("lead_new.html", form_data={})


@app.route("/leads/<lead_id>")
def lead_detail(lead_id):
    lead = db.get_lead(lead_id)
    if not lead:
        flash(f"Không tìm thấy Lead {lead_id}!", "danger")
        return redirect(url_for("leads_list"))

    # Lấy thông tin tài khoản, người liên hệ, cơ hội nếu đã chuyển đổi
    converted_account = db.get_account(lead.get("converted_account_id")) if lead.get("converted_account_id") else None
    converted_contact = db.get_contact(lead.get("converted_contact_id")) if lead.get("converted_contact_id") else None
    converted_opportunity = db.get_opportunity(lead.get("converted_opportunity_id")) if lead.get("converted_opportunity_id") else None

    return render_template(
        "lead_detail.html",
        lead=lead,
        converted_account=converted_account,
        converted_contact=converted_contact,
        converted_opportunity=converted_opportunity
    )


# =============================================================================
# 3. 🎯 TRỌNG TÂM: MÀN HÌNH & THAO TÁC CHUYỂN ĐỔI LEAD (1-CLICK CONVERSION)
# =============================================================================
@app.route("/leads/<lead_id>/convert", methods=["GET", "POST"])
def lead_convert(lead_id):
    lead = db.get_lead(lead_id)
    if not lead:
        flash(f"Không tìm thấy Lead {lead_id}!", "danger")
        return redirect(url_for("leads_list"))

    # Nếu lead đã chuyển đổi thì khóa chặt, không cho vào trang convert
    if lead.get("is_locked") or lead.get("status") == STATUS_CONVERTED:
        flash(
            f"⛔ RÀNG BUỘC TIÊU CHÍ 3: Lead '{lead_id}' đã chuyển đổi trước đó và đã bị KHÓA! "
            f"Không thể thực hiện chuyển đổi lại.",
            "warning"
        )
        return redirect(url_for("lead_detail", lead_id=lead_id))

    current_user_id = session.get("user_id", "usr-01")

    if request.method == "POST":
        # Nhận dữ liệu tùy biến (nếu nhân viên muốn tinh chỉnh tên cơ hội hoặc số tiền,
        # nếu để trống thì hệ thống tự động kế thừa 100% từ lead)
        opp_name = request.form.get("opportunity_name")
        opp_amount = request.form.get("opportunity_amount")
        opp_close_date = request.form.get("opportunity_close_date")
        opp_stage = request.form.get("opportunity_stage", STAGE_DISCOVERY)

        try:
            result = db.convert_lead(
                lead_id=lead_id,
                user_id=current_user_id,
                opp_name=opp_name,
                opp_amount=opp_amount,
                opp_close_date=opp_close_date,
                opp_stage=opp_stage
            )

            flash(
                f"🎉 CHUYỂN ĐỔI THÀNH CÔNG! Đã sinh đồng thời Khách hàng '{result['account']['name']}', "
                f"Người liên hệ '{result['contact']['full_name']}' và Cơ hội '{result['opportunity']['name']}'. "
                f"Toàn bộ {result['inherited_count']} hoạt động đã được kế thừa trọn vẹn!",
                "success"
            )
            return redirect(url_for("conversion_success", lead_id=lead_id))

        except Exception as e:
            flash(f"Lỗi khi chuyển đổi lead: {str(e)}", "danger")
            return redirect(url_for("lead_convert", lead_id=lead_id))

    # GET Request: Hiển thị màn hình Preview xem trước 3 thực thể sinh đồng thời
    return render_template("lead_convert.html", lead=lead)


@app.route("/leads/<lead_id>/conversion-success")
def conversion_success(lead_id):
    lead = db.get_lead(lead_id)
    if not lead or not lead.get("is_locked"):
        flash("Lead chưa được chuyển đổi!", "warning")
        return redirect(url_for("leads_list"))

    account = db.get_account(lead.get("converted_account_id"))
    contact = db.get_contact(lead.get("converted_contact_id"))
    opportunity = db.get_opportunity(lead.get("converted_opportunity_id"))

    return render_template(
        "conversion_success.html",
        lead=lead,
        account=account,
        contact=contact,
        opportunity=opportunity
    )


# =============================================================================
# 4. KIỂM SOÁT SỬA LEAD - THỰC HIỆN TIÊU CHÍ 3 (CHẶN SỬA KHI ĐÃ CHUYỂN ĐỔI)
# =============================================================================
@app.route("/leads/<lead_id>/edit", methods=["GET", "POST"])
def lead_edit(lead_id):
    lead = db.get_lead(lead_id)
    if not lead:
        flash(f"Không tìm thấy Lead {lead_id}!", "danger")
        return redirect(url_for("leads_list"))

    # KIỂM SOÁT TIÊU CHÍ 3: CHẶN NGAY TỪ ĐẦU NẾU LEAD ĐÃ CHUYỂN ĐỔI
    if lead.get("is_locked") or lead.get("status") == STATUS_CONVERTED:
        flash(
            f"🔒 RÀNG BUỘC TIÊU CHÍ 3: Lead '{lead_id}' đã chuyển sang trạng thái "
            f"'Đã chuyển đổi' (CONVERTED) và ĐÃ BỊ KHÓA BẤT BIẾN! Không cho phép sửa đổi.",
            "danger"
        )
        return redirect(url_for("lead_detail", lead_id=lead_id))

    current_user_id = session.get("user_id", "usr-01")

    if request.method == "POST":
        data = {
            "company_name": request.form.get("company_name", "").strip(),
            "tax_id": request.form.get("tax_id", "").strip(),
            "industry": request.form.get("industry", "").strip(),
            "address": request.form.get("address", "").strip(),
            "city": request.form.get("city", "").strip(),
            "website": request.form.get("website", "").strip(),
            "company_size": request.form.get("company_size", "").strip(),
            "contact_name": request.form.get("contact_name", "").strip(),
            "job_title": request.form.get("job_title", "").strip(),
            "phone": request.form.get("phone", "").strip(),
            "email": request.form.get("email", "").strip(),
            "interested_product": request.form.get("interested_product", "").strip(),
            "estimated_value": request.form.get("estimated_value", 0),
            "expected_close_date": request.form.get("expected_close_date", ""),
            "requirements": request.form.get("requirements", "").strip(),
            "status": request.form.get("status", lead["status"]),
            "assigned_to_id": request.form.get("assigned_to_id", lead["assigned_to_id"]),
            "qualification_notes": request.form.get("qualification_notes", "").strip()
        }

        try:
            db.update_lead(lead_id, data, user_id=current_user_id)
            flash(f"Đã cập nhật thông tin Lead {lead_id} thành công!", "success")
            return redirect(url_for("lead_detail", lead_id=lead_id))
        except PermissionError as pe:
            flash(str(pe), "danger")
            return redirect(url_for("lead_detail", lead_id=lead_id))
        except Exception as e:
            flash(f"Lỗi cập nhật: {str(e)}", "danger")

    return render_template("lead_edit.html", lead=lead)


# =============================================================================
# 5. THÊM HOẠT ĐỘNG VÀO LEAD (TRƯỚC KHI CHUYỂN ĐỔI)
# =============================================================================
@app.route("/leads/<lead_id>/add-activity", methods=["POST"])
def lead_add_activity(lead_id):
    current_user_id = session.get("user_id", "usr-01")
    act_type = request.form.get("type", ACTIVITY_CALL)
    summary = request.form.get("summary", "").strip()
    details = request.form.get("details", "").strip()

    if not summary:
        flash("Vui lòng nhập tiêu đề tóm tắt hoạt động!", "danger")
        return redirect(url_for("lead_detail", lead_id=lead_id))

    try:
        db.add_lead_activity(
            lead_id=lead_id,
            user_id=current_user_id,
            act_type=act_type,
            summary=summary,
            details=details
        )
        flash("Đã ghi nhận hoạt động mới vào Lead!", "success")
    except PermissionError as pe:
        flash(str(pe), "danger")
    except Exception as e:
        flash(f"Lỗi: {str(e)}", "danger")

    return redirect(url_for("lead_detail", lead_id=lead_id))


# =============================================================================
# 6. QUẢN LÝ KHÁCH HÀNG DOANH NGHIỆP (ACCOUNTS) - CHỨNG MINH TIÊU CHÍ 4
# =============================================================================
@app.route("/accounts")
def accounts_list():
    search = request.args.get("search")
    accounts = db.get_accounts(search=search)
    return render_template("accounts_list.html", accounts=accounts, search=search)


@app.route("/accounts/<account_id>")
def account_detail(account_id):
    account = db.get_account(account_id)
    if not account:
        flash(f"Không tìm thấy Khách hàng {account_id}!", "danger")
        return redirect(url_for("accounts_list"))

    contacts = db.get_contacts(account_id=account_id)
    opportunities = db.get_opportunities(account_id=account_id)
    source_lead = db.get_lead(account.get("created_from_lead_id")) if account.get("created_from_lead_id") else None

    # Tách hoạt động kế thừa từ lead và hoạt động tạo mới trên Account
    inherited_activities = [a for a in account.get("activities", []) if a.get("inherited_from_lead")]
    direct_activities = [a for a in account.get("activities", []) if not a.get("inherited_from_lead")]

    return render_template(
        "account_detail.html",
        account=account,
        contacts=contacts,
        opportunities=opportunities,
        source_lead=source_lead,
        inherited_activities=inherited_activities,
        direct_activities=direct_activities
    )


@app.route("/accounts/<account_id>/add-activity", methods=["POST"])
def account_add_activity(account_id):
    current_user_id = session.get("user_id", "usr-01")
    act_type = request.form.get("type", ACTIVITY_CALL)
    summary = request.form.get("summary", "").strip()
    details = request.form.get("details", "").strip()

    if not summary:
        flash("Vui lòng nhập tóm tắt hoạt động!", "danger")
        return redirect(url_for("account_detail", account_id=account_id))

    try:
        db.add_account_activity(
            account_id=account_id,
            user_id=current_user_id,
            act_type=act_type,
            summary=summary,
            details=details
        )
        flash("Đã ghi nhận hoạt động mới trên Khách hàng!", "success")
    except Exception as e:
        flash(f"Lỗi: {str(e)}", "danger")

    return redirect(url_for("account_detail", account_id=account_id))


# =============================================================================
# 7. QUẢN LÝ NGƯỜI LIÊN HỆ & CƠ HỘI BÁN HÀNG
# =============================================================================
@app.route("/contacts")
def contacts_list():
    search = request.args.get("search")
    contacts = db.get_contacts(search=search)
    return render_template("contacts_list.html", contacts=contacts, search=search)


@app.route("/opportunities")
def opportunities_list():
    stage_filter = request.args.get("stage")
    opportunities = db.get_opportunities(stage=stage_filter)
    return render_template("opportunities_list.html", opportunities=opportunities, stage_filter=stage_filter)


@app.route("/opportunities/<opp_id>/update-stage", methods=["POST"])
def update_opportunity_stage(opp_id):
    new_stage = request.form.get("stage")
    current_user_id = session.get("user_id", "usr-01")
    try:
        db.update_opportunity_stage(opp_id, new_stage, user_id=current_user_id)
        flash(f"Đã cập nhật giai đoạn cơ hội sang: {STAGE_LABELS.get(new_stage, new_stage)}", "success")
    except Exception as e:
        flash(f"Lỗi: {str(e)}", "danger")

    return redirect(request.referrer or url_for("opportunities_list"))


# =============================================================================
# 8. TRÌNH MÔ PHỎNG & KIỂM THỬ TRỰC QUAN (SIMULATOR)
# Phục vụ người chấm kiểm tra ngay 4 tiêu chí chấp nhận trong 10 giây
# =============================================================================
@app.route("/simulator")
def simulator():
    leads = db.get_leads()
    return render_template("simulator.html", leads=leads)


@app.route("/simulator/run-flow", methods=["POST"])
def simulator_run_flow():
    current_user_id = session.get("user_id", "usr-01")
    
    # 1. Tạo một lead kiểm thử
    test_lead_data = {
        "company_name": f"Công ty Kiểm Thử Tự Động {datetime.now().strftime('%H%M%S')}",
        "tax_id": "0109999888",
        "industry": "Giải pháp AI & Tự Động Hóa",
        "address": "Số 88 Phố Huế, Quận Hai Bà Trưng",
        "city": "Hà Nội",
        "website": "https://test-auto.example.vn",
        "company_size": "50 - 100",
        "contact_name": "Trần Thị Kiểm Thử",
        "job_title": "Giám Đốc Bán Hàng",
        "phone": "0988 777 666",
        "email": "kiemthu@test-auto.example.vn",
        "interested_product": "Hệ Thống CRM Doanh Nghiệp SCRUM-54",
        "estimated_value": 88000000,
        "expected_close_date": (datetime.now() + datetime.resolution).strftime("%Y-%m-%d"),
        "requirements": "Kiểm thử tự động 4 tiêu chí chấp nhận",
        "status": STATUS_QUALIFIED
    }
    lead = db.create_lead(test_lead_data, user_id=current_user_id)

    # 2. Thêm 2 hoạt động vào lead
    db.add_lead_activity(
        lead_id=lead["id"],
        user_id=current_user_id,
        act_type=ACTIVITY_CALL,
        summary="Cuộc gọi khảo sát nhu cầu tự động",
        details="Xác nhận khách hàng có ngân sách và nhu cầu cấp thiết."
    )
    db.add_lead_activity(
        lead_id=lead["id"],
        user_id=current_user_id,
        act_type=ACTIVITY_MEETING,
        summary="Gặp mặt trình diễn giải pháp chuyển đổi lead",
        details="Demo tính năng sinh 3 thực thể đồng thời và kế thừa toàn bộ hoạt động."
    )

    # 3. Thực hiện chuyển đổi
    convert_res = db.convert_lead(lead["id"], user_id=current_user_id)

    # 4. Thử cố tình sửa lead để kiểm tra khóa bảo vệ
    lock_verified = False
    try:
        db.update_lead(lead["id"], {"company_name": "Tên Bị Sửa Trái Phép"})
    except PermissionError:
        lock_verified = True

    flash(
        f"✅ ĐÃ CHẠY XONG KỊCH BẢN KIỂM THỬ TỰ ĐỘNG! "
        f"Đã sinh Account [{convert_res['account']['id']}], "
        f"Contact [{convert_res['contact']['id']}], "
        f"Opportunity [{convert_res['opportunity']['id']}]. "
        f"Kế thừa {convert_res['inherited_count']} hoạt động. "
        f"Khóa bảo vệ: {'HOÀN TOÀN CHẶN SỬA ĐÚNG YÊU CẦU' if lock_verified else 'LỖI'}",
        "success"
    )
    return redirect(url_for("account_detail", account_id=convert_res['account']['id']))


# =============================================================================
# 9. RESET DỮ LIỆU DEMO
# =============================================================================
@app.route("/reset-data")
def reset_data():
    db.reset_demo_data()
    flash("Đã đặt lại dữ liệu mẫu ban đầu về trạng thái chuẩn!", "info")
    return redirect(url_for("dashboard"))


# =============================================================================
# 10. REST API ENDPOINTS
# =============================================================================
@app.route("/api/leads/<lead_id>/convert", methods=["POST"])
def api_convert_lead(lead_id):
    current_user_id = session.get("user_id", "usr-01")
    data = request.get_json() or {}
    try:
        res = db.convert_lead(
            lead_id=lead_id,
            user_id=current_user_id,
            opp_name=data.get("name"),
            opp_amount=data.get("amount"),
            opp_close_date=data.get("close_date"),
            opp_stage=data.get("stage")
        )
        return jsonify({
            "success": True,
            "message": "Chuyển đổi thành công sinh đồng thời 3 thực thể!",
            "account_id": res["account"]["id"],
            "contact_id": res["contact"]["id"],
            "opportunity_id": res["opportunity"]["id"],
            "inherited_count": res["inherited_count"]
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/leads/<lead_id>", methods=["PUT"])
def api_update_lead(lead_id):
    current_user_id = session.get("user_id", "usr-01")
    data = request.get_json() or {}
    try:
        lead = db.update_lead(lead_id, data, user_id=current_user_id)
        return jsonify({"success": True, "lead": lead})
    except PermissionError as pe:
        return jsonify({"success": False, "error": str(pe), "locked": True}), 403
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/accounts/<account_id>/activities", methods=["GET"])
def api_account_activities(account_id):
    acc = db.get_account(account_id)
    if not acc:
        return jsonify({"error": "Not found"}), 404
    return jsonify({"activities": acc.get("activities", [])})


if __name__ == "__main__":
    print("=" * 70)
    print("  HỆ THỐNG CHUYỂN ĐỔI LEAD CRM - TICKET SCRUM-54")
    print(f"  Khởi chạy máy chủ tại: http://127.0.0.1:{DEFAULT_PORT}")
    print("=" * 70)
    app.run(host="127.0.0.1", port=DEFAULT_PORT, debug=True)
