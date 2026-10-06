"""
Ứng Dụng Flask - Hệ Thống Duyệt Báo Giá Theo Mức Chiết Khấu (SCRUM-35 / SCRUM-33)
Subtasks: SCRUM-232 (FE) & SCRUM-233 (BE)
User Story: "Là Trưởng nhóm kinh doanh, tôi muốn duyệt báo giá theo mức chiết khấu, để kiểm soát biên lợi nhuận mà không phải trả lời từng tin nhắn xin giảm giá."

5 Tiêu chí chấp nhận (Acceptance Criteria):
1. Chiết khấu dưới ngưỡng thứ nhất thì tự động thông qua, không cần duyệt.
2. Vượt ngưỡng thứ nhất do Trưởng nhóm duyệt; vượt ngưỡng thứ hai hoặc dưới giá sàn thì bắt buộc Giám đốc kinh doanh duyệt.
3. Ba hành động: Duyệt, Từ chối, Trả lại sửa — hai hành động sau bắt buộc nhập ý kiến.
4. Chỉ báo giá đã duyệt mới gửi được cho khách.
5. Lịch sử duyệt không sửa và không xoá được.
"""

import os
import sys
import json
from datetime import datetime

if sys.platform == "win32":
    try:
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
    SUBTASK_FE,
    SUBTASK_BE,
    DEFAULT_PORT,
    ROLE_SALES_REP,
    ROLE_TEAM_LEAD,
    ROLE_DIRECTOR,
    ROLE_SYSTEM,
    ROLE_LABELS,
    ROLE_AVATARS,
    THRESHOLD_1_PERCENT,
    THRESHOLD_2_PERCENT,
    STATUS_DRAFT,
    STATUS_PENDING_APPROVAL,
    STATUS_APPROVED,
    STATUS_CHANGES_REQUESTED,
    STATUS_REJECTED,
    STATUS_SENT,
    STATUS_LABELS,
    STATUS_BADGE_CLASSES,
    ACTION_APPROVE,
    ACTION_REJECT,
    ACTION_REQUEST_CHANGES,
    ACTION_AUTO_APPROVE,
    ACTION_SUBMIT,
    ACTION_LABELS,
    AUTHORITY_AUTO,
    AUTHORITY_TEAM_LEAD,
    AUTHORITY_DIRECTOR,
    AUTHORITY_LABELS,
    PRODUCT_CATALOG
)
from database import (
    db,
    format_currency,
    format_datetime,
    format_date,
    get_current_time
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "scrum-33-quote-approval-secret-key-2026")


# Jinja2 Template Filters
@app.template_filter("vi_currency")
def vi_currency_filter(val):
    return format_currency(val)


@app.template_filter("vi_datetime")
def vi_datetime_filter(dt):
    return format_datetime(dt)


@app.template_filter("vi_date")
def vi_date_filter(dt):
    return format_date(dt)


# Middleware nạp thông tin người dùng và context toàn cục
@app.context_processor
def inject_global_context():
    # Mặc định vai trò là Trưởng nhóm kinh doanh (usr-03) theo đúng trọng tâm User Story
    user_id = session.get("user_id", "usr-03")
    current_user = db.get_user(user_id)
    if not current_user:
        current_user = db.get_user("usr-03")

    metrics = db.get_dashboard_metrics()
    notifications = db.get_user_notifications(current_user["id"])

    return {
        "current_user": current_user,
        "all_users": db.get_all_users(),
        "metrics": metrics,
        "notifications": notifications,
        "TICKET_ID": TICKET_ID,
        "PARENT_EPIC": PARENT_EPIC,
        "SUBTASK_FE": SUBTASK_FE,
        "SUBTASK_BE": SUBTASK_BE,
        "THRESHOLD_1_PERCENT": THRESHOLD_1_PERCENT,
        "THRESHOLD_2_PERCENT": THRESHOLD_2_PERCENT,
        "STATUS_DRAFT": STATUS_DRAFT,
        "STATUS_PENDING_APPROVAL": STATUS_PENDING_APPROVAL,
        "STATUS_APPROVED": STATUS_APPROVED,
        "STATUS_CHANGES_REQUESTED": STATUS_CHANGES_REQUESTED,
        "STATUS_REJECTED": STATUS_REJECTED,
        "STATUS_SENT": STATUS_SENT,
        "STATUS_LABELS": STATUS_LABELS,
        "STATUS_BADGE_CLASSES": STATUS_BADGE_CLASSES,
        "ROLE_SALES_REP": ROLE_SALES_REP,
        "ROLE_TEAM_LEAD": ROLE_TEAM_LEAD,
        "ROLE_DIRECTOR": ROLE_DIRECTOR,
        "ROLE_LABELS": ROLE_LABELS,
        "ROLE_AVATARS": ROLE_AVATARS,
        "AUTHORITY_AUTO": AUTHORITY_AUTO,
        "AUTHORITY_TEAM_LEAD": AUTHORITY_TEAM_LEAD,
        "AUTHORITY_DIRECTOR": AUTHORITY_DIRECTOR,
        "AUTHORITY_LABELS": AUTHORITY_LABELS
    }


