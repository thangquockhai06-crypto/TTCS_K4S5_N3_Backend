"""
Ứng Dụng Flask - Hệ Thống Soạn Báo Giá Từ Cơ Hội (SCRUM-35 / SCRUM-31)
User Story: "Là Nhân viên kinh doanh, tôi muốn soạn báo giá từ một cơ hội, để gửi báo giá trong buổi chiều cùng ngày khách hỏi."

5 Tiêu chí chấp nhận:
1. Dòng sản phẩm được kế thừa từ cơ hội, sửa lại được.
2. Mỗi dòng nhập chiết khấu theo phần trăm hoặc số tiền, hệ thống tính lại thành tiền ngay.
3. Hiển thị mức chiết khấu tổng và cảnh báo khi chạm ngưỡng cần duyệt.
4. Khai báo hiệu lực báo giá, điều khoản thanh toán và điều khoản giao hàng.
5. Lưu nháp và sửa tiếp được.
"""

import os
import sys
import json
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
    STATUS_DRAFT,
    STATUS_PENDING_APPROVAL,
    STATUS_APPROVED,
    STATUS_SENT,
    STATUS_ACCEPTED,
    STATUS_REJECTED,
    STATUS_EXPIRED,
    STATUS_LABELS,
    STATUS_COLORS,
    STATUS_BADGE_CLASSES,
    DISCOUNT_APPROVAL_THRESHOLD_PERCENT,
    DISCOUNT_WARNING_THRESHOLD_PERCENT,
    DISCOUNT_TYPE_PERCENT,
    DISCOUNT_TYPE_AMOUNT,
    DISCOUNT_TYPE_LABELS,
    DEFAULT_VAT_PERCENT,
    VALIDITY_PRESETS,
    PAYMENT_TERMS_PRESETS,
    DELIVERY_TERMS_PRESETS,
    ROLE_SALES_REP,
    ROLE_TEAM_LEAD,
    ROLE_DIRECTOR,
    ROLE_LABELS,
    PRODUCT_CATALOG,
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
app.secret_key = os.environ.get("SECRET_KEY", "scrum-31-quotation-secret-key-2026")


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


# Middleware nạp thông tin người dùng và context chung
@app.context_processor
def inject_global_context():
    user_id = session.get("user_id", "usr-01")
    current_user = db.get_user(user_id)
    if not current_user:
        current_user = db.get_user("usr-01")
        session["user_id"] = "usr-01"

    all_users = db.get_all_users()
    kpis = db.get_kpis()

    return {
        "current_user": current_user,
        "all_users": all_users,
        "kpis": kpis,
        "TICKET_ID": TICKET_ID,
        "PARENT_EPIC": PARENT_EPIC,
        "DISCOUNT_APPROVAL_THRESHOLD_PERCENT": DISCOUNT_APPROVAL_THRESHOLD_PERCENT,
        "DISCOUNT_WARNING_THRESHOLD_PERCENT": DISCOUNT_WARNING_THRESHOLD_PERCENT,
        "VALIDITY_PRESETS": VALIDITY_PRESETS,
        "PAYMENT_TERMS_PRESETS": PAYMENT_TERMS_PRESETS,
        "DELIVERY_TERMS_PRESETS": DELIVERY_TERMS_PRESETS,
        "STATUS_LABELS": STATUS_LABELS,
        "STATUS_BADGE_CLASSES": STATUS_BADGE_CLASSES
    }


# =========================================================================
# WEB ROUTES
# =========================================================================

@app.route("/")
@app.route("/dashboard")
def dashboard():
    """Trang Bàn làm việc Sales Rep: Cơ hội chờ báo giá & Danh sách báo giá gần đây"""
    user_id = session.get("user_id", "usr-01")
    opportunities = db.get_all_opportunities()
    recent_quotes = db.get_all_quotes()[:6]
    draft_quotes = [q for q in db.get_all_quotes() if q.get("status") == STATUS_DRAFT]
    pending_quotes = [q for q in db.get_all_quotes() if q.get("status") == STATUS_PENDING_APPROVAL]

    return render_template(
        "dashboard.html",
        opportunities=opportunities,
        recent_quotes=recent_quotes,
        draft_quotes=draft_quotes,
        pending_quotes=pending_quotes
    )


@app.route("/opportunities")
def opportunities_list():
    """Danh sách Cơ hội bán hàng - Điểm xuất phát để Soạn Báo Giá (AC1)"""
    opportunities = db.get_all_opportunities()
    return render_template("opportunities_list.html", opportunities=opportunities)


