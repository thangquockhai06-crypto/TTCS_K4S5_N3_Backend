"""
Ứng Dụng Flask - Dòng Thời Gian Tương Tác Khách Hàng
Ticket: SCRUM-36 / SCRUM-57
Vai trò: Chăm sóc khách hàng (Customer Service)

User Story:
"Là Chăm sóc khách hàng, tôi muốn xem dòng thời gian tương tác đầy đủ của một khách hàng,
để tiếp nhận khách từ đồng nghiệp mà nắm được bối cảnh trong năm phút."

Tiêu chí chấp nhận:
1. Gộp toàn bộ hoạt động, thay đổi cơ hội, báo giá đã gửi theo thứ tự thời gian.
2. Lọc theo loại hoạt động và theo người thực hiện.
"""

import os
import sys
from datetime import datetime

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify

from config import (
    TICKET_ID,
    PARENT_EPIC,
    EVENT_TYPES,
    ACTIVITY_TYPES,
    EVENT_TYPE_LABELS,
    EVENT_TYPE_ICONS,
    EVENT_TYPE_COLORS,
    ORDER_ASC,
    ORDER_DESC,
    DEFAULT_PORT,
)
from database import (
    db,
    event_to_json,
    format_currency,
    format_datetime,
    format_date,
    format_relative,
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "scrum-57-customer-timeline-key-2026")
app.json.ensure_ascii = False  # Trả JSON tiếng Việt dễ đọc

DEFAULT_USER_ID = "usr-cs1"

_WEEKDAYS = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]


# =============================================================================
# JINJA FILTERS & BIẾN TOÀN CỤC
# =============================================================================
@app.template_filter("vi_currency")
def vi_currency_filter(amount):
    return format_currency(amount)


@app.template_filter("vi_datetime")
def vi_datetime_filter(dt):
    return format_datetime(dt)


@app.template_filter("vi_date")
def vi_date_filter(dt):
    return format_date(dt)


@app.template_filter("vi_time")
def vi_time_filter(dt):
    return dt.strftime("%H:%M") if dt else "—"


@app.template_filter("relative")
def relative_filter(dt):
    return format_relative(dt)


@app.template_filter("day_heading")
def day_heading_filter(d):
    today = datetime.now().date()
    diff = (today - d).days
    if diff == 0:
        prefix = "Hôm nay"
    elif diff == 1:
        prefix = "Hôm qua"
    else:
        prefix = _WEEKDAYS[d.weekday()]
    return f"{prefix}, {d.strftime('%d/%m/%Y')}"


def _current_user_id():
    uid = session.get("user_id", DEFAULT_USER_ID)
    return uid if uid in db.users else DEFAULT_USER_ID


@app.context_processor
def inject_globals():
    return {
        "TICKET_ID": TICKET_ID,
        "PARENT_EPIC": PARENT_EPIC,
        "EVENT_TYPES": EVENT_TYPES,
        "ACTIVITY_TYPES": ACTIVITY_TYPES,
        "EVENT_TYPE_LABELS": EVENT_TYPE_LABELS,
        "EVENT_TYPE_ICONS": EVENT_TYPE_ICONS,
        "EVENT_TYPE_COLORS": EVENT_TYPE_COLORS,
        "current_user": db.users[_current_user_id()],
        "all_users": db.users,
    }


# =============================================================================
# 0. CHUYỂN NGƯỜI DÙNG GIẢ LẬP
# =============================================================================
@app.route("/switch-user/<user_id>")
def switch_user(user_id):
    if user_id in db.users:
        session["user_id"] = user_id
        user = db.users[user_id]
        flash(f"Đã chuyển sang tài khoản: {user['name']} ({user['role_name']})", "info")
    return redirect(request.referrer or url_for("customers_view"))


# =============================================================================
# 1. DANH SÁCH KHÁCH HÀNG
# =============================================================================
@app.route("/")
@app.route("/customers")
def customers_view():
    search = request.args.get("search", "").strip()
    customers = db.list_customers(search)
    return render_template("customers.html", customers=customers, search=search)


# =============================================================================
# 2. DÒNG THỜI GIAN TƯƠNG TÁC (TIÊU CHÍ 1 + 2)
# =============================================================================
def _read_filter_args():
    return request.args.getlist("type"), request.args.getlist("performer")


