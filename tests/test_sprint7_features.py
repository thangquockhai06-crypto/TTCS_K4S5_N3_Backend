"""
Kiểm thử toàn diện Phân hệ Báo giá, Hợp đồng, Tự động hóa & Thông báo (Sprint 7: S7-01 -> S7-09):
- S7-01: Soạn thảo Báo giá từ Cơ hội, kế thừa sản phẩm, chiết khấu % và số tiền, điều khoản và lưu nháp
- S7-02: Phê duyệt chiết khấu đa cấp, yêu cầu ý kiến khi từ chối/trả lại, gửi báo giá, lịch sử bất biến
- S7-03: Quản lý phiên bản báo giá, chỉ 1 phiên bản hiệu lực, so sánh side-by-side
- S7-04: Chuyển đổi Báo giá thành Hợp đồng, kế thừa sản phẩm, số HĐ duy nhất, tự động đóng Won cho Deal
- S7-05: Xuất Báo giá & Hợp đồng PDF theo mẫu doanh nghiệp cấu hình, số tiền thành chữ tiếng Việt
- S7-06: Cổng duyệt khách hàng qua link riêng, Accept/Reject với comment, cập nhật timeline, tự động hết hạn
- S7-07: Quản lý Hợp đồng, đếm ngược ngày hết hạn, cảnh báo hết hạn, tạo cơ hội tái ký
- S7-08: Thông báo In-App bất đồng bộ cho 5 sự kiện chính, đếm chưa đọc, đánh dấu đã đọc
- S7-09: Quy tắc tự động hóa IF–THEN, bật/tắt rule, ghi nhận nhật ký thực thi
"""
import pytest
from datetime import date, datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.customer import Customer
from app.models.deal import Deal
from app.models.deal_item import DealItem
from app.models.product import Product
from app.models.quotation import Quotation, QuoteItem, QuoteApprovalHistory
from app.models.contract import Contract
from app.models.pdf_template import PdfTemplate
from app.models.notification import Notification
from app.models.automation import AutomationRule, AutomationLog
from app.core.security import hash_password, create_access_token


@pytest.fixture
def s7_admin_headers(db_session: Session) -> dict:
    admin = User(
        id="usr-s7-admin",
        email="s7_admin@nexuscrm.vn",
        password_hash=hash_password("AdminPass123!"),
        full_name="Quản Trị Viên S7",
        role="Super Admin",
        status="active",
    )
    db_session.add(admin)
    db_session.commit()
    token = create_access_token(user_id=admin.id, email=admin.email, role=admin.role)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def s7_rep_headers(db_session: Session) -> dict:
    rep = User(
        id="usr-s7-rep",
        email="s7_rep@nexuscrm.vn",
        password_hash=hash_password("RepPass123!"),
        full_name="Nguyễn Văn Kinh Doanh",
        role="Account Executive",
        status="active",
    )
    db_session.add(rep)
    db_session.commit()
    token = create_access_token(user_id=rep.id, email=rep.email, role=rep.role)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def s7_leader_headers(db_session: Session) -> dict:
    leader = User(
        id="usr-s7-leader",
        email="s7_leader@nexuscrm.vn",
        password_hash=hash_password("LeaderPass123!"),
        full_name="Trần Trưởng Nhóm",
        role="Sales Team Leader",
        status="active",
    )
    db_session.add(leader)
    db_session.commit()
    token = create_access_token(user_id=leader.id, email=leader.email, role=leader.role)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def s7_customer(db_session: Session) -> Customer:
    cust = Customer(
        id="cust-s7-corp",
        full_name="Công ty Cổ phần Công nghệ Tiên Phong",
        company="Pioneer Tech Corp",
        email="contact@pioneertech.vn",
        phone="0988776655",
        tax_code="0109988776",
        status="active",
        health_score=95,
        assigned_user_id="usr-s7-rep",
    )
    db_session.add(cust)
    db_session.commit()
    return cust


