"""
Bộ kiểm thử tự động toàn diện cho 3 tính năng:
1. User Account Management (CRUD)
2. Role & Team Assignment
3. Account Deactivation & Data Handover
Bảo đảm 100% yêu cầu kỹ thuật và an ninh dữ liệu.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.customer import Customer
from app.models.deal import Deal
from app.models.role import Role
from app.models.team import Team


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# 1. USER CRUD & PASSWORD
# ==============================================================================

def test_create_user(client: TestClient, seed_data: dict, db_session: Session):
    token = seed_data["tokens"]["sales_director"]
    payload = {
        "full_name": "Trịnh Văn Mới",
        "email": "new_user@nexuscrm.vn",
        "role": "Account Executive",
        "title": "Chuyên viên bán hàng",
        "department": "Kinh Doanh 1",
    }
    response = client.post("/api/v1/users", json=payload, headers=auth_header(token))
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "new_user@nexuscrm.vn"
    assert data["fullName"] == "Trịnh Văn Mới"
    assert data["status"] == "active"
    assert "password" not in data
    assert "password_hash" not in data


def test_create_user_duplicate_email(client: TestClient, seed_data: dict):
    token = seed_data["tokens"]["sales_director"]
    payload = {
        "full_name": "Người Dùng Trùng Email",
        "email": seed_data["users"]["emp_a"].email,  # Trùng email của emp_a
        "role": "Employee",
    }
    response = client.post("/api/v1/users", json=payload, headers=auth_header(token))
    assert response.status_code == 400
    assert "đã được sử dụng" in response.json()["detail"]


def test_update_user(client: TestClient, seed_data: dict):
    token = seed_data["tokens"]["sales_director"]
    user_b_id = seed_data["users"]["emp_b"].id
    payload = {
        "full_name": "Trần Thị Bích Cập Nhật",
        "title": "Trưởng nhóm tư vấn",
    }
    response = client.put(f"/api/v1/users/{user_b_id}", json=payload, headers=auth_header(token))
    assert response.status_code == 200
    data = response.json()
    assert data["fullName"] == "Trần Thị Bích Cập Nhật"
    assert data["title"] == "Trưởng nhóm tư vấn"


def test_get_user(client: TestClient, seed_data: dict):
    token = seed_data["tokens"]["emp_a"]
    user_a_id = seed_data["users"]["emp_a"].id
    response = client.get(f"/api/v1/users/{user_a_id}", headers=auth_header(token))
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user_a_id
    assert data["email"] == seed_data["users"]["emp_a"].email


def test_list_users(client: TestClient, seed_data: dict):
    token = seed_data["tokens"]["sales_director"]

    # 1. Danh sách đầy đủ
    res_all = client.get("/api/v1/users", headers=auth_header(token))
    assert res_all.status_code == 200
    users = res_all.json()
    assert len(users) >= 4

    # 2. Tìm kiếm theo email
    res_search = client.get("/api/v1/users?search=emp_a", headers=auth_header(token))
    assert res_search.status_code == 200
    search_results = res_search.json()
    assert len(search_results) == 1
    assert search_results[0]["email"] == seed_data["users"]["emp_a"].email

    # 3. Lọc theo vai trò (Role)
    res_role = client.get("/api/v1/users?role=Team Leader", headers=auth_header(token))
    assert res_role.status_code == 200
    for u in res_role.json():
        assert u["role"] == "Team Leader"


def test_generated_password_is_hashed(client: TestClient, seed_data: dict, db_session: Session):
    token = seed_data["tokens"]["sales_director"]
    payload = {
        "full_name": "Kiểm Tra Mật Khẩu Băm",
        "email": "hashed_test@nexuscrm.vn",
        "role": "Employee",
    }
    res = client.post("/api/v1/users", json=payload, headers=auth_header(token))
    assert res.status_code == 201

    db_user = db_session.query(User).filter(User.email == "hashed_test@nexuscrm.vn").first()
    assert db_user is not None
    assert db_user.password_hash.startswith("$2b$") or len(db_user.password_hash) >= 50
    assert db_user.password_hash != ""


def test_password_hash_is_not_returned(client: TestClient, seed_data: dict):
    token = seed_data["tokens"]["sales_director"]
    user_a_id = seed_data["users"]["emp_a"].id
    response = client.get(f"/api/v1/users/{user_a_id}", headers=auth_header(token))
    data = response.json()
    assert "password_hash" not in data
    assert "password" not in data


# ==============================================================================
# 2. ROLE & TEAM ASSIGNMENT
# ==============================================================================

def test_assign_role(client: TestClient, seed_data: dict, db_session: Session):
    token = seed_data["tokens"]["sales_director"]
    user_b_id = seed_data["users"]["emp_b"].id

    payload = {"roleName": "Account Executive"}
    res = client.post(f"/api/v1/users/{user_b_id}/roles", json=payload, headers=auth_header(token))
    assert res.status_code == 200
    assert res.json()["role"] == "Account Executive"


def test_admin_cannot_demote_self(client: TestClient, seed_data: dict):
    """
    Quản trị viên / Giám đốc kinh doanh không thể tự hạ quyền của chính mình.
    """
    token_director = seed_data["tokens"]["sales_director"]
    director_id = seed_data["users"]["sales_director"].id

    payload = {"role": "Employee"}
    res = client.put(f"/api/v1/users/{director_id}", json=payload, headers=auth_header(token_director))
    assert res.status_code == 400
    assert "Quản trị viên không thể tự hạ quyền của chính mình." in res.json()["detail"]


def test_assign_user_to_team(client: TestClient, seed_data: dict, db_session: Session):
    token = seed_data["tokens"]["sales_director"]
    user_a_id = seed_data["users"]["emp_a"].id

    payload = {"teamId": "team-gamma"}
    res = client.post(f"/api/v1/users/{user_a_id}/teams", json=payload, headers=auth_header(token))
    assert res.status_code == 200
    assert res.json()["teamId"] == "team-gamma"


def test_leader_requires_team(client: TestClient, seed_data: dict):
    """
    Một người dùng được gán vai trò Leader/Team Leader bắt buộc phải có nhóm kinh doanh.
    """
    token = seed_data["tokens"]["sales_director"]
    # usr-lead-no-team không có team
    no_team_id = seed_data["users"]["leader_no_team"].id

    # 1. Cố gán vai trò Team Leader khi không có team_id -> 400
    payload = {"role": "Team Leader", "team_id": ""}
    res = client.put(f"/api/v1/users/{no_team_id}", json=payload, headers=auth_header(token))
    assert res.status_code == 400
    assert "Trưởng nhóm phải được gán vào ít nhất một nhóm kinh doanh." in res.json()["detail"]

    # 2. Tạo mới tài khoản với vai trò Leader nhưng không truyền team_id -> 400
    create_payload = {
        "full_name": "Trưởng Nhóm Mới Thiếu Team",
        "email": "leader_no_team_create@test.com",
        "role": "Team Leader",
        "team_id": None,
    }
    res_create = client.post("/api/v1/users", json=create_payload, headers=auth_header(token))
    assert res_create.status_code == 400
    assert "Trưởng nhóm phải được gán vào ít nhất một nhóm kinh doanh." in res_create.json()["detail"]


# ==============================================================================
# 3. ACCOUNT DEACTIVATION & DATA HANDOVER
# ==============================================================================

def test_deactivate_user(client: TestClient, seed_data: dict, db_session: Session):
    token = seed_data["tokens"]["sales_director"]
    target_id = seed_data["users"]["emp_b"].id
    successor_id = seed_data["users"]["emp_a"].id

    payload = {
        "successorUserId": successor_id,
        "reason": "Chuyển công tác",
    }
    res = client.post(f"/api/v1/users/{target_id}/deactivate", json=payload, headers=auth_header(token))
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["userStatus"] == "inactive"


def test_deactivate_transfers_customer_ownership(client: TestClient, seed_data: dict, db_session: Session):
    """
    Khi vô hiệu hóa user, toàn bộ khách hàng của target_user phải được chuyển giao sang successor.
    """
    token = seed_data["tokens"]["sales_director"]
    target_id = seed_data["users"]["emp_b"].id
    successor_id = seed_data["users"]["emp_a"].id
    cust_b_id = seed_data["customers"]["cust_b"].id

    # Trước khi bàn giao: KH cust_b thuộc về emp_b
    cust_before = db_session.query(Customer).filter(Customer.id == cust_b_id).first()
    assert cust_before.assigned_user_id == target_id

    # Thực thi bàn giao
    payload = {"successorUserId": successor_id}
    res = client.post(f"/api/v1/users/{target_id}/deactivate", json=payload, headers=auth_header(token))
    assert res.status_code == 200

    # Sau khi bàn giao: KH cust_b phải thuộc về successor (emp_a)
    db_session.expire_all()
    cust_after = db_session.query(Customer).filter(Customer.id == cust_b_id).first()
    assert cust_after.assigned_user_id == successor_id


def test_deactivate_transfers_deal_ownership(client: TestClient, seed_data: dict, db_session: Session):
    """
    Toàn bộ cơ hội bán hàng (Deal) của target_user phải được chuyển giao sang successor.
    """
    token = seed_data["tokens"]["sales_director"]
    target_id = seed_data["users"]["emp_b"].id
    successor_id = seed_data["users"]["emp_a"].id
    deal_b_id = seed_data["deals"]["deal_b"].id

    payload = {"successorUserId": successor_id}
    res = client.post(f"/api/v1/users/{target_id}/deactivate", json=payload, headers=auth_header(token))
    assert res.status_code == 200

    db_session.expire_all()
    deal_after = db_session.query(Deal).filter(Deal.id == deal_b_id).first()
    assert deal_after.owner_id == successor_id


def test_deactivated_user_cannot_login(client: TestClient, seed_data: dict, db_session: Session):
    """
    Tài khoản bị vô hiệu hóa (inactive) không thể đăng nhập hoặc dùng token cũ.
    """
    token = seed_data["tokens"]["sales_director"]
    target_user = seed_data["users"]["emp_b"]
    successor_id = seed_data["users"]["emp_a"].id

    # Vô hiệu hóa emp_b
    client.post(
        f"/api/v1/users/{target_user.id}/deactivate",
        json={"successorUserId": successor_id},
        headers=auth_header(token),
    )

    # 1. Thử đăng nhập lại -> 401
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": target_user.email, "password": "Password123!"},
    )
    assert login_res.status_code == 401
    assert "đã bị vô hiệu hóa" in login_res.json()["detail"]

    # 2. Thử dùng Access Token cũ -> 401
    old_token = seed_data["tokens"]["emp_b"]
    api_res = client.get("/api/v1/customers", headers=auth_header(old_token))
    assert api_res.status_code == 401


def test_deactivate_is_atomic(client: TestClient, seed_data: dict, db_session: Session):
    """
    Tính nguyên tử: Nếu có lỗi xảy ra, toàn bộ thao tác bàn giao phải rollback.
    """
    token = seed_data["tokens"]["sales_director"]
    target_user = seed_data["users"]["emp_b"]

    # Gửi successor không tồn tại -> bắt buộc dừng và không đổi trạng thái
    res = client.post(
        f"/api/v1/users/{target_user.id}/deactivate",
        json={"successorUserId": "invalid-successor-uuid-1234"},
        headers=auth_header(token),
    )
    assert res.status_code == 400

    # User vẫn phải active
    db_session.refresh(target_user)
    assert target_user.status == "active"


def test_unauthorized_user_cannot_deactivate_user(client: TestClient, seed_data: dict):
    """Quản trị viên không được tự vô hiệu hóa tài khoản của chính mình."""
    token_director = seed_data["tokens"]["sales_director"]
    director_id = seed_data["users"]["sales_director"].id
    successor_id = seed_data["users"]["emp_a"].id

    res = client.post(
        f"/api/v1/users/{director_id}/deactivate",
        json={"successorUserId": successor_id},
        headers=auth_header(token_director),
    )
    assert res.status_code == 400
    assert "Quản trị viên không thể tự vô hiệu hóa tài khoản của chính mình." in res.json()["detail"]


def test_invalid_successor_is_rejected(client: TestClient, seed_data: dict):
    token = seed_data["tokens"]["sales_director"]
    target_id = seed_data["users"]["emp_b"].id

    # Người kế thừa là chính mình -> 400
    res = client.post(
        f"/api/v1/users/{target_id}/deactivate",
        json={"successorUserId": target_id},
        headers=auth_header(token),
    )
    assert res.status_code == 400
    assert "Người kế thừa không thể là chính người dùng bị vô hiệu hóa." in res.json()["detail"]


def test_successor_must_be_active(client: TestClient, seed_data: dict, db_session: Session):
    """Người kế thừa bắt buộc phải ở trạng thái active."""
    token = seed_data["tokens"]["sales_director"]
    target_id = seed_data["users"]["emp_a"].id

    # Đưa emp_b về inactive
    emp_b = seed_data["users"]["emp_b"]
    emp_b.status = "inactive"
    db_session.commit()

    res = client.post(
        f"/api/v1/users/{target_id}/deactivate",
        json={"successorUserId": emp_b.id},
        headers=auth_header(token),
    )
    assert res.status_code == 400
    assert "hiện không ở trạng thái hoạt động" in res.json()["detail"]


# ==============================================================================
# 4. TÍCH HỢP DATA SCOPE SAU BÀN GIAO
# ==============================================================================

def test_successor_can_access_transferred_customer(client: TestClient, seed_data: dict, db_session: Session):
    """
    Sau khi bàn giao, Employee A (OWN scope) lập tức nhìn thấy khách hàng cust_b vừa nhận.
    """
    token_director = seed_data["tokens"]["sales_director"]
    token_emp_a = seed_data["tokens"]["emp_a"]
    target_id = seed_data["users"]["emp_b"].id
    successor_id = seed_data["users"]["emp_a"].id
    cust_b_id = seed_data["customers"]["cust_b"].id

    # Trước bàn giao: A không đọc được B -> 403
    res_before = client.get(f"/api/v1/customers/{cust_b_id}", headers=auth_header(token_emp_a))
    assert res_before.status_code == 403

    # Thực hiện bàn giao
    res_deact = client.post(
        f"/api/v1/users/{target_id}/deactivate",
        json={"successorUserId": successor_id},
        headers=auth_header(token_director),
    )
    assert res_deact.status_code == 200

    # Sau bàn giao: A đã là chủ sở hữu mới -> Đọc thành công 200
    res_after = client.get(f"/api/v1/customers/{cust_b_id}", headers=auth_header(token_emp_a))
    assert res_after.status_code == 200
    assert res_after.json()["id"] == cust_b_id


def test_old_user_cannot_access_transferred_customer(client: TestClient, seed_data: dict):
    token_director = seed_data["tokens"]["sales_director"]
    token_emp_b = seed_data["tokens"]["emp_b"]
    target_id = seed_data["users"]["emp_b"].id
    successor_id = seed_data["users"]["emp_a"].id
    cust_b_id = seed_data["customers"]["cust_b"].id

    # Bàn giao
    client.post(
        f"/api/v1/users/{target_id}/deactivate",
        json={"successorUserId": successor_id},
        headers=auth_header(token_director),
    )

    # User cũ (B) thử truy cập -> Bị chặn 401 vì tài khoản inactive
    res = client.get(f"/api/v1/customers/{cust_b_id}", headers=auth_header(token_emp_b))
    assert res.status_code == 401


def test_transferred_deal_respects_data_scope(client: TestClient, seed_data: dict):
    """
    Cơ hội bán hàng (Deal) sau khi bàn giao hiển thị đúng trong danh sách của người kế thừa theo Data Scope.
    """
    token_director = seed_data["tokens"]["sales_director"]
    token_emp_a = seed_data["tokens"]["emp_a"]
    target_id = seed_data["users"]["emp_b"].id
    successor_id = seed_data["users"]["emp_a"].id
    deal_b_id = seed_data["deals"]["deal_b"].id

    # Bàn giao
    client.post(
        f"/api/v1/users/{target_id}/deactivate",
        json={"successorUserId": successor_id},
        headers=auth_header(token_director),
    )

    # Employee A xem danh sách deals
    res_deals = client.get("/api/v1/deals", headers=auth_header(token_emp_a))
    assert res_deals.status_code == 200
    deal_ids = [d["id"] for d in res_deals.json()]
    assert deal_b_id in deal_ids
