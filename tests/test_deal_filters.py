from datetime import date, timedelta
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.deal import Deal, deal_products
from app.models.product import Product
from app.models.saved_deal_filter import SavedDealFilter


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def filter_setup_data(db_session: Session, seed_data: dict) -> dict:
    """Bổ sung thêm sản phẩm và các deal đa dạng để phục vụ kiểm thử lọc nâng cao."""
    emp_a = seed_data["users"]["emp_a"]
    emp_b = seed_data["users"]["emp_b"]
    emp_beta = seed_data["users"]["emp_beta"]
    cust_a = seed_data["customers"]["cust_a"]
    cust_b = seed_data["customers"]["cust_b"]
    cust_beta = seed_data["customers"]["cust_beta"]

    # 1. Tạo 2 sản phẩm mẫu
    prod_crm = Product(
        id="prod-crm-cloud",
        code="CRM-CLOUD-01",
        name="NexusCRM Cloud Enterprise",
        category="Phần mềm",
        selling_price=50000000.0,
        cost_price=20000000.0,
    )
    prod_erp = Product(
        id="prod-erp-module",
        code="ERP-MOD-01",
        name="Module Tích Hợp ERP SAP",
        category="Phần mềm",
        selling_price=100000000.0,
        cost_price=40000000.0,
    )
    db_session.add_all([prod_crm, prod_erp])
    db_session.commit()

    # 2. Cập nhật ngày chốt dự kiến và giá trị cho các deals có sẵn
    deal_a = seed_data["deals"]["deal_a"]
    deal_a.expected_close_date = date(2026, 10, 25)
    deal_a.value = 50000000.00
    deal_a.stage = "proposal"

    deal_b = seed_data["deals"]["deal_b"]
    deal_b.expected_close_date = date(2026, 11, 15)
    deal_b.value = 80000000.00
    deal_b.stage = "negotiation"

    deal_beta = seed_data["deals"]["deal_beta"]
    deal_beta.expected_close_date = date(2026, 12, 10)
    deal_beta.value = 150000000.00
    deal_beta.stage = "won"

    # 3. Tạo thêm deal cho emp_a để test phân trang và tìm kiếm
    deal_a2 = Deal(
        id="deal-emp-a-2",
        title="Dự án Chuyển đổi số CRM Tech Corp",
        value=30000000.00,
        stage="lead",
        probability=30,
        customer_id=cust_a.id,
        owner_id=emp_a.id,
        expected_close_date=date(2026, 10, 30),
    )
    db_session.add(deal_a2)
    db_session.commit()

    # 4. Gắn sản phẩm vào deal_a qua bảng liên kết deal_products
    db_session.execute(
        deal_products.insert().values(deal_id=deal_a.id, product_id=prod_crm.id)
    )
    db_session.execute(
        deal_products.insert().values(deal_id=deal_beta.id, product_id=prod_erp.id)
    )
    db_session.commit()

    return {
        "products": {"crm": prod_crm, "erp": prod_erp},
        "deals": {
            "deal_a": deal_a,
            "deal_a2": deal_a2,
            "deal_b": deal_b,
            "deal_beta": deal_beta,
        },
    }


# ==============================================================================
# 1. KIỂM THỬ LỌC THEO TỪNG TIÊU CHÍ ĐƠN LẺ
# ==============================================================================

def test_filter_deals_by_stage_single_and_multiple(client: TestClient, seed_data: dict, filter_setup_data: dict):
    """Test lọc theo 1 hoặc nhiều giai đoạn (stages), không phân biệt hoa thường."""
    token = seed_data["tokens"]["sales_director"]

    # 1. Lọc đơn lẻ: stage = proposal
    res1 = client.get("/api/v1/deals", params={"stages": "proposal", "page": 1}, headers=auth_header(token))
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["total_items"] >= 1
    for item in data1["items"]:
        assert item["stage"] == "proposal"

    # 2. Lọc hoa thường: stages = ['PROPOSAL', 'NEGOTIATION']
    res2 = client.get(
        "/api/v1/deals",
        params=[("stages", "PROPOSAL"), ("stages", "NEGOTIATION"), ("page", "1")],
        headers=auth_header(token),
    )
    assert res2.status_code == 200
    data2 = res2.json()
    stages_in_res = {item["stage"] for item in data2["items"]}
    assert stages_in_res.issubset({"proposal", "negotiation"})
    assert "won" not in stages_in_res


