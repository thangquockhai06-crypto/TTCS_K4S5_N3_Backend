"""
Bộ kiểm thử toàn diện cho Chức năng Ghi nhận và Truy xuất Lịch sử Thay đổi Cơ hội bán hàng:
(Deal Change History / Audit Log - SCRUM-91 / Sprint 5 / EP-05).

Các kịch bản kiểm thử:
1. Cập nhật Deal làm thay đổi 'stage' và 'amount' sinh đúng 2 bản ghi lịch sử trong DB.
2. Endpoint GET /api/v1/deals/{id}/history trả về đúng giá trị trước, giá trị sau và tên người sửa.
3. Chặn quyền xem lịch sử khi SALES_REP truy cập vào Deal không thuộc sở hữu (403 Forbidden).
4. Cho phép SALES_REP xem lịch sử Deal do chính mình phụ trách (200 OK).
5. Cho phép TEAM_LEAD xem lịch sử Deal của thành viên trong nhóm (200 OK) và chặn nhóm khác (403 Forbidden).
6. Cho phép DIRECTOR xem lịch sử của toàn bộ cơ hội trong hệ thống (200 OK).
7. Lọc lịch sử theo từng trường dữ liệu (?field_name=stage, ?field_name=amount, ...).
8. Không sinh bản ghi lịch sử khi giá trị cập nhật không thay đổi (old_value == new_value).
9. Bắt vết thay đổi trường expected_close_date và assigned_to.
10. Tính bất biến: Không hỗ trợ PUT/DELETE trên endpoint lịch sử (405 Method Not Allowed).
11. Trả về 404 Not Found khi deal_id không tồn tại.
"""
import uuid
from datetime import date, datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.customer import Customer
from app.models.deal import Deal
from app.models.deal_history import DealHistory
from app.core.security import hash_password, create_access_token


@pytest.fixture
def test_customer(db_session: Session) -> Customer:
    customer = Customer(
        id="cust-history-test-01",
        full_name="Tập Đoàn Công Nghệ Số FPTX",
        email="fptx@company.vn",
        phone="0988776655",
        company="FPTX Corporation",
        status="active",
        health_score=95,
    )
    db_session.add(customer)
    db_session.commit()
    return customer


@pytest.fixture
def users_fixture(db_session: Session) -> dict:
    pwd = hash_password("Password123!")

    # 1. Super Admin
    admin = User(
        id="usr-test-admin",
        email="test_admin@nexuscrm.vn",
        password_hash=pwd,
        full_name="Quản Trị Viên Hệ Thống",
        role="Super Admin",
        status="active",
    )

    # 2. Giám đốc kinh doanh (DIRECTOR - ALL Scope)
    director = User(
        id="usr-test-director",
        email="test_director@nexuscrm.vn",
        password_hash=pwd,
        full_name="Nguyễn Văn Giám Đốc",
        role="DIRECTOR",
        status="active",
    )

    # 3. Trưởng nhóm Kinh doanh Bắc (TEAM_LEAD - TEAM Scope)
    leader_north = User(
        id="usr-test-lead-north",
        email="lead_north@nexuscrm.vn",
        password_hash=pwd,
        full_name="Trần Văn Trưởng Nhóm Bắc",
        role="TEAM_LEAD",
        team_id="team-north",
        status="active",
    )

    # 4. Trưởng nhóm Kinh doanh Nam (TEAM_LEAD - Khác nhóm)
    leader_south = User(
        id="usr-test-lead-south",
        email="lead_south@nexuscrm.vn",
        password_hash=pwd,
        full_name="Lê Văn Trưởng Nhóm Nam",
        role="TEAM_LEAD",
        team_id="team-south",
        status="active",
    )

    # 5. Nhân viên kinh doanh 1 (SALES_REP - Thuộc team-north)
    sales1 = User(
        id="usr-test-sales-1",
        email="sales1@nexuscrm.vn",
        password_hash=pwd,
        full_name="Phạm Văn Sales Một",
        role="SALES_REP",
        team_id="team-north",
        status="active",
    )

    # 6. Nhân viên kinh doanh 2 (SALES_REP - Thuộc team-north)
    sales2 = User(
        id="usr-test-sales-2",
        email="sales2@nexuscrm.vn",
        password_hash=pwd,
        full_name="Đỗ Văn Sales Hai",
        role="SALES_REP",
        team_id="team-north",
        status="active",
    )

    db_session.add_all([admin, director, leader_north, leader_south, sales1, sales2])
    db_session.commit()

    def make_auth(user: User) -> dict:
        token = create_access_token(user_id=user.id, email=user.email, role=user.role)
        return {"Authorization": f"Bearer {token}"}

    return {
        "admin": admin,
        "admin_auth": make_auth(admin),
        "director": director,
        "director_auth": make_auth(director),
        "leader_north": leader_north,
        "leader_north_auth": make_auth(leader_north),
        "leader_south": leader_south,
        "leader_south_auth": make_auth(leader_south),
        "sales1": sales1,
        "sales1_auth": make_auth(sales1),
        "sales2": sales2,
        "sales2_auth": make_auth(sales2),
    }


