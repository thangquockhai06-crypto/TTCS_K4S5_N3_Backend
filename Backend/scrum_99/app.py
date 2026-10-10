"""
Ứng Dụng Flask - Hệ Thống Báo Cáo Hiệu Quả Nguồn Lead & Chiến Dịch Marketing
Ticket: SCRUM-30 / SCRUM-99
Vai trò: Nhân viên Marketing (Marketing Specialist)

Tiêu chí chấp nhận:
1. Số lead, tỷ lệ được nhận, tỷ lệ chuyển đổi thành cơ hội theo từng nguồn và từng chiến dịch.
2. Lọc theo khoảng thời gian linh hoạt.
3. Xuất Excel (.xlsx).
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
    send_file,
    jsonify
)

from config import (
    TICKET_ID,
    PARENT_EPIC,
    SOURCES,
    SOURCE_ICONS,
    SOURCE_COLORS,
    ROLE_MARKETING,
    ROLE_SALES_REP,
    ROLE_TEAM_LEAD,
    ROLE_DIRECTOR,
    ROLE_LABELS,
    STATUS_NEW,
    STATUS_ACCEPTED,
    STATUS_OPPORTUNITY,
    STATUS_WON,
    STATUS_REJECTED,
    STATUS_LOST,
    STATUS_LABELS,
    DEFAULT_PORT
)
from database import (
    db,
    format_currency,
    format_percent,
    format_datetime,
    format_date
)
from excel_exporter import generate_excel_report

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "scrum-99-marketing-report-secret-key-2026")


# Jinja2 Filters
@app.template_filter("vi_currency")
def vi_currency_filter(amount):
    return format_currency(amount)


@app.template_filter("vi_percent")
def vi_percent_filter(rate):
    return format_percent(rate)


@app.template_filter("vi_datetime")
def vi_datetime_filter(dt):
    return format_datetime(dt)


@app.template_filter("vi_date")
def vi_date_filter(dt):
    return format_date(dt)


# Globals
@app.context_processor
def inject_globals():
    current_user_id = session.get("user_id", "usr-mkt-01")
    current_user = db.users.get(current_user_id, db.users["usr-mkt-01"])

    return {
        "db": db,
        "current_user": current_user,
        "all_users": db.users,
        "TICKET_ID": TICKET_ID,
        "PARENT_EPIC": PARENT_EPIC,
        "SOURCES": SOURCES,
        "SOURCE_ICONS": SOURCE_ICONS,
        "SOURCE_COLORS": SOURCE_COLORS,
        "STATUS_LABELS": STATUS_LABELS,
        "now": datetime.now()
    }


# =============================================================================
# 0. CHUYỂN ĐỔI NGƯỜI DÙNG GIẢ LẬP (PERSONA SWITCHER)
# =============================================================================
@app.route("/switch-user/<user_id>")
def switch_user(user_id):
    if user_id in db.users:
        session["user_id"] = user_id
        flash(f"Đã chuyển đổi sang tài khoản: {db.users[user_id]['name']} ({db.users[user_id]['role_name']})", "info")
    return redirect(request.referrer or url_for("report_view"))


# =============================================================================
# 1. BÁO CÁO HIỆU QUẢ NGUỒN LEAD & CHIẾN DỊCH (CORE VIEW)
# =============================================================================
@app.route("/")
@app.route("/report")
def report_view():
    preset = request.args.get("preset", "all")
    from_date_str = request.args.get("from_date", "")
    to_date_str = request.args.get("to_date", "")

    # Phân giải khoảng thời gian
    from_dt, to_dt = db.parse_date_range(preset=preset, from_date_str=from_date_str, to_date_str=to_date_str)

    # Nhãn hiển thị khoảng thời gian
    preset_labels = {
        "all": "Toàn bộ thời gian",
        "today": "Hôm nay",
        "last_7_days": "7 ngày gần nhất",
        "last_30_days": "30 ngày gần nhất",
        "this_month": "Tháng này",
        "this_quarter": "Quý này",
        "custom": f"Từ {from_date_str} đến {to_date_str}" if from_date_str else "Tùy chọn"
    }
    date_label = preset_labels.get(preset, "Toàn bộ thời gian")

    # Tính toán báo cáo nguồn lead & chiến dịch
    source_reports = db.get_report_by_source(from_dt, to_dt)
    campaign_reports = db.get_report_by_campaign(from_dt, to_dt)
    summary_metrics = db.get_summary_metrics(from_dt, to_dt)

    return render_template(
        "report.html",
        preset=preset,
        from_date=from_date_str,
        to_date=to_date_str,
        date_label=date_label,
        source_reports=source_reports,
        campaign_reports=campaign_reports,
        summary=summary_metrics
    )


# =============================================================================
# 2. XUẤT BÁO CÁO EXCEL (TIÊU CHÍ 3)
# =============================================================================
@app.route("/export/excel")
def export_excel():
    preset = request.args.get("preset", "all")
    from_date_str = request.args.get("from_date", "")
    to_date_str = request.args.get("to_date", "")

    from_dt, to_dt = db.parse_date_range(preset=preset, from_date_str=from_date_str, to_date_str=to_date_str)

    preset_labels = {
        "all": "Toàn bộ thời gian",
        "today": "Hôm nay",
        "last_7_days": "7 ngày gần nhất",
        "last_30_days": "30 ngày gần nhất",
        "this_month": "Tháng này",
        "this_quarter": "Quý này",
        "custom": f"Từ {from_date_str} đến {to_date_str}" if from_date_str else "Tùy chọn"
    }
    date_label = preset_labels.get(preset, "Toàn bộ thời gian")

    excel_file = generate_excel_report(db, from_dt=from_dt, to_dt=to_dt, date_label=date_label)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"Bao_Cao_Hieu_Qua_Nguon_Lead_SCRUM-99_{timestamp}.xlsx"

    return send_file(
        excel_file,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename
    )


# =============================================================================
# 3. QUẢN LÝ CHIẾN DỊCH MARKETING
# =============================================================================
@app.route("/campaigns")
def campaigns_view():
    preset = request.args.get("preset", "all")
    from_date_str = request.args.get("from_date", "")
    to_date_str = request.args.get("to_date", "")

    from_dt, to_dt = db.parse_date_range(preset=preset, from_date_str=from_date_str, to_date_str=to_date_str)
    campaign_reports = db.get_report_by_campaign(from_dt, to_dt)

    return render_template(
        "campaigns.html",
        campaign_reports=campaign_reports,
        preset=preset
    )


# =============================================================================
# 4. DANH SÁCH LEAD CHI TIẾT (DRILL-DOWN)
# =============================================================================
@app.route("/leads")
def leads_view():
    source = request.args.get("source")
    campaign_id = request.args.get("campaign_id")
    status = request.args.get("status")
    preset = request.args.get("preset", "all")
    from_date_str = request.args.get("from_date", "")
    to_date_str = request.args.get("to_date", "")

    from_dt, to_dt = db.parse_date_range(preset=preset, from_date_str=from_date_str, to_date_str=to_date_str)
    leads = db.get_leads_filtered(from_dt=from_dt, to_dt=to_dt, source=source, campaign_id=campaign_id, status=status)

    return render_template(
        "leads_list.html",
        leads=leads,
        selected_source=source,
        selected_campaign=campaign_id,
        selected_status=status,
        preset=preset
    )


# =============================================================================
# 5. REST APIs DÀNH CHO BIỂU ĐỒ & DỊCH VỤ NGOÀI
# =============================================================================
@app.route("/api/report/source")
def api_report_source():
    preset = request.args.get("preset", "all")
    from_dt, to_dt = db.parse_date_range(preset=preset)
    data = db.get_report_by_source(from_dt, to_dt)
    return jsonify({"success": True, "data": data})


@app.route("/api/report/campaign")
def api_report_campaign():
    preset = request.args.get("preset", "all")
    from_dt, to_dt = db.parse_date_range(preset=preset)
    data = db.get_report_by_campaign(from_dt, to_dt)
    return jsonify({"success": True, "data": data})


@app.route("/api/report/summary")
def api_report_summary():
    preset = request.args.get("preset", "all")
    from_dt, to_dt = db.parse_date_range(preset=preset)
    data = db.get_summary_metrics(from_dt, to_dt)
    return jsonify({"success": True, "data": data})


# =============================================================================
# 6. RESET DATA
# =============================================================================
@app.route("/reset-data")
def reset_data():
    db.reset_demo_data()
    flash("Đã đặt lại dữ liệu mẫu phân tích ban đầu!", "info")
    return redirect(url_for("report_view"))


if __name__ == "__main__":
    print("=" * 70)
    print("  BÁO CÁO HIỆU QUẢ NGUỒN LEAD & CHIẾN DỊCH MARKETING - TICKET SCRUM-99")
    print(f"  Khởi chạy máy chủ tại: http://127.0.0.1:{DEFAULT_PORT}")
    print("=" * 70)
    app.run(host="127.0.0.1", port=DEFAULT_PORT, debug=True)