# =============================================================================
# WEB ROUTES
# =============================================================================

@app.route("/")
@app.route("/dashboard")
def dashboard():
    """Bàn làm việc của Trưởng nhóm & Giám đốc kinh doanh"""
    current_user = db.get_user(session.get("user_id", "usr-03"))
    pending_quotes = db.get_approval_queue(viewer_role=current_user["role"])
    recent_quotes = db.get_all_quotes()[:6]
    return render_template(
        "dashboard.html",
        pending_quotes=pending_quotes,
        recent_quotes=recent_quotes
    )


@app.route("/approval-queue")
def approval_queue():
    """Hàng chờ duyệt chuyên sâu với bộ lọc theo thẩm quyền và cảnh báo giá sàn"""
    filter_role = request.args.get("authority", "")
    all_pending = db.get_approval_queue()

    if filter_role == "TEAM_LEAD":
        filtered = [q for q in all_pending if q.get("required_role") == ROLE_TEAM_LEAD]
    elif filter_role == "DIRECTOR":
        filtered = [q for q in all_pending if q.get("required_role") == ROLE_DIRECTOR]
    elif filter_role == "BELOW_FLOOR":
        filtered = [q for q in all_pending if q.get("below_floor_price")]
    else:
        filtered = all_pending

    return render_template(
        "approval_queue.html",
        quotes=filtered,
        active_filter=filter_role
    )


@app.route("/quotes")
def quotes_list():
    """Danh sách toàn bộ Báo giá trong hệ thống kèm bộ lọc trạng thái"""
    status_filter = request.args.get("status", "")
    quotes = db.get_all_quotes(status=status_filter if status_filter else None)
    return render_template(
        "quotes_list.html",
        quotes=quotes,
        active_status=status_filter
    )


@app.route("/quotes/<quote_id>")
def quote_detail(quote_id):
    """Trang chi tiết báo giá, duyệt/từ chối/trả lại sửa, và lịch sử duyệt bất biến"""
    quote = db.get_quote(quote_id)
    if not quote:
        flash(f"Không tìm thấy báo giá {quote_id}!", "danger")
        return redirect(url_for("quotes_list"))

    current_user = db.get_user(session.get("user_id", "usr-03"))

    # Kiểm tra quyền duyệt của người dùng hiện tại đối với báo giá này
    can_approve = False
    permission_warning = None

    if quote["status"] in [STATUS_PENDING_APPROVAL, STATUS_CHANGES_REQUESTED]:
        if current_user["role"] == ROLE_DIRECTOR:
            # Giám đốc có quyền tối cao duyệt mọi báo giá
            can_approve = True
        elif current_user["role"] == ROLE_TEAM_LEAD:
            # Trưởng nhóm chỉ duyệt khi không vượt ngưỡng 2 và không dưới giá sàn
            if quote.get("required_role") == ROLE_DIRECTOR:
                can_approve = False
                permission_warning = (
                    "⚠️ Báo giá này vượt ngưỡng thứ hai (>20%) hoặc bán dưới giá sàn! "
                    "Theo quy định, bắt buộc GIÁM ĐỐC KINH DOANH phê duyệt. "
                    "Trưởng nhóm chỉ có quyền xem xét, không thể bấm Duyệt."
                )
            else:
                can_approve = True
        else:
            can_approve = False
            permission_warning = "Nhân viên kinh doanh không có thẩm quyền phê duyệt báo giá."

    return render_template(
        "quote_detail.html",
        quote=quote,
        can_approve=can_approve,
        permission_warning=permission_warning
    )