@app.route("/quotes")
def quotes_list():
    """Danh sách tất cả Báo giá với bộ lọc trạng thái (Bản nháp, Chờ duyệt, Đã gửi...)"""
    status_filter = request.args.get("status")
    quotes = db.get_all_quotes(status=status_filter)
    return render_template(
        "quotes_list.html",
        quotes=quotes,
        current_status=status_filter
    )


@app.route("/quotes/new/<opp_id>", methods=["GET", "POST"])
def quote_create(opp_id):
    """
    AC1: Kế thừa dòng sản phẩm từ Cơ hội và tạo Báo giá mới
    AC2: Nhập chiết khấu theo % hoặc tiền, tính lại ngay
    AC3: Cảnh báo khi chạm ngưỡng cần duyệt
    AC4: Khai báo hiệu lực, điều khoản thanh toán & giao hàng
    AC5: Lưu nháp và sửa tiếp được
    """
    user_id = session.get("user_id", "usr-01")
    opp = db.get_opportunity(opp_id)
    if not opp:
        flash(f"Không tìm thấy cơ hội bán hàng: {opp_id}", "danger")
        return redirect(url_for("opportunities_list"))

    if request.method == "POST":
        action = request.form.get("action", "save_draft")
        # Thu thập dữ liệu từ form
        form_data = parse_quote_form_data(request.form)

        try:
            # 1. Tạo quote mới kế thừa từ cơ hội (AC1)
            quote = db.create_quote_from_opportunity(opp_id, user_id)
            quote_id = quote["id"]

            # 2. Cập nhật các dòng sản phẩm, chiết khấu và điều khoản từ form (AC1, AC2, AC3, AC4)
            updated_quote = db.save_draft(quote_id, form_data, user_id)

            if action == "submit":
                # Nộp báo giá: nếu chạm ngưỡng cần duyệt -> PENDING_APPROVAL, ngược lại -> SENT
                submitted_quote = db.submit_quote(quote_id, user_id)
                if submitted_quote.get("status") == STATUS_PENDING_APPROVAL:
                    flash(
                        f"⚠️ Báo giá {submitted_quote['quote_number']} có chiết khấu {submitted_quote['overall_discount_percent']}% "
                        f"(vượt ngưỡng 10%). Đã chuyển sang trạng thái CHỜ DUYỆT CHIẾT KHẤU!",
                        "warning"
                    )
                else:
                    flash(
                        f"🎉 Báo giá {submitted_quote['quote_number']} đã hoàn tất và gửi khách hàng thành công trong buổi chiều!",
                        "success"
                    )
                return redirect(url_for("quote_detail", quote_id=quote_id))
            else:
                flash(f"💾 Đã lưu nháp báo giá {updated_quote['quote_number']}. Bạn có thể tiếp tục chỉnh sửa bất kỳ lúc nào!", "info")
                return redirect(url_for("quote_edit", quote_id=quote_id))

        except Exception as e:
            flash(f"Lỗi khi xử lý báo giá: {str(e)}", "danger")
            return redirect(url_for("opportunities_list"))

    # GET: Hiển thị form tạo mới với các dòng sản phẩm kế thừa từ Cơ hội
    catalog = db.get_all_products()
    return render_template(
        "quote_create.html",
        opp=opp,
        catalog=catalog
    )


@app.route("/quotes/<quote_id>")
def quote_detail(quote_id):
    """Xem chi tiết Báo giá - Hồ sơ thương mại chuẩn B2B"""
    quote = db.get_quote(quote_id)
    if not quote:
        flash(f"Không tìm thấy báo giá: {quote_id}", "danger")
        return redirect(url_for("quotes_list"))

    return render_template("quote_detail.html", quote=quote)