# ==============================================================================
# 1. KIỂM THỬ GHI NHẬN LỊCH SỬ THAY ĐỔI TRONG DB KHI CẬP NHẬT DEAL
# ==============================================================================

def test_deal_update_stage_and_amount_creates_two_history_records(
    client: TestClient,
    db_session: Session,
    users_fixture: dict,
    test_customer: Customer,
):
    """
    AC1 & AC2: Cập nhật đồng thời stage và amount của Deal
    phải sinh đúng 2 bản ghi lịch sử tương ứng trong CSDL.
    """
    admin_auth = users_fixture["admin_auth"]
    admin = users_fixture["admin"]

    # 1. Tạo mới một cơ hội bán hàng
    create_res = client.post(
        "/api/v1/deals",
        json={
            "title": "Hợp Đồng Triển Khai ERP Doanh Nghiệp",
            "value": 50000000.0,
            "stage": "lead",
            "customerId": test_customer.id,
        },
        headers=admin_auth,
    )
    assert create_res.status_code == 201
    deal_id = create_res.json()["id"]

    # 2. Cập nhật deal làm thay đổi stage và amount (sử dụng PATCH hoặc PUT)
    update_payload = {
        "stage": "proposal",
        "amount": 35000000.0,
    }
    update_res = client.patch(
        f"/api/v1/deals/{deal_id}",
        json=update_payload,
        headers=admin_auth,
    )
    assert update_res.status_code == 200
    updated_data = update_res.json()
    assert updated_data["stage"] == "proposal"
    assert updated_data["value"] == 35000000.0

    # 3. Kiểm tra trực tiếp bảng deal_histories trong CSDL
    histories = (
        db_session.query(DealHistory)
        .filter(DealHistory.deal_id == deal_id)
        .order_by(DealHistory.field_name.asc())
        .all()
    )
    assert len(histories) == 2

    # Bản ghi thay đổi amount
    amount_history = next(h for h in histories if h.field_name == "amount")
    assert amount_history.old_value == "50000000"
    assert amount_history.new_value == "35000000"
    assert amount_history.changed_by == admin.id

    # Bản ghi thay đổi stage
    stage_history = next(h for h in histories if h.field_name == "stage")
    assert stage_history.old_value == "lead"
    assert stage_history.new_value == "proposal"
    assert stage_history.changed_by == admin.id


# ==============================================================================
# 2. KIỂM THỬ ENDPOINT GET /history TRẢ VỀ ĐÚNG GIÁ TRỊ VÀ TÊN NGƯỜI SỬA
# ==============================================================================

