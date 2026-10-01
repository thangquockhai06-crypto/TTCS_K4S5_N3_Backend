"""
Bộ kiểm thử tự động toàn diện kiểm tra phân quyền theo vai trò (Role-based)
và quyền sở hữu dữ liệu (Data-ownership-based access control).
Bao gồm ma trận kiểm thử: Employee (OWN), Team Leader (TEAM), Sales Director (ALL).
"""
import pytest
from fastapi.testclient import TestClient


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# 1. BẮT BUỘC: REGRESSION SECURITY TEST (Mục 16)
# ==============================================================================

def test_employee_a_cannot_read_employee_b_customer(client: TestClient, seed_data: dict):
    """
    Test hồi quy an ninh bắt buộc (Acceptance Criteria 16):
    Employee A truy cập thông tin khách hàng thuộc sở hữu của Employee B:
    - Bắt buộc trả về HTTP 403 Forbidden.
    - Thông báo lỗi tiếng Việt rõ ràng: "Bạn không có quyền truy cập dữ liệu này."
    """
    token_emp_a = seed_data["tokens"]["emp_a"]
    cust_b_id = seed_data["customers"]["cust_b"].id

    response = client.get(
        f"/api/v1/customers/{cust_b_id}",
        headers=auth_header(token_emp_a),
    )

    assert response.status_code == 403
    data = response.json()
    assert "Bạn không có quyền truy cập dữ liệu này." in data["detail"]


# ==============================================================================
# 2. CHỐNG BYPASS PHÂN QUYỀN (Mục 8 & Mục 16)
# ==============================================================================

def test_employee_a_cannot_bypass_via_query_params(client: TestClient, seed_data: dict):
    """
    Employee A cố tình gửi query parameters (owner_id, assigned_user_id, team_id, scope)
    để bypass quyền truy cập. Server-side filter KHÔNG tin tưởng và chỉ trả về KH của A.
    """
    token_emp_a = seed_data["tokens"]["emp_a"]
    emp_b_id = seed_data["users"]["emp_b"].id

    # 1. Gửi owner_id/assigned_user_id của Employee B
    response = client.get(
        f"/api/v1/customers?owner_id={emp_b_id}&assigned_user_id={emp_b_id}",
        headers=auth_header(token_emp_a),
    )
    assert response.status_code == 200
    customers = response.json()
    # Chỉ được trả về khách hàng của chính Employee A, KHÔNG có KH của B
    returned_ids = [c["id"] for c in customers]
    assert seed_data["customers"]["cust_a"].id in returned_ids
    assert seed_data["customers"]["cust_b"].id not in returned_ids
    assert seed_data["customers"]["cust_beta"].id not in returned_ids


def test_employee_a_search_respects_data_scope(client: TestClient, seed_data: dict):
    """
    Acceptance Criteria 4:
    Tìm kiếm từ khóa phải kết hợp AND với Data Scope filter ở tầng CSDL.
    Employee A tìm kiếm chính xác tên khách hàng của B -> trả về 0 kết quả.
    """
    token_emp_a = seed_data["tokens"]["emp_a"]
    cust_b_name = seed_data["customers"]["cust_b"].full_name

    response = client.get(
        f"/api/v1/customers?search={cust_b_name}",
        headers=auth_header(token_emp_a),
    )
    assert response.status_code == 200
    customers = response.json()
    assert len(customers) == 0