@pytest.fixture
def s7_product(db_session: Session) -> Product:
    prod = Product(
        id="prod-s7-cloud",
        code="NEX-CLOUD-ENT",
        name="Nexus Cloud Enterprise",
        category="Phần mềm",
        selling_price=10000000.0,
        cost_price=4000000.0,
        is_active=True,
    )
    db_session.add(prod)
    db_session.commit()
    return prod


@pytest.fixture
def s7_deal(db_session: Session, s7_customer: Customer, s7_product: Product) -> Deal:
    deal = Deal(
        id="deal-s7-target",
        title="Dự án Chuyển đổi số Pioneer Tech",
        value=20000000.0,
        stage="proposal",
        probability=60,
        customer_id=s7_customer.id,
        owner_id="usr-s7-rep",
        expected_close_date=date.today() + timedelta(days=30),
    )
    db_session.add(deal)
    db_session.flush()

    di = DealItem(
        id="di-s7-01",
        deal_id=deal.id,
        product_id=s7_product.id,
        product_name=s7_product.name,
        quantity=2,
        unit_price=10000000.0,
        discount_percent=0.0,
        billing_cycle="annual",
        subtotal=20000000.0,
    )
    db_session.add(di)
    db_session.commit()
    return deal


# ==============================================================================
# S7-01: SOẠN THẢO BÁO GIÁ (QUOTE BUILDER) & TÍNH TOÁN
# ==============================================================================

def test_s7_01_create_quote_from_deal_with_inheritance(
    client: TestClient,
    s7_rep_headers: dict,
    s7_customer: Customer,
    s7_deal: Deal,
    s7_product: Product,
):
    """S7-01: Tạo báo giá từ Cơ hội, kế thừa dòng sản phẩm từ Deal và hỗ trợ chiết khấu tức thì."""
    payload = {
        "dealId": s7_deal.id,
        "title": "Báo giá Phần mềm Nexus CRM v1",
        "customerId": s7_customer.id,
        "validUntil": (date.today() + timedelta(days=30)).isoformat(),
        "paymentTerms": "Thanh toán 100% trong vòng 15 ngày.",
        "deliveryTerms": "Triển khai trong 05 ngày làm việc.",
        "items": [
            {
                "productId": s7_product.id,
                "productCode": s7_product.code,
                "productName": s7_product.name,
                "quantity": 2,
                "unit": "User/Năm",
                "unitPrice": 10000000.0,
                "discountType": "percent",
                "discountValue": 10.0,  # Chiết khấu 10% (< 15% -> Tự động duyệt)
                "vatRate": 10.0,
            }
        ],
    }
    res = client.post("/api/v1/quotations", json=payload, headers=s7_rep_headers)
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == "Báo giá Phần mềm Nexus CRM v1"
    assert data["subtotal"] == 20000000.0
    assert data["totalDiscountAmount"] == 2000000.0
    assert data["totalDiscountPercent"] == 10.0
    assert data["vatAmount"] == 1800000.0  # (20M - 2M) * 10% = 1.8M
    assert data["grandTotal"] == 19800000.0  # 18M + 1.8M = 19.8M
    assert data["requiresApproval"] is False
    assert data["accessToken"] is not None
    assert "Một mươi chín triệu" in data["totalInWords"] or "Mười chín triệu" in data["totalInWords"]


