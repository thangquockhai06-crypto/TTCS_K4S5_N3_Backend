"""
Bộ kiểm thử toàn diện cho Phân hệ Quản lý Cơ hội bán hàng (EP-05: Deal Management S5-01 -> S5-08):
- S5-01: Tạo và quản lý cơ hội bán hàng, xác thực khách hàng và xác suất
- S5-02: Bảng Kanban và cập nhật giai đoạn
- S5-03: Dòng sản phẩm & tính toán lại giá trị authoritative trên backend
- S5-04: Điều kiện thoát giai đoạn (Stage Exit Conditions) & quyền override
- S5-05: Đóng Deal (Close Won / Close Lost) kèm lý do và đối thủ
- S5-06: Báo cáo dự báo doanh thu (Sales Forecast - Weighted formula)
- S5-07: Cơ hội ứ đọng (Stalled deals)
- S5-08: Tái phân bổ hàng loạt (Deal Reassignment) kèm ghi nhận kiểm toán
"""
import pytest
from datetime import datetime, date, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.customer import Customer
from app.models.deal import Deal
from app.models.product import Product
from app.core.security import hash_password, create_access_token


@pytest.fixture
def auth_headers(db_session: Session) -> dict:
    admin = User(
        id="usr-ep05-admin",
        email="ep05_admin@nexuscrm.vn",
        password_hash=hash_password("AdminPass123!"),
        full_name="Quản Trị Viên EP05",
        role="Super Admin",
        status="active",
    )
    db_session.add(admin)
    db_session.commit()
    token = create_access_token(user_id=admin.id, email=admin.email, role=admin.role)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_customer(db_session: Session) -> Customer:
    cust = Customer(
        id="cust-ep05-test",
        full_name="Công ty TNHH Thử Nghiệm Deal",
        email="deal_test@company.vn",
        phone="0911223344",
        company="Deal Test Corp",
        status="active",
        health_score=90,
    )
    db_session.add(cust)
    db_session.commit()
    return cust


@pytest.fixture
def test_product(db_session: Session) -> Product:
    prod = Product(
        id="prod-ep05-test",
        code="PROD-CRM-ENT",
        name="NexusCRM Enterprise License",
        category="Phần mềm",
        selling_price=50000000.0,
        cost_price=20000000.0,
        is_active=True,
    )
    db_session.add(prod)
    db_session.commit()
    return prod


def test_s5_01_create_deal_with_validation(client: TestClient, auth_headers: dict, test_customer: Customer):
    """S5-01: Tạo Deal mới có liên kết khách hàng hợp lệ và tự gán win probability."""
    payload = {
        "title": "Hợp đồng Triển khai CRM Toàn quốc",
        "value": 150000000.0,
        "stage": "lead",
        "customerId": test_customer.id,
        "expectedCloseDate": "2026-12-31",
    }
    res = client.post("/api/v1/deals", json=payload, headers=auth_headers)
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == "Hợp đồng Triển khai CRM Toàn quốc"
    assert data["probability"] == 20  # Stage 'lead' default 20%
    assert data["customerId"] == test_customer.id


def test_s5_03_products_and_deal_items_authoritative(client: TestClient, auth_headers: dict, test_customer: Customer, test_product: Product):
    """S5-03: Thêm sản phẩm vào Deal và tính lại authoritative total trên backend."""
    # 1. Tạo deal khởi điểm 0đ
    create_res = client.post("/api/v1/deals", json={
        "title": "Deal Kèm Sản Phẩm",
        "value": 0.0,
        "customerId": test_customer.id,
    }, headers=auth_headers)
    assert create_res.status_code == 201
    deal_id = create_res.json()["id"]

    # 2. Thêm dòng sản phẩm: 2 licenses giá 50M chiết khấu 10% => subtotal = 90M
    item_payload = {
        "productId": test_product.id,
        "productName": test_product.name,
        "quantity": 2,
        "unitPrice": 50000000.0,
        "discountPercent": 10.0,
        "billingCycle": "annual",
    }
    item_res = client.post(f"/api/v1/deals/{deal_id}/items", json=item_payload, headers=auth_headers)
    assert item_res.status_code == 201
    item_data = item_res.json()
    assert item_data["subtotal"] == 90000000.0

    # 3. Kiểm tra Deal tổng đã được backend tự động cập nhật lên 90M
    deal_check = client.get(f"/api/v1/deals/{deal_id}", headers=auth_headers).json()
    assert deal_check["value"] == 90000000.0
    assert len(deal_check["items"]) == 1