@app.route("/quotes/<quote_id>/action", methods=["POST"])
def quote_action(quote_id):
    """
    Xử lý 3 hành động phê duyệt: Duyệt, Từ chối, Trả lại sửa (AC3)
    Kiểm tra bắt buộc nhập ý kiến đối với Từ chối và Trả lại sửa
    """
    action = request.form.get("action")
    comment = request.form.get("comment", "").strip()
    user_id = session.get("user_id", "usr-03")

    try:
        if action == ACTION_APPROVE:
            db.approve_quote(quote_id, actor_id=user_id, comment=comment)
            flash(f"✅ Đã phê duyệt thành công báo giá {quote_id}! Báo giá đã sẵn sàng gửi cho khách hàng.", "success")

        elif action == ACTION_REJECT:
            db.reject_quote(quote_id, actor_id=user_id, comment=comment)
            flash(f"❌ Đã từ chối báo giá {quote_id}. Lý do từ chối đã được ghi vào lịch sử kiểm toán.", "warning")

        elif action == ACTION_REQUEST_CHANGES:
            db.request_changes_quote(quote_id, actor_id=user_id, comment=comment)
            flash(f"🔄 Đã trả lại báo giá {quote_id} yêu cầu chỉnh sửa. NVKD đã nhận được thông báo để điều chỉnh.", "info")

        else:
            flash(f"Hành động '{action}' không hợp lệ!", "danger")

    except PermissionError as pe:
        flash(f"🚫 LỖI PHÂN QUYỀN: {str(pe)}", "danger")
    except ValueError as ve:
        flash(f"⚠️ LỖI RÀNG BUỘC DỮ LIỆU: {str(ve)}", "danger")
    except Exception as ex:
        flash(f"Đã xảy ra lỗi hệ thống: {str(ex)}", "danger")

    return redirect(url_for("quote_detail", quote_id=quote_id))


@app.route("/quotes/<quote_id>/send", methods=["POST"])
def send_quote(quote_id):
    """
    Gửi báo giá cho khách hàng (AC4):
    Chỉ báo giá ở trạng thái APPROVED mới được gửi!
    """
    user_id = session.get("user_id", "usr-01")
    try:
        db.send_to_customer(quote_id, actor_id=user_id)
        flash(f"📤 Đã gửi báo giá {quote_id} thành công cho khách hàng qua Email!", "success")
    except ValueError as ve:
        flash(f"🚫 KHÔNG THỂ GỬI: {str(ve)}", "danger")
    except Exception as ex:
        flash(f"Đã xảy ra lỗi khi gửi báo giá: {str(ex)}", "danger")

    return redirect(url_for("quote_detail", quote_id=quote_id))


@app.route("/quotes/<quote_id>/submit", methods=["POST"])
def submit_quote(quote_id):
    """
    Trình duyệt báo giá:
    Nếu chiết khấu < ngưỡng 1 và không dưới sàn -> Tự động thông qua (AC1)
    """
    user_id = session.get("user_id", "usr-01")
    try:
        quote = db.submit_quote_for_approval(quote_id, user_id=user_id)
        if quote["status"] == STATUS_APPROVED:
            flash(f"⚡ Báo giá {quote_id} có mức chiết khấu dưới ngưỡng 1 (< 10%) nên đã được TỰ ĐỘNG THÔNG QUA! Bạn có thể gửi cho khách ngay.", "success")
        else:
            role_label = ROLE_LABELS.get(quote.get("required_role"), "Cấp quản lý")
            flash(f"📋 Đã trình duyệt báo giá {quote_id}. Báo giá đã được chuyển vào hàng chờ của {role_label}.", "info")
    except Exception as ex:
        flash(f"Lỗi khi trình duyệt: {str(ex)}", "danger")

    return redirect(url_for("quote_detail", quote_id=quote_id))


