"""
BỘ KIỂM THỬ TỰ ĐỘNG TOÀN DIỆN CHO TICKET SCRUM-67 (Sprint 3 / Story S3-09)
Danh sách Khách hàng Cần chăm sóc định kỳ & Thao tác ghi nhanh liên hệ
"""
from datetime import datetime, timedelta
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.customer import Customer, Contact
from app.models.deal import Deal
from app.models.activity import Activity
from app.models.user import User
from app.core.security import create_access_token


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def care_test_data(db_session: Session, seed_data: dict) -> dict:
    """
    Tạo dữ liệu chuyên biệt để kiểm thử các tiêu chí chấp nhận của SCRUM-67:
    - cust_vip_1 (Alpha Corp): Thuộc emp_a, Hợp đồng Won 250,000,000, Tương tác cuối: 45 ngày trước (Inactive 45 ngày)
    - cust_vip_2 (Beta Tech): Thuộc emp_a, Hợp đồng Won 150,000,000, Tương tác cuối: 20 ngày trước (Inactive 20 ngày)
    - cust_vip_3 (Gamma Global): Thuộc emp_b, Hợp đồng Won 80,000,000, Tương tác cuối: 5 ngày trước (Inactive 5 ngày)
    - cust_vip_4 (Delta Team Beta): Thuộc emp_beta, Hợp đồng Won 300,000,000, Tương tác cuối: 40 ngày trước (Inactive 40 ngày)
    - cust_lead_5: Lead chưa ký hợp đồng (stage lead, 0 won deals), không có tương tác 60 ngày -> Không được đưa vào DS
    - cust_deleted_6: Khách hàng đã xóa mềm (is_deleted = True), hợp đồng Won 500,000,000 -> Không được đưa vào DS
    """
    now = datetime.utcnow()
    emp_a: User = seed_data["users"]["emp_a"]
    emp_b: User = seed_data["users"]["emp_b"]
    emp_beta: User = seed_data["users"]["emp_beta"]

    # 1. VIP 1 (45 ngày trước, Hợp đồng 250 triệu)
    c1 = Customer(
        id=f"care-cust-1-{uuid.uuid4().hex[:6]}",
        full_name="Đỗ Hoàng Nam",
        company="Alpha Corp Vietnam",
        email="nam.do@alphacorp.vn",
        phone="0912345001",
        status="active",
        health_score=95,
        assigned_user_id=emp_a.id,
        created_at=now - timedelta(days=100),
    )
    d1 = Deal(
        id=f"care-deal-1-{uuid.uuid4().hex[:6]}",
        title="Gói Enterprise ERP Alpha",
        value=250000000.0,
        stage="won",
        probability=100,
        customer_id=c1.id,
        owner_id=emp_a.id,
    )
    act1 = Activity(
        id=f"care-act-1-{uuid.uuid4().hex[:6]}",
        customer_id=c1.id,
        user_id=emp_a.id,
        type="call",
        title="Cuộc gọi định kỳ tháng 8",
        description="Đã trao đổi về tiến độ gia hạn",
        created_at=now - timedelta(days=45),
    )

    # 2. VIP 2 (20 ngày trước, Hợp đồng 150 triệu)
    c2 = Customer(
        id=f"care-cust-2-{uuid.uuid4().hex[:6]}",
        full_name="Nguyễn Thúy Quỳnh",
        company="Beta Tech Solutions",
        email="quynh.nguyen@betatech.vn",
        phone="0912345002",
        status="active",
        health_score=88,
        assigned_user_id=emp_a.id,
        created_at=now - timedelta(days=80),
    )
    d2 = Deal(
        id=f"care-deal-2-{uuid.uuid4().hex[:6]}",
        title="Bản quyền NexusCRM Cloud",
        value=150000000.0,
        stage="won",
        probability=100,
        customer_id=c2.id,
        owner_id=emp_a.id,
    )
    act2 = Activity(
        id=f"care-act-2-{uuid.uuid4().hex[:6]}",
        customer_id=c2.id,
        user_id=emp_a.id,
        type="meeting",
        title="Họp trực tiếp tối ưu hóa quy trình",
        description="Demo các tính năng mới",
        created_at=now - timedelta(days=20),
    )

    # 3. VIP 3 (5 ngày trước, Hợp đồng 80 triệu)
    c3 = Customer(
        id=f"care-cust-3-{uuid.uuid4().hex[:6]}",
        full_name="Phạm Hồng Sơn",
        company="Gamma Global Logistics",
        email="son.pham@gammaglobal.vn",
        phone="0912345003",
        status="active",
        health_score=90,
        assigned_user_id=emp_b.id,
        created_at=now - timedelta(days=60),
    )
    d3 = Deal(
        id=f"care-deal-3-{uuid.uuid4().hex[:6]}",
        title="Gói vận hành Logistics",
        value=80000000.0,
        stage="won",
        probability=100,
        customer_id=c3.id,
        owner_id=emp_b.id,
    )
    act3 = Activity(
        id=f"care-act-3-{uuid.uuid4().hex[:6]}",
        customer_id=c3.id,
        user_id=emp_b.id,
        type="email",
        title="Gửi báo cáo hiệu suất tuần",
        description="Đã gửi email tự động",
        created_at=now - timedelta(days=5),
    )

    # 4. VIP 4 (40 ngày trước, Hợp đồng 300 triệu, thuộc Team Beta)
    c4 = Customer(
        id=f"care-cust-4-{uuid.uuid4().hex[:6]}",
        full_name="Trần Văn Thịnh",
        company="Delta Holdings Team Beta",
        email="thinh.tran@deltaholdings.vn",
        phone="0912345004",
        status="active",
        health_score=92,
        assigned_user_id=emp_beta.id,
        created_at=now - timedelta(days=90),
    )
    d4 = Deal(
        id=f"care-deal-4-{uuid.uuid4().hex[:6]}",
        title="Hợp đồng tích hợp hệ thống Core",
        value=300000000.0,
        stage="won",
        probability=100,
        customer_id=c4.id,
        owner_id=emp_beta.id,
    )
    act4 = Activity(
        id=f"care-act-4-{uuid.uuid4().hex[:6]}",
        customer_id=c4.id,
        user_id=emp_beta.id,
        type="call",
        title="Cuộc gọi rà soát chất lượng",
        description="Khách phản ánh cần thêm tài liệu",
        created_at=now - timedelta(days=40),
    )

    # 5. Lead 5: Chưa từng ký hợp đồng (chỉ có deal proposal, status = lead)
    c5 = Customer(
        id=f"care-cust-5-{uuid.uuid4().hex[:6]}",
        full_name="Khách Tiềm Năng Chưa Ký",
        company="Unsigned Lead Corp",
        email="lead@unsigned.com",
        phone="0912345005",
        status="lead",
        health_score=60,
        assigned_user_id=emp_a.id,
        created_at=now - timedelta(days=60),
    )
    d5 = Deal(
        id=f"care-deal-5-{uuid.uuid4().hex[:6]}",
        title="Báo giá chào hàng",
        value=50000000.0,
        stage="proposal",
        probability=30,
        customer_id=c5.id,
        owner_id=emp_a.id,
    )

    # 6. Khách hàng đã xóa mềm (is_deleted = True)
    c6 = Customer(
        id=f"care-cust-6-{uuid.uuid4().hex[:6]}",
        full_name="Khách Hàng Đã Xóa",
        company="Deleted Corp",
        email="deleted@corp.vn",
        phone="0912345006",
        status="active",
        health_score=80,
        assigned_user_id=emp_a.id,
        is_deleted=True,
        created_at=now - timedelta(days=70),
    )
    d6 = Deal(
        id=f"care-deal-6-{uuid.uuid4().hex[:6]}",
        title="Hợp đồng cũ",
        value=500000000.0,
        stage="won",
        probability=100,
        customer_id=c6.id,
        owner_id=emp_a.id,
    )

    # Thêm người dùng role CS (Chăm sóc khách hàng)
    cs_user = User(
        id=f"usr-cs-{uuid.uuid4().hex[:6]}",
        email="cs.specialist@nexuscrm.vn",
        password_hash=seed_data["users"]["emp_a"].password_hash,
        full_name="Nguyễn Chăm Sóc Khách Hàng",
        role="CS",
        team_id=None,
        department="Chăm Sóc Khách Hàng",
    )

    db_session.add_all([c1, c2, c3, c4, c5, c6, d1, d2, d3, d4, d5, d6, act1, act2, act3, act4, cs_user])
    db_session.commit()

    cs_token = create_access_token(cs_user.id, cs_user.email, cs_user.role)

    return {
        "c1": c1,
        "c2": c2,
        "c3": c3,
        "c4": c4,
        "c5": c5,
        "c6": c6,
        "cs_user": cs_user,
        "cs_token": cs_token,
        "tokens": seed_data["tokens"],
    }