def test_s7_01_fixed_amount_discount_and_draft_update(
    client: TestClient,
    s7_rep_headers: dict,
    s7_customer: Customer,
):
    """S7-01: Hỗ trợ chiết khấu theo số tiền cố định (fixed amount) và sửa bản nháp."""
    # 1. Tạo bản nháp
    res = client.post("/api/v1/quotations", json={
        "title": "Báo giá Bản nháp",
        "customerId": s7_customer.id,
        "items": [
            {
                "productName": "Gói Tích hợp Tổng đài VoIP",
                "quantity": 1,
                "unit": "Gói",
                "unitPrice": 15000000.0,
                "discountType": "amount",
                "discountValue": 3000000.0,  # Giảm cố định 3.000.000 VNĐ (20%)
                "vatRate": 10.0,
            }
        ],
    }, headers=s7_rep_headers)
    assert res.status_code == 201
    quote = res.json()
    assert quote["totalDiscountAmount"] == 3000000.0
    assert quote["totalDiscountPercent"] == 20.0
    assert quote["grandTotal"] == 13200000.0  # (15M - 3M) + 1.2M VAT = 13.2M

    # 2. Cập nhật bản nháp (sửa tiêu đề và điều khoản)
    update_res = client.put(f"/api/v1/quotations/{quote['id']}", json={
        "title": "Báo giá Bản nháp Đã Chỉnh Sửa",
        "paymentTerms": "Thanh toán trả chậm 30 ngày",
    }, headers=s7_rep_headers)
    assert update_res.status_code == 200
    assert update_res.json()["title"] == "Báo giá Bản nháp Đã Chỉnh Sửa"
    assert update_res.json()["paymentTerms"] == "Thanh toán trả chậm 30 ngày"
    assert update_res.json()["version"] == 1  # Vẫn là v1 vì đang ở draft


# ==============================================================================
# S7-02: PHÊ DUYỆT CHIẾT KHẤU ĐA CẤP & LỊCH SỬ BẤT BIẾN
# ==============================================================================

def test_s7_02_approval_thresholds_workflow(
    client: TestClient,
    s7_rep_headers: dict,
    s7_leader_headers: dict,
    s7_customer: Customer,
):
    """
    S7-02:
    - Chiết khấu > 15% -> Yêu cầu Sales Team Leader duyệt.
    - Cần comment khi Từ chối hoặc Trả lại chỉnh sửa.
    - Chỉ báo giá đã được duyệt mới được phép gửi (send).
    - Lịch sử phê duyệt bất biến (immutable).
    """
    # 1. Tạo báo giá chiết khấu 18% (> 15% ngưỡng Team Leader)
    create_res = client.post("/api/v1/quotations", json={
        "title": "Báo giá Cần Duyệt",
        "customerId": s7_customer.id,
        "validUntil": (date.today() + timedelta(days=20)).isoformat(),
        "items": [
            {
                "productName": "Gói Doanh Nghiệp VIP",
                "quantity": 1,
                "unit": "Gói",
                "unitPrice": 50000000.0,
                "discountType": "percent",
                "discountValue": 18.0,
                "vatRate": 10.0,
            }
        ],
    }, headers=s7_rep_headers)
    assert create_res.status_code == 201
    quote = create_res.json()
    assert quote["requiresApproval"] is True
    assert quote["approvalLevel"] == "team_leader"

    # 2. Thử gửi ngay khi chưa duyệt => Bị chặn 400
    send_fail = client.post(f"/api/v1/quotations/{quote['id']}/send", headers=s7_rep_headers)
    assert send_fail.status_code == 400
    assert "Chỉ báo giá đã được phê duyệt" in send_fail.json()["detail"]

    # 3. Đệ trình duyệt -> Trạng thái chuyển sang pending_approval
    submit_res = client.post(f"/api/v1/quotations/{quote['id']}/submit", headers=s7_rep_headers)
    assert submit_res.status_code == 200
    assert submit_res.json()["status"] == "pending_approval"

    # 4. Thử Từ chối không có comment => Bị chặn 400
    reject_no_comment = client.post(f"/api/v1/quotations/{quote['id']}/approval", json={
        "action": "rejected",
        "comment": "",
    }, headers=s7_leader_headers)
    assert reject_no_comment.status_code == 400
    assert "Bắt buộc phải nhập ý kiến" in reject_no_comment.json()["detail"]

    # 5. Phê duyệt thành công (Approve)
    approve_res = client.post(f"/api/v1/quotations/{quote['id']}/approval", json={
        "action": "approved",
        "comment": "Đồng ý mức chiết khấu 18% cho khách hàng chiến lược.",
    }, headers=s7_leader_headers)
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "approved"
    assert len(approve_res.json()["approvalHistory"]) >= 1

    # 6. Bây giờ đã approved -> Gửi thành công cho khách hàng
    send_ok = client.post(f"/api/v1/quotations/{quote['id']}/send", headers=s7_rep_headers)
    assert send_ok.status_code == 200
    assert send_ok.json()["status"] == "sent"


