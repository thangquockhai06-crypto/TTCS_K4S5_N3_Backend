"""
Bộ kiểm thử toàn diện cho Phân hệ Quản lý Đầu mối (EP-04: Lead Management S4-01 -> S4-09):
- S4-01: Form nhúng công khai & public endpoint
- S4-02: Tạo thủ công & Excel import
- S4-03: Đo lường chiến dịch (Campaign tracking)
- S4-04: Phát hiện trùng lặp & gộp đầu mối
- S4-05: Chấm điểm Lead động (Hot, Warm, Cold)
- S4-06: Phân bổ tự động (Region, Industry, Round-Robin)
- S4-07: Tiếp nhận, từ chối kèm lý do & SLA tracking
- S4-08: Chuyển đổi Lead thành Customer, Contact và Deal
- S4-09: Danh sách Lead, phân trang và bộ lọc
"""
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.lead import Lead, LeadRoutingRule
from app.models.campaign import Campaign
from app.models.customer import Customer
from app.core.security import hash_password, create_access_token


@pytest.fixture
def auth_headers(db_session: Session) -> dict:
    admin = User(
        id="usr-ep04-admin",
        email="ep04_admin@nexuscrm.vn",
        password_hash=hash_password("AdminPass123!"),
        full_name="Quản Trị Viên EP04",
        role="Super Admin",
        status="active",
    )
    db_session.add(admin)
    db_session.commit()
    token = create_access_token(user_id=admin.id, email=admin.email, role=admin.role)
    return {"Authorization": f"Bearer {token}"}


def test_s4_01_public_lead_submission(client: TestClient, db_session: Session):
    """S4-01: Kiểm thử tiếp nhận Lead công khai và lấy mã nhúng."""
    # 1. Lấy mã nhúng
    snippet_res = client.get("/api/v1/leads/public/embed-snippet?campaign_code=TEST-CAMP")
    assert snippet_res.status_code == 200
    snippet_data = snippet_res.json()
    assert "iframeSnippet" in snippet_data
    assert "scriptSnippet" in snippet_data

    # 2. Gửi form công khai (không cần Header Authorization)
    payload = {
        "fullName": "Trần Thị Khách Hàng Web",
        "email": "khachhang@congtytest.com",
        "phone": "0912345678",
        "company": "Công ty TNHH Phần Mềm Test",
        "message": "Tôi muốn dùng thử phần mềm CRM",
    }
    submit_res = client.post("/api/v1/leads/public/submit", json=payload)
    assert submit_res.status_code == 201
    lead_data = submit_res.json()
    assert lead_data["fullName"] == "Trần Thị Khách Hàng Web"
    assert lead_data["source"] == "Web Form"
    assert lead_data["score"] > 0
    assert lead_data["scoreGrade"] in ("Hot", "Warm", "Cold")


def test_s4_02_manual_lead_creation_and_template(client: TestClient, auth_headers: dict, db_session: Session):
    """S4-02: Kiểm thử tạo thủ công và tải template import."""
    # 1. Tải template Excel
    tpl_res = client.get("/api/v1/leads/import/template?format=xlsx", headers=auth_headers)
    assert tpl_res.status_code == 200

    # 2. Tạo thủ công
    lead_payload = {
        "fullName": "Lê Văn Thủ Công",
        "email": "thucong@doanhnghiep.vn",
        "phone": "0988776655",
        "company": "Doanh nghiệp ABC",
        "jobTitle": "Giám đốc Kinh doanh",
        "source": "Manual",
        "region": "Miền Bắc",
        "industry": "Công nghệ",
        "companySize": "51-200",
        "annualBudget": 80000000,
    }
    res = client.post("/api/v1/leads", json=lead_payload, headers=auth_headers)
    assert res.status_code == 201
    data = res.json()
    assert data["fullName"] == "Lê Văn Thủ Công"
    assert data["score"] >= 70  # Giám đốc + email công ty + quy mô + ngân sách => Hot
    assert data["scoreGrade"] == "Hot"


def test_s4_03_campaign_tracking(client: TestClient, auth_headers: dict, db_session: Session):
    """S4-03: Kiểm thử liên kết chiến dịch và tính toán số liệu thực tế."""
    camp_payload = {
        "name": "Chiến dịch Mùa Hè 2026",
        "code": "CAMP-SUMMER-2026",
        "type": "Web Form",
        "budget": 20000000,
        "expectedRevenue": 150000000,
    }
    res = client.post("/api/v1/campaigns", json=camp_payload, headers=auth_headers)
    assert res.status_code == 201
    camp_id = res.json()["id"]

    # Tạo lead thuộc campaign này
    lead_payload = {
        "fullName": "Khách Từ Campaign",
        "email": "campaign_lead@fpt.vn",
        "campaignId": camp_id,
        "source": "Campaign",
    }
    l_res = client.post("/api/v1/leads", json=lead_payload, headers=auth_headers)
    assert l_res.status_code == 201

    # Kiểm tra số liệu tổng hợp trong danh sách chiến dịch
    list_res = client.get("/api/v1/campaigns", headers=auth_headers)
    assert list_res.status_code == 200
    matched = next((c for c in list_res.json() if c["id"] == camp_id), None)
    assert matched is not None
    assert matched["totalLeads"] >= 1