def test_overdue_followups_with_different_days_inactive(client: TestClient, care_test_data: dict):
    """
    AC 2: Lọc theo số ngày chưa tương tác (N ngày cấu hình được):
    - Khi N = 30: Trả về các khách chưa tương tác >= 30 ngày (c1: 45 ngày, c4: 40 ngày).
    - Khi N = 15: Trả về thêm khách chưa tương tác >= 15 ngày (c1: 45 ngày, c4: 40 ngày, c2: 20 ngày).
    - Khi N = 60: Không có khách nào bị bỏ quên >= 60 ngày -> trả về 0 kết quả.
    """
    director_token = care_test_data["tokens"]["sales_director"]

    # 1. Kiểm tra với N = 30 ngày
    res_30 = client.get(
        "/api/v1/customer-care/overdue-followups?days_inactive=30",
        headers=auth_header(director_token),
    )
    assert res_30.status_code == 200
    data_30 = res_30.json()
    assert data_30["days_inactive_threshold"] == 30
    returned_ids_30 = [item["customer_id"] for item in data_30["items"]]

    assert care_test_data["c1"].id in returned_ids_30
    assert care_test_data["c4"].id in returned_ids_30
    assert care_test_data["c2"].id not in returned_ids_30  # 20 ngày < 30
    assert care_test_data["c3"].id not in returned_ids_30  # 5 ngày < 30
    assert care_test_data["c5"].id not in returned_ids_30  # Lead chưa ký hợp đồng
    assert care_test_data["c6"].id not in returned_ids_30  # Đã xóa mềm

    # 2. Kiểm tra với N = 15 ngày (Mở rộng phạm vi cảnh báo)
    res_15 = client.get(
        "/api/v1/customer-care/overdue-followups?days_inactive=15",
        headers=auth_header(director_token),
    )
    assert res_15.status_code == 200
    data_15 = res_15.json()
    returned_ids_15 = [item["customer_id"] for item in data_15["items"]]

    assert care_test_data["c1"].id in returned_ids_15  # 45 ngày
    assert care_test_data["c4"].id in returned_ids_15  # 40 ngày
    assert care_test_data["c2"].id in returned_ids_15  # 20 ngày >= 15 ngày

    # 3. Kiểm tra với N = 60 ngày
    res_60 = client.get(
        "/api/v1/customer-care/overdue-followups?days_inactive=60",
        headers=auth_header(director_token),
    )
    assert res_60.status_code == 200
    data_60 = res_60.json()
    # Không có khách nào trong nhóm test quá 60 ngày
    matched_test_ids = [item["customer_id"] for item in data_60["items"] if item["customer_id"] in [care_test_data["c1"].id, care_test_data["c2"].id, care_test_data["c3"].id, care_test_data["c4"].id]]
    assert len(matched_test_ids) == 0