@app.route("/quotes/<quote_id>/edit", methods=["GET", "POST"])
def quote_edit(quote_id):
    """
    AC5: Lưu nháp và sửa tiếp được
    Cho phép mở lại bản nháp, sửa số lượng, giá, chiết khấu từng dòng (% hoặc tiền),
    thêm/xóa sản phẩm, cập nhật điều khoản thanh toán & giao hàng.
    """
    user_id = session.get("user_id", "usr-01")
    quote = db.get_quote(quote_id)
    if not quote:
        flash(f"Không tìm thấy báo giá: {quote_id}", "danger")
        return redirect(url_for("quotes_list"))

    if not quote.get("can_edit", True):
        flash(f"Báo giá {quote['quote_number']} đang ở trạng thái '{quote['status_label']}' nên không thể chỉnh sửa!", "warning")
        return redirect(url_for("quote_detail", quote_id=quote_id))

    if request.method == "POST":
        action = request.form.get("action", "save_draft")
        form_data = parse_quote_form_data(request.form)

        try:
            updated_quote = db.save_draft(quote_id, form_data, user_id)

            if action == "submit":
                submitted_quote = db.submit_quote(quote_id, user_id)
                if submitted_quote.get("status") == STATUS_PENDING_APPROVAL:
                    flash(
                        f"⚠️ Báo giá {submitted_quote['quote_number']} có chiết khấu {submitted_quote['overall_discount_percent']}% "
                        f"(vượt ngưỡng 10%). Đã chuyển sang trạng thái CHỜ DUYỆT CHIẾT KHẤU!",
                        "warning"
                    )
                else:
                    flash(
                        f"🎉 Báo giá {submitted_quote['quote_number']} đã được duyệt gửi khách hàng ngay trong buổi chiều!",
                        "success"
                    )
                return redirect(url_for("quote_detail", quote_id=quote_id))
            else:
                flash(f"💾 Đã lưu nháp phiên bản v{updated_quote['draft_version']} cho {updated_quote['quote_number']} thành công!", "success")
                return redirect(url_for("quote_edit", quote_id=quote_id))

        except Exception as e:
            flash(f"Lỗi khi lưu báo giá: {str(e)}", "danger")

    catalog = db.get_all_products()
    return render_template(
        "quote_edit.html",
        quote=quote,
        catalog=catalog
    )


@app.route("/quotes/<quote_id>/submit", methods=["POST"])
def quote_submit(quote_id):
    """Gửi duyệt hoặc gửi khách hàng từ trang chi tiết"""
    user_id = session.get("user_id", "usr-01")
    try:
        quote = db.submit_quote(quote_id, user_id)
        if quote.get("status") == STATUS_PENDING_APPROVAL:
            flash(f"⚠️ Báo giá {quote['quote_number']} chiết khấu {quote['overall_discount_percent']}% >= 10%. Đã gửi tới Trưởng nhóm chờ duyệt!", "warning")
        else:
            flash(f"🎉 Báo giá {quote['quote_number']} đã gửi khách hàng thành công!", "success")
    except Exception as e:
        flash(f"Lỗi: {str(e)}", "danger")
    return redirect(url_for("quote_detail", quote_id=quote_id))


@app.route("/quotes/<quote_id>/approve", methods=["POST"])
def quote_approve(quote_id):
    """Duyệt chiết khấu báo giá (Dành cho Trưởng nhóm / Giám đốc)"""
    user_id = session.get("user_id", "usr-01")
    note = request.form.get("approval_note", "")
    try:
        quote = db.approve_quote(quote_id, user_id, note)
        flash(f"✅ Đã phê duyệt mức chiết khấu cho Báo giá {quote['quote_number']} thành công!", "success")
    except Exception as e:
        flash(f"Lỗi phê duyệt: {str(e)}", "danger")
    return redirect(url_for("quote_detail", quote_id=quote_id))


@app.route("/quotes/<quote_id>/reject", methods=["POST"])
def quote_reject(quote_id):
    """Từ chối duyệt chiết khấu báo giá, trả lại cho NVKD sửa tiếp (AC3 & AC5)"""
    user_id = session.get("user_id", "usr-01")
    reason = request.form.get("rejection_reason", "")
    try:
        quote = db.reject_quote(quote_id, user_id, reason)
        flash(f"❌ Đã từ chối duyệt chiết khấu Báo giá {quote['quote_number']}. Trả về cho NVKD sửa lại!", "warning")
    except Exception as e:
        flash(f"Lỗi từ chối: {str(e)}", "danger")
    return redirect(url_for("quote_detail", quote_id=quote_id))


@app.route("/quotes/<quote_id>/print")
def quote_print(quote_id):
    """Mẫu in Báo giá thương mại B2B A4 chuyên nghiệp"""
    quote = db.get_quote(quote_id)
    if not quote:
        flash(f"Không tìm thấy báo giá: {quote_id}", "danger")
        return redirect(url_for("quotes_list"))
    return render_template("quote_print.html", quote=quote)