@app.route("/quotes/create", methods=["GET", "POST"])
def quote_create():
    """Tạo báo giá mới để thử nghiệm các trường hợp chiết khấu & giá sàn"""
    if request.method == "POST":
        title = request.form.get("title", "Báo giá mới")
        account_name = request.form.get("account_name", "Công ty Khách hàng")
        contact_name = request.form.get("contact_name", "Người liên hệ")
        contact_email = request.form.get("contact_email", "contact@customer.com")
        contact_phone = request.form.get("contact_phone", "0900.123.456")
        auto_submit = request.form.get("auto_submit") == "on"

        # Đọc danh sách dòng sản phẩm từ form
        product_ids = request.form.getlist("product_id[]")
        quantities = request.form.getlist("quantity[]")
        unit_prices = request.form.getlist("unit_price[]")
        discount_percents = request.form.getlist("discount_percent[]")

        items = []
        for i in range(len(product_ids)):
            p_id = product_ids[i]
            if not p_id:
                continue
            qty = float(quantities[i]) if i < len(quantities) and quantities[i] else 1
            u_p = float(unit_prices[i]) if i < len(unit_prices) and unit_prices[i] else 0
            d_p = float(discount_percents[i]) if i < len(discount_percents) and discount_percents[i] else 0

            items.append({
                "product_id": p_id,
                "quantity": qty,
                "unit_price": u_p,
                "discount_percent": d_p
            })

        quote_data = {
            "title": title,
            "account_name": account_name,
            "contact_name": contact_name,
            "contact_email": contact_email,
            "contact_phone": contact_phone,
            "items": items,
            "auto_submit": auto_submit
        }

        user_id = session.get("user_id", "usr-01")
        new_quote = db.create_quote(quote_data, user_id=user_id)

        if auto_submit:
            if new_quote["status"] == STATUS_APPROVED:
                flash(f"⚡ Báo giá {new_quote['id']} được TỰ ĐỘNG THÔNG QUA (Chiết khấu < 10% và trên giá sàn)!", "success")
            else:
                flash(f"📋 Báo giá {new_quote['id']} đã được trình duyệt tới {ROLE_LABELS.get(new_quote.get('required_role'))}!", "info")
        else:
            flash(f"📝 Đã tạo bản nháp báo giá {new_quote['id']} thành công!", "success")

        return redirect(url_for("quote_detail", quote_id=new_quote["id"]))

    products = db.get_all_products()
    return render_template("quote_create.html", products=products)


@app.route("/simulator")
def simulator():
    """Trang mô phỏng và kiểm thử tự động 5 tiêu chí chấp nhận trong 1 click"""
    return render_template("simulator.html")


@app.route("/switch-persona/<user_id>")
def switch_persona(user_id):
    """Chuyển đổi nhanh giữa các vai trò (Trưởng nhóm, Giám đốc, NVKD)"""
    user = db.get_user(user_id)
    if user:
        session["user_id"] = user_id
        flash(f"Đã chuyển đổi người dùng sang: {user['avatar']} {user['name']} ({user['role_name']})", "info")
    next_url = request.args.get("next", url_for("dashboard"))
    return redirect(next_url)


@app.route("/reset-data", methods=["POST", "GET"])
def reset_data():
    """Khôi phục lại dữ liệu mẫu ban đầu"""
    db.reset_demo_data()
    flash("🔄 Đã khôi phục toàn bộ dữ liệu mẫu ban đầu thành công!", "success")
    return redirect(url_for("dashboard"))


# =============================================================================
# REST APIS (Hỗ trợ Frontend SCRUM-232 & Subtask BE SCRUM-233)
# =============================================================================

@app.route("/api/calculate-discount", methods=["POST"])
def api_calculate_discount():
    """API tính toán chiết khấu và xác định thẩm quyền duyệt theo thời gian thực"""
    data = request.get_json() or {}
    items = data.get("items", [])
    calc = db.calculate_quote_discount(items)
    return jsonify({
        "success": True,
        "calculation": calc
    })