def test_s5_04_stage_exit_conditions_and_override(client: TestClient, auth_headers: dict, test_customer: Customer):
    """S5-04: Kiểm tra điều kiện chuyển giai đoạn & quyền ghi đè (override)."""
    # Tạo deal giá trị 0đ và không có ngày đóng
    deal = client.post("/api/v1/deals", json={
        "title": "Deal Kiểm Tra Exit Conditions",
        "value": 0.0,
        "stage": "contact",
        "customerId": test_customer.id,
    }, headers=auth_headers).json()

    # Thử chuyển sang "proposal" khi giá trị = 0đ và không có expectedCloseDate => Bị chặn 400
    move_fail = client.patch(f"/api/v1/deals/{deal['id']}/stage", json={"stage": "proposal", "override": False}, headers=auth_headers)
    assert move_fail.status_code == 400
    assert "Chưa đáp ứng điều kiện" in move_fail.json()["detail"]

    # Quản trị viên sử dụng quyền ghi đè (override = True) => Cho phép chuyển
    move_override = client.patch(f"/api/v1/deals/{deal['id']}/stage", json={"stage": "proposal", "override": True}, headers=auth_headers)
    assert move_override.status_code == 200
    assert move_override.json()["stage"] == "proposal"


def test_s5_05_close_won_and_lost(client: TestClient, auth_headers: dict, test_customer: Customer):
    """S5-05: Đóng Deal dạng Won hoặc Lost."""
    deal1 = client.post("/api/v1/deals", json={"title": "Deal Sắp Thắng", "value": 100000000, "customerId": test_customer.id}, headers=auth_headers).json()
    deal2 = client.post("/api/v1/deals", json={"title": "Deal Sắp Thua", "value": 50000000, "customerId": test_customer.id}, headers=auth_headers).json()

    # Đóng Won
    won_res = client.post(f"/api/v1/deals/{deal1['id']}/close", json={
        "stage": "won",
        "actualValue": 100000000,
        "signingDate": "2026-10-15",
    }, headers=auth_headers)
    assert won_res.status_code == 200
    assert won_res.json()["stage"] == "won"
    assert won_res.json()["probability"] == 100

    # Đóng Lost (yêu cầu lý do thất bại)
    lost_fail = client.post(f"/api/v1/deals/{deal2['id']}/close", json={"stage": "lost"}, headers=auth_headers)
    assert lost_fail.status_code == 400

    lost_ok = client.post(f"/api/v1/deals/{deal2['id']}/close", json={
        "stage": "lost",
        "lossReason": "Giá cao hơn đối thủ",
        "lossCompetitor": "Competitor X",
    }, headers=auth_headers)
    assert lost_ok.status_code == 200
    assert lost_ok.json()["stage"] == "lost"
    assert lost_ok.json()["lossReason"] == "Giá cao hơn đối thủ"


def test_s5_06_sales_forecast_calculation(client: TestClient, auth_headers: dict, test_customer: Customer):
    """S5-06: Dự báo doanh thu theo công thức Weighted forecast = Sum(value * prob)."""
    forecast_res = client.get("/api/v1/deals/forecast", headers=auth_headers)
    assert forecast_res.status_code == 200
    f_data = forecast_res.json()
    assert "totalPipelineValue" in f_data
    assert "totalWeightedForecast" in f_data
    assert "periods" in f_data
    assert "stageBreakdowns" in f_data


def test_s5_07_stalled_deals_detection(client: TestClient, auth_headers: dict):
    """S5-07: Quét và nhận diện các cơ hội ứ đọng."""
    res = client.get("/api/v1/deals/stalled?days=14", headers=auth_headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_s5_08_deal_reassignment(client: TestClient, auth_headers: dict, test_customer: Customer, db_session: Session):
    """S5-08: Tái phân bổ hàng loạt cơ hội bán hàng kèm ghi nhật ký kiểm toán."""
    # Tạo nhân viên mới
    new_rep = User(
        id="usr-rep-target",
        email="target_rep@nexuscrm.vn",
        password_hash=hash_password("Pass123!"),
        full_name="Lê Nhân Viên Mới",
        role="Account Executive",
        status="active",
    )
    db_session.add(new_rep)
    db_session.commit()

    deal = client.post("/api/v1/deals", json={"title": "Deal Cần Chuyển Giao", "value": 60000000, "customerId": test_customer.id}, headers=auth_headers).json()

    reassign_payload = {
        "dealIds": [deal["id"]],
        "newOwnerId": new_rep.id,
        "reason": "Điều chuyển địa bàn phụ trách kinh doanh Q4",
    }
    reassign_res = client.post("/api/v1/deals/reassign", json=reassign_payload, headers=auth_headers)
    assert reassign_res.status_code == 200
    assert reassign_res.json()["updatedCount"] == 1

    # Kiểm tra deal đã đổi chủ sở hữu
    check_deal = client.get(f"/api/v1/deals/{deal['id']}", headers=auth_headers).json()
    assert check_deal["ownerId"] == new_rep.id
    assert check_deal["reassignmentReason"] == "Điều chuyển địa bàn phụ trách kinh doanh Q4"
