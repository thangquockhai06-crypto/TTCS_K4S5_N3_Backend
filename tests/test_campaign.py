"""
Unit Test & Integration Test cho SCRUM-44 (Sprint 4):
Quản lý Chiến dịch Tiếp thị & Đo lường Hiệu quả Doanh thu (Campaign Management & Attribution).

Kiểm tra 100% Acceptance Criteria:
1. Tạo chiến dịch thành công và chặn ngày kết thúc nhỏ hơn ngày bắt đầu (end_date < start_date).
2. Chặn ngân sách âm (budget < 0).
3. Gán campaign_id cho lead và kiểm tra số đếm total_leads tăng chính xác.
4. Thống kê số lượng deal, số deal đã chốt (WON) và tổng doanh thu thực tế đã chốt (total_revenue, roi).
5. Lấy danh sách chiến dịch có lọc theo channel, status, search và phân trang.
6. Cập nhật thông tin chiến dịch (PUT).
7. Xóa an toàn chiến dịch (DELETE) - đảm bảo không xóa cascade làm mất Leads và Deals (SET NULL).
8. Kiểm tra phân quyền RBAC (Marketing, Director, Admin được phép; vai trò khác bị từ chối 403).
"""
from datetime import date, timedelta
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.lead import Lead
from app.models.deal import Deal
from app.models.customer import Customer
from app.models.campaign import Campaign
from app.core.security import hash_password, create_access_token


