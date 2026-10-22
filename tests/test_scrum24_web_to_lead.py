"""
Unit & Integration Tests for SCRUM-24 (Sprint 4 / Story S4-01):
Thu thập Lead từ Biểu mẫu nhúng trên Website (Web-to-Lead Form).

Kiểm thử:
1. Sinh mã nhúng cho biểu mẫu (Embed Code Generation): POST, GET, PUT, DELETE, embed-code
2. Thu thập đầy đủ trường thông tin khách hàng tiềm năng & Validation (Họ tên, Email, Phone chuẩn VN 10 số)
3. Chống spam Honeypot: Bot gửi honeypot trả về 200 giả lập nhưng KHÔNG lưu vào DB
4. IP Rate Limiting: Giới hạn tối đa 5 lượt submit / phút / IP -> HTTP 429
5. Tạo Lead tự động với status='NEW' và source=form.lead_source
6. Public API không yêu cầu JWT Token, hỗ trợ CORS
7. Render HTML form và script form-loader.js
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.lead import Lead
from app.models.web_form import WebForm
from app.services.web_form_service import ip_rate_limiter


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset bộ đếm IP rate limit trước mỗi test case."""
    ip_rate_limiter.reset()
    yield
    ip_rate_limiter.reset()


# ==============================================================================
# 1. Quản lý Biểu mẫu nhúng (Marketing / Admin API)
# ==============================================================================

def test_create_web_form(client: TestClient, seed_data: dict):
    """Marketing tạo biểu mẫu nhúng website mới thành công."""
    token = seed_data["tokens"]["sales_director"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "name": "Form Đăng ký dùng thử CRM 2026",
        "lead_source": "Website Landing Page",
        "is_active": True,
    }

    response = client.post("/api/v1/forms", json=payload, headers=headers)
    assert response.status_code == 201

    data = response.json()
    assert data["name"] == payload["name"]
    assert data["lead_source"] == payload["lead_source"]
    assert data["is_active"] is True
    assert data["form_key"].startswith("wf_")
    assert "<script" in data["embed_code"]
    assert data["form_key"] in data["embed_code"]
    assert "<iframe" in data["iframe_code"]


def test_list_and_get_web_form(client: TestClient, seed_data: dict):
    """Liệt kê danh sách và xem chi tiết biểu mẫu kèm mã nhúng."""
    token = seed_data["tokens"]["emp_a"]
    headers = {"Authorization": f"Bearer {token}"}

    # Tạo form
    create_res = client.post(
        "/api/v1/forms",
        json={"name": "Form Tư Vấn Khách Hàng Doanh Nghiệp", "lead_source": "Khảo sát Online"},
        headers=headers,
    )
    assert create_res.status_code == 201
    form_id = create_res.json()["id"]

    # Danh sách
    list_res = client.get("/api/v1/forms", headers=headers)
    assert list_res.status_code == 200
    forms = list_res.json()
    assert any(f["id"] == form_id for f in forms)

    # Chi tiết
    detail_res = client.get(f"/api/v1/forms/{form_id}", headers=headers)
    assert detail_res.status_code == 200
    assert detail_res.json()["name"] == "Form Tư Vấn Khách Hàng Doanh Nghiệp"
    assert detail_res.json()["total_leads"] == 0

    # Lấy riêng embed-code
    embed_res = client.get(f"/api/v1/forms/{form_id}/embed-code", headers=headers)
    assert embed_res.status_code == 200
    embed_data = embed_res.json()
    assert embed_data["form_id"] == form_id
    assert "<div id=\"crm-lead-form\"" in embed_data["embed_code"]
    assert "<iframe" in embed_data["iframe_code"]
    assert "/api/v1/public/forms/" in embed_data["direct_submit_url"]