def test_sorted_by_total_contract_value_desc(client: TestClient, care_test_data: dict):
    """
    AC 3: Sắp xếp theo giá trị hợp đồng giảm dần:
    - Khi N = 15, danh sách gồm c4 (300M), c1 (250M), c2 (150M).
    - Thứ tự trả về bắt buộc: c4 -> c1 -> c2.
    """
    director_token = care_test_data["tokens"]["sales_director"]

    response = client.get(
        "/api/v1/customer-care/overdue-followups?days_inactive=15",
        headers=auth_header(director_token),
    )
    assert response.status_code == 200
    items = response.json()["items"]

    # Lọc chỉ xét các khách hàng trong bộ test
    test_items = [it for it in items if it["customer_id"] in [care_test_data["c4"].id, care_test_data["c1"].id, care_test_data["c2"].id]]
    assert len(test_items) == 3

    assert test_items[0]["customer_id"] == care_test_data["c4"].id
    assert test_items[0]["total_contract_value"] == 300000000.0

    assert test_items[1]["customer_id"] == care_test_data["c1"].id
    assert test_items[1]["total_contract_value"] == 250000000.0

    assert test_items[2]["customer_id"] == care_test_data["c2"].id
    assert test_items[2]["total_contract_value"] == 150000000.0


def test_quick_contact_action_creates_activity_and_resets_days(client: TestClient, care_test_data: dict, db_session: Session):
    """
    AC 4: Thao tác đánh dấu liên hệ nhanh ngay trên danh sách:
    - POST /api/v1/customer-care/{c1_id}/quick-contact
    - Tạo thành công Activity mới trong DB.
    - Gọi lại GET overdue-followups: c1 không còn nằm trong danh sách cần chăm sóc định kỳ.
    """
    emp_a_token = care_test_data["tokens"]["emp_a"]
    c1_id = care_test_data["c1"].id

    # 1. Ban đầu c1 nằm trong danh sách quá hạn 30 ngày
    initial_res = client.get(
        "/api/v1/customer-care/overdue-followups?days_inactive=30",
        headers=auth_header(emp_a_token),
    )
    assert c1_id in [it["customer_id"] for it in initial_res.json()["items"]]

    # 2. Thực hiện click nhanh "Đã liên hệ"
    contact_payload = {
        "activity_type": "CALL",
        "notes": "Đã gọi điện hỏi thăm tình hình sử dụng hệ thống và tiến độ gia hạn Quý 4.",
    }
    contact_res = client.post(
        f"/api/v1/customer-care/{c1_id}/quick-contact",
        json=contact_payload,
        headers=auth_header(emp_a_token),
    )
    assert contact_res.status_code == 201
    contact_data = contact_res.json()
    assert "Đã ghi nhận tương tác thành công" in contact_data["message"]
    assert "last_contacted_at" in contact_data

    # 3. Kiểm tra bản ghi Activity mới trong CSDL
    latest_activity = (
        db_session.query(Activity)
        .filter(Activity.customer_id == c1_id)
        .order_by(Activity.created_at.desc())
        .first()
    )
    assert latest_activity is not None
    assert latest_activity.type == "call"
    assert "Đã gọi điện hỏi thăm" in latest_activity.description

    # 4. Gọi lại danh sách quá hạn 30 ngày: c1 PHẢI BIẾN MẤT ngay lập tức
    after_res = client.get(
        "/api/v1/customer-care/overdue-followups?days_inactive=30",
        headers=auth_header(emp_a_token),
    )
    assert c1_id not in [it["customer_id"] for it in after_res.json()["items"]]