@app.route("/simulator")
def simulator():
    """Trình kiểm thử & Chấm điểm 5 Tiêu chí Chấp nhận tự động (Interactive Simulator)"""
    return render_template("simulator.html")


# =========================================================================
# REST APIS & HỖ TRỢ TÍNH TOÁN REALTIME CHO CLIENT JAVASCRIPT
# =========================================================================

@app.route("/api/calculate-line", methods=["POST"])
def api_calculate_line():
    """API tính toán dòng sản phẩm tức thời cho frontend"""
    data = request.get_json() or {}
    result = db.calculate_line_item(data)
    return jsonify(result)


@app.route("/api/calculate-totals", methods=["POST"])
def api_calculate_totals():
    """API tính toán tổng hợp chiết khấu & kiểm tra ngưỡng duyệt tức thời (AC2 & AC3)"""
    data = request.get_json() or {}
    items = data.get("items", [])
    processed_items = [db.calculate_line_item(itm) for itm in items]
    totals = db.calculate_quote_totals(processed_items)
    totals["items"] = processed_items
    return jsonify(totals)


@app.route("/api/product-catalog")
def api_product_catalog():
    """API lấy danh mục sản phẩm chuẩn"""
    products = db.get_all_products()
    return jsonify(products)


@app.route("/api/run-simulator-tests", methods=["POST", "GET"])
def api_run_simulator():
    """API thực thi kiểm thử 5 Tiêu chí chấp nhận và trả về kết quả thời gian thực"""
    results = []

    # AC1: Kế thừa dòng sản phẩm từ cơ hội, sửa lại được
    try:
        opp = db.get_opportunity("OPP-401")
        initial_opp_items_count = len(opp["line_items"])
        quote = db.create_quote_from_opportunity("OPP-401", "usr-01")
        ac1_inherited = (len(quote["items"]) == initial_opp_items_count)
        
        # Thử sửa dòng sản phẩm: Thêm 1 sản phẩm mới
        new_items = list(quote["items"])
        new_items.append({
            "product_id": "PRD-004",
            "product_code": "SRV-INTEGRATION",
            "product_name": "Gói Tích Hợp API Đa Kênh",
            "unit": "Hệ thống",
            "quantity": 1,
            "unit_price": 8000000,
            "discount_type": DISCOUNT_TYPE_PERCENT,
            "discount_value": 0
        })
        updated = db.save_draft(quote["id"], {"items": new_items}, "usr-01")
        ac1_editable = (len(updated["items"]) == initial_opp_items_count + 1)

        results.append({
            "id": "AC1",
            "title": "Tiêu chí 1: Dòng sản phẩm được kế thừa từ cơ hội, sửa lại được",
            "status": "PASSED" if (ac1_inherited and ac1_editable) else "FAILED",
            "details": f"Kế thừa chính xác {len(quote['items'])} dòng sản phẩm từ OPP-401. Đã kiểm tra sửa đổi và thêm sản phẩm thành công (từ {initial_opp_items_count} lên {len(updated['items'])} dòng)."
        })
    except Exception as e:
        results.append({
            "id": "AC1",
            "title": "Tiêu chí 1: Dòng sản phẩm được kế thừa từ cơ hội, sửa lại được",
            "status": "FAILED",
            "details": f"Lỗi: {str(e)}"
        })

    # AC2: Nhập chiết khấu theo % hoặc tiền, tính lại thành tiền ngay
    try:
        # Test chiết khấu theo % (10%)
        item_percent = db.calculate_line_item({
            "quantity": 2,
            "unit_price": 10000000,  # 20.000.000 đ
            "discount_type": DISCOUNT_TYPE_PERCENT,
            "discount_value": 10.0
        })
        percent_pass = (item_percent["discount_amount"] == 2000000.0 and item_percent["total"] == 18000000.0)

        # Test chiết khấu theo số tiền cố định (3.000.000 đ)
        item_amount = db.calculate_line_item({
            "quantity": 1,
            "unit_price": 15000000,  # 15.000.000 đ
            "discount_type": DISCOUNT_TYPE_AMOUNT,
            "discount_value": 3000000.0
        })
        amount_pass = (item_amount["discount_amount"] == 3000000.0 and item_amount["total"] == 12000000.0)

        results.append({
            "id": "AC2",
            "title": "Tiêu chí 2: Mỗi dòng nhập chiết khấu theo % hoặc số tiền, tính lại thành tiền ngay",
            "status": "PASSED" if (percent_pass and amount_pass) else "FAILED",
            "details": f"Đã kiểm thử cả 2 chế độ chiết khấu: Chiết khấu 10% (giảm {format_currency(item_percent['discount_amount'])}, còn {format_currency(item_percent['total'])}) & Chiết khấu số tiền {format_currency(3000000)} (còn {format_currency(item_amount['total'])}). Tính toán chính xác 100%."
        })
    except Exception as e:
        results.append({
            "id": "AC2",
            "title": "Tiêu chí 2: Mỗi dòng nhập chiết khấu theo % hoặc số tiền, tính lại thành tiền ngay",
            "status": "FAILED",
            "details": f"Lỗi: {str(e)}"
        })

    # AC3: Hiển thị mức chiết khấu tổng và cảnh báo khi chạm ngưỡng cần duyệt
    try:
        # Trường hợp 1: Chiết khấu dưới ngưỡng (5% < 10%)
        totals_low = db.calculate_quote_totals([
            {"subtotal": 100000000, "discount_amount": 5000000}
        ])
        low_pass = (totals_low["overall_discount_percent"] == 5.0 and not totals_low["is_approval_required"])

        # Trường hợp 2: Chiết khấu chạm/vượt ngưỡng duyệt (15% >= 10%)
        totals_high = db.calculate_quote_totals([
            {"subtotal": 100000000, "discount_amount": 15000000}
        ])
        high_pass = (totals_high["overall_discount_percent"] == 15.0 and totals_high["is_approval_required"] and len(totals_high["warning_message"]) > 0)

        results.append({
            "id": "AC3",
            "title": "Tiêu chí 3: Hiển thị mức chiết khấu tổng và cảnh báo khi chạm ngưỡng cần duyệt",
            "status": "PASSED" if (low_pass and high_pass) else "FAILED",
            "details": f"Chiết khấu tổng được tính chuẩn xác: Mức 5.0% < ngưỡng 10% (Không cần duyệt); Mức 15.0% >= ngưỡng 10% (Kích hoạt cờ is_approval_required=True và hiển thị thông báo cảnh báo màu đỏ)."
        })
    except Exception as e:
        results.append({
            "id": "AC3",
            "title": "Tiêu chí 3: Hiển thị mức chiết khấu tổng và cảnh báo khi chạm ngưỡng cần duyệt",
            "status": "FAILED",
            "details": f"Lỗi: {str(e)}"
        })

    # AC4: Khai báo hiệu lực báo giá, điều khoản thanh toán và điều khoản giao hàng
    try:
        quote = db.get_quote("QUOTE-501")
        has_validity = bool(quote.get("valid_until") and quote.get("validity_days"))
        has_payment = bool(quote.get("payment_terms"))
        has_delivery = bool(quote.get("delivery_terms"))

        results.append({
            "id": "AC4",
            "title": "Tiêu chí 4: Khai báo hiệu lực báo giá, điều khoản thanh toán và điều khoản giao hàng",
            "status": "PASSED" if (has_validity and has_payment and has_delivery) else "FAILED",
            "details": f"Hiệu lực báo giá: {quote.get('validity_days')} ngày (Hết hạn ngày {quote.get('valid_until')}). Điều khoản thanh toán và giao hàng được khai báo đầy đủ, cho phép chọn mẫu có sẵn hoặc nhập tùy biến."
        })
    except Exception as e:
        results.append({
            "id": "AC4",
            "title": "Tiêu chí 4: Khai báo hiệu lực báo giá, điều khoản thanh toán và điều khoản giao hàng",
            "status": "FAILED",
            "details": f"Lỗi: {str(e)}"
        })

    # AC5: Lưu nháp và sửa tiếp được
    try:
        quote_draft = db.get_quote("QUOTE-501")
        v_before = quote_draft.get("draft_version", 1)
        # Thực hiện lưu nháp tiếp tục
        updated_draft = db.save_draft(
            "QUOTE-501",
            {
                "title": quote_draft["title"] + " (Cập nhật)",
                "items": quote_draft["items"],
                "notes": "Lưu nháp bổ sung vào buổi chiều."
            },
            "usr-01"
        )
        v_after = updated_draft.get("draft_version", 1)
        ac5_pass = (updated_draft["status"] == STATUS_DRAFT and updated_draft["can_edit"] and v_after > v_before)

        results.append({
            "id": "AC5",
            "title": "Tiêu chí 5: Lưu nháp và sửa tiếp được",
            "status": "PASSED" if ac5_pass else "FAILED",
            "details": f"Báo giá giữ nguyên trạng thái DRAFT (Bản nháp), can_edit=True cho phép sửa không giới hạn số lần. Phiên bản nháp tự động tăng từ v{v_before} lên v{v_after}."
        })
    except Exception as e:
        results.append({
            "id": "AC5",
            "title": "Tiêu chí 5: Lưu nháp và sửa tiếp được",
            "status": "FAILED",
            "details": f"Lỗi: {str(e)}"
        })

    return jsonify({"results": results, "timestamp": datetime.now().strftime("%H:%M:%S %d/%m/%Y")})