def test_update_and_delete_web_form(client: TestClient, seed_data: dict):
    """Cập nhật thông tin biểu mẫu và xóa biểu mẫu."""
    token = seed_data["tokens"]["sales_director"]
    headers = {"Authorization": f"Bearer {token}"}

    create_res = client.post(
        "/api/v1/forms",
        json={"name": "Form Tạm Thời", "lead_source": "Test"},
        headers=headers,
    )
    form_id = create_res.json()["id"]

    # Cập nhật
    update_res = client.put(
        f"/api/v1/forms/{form_id}",
        json={"name": "Form Đã Cập Nhật", "is_active": False},
        headers=headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["name"] == "Form Đã Cập Nhật"
    assert update_res.json()["is_active"] is False

    # Xóa
    delete_res = client.delete(f"/api/v1/forms/{form_id}", headers=headers)
    assert delete_res.status_code == 204

    # Xem lại -> 404
    get_res = client.get(f"/api/v1/forms/{form_id}", headers=headers)
    assert get_res.status_code == 404


# ==============================================================================
# 2. Public API Thu thập Lead từ Website (Web-to-Lead)
# ==============================================================================

def test_public_lead_submission_success(client: TestClient, seed_data: dict, db_session: Session):
    """Khách truy cập submit form công khai -> Tạo Lead thành công ở trạng thái 'NEW'."""
    token = seed_data["tokens"]["sales_director"]
    create_res = client.post(
        "/api/v1/forms",
        json={"name": "Form Đăng Ký Tư Vấn Bất Động Sản", "lead_source": "Landing Page BĐS"},
        headers={"Authorization": f"Bearer {token}"},
    )
    form_key = create_res.json()["form_key"]
    form_id = create_res.json()["id"]

    lead_payload = {
        "full_name": "Nguyễn Hoàng Nam",
        "email": "hoangnam.bds@gmail.com",
        "phone": "0987654321",
        "company": "Công ty Cổ phần Địa ốc Vàng",
        "interest_need": "Quan tâm gói CRM quản lý 50 môi giới bất động sản.",
    }

    # Public submit không cần Bearer token
    res = client.post(
        f"/api/v1/public/forms/{form_key}/submit",
        json=lead_payload,
        headers={"X-Forwarded-For": "113.190.23.45"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["lead_id"] is not None

    # Kiểm tra bản ghi trong DB
    lead = db_session.query(Lead).filter(Lead.id == data["lead_id"]).first()
    assert lead is not None
    assert lead.full_name == lead_payload["full_name"]
    assert lead.email == lead_payload["email"]
    assert lead.phone == lead_payload["phone"]
    assert lead.company == lead_payload["company"]
    assert lead.interest_need == lead_payload["interest_need"]
    assert lead.status == "NEW"
    assert lead.source == "Landing Page BĐS"
    assert lead.form_id == form_id
    assert lead.client_ip == "113.190.23.45"


def test_public_lead_phone_validation(client: TestClient, seed_data: dict):
    """Xác thực số điện thoại chuẩn di động Việt Nam (10 số, đầu số 03, 05, 07, 08, 09)."""
    token = seed_data["tokens"]["sales_director"]
    create_res = client.post(
        "/api/v1/forms",
        json={"name": "Form Kiểm Tra SĐT", "lead_source": "Website"},
        headers={"Authorization": f"Bearer {token}"},
    )
    form_key = create_res.json()["form_key"]

    invalid_phones = [
        "123456",            # Quá ngắn
        "0123456789",        # Đầu số 01 đã ngừng
        "09876543210",       # 11 số (thừa số)
        "0243823456",        # Đầu số cố định (Hà Nội), không phải di động
        "abcd123456",        # Chứa ký tự chữ
        "+1987654321",       # Đầu số quốc tế Mỹ, không phải Việt Nam
    ]

    for p in invalid_phones:
        res = client.post(
            f"/api/v1/public/forms/{form_key}/submit",
            json={
                "full_name": "Test Tester",
                "email": "test@example.com",
                "phone": p,
            },
        )
        assert res.status_code == 422, f"Số điện thoại '{p}' đáng lẽ phải bị từ chối"

    # Các đầu số di động hợp lệ (kể cả đầu số quốc tế +84 được chuẩn hóa)
    valid_phones = [
        "0326123456",     # Viettel 03
        "0568123456",     # Vietnamobile 05
        "0703123456",     # Mobifone 07
        "0834123456",     # Vinaphone 08
        "0912345678",     # Vinaphone 09
        "+84912345678",   # Chuẩn quốc tế +84 tự động chuyển về 0912345678
    ]

    for i, vp in enumerate(valid_phones):
        res = client.post(
            f"/api/v1/public/forms/{form_key}/submit",
            json={
                "full_name": f"Hợp Lệ {i}",
                "email": f"valid_{i}@example.com",
                "phone": vp,
            },
            headers={"X-Forwarded-For": f"10.0.0.{i+1}"},
        )
        assert res.status_code == 200, f"Số điện thoại '{vp}' hợp lệ nhưng bị từ chối"


# ==============================================================================
# 3. Chống Spam: Honeypot Protection
# ==============================================================================

def test_honeypot_spam_protection(client: TestClient, seed_data: dict, db_session: Session):
    """Bot spam tự động điền trường ẩn honeypot (_hp hoặc website_hp) -> 200 giả lập, không lưu DB."""
    token = seed_data["tokens"]["sales_director"]
    create_res = client.post(
        "/api/v1/forms",
        json={"name": "Form Honeypot Test", "lead_source": "Website Honeypot"},
        headers={"Authorization": f"Bearer {token}"},
    )
    form_key = create_res.json()["form_key"]

    initial_lead_count = db_session.query(Lead).count()

    # Bot điền _hp
    bot_res_1 = client.post(
        f"/api/v1/public/forms/{form_key}/submit",
        json={
            "full_name": "Spam Bot Alpha",
            "email": "spambot@spam.com",
            "phone": "0987654321",
            "_hp": "http://spam-link.ru",
        },
        headers={"X-Forwarded-For": "185.220.101.5"},
    )
    assert bot_res_1.status_code == 200
    assert bot_res_1.json()["success"] is True
    assert bot_res_1.json()["lead_id"] is None

    # Bot điền website_hp
    bot_res_2 = client.post(
        f"/api/v1/public/forms/{form_key}/submit",
        json={
            "full_name": "Spam Bot Beta",
            "email": "spambot2@spam.com",
            "phone": "0987654321",
            "website_hp": "http://spam-crypto.io",
        },
        headers={"X-Forwarded-For": "185.220.101.6"},
    )
    assert bot_res_2.status_code == 200
    assert bot_res_2.json()["success"] is True
    assert bot_res_2.json()["lead_id"] is None

    # DB không được tăng thêm lead nào
    current_lead_count = db_session.query(Lead).count()
    assert current_lead_count == initial_lead_count


# ==============================================================================
# 4. Giới hạn tần suất: IP Rate Limiting (5 req / min)
# ==============================================================================

def test_ip_rate_limiting_enforcement(client: TestClient, seed_data: dict):
    """Mỗi địa chỉ IP chỉ được submit tối đa 5 lượt / phút. Lượt thứ 6 trả về HTTP 429."""
    token = seed_data["tokens"]["sales_director"]
    create_res = client.post(
        "/api/v1/forms",
        json={"name": "Form Test Rate Limit", "lead_source": "Website"},
        headers={"Authorization": f"Bearer {token}"},
    )
    form_key = create_res.json()["form_key"]

    client_ip = "203.113.150.10"

    # 5 lượt gửi đầu tiên từ cùng 1 IP -> Thành công
    for i in range(5):
        res = client.post(
            f"/api/v1/public/forms/{form_key}/submit",
            json={
                "full_name": f"Khách Hàng Thứ {i+1}",
                "email": f"customer_{i+1}@testrate.com",
                "phone": "0912345678",
            },
            headers={"X-Forwarded-For": client_ip},
        )
        assert res.status_code == 200

    # Lượt thứ 6 từ cùng IP -> Bị chặn với HTTP 429 Too Many Requests
    blocked_res = client.post(
        f"/api/v1/public/forms/{form_key}/submit",
        json={
            "full_name": "Khách Hàng Bị Chặn",
            "email": "blocked@testrate.com",
            "phone": "0912345678",
        },
        headers={"X-Forwarded-For": client_ip},
    )
    assert blocked_res.status_code == 429
    assert "Retry-After" in blocked_res.headers
    assert "Quá nhiều yêu cầu" in blocked_res.json()["detail"]

    # Địa chỉ IP khác vẫn gửi bình thường (không bị ảnh hưởng)
    other_ip_res = client.post(
        f"/api/v1/public/forms/{form_key}/submit",
        json={
            "full_name": "Khách Hàng Khác IP",
            "email": "other_ip@testrate.com",
            "phone": "0912345678",
        },
        headers={"X-Forwarded-For": "203.113.150.99"},
    )
    assert other_ip_res.status_code == 200


# ==============================================================================
# 5. Kiểm tra Biểu mẫu ngưng hoạt động hoặc không tồn tại
# ==============================================================================

def test_submit_to_inactive_or_nonexistent_form(client: TestClient, seed_data: dict):
    """Gửi tới form không hoạt động -> 400 Bad Request; form không tồn tại -> 404 Not Found."""
    token = seed_data["tokens"]["sales_director"]
    create_res = client.post(
        "/api/v1/forms",
        json={"name": "Form Đã Đóng", "lead_source": "Website", "is_active": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    inactive_form_key = create_res.json()["form_key"]

    # Submit tới form bị đóng
    res_inactive = client.post(
        f"/api/v1/public/forms/{inactive_form_key}/submit",
        json={"full_name": "Test Name", "email": "test@test.com", "phone": "0912345678"},
    )
    assert res_inactive.status_code == 400
    assert "ngừng tiếp nhận" in res_inactive.json()["detail"]

    # Submit tới form_key bừa bãi
    res_not_found = client.post(
        "/api/v1/public/forms/wf_non_existent_key_12345/submit",
        json={"full_name": "Test Name", "email": "test@test.com", "phone": "0912345678"},
    )
    assert res_not_found.status_code == 404


# ==============================================================================
# 6. Quản lý Danh sách Lead & Cập nhật trạng thái (EP-04)
# ==============================================================================

def test_leads_management_and_status_update(client: TestClient, seed_data: dict):
    """Marketing/Sales xem danh sách lead, lọc trạng thái và cập nhật trạng thái xử lý."""
    token = seed_data["tokens"]["sales_director"]
    headers = {"Authorization": f"Bearer {token}"}

    # Tạo form và submit 1 lead
    form_res = client.post(
        "/api/v1/forms",
        json={"name": "Form Tuyển Dụng & Đối Tác", "lead_source": "Đối Tác Kênh"},
        headers=headers,
    )
    form_key = form_res.json()["form_key"]
    form_id = form_res.json()["id"]

    submit_res = client.post(
        f"/api/v1/public/forms/{form_key}/submit",
        json={
            "full_name": "Đặng Thị Mai",
            "email": "maidx@partner.vn",
            "phone": "0933123456",
            "company": "Công ty Đối Tác Mai Lan",
            "interest_need": "Hợp tác phân phối sản phẩm CRM",
        },
        headers={"X-Forwarded-For": "14.232.100.2"},
    )
    lead_id = submit_res.json()["lead_id"]

    # Xem danh sách leads cho form cụ thể
    form_leads_res = client.get(f"/api/v1/forms/{form_id}/leads", headers=headers)
    assert form_leads_res.status_code == 200
    leads = form_leads_res.json()
    assert len(leads) >= 1
    assert any(l["id"] == lead_id for l in leads)

    # Xem danh sách leads tổng thể với bộ lọc
    leads_list_res = client.get(f"/api/v1/leads?status=NEW&form_id={form_id}", headers=headers)
    assert leads_list_res.status_code == 200
    assert leads_list_res.json()["total"] >= 1
    target_lead = next(l for l in leads_list_res.json()["items"] if l["id"] == lead_id)
    assert target_lead["status"] == "NEW"

    # Cập nhật trạng thái xử lý: NEW -> CONTACTED
    status_update_res = client.put(
        f"/api/v1/leads/{lead_id}/status",
        json={"status": "CONTACTED"},
        headers=headers,
    )
    assert status_update_res.status_code == 200
    assert status_update_res.json()["status"] == "CONTACTED"

    # Thử cập nhật trạng thái không hợp lệ -> 400
    invalid_status_res = client.put(
        f"/api/v1/leads/{lead_id}/status",
        json={"status": "INVALID_STATUS"},
        headers=headers,
    )
    assert invalid_status_res.status_code == 400


# ==============================================================================
# 7. Public Static Endpoints (HTML Render & JS Loader) & CORS
# ==============================================================================

def test_public_html_render_and_js_loader(client: TestClient, seed_data: dict):
    """Kiểm tra render giao diện HTML iframe và script loader.js."""
    token = seed_data["tokens"]["sales_director"]
    form_res = client.post(
        "/api/v1/forms",
        json={"name": "Form Nhúng Website Độc Lập", "lead_source": "Trang Chủ"},
        headers={"Authorization": f"Bearer {token}"},
    )
    form_key = form_res.json()["form_key"]

    # 1. Render giao diện HTML độc lập
    render_res = client.get(f"/api/v1/public/forms/{form_key}/render")
    assert render_res.status_code == 200
    assert "text/html" in render_res.headers["content-type"]
    assert "Form Nhúng Website Độc Lập" in render_res.text
    assert 'name="_hp"' in render_res.text
    assert 'name="website_hp"' in render_res.text
    assert 'id="nexus-lead-form"' in render_res.text

    # 2. Tải form-loader.js tĩnh
    loader_res = client.get("/static/form-loader.js")
    assert loader_res.status_code == 200
    assert "javascript" in loader_res.headers["content-type"]
    assert "crm-lead-form" in loader_res.text

    # 3. CORS Preflight OPTIONS request
    options_res = client.options(f"/api/v1/public/forms/{form_key}/submit")
    assert options_res.status_code == 204
    assert options_res.headers.get("access-control-allow-origin") == "*"