def test_filter_deals_by_amount_range(client: TestClient, seed_data: dict, filter_setup_data: dict):
    """Test lọc theo khoảng giá trị cơ hội: min_amount & max_amount."""
    token = seed_data["tokens"]["sales_director"]

    # Min amount = 60,000,000 (sẽ loại deal 30M và 50M)
    res_min = client.get("/api/v1/deals", params={"min_amount": 60000000, "page": 1}, headers=auth_header(token))
    assert res_min.status_code == 200
    data_min = res_min.json()
    for item in data_min["items"]:
        assert float(item["amount"]) >= 60000000.0

    # Max amount = 60,000,000 (sẽ chỉ giữ deal 30M và 50M)
    res_max = client.get("/api/v1/deals", params={"max_amount": 60000000, "page": 1}, headers=auth_header(token))
    assert res_max.status_code == 200
    data_max = res_max.json()
    for item in data_max["items"]:
        assert float(item["amount"]) <= 60000000.0

    # Khoảng min_amount = 40M và max_amount = 90M (sẽ có 50M và 80M)
    res_range = client.get(
        "/api/v1/deals",
        params={"min_amount": 40000000, "max_amount": 90000000, "page": 1},
        headers=auth_header(token),
    )
    assert res_range.status_code == 200
    data_range = res_range.json()
    deal_ids = [item["id"] for item in data_range["items"]]
    assert "deal-emp-a" in deal_ids
    assert "deal-emp-b" in deal_ids
    assert "deal-emp-beta" not in deal_ids


