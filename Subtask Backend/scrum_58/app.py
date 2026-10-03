"""
ỨNG DỤNG QUẢN LÝ NGƯỜI LIÊN HỆ & VAI TRÒ TRONG QUYẾT ĐỊNH MUA (B2B CRM)
========================================================================
Mã Nhiệm Vụ: SCRUM-50 / SCRUM-58
User Story:
  "Là Nhân viên kinh doanh, tôi muốn quản lý người liên hệ và vai trò của họ
   trong quyết định mua, để biết phải thuyết phục ai và ai là người có thể cản thương vụ."

Đáp ứng 100% 4 Tiêu chí chấp nhận (Description):
  1. Mỗi khách hàng có nhiều người liên hệ, mỗi người có chức danh, email, số điện thoại.
  2. Đánh dấu vai trò trong quyết định mua: người quyết định, người ảnh hưởng,
     người dùng cuối, người cản trở.
  3. Đánh dấu một người là đầu mối chính (duy nhất 1 đầu mối chính tại mỗi khách hàng).
  4. Một người liên hệ chuyển sang công ty khác thì gắn lại được sang khách hàng mới,
     giữ nguyên lịch sử công tác và vai trò cũ.
========================================================================
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
    BUYING_ROLES,
    get_all_customers,
    get_customer,
    create_customer,
    get_all_contacts,
    get_contacts_by_customer,
    get_contact,
    add_contact,
    update_contact,
    delete_contact,
    set_primary_contact,
    transfer_contact_to_new_customer,
    get_buying_decision_matrix,
    reset_database,
    validate_email_address,
    validate_phone_number,
    DB_CUSTOMERS,
    DB_CONTACTS
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "scrum-58-buying-roles-matrix-secret-2026")


# ==============================================================================
# HÀM BỔ TRỢ & CONTEXT PROCESSOR TOÀN CỤC
# ==============================================================================
@app.context_processor
def inject_global_data():
    """Cung cấp các biến hệ thống vào tất cả Jinja2 templates."""
    customers = get_all_customers()
    contacts = get_all_contacts()
    
    # Tính toán tổng hợp số lượng 4 vai trò mua trên toàn hệ thống
    total_decision_makers = sum(1 for c in contacts if c.get("buying_role") == "decision_maker")
    total_influencers = sum(1 for c in contacts if c.get("buying_role") == "influencer")
    total_end_users = sum(1 for c in contacts if c.get("buying_role") == "end_user")
    total_blockers = sum(1 for c in contacts if c.get("buying_role") == "blocker")
    
    return {
        "global_customers": customers,
        "buying_roles": BUYING_ROLES,
        "total_contacts_count": len(contacts),
        "total_customers_count": len(customers),
        "total_decision_makers": total_decision_makers,
        "total_influencers": total_influencers,
        "total_end_users": total_end_users,
        "total_blockers": total_blockers,
        "current_sales_rep": {
            "name": "Nguyễn Hoàng Phúc",
            "code": "SR089",
            "title": "Chuyên Viên Kinh Doanh Doanh Nghiệp (Enterprise Sales Rep)",
            "email": "phuc.nguyen@crm-enterprise.vn"
        }
    }


# ==============================================================================
# 1. TRANG BẢNG ĐIỀU KHIỂN & DANH SÁCH NGƯỜI LIÊN HỆ TOÀN CỤC
# ==============================================================================
@app.route("/")
def index():
    """
    Trang chủ: Danh sách tất cả người liên hệ có bộ lọc đa tiêu chí:
    - Tìm kiếm theo từ khóa (tên, chức danh, email, SĐT)
    - Lọc theo Khách hàng
    - Lọc theo Vai trò trong quyết định mua (Người quyết định, Người ảnh hưởng, Người dùng cuối, Người cản trở)
    """
    customer_id = request.args.get("customer_id")
    buying_role = request.args.get("buying_role")
    keyword = request.args.get("q")

    contacts = get_all_contacts(
        customer_id=customer_id,
        buying_role=buying_role,
        keyword=keyword
    )

    selected_customer = get_customer(customer_id) if customer_id else None

    return render_template(
        "index.html",
        contacts=contacts,
        selected_customer_id=customer_id,
        selected_buying_role=buying_role,
        keyword=keyword or "",
        selected_customer=selected_customer
    )


# ==============================================================================
# 2. QUẢN LÝ KHÁCH HÀNG & MA TRẬN QUYẾT ĐỊNH MUA (BUYING CENTER MATRIX)
# ==============================================================================
@app.route("/customers")
def customers_list():
    """Danh sách các khách hàng doanh nghiệp kèm chỉ số phân bổ người liên hệ."""
    customers = get_all_customers()
    return render_template("customers.html", customers=customers)


@app.route("/customers/create", methods=["GET", "POST"])
def customer_create():
    """Tạo mới một khách hàng doanh nghiệp."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        code = request.form.get("code", "").strip()
        industry = request.form.get("industry", "").strip()
        scale = request.form.get("scale", "").strip()
        address = request.form.get("address", "").strip()
        website = request.form.get("website", "").strip()
        status = request.form.get("status", "Tiếp cận ban đầu").strip()
        estimated_value = request.form.get("estimated_value", "0")

        if not name or not code:
            flash("Vui lòng nhập tên công ty và mã khách hàng!", "danger")
            return redirect(url_for("customer_create"))

        try:
            val = int(estimated_value or 0)
        except ValueError:
            val = 0

        cust = create_customer(
            name=name,
            code=code,
            industry=industry,
            scale=scale,
            address=address,
            website=website,
            status=status,
            estimated_value=val
        )
        flash(f"Đã tạo thành công khách hàng '{cust['name']}'!", "success")
        return redirect(url_for("customer_detail", customer_id=cust["id"]))

    return render_template("customer_form.html")