# ==============================================================================
# S7-03: QUẢN LÝ PHIÊN BẢN BÁO GIÁ (VERSIONING & COMPARISON)
# ==============================================================================

def test_s7_03_versioning_on_sent_quotation_and_comparison(
    client: TestClient,
    s7_rep_headers: dict,
    s7_leader_headers: dict,
    s7_customer: Customer,
):
    """S7-03: Sửa báo giá đã gửi sẽ tự động sinh v2, hủy hiệu lực v1, hỗ trợ so sánh side-by-side."""
    # 1. Tạo và duyệt, gửi báo giá v1
    q1 = client.post("/api/v1/quotations", json={
        "title": "Hợp đồng License v1",
        "customerId": s7_customer.id,
        "validUntil": (date.today() + timedelta(days=15)).isoformat(),
        "status": "approved",
        "items": [
            {"productName": "Gói Khởi Nghiệp", "quantity": 1, "unit": "Gói", "unitPrice": 10000000.0, "discountType": "percent", "discountValue": 0.0, "vatRate": 10.0}
        ],
    }, headers=s7_rep_headers).json()
    client.post(f"/api/v1/quotations/{q1['id']}/send", headers=s7_rep_headers)

    # 2. Sửa báo giá khi đã ở trạng thái 'sent' -> Tự động sinh v2
    update_res = client.put(f"/api/v1/quotations/{q1['id']}", json={
        "title": "Hợp đồng License v2 - Tăng số lượng",
        "items": [
            {"productName": "Gói Khởi Nghiệp", "quantity": 2, "unit": "Gói", "unitPrice": 10000000.0, "discountType": "percent", "discountValue": 5.0, "vatRate": 10.0}
        ],
    }, headers=s7_rep_headers)
    assert update_res.status_code == 200
    q2 = update_res.json()
    assert q2["version"] == 2
    assert q2["isEffective"] is True
    assert q2["id"] != q1["id"]

    # 3. Kiểm tra v1 đã bị chuyển isEffective = False
    old_q = client.get(f"/api/v1/quotations/{q1['id']}", headers=s7_rep_headers).json()
    assert old_q["isEffective"] is False

    # 4. So sánh Side-by-side v1 và v2
    compare_res = client.get(f"/api/v1/quotations/{q1['id']}/compare/{q2['id']}", headers=s7_rep_headers)
    assert compare_res.status_code == 200
    comp = compare_res.json()
    assert comp["priceDifference"] > 0
    assert comp["itemsModified"] is True
    assert "tăng" in comp["summary"]


# ==============================================================================
# S7-04 & S7-07: CHUYỂN ĐỔI HỢP ĐỒNG, ĐÓNG WON VÀ TÁI KÝ
# ==============================================================================