def test_get_deal_history_endpoint_returns_correct_data_and_operator_name(
    client: TestClient,
    users_fixture: dict,
    test_customer: Customer,
):
    """
    AC2 & AC4: Endpoint GET /api/v1/deals/{id}/history trả về đúng giá trị trước,
    giá trị sau, nhãn tiếng Việt thân thiện và họ tên người thực hiện thay đổi.
    """
    admin_auth = users_fixture["admin_auth"]
    admin = users_fixture["admin"]

    # 1. Tạo deal
    deal = client.post(
        "/api/v1/deals",
        json={
            "title": "Gói Chữ Ký Số Doanh Nghiệp",
            "value": 10000000.0,
            "stage": "lead",
            "customerId": test_customer.id,
        },
        headers=admin_auth,
    ).json()
    deal_id = deal["id"]

    # 2. Cập nhật deal
    client.put(
        f"/api/v1/deals/{deal_id}",
        json={"stage": "contact", "value": 15000000.0},
        headers=admin_auth,
    )

    # 3. Gọi endpoint GET /api/v1/deals/{id}/history
    history_res = client.get(
        f"/api/v1/deals/{deal_id}/history",
        headers=admin_auth,
    )
    assert history_res.status_code == 200
    data = history_res.json()

    assert data["deal_id"] == deal_id
    assert data["total_changes"] == 2
    assert len(data["items"]) == 2

    # Kiểm tra chi tiết từng bản ghi trả về
    items_by_field = {item["field_name"]: item for item in data["items"]}

    assert "stage" in items_by_field
    stage_item = items_by_field["stage"]
    assert stage_item["field_label"] == "Giai đoạn"
    assert stage_item["old_value"] == "lead"
    assert stage_item["new_value"] == "contact"
    assert stage_item["changed_by_id"] == admin.id
    assert stage_item["changed_by_name"] == admin.full_name

    assert "amount" in items_by_field
    amount_item = items_by_field["amount"]
    assert amount_item["field_label"] == "Giá trị"
    assert amount_item["old_value"] == "10000000"
    assert amount_item["new_value"] == "15000000"
    assert amount_item["changed_by_id"] == admin.id
    assert amount_item["changed_by_name"] == admin.full_name


# ==============================================================================
# 3. KIỂM THỬ LỌC THEO TỪNG TRƯỜNG DỮ LIỆU (?field_name=...)
# ==============================================================================

def test_get_deal_history_filtering_by_field_name(
    client: TestClient,
    users_fixture: dict,
    test_customer: Customer,
):
    """
    AC4.A: Hỗ trợ query param field_name để lọc riêng lẻ:
    'stage', 'amount', 'expected_close_date', 'assigned_to'.
    """
    admin_auth = users_fixture["admin_auth"]

    # Tạo deal và cập nhật đồng thời stage và value
    deal = client.post(
        "/api/v1/deals",
        json={"title": "Hợp Đồng Đào Tạo CRM", "value": 20000000.0, "stage": "lead", "customerId": test_customer.id},
        headers=admin_auth,
    ).json()
    deal_id = deal["id"]

    client.patch(
        f"/api/v1/deals/{deal_id}",
        json={"stage": "negotiation", "amount": 25000000.0},
        headers=admin_auth,
    )

    # 1. Lọc chỉ trường 'stage'
    stage_res = client.get(f"/api/v1/deals/{deal_id}/history?field_name=stage", headers=admin_auth)
    assert stage_res.status_code == 200
    stage_data = stage_res.json()
    assert stage_data["total_changes"] == 1
    assert len(stage_data["items"]) == 1
    assert stage_data["items"][0]["field_name"] == "stage"
    assert stage_data["items"][0]["field_label"] == "Giai đoạn"

    # 2. Lọc chỉ trường 'amount'
    amount_res = client.get(f"/api/v1/deals/{deal_id}/history?field_name=amount", headers=admin_auth)
    assert amount_res.status_code == 200
    amount_data = amount_res.json()
    assert amount_data["total_changes"] == 1
    assert len(amount_data["items"]) == 1
    assert amount_data["items"][0]["field_name"] == "amount"
    assert amount_data["items"][0]["field_label"] == "Giá trị"


# ==============================================================================
# 4. KIỂM THỬ PHÂN QUYỀN (RBAC & RECORD-LEVEL SECURITY)
# ==============================================================================

