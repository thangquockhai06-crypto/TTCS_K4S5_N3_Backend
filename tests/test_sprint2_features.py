import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.product import Product
from app.models.category import Category
from app.models.customer import Customer
from app.models.quotation import Quotation
from app.core.security import hash_password, create_access_token


@pytest.fixture
def admin_user(db_session: Session) -> User:
    user = User(
        id="usr-test-admin-s2",
        email="admin_s2@nexuscrm.vn",
        password_hash=hash_password("AdminPass123!"),
        full_name="Quản Trị Viên S2",
        role="admin",
        status="active",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def staff_user(db_session: Session) -> User:
    user = User(
        id="usr-test-staff-s2",
        email="staff_s2@nexuscrm.vn",
        password_hash=hash_password("StaffPass123!"),
        full_name="Nhân Viên Kinh Doanh S2",
        role="sales",
        status="active",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_headers(admin_user: User) -> dict:
    token = create_access_token(admin_user.id, admin_user.email, admin_user.role)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def staff_headers(staff_user: User) -> dict:
    token = create_access_token(staff_user.id, staff_user.email, staff_user.role)
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# S2-01: Excel User Import Tests
# ==============================================================================
def test_excel_user_import_valid_and_invalid(client: TestClient, admin_headers: dict, db_session: Session):
    payload = {
        "rows": [
            {
                "name": "Nguyễn Văn Hợp Lệ",
                "email": "hople@nexuscrm.vn",
                "role": "sales",
                "group": "Miền Bắc",
                "phone": "0912345678",
            },
            {
                "name": "Trần Lỗi Email",
                "email": "invalid-email-format",
                "role": "sales",
                "group": "Miền Bắc",
                "phone": "0912345678",
            },
            {
                "name": "Lê Lỗi Phone",
                "email": "leloi@nexuscrm.vn",
                "role": "sales",
                "group": "Miền Bắc",
                "phone": "012345",  # Phone không chuẩn VN
            },
        ]
    }
    response = client.post("/api/v1/users/import-excel", json=payload, headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert data["success_count"] == 1
    assert data["failed_count"] == 2
    assert len(data["failed_rows"]) == 2

    # Check that invalid user was NOT inserted
    invalid_in_db = db_session.query(User).filter(User.email == "invalid-email-format").first()
    assert invalid_in_db is None

    # Check that valid user was inserted
    valid_in_db = db_session.query(User).filter(User.email == "hople@nexuscrm.vn").first()
    assert valid_in_db is not None
    assert valid_in_db.full_name == "Nguyễn Văn Hợp Lệ"


# ==============================================================================
# S2-02: Profile Update Tests (Vietnamese Phone & Read-only Role/Email)
# ==============================================================================
def test_user_profile_update_success(client: TestClient, staff_headers: dict, staff_user: User, db_session: Session):
    payload = {
        "full_name": "Nhân Viên Đã Đổi Tên",
        "phone": "0987654321",
        "title": "Chuyên viên Khách hàng Doanh nghiệp",
        "department": "Khối Doanh Nghiệp Lớn",
    }
    response = client.put("/api/v1/users/me/profile", json=payload, headers=staff_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["fullName"] == "Nhân Viên Đã Đổi Tên"
    # Role and email should remain intact
    assert data["email"] == staff_user.email
    assert data["role"] == staff_user.role


def test_user_profile_update_invalid_phone_rejected(client: TestClient, staff_headers: dict):
    payload = {
        "phone": "1234567",  # Invalid phone
    }
    response = client.put("/api/v1/users/me/profile", json=payload, headers=staff_headers)
    assert response.status_code == 400
    assert "Số điện thoại không đúng" in response.json()["detail"]


# ==============================================================================
# S2-04: Audit Log Tests
# ==============================================================================
def test_audit_logs_retrieval(client: TestClient, admin_headers: dict):
    response = client.get("/api/v1/audit-logs", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert "data" in data or "items" in data
    assert "total" in data
    assert "page" in data


# ==============================================================================
# S2-05: Products & Price Lists Tests (Cost Price & Quoted Delete Protection)
# ==============================================================================
def test_product_cost_price_director_visibility(client: TestClient, admin_headers: dict, staff_headers: dict, db_session: Session):
    prod = Product(
        code="TEST-SKU-001",
        name="Nexus CRM Enterprise License",
        category="Phần mềm CRM",
        selling_price=10000000.0,
        cost_price=5000000.0,
        unit="Gói/Năm",
    )
    db_session.add(prod)
    db_session.commit()

    # 1. Admin / Director sees cost_price
    res_admin = client.get("/api/v1/products", headers=admin_headers)
    assert res_admin.status_code == 200
    admin_items = [p for p in res_admin.json() if p["code"] == "TEST-SKU-001"]
    assert len(admin_items) == 1
    assert admin_items[0]["cost_price"] == 5000000.0

    # 2. Staff user does NOT see cost_price (returns None)
    res_staff = client.get("/api/v1/products", headers=staff_headers)
    assert res_staff.status_code == 200
    staff_items = [p for p in res_staff.json() if p["code"] == "TEST-SKU-001"]
    assert len(staff_items) == 1
    assert staff_items[0]["cost_price"] is None


def test_product_delete_prevention_when_quoted(client: TestClient, admin_headers: dict, admin_user: User, db_session: Session):
    quoted_prod = Product(
        code="TEST-QUOTED-001",
        name="Gói Tích Hợp API Đã Có Báo Giá",
        category="Phần mềm CRM",
        selling_price=15000000.0,
        cost_price=7000000.0,
        unit="Gói",
    )
    db_session.add(quoted_prod)
    db_session.commit()

    # Also add a customer and quotation referencing this product
    customer = Customer(
        full_name="Nguyễn Văn Test",
        company="Công ty Báo Giá Test",
        email="customer_test@example.com",
        phone="0912345678",
        assigned_user_id=admin_user.id,
    )
    db_session.add(customer)
    db_session.commit()

    quote = Quotation(
        quote_number="BG-TEST-001",
        title=f"Báo giá cho {quoted_prod.name}",
        customer_id=customer.id,
        owner_id=admin_user.id,
        total_amount=15000000.0,
        status="sent",
    )
    db_session.add(quote)
    db_session.commit()

    # Attempt to delete quoted product should be blocked
    del_res = client.delete(f"/api/v1/products/{quoted_prod.id}", headers=admin_headers)
    assert del_res.status_code == 400
    assert "Không thể xóa sản phẩm" in del_res.json()["detail"]


# ==============================================================================
# S2-06: Organization Tree Tests
# ==============================================================================
def test_org_tree_endpoints(client: TestClient, admin_headers: dict):
    response = client.get("/api/v1/org-tree", headers=admin_headers)
    assert response.status_code == 200
    nodes = response.json()
    assert len(nodes) > 0
    assert "name" in nodes[0]
    assert "region" in nodes[0]


# ==============================================================================
# S2-07: Categories Tests (Usage Check & Ordering)
# ==============================================================================
def test_category_endpoints_and_delete_protection(client: TestClient, admin_headers: dict, db_session: Session):
    in_use_cat = Category(
        type="lead_source",
        code="IN_USE_SRC",
        name="Kênh Đang Được Dùng",
        order_index=99,
        usage_count=5,  # In use
    )
    db_session.add(in_use_cat)
    db_session.commit()

    # Deleting in-use category must fail
    del_res = client.delete(f"/api/v1/categories/{in_use_cat.id}", headers=admin_headers)
    assert del_res.status_code == 400
    assert "Không thể xóa danh mục" in del_res.json()["detail"]


# ==============================================================================
# S2-08: Custom Fields Tests
# ==============================================================================
def test_custom_fields_crud(client: TestClient, admin_headers: dict):
    # 1. Create a custom field
    payload = {
        "entity_type": "customer",
        "field_name": "tax_id_s2_test",
        "field_label": "Mã số thuế doanh nghiệp",
        "field_type": "text",
        "is_required": True,
    }
    create_res = client.post("/api/v1/custom-fields", json=payload, headers=admin_headers)
    assert create_res.status_code == 201
    field_id = create_res.json()["id"]

    # 2. Get custom fields
    get_res = client.get("/api/v1/custom-fields?entity_type=customer", headers=admin_headers)
    assert get_res.status_code == 200
    field_names = [f["field_name"] for f in get_res.json()]
    assert "tax_id_s2_test" in field_names


# ==============================================================================
# S2-09: Pipeline Stages Tests
# ==============================================================================
def test_pipeline_stages_endpoints(client: TestClient, admin_headers: dict):
    response = client.get("/api/v1/pipelines/stages", headers=admin_headers)
    assert response.status_code == 200
    stages = response.json()
    assert len(stages) >= 3
    assert all(0 <= s["probability"] <= 100 for s in stages)


# ==============================================================================
# S2-10: Win/Loss Reasons & Competitors Tests
# ==============================================================================
def test_win_loss_reasons_and_competitors(client: TestClient, admin_headers: dict):
    # 1. Reasons
    res_reasons = client.get("/api/v1/win-loss-config/reasons?resultType=WON", headers=admin_headers)
    assert res_reasons.status_code == 200
    reasons = res_reasons.json()
    assert all(r["result_type"] == "WON" for r in reasons)

    # 2. Competitors
    comp_payload = {
        "name": "Test Global CRM",
        "pricing_tier": "Cao cấp",
        "strengths": "Thương hiệu mạnh",
        "weaknesses": "Giá thành cao",
        "win_rate": 40,
    }
    create_comp = client.post("/api/v1/win-loss-config/competitors", json=comp_payload, headers=admin_headers)
    assert create_comp.status_code == 201
    assert create_comp.json()["name"] == "Test Global CRM"