# =========================================================================
# UTILITIES & SYSTEM CONTROL
# =========================================================================

def parse_quote_form_data(form):
    """Phân tích dữ liệu POST từ form gửi lên"""
    title = form.get("title", "")
    validity_days = form.get("validity_days", 15)
    valid_until_custom = form.get("valid_until_custom", "")
    payment_terms = form.get("payment_terms", "")
    delivery_terms = form.get("delivery_terms", "")
    warranty_terms = form.get("warranty_terms", "")
    notes = form.get("notes", "")

    # Phân tích danh sách sản phẩm
    item_ids = form.getlist("item_id[]")
    product_ids = form.getlist("product_id[]")
    product_codes = form.getlist("product_code[]")
    product_names = form.getlist("product_name[]")
    units = form.getlist("unit[]")
    quantities = form.getlist("quantity[]")
    unit_prices = form.getlist("unit_price[]")
    discount_types = form.getlist("discount_type[]")
    discount_values = form.getlist("discount_value[]")
    descriptions = form.getlist("description[]")

    items = []
    for i in range(len(product_names)):
        p_name = product_names[i].strip() if i < len(product_names) else ""
        if not p_name:
            continue
        items.append({
            "item_id": item_ids[i] if i < len(item_ids) else None,
            "product_id": product_ids[i] if i < len(product_ids) else None,
            "product_code": product_codes[i] if i < len(product_codes) else "PRD-CUSTOM",
            "product_name": p_name,
            "unit": units[i] if i < len(units) else "Cái",
            "quantity": float(quantities[i]) if (i < len(quantities) and quantities[i]) else 1.0,
            "unit_price": float(unit_prices[i]) if (i < len(unit_prices) and unit_prices[i]) else 0.0,
            "discount_type": discount_types[i] if i < len(discount_types) else DISCOUNT_TYPE_PERCENT,
            "discount_value": float(discount_values[i]) if (i < len(discount_values) and discount_values[i]) else 0.0,
            "description": descriptions[i] if i < len(descriptions) else ""
        })

    return {
        "title": title,
        "validity_days": validity_days,
        "valid_until_custom": valid_until_custom,
        "payment_terms": payment_terms,
        "delivery_terms": delivery_terms,
        "warranty_terms": warranty_terms,
        "notes": notes,
        "items": items
    }