def test_sales_rep_access_control_forbidden_and_allowed(
    client: TestClient,
    users_fixture: dict,
    test_customer: Customer,
):
    """
    AC4:
    - SALES_REP chỉ được xem lịch sử của Deal do chính mình phụ trách.
    - Chặn 403 Forbidden khi SALES_REP truy cập vào Deal không thuộc sở hữu.
    """
    sales1_auth = users_fixture["sales1_auth"]
    sales2_auth = users_fixture["sales2_auth"]

    # 1. Sales 1 tạo một deal do mình sở hữu
    deal = client.post(
        "/api/v1/deals",
        json={
            "title": "Deal Riêng Của Sales 1",
            "value": 40000000.0,
            "stage": "lead",
            "customerId": test_customer.id,
        },
        headers=sales1_auth,
    ).json()
    deal_id = deal["id"]

    # Sales 1 cập nhật deal để tạo lịch sử
    client.patch(
        f"/api/v1/deals/{deal_id}",
        json={"stage": "contact", "value": 45000000.0},
        headers=sales1_auth,
    )

    # 2. Sales 1 truy cập xem lịch sử Deal của chính mình => Thành công 200 OK
    res_owner = client.get(f"/api/v1/deals/{deal_id}/history", headers=sales1_auth)
    assert res_owner.status_code == 200
    assert res_owner.json()["total_changes"] == 2

    # 3. Sales 2 (nhân viên khác) truy cập vào Deal của Sales 1 => Bị chặn 403 Forbidden
    res_other = client.get(f"/api/v1/deals/{deal_id}/history", headers=sales2_auth)
    assert res_other.status_code == 403
    assert "quyền" in res_other.json()["detail"].lower()


def test_team_lead_and_director_role_based_access_control(
    client: TestClient,
    users_fixture: dict,
    test_customer: Customer,
):
    """
    AC4:
    - TEAM_LEAD: Xem được lịch sử của cơ hội thuộc nhân viên trong nhóm mình quản lý.
    - TEAM_LEAD: Bị chặn 403 khi xem cơ hội của nhóm khác.
    - DIRECTOR: Xem được lịch sử của toàn bộ cơ hội trong hệ thống.
    """
    sales1_auth = users_fixture["sales1_auth"]
    leader_north_auth = users_fixture["leader_north_auth"]
    leader_south_auth = users_fixture["leader_south_auth"]
    director_auth = users_fixture["director_auth"]

    # Sales 1 (team-north) tạo deal
    deal = client.post(
        "/api/v1/deals",
        json={
            "title": "Deal Dự Án Team Bắc",
            "value": 80000000.0,
            "stage": "lead",
            "customerId": test_customer.id,
        },
        headers=sales1_auth,
    ).json()
    deal_id = deal["id"]

    # Cập nhật deal
    client.patch(f"/api/v1/deals/{deal_id}", json={"stage": "proposal"}, headers=sales1_auth)

    # 1. Trưởng nhóm Bắc (cùng team-north) xem lịch sử => 200 OK
    res_lead_north = client.get(f"/api/v1/deals/{deal_id}/history", headers=leader_north_auth)
    assert res_lead_north.status_code == 200
    assert res_lead_north.json()["total_changes"] >= 1

    # 2. Trưởng nhóm Nam (khác team) xem lịch sử => 403 Forbidden
    res_lead_south = client.get(f"/api/v1/deals/{deal_id}/history", headers=leader_south_auth)
    assert res_lead_south.status_code == 403
    assert "quyền" in res_lead_south.json()["detail"].lower()

    # 3. Giám đốc kinh doanh (DIRECTOR) xem lịch sử => 200 OK
    res_director = client.get(f"/api/v1/deals/{deal_id}/history", headers=director_auth)
    assert res_director.status_code == 200
    assert res_director.json()["total_changes"] >= 1


# ==============================================================================
# 5. KIỂM THỬ KHÔNG SINH LOG KHI GIÁ TRỊ KHÔNG THAY ĐỔI
# ==============================================================================