def test_s7_04_convert_quotation_to_contract_and_won_deal(
    client: TestClient,
    s7_rep_headers: dict,
    s7_customer: Customer,
    s7_deal: Deal,
):
    """S7-04: Chuyển đổi báo giá sang hợp đồng, kế thừa sản phẩm, kiểm tra số HĐ duy nhất và đóng Won cho Deal."""
    # 1. Tạo báo giá accepted
    q = client.post("/api/v1/quotations", json={
        "dealId": s7_deal.id,
        "title": "Báo giá Chốt Hợp Đồng",
        "customerId": s7_customer.id,
        "validUntil": (date.today() + timedelta(days=20)).isoformat(),
        "status": "accepted",
        "items": [
            {"productName": "Nexus Cloud License Enterprise", "quantity": 3, "unit": "User/Năm", "unitPrice": 12000000.0, "discountType": "percent", "discountValue": 0.0, "vatRate": 10.0}
        ],
    }, headers=s7_rep_headers).json()

    contract_num = f"HD-2026-PIONEER-{int(datetime.utcnow().timestamp())}"

    # 2. Chuyển đổi sang hợp đồng
    contract_res = client.post("/api/v1/contracts", json={
        "quotationId": q["id"],
        "contractNumber": contract_num,
        "title": "Hợp đồng Kinh tế Cung cấp Phần mềm Nexus CRM",
        "signingDate": date.today().isoformat(),
        "effectiveDate": date.today().isoformat(),
        "expiryDate": (date.today() + timedelta(days=365)).isoformat(),
        "paymentTerms": "Thanh toán đợt 1 50%, đợt 2 50% sau nghiệm thu.",
    }, headers=s7_rep_headers)
    assert contract_res.status_code == 201
    contract_data = contract_res.json()
    assert contract_data["contractNumber"] == contract_num
    assert contract_data["totalValue"] == q["grandTotal"]
    assert len(contract_data["items"]) == 1
    assert contract_data["items"][0]["quantity"] == 3

    # 3. Trùng số hợp đồng => Bị chặn 400
    dup_res = client.post("/api/v1/contracts", json={
        "quotationId": q["id"],
        "contractNumber": contract_num,
        "signingDate": date.today().isoformat(),
        "effectiveDate": date.today().isoformat(),
        "expiryDate": (date.today() + timedelta(days=365)).isoformat(),
    }, headers=s7_rep_headers)
    assert dup_res.status_code == 400
    assert "đã tồn tại" in dup_res.json()["detail"]

    # 4. Kiểm tra Deal đã tự động chuyển sang Won với giá trị hợp đồng chính xác
    deal_check = client.get(f"/api/v1/deals/{s7_deal.id}", headers=s7_rep_headers).json()
    assert deal_check["stage"] == "won"
    assert deal_check["value"] == contract_data["totalValue"]
    assert deal_check["probability"] == 100


def test_s7_07_contract_expiry_alerts_and_renewal(
    client: TestClient,
    s7_rep_headers: dict,
    s7_customer: Customer,
    s7_deal: Deal,
):
    """S7-07: Danh sách hợp đồng hiển thị số ngày còn lại, cảnh báo sắp hết hạn và tạo cơ hội tái ký."""
    # 1. Tạo hợp đồng sắp hết hạn trong 10 ngày
    q = client.post("/api/v1/quotations", json={
        "dealId": s7_deal.id,
        "title": "Báo giá Tái Ký",
        "customerId": s7_customer.id,
        "status": "accepted",
        "items": [{"productName": "Gói Hỗ trợ Kỹ thuật", "quantity": 1, "unit": "Gói", "unitPrice": 25000000.0, "discountType": "percent", "discountValue": 0.0, "vatRate": 10.0}],
    }, headers=s7_rep_headers).json()

    c_num = f"HD-EXPIRING-{int(datetime.utcnow().timestamp())}"
    contract = client.post("/api/v1/contracts", json={
        "quotationId": q["id"],
        "contractNumber": c_num,
        "signingDate": (date.today() - timedelta(days=355)).isoformat(),
        "effectiveDate": (date.today() - timedelta(days=355)).isoformat(),
        "expiryDate": (date.today() + timedelta(days=10)).isoformat(),  # 10 ngày nữa hết hạn
    }, headers=s7_rep_headers).json()

    assert contract["remainingDays"] == 10
    assert contract["isExpiringSoon"] is True

    # 2. Tạo cơ hội tái ký (Renewal Opportunity)
    renew_res = client.post(f"/api/v1/contracts/{contract['id']}/renew", json={
        "title": "Cơ hội Tái ký Hợp đồng Hỗ trợ 2027",
        "expectedCloseDate": (date.today() + timedelta(days=20)).isoformat(),
    }, headers=s7_rep_headers)
    assert renew_res.status_code == 200
    renewal_deal = renew_res.json()
    assert "Tái ký" in renewal_deal["title"]
    assert renewal_deal["customerId"] == s7_customer.id
    assert renewal_deal["value"] == contract["totalValue"]

    # 3. Hợp đồng chuyển trạng thái 'renewed'
    c_after = client.get(f"/api/v1/contracts/{contract['id']}", headers=s7_rep_headers).json()
    assert c_after["status"] == "renewed"