@app.route("/switch-user/<user_id>")
def switch_user(user_id):
    """Chuyển đổi vai trò người dùng (Sales Rep vs Team Lead vs Director)"""
    user = db.get_user(user_id)
    if user:
        session["user_id"] = user_id
        flash(f"Đã chuyển sang vai trò: {user['name']} ({user['role_name']})", "info")
    return redirect(request.referrer or url_for("dashboard"))


@app.route("/reset-data")
def reset_data():
    """Khôi phục dữ liệu mẫu ban đầu"""
    db.reset_demo_data()
    flash("Đã đặt lại dữ liệu mẫu thành công!", "success")
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", DEFAULT_PORT))
    print(f"=================================================================")
    print(f" HỆ THỐNG SOẠN BÁO GIÁ TỪ CƠ HỘI - {TICKET_ID} (EPIC {PARENT_EPIC})")
    print(f" Khởi động Flask Server tại: http://127.0.0.1:{port}")
    print(f"=================================================================")
    app.run(host="0.0.0.0", port=port, debug=True)


def calculate_tiered_discount(quantity: int, unit_price: float) -> float:
    """Tính chiết khấu bậc thang theo số lượng hàng hóa đặt mua"""
    if quantity >= 100: return unit_price * 0.15
    elif quantity >= 50: return unit_price * 0.10
    elif quantity >= 20: return unit_price * 0.05
    return 0.0