def test_rbac_access_control_matrix(client: TestClient, care_test_data: dict):
    """
    AC 5: Phân quyền truy cập theo vai trò:
    - CS, DIRECTOR: Xem được toàn bộ khách hàng trên toàn hệ thống (c1 của emp_a và c4 của emp_beta).
    - TEAM_LEAD: Xem các khách hàng thuộc Alpha Team (c1, c2), KHÔNG thấy c4 (Beta Team).
    - SALES_REP (emp_a): Chỉ xem khách hàng do mình phụ trách (c1, c2), KHÔNG thấy c3 (emp_b) và c4 (emp_beta).
    """
    cs_token = care_test_data["cs_token"]
    leader_token = care_test_data["tokens"]["team_leader"]
    emp_a_token = care_test_data["tokens"]["emp_a"]

    # 1. CS: Xem toàn hệ thống
    res_cs = client.get(
        "/api/v1/customer-care/overdue-followups?days_inactive=15",
        headers=auth_header(cs_token),
    )
    assert res_cs.status_code == 200
    ids_cs = [it["customer_id"] for it in res_cs.json()["items"]]
    assert care_test_data["c1"].id in ids_cs
    assert care_test_data["c4"].id in ids_cs  # Thuộc team Beta

    # 2. Team Leader Alpha: Thấy c1, c2; KHÔNG thấy c4 (thuộc team Beta)
    res_lead = client.get(
        "/api/v1/customer-care/overdue-followups?days_inactive=15",
        headers=auth_header(leader_token),
    )
    assert res_lead.status_code == 200
    ids_lead = [it["customer_id"] for it in res_lead.json()["items"]]
    assert care_test_data["c1"].id in ids_lead
    assert care_test_data["c2"].id in ids_lead
    assert care_test_data["c4"].id not in ids_lead

    # 3. Sales Rep (emp_a): Chỉ thấy khách của mình (c1, c2)
    res_emp = client.get(
        "/api/v1/customer-care/overdue-followups?days_inactive=15",
        headers=auth_header(emp_a_token),
    )
    assert res_emp.status_code == 200
    ids_emp = [it["customer_id"] for it in res_emp.json()["items"]]
    assert care_test_data["c1"].id in ids_emp
    assert care_test_data["c2"].id in ids_emp
    assert care_test_data["c4"].id not in ids_emp