@app.route("/customers/<customer_id>")
def customer_detail(customer_id):
    """
    Trang chi tiết Khách hàng & MA TRẬN QUYẾT ĐỊNH MUA HÀNG (Buying Decision Matrix / Power Map):
    - Trực quan hóa 4 nhóm vai trò:
      + 🎯 Người quyết định (Decision Maker)
      + 💡 Người ảnh hưởng (Influencer)
      + 👤 Người dùng cuối (End User)
      + ⚠️ Người cản trở (Blocker)
    - Đánh giá sức khỏe thương vụ & Gợi ý chiến lược cho Nhân viên kinh doanh.
    - Đánh dấu và đổi nhanh Đầu mối chính (Primary Contact).
    """
    try:
        matrix_data = get_buying_decision_matrix(customer_id)
    except ValueError as e:
        flash(str(e), "danger")
        return redirect(url_for("customers_list"))

    return render_template(
        "customer_detail.html",
        matrix_data=matrix_data,
        customer=matrix_data["customer"]
    )


# ==============================================================================
# 3. QUẢN LÝ NGƯỜI LIÊN HỆ: THÊM, SỬA, XÓA, ĐẦU MỐI CHÍNH
# ==============================================================================
@app.route("/contacts/create", methods=["GET", "POST"])
def contact_create():
    """
    Thêm mới người liên hệ cho một khách hàng.
    Đáp ứng Tiêu chí 1: Đầy đủ chức danh, email, số điện thoại.
    Đáp ứng Tiêu chí 2: Chọn 1 trong 4 vai trò mua.
    Đáp ứng Tiêu chí 3: Tùy chọn đánh dấu là đầu mối chính.
    """
    preset_customer_id = request.args.get("customer_id")

    if request.method == "POST":
        customer_id = request.form.get("customer_id", "").strip()
        full_name = request.form.get("full_name", "").strip()
        job_title = request.form.get("job_title", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        buying_role = request.form.get("buying_role", "influencer").strip()
        is_primary = request.form.get("is_primary") == "on"
        notes = request.form.get("notes", "").strip()
        support_level = request.form.get("support_level", "Ủng hộ").strip()

        try:
            new_contact = add_contact(
                customer_id=customer_id,
                full_name=full_name,
                job_title=job_title,
                email=email,
                phone=phone,
                buying_role=buying_role,
                is_primary=is_primary,
                notes=notes,
                support_level=support_level
            )
            flash(
                f"Đã thêm thành công người liên hệ '{new_contact['full_name']}' với vai trò '{BUYING_ROLES[buying_role]['name']}'!",
                "success"
            )
            return redirect(url_for("customer_detail", customer_id=customer_id))
        except ValueError as err:
            flash(str(err), "danger")
            return render_template(
                "contact_form.html",
                is_edit=False,
                preset_customer_id=customer_id,
                form_data=request.form
            )

    return render_template(
        "contact_form.html",
        is_edit=False,
        preset_customer_id=preset_customer_id,
        form_data={}
    )


@app.route("/contacts/<contact_id>")
def contact_detail(contact_id):
    """
    Xem chi tiết hồ sơ người liên hệ, vai trò quyết định mua,
    và ĐẶC BIỆT LÀ: DÒNG THỜI GIAN LỊCH SỬ CÔNG TÁC (CAREER HISTORY TIMELINE)
    thể hiện đầy đủ Tiêu chí 4 khi chuyển công tác sang công ty khác.
    """
    contact = get_contact(contact_id)
    if not contact:
        flash(f"Không tìm thấy người liên hệ {contact_id}!", "danger")
        return redirect(url_for("index"))

    customer = get_customer(contact["customer_id"])
    return render_template(
        "contact_detail.html",
        contact=contact,
        customer=customer
    )


@app.route("/contacts/<contact_id>/edit", methods=["GET", "POST"])
def contact_edit(contact_id):
    """Chỉnh sửa thông tin người liên hệ."""
    contact = get_contact(contact_id)
    if not contact:
        flash(f"Không tìm thấy người liên hệ {contact_id}!", "danger")
        return redirect(url_for("index"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        job_title = request.form.get("job_title", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        buying_role = request.form.get("buying_role", "influencer").strip()
        is_primary = request.form.get("is_primary") == "on"
        notes = request.form.get("notes", "").strip()
        support_level = request.form.get("support_level", "Ủng hộ").strip()

        try:
            updated = update_contact(
                contact_id=contact_id,
                full_name=full_name,
                job_title=job_title,
                email=email,
                phone=phone,
                buying_role=buying_role,
                is_primary=is_primary,
                notes=notes,
                support_level=support_level
            )
            flash(f"Đã cập nhật thông tin người liên hệ '{updated['full_name']}'!", "success")
            return redirect(url_for("contact_detail", contact_id=contact_id))
        except ValueError as err:
            flash(str(err), "danger")

    return render_template(
        "contact_form.html",
        is_edit=True,
        contact=contact,
        preset_customer_id=contact["customer_id"],
        form_data=contact
    )


@app.route("/contacts/<contact_id>/delete", methods=["POST"])
def contact_delete(contact_id):
    """Xóa một người liên hệ."""
    contact = get_contact(contact_id)
    cust_id = contact["customer_id"] if contact else None
    if delete_contact(contact_id):
        flash(f"Đã xóa người liên hệ {contact_id} khỏi hệ thống!", "info")
    else:
        flash("Không thể xóa người liên hệ này!", "danger")

    if cust_id:
        return redirect(url_for("customer_detail", customer_id=cust_id))
    return redirect(url_for("index"))


# ==============================================================================
# 4. TIÊU CHÍ 3: THIẾT LẬP ĐẦU MỐI CHÍNH (PRIMARY CONTACT)
# ==============================================================================
@app.route("/customers/<customer_id>/set-primary/<contact_id>", methods=["POST"])
def set_primary(customer_id, contact_id):
    """
    Đặt một người làm đầu mối chính của khách hàng.
    Tự động gỡ cờ của người cũ.
    """
    try:
        set_primary_contact(customer_id, contact_id)
        contact = get_contact(contact_id)
        flash(f"⭐ Đã đặt '{contact['full_name']}' làm Đầu Mối Chính cho khách hàng này!", "success")
    except ValueError as err:
        flash(str(err), "danger")

    # Điều hướng lại trang phù hợp
    referrer = request.referrer
    if referrer and "contacts" in referrer:
        return redirect(url_for("contact_detail", contact_id=contact_id))
    return redirect(url_for("customer_detail", customer_id=customer_id))


# ==============================================================================
# 5. TIÊU CHÍ 4: CHUYỂN CÔNG TÁC SANG KHÁCH HÀNG MỚI & LƯU LỊCH SỬ NGUYÊN VẸN
# ==============================================================================
@app.route("/contacts/<contact_id>/transfer", methods=["GET", "POST"])
def contact_transfer(contact_id):
    """
    Giao diện và xử lý chuyển người liên hệ sang khách hàng mới:
    - Chọn công ty mới
    - Nhập chức danh mới, email mới, SĐT mới, vai trò mua mới
    - Ghi nhận lý do chuyển và lưu lại toàn bộ dấu vết lịch sử cũ
    """
    contact = get_contact(contact_id)
    if not contact:
        flash(f"Không tìm thấy người liên hệ {contact_id}!", "danger")
        return redirect(url_for("index"))

    current_customer = get_customer(contact["customer_id"])
    all_customers = get_all_customers()
    # Loại bỏ công ty hiện tại khỏi danh sách chọn công ty mới
    available_customers = [c for c in all_customers if c["id"] != contact["customer_id"]]

    if request.method == "POST":
        new_customer_id = request.form.get("new_customer_id", "").strip()
        new_job_title = request.form.get("new_job_title", "").strip()
        new_email = request.form.get("new_email", "").strip()
        new_phone = request.form.get("new_phone", "").strip()
        new_buying_role = request.form.get("new_buying_role", "").strip()
        is_primary_at_new = request.form.get("is_primary_at_new") == "on"
        transfer_reason = request.form.get("transfer_reason", "").strip()
        sales_impact_note = request.form.get("sales_impact_note", "").strip()

        try:
            transferred = transfer_contact_to_new_customer(
                contact_id=contact_id,
                new_customer_id=new_customer_id,
                new_job_title=new_job_title,
                new_email=new_email if new_email else None,
                new_phone=new_phone if new_phone else None,
                new_buying_role=new_buying_role if new_buying_role else None,
                is_primary_at_new_customer=is_primary_at_new,
                transfer_reason=transfer_reason,
                sales_impact_note=sales_impact_note
            )
            new_cust = get_customer(new_customer_id)
            flash(
                f"🎉 Chuyển công tác thành công! '{transferred['full_name']}' hiện thuộc '{new_cust['name']}'. Toàn bộ lịch sử công tác trước đó đã được lưu trữ an toàn!",
                "success"
            )
            return redirect(url_for("contact_detail", contact_id=contact_id))
        except ValueError as err:
            flash(str(err), "danger")

    return render_template(
        "contact_transfer.html",
        contact=contact,
        current_customer=current_customer,
        available_customers=available_customers
    )


# ==============================================================================
# 6. RESTFUL API ENDPOINTS (HỖ TRỢ TÍCH HỢP AJAX & KIỂM THỬ)
# ==============================================================================
@app.route("/api/contacts", methods=["GET", "POST"])
def api_contacts():
    """API lấy danh sách hoặc tạo người liên hệ qua JSON."""
    if request.method == "POST":
        data = request.get_json() or {}
        try:
            c = add_contact(
                customer_id=data.get("customer_id"),
                full_name=data.get("full_name"),
                job_title=data.get("job_title"),
                email=data.get("email"),
                phone=data.get("phone"),
                buying_role=data.get("buying_role", "influencer"),
                is_primary=bool(data.get("is_primary", False)),
                notes=data.get("notes", ""),
                support_level=data.get("support_level", "Ủng hộ")
            )
            return jsonify({"success": True, "contact": c}), 201
        except ValueError as err:
            return jsonify({"success": False, "error": str(err)}), 400

    # GET
    cid = request.args.get("customer_id")
    role = request.args.get("buying_role")
    kw = request.args.get("q")
    contacts = get_all_contacts(customer_id=cid, buying_role=role, keyword=kw)
    return jsonify({"success": True, "count": len(contacts), "contacts": contacts})


@app.route("/api/contacts/<contact_id>", methods=["GET"])
def api_contact_detail(contact_id):
    """API lấy chi tiết một người liên hệ."""
    c = get_contact(contact_id)
    if not c:
        return jsonify({"success": False, "error": "Not Found"}), 404
    return jsonify({"success": True, "contact": c})


@app.route("/api/contacts/<contact_id>/transfer", methods=["POST"])
def api_contact_transfer(contact_id):
    """API chuyển công tác sang công ty mới."""
    data = request.get_json() or {}
    try:
        updated = transfer_contact_to_new_customer(
            contact_id=contact_id,
            new_customer_id=data.get("new_customer_id"),
            new_job_title=data.get("new_job_title"),
            new_email=data.get("new_email"),
            new_phone=data.get("new_phone"),
            new_buying_role=data.get("new_buying_role"),
            is_primary_at_new_customer=bool(data.get("is_primary_at_new", False)),
            transfer_reason=data.get("transfer_reason", ""),
            sales_impact_note=data.get("sales_impact_note", "")
        )
        return jsonify({"success": True, "contact": updated}), 200
    except ValueError as err:
        return jsonify({"success": False, "error": str(err)}), 400


@app.route("/api/customers/<customer_id>/set-primary/<contact_id>", methods=["POST"])
def api_set_primary(customer_id, contact_id):
    """API đặt đầu mối chính."""
    try:
        set_primary_contact(customer_id, contact_id)
        return jsonify({"success": True, "message": "Primary contact updated"})
    except ValueError as err:
        return jsonify({"success": False, "error": str(err)}), 400


@app.route("/api/customers/<customer_id>/matrix", methods=["GET"])
def api_matrix(customer_id):
    """API lấy ma trận 4 vai trò quyết định mua."""
    try:
        matrix = get_buying_decision_matrix(customer_id)
        return jsonify({"success": True, "data": matrix})
    except ValueError as err:
        return jsonify({"success": False, "error": str(err)}), 400


# ==============================================================================
# 7. KHÔI PHỤC DỮ LIỆU MẪU & XỬ LÝ LỖI
# ==============================================================================
@app.route("/reset-demo-data", methods=["POST", "GET"])
def reset_demo():
    """Khôi phục dữ liệu ban đầu cho kịch bản demo."""
    reset_database()
    flash("✨ Đã khôi phục dữ liệu mẫu về trạng thái chuẩn ban đầu!", "info")
    return redirect(url_for("index"))


@app.errorhandler(404)
def page_not_found(e):
    return render_template("errors/404.html"), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template("errors/500.html"), 500


# ==============================================================================
# KHỞI CHẠY MÁY CHỦ (MAIN ENTRYPOINT)
# ==============================================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5058))
    print(f"\n========================================================")
    print(f"🚀 MÁY CHỦ SCRUM-58 ĐANG KHỞI CHẠY TRÊN CỔNG: {port}")
    print(f"📍 TRUY CẬP ỨNG DỤNG TẠI: http://localhost:{port}")
    print(f"========================================================\n")
    app.run(host="0.0.0.0", port=port, debug=True)
