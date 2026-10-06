import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.activity import Activity, Note
from app.models.customer import Contact, Customer
from app.models.deal import Deal


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# 1. TEST PHÁT HIỆN TRÙNG LẶP ĐA TIÊU CHÍ (DUPLICATE SCANNING)
# ==============================================================================

def test_scan_duplicates_by_tax_code(client: TestClient, db_session: Session, seed_data: dict):
    """
    Phát hiện trùng theo mã số thuế:
    Chuẩn hóa bỏ dấu cách, gạch nối, hoa thường (' 0108-923-456 ' ~ '0108923456').
    """
    token = seed_data["tokens"]["team_leader"]

    # Tạo khách hàng mẫu có mã số thuế
    cust = Customer(
        id=str(uuid.uuid4()),
        full_name="Công ty TNHH Hóa Chất Sao Mai",
        email="saomai@chem.vn",
        phone="0243123456",
        company="Hóa Chất Sao Mai",
        tax_code="0108923456",
        assigned_user_id=seed_data["users"]["emp_a"].id,
    )
    db_session.add(cust)
    db_session.commit()

    # Quét trùng với mã số thuế có định dạng gạch nối và khoảng trắng
    response = client.post(
        "/api/v1/customers/duplicates/scan",
        json={"tax_code": " 0108-923-456 "},
        headers=auth_header(token),
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    matched = next((item for item in data if item["id"] == cust.id), None)
    assert matched is not None
    assert matched["similarity_score"] == 1.0
    assert any("Trùng mã số thuế" in reason for reason in matched["match_reasons"])


def test_scan_duplicates_by_website_domain(client: TestClient, db_session: Session, seed_data: dict):
    """
    Phát hiện trùng theo website:
    Chuẩn hóa bỏ scheme https://, tiền tố www. và trailing slash/path.
    """
    token = seed_data["tokens"]["emp_a"]

    cust = Customer(
        id=str(uuid.uuid4()),
        full_name="Tập đoàn Công nghệ Alpha",
        email="contact@alphatech.vn",
        phone="0988776655",
        company="Alpha Tech Group",
        website="https://www.alphatech.vn/",
        assigned_user_id=seed_data["users"]["emp_b"].id,
    )
    db_session.add(cust)
    db_session.commit()

    # Quét với website khác tiền tố và có path
    response = client.post(
        "/api/v1/customers/duplicates/scan",
        json={"website": "http://alphatech.vn/products/enterprise"},
        headers=auth_header(token),
    )
    assert response.status_code == 200
    data = response.json()
    matched = next((item for item in data if item["id"] == cust.id), None)
    assert matched is not None
    assert matched["similarity_score"] == 1.0
    assert any("Trùng tên miền website" in reason or "Trùng website" in reason for reason in matched["match_reasons"])


def test_scan_duplicates_by_company_name_fuzzy(client: TestClient, db_session: Session, seed_data: dict):
    """
    Phát hiện trùng theo tên công ty gần giống:
    Chuẩn hóa loại bỏ các tiền tố / hậu tố pháp lý ('Công ty Cổ phần' vs 'TNHH', 'JSC').
    Độ tương đồng >= 80%.
    """
    token = seed_data["tokens"]["sales_director"]

    cust = Customer(
        id=str(uuid.uuid4()),
        full_name="Nguyễn Văn Đại Diện",
        email="contact@viettelcloud.vn",
        phone="0912345678",
        company="Công ty Cổ phần Giải pháp Đám mây Viettel",
        assigned_user_id=seed_data["users"]["emp_a"].id,
    )
    db_session.add(cust)
    db_session.commit()

    # Quét với tên gần giống: Công ty TNHH Giải pháp Đám mây Viettel (VN)
    response = client.post(
        "/api/v1/customers/duplicates/scan",
        json={"name": "Công ty TNHH Giải pháp Đám mây Viettel"},
        headers=auth_header(token),
    )
    assert response.status_code == 200
    data = response.json()
    matched = next((item for item in data if item["id"] == cust.id), None)
    assert matched is not None
    assert matched["similarity_score"] >= 0.8
    assert any("Tên công ty tương đồng" in reason for reason in matched["match_reasons"])


def test_scan_duplicates_by_existing_customer_id(client: TestClient, db_session: Session, seed_data: dict):
    """
    Quét trùng lặp bằng cách truyền customer_id của bản ghi đã có.
    Không được trả về chính bản ghi đó trong kết quả quét.
    """
    token = seed_data["tokens"]["team_leader"]

    cust1 = Customer(
        id=str(uuid.uuid4()),
        full_name="Đại diện Khách 1",
        email="k1@vinatex.vn",
        phone="0909000111",
        company="Tập đoàn Dệt May Vinatex",
        tax_code="0100123987",
        assigned_user_id=seed_data["users"]["emp_a"].id,
    )
    cust2 = Customer(
        id=str(uuid.uuid4()),
        full_name="Đại diện Khách 2",
        email="k2@vinatex.vn",
        phone="0909000222",
        company="Công ty CP Dệt May Vinatex Việt Nam",
        tax_code="0100123987",
        assigned_user_id=seed_data["users"]["emp_b"].id,
    )
    db_session.add_all([cust1, cust2])
    db_session.commit()

    response = client.post(
        "/api/v1/customers/duplicates/scan",
        json={"customer_id": cust1.id},
        headers=auth_header(token),
    )
    assert response.status_code == 200
    data = response.json()
    result_ids = [item["id"] for item in data]
    assert cust1.id not in result_ids  # Tự loại trừ chính mình
    assert cust2.id in result_ids      # Phát hiện ra cust2


# ==============================================================================
# 2. TEST SO SÁNH HAI KHÁCH HÀNG CẠNH NHAU (SIDE-BY-SIDE COMPARE)
# ==============================================================================

def test_compare_customers_success(client: TestClient, db_session: Session, seed_data: dict):
    """
    So sánh chi tiết 2 khách hàng, trả về thông tin hồ sơ, contacts, deals, activities
    và các trường khác biệt.
    """
    token = seed_data["tokens"]["team_leader"]
    cust_a = seed_data["customers"]["cust_a"]
    cust_b = seed_data["customers"]["cust_b"]

    response = client.get(
        "/api/v1/customers/compare",
        params={"primary_id": cust_a.id, "duplicate_id": cust_b.id},
        headers=auth_header(token),
    )
    assert response.status_code == 200
    data = response.json()
    assert "primary_customer" in data
    assert "duplicate_customer" in data
    assert data["primary_customer"]["id"] == cust_a.id
    assert data["duplicate_customer"]["id"] == cust_b.id
    assert "field_differences" in data
    assert len(data["field_differences"]) > 0


def test_compare_customers_same_id_error(client: TestClient, seed_data: dict):
    """So sánh một khách hàng với chính nó phải trả về 400 Bad Request."""
    token = seed_data["tokens"]["team_leader"]
    cust_a = seed_data["customers"]["cust_a"]

    response = client.get(
        "/api/v1/customers/compare",
        params={"primary_id": cust_a.id, "duplicate_id": cust_a.id},
        headers=auth_header(token),
    )
    assert response.status_code == 400
    assert "Không thể so sánh" in response.json()["detail"]


def test_compare_customers_not_found(client: TestClient, seed_data: dict):
    """So sánh với ID không tồn tại phải trả về 404 Not Found."""
    token = seed_data["tokens"]["team_leader"]
    cust_a = seed_data["customers"]["cust_a"]

    response = client.get(
        "/api/v1/customers/compare",
        params={"primary_id": cust_a.id, "duplicate_id": "non-existent-id"},
        headers=auth_header(token),
    )
    assert response.status_code == 404


# ==============================================================================
# 3. TEST GỘP KHÁCH HÀNG & BẢO TOÀN DỮ LIỆU (MERGE OPERATION)
# ==============================================================================

def test_merge_customers_success_as_team_lead(client: TestClient, db_session: Session, seed_data: dict):
    """
    Trưởng nhóm (TEAM_LEAD) thực hiện gộp 2 khách hàng trong nhóm:
    - Chuyển giao toàn bộ contacts, deals, activities sang khách chính.
    - Đánh dấu khách phụ is_deleted = True, merged_into_id = target_id.
    - Ghi nhận Activity trên khách chính.
    - Khách phụ không còn xuất hiện trong danh sách thông thường.
    """
    token_lead = seed_data["tokens"]["team_leader"]

    # 1. Tạo 2 khách hàng thuộc Team Alpha
    target_cust = Customer(
        id=str(uuid.uuid4()),
        full_name="Nguyễn Văn Trưởng",
        email="truong@alpha.vn",
        phone="0911000111",
        company="Tập đoàn Alpha Holdings",
        assigned_user_id=seed_data["users"]["emp_a"].id,
    )
    source_cust = Customer(
        id=str(uuid.uuid4()),
        full_name="Nguyễn Văn Phụ",
        email="phu@alpha.vn",
        phone="0911000222",
        company="Công ty CP Alpha Holdings",
        assigned_user_id=seed_data["users"]["emp_b"].id,
        website="https://alphaholdings.vn",
        tax_code="0109998888",
    )
    db_session.add_all([target_cust, source_cust])
    db_session.commit()

    # 2. Gắn contact, deal, activity vào source_cust
    contact_src = Contact(
        id=str(uuid.uuid4()),
        customer_id=source_cust.id,
        full_name="Người liên hệ Phụ",
        phone="0988000111",
        email="contact_phu@alpha.vn",
    )
    deal_src = Deal(
        id=str(uuid.uuid4()),
        customer_id=source_cust.id,
        owner_id=seed_data["users"]["emp_b"].id,
        title="Cơ hội CRM Phụ",
        value=150000000.0,
        stage="proposal",
    )
    act_src = Activity(
        id=str(uuid.uuid4()),
        customer_id=source_cust.id,
        user_id=seed_data["users"]["emp_b"].id,
        type="call",
        title="Cuộc gọi tư vấn lần 1",
    )
    note_src = Note(
        id=str(uuid.uuid4()),
        customer_id=source_cust.id,
        author_id=seed_data["users"]["emp_b"].id,
        content="Khách hàng quan tâm gói Enterprise",
    )
    db_session.add_all([contact_src, deal_src, act_src, note_src])
    db_session.commit()

    # 3. Gọi API Gộp
    merge_payload = {
        "target_customer_id": target_cust.id,
        "source_customer_id": source_cust.id,
    }
    response = client.post(
        "/api/v1/customers/merge",
        json=merge_payload,
        headers=auth_header(token_lead),
    )
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    assert res_data["transferred_contacts_count"] == 1
    assert res_data["transferred_deals_count"] == 1
    assert res_data["transferred_activities_count"] == 2

    # 4. Kiểm tra CSDL sau gộp
    db_session.expire_all()
    # Khách phụ: is_deleted = True, merged_into_id = target_cust.id
    updated_source = db_session.query(Customer).filter(Customer.id == source_cust.id).first()
    assert updated_source.is_deleted is True
    assert updated_source.merged_into_id == target_cust.id

    # Contacts, Deals, Activities của source đã được chuyển sang target
    updated_contact = db_session.query(Contact).filter(Contact.id == contact_src.id).first()
    assert updated_contact.customer_id == target_cust.id

    updated_deal = db_session.query(Deal).filter(Deal.id == deal_src.id).first()
    assert updated_deal.customer_id == target_cust.id

    updated_act = db_session.query(Activity).filter(Activity.id == act_src.id).first()
    assert updated_act.customer_id == target_cust.id

    # Khách chính: Tự động bổ sung website, tax_code từ khách phụ
    updated_target = db_session.query(Customer).filter(Customer.id == target_cust.id).first()
    assert updated_target.website == "https://alphaholdings.vn"
    assert updated_target.tax_code == "0109998888"

    # Kiểm tra có Activity ghi nhận lịch sử gộp
    merge_activity = (
        db_session.query(Activity)
        .filter(Activity.customer_id == target_cust.id, Activity.title == "Gộp khách hàng trùng lặp")
        .first()
    )
    assert merge_activity is not None

    # Khách phụ không còn xuất hiện khi gọi GET /api/v1/customers
    list_res = client.get("/api/v1/customers", headers=auth_header(token_lead))
    assert list_res.status_code == 200
    returned_ids = [c["id"] for c in list_res.json()]
    assert source_cust.id not in returned_ids


# ==============================================================================
# 4. TEST PHÂN QUYỀN RBAC & DATA SCOPE (PERMISSIONS & SECURITY)
# ==============================================================================

def test_merge_customers_forbidden_for_sales_rep(client: TestClient, seed_data: dict):
    """
    Nhân viên kinh doanh (SALES_REP / Employee) gọi API gộp /merge:
    Bắt buộc bị chặn với HTTP 403 Forbidden.
    """
    token_emp = seed_data["tokens"]["emp_a"]
    cust_a = seed_data["customers"]["cust_a"]
    cust_b = seed_data["customers"]["cust_b"]

    response = client.post(
        "/api/v1/customers/merge",
        json={"target_customer_id": cust_a.id, "source_customer_id": cust_b.id},
        headers=auth_header(token_emp),
    )
    assert response.status_code == 403
    assert "quyền" in response.json()["detail"].lower()


def test_merge_customers_cross_team_forbidden_for_team_lead(client: TestClient, seed_data: dict):
    """
    Trưởng nhóm (Team Alpha) cố gộp khách hàng thuộc Team Beta:
    Bị chặn với HTTP 403 Forbidden ("không thuộc quyền quản lý của nhóm bạn").
    """
    token_lead = seed_data["tokens"]["team_leader"]
    cust_a = seed_data["customers"]["cust_a"]        # Team Alpha
    cust_beta = seed_data["customers"]["cust_beta"]  # Team Beta

    response = client.post(
        "/api/v1/customers/merge",
        json={"target_customer_id": cust_a.id, "source_customer_id": cust_beta.id},
        headers=auth_header(token_lead),
    )
    assert response.status_code == 403
    assert "không thuộc quyền quản lý" in response.json()["detail"]


def test_merge_customers_allowed_for_director_across_teams(client: TestClient, db_session: Session, seed_data: dict):
    """
    Giám đốc kinh doanh (DIRECTOR) có phạm vi ALL:
    Được phép gộp khách hàng giữa các nhóm khác nhau.
    """
    token_director = seed_data["tokens"]["sales_director"]
    cust_a = seed_data["customers"]["cust_a"]        # Team Alpha
    cust_beta = seed_data["customers"]["cust_beta"]  # Team Beta

    response = client.post(
        "/api/v1/customers/merge",
        json={"target_customer_id": cust_a.id, "source_customer_id": cust_beta.id},
        headers=auth_header(token_director),
    )
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_merge_customers_with_field_overrides(client: TestClient, db_session: Session, seed_data: dict):
    """
    Gộp khách hàng kèm tùy chọn override một số trường cụ thể (merged_data).
    """
    token_director = seed_data["tokens"]["sales_director"]

    cust1 = Customer(
        id=str(uuid.uuid4()),
        full_name="Bản Gốc",
        email="old@email.com",
        phone="0901111111",
        company="Cũ Corp",
    )
    cust2 = Customer(
        id=str(uuid.uuid4()),
        full_name="Bản Gộp",
        email="new@email.com",
        phone="0902222222",
        company="Mới Corp",
    )
    db_session.add_all([cust1, cust2])
    db_session.commit()

    override_payload = {
        "target_customer_id": cust1.id,
        "source_customer_id": cust2.id,
        "merged_data": {
            "email": "chosen_override@email.com",
            "phone": "0988999999",
            "company": "Tên Công Ty Được Chọn",
        },
    }
    response = client.post(
        "/api/v1/customers/merge",
        json=override_payload,
        headers=auth_header(token_director),
    )
    assert response.status_code == 200

    db_session.expire_all()
    updated_cust1 = db_session.query(Customer).filter(Customer.id == cust1.id).first()
    assert updated_cust1.email == "chosen_override@email.com"
    assert updated_cust1.phone == "0988999999"
    assert updated_cust1.company == "Tên Công Ty Được Chọn"