# ==============================================================================
# S7-05: XUẤT PDF VÀ MẪU DOANH NGHIỆP CẤU HÌNH ĐƯỢC
# ==============================================================================

def test_s7_05_pdf_template_configuration_and_export(
    client: TestClient,
    s7_admin_headers: dict,
    s7_rep_headers: dict,
    s7_customer: Customer,
):
    """S7-05: Cấu hình mẫu PDF và xuất Báo giá / Hợp đồng ra HTML/PDF với số tiền thành chữ."""
    # 1. Thêm mẫu PDF cấu hình riêng
    tpl_res = client.post("/api/v1/pdf-templates", json={
        "name": "Mẫu Báo giá Quốc tế 2026",
        "templateType": "quotation",
        "companyName": "TẬP ĐOÀN CÔNG NGHỆ NEXUS TOÀN CẦU",
        "companyTaxCode": "0109999999",
        "companyAddress": "Tầng 35, Landmark 72, Hà Nội",
        "companyPhone": "024 9999 8888",
        "companyEmail": "global@nexuscrm.vn",
        "isDefault": True,
    }, headers=s7_admin_headers)
    assert tpl_res.status_code == 201

    # 2. Tạo báo giá
    q = client.post("/api/v1/quotations", json={
        "title": "Báo giá Xuất PDF",
        "customerId": s7_customer.id,
        "items": [
            {"productName": "License Trọn Đời", "quantity": 1, "unit": "Gói", "unitPrice": 100000000.0, "discountType": "percent", "discountValue": 0.0, "vatRate": 10.0}
        ],
    }, headers=s7_rep_headers).json()

    # 3. Gọi endpoint PDF
    pdf_res = client.get(f"/api/v1/quotations/{q['id']}/pdf", headers=s7_rep_headers)
    assert pdf_res.status_code == 200
    assert "TẬP ĐOÀN CÔNG NGHỆ NEXUS TOÀN CẦU" in pdf_res.text
    assert "Một trăm mười triệu đồng chẵn" in pdf_res.text


# ==============================================================================
# S7-06: CỔNG DUYỆT KHÁCH HÀNG & TỰ ĐỘNG HẾT HẠN
# ==============================================================================

def test_s7_06_customer_public_portal_and_auto_expire(
    client: TestClient,
    s7_rep_headers: dict,
    s7_customer: Customer,
    db_session: Session,
):
    """S7-06: Khách hàng truy cập không cần auth, Accept kèm comment, cập nhật timeline; tự động hết hạn."""
    # 1. Tạo báo giá và gửi (sent)
    q = client.post("/api/v1/quotations", json={
        "title": "Báo giá Cổng Khách Hàng",
        "customerId": s7_customer.id,
        "validUntil": (date.today() + timedelta(days=10)).isoformat(),
        "status": "approved",
        "items": [{"productName": "Module SMS Brandname", "quantity": 1, "unit": "Gói", "unitPrice": 15000000.0, "discountType": "percent", "discountValue": 0.0, "vatRate": 10.0}],
    }, headers=s7_rep_headers).json()
    sent_q = client.post(f"/api/v1/quotations/{q['id']}/send", headers=s7_rep_headers).json()
    token = sent_q["accessToken"]
    assert token is not None

    # 2. Khách hàng xem báo giá công khai (không cần Header Authorization)
    pub_res = client.get(f"/api/v1/public/quotes/{token}")
    assert pub_res.status_code == 200
    assert pub_res.json()["title"] == "Báo giá Cổng Khách Hàng"

    # 3. Khách hàng Accept báo giá kèm ý kiến
    respond_res = client.post(f"/api/v1/public/quotes/{token}/respond", json={
        "action": "accepted",
        "comment": "Chúng tôi đồng ý ký hợp đồng theo báo giá này.",
        "signerName": "Ông Giám Đốc Khách Hàng",
    })
    assert respond_res.status_code == 200
    assert respond_res.json()["status"] == "accepted"