@app.route("/api/quotes/<quote_id>", methods=["GET"])
def api_get_quote(quote_id):
    """Lấy dữ liệu chi tiết báo giá và lịch sử duyệt"""
    quote = db.get_quote(quote_id)
    if not quote:
        return jsonify({"success": False, "error": "Báo giá không tồn tại"}), 404
    return jsonify({"success": True, "data": quote})


@app.route("/api/quotes/<quote_id>/history", methods=["GET"])
def api_get_history(quote_id):
    """Lấy sổ cái lịch sử duyệt bất biến của báo giá (AC5)"""
    history = db.get_approval_history(quote_id)
    return jsonify({
        "success": True,
        "quote_id": quote_id,
        "is_immutable": True,
        "history": history
    })


@app.route("/api/quotes/<quote_id>/action", methods=["POST"])
def api_quote_action(quote_id):
    """Thực hiện hành động duyệt qua REST API"""
    data = request.get_json() or {}
    action = data.get("action")
    comment = data.get("comment", "")
    actor_id = data.get("actor_id") or session.get("user_id", "usr-03")

    try:
        if action == ACTION_APPROVE:
            res = db.approve_quote(quote_id, actor_id=actor_id, comment=comment)
        elif action == ACTION_REJECT:
            res = db.reject_quote(quote_id, actor_id=actor_id, comment=comment)
        elif action == ACTION_REQUEST_CHANGES:
            res = db.request_changes_quote(quote_id, actor_id=actor_id, comment=comment)
        else:
            return jsonify({"success": False, "error": f"Hành động '{action}' không hợp lệ"}), 400

        return jsonify({
            "success": True,
            "message": f"Thực hiện hành động {action} thành công",
            "quote": res
        })
    except PermissionError as pe:
        return jsonify({"success": False, "error": str(pe), "code": "PERMISSION_DENIED"}), 403
    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve), "code": "VALIDATION_ERROR"}), 400
    except Exception as ex:
        return jsonify({"success": False, "error": str(ex)}), 500


@app.route("/api/quotes/<quote_id>/send", methods=["POST"])
def api_quote_send(quote_id):
    """Gửi báo giá cho khách hàng qua REST API (AC4)"""
    data = request.get_json() or {}
    actor_id = data.get("actor_id") or session.get("user_id", "usr-01")
    try:
        res = db.send_to_customer(quote_id, actor_id=actor_id)
        return jsonify({"success": True, "message": "Gửi khách hàng thành công", "quote": res})
    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve), "code": "NOT_APPROVED"}), 400
    except Exception as ex:
        return jsonify({"success": False, "error": str(ex)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", DEFAULT_PORT))
    print(f"================================================================")
    print(f"🚀 AUTOLEAD CRM - HỆ THỐNG DUYỆT BÁO GIÁ THEO CHIẾT KHẤU")
    print(f"📌 Ticket: {PARENT_EPIC} / {TICKET_ID} (Subtasks: {SUBTASK_FE} & {SUBTASK_BE})")
    print(f"🌐 Server khởi chạy tại: http://127.0.0.1:{port}")
    print(f"👑 Thẩm quyền phê duyệt: Trưởng nhóm kinh doanh & Giám đốc kinh doanh")
    print(f"================================================================")
    app.run(host="0.0.0.0", port=port, debug=True)


def validate_rejection_reason(reason: str) -> bool:
    """Xác thực lý do từ chối phê duyệt bắt buộc có độ dài tối thiểu 5 ký tự"""
    return bool(reason and len(reason.strip()) >= 5)


def format_approval_webhook_payload(quote_data: dict, status: str) -> dict:
    """Định dạng payload gửi webhook tới kênh thông báo Slack/Telegram nội bộ"""
    return {'quote_id': quote_data.get('id'), 'status': status, 'timestamp': '2026-10-04'}

# SLA Indicator
DEFAULT_APPROVAL_SLA_HOURS = 24
