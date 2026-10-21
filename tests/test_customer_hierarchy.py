"""
Bộ kiểm thử tự động (Unit Test / Integration Test) cho tính năng SCRUM-63:
Khai báo quan hệ Công ty mẹ - con và Tổng hợp giá trị Tập đoàn (Group Valuation Rollup).
Kiểm tra đầy đủ các kịch bản:
1. Gán công ty mẹ thành công.
2. Gỡ bỏ công ty mẹ thành công (parent_id = None).
3. Bắt lỗi khi tự gán chính mình làm công ty mẹ (HTTP 400).
4. Bắt lỗi chu trình lặp 2 cấp (A -> B -> A) và đa cấp (A -> B -> C -> A) (HTTP 400).
5. Bắt lỗi khi công ty mẹ hoặc khách hàng không tồn tại (HTTP 404).
6. Lấy danh sách công ty con trực tiếp (GET /subsidiaries).
7. Tính toán chính xác tổng giá trị tập đoàn (GET /group-summary).
8. Phân quyền truy cập theo Data Scope (RBAC / Record-level security: HTTP 403).
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.deal import Deal


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# 1. GÁN CÔNG TY MẸ THÀNH CÔNG (ASSIGN PARENT)
# ==============================================================================

def test_assign_parent_success(client: TestClient, seed_data: dict, db_session: Session):
    """
    Kịch bản: Sales Director gán Customer B làm công ty con của Customer A.
    - Kết quả: HTTP 200, message thành công, parent_id được cập nhật.
    """
    token_director = seed_data["tokens"]["sales_director"]
    cust_a_id = seed_data["customers"]["cust_a"].id
    cust_b_id = seed_data["customers"]["cust_b"].id

    payload = {"parent_id": cust_a_id}
    response = client.put(
        f"/api/v1/customers/{cust_b_id}/parent",
        json=payload,
        headers=auth_header(token_director),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["customer_id"] == cust_b_id
    assert data["parent_id"] == cust_a_id
    assert "thành công" in data["message"].lower()

    # Kiểm tra trong DB
    cust_b = db_session.query(Customer).filter(Customer.id == cust_b_id).first()
    assert cust_b.parent_id == cust_a_id


# ==============================================================================
# 2. GỠ BỎ CÔNG TY MẸ THÀNH CÔNG (REMOVE PARENT)
# ==============================================================================

def test_remove_parent_success(client: TestClient, seed_data: dict, db_session: Session):
    """
    Kịch bản: Gỡ bỏ công ty mẹ bằng cách gửi parent_id = None.
    - Kết quả: HTTP 200, parent_id trở về None.
    """
    token_director = seed_data["tokens"]["sales_director"]
    cust_a_id = seed_data["customers"]["cust_a"].id
    cust_b_id = seed_data["customers"]["cust_b"].id

    # Trước tiên gán B là con của A
    client.put(
        f"/api/v1/customers/{cust_b_id}/parent",
        json={"parent_id": cust_a_id},
        headers=auth_header(token_director),
    )

    # Gỡ bỏ liên kết (truyền parent_id = None)
    response = client.put(
        f"/api/v1/customers/{cust_b_id}/parent",
        json={"parent_id": None},
        headers=auth_header(token_director),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["customer_id"] == cust_b_id
    assert data["parent_id"] is None
    assert "gỡ bỏ" in data["message"].lower()

    # Kiểm tra trong DB
    cust_b = db_session.query(Customer).filter(Customer.id == cust_b_id).first()
    assert cust_b.parent_id is None


# ==============================================================================
# 3. BẮT LỖI TỰ GÁN CHÍNH MÌNH (SELF-ASSIGNMENT PREVENTION)
# ==============================================================================

def test_self_assignment_prevention(client: TestClient, seed_data: dict):
    """
    Kịch bản: Một công ty tự gán chính nó làm công ty mẹ (customer_id == parent_id).
    - Kết quả: HTTP 400 Bad Request kèm thông báo lỗi rõ ràng.
    """
    token_director = seed_data["tokens"]["sales_director"]
    cust_a_id = seed_data["customers"]["cust_a"].id

    response = client.put(
        f"/api/v1/customers/{cust_a_id}/parent",
        json={"parent_id": cust_a_id},
        headers=auth_header(token_director),
    )

    assert response.status_code == 400
    data = response.json()
    assert "Một công ty không thể tự làm công ty mẹ của chính mình" in data["detail"]


# ==============================================================================
# 4. BẮT LỖI CHU TRÌNH LẶP (CIRCULAR HIERARCHY PREVENTION)
# ==============================================================================

def test_circular_dependency_2_levels(client: TestClient, seed_data: dict):
    """
    Kịch bản vòng lặp 2 cấp (A -> B -> A):
    - Đã có: B là con của A (B.parent_id = A).
    - Cố tình gán: A là con của B (A.parent_id = B).
    - Kết quả: HTTP 400 Bad Request chặn chu trình lặp.
    """
    token_director = seed_data["tokens"]["sales_director"]
    cust_a_id = seed_data["customers"]["cust_a"].id
    cust_b_id = seed_data["customers"]["cust_b"].id

    # B là con của A
    resp_assign = client.put(
        f"/api/v1/customers/{cust_b_id}/parent",
        json={"parent_id": cust_a_id},
        headers=auth_header(token_director),
    )
    assert resp_assign.status_code == 200

    # Cố tình gán A là con của B -> Chu trình lặp!
    response = client.put(
        f"/api/v1/customers/{cust_a_id}/parent",
        json={"parent_id": cust_b_id},
        headers=auth_header(token_director),
    )

    assert response.status_code == 400
    data = response.json()
    assert "Phát hiện chu trình lặp" in data["detail"]


def test_circular_dependency_multi_levels(client: TestClient, seed_data: dict):
    """
    Kịch bản vòng lặp 3 cấp (A -> B -> C -> A):
    - Đã có: B là con của A, C là con của B.
    - Cố tình gán: A là con của C.
    - Kết quả: HTTP 400 Bad Request chặn chu trình lặp.
    """
    token_director = seed_data["tokens"]["sales_director"]
    cust_a_id = seed_data["customers"]["cust_a"].id
    cust_b_id = seed_data["customers"]["cust_b"].id
    cust_beta_id = seed_data["customers"]["cust_beta"].id

    # 1. B là con của A
    client.put(
        f"/api/v1/customers/{cust_b_id}/parent",
        json={"parent_id": cust_a_id},
        headers=auth_header(token_director),
    )

    # 2. Beta là con của B
    client.put(
        f"/api/v1/customers/{cust_beta_id}/parent",
        json={"parent_id": cust_b_id},
        headers=auth_header(token_director),
    )

    # 3. Cố tình gán A là con của Beta -> Chu trình lặp đa cấp!
    response = client.put(
        f"/api/v1/customers/{cust_a_id}/parent",
        json={"parent_id": cust_beta_id},
        headers=auth_header(token_director),
    )

    assert response.status_code == 400
    data = response.json()
    assert "Phát hiện chu trình lặp" in data["detail"]


# ==============================================================================
# 5. BẮT LỖI KHÔNG TỒN TẠI (HTTP 404 NOT FOUND)
# ==============================================================================

def test_customer_not_found(client: TestClient, seed_data: dict):
    """Khách hàng customer_id không tồn tại trong hệ thống -> HTTP 404."""
    token_director = seed_data["tokens"]["sales_director"]

    response = client.put(
        "/api/v1/customers/non-existent-id/parent",
        json={"parent_id": "cust-emp-a"},
        headers=auth_header(token_director),
    )
    assert response.status_code == 404
    assert "Khách hàng không tồn tại" in response.json()["detail"]


def test_parent_company_not_found(client: TestClient, seed_data: dict):
    """Công ty mẹ parent_id không tồn tại trong hệ thống -> HTTP 404."""
    token_director = seed_data["tokens"]["sales_director"]
    cust_a_id = seed_data["customers"]["cust_a"].id

    response = client.put(
        f"/api/v1/customers/{cust_a_id}/parent",
        json={"parent_id": "parent-does-not-exist"},
        headers=auth_header(token_director),
    )
    assert response.status_code == 404
    assert "Công ty mẹ không tồn tại" in response.json()["detail"]


# ==============================================================================
# 6. LẤY DANH SÁCH CÔNG TY CON (GET SUBSIDIARIES)
# ==============================================================================

def test_get_subsidiaries_list(client: TestClient, seed_data: dict):
    """
    Kịch bản: Gán B và Beta làm công ty con của A.
    Sau đó lấy danh sách công ty con của A:
    - Trả về danh sách gồm 2 công ty con với đầy đủ deals_count và total_deal_value.
    """
    token_director = seed_data["tokens"]["sales_director"]
    cust_a_id = seed_data["customers"]["cust_a"].id
    cust_b_id = seed_data["customers"]["cust_b"].id
    cust_beta_id = seed_data["customers"]["cust_beta"].id

    # Gán B và Beta làm con của A
    client.put(
        f"/api/v1/customers/{cust_b_id}/parent",
        json={"parent_id": cust_a_id},
        headers=auth_header(token_director),
    )
    client.put(
        f"/api/v1/customers/{cust_beta_id}/parent",
        json={"parent_id": cust_a_id},
        headers=auth_header(token_director),
    )

    response = client.get(
        f"/api/v1/customers/{cust_a_id}/subsidiaries",
        headers=auth_header(token_director),
    )
    assert response.status_code == 200
    subs = response.json()
    assert len(subs) == 2

    sub_ids = [s["id"] for s in subs]
    assert cust_b_id in sub_ids
    assert cust_beta_id in sub_ids

    # Kiểm tra thông tin deal của B (deal_b: 80,000,000)
    item_b = next(s for s in subs if s["id"] == cust_b_id)
    assert item_b["deals_count"] >= 1
    assert item_b["total_deal_value"] == 80000000.0


# ==============================================================================
# 7. TÍNH TOÁN TỔNG GIÁ TRỊ TẬP ĐOÀN (GROUP VALUATION ROLLUP)
# ==============================================================================

def test_group_summary_valuation_rollup(client: TestClient, seed_data: dict):
    """
    Kịch bản tổng hợp giá trị tập đoàn (Group Valuation Rollup):
    - Công ty mẹ: Customer A (deal_a: 50,000,000)
    - Công ty con 1: Customer B (deal_b: 80,000,000)
    - Công ty con 2: Customer Beta (deal_beta: 120,000,000)
    Kỳ vọng:
    - own_deal_value = 50,000,000
    - subsidiaries_deal_value = 80,000,000 + 120,000,000 = 200,000,000
    - total_group_value = 50,000,000 + 200,000,000 = 250,000,000
    - total_subsidiaries = 2
    """
    token_director = seed_data["tokens"]["sales_director"]
    cust_a_id = seed_data["customers"]["cust_a"].id
    cust_b_id = seed_data["customers"]["cust_b"].id
    cust_beta_id = seed_data["customers"]["cust_beta"].id

    client.put(
        f"/api/v1/customers/{cust_b_id}/parent",
        json={"parent_id": cust_a_id},
        headers=auth_header(token_director),
    )
    client.put(
        f"/api/v1/customers/{cust_beta_id}/parent",
        json={"parent_id": cust_a_id},
        headers=auth_header(token_director),
    )

    response = client.get(
        f"/api/v1/customers/{cust_a_id}/group-summary",
        headers=auth_header(token_director),
    )
    assert response.status_code == 200
    summary = response.json()

    assert summary["parent_company_id"] == cust_a_id
    assert summary["parent_company_name"] == seed_data["customers"]["cust_a"].company
    assert summary["total_subsidiaries"] == 2
    assert summary["own_deal_value"] == 50000000.0
    assert summary["subsidiaries_deal_value"] == 200000000.0
    assert summary["total_group_value"] == 250000000.0
    assert len(summary["subsidiaries"]) == 2


# ==============================================================================
# 8. PHÂN QUYỀN TRUY CẬP (RBAC & RECORD-LEVEL SECURITY)
# ==============================================================================

def test_employee_a_cannot_modify_employee_b_hierarchy(client: TestClient, seed_data: dict):
    """
    Kiểm tra bảo mật phân quyền bản ghi:
    Employee A chỉ có quyền trên khách hàng của A (cust_a).
    Khi cố tình sửa công ty mẹ của Customer B (cust_b):
    - Trả về HTTP 403 Forbidden.
    """
    token_emp_a = seed_data["tokens"]["emp_a"]
    cust_a_id = seed_data["customers"]["cust_a"].id
    cust_b_id = seed_data["customers"]["cust_b"].id

    response = client.put(
        f"/api/v1/customers/{cust_b_id}/parent",
        json={"parent_id": cust_a_id},
        headers=auth_header(token_emp_a),
    )

    assert response.status_code == 403
    assert "Bạn không có quyền truy cập dữ liệu này." in response.json()["detail"]


def test_team_lead_can_access_team_member_hierarchy(client: TestClient, seed_data: dict):
    """
    Trưởng nhóm (Team Leader) có quyền TEAM:
    Có thể xem danh sách công ty con và group-summary của thành viên cùng nhóm (Customer B).
    - Trả về HTTP 200.
    """
    token_team_lead = seed_data["tokens"]["team_leader"]
    cust_b_id = seed_data["customers"]["cust_b"].id

    response = client.get(
        f"/api/v1/customers/{cust_b_id}/group-summary",
        headers=auth_header(token_team_lead),
    )
    assert response.status_code == 200