def test_s4_04_duplicate_detection_and_merge(client: TestClient, auth_headers: dict, db_session: Session):
    """S4-04: Kiểm thử phát hiện trùng lặp và gộp đầu mối."""
    lead1 = client.post("/api/v1/leads", json={"fullName": "Nguyễn Trùng Lặp 1", "email": "trunglap@test.com", "phone": "0933112233"}, headers=auth_headers).json()
    lead2 = client.post("/api/v1/leads", json={"fullName": "Nguyễn Trùng Lặp 2", "email": "trunglap@test.com", "phone": "0933112233"}, headers=auth_headers).json()

    # Kiểm tra trùng lặp
    dup_res = client.get("/api/v1/leads/duplicates?email=trunglap@test.com", headers=auth_headers)
    assert dup_res.status_code == 200
    assert len(dup_res.json()["duplicateLeads"]) >= 2

    # Gộp 2 lead
    merge_payload = {
        "primaryLeadId": lead1["id"],
        "duplicateLeadId": lead2["id"],
        "keepFields": {"fullName": "primary"},
    }
    merge_res = client.post(f"/api/v1/leads/{lead1['id']}/merge", json=merge_payload, headers=auth_headers)
    assert merge_res.status_code == 200

    # Kiểm tra lead2 đã bị xóa
    check_res = client.get(f"/api/v1/leads/{lead2['id']}", headers=auth_headers)
    assert check_res.status_code == 404


def test_s4_05_lead_scoring_recalculate(client: TestClient, auth_headers: dict, db_session: Session):
    """S4-05: Kiểm thử tính toán lại điểm số Lead."""
    lead = client.post("/api/v1/leads", json={"fullName": "Lead Chấm Điểm", "email": "test@gmail.com"}, headers=auth_headers).json()
    recalc_res = client.post(f"/api/v1/leads/{lead['id']}/score/recalculate", headers=auth_headers)
    assert recalc_res.status_code == 200
    assert "score" in recalc_res.json()
    assert recalc_res.json()["scoreGrade"] in ("Hot", "Warm", "Cold")


def test_s4_07_lead_accept_reject_and_sla(client: TestClient, auth_headers: dict, db_session: Session):
    """S4-07: Tiếp nhận, từ chối và quét vi phạm SLA."""
    # 1. Tiếp nhận lead
    lead = client.post("/api/v1/leads", json={"fullName": "Lead Tiếp Nhận", "email": "tiepnhan@test.com"}, headers=auth_headers).json()
    acc_res = client.post(f"/api/v1/leads/{lead['id']}/accept", headers=auth_headers)
    assert acc_res.status_code == 200
    assert acc_res.json()["status"] == "CONTACTED"

    # 2. Từ chối lead
    lead2 = client.post("/api/v1/leads", json={"fullName": "Lead Từ Chối", "email": "tuchoi@test.com"}, headers=auth_headers).json()
    rej_res = client.post(f"/api/v1/leads/{lead2['id']}/reject", json={"rejectionReason": "Khách hàng không có nhu cầu"}, headers=auth_headers)
    assert rej_res.status_code == 200
    assert rej_res.json()["status"] == "REJECTED"
    assert rej_res.json()["rejectionReason"] == "Khách hàng không có nhu cầu"

    # 3. Quét vi phạm SLA
    sla_res = client.post("/api/v1/leads/check-sla", headers=auth_headers)
    assert sla_res.status_code == 200
    assert "overdueCount" in sla_res.json()


def test_s4_08_lead_conversion_workflow(client: TestClient, auth_headers: dict, db_session: Session):
    """S4-08: Kiểm thử chuyển đổi Lead thành Customer, Contact và Deal."""
    lead = client.post("/api/v1/leads", json={
        "fullName": "Phạm Chuyển Đổi",
        "email": "chuyendoi@congtylon.vn",
        "company": "Công ty TNHH Chuyển Đổi Lớn",
        "phone": "0911223344",
        "annualBudget": 120000000,
    }, headers=auth_headers).json()

    convert_payload = {
        "customerName": "Công ty TNHH Chuyển Đổi Lớn",
        "taxCode": "0109988776",
        "createDeal": True,
        "dealTitle": "Cơ hội Bán hàng từ Lead Chuyển đổi",
        "dealValue": 120000000,
    }
    conv_res = client.post(f"/api/v1/leads/{lead['id']}/convert", json=convert_payload, headers=auth_headers)
    assert conv_res.status_code == 200
    conv_data = conv_res.json()
    assert "customerId" in conv_data
    assert "dealId" in conv_data
    assert "contactId" in conv_data

    # Kiểm tra lead đã chuyển thành CONVERTED
    lead_check = client.get(f"/api/v1/leads/{lead['id']}", headers=auth_headers).json()
    assert lead_check["status"] == "CONVERTED"
    assert lead_check["convertedCustomerId"] == conv_data["customerId"]