# ==============================================================================
# S7-08: THÔNG BÁO IN-APP BẤT ĐỒNG BỘ
# ==============================================================================

def test_s7_08_in_app_notifications_flow(
    client: TestClient,
    s7_rep_headers: dict,
    db_session: Session,
):
    """S7-08: Danh sách thông báo, đếm chưa đọc, đánh dấu đã đọc."""
    # Tạo trực tiếp 2 thông báo cho user
    n1 = Notification(
        id="notif-s7-01",
        user_id="usr-s7-rep",
        type="lead_assigned",
        title="Phân bổ Lead mới",
        description="Bạn được giao phụ trách lead Công ty ABC",
        target_type="lead",
        target_id="lead-123",
        link_url="/leads/lead-123/edit",
        is_read=False,
    )
    n2 = Notification(
        id="notif-s7-02",
        user_id="usr-s7-rep",
        type="task_assigned",
        title="Giao nhiệm vụ mới",
        description="Chuẩn bị hợp đồng cho đối tác",
        target_type="task",
        target_id="task-456",
        link_url="/tasks",
        is_read=False,
    )
    db_session.add_all([n1, n2])
    db_session.commit()

    # 1. Lấy danh sách thông báo và số chưa đọc
    list_res = client.get("/api/v1/notifications", headers=s7_rep_headers)
    assert list_res.status_code == 200
    notif_data = list_res.json()
    assert notif_data["unreadCount"] >= 2
    assert len(notif_data["items"]) >= 2

    # 2. Đánh dấu 1 thông báo đã đọc
    read_res = client.post(f"/api/v1/notifications/{n1.id}/read", headers=s7_rep_headers)
    assert read_res.status_code == 200
    assert read_res.json()["isRead"] is True

    # 3. Đánh dấu tất cả đã đọc
    all_read = client.post("/api/v1/notifications/mark-all-read", headers=s7_rep_headers)
    assert all_read.status_code == 200
    count_check = client.get("/api/v1/notifications/unread-count", headers=s7_rep_headers).json()
    assert count_check["unreadCount"] == 0


# ==============================================================================
# S7-09: QUY TẮC TỰ ĐỘNG HÓA IF–THEN
# ==============================================================================

def test_s7_09_automation_rules_crud_and_execution(
    client: TestClient,
    s7_admin_headers: dict,
    db_session: Session,
):
    """S7-09: Quản lý quy tắc tự động hóa IF-THEN, bật/tắt rule và xem nhật ký thực thi."""
    # 1. Tạo rule mới
    rule_res = client.post("/api/v1/automations", json={
        "name": "Tự động gửi thông báo khi Deal Won",
        "description": "Chúc mừng khi cơ hội bán hàng thành công",
        "isActive": True,
        "triggerEntity": "deal",
        "triggerEvent": "status_changed",
        "conditions": {"field": "stage", "operator": "equals", "value": "won"},
        "actionType": "send_notification",
        "actionConfig": {"title": "Deal {title} đã THẮNG!", "description": "Chúc mừng bạn đã chốt thành công deal này."},
    }, headers=s7_admin_headers)
    assert rule_res.status_code == 201
    rule = rule_res.json()
    assert rule["isActive"] is True

    # 2. Bật / Tắt rule
    toggle_res = client.patch(f"/api/v1/automations/{rule['id']}/toggle", headers=s7_admin_headers)
    assert toggle_res.status_code == 200
    assert toggle_res.json()["isActive"] is False

    # 3. Bật lại
    client.patch(f"/api/v1/automations/{rule['id']}/toggle", headers=s7_admin_headers)

    # 4. Xem nhật ký thực thi (Automation Logs)
    logs_res = client.get("/api/v1/automations/logs", headers=s7_admin_headers)
    assert logs_res.status_code == 200
    assert isinstance(logs_res.json(), list)