def test_no_history_logged_when_values_are_unchanged(
    client: TestClient,
    users_fixture: dict,
    test_customer: Customer,
):
    """
    AC1: Chỉ tạo bản ghi log khi giá trị thực tế có sự thay đổi (old_value != new_value).
    Gửi payload với giá trị giống y hệt sẽ không sinh thêm bản ghi lịch sử nào.
    """
    admin_auth = users_fixture["admin_auth"]

    deal = client.post(
        "/api/v1/deals",
        json={"title": "Deal Không Thay Đổi", "value": 30000000.0, "stage": "lead", "customerId": test_customer.id},
        headers=admin_auth,
    ).json()
    deal_id = deal["id"]

    # Gửi lại đúng giá trị stage="lead" và value=30000000.0
    client.put(
        f"/api/v1/deals/{deal_id}",
        json={"stage": "lead", "value": 30000000.0},
        headers=admin_auth,
    )

    # Lấy lịch sử => Số thay đổi phải là 0
    res = client.get(f"/api/v1/deals/{deal_id}/history", headers=admin_auth)
    assert res.status_code == 200
    assert res.json()["total_changes"] == 0
    assert len(res.json()["items"]) == 0


# ==============================================================================
# 6. KIỂM THỬ BẮT VẾT expected_close_date VÀ assigned_to
# ==============================================================================

def test_history_logging_for_close_date_and_reassignment(
    client: TestClient,
    users_fixture: dict,
    test_customer: Customer,
):
    """
    AC1: Tự động bắt vết thay đổi cả 4 trường trọng yếu:
    - expected_close_date ("Ngày chốt dự kiến")
    - assigned_to ("Người sở hữu")
    """
    admin_auth = users_fixture["admin_auth"]
    sales1 = users_fixture["sales1"]
    sales2 = users_fixture["sales2"]

    # Tạo deal khởi điểm được gán cho sales1
    deal = client.post(
        "/api/v1/deals",
        json={
            "title": "Deal Chuyển Giao Trách Nhiệm",
            "value": 120000000.0,
            "stage": "lead",
            "customerId": test_customer.id,
            "expectedCloseDate": "2026-11-30",
        },
        headers=users_fixture["sales1_auth"],
    ).json()
    deal_id = deal["id"]

    # Cập nhật expected_close_date sang 2026-12-31 và assigned_to sang sales2
    update_res = client.patch(
        f"/api/v1/deals/{deal_id}",
        json={
            "expected_close_date": "2026-12-31",
            "assigned_to": sales2.id,
        },
        headers=admin_auth,
    )
    assert update_res.status_code == 200

    # Kiểm tra lịch sử
    res = client.get(f"/api/v1/deals/{deal_id}/history", headers=admin_auth)
    assert res.status_code == 200
    items = res.json()["items"]
    field_names = [i["field_name"] for i in items]

    assert "expected_close_date" in field_names
    date_item = next(i for i in items if i["field_name"] == "expected_close_date")
    assert date_item["field_label"] == "Ngày chốt dự kiến"
    assert date_item["old_value"] == "2026-11-30"
    assert date_item["new_value"] == "2026-12-31"

    assert "assigned_to" in field_names
    assign_item = next(i for i in items if i["field_name"] == "assigned_to")
    assert assign_item["field_label"] == "Người sở hữu"
    assert assign_item["old_value"] == sales1.id
    assert assign_item["new_value"] == sales2.id


# ==============================================================================
# 7. KIỂM THỬ TÍNH BẤT BIẾN (IMMUTABILITY) VÀ TRƯỜNG HỢP 404 NOT FOUND
# ==============================================================================

def test_history_immutability_and_not_found_handling(
    client: TestClient,
    users_fixture: dict,
):
    """
    AC3: Tính bất biến (Audit Immutability) - Không hỗ trợ thao tác UPDATE hay DELETE.
    Endpoint trả về 405 Method Not Allowed khi cố tình chỉnh sửa hoặc xóa lịch sử.
    Trả về 404 Not Found khi deal_id không tồn tại.
    """
    admin_auth = users_fixture["admin_auth"]

    # 1. Thử gửi request DELETE lên endpoint lịch sử => 405 Method Not Allowed
    delete_res = client.delete("/api/v1/deals/any-deal-id/history", headers=admin_auth)
    assert delete_res.status_code == 405

    # 2. Thử gửi request PUT lên endpoint lịch sử => 405 Method Not Allowed
    put_res = client.put("/api/v1/deals/any-deal-id/history", json={}, headers=admin_auth)
    assert put_res.status_code == 405

    # 3. Truy vấn lịch sử của Deal không tồn tại => 404 Not Found
    not_found_res = client.get("/api/v1/deals/non-existent-deal-uuid-12345/history", headers=admin_auth)
    assert not_found_res.status_code == 404
    assert "Không tìm thấy" in not_found_res.json()["detail"]