def test_filter_deals_by_expected_close_date_range(client: TestClient, seed_data: dict, filter_setup_data: dict):
    """Test lọc theo khoảng ngày chốt dự kiến (expected_close_from, expected_close_to)."""
    token = seed_data["tokens"]["sales_director"]

    # Khoảng tháng 10/2026: từ 2026-10-01 đến 2026-10-31
    res = client.get(
        "/api/v1/deals",
        params={
            "expected_close_from": "2026-10-01",
            "expected_close_to": "2026-10-31",
            "page": 1,
        },
        headers=auth_header(token),
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_items"] >= 2
    for item in data["items"]:
        close_date = date.fromisoformat(item["expectedCloseDate"])
        assert date(2026, 10, 1) <= close_date <= date(2026, 10, 31)


def test_filter_deals_by_search_keyword(client: TestClient, seed_data: dict, filter_setup_data: dict):
    """Test tìm kiếm theo từ khóa search (title, deal id, tên khách hàng)."""
    token = seed_data["tokens"]["sales_director"]

    # 1. Tìm theo tên cơ hội
    res1 = client.get("/api/v1/deals", params={"search": "Chuyển đổi số", "page": 1}, headers=auth_header(token))
    assert res1.status_code == 200
    assert any("Chuyển đổi số" in item["title"] for item in res1.json()["items"])

    # 2. Tìm theo tên khách hàng qua JOIN Customer
    cust_a_name = seed_data["customers"]["cust_a"].full_name
    res2 = client.get("/api/v1/deals", params={"search": cust_a_name, "page": 1}, headers=auth_header(token))
    assert res2.status_code == 200
    for item in res2.json()["items"]:
        assert item["customerId"] == seed_data["customers"]["cust_a"].id

    # 3. Tìm theo mã cơ hội deal_id
    res3 = client.get("/api/v1/deals", params={"search": "deal-emp-beta", "page": 1}, headers=auth_header(token))
    assert res3.status_code == 200
    assert len(res3.json()["items"]) == 1
    assert res3.json()["items"][0]["id"] == "deal-emp-beta"


def test_filter_deals_by_product(client: TestClient, seed_data: dict, filter_setup_data: dict):
    """Test lọc cơ hội theo sản phẩm quan tâm (product_id)."""
    token = seed_data["tokens"]["sales_director"]
    crm_prod_id = filter_setup_data["products"]["crm"].id
    erp_prod_id = filter_setup_data["products"]["erp"].id

    # Lọc theo sản phẩm CRM -> trả về deal_a
    res_crm = client.get("/api/v1/deals", params={"product_id": crm_prod_id, "page": 1}, headers=auth_header(token))
    assert res_crm.status_code == 200
    crm_deal_ids = [d["id"] for d in res_crm.json()["items"]]
    assert "deal-emp-a" in crm_deal_ids
    assert "deal-emp-beta" not in crm_deal_ids

    # Lọc theo sản phẩm ERP -> trả về deal_beta
    res_erp = client.get("/api/v1/deals", params={"product_id": erp_prod_id, "page": 1}, headers=auth_header(token))
    assert res_erp.status_code == 200
    erp_deal_ids = [d["id"] for d in res_erp.json()["items"]]
    assert "deal-emp-beta" in erp_deal_ids
    assert "deal-emp-a" not in erp_deal_ids


# ==============================================================================
# 2. KIỂM THỬ TỔ HỢP ĐA TIÊU CHÍ (AND LOGIC) & TÍNH TỔNG PIPELINE
# ==============================================================================

def test_filter_multi_criteria_and_total_amount_sum(client: TestClient, seed_data: dict, filter_setup_data: dict):
    """
    Test kết hợp đồng thời (AND logic) nhiều tiêu chí:
    search + stages + min_amount + max_amount + date range
    và kiểm tra tính toán tổng giá trị pipeline (total_amount_sum).
    """
    token = seed_data["tokens"]["sales_director"]

    params = [
        ("stages", "proposal"),
        ("stages", "negotiation"),
        ("min_amount", "40000000"),
        ("max_amount", "90000000"),
        ("expected_close_from", "2026-10-01"),
        ("expected_close_to", "2026-11-30"),
        ("page", "1"),
        ("page_size", "20"),
    ]
    res = client.get("/api/v1/deals", params=params, headers=auth_header(token))
    assert res.status_code == 200
    data = res.json()

    assert data["total_items"] == 2  # deal_a (50M) và deal_b (80M)
    assert data["page"] == 1
    assert data["page_size"] == 20
    assert data["total_pages"] == 1
    # Tổng giá trị: 50M + 80M = 130M
    assert float(data["total_amount_sum"]) == 130000000.0


# ==============================================================================
# 3. KIỂM THỬ PHÂN TRANG VÀ SẮP XẾP
# ==============================================================================

def test_pagination_and_sorting(client: TestClient, seed_data: dict, filter_setup_data: dict):
    """Test phân trang (page, page_size) và sắp xếp (sort_by, sort_order)."""
    token = seed_data["tokens"]["sales_director"]

    # 1. Phân trang page=1, page_size=2
    res_page1 = client.get(
        "/api/v1/deals",
        params={"page": 1, "page_size": 2, "sort_by": "amount", "sort_order": "asc"},
        headers=auth_header(token),
    )
    assert res_page1.status_code == 200
    data1 = res_page1.json()
    assert len(data1["items"]) == 2
    assert data1["page"] == 1
    assert data1["total_pages"] >= 2

    # Giá trị tăng dần: item 0 <= item 1
    assert float(data1["items"][0]["amount"]) <= float(data1["items"][1]["amount"])

    # 2. Trang 2
    res_page2 = client.get(
        "/api/v1/deals",
        params={"page": 2, "page_size": 2, "sort_by": "amount", "sort_order": "asc"},
        headers=auth_header(token),
    )
    assert res_page2.status_code == 200
    data2 = res_page2.json()
    assert data2["page"] == 2
    # Giá trị ở trang 2 phải >= giá trị cuối của trang 1
    assert float(data2["items"][0]["amount"]) >= float(data1["items"][1]["amount"])


# ==============================================================================
# 4. KIỂM THỬ BẢO MẬT & PHÂN QUYỀN SỞ HỮU (RECORD-LEVEL SECURITY)
# ==============================================================================

def test_sales_rep_record_level_security_override(client: TestClient, seed_data: dict, filter_setup_data: dict):
    """
    SALES_REP (Employee):
    - Chỉ được phép xem deals do chính mình phụ trách.
    - Cố tình truyền owner_id của người khác -> Backend bắt buộc ghi đè/giới hạn về chính mình.
    """
    token_emp_a = seed_data["tokens"]["emp_a"]
    emp_b_id = seed_data["users"]["emp_b"].id

    # 1. Emp A xem danh sách với filter bình thường
    res = client.get("/api/v1/deals", params={"page": 1}, headers=auth_header(token_emp_a))
    assert res.status_code == 200
    data = res.json()
    for item in data["items"]:
        assert item["ownerId"] == seed_data["users"]["emp_a"].id

    # 2. Emp A cố tình truyền owner_id của Emp B
    bypass_res = client.get(
        "/api/v1/deals",
        params={"owner_id": emp_b_id, "page": 1},
        headers=auth_header(token_emp_a),
    )
    assert bypass_res.status_code == 200
    bypass_data = bypass_res.json()
    # Backend bắt buộc ghi đè -> KHÔNG BAO GIỜ trả về deal của B
    for item in bypass_data["items"]:
        assert item["ownerId"] == seed_data["users"]["emp_a"].id
        assert item["ownerId"] != emp_b_id


def test_team_lead_record_level_security(client: TestClient, seed_data: dict, filter_setup_data: dict):
    """
    TEAM_LEAD (Team Alpha):
    - Xem được toàn bộ deals của thành viên trong nhóm mình (Emp A và Emp B).
    - KHÔNG xem được deals của Emp Beta (thuộc Team Beta).
    - Nếu truyền owner_id ngoài team -> trả về 0 kết quả (Fail-closed).
    """
    token_lead = seed_data["tokens"]["team_leader"]
    emp_beta_id = seed_data["users"]["emp_beta"].id

    # 1. Team Leader lấy toàn bộ deals của team
    res = client.get("/api/v1/deals", params={"page": 1}, headers=auth_header(token_lead))
    assert res.status_code == 200
    deal_ids = [d["id"] for d in res.json()["items"]]
    assert "deal-emp-a" in deal_ids
    assert "deal-emp-b" in deal_ids
    assert "deal-emp-beta" not in deal_ids

    # 2. Team Leader lọc theo nhân viên ngoài nhóm (Emp Beta) -> 0 kết quả
    cross_res = client.get(
        "/api/v1/deals",
        params={"owner_id": emp_beta_id, "page": 1},
        headers=auth_header(token_lead),
    )
    assert cross_res.status_code == 200
    assert cross_res.json()["total_items"] == 0


def test_director_can_filter_any_owner(client: TestClient, seed_data: dict, filter_setup_data: dict):
    """DIRECTOR / ADMIN: Toàn quyền xem và lọc theo bất kỳ nhân viên nào."""
    token_director = seed_data["tokens"]["sales_director"]
    emp_beta_id = seed_data["users"]["emp_beta"].id

    res = client.get(
        "/api/v1/deals",
        params={"owner_id": emp_beta_id, "page": 1},
        headers=auth_header(token_director),
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_items"] >= 1
    for item in data["items"]:
        assert item["ownerId"] == emp_beta_id


# ==============================================================================
# 5. KIỂM THỬ QUẢN LÝ BỘ LỌC CÁ NHÂN (SAVED FILTERS CRUD & IS_DEFAULT)
# ==============================================================================

def test_saved_deal_filters_crud_and_default_flag(client: TestClient, seed_data: dict):
    """
    Kiểm thử trọn vẹn CRUD bộ lọc cá nhân cho Deals:
    - Tạo mới với is_default = True.
    - Tạo bộ lọc thứ hai với is_default = True -> bộ lọc thứ nhất tự chuyển False.
    - Sửa tên, cập nhật điều kiện (PUT và PATCH).
    - Xem chi tiết và xóa bộ lọc.
    """
    token = seed_data["tokens"]["emp_a"]

    # 1. Tạo bộ lọc thứ nhất: "Deals chốt trong tuần" (is_default = True)
    res_create1 = client.post(
        "/api/v1/deals/saved-filters",
        json={
            "name": "Deals chốt trong tuần",
            "filter_criteria": {
                "stages": ["proposal", "negotiation"],
                "min_amount": 50000000,
            },
            "is_default": True,
        },
        headers=auth_header(token),
    )
    assert res_create1.status_code == 201
    filter1 = res_create1.json()
    assert filter1["name"] == "Deals chốt trong tuần"
    assert filter1["is_default"] is True
    assert filter1["filter_criteria"]["min_amount"] == 50000000

    # 2. Tạo bộ lọc thứ hai: "Deals lớn > 100tr" (is_default = True)
    res_create2 = client.post(
        "/api/v1/deals/saved-filters",
        json={
            "name": "Deals lớn > 100tr",
            "filter_criteria": {"min_amount": 100000000},
            "is_default": True,
        },
        headers=auth_header(token),
    )
    assert res_create2.status_code == 201
    filter2 = res_create2.json()
    assert filter2["is_default"] is True

    # Kiểm tra lại bộ lọc 1: cờ is_default phải tự động chuyển thành False
    res_get1 = client.get(f"/api/v1/deals/saved-filters/{filter1['id']}", headers=auth_header(token))
    assert res_get1.status_code == 200
    assert res_get1.json()["is_default"] is False

    # 3. Lấy danh sách bộ lọc cá nhân của user
    res_list = client.get("/api/v1/deals/saved-filters", headers=auth_header(token))
    assert res_list.status_code == 200
    listed_ids = [f["id"] for f in res_list.json()]
    assert filter1["id"] in listed_ids
    assert filter2["id"] in listed_ids

    # 4. Cập nhật bộ lọc qua PATCH
    res_patch = client.patch(
        f"/api/v1/deals/saved-filters/{filter1['id']}",
        json={"name": "Deals chốt trong tuần (Đã sửa)"},
        headers=auth_header(token),
    )
    assert res_patch.status_code == 200
    assert res_patch.json()["name"] == "Deals chốt trong tuần (Đã sửa)"

    # 5. Cập nhật qua PUT
    res_put = client.put(
        f"/api/v1/deals/saved-filters/{filter1['id']}",
        json={
            "name": "Deals chốt trong tuần (Đã PUT)",
            "filter_criteria": {"stages": ["negotiation"]},
            "is_default": True,
        },
        headers=auth_header(token),
    )
    assert res_put.status_code == 200
    assert res_put.json()["name"] == "Deals chốt trong tuần (Đã PUT)"
    assert res_put.json()["is_default"] is True

    # 6. Xóa bộ lọc cá nhân
    res_del = client.delete(f"/api/v1/deals/saved-filters/{filter1['id']}", headers=auth_header(token))
    assert res_del.status_code == 204

    # Kiểm tra lại sau khi xóa -> 404
    assert client.get(f"/api/v1/deals/saved-filters/{filter1['id']}", headers=auth_header(token)).status_code == 404


def test_saved_deal_filters_user_isolation(client: TestClient, seed_data: dict):
    """Bộ lọc cá nhân thuộc quyền sở hữu riêng, user khác không can thiệp hay nhìn thấy."""
    token_a = seed_data["tokens"]["emp_a"]
    token_b = seed_data["tokens"]["emp_b"]

    # User A tạo bộ lọc
    create = client.post(
        "/api/v1/deals/saved-filters",
        json={"name": "Filter bí mật của A", "filter_criteria": {"stages": ["lead"]}},
        headers=auth_header(token_a),
    )
    assert create.status_code == 201
    filter_id = create.json()["id"]

    # User B không thấy trong danh sách của mình
    list_b = client.get("/api/v1/deals/saved-filters", headers=auth_header(token_b))
    assert filter_id not in [f["id"] for f in list_b.json()]

    # User B cố tình truy cập chi tiết -> 403 Forbidden
    get_b = client.get(f"/api/v1/deals/saved-filters/{filter_id}", headers=auth_header(token_b))
    assert get_b.status_code == 403

    # User B cố tình sửa -> 403 Forbidden
    patch_b = client.patch(
        f"/api/v1/deals/saved-filters/{filter_id}",
        json={"name": "Hacked filter"},
        headers=auth_header(token_b),
    )
    assert patch_b.status_code == 403

    # User B cố tình xóa -> 403 Forbidden
    del_b = client.delete(f"/api/v1/deals/saved-filters/{filter_id}", headers=auth_header(token_b))
    assert del_b.status_code == 403


def test_apply_saved_filter_to_deals_query(client: TestClient, seed_data: dict, filter_setup_data: dict):
    """Test truyền saved_filter_id để tự động áp dụng các tiêu chí đã lưu vào danh sách deals."""
    token = seed_data["tokens"]["sales_director"]

    # Tạo saved filter chỉ lấy stage 'won'
    saved = client.post(
        "/api/v1/deals/saved-filters",
        json={"name": "Deals đã chốt Won", "filter_criteria": {"stages": ["won"]}},
        headers=auth_header(token),
    ).json()

    # Gọi GET /api/v1/deals kèm saved_filter_id
    res = client.get(
        "/api/v1/deals",
        params={"saved_filter_id": saved["id"], "page": 1},
        headers=auth_header(token),
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_items"] >= 1
    for item in data["items"]:
        assert item["stage"] == "won"


def test_post_deal_search_endpoint(client: TestClient, seed_data: dict, filter_setup_data: dict):
    """Test endpoint POST /api/v1/deals/search nhận request body DealFilterParams."""
    token = seed_data["tokens"]["sales_director"]

    payload = {
        "stages": ["proposal", "negotiation"],
        "min_amount": 40000000,
        "max_amount": 90000000,
        "sort_by": "amount",
        "sort_order": "desc",
        "page": 1,
        "page_size": 10,
    }
    res = client.post("/api/v1/deals/search", json=payload, headers=auth_header(token))
    assert res.status_code == 200
    data = res.json()
    assert data["total_items"] == 2
    # Đã sắp xếp desc theo amount: 80M trước, 50M sau
    assert float(data["items"][0]["amount"]) >= float(data["items"][1]["amount"])