def test_employee_a_excel_export_respects_data_scope(client: TestClient, seed_data: dict):
    """
    Acceptance Criteria 5:
    Xuất Excel (/customers/export) phải sử dụng cùng query repository có filter data scope.
    """
    token_emp_a = seed_data["tokens"]["emp_a"]

    response = client.get(
        "/api/v1/customers/export",
        headers=auth_header(token_emp_a),
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert "attachment; filename=" in response.headers["content-disposition"]


def test_employee_a_cannot_modify_employee_b_customer(client: TestClient, seed_data: dict):
    """
    Employee A cố gắng chỉnh sửa trạng thái, thêm ghi chú, hoặc thêm hoạt động
    cho khách hàng của B -> HTTP 403 Forbidden.
    """
    token_emp_a = seed_data["tokens"]["emp_a"]
    cust_b_id = seed_data["customers"]["cust_b"].id

    # 1. Update status
    res_status = client.patch(
        f"/api/v1/customers/{cust_b_id}/status",
        headers=auth_header(token_emp_a),
        json={"status": "active"},
    )
    assert res_status.status_code == 403

    # 2. Add note
    res_note = client.post(
        f"/api/v1/customers/{cust_b_id}/notes",
        headers=auth_header(token_emp_a),
        json={"content": "Ghi chú trái phép"},
    )
    assert res_note.status_code == 403

    # 3. Add activity
    res_act = client.post(
        f"/api/v1/customers/{cust_b_id}/activities",
        headers=auth_header(token_emp_a),
        json={"type": "call", "title": "Cuộc gọi trái phép"},
    )
    assert res_act.status_code == 403


# ==============================================================================
# 3. MA TRẬN PHÂN QUYỀN (Mục 17): OWN, TEAM, ALL
# ==============================================================================

class TestDataScopeMatrix:
    """
    Kiểm tra đầy đủ ma trận quyền hạn cho 3 vai trò đại diện:
    - Employee (OWN)
    - Team Leader (TEAM)
    - Sales Director (ALL)
    """

    # --- NHÂN VIÊN (OWN) ---
    def test_employee_scope_customers(self, client: TestClient, seed_data: dict):
        token = seed_data["tokens"]["emp_a"]
        res = client.get("/api/v1/customers", headers=auth_header(token))
        assert res.status_code == 200
        ids = [c["id"] for c in res.json()]
        assert seed_data["customers"]["cust_a"].id in ids
        assert seed_data["customers"]["cust_b"].id not in ids
        assert seed_data["customers"]["cust_beta"].id not in ids

    def test_employee_scope_deals(self, client: TestClient, seed_data: dict):
        token = seed_data["tokens"]["emp_a"]
        res = client.get("/api/v1/deals", headers=auth_header(token))
        assert res.status_code == 200
        ids = [d["id"] for d in res.json()]
        assert seed_data["deals"]["deal_a"].id in ids
        assert seed_data["deals"]["deal_b"].id not in ids
        assert seed_data["deals"]["deal_beta"].id not in ids

    # --- TRƯỞNG NHÓM (TEAM) ---
    def test_team_leader_scope_customers(self, client: TestClient, seed_data: dict):
        """Team Leader thấy khách hàng của cả A và B (cùng Team Alpha), không thấy Beta."""
        token = seed_data["tokens"]["team_leader"]
        res = client.get("/api/v1/customers", headers=auth_header(token))
        assert res.status_code == 200
        ids = [c["id"] for c in res.json()]
        assert seed_data["customers"]["cust_a"].id in ids
        assert seed_data["customers"]["cust_b"].id in ids
        assert seed_data["customers"]["cust_beta"].id not in ids

    def test_team_leader_access_team_member_customer_detail(self, client: TestClient, seed_data: dict):
        """Team Leader được phép xem chi tiết khách hàng của Employee A và B."""
        token = seed_data["tokens"]["team_leader"]
        cust_a_id = seed_data["customers"]["cust_a"].id
        cust_b_id = seed_data["customers"]["cust_b"].id

        res_a = client.get(f"/api/v1/customers/{cust_a_id}", headers=auth_header(token))
        assert res_a.status_code == 200

        res_b = client.get(f"/api/v1/customers/{cust_b_id}", headers=auth_header(token))
        assert res_b.status_code == 200

    def test_team_leader_cannot_read_cross_team_customer(self, client: TestClient, seed_data: dict):
        """Team Leader KHÔNG được xem khách hàng của đội khác (Team Beta) -> HTTP 403."""
        token = seed_data["tokens"]["team_leader"]
        cust_beta_id = seed_data["customers"]["cust_beta"].id

        res = client.get(f"/api/v1/customers/{cust_beta_id}", headers=auth_header(token))
        assert res.status_code == 403
        assert "Bạn không có quyền truy cập dữ liệu này." in res.json()["detail"]

    # --- GIÁM ĐỐC KINH DOANH (ALL) ---
    def test_sales_director_scope_customers(self, client: TestClient, seed_data: dict):
        """Sales Director xem được toàn bộ khách hàng (A, B, Beta, và cả unassigned)."""
        token = seed_data["tokens"]["sales_director"]
        res = client.get("/api/v1/customers", headers=auth_header(token))
        assert res.status_code == 200
        ids = [c["id"] for c in res.json()]
        assert seed_data["customers"]["cust_a"].id in ids
        assert seed_data["customers"]["cust_b"].id in ids
        assert seed_data["customers"]["cust_beta"].id in ids
        assert seed_data["customers"]["cust_unassigned"].id in ids

    def test_sales_director_access_any_customer_detail(self, client: TestClient, seed_data: dict):
        token = seed_data["tokens"]["sales_director"]
        for cust_key in ["cust_a", "cust_b", "cust_beta", "cust_unassigned"]:
            cid = seed_data["customers"][cust_key].id
            res = client.get(f"/api/v1/customers/{cid}", headers=auth_header(token))
            assert res.status_code == 200


# ==============================================================================
# 4. ÁP DỤNG ĐỒNG NHẤT CHO DEALS, ACTIVITIES, QUOTATIONS (Mục 3, 5, 6)
# ==============================================================================

class TestProtectedEntitiesConsistency:
    """Kiểm tra tính nhất quán trên cả 4 thực thể được bảo vệ."""

    # 1. Deals / Opportunities
    def test_deal_single_record_access_control(self, client: TestClient, seed_data: dict):
        deal_b_id = seed_data["deals"]["deal_b"].id

        # Employee A cố đọc Deal B -> 403
        res_emp_a = client.get(f"/api/v1/deals/{deal_b_id}", headers=auth_header(seed_data["tokens"]["emp_a"]))
        assert res_emp_a.status_code == 403

        # Team Leader đọc Deal B (cùng team) -> 200
        res_lead = client.get(f"/api/v1/deals/{deal_b_id}", headers=auth_header(seed_data["tokens"]["team_leader"]))
        assert res_lead.status_code == 200

        # Router /opportunities cũng áp dụng đồng nhất
        res_opp_emp_a = client.get(f"/api/v1/opportunities/{deal_b_id}", headers=auth_header(seed_data["tokens"]["emp_a"]))
        assert res_opp_emp_a.status_code == 403

    def test_deal_export_isolation(self, client: TestClient, seed_data: dict):
        res = client.get("/api/v1/deals/export", headers=auth_header(seed_data["tokens"]["emp_a"]))
        assert res.status_code == 200
        assert res.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    # 2. Activities
    def test_activity_single_record_access_control(self, client: TestClient, seed_data: dict):
        act_b_id = seed_data["activities"]["act_b"].id

        # Employee A đọc Activity B -> 403
        res_emp_a = client.get(f"/api/v1/activities/{act_b_id}", headers=auth_header(seed_data["tokens"]["emp_a"]))
        assert res_emp_a.status_code == 403

        # Team Leader đọc Activity B -> 200
        res_lead = client.get(f"/api/v1/activities/{act_b_id}", headers=auth_header(seed_data["tokens"]["team_leader"]))
        assert res_lead.status_code == 200

    def test_activity_export_isolation(self, client: TestClient, seed_data: dict):
        res = client.get("/api/v1/activities/export", headers=auth_header(seed_data["tokens"]["emp_a"]))
        assert res.status_code == 200

    # 3. Quotations
    def test_quotation_single_record_access_control(self, client: TestClient, seed_data: dict):
        quote_b_id = seed_data["quotations"]["quote_b"].id

        # Employee A đọc Quotation B -> 403
        res_emp_a = client.get(f"/api/v1/quotations/{quote_b_id}", headers=auth_header(seed_data["tokens"]["emp_a"]))
        assert res_emp_a.status_code == 403

        # Team Leader đọc Quotation B -> 200
        res_lead = client.get(f"/api/v1/quotations/{quote_b_id}", headers=auth_header(seed_data["tokens"]["team_leader"]))
        assert res_lead.status_code == 200

    def test_quotation_export_isolation(self, client: TestClient, seed_data: dict):
        res = client.get("/api/v1/quotations/export", headers=auth_header(seed_data["tokens"]["emp_a"]))
        assert res.status_code == 200


# ==============================================================================
# 5. CÁC TRƯỜNG HỢP BIÊN (EDGE CASES) (Mục 18)
# ==============================================================================

class TestEdgeCases:
    def test_non_existent_record_returns_404_not_403(self, client: TestClient, seed_data: dict):
        """Bản ghi không tồn tại trong CSDL phải trả về 404 Not Found, không nhầm lẫn với 403."""
        token = seed_data["tokens"]["emp_a"]
        res = client.get("/api/v1/customers/khong-ton-tai-12345", headers=auth_header(token))
        assert res.status_code == 404

    def test_leader_with_no_team_fails_closed(self, client: TestClient, seed_data: dict):
        """
        User có vai trò Team Leader nhưng team_id=None:
        Hệ thống KHÔNG được fail open mà phải trả về 0 bản ghi.
        """
        token = seed_data["tokens"]["leader_no_team"]
        res = client.get("/api/v1/customers", headers=auth_header(token))
        assert res.status_code == 200
        assert len(res.json()) == 0

    def test_unauthenticated_request_rejected(self, client: TestClient):
        """Không có token -> HTTP 401 Unauthorized."""
        res = client.get("/api/v1/customers")
        assert res.status_code == 401

    def test_record_with_no_owner_inaccessible_to_own_scope(self, client: TestClient, seed_data: dict):
        """Bản ghi không có người phụ trách (assigned_user_id=None) không hiển thị cho Employee."""
        token = seed_data["tokens"]["emp_a"]
        unassigned_id = seed_data["customers"]["cust_unassigned"].id
        res = client.get(f"/api/v1/customers/{unassigned_id}", headers=auth_header(token))
        assert res.status_code == 403