def test_quick_contact_permissions_and_errors(client: TestClient, care_test_data: dict):
    """
    Kiểm tra xử lý lỗi cho API Quick Contact:
    - HTTP 403 Forbidden: Sales Rep (emp_a) cố tình liên hệ khách của emp_beta.
    - HTTP 404 Not Found: Khách hàng không tồn tại trong hệ thống.
    """
    emp_a_token = care_test_data["tokens"]["emp_a"]
    c4_id = care_test_data["c4"].id  # Thuộc emp_beta

    # 1. emp_a cố tình gọi quick-contact cho c4
    unauthorized_res = client.post(
        f"/api/v1/customer-care/{c4_id}/quick-contact",
        json={"activity_type": "CALL", "notes": "Cố tình ghi nhận"},
        headers=auth_header(emp_a_token),
    )
    assert unauthorized_res.status_code == 403

    # 2. Gửi customer_id không tồn tại
    non_existent_id = "non-existent-customer-99999"
    not_found_res = client.post(
        f"/api/v1/customer-care/{non_existent_id}/quick-contact",
        json={"activity_type": "CALL", "notes": "Test 404"},
        headers=auth_header(emp_a_token),
    )
    assert not_found_res.status_code == 404


def test_search_customer_care(client: TestClient, care_test_data: dict):
    """
    Kiểm tra tìm kiếm từ khóa trong danh sách cần chăm sóc định kỳ:
    - Tìm theo tên công ty 'Alpha Corp' -> chỉ trả về c1.
    - Tìm theo số điện thoại '0912345001' -> chỉ trả về c1.
    """
    director_token = care_test_data["tokens"]["sales_director"]

    # Tìm theo tên công ty
    res_company = client.get(
        "/api/v1/customer-care/overdue-followups?days_inactive=15&search=Alpha Corp",
        headers=auth_header(director_token),
    )
    assert res_company.status_code == 200
    items = res_company.json()["items"]
    assert len(items) == 1
    assert items[0]["customer_id"] == care_test_data["c1"].id

    # Tìm theo SĐT
    res_phone = client.get(
        "/api/v1/customer-care/overdue-followups?days_inactive=15&search=0912345001",
        headers=auth_header(director_token),
    )
    assert res_phone.status_code == 200
    items_phone = res_phone.json()["items"]
    assert len(items_phone) == 1
    assert items_phone[0]["customer_id"] == care_test_data["c1"].id