@app.route("/customers/<customer_id>")
@app.route("/customers/<customer_id>/timeline")
def customer_timeline_view(customer_id):
    customer = db.get_customer(customer_id)
    if not customer:
        flash(f"Không tìm thấy khách hàng {customer_id}!", "danger")
        return redirect(url_for("customers_view"))

    raw_types, raw_performers = _read_filter_args()
    order = request.args.get("order", ORDER_DESC)
    if order not in (ORDER_ASC, ORDER_DESC):
        order = ORDER_DESC

    try:
        selected_types, selected_performers = db.normalize_filters(raw_types, raw_performers)
    except ValueError as exc:
        flash(f"{exc}. Đã bỏ qua bộ lọc không hợp lệ.", "warning")
        selected_types, selected_performers = [], []

    events = db.build_timeline(customer_id, selected_types, selected_performers, order)

    return render_template(
        "timeline.html",
        customer=customer,
        summary=db.get_handover_summary(customer_id),
        day_groups=db.group_by_day(events),
        total_shown=len(events),
        total_all=len(db.build_timeline(customer_id)),
        performers=db.get_performers(customer_id),
        type_counts=db.get_type_counts(customer_id, selected_performers),
        selected_types=selected_types,
        selected_performers=selected_performers,
        order=order,
        has_filter=bool(selected_types or selected_performers),
    )


@app.route("/customers/<customer_id>/activities", methods=["POST"])
def customer_add_activity(customer_id):
    try:
        db.add_activity(
            customer_id=customer_id,
            activity_type=request.form.get("type", "NOTE"),
            subject=request.form.get("subject", ""),
            content=request.form.get("content", ""),
            user_id=_current_user_id(),
        )
        flash("Đã ghi nhận hoạt động vào dòng thời gian!", "success")
    except KeyError as exc:
        flash(str(exc).strip("'"), "danger")
        return redirect(url_for("customers_view"))
    except ValueError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("customer_timeline_view", customer_id=customer_id))


# =============================================================================
# 3. REST APIs
# =============================================================================
@app.route("/api/customers")
def api_customers():
    customers = db.list_customers(request.args.get("search"))
    data = [
        {
            "id": c["id"],
            "name": c["name"],
            "contact_name": c["contact_name"],
            "total_events": c["total_events"],
            "last_interaction_at": c["last_event"]["occurred_at"].isoformat() if c["last_event"] else None,
        }
        for c in customers
    ]
    return jsonify({"success": True, "count": len(data), "customers": data})


@app.route("/api/customers/<customer_id>/timeline")
def api_customer_timeline(customer_id):
    if not db.get_customer(customer_id):
        return jsonify({"success": False, "error": f"Không tìm thấy khách hàng {customer_id}"}), 404

    raw_types, raw_performers = _read_filter_args()
    order = request.args.get("order", ORDER_DESC)
    try:
        events = db.build_timeline(customer_id, raw_types, raw_performers, order)
        types, performers = db.normalize_filters(raw_types, raw_performers)
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400

    return jsonify({
        "success": True,
        "customer_id": customer_id,
        "filters": {"types": types, "performers": performers, "order": order},
        "count": len(events),
        "events": [event_to_json(e) for e in events],
    })


@app.route("/api/customers/<customer_id>/summary")
def api_customer_summary(customer_id):
    if not db.get_customer(customer_id):
        return jsonify({"success": False, "error": f"Không tìm thấy khách hàng {customer_id}"}), 404
    s = db.get_handover_summary(customer_id)
    return jsonify({
        "success": True,
        "customer_id": customer_id,
        "total_events": s["total_events"],
        "last_contact": event_to_json(s["last_contact"]) if s["last_contact"] else None,
        "open_opportunities": [
            {"id": o["id"], "name": o["name"], "stage": o["stage"], "amount": o["amount"]}
            for o in s["open_opportunities"]
        ],
        "latest_quote": {
            "code": s["latest_quote"]["code"],
            "status": s["latest_quote"]["status"],
            "amount": s["latest_quote"]["amount"],
        } if s["latest_quote"] else None,
        "pending_follow_ups": [
            {"text": p["text"], "due": p["due"].isoformat(), "is_overdue": p["is_overdue"]}
            for p in s["pending_follow_ups"]
        ],
    })


# =============================================================================
# 4. RESET DỮ LIỆU MẪU
# =============================================================================
@app.route("/reset-data")
def reset_data():
    db.reset_demo_data()
    flash("Đã đặt lại dữ liệu mẫu ban đầu!", "info")
    return redirect(url_for("customers_view"))


if __name__ == "__main__":
    print("=" * 70)
    print("  DÒNG THỜI GIAN TƯƠNG TÁC KHÁCH HÀNG - TICKET SCRUM-57")
    print(f"  Khởi chạy máy chủ tại: http://127.0.0.1:{DEFAULT_PORT}")
    print("=" * 70)
    app.run(host="127.0.0.1", port=DEFAULT_PORT, debug=True)


def paginate_timeline_events(events: list, page: int = 1, page_size: int = 15) -> dict:
    """Phân trang danh sách sự kiện timeline tương tác khách hàng"""
    total = len(events)
    start = (page - 1) * page_size
    end = start + page_size
    return {
        'items': events[start:end],
        'total': total,
        'page': page,
        'total_pages': (total + page_size - 1) // page_size if total > 0 else 1
    }