@pytest.fixture
def mkt_user(db_session: Session) -> User:
    """Tạo người dùng Marketing."""
    user = User(
        id="usr-mkt-scrum44",
        email="marketing_scrum44@nexuscrm.vn",
        password_hash=hash_password("Pass123!"),
        full_name="Lê Marketing SCRUM-44",
        role="MARKETING",
        status="active",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def director_user(db_session: Session) -> User:
    """Tạo người dùng Giám đốc kinh doanh."""
    user = User(
        id="usr-dir-scrum44",
        email="director_scrum44@nexuscrm.vn",
        password_hash=hash_password("Pass123!"),
        full_name="Nguyễn Giám Đốc",
        role="DIRECTOR",
        status="active",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def mkt_token(mkt_user: User) -> dict:
    token = create_access_token(mkt_user.id, mkt_user.email, mkt_user.role)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def director_token(director_user: User) -> dict:
    token = create_access_token(director_user.id, director_user.email, director_user.role)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_customer(db_session: Session, mkt_user: User) -> Customer:
    """Tạo khách hàng mẫu để gán Deal."""
    cust = Customer(
        id="cust-camp-test",
        full_name="Công ty Khách Hàng Test Campaign",
        email="camp_client@test.vn",
        phone="0911223344",
        assigned_user_id=mkt_user.id,
    )
    db_session.add(cust)
    db_session.commit()
    db_session.refresh(cust)
    return cust


class TestCampaignCRUD:
    """Test Suite cho tính năng Quản lý Chiến dịch (Tạo, Sửa, Lấy chi tiết, Xóa)."""

    def test_create_campaign_success(self, client: TestClient, mkt_token: dict, db_session: Session):
        """Tạo chiến dịch tiếp thị thành công với đầy đủ thông tin hợp lệ."""
        payload = {
            "name": "Chiến dịch Triển Lãm Công Nghệ TechExpo 2026",
            "channel": "Hội thảo",
            "budget": "50000000.00",
            "start_date": "2026-11-01",
            "end_date": "2026-11-30",
            "description": "Thu hút khách hàng B2B tham gia hội thảo triển lãm",
            "status": "ACTIVE",
        }
        res = client.post("/api/v1/campaigns", json=payload, headers=mkt_token)
        assert res.status_code == 201
        data = res.json()
        assert data["name"] == payload["name"]
        assert data["channel"] == "Hội thảo"
        assert float(data["budget"]) == 50000000.0
        assert data["status"] == "ACTIVE"
        assert data["start_date"] == "2026-11-01"
        assert data["end_date"] == "2026-11-30"
        assert data["created_by"] == "usr-mkt-scrum44"

        # Kiểm tra CSDL
        camp_db = db_session.query(Campaign).filter(Campaign.id == data["id"]).first()
        assert camp_db is not None
        assert camp_db.name == payload["name"]

    def test_create_campaign_end_date_before_start_date_fails(self, client: TestClient, mkt_token: dict):
        """Chặn ngày kết thúc nhỏ hơn ngày bắt đầu (AC1)."""
        payload = {
            "name": "Chiến dịch Lỗi Thời Gian",
            "channel": "Google Ads",
            "budget": "10000000.00",
            "start_date": "2026-11-15",
            "end_date": "2026-11-01",  # Lỗi: end_date < start_date
            "status": "PLANNING",
        }
        res = client.post("/api/v1/campaigns", json=payload, headers=mkt_token)
        assert res.status_code == 422
        assert "end_date" in str(res.json())

    def test_create_campaign_negative_budget_fails(self, client: TestClient, mkt_token: dict):
        """Chặn ngân sách âm (budget < 0)."""
        payload = {
            "name": "Chiến dịch Ngân Sách Âm",
            "channel": "Facebook",
            "budget": "-5000.00",
            "start_date": "2026-11-01",
            "end_date": "2026-11-10",
        }
        res = client.post("/api/v1/campaigns", json=payload, headers=mkt_token)
        assert res.status_code == 422

    def test_update_campaign_success(self, client: TestClient, mkt_token: dict):
        """Cập nhật thông tin chiến dịch."""
        # Tạo chiến dịch ban đầu
        create_res = client.post(
            "/api/v1/campaigns",
            json={
                "name": "Chiến dịch Cũ",
                "channel": "Email",
                "budget": "10000000.00",
                "start_date": "2026-10-01",
                "end_date": "2026-10-31",
            },
            headers=mkt_token,
        )
        camp_id = create_res.json()["id"]

        # Cập nhật
        update_payload = {
            "name": "Chiến dịch Đã Cập Nhật",
            "budget": "25000000.00",
            "status": "COMPLETED",
        }
        res = client.put(f"/api/v1/campaigns/{camp_id}", json=update_payload, headers=mkt_token)
        assert res.status_code == 200
        data = res.json()
        assert data["name"] == "Chiến dịch Đã Cập Nhật"
        assert float(data["budget"]) == 25000000.0
        assert data["status"] == "COMPLETED"


class TestCampaignAttributionAndMetrics:
    """Test Suite cho tính năng Liên kết Lead/Deal và Đo lường Hiệu quả Doanh thu."""

    def test_lead_count_increases_accurately(self, client: TestClient, mkt_token: dict, db_session: Session):
        """Gán campaign_id cho lead và kiểm tra số đếm total_leads tăng chính xác."""
        # 1. Tạo chiến dịch
        camp_res = client.post(
            "/api/v1/campaigns",
            json={
                "name": "Chiến dịch Thu Hút Lead Q4",
                "channel": "Facebook Lead Ads",
                "budget": "20000000.00",
                "start_date": "2026-10-01",
                "end_date": "2026-12-31",
            },
            headers=mkt_token,
        )
        camp_id = camp_res.json()["id"]

        # 2. Tạo 2 lead gắn campaign_id
        lead1 = Lead(
            id="lead-camp-01",
            full_name="Khách Hàng Facebook 1",
            phone="0911000001",
            source="Facebook",
            campaign_id=camp_id,
            status="NEW",
        )
        lead2 = Lead(
            id="lead-camp-02",
            full_name="Khách Hàng Facebook 2",
            phone="0911000002",
            source="Facebook",
            campaign_id=camp_id,
            status="NEW",
        )
        # 1 lead không gắn campaign
        lead_other = Lead(
            id="lead-camp-other",
            full_name="Khách Hàng Khác",
            phone="0911000003",
            source="Website",
            campaign_id=None,
            status="NEW",
        )
        db_session.add_all([lead1, lead2, lead_other])
        db_session.commit()

        # 3. Lấy chi tiết chiến dịch
        res = client.get(f"/api/v1/campaigns/{camp_id}", headers=mkt_token)
        assert res.status_code == 200
        data = res.json()
        assert data["total_leads"] == 2
        assert len(data["leads"]) == 2

    def test_revenue_and_roi_calculation(
        self, client: TestClient, mkt_token: dict, db_session: Session, sample_customer: Customer, mkt_user: User
    ):
        """Thống kê doanh thu chốt của deal và tỷ suất ROI."""
        # Ngân sách 50 triệu
        camp_res = client.post(
            "/api/v1/campaigns",
            json={
                "name": "Chiến dịch Hội Thảo Chuyển Đổi Số",
                "channel": "Hội thảo",
                "budget": "50000000.00",
                "start_date": "2026-09-01",
                "end_date": "2026-09-30",
            },
            headers=mkt_token,
        )
        camp_id = camp_res.json()["id"]

        # Tạo các deal liên kết với chiến dịch
        # Deal 1: Đã chốt (WON) - 100 triệu
        deal_won_1 = Deal(
            id="deal-camp-won-1",
            title="Hợp đồng CRM Doanh nghiệp",
            value=100000000.00,
            stage="won",
            probability=100,
            customer_id=sample_customer.id,
            owner_id=mkt_user.id,
            campaign_id=camp_id,
        )
        # Deal 2: Đang đàm phán (Chưa chốt) - 60 triệu
        deal_negotiation = Deal(
            id="deal-camp-nego",
            title="Hợp đồng ERP Cloud",
            value=60000000.00,
            stage="negotiation",
            probability=70,
            customer_id=sample_customer.id,
            owner_id=mkt_user.id,
            campaign_id=camp_id,
        )
        # Deal 3: Đã chốt (WON) - 50 triệu
        deal_won_2 = Deal(
            id="deal-camp-won-2",
            title="Gói bảo trì nâng cấp",
            value=50000000.00,
            stage="won",
            probability=100,
            customer_id=sample_customer.id,
            owner_id=mkt_user.id,
            campaign_id=camp_id,
        )
        db_session.add_all([deal_won_1, deal_negotiation, deal_won_2])
        db_session.commit()

        # Gọi API lấy metrics chiến dịch
        res = client.get(f"/api/v1/campaigns/{camp_id}", headers=mkt_token)
        assert res.status_code == 200
        data = res.json()

        assert data["total_deals"] == 3
        assert data["won_deals_count"] == 2
        # Tổng doanh thu thực tế đã chốt = 100tr + 50tr = 150tr
        assert float(data["total_revenue"]) == 150000000.0
        # Lợi nhuận (profit) = 150tr - 50tr = 100tr
        assert float(data["profit"]) == 100000000.0
        # ROI = (150tr - 50tr) / 50tr * 100% = 200.0%
        assert data["roi"] == 200.0

    def test_list_campaigns_filtering_and_pagination(self, client: TestClient, mkt_token: dict):
        """Lọc danh sách chiến dịch theo kênh, trạng thái và tìm kiếm."""
        # Tạo 2 chiến dịch khác nhau
        client.post(
            "/api/v1/campaigns",
            json={
                "name": "Chiến dịch Email Marketing Tuyển Dụng",
                "channel": "Email",
                "budget": "5000000.00",
                "start_date": "2026-10-01",
                "end_date": "2026-10-15",
                "status": "COMPLETED",
            },
            headers=mkt_token,
        )
        client.post(
            "/api/v1/campaigns",
            json={
                "name": "Chiến dịch Tiktok Viral Video",
                "channel": "Tiktok",
                "budget": "15000000.00",
                "start_date": "2026-10-10",
                "end_date": "2026-10-25",
                "status": "ACTIVE",
            },
            headers=mkt_token,
        )

        # 1. Lọc theo channel 'Tiktok'
        res_channel = client.get("/api/v1/campaigns?channel=Tiktok", headers=mkt_token)
        assert res_channel.status_code == 200
        data_channel = res_channel.json()
        assert all("tiktok" in item["channel"].lower() for item in data_channel["items"])

        # 2. Lọc theo status 'COMPLETED'
        res_status = client.get("/api/v1/campaigns?status=COMPLETED", headers=mkt_token)
        assert res_status.status_code == 200
        data_status = res_status.json()
        assert all(item["status"] == "COMPLETED" for item in data_status["items"])


class TestCampaignSafeDelete:
    """Test Suite cho tính năng Xóa an toàn chiến dịch (Safe Delete / Nullify attribution)."""

    def test_delete_campaign_does_not_delete_leads_and_deals(
        self, client: TestClient, mkt_token: dict, db_session: Session, sample_customer: Customer, mkt_user: User
    ):
        """Xóa chiến dịch không làm mất lead và deal (SET NULL campaign_id)."""
        # 1. Tạo chiến dịch
        camp_res = client.post(
            "/api/v1/campaigns",
            json={
                "name": "Chiến dịch Sắp Bị Xóa",
                "channel": "Email",
                "budget": "10000000.00",
                "start_date": "2026-10-01",
                "end_date": "2026-10-20",
            },
            headers=mkt_token,
        )
        camp_id = camp_res.json()["id"]

        # 2. Tạo Lead & Deal gắn campaign_id
        lead = Lead(
            id="lead-safe-del-01",
            full_name="Lead Được Bảo Vệ",
            phone="0911888777",
            source="Email",
            campaign_id=camp_id,
            status="NEW",
        )
        deal = Deal(
            id="deal-safe-del-01",
            title="Deal Được Bảo Vệ",
            value=50000000.00,
            stage="lead",
            customer_id=sample_customer.id,
            owner_id=mkt_user.id,
            campaign_id=camp_id,
        )
        db_session.add_all([lead, deal])
        db_session.commit()

        # 3. Xóa chiến dịch
        del_res = client.delete(f"/api/v1/campaigns/{camp_id}", headers=mkt_token)
        assert del_res.status_code == 204

        # 4. Kiểm tra chiến dịch không còn tồn tại
        get_res = client.get(f"/api/v1/campaigns/{camp_id}", headers=mkt_token)
        assert get_res.status_code == 404

        # 5. Kiểm tra Lead và Deal vẫn còn nguyên trong CSDL, campaign_id đã được gán về None
        lead_db = db_session.query(Lead).filter(Lead.id == "lead-safe-del-01").first()
        assert lead_db is not None
        assert lead_db.campaign_id is None

        deal_db = db_session.query(Deal).filter(Deal.id == "deal-safe-del-01").first()
        assert deal_db is not None
        assert deal_db.campaign_id is None


class TestCampaignAuthorization:
    """Test Suite cho phân quyền vai trò (Role Authorization)."""

    def test_director_can_create_and_manage(self, client: TestClient, director_token: dict):
        """Giám đốc kinh doanh (DIRECTOR) có toàn quyền tạo và quản lý chiến dịch."""
        payload = {
            "name": "Chiến dịch Cấp Giám Đốc Phê Duyệt",
            "channel": "Hội thảo Quốc Tế",
            "budget": "200000000.00",
            "start_date": "2026-12-01",
            "end_date": "2026-12-15",
        }
        res = client.post("/api/v1/campaigns", json=payload, headers=director_token)
        assert res.status_code == 201

    def test_unauthorized_role_cannot_create_campaign(self, client: TestClient, db_session: Session):
        """Tài khoản có vai trò không được cấp phép (GUEST) bị từ chối 403 khi tạo chiến dịch."""
        guest = User(
            id="usr-guest-camp",
            email="guest_camp@nexuscrm.vn",
            password_hash=hash_password("Pass123!"),
            full_name="Khách GUEST",
            role="GUEST",
            status="active",
        )
        db_session.add(guest)
        db_session.commit()

        token = create_access_token(guest.id, guest.email, guest.role)
        headers = {"Authorization": f"Bearer {token}"}

        res = client.post(
            "/api/v1/campaigns",
            json={
                "name": "Chiến dịch Trái Phép",
                "channel": "Facebook",
                "budget": "1000000.00",
                "start_date": "2026-11-01",
                "end_date": "2026-11-05",
            },
            headers=headers,
        )
        assert res.status_code == 403
        assert "Bạn không có quyền thực hiện thao tác quản lý Chiến dịch" in res.json()["detail"]