# ==============================================================================
# 8. KIỂM THỬ BỘ LỌC THEO NGÀY (START_DATE, END_DATE) VÀ NGƯỜI THỰC HIỆN (CHANGED_BY)
# ==============================================================================

def test_get_deal_history_filtering_by_date_and_operator(
    client: TestClient,
    db_session: Session,
    users_fixture: dict,
    test_customer: Customer,
):
    """
    Kiểm thử chức năng lọc lịch sử theo khoảng thời gian và theo ID người thực hiện (SCRUM-91).
    Xác minh các trường thân thiện: old_display_value, new_display_value, change_description.
    """
    director_auth = users_fixture["director_auth"]
    sales1_auth = users_fixture["sales1_auth"]
    sales1 = users_fixture["sales1"]
    director = users_fixture["director"]

    # 1. Tạo deal
    deal = Deal(
        id=str(uuid.uuid4()),
        title="Dự án ERP Năng Lượng Xanh",
        value=500000000.0,
        stage="lead",
        probability=20,
        customer_id=test_customer.id,
        owner_id=sales1.id,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db_session.add(deal)
    db_session.commit()

    # 2. Tạo thay đổi bởi sales1
    client.put(
        f"/api/v1/deals/{deal.id}",
        json={"stage": "contact", "amount": 600000000.0},
        headers=sales1_auth,
    )

    # 3. Tạo thay đổi bởi director
    client.put(
        f"/api/v1/deals/{deal.id}",
        json={"stage": "proposal"},
        headers=director_auth,
    )

    # 4. Lọc theo changed_by = sales1.id
    res_sales = client.get(
        f"/api/v1/deals/{deal.id}/history",
        params={"changed_by": sales1.id},
        headers=director_auth,
    )
    assert res_sales.status_code == 200
    data_sales = res_sales.json()
    assert data_sales["total_changes"] == 2
    for item in data_sales["items"]:
        assert item["changed_by_id"] == sales1.id

    # 5. Lọc theo changed_by = director.id
    res_dir = client.get(
        f"/api/v1/deals/{deal.id}/history",
        params={"changed_by": director.id},
        headers=director_auth,
    )
    assert res_dir.status_code == 200
    data_dir = res_dir.json()
    assert data_dir["total_changes"] == 1
    assert data_dir["items"][0]["changed_by_id"] == director.id
    assert data_dir["items"][0]["field_name"] == "stage"
    assert "proposal" in data_dir["items"][0]["new_value"]
    assert data_dir["items"][0]["change_description"] is not None

    # 6. Lọc khoảng ngày hôm nay
    today_str = datetime.now().strftime("%Y-%m-%d")
    res_today = client.get(
        f"/api/v1/deals/{deal.id}/history",
        params={"start_date": today_str, "end_date": today_str},
        headers=director_auth,
    )
    assert res_today.status_code == 200
    assert res_today.json()["total_changes"] == 3

    # 7. Lọc ngày tương lai => 0 bản ghi
    res_future = client.get(
        f"/api/v1/deals/{deal.id}/history",
        params={"start_date": "2099-01-01"},
        headers=director_auth,
    )
    assert res_future.status_code == 200
    assert res_future.json()["total_changes"] == 0

    # 8. Sai định dạng start_date => 400 Bad Request
    res_invalid = client.get(
        f"/api/v1/deals/{deal.id}/history",
        params={"start_date": "invalid-date-format"},
        headers=director_auth,
    )
    assert res_invalid.status_code == 400
    assert "Định dạng start_date không hợp lệ" in res_invalid.json()["detail"]

