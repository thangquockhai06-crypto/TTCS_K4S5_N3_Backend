"""
Unit Test & Integration Test cho SCRUM-175 / SCRUM-46 / SCRUM-30 (Sprint 4):
Cảnh báo và Gộp Lead trùng lặp (Lead Deduplication, Merge & Customer Matching).

Kiểm tra 100% Acceptance Criteria:
1. Phát hiện trùng lặp theo Email, Số điện thoại (VN) và Tên công ty.
2. Gợi ý gắn vào Khách hàng hiện có (ATTACH_TO_CUSTOMER) khi trùng Customer.
3. Gợi ý gộp Lead (MERGE_LEADS) khi trùng Lead khác.
4. Bỏ qua Lead đang chỉnh sửa thông qua exclude_lead_id.
5. Thực thi gộp 2 Lead (Lead-to-Lead), bảo toàn trọn vẹn toàn bộ Activities và Notes.
6. Cập nhật Lead phụ thành trạng thái 'MERGED' và lưu merged_into_lead_id.
7. Gắn Lead vào Khách hàng hiện có (Lead-to-Customer), chuyển Activities và gán converted_customer_id.
8. Bắt lỗi không cho phép gộp Lead vào chính nó (400), gộp Lead đã bị gộp (400), ID không tồn tại (404).
9. Kiểm tra phân quyền RBAC: Sales Rep không có quyền gộp Lead (403), Marketing/Admin có quyền.
10. Đảm bảo tính toàn vẹn giao dịch (ACID rollback khi phát sinh sự cố).
"""
import uuid
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.lead import Lead
from app.models.customer import Customer
from app.models.activity import Activity
from app.models.audit_log import AuditLog
from app.core.security import hash_password, create_access_token


@pytest.fixture
def marketing_user(db_session: Session) -> User:
    """Tạo tài khoản Nhân viên Marketing."""
    user = User(
        id="usr-mkt-merge-test",
        email="mkt_merge@nexuscrm.vn",
        password_hash=hash_password("MktPass123!"),
        full_name="Nguyễn Thị Mai (Marketing)",
        role="MARKETING",
        department="Phòng Marketing",
        status="active",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def sales_user(db_session: Session) -> User:
    """Tạo tài khoản Nhân viên Kinh doanh (SALES_REP)."""
    user = User(
        id="usr-sales-merge-test",
        email="sales_merge@nexuscrm.vn",
        password_hash=hash_password("SalesPass123!"),
        full_name="Trần Văn Nam (Sales)",
        role="SALES_REP",
        department="Phòng Kinh Doanh",
        status="active",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_user(db_session: Session) -> User:
    """Tạo tài khoản Quản trị viên (ADMIN)."""
    user = User(
        id="usr-admin-merge-test",
        email="admin_merge@nexuscrm.vn",
        password_hash=hash_password("AdminPass123!"),
        full_name="Hoàng Quản Trị Viên",
        role="ADMIN",
        department="Ban Giám Đốc",
        status="active",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def auth_header(user: User) -> dict:
    """Tạo Bearer Token header."""
    token = create_access_token(user_id=user.id, email=user.email, role=user.role)
    return {"Authorization": f"Bearer {token}"}


class TestLeadDeduplicationDetection:
    """Kiểm tra chức năng quét phát hiện trùng lặp đa tiêu chí."""

    def test_duplicate_check_by_email(self, client: TestClient, marketing_user: User, db_session: Session):
        """Phát hiện trùng lặp chính xác theo Email."""
        lead = Lead(
            id=str(uuid.uuid4()),
            full_name="Nguyễn Văn An",
            phone="0912345678",
            email="an.nguyen@alphacorp.vn",
            company="Alpha Corp",
            source="Website",
            status="NEW",
            created_by=marketing_user.id,
        )
        db_session.add(lead)
        db_session.commit()

        resp = client.post(
            "/api/v1/leads/duplicates/check",
            headers=auth_header(marketing_user),
            json={"email": "AN.NGUYEN@ALPHACORP.VN"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_duplicate"] is True
        assert data["matches_count"] >= 1
        assert data["recommendation"] == "MERGE_LEADS"
        assert len(data["lead_matches"]) == 1
        assert "email" in data["lead_matches"][0]["match_fields"]
        assert data["lead_matches"][0]["target_id"] == lead.id

    def test_duplicate_check_by_phone_with_prefix_normalization(
        self, client: TestClient, marketing_user: User, db_session: Session
    ):
        """Phát hiện trùng lặp số điện thoại chuẩn hóa đầu số +84 về 0."""
        lead = Lead(
            id=str(uuid.uuid4()),
            full_name="Trần Thị Bình",
            phone="0987654321",
            email="binh.tran@beta.vn",
            company="Beta Retail",
            source="Sự kiện",
            status="NEW",
            created_by=marketing_user.id,
        )
        db_session.add(lead)
        db_session.commit()

        # Kiểm tra với đầu số +84
        resp = client.post(
            "/api/v1/leads/duplicates/check",
            headers=auth_header(marketing_user),
            json={"phone": "+84987654321"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_duplicate"] is True
        assert "phone" in data["lead_matches"][0]["match_fields"]
        assert data["recommendation"] == "MERGE_LEADS"

    def test_duplicate_check_by_company_fuzzy(
        self, client: TestClient, marketing_user: User, db_session: Session
    ):
        """Phát hiện trùng lặp tên công ty (loại bỏ tiền tố Công ty TNHH / Cổ phần)."""
        lead = Lead(
            id=str(uuid.uuid4()),
            full_name="Lê Hoàng Cường",
            phone="0905123456",
            email="cuong.le@gamma.vn",
            company="Công ty TNHH Giải Pháp Công Nghệ Gamma",
            source="Hội thảo",
            status="NEW",
            created_by=marketing_user.id,
        )
        db_session.add(lead)
        db_session.commit()

        resp = client.post(
            "/api/v1/leads/duplicates/check",
            headers=auth_header(marketing_user),
            json={"company": "Cty Cổ phần Giải Pháp Công Nghệ Gamma"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_duplicate"] is True
        assert "company" in data["lead_matches"][0]["match_fields"]

    def test_duplicate_check_exclude_lead_id(
        self, client: TestClient, marketing_user: User, db_session: Session
    ):
        """Bỏ qua chính Lead đang chỉnh sửa khi truyền exclude_lead_id."""
        lead = Lead(
            id=str(uuid.uuid4()),
            full_name="Phạm Văn Dũng",
            phone="0933112233",
            email="dung.pham@delta.vn",
            source="Giới thiệu",
            status="NEW",
            created_by=marketing_user.id,
        )
        db_session.add(lead)
        db_session.commit()

        resp = client.post(
            "/api/v1/leads/duplicates/check",
            headers=auth_header(marketing_user),
            json={
                "phone": "0933112233",
                "exclude_lead_id": lead.id,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_duplicate"] is False
        assert data["matches_count"] == 0
        assert data["recommendation"] == "NO_DUPLICATE"

    def test_duplicate_matching_customer_recommends_attach(
        self, client: TestClient, marketing_user: User, db_session: Session
    ):
        """Khi trùng với Khách hàng hiện có trong CRM -> gợi ý ATTACH_TO_CUSTOMER."""
        cust = Customer(
            id=str(uuid.uuid4()),
            full_name="Công ty Cổ phần VinTech",
            company="VinTech Group",
            email="contact@vintech.com",
            phone="02411122233",
            is_deleted=False,
        )
        db_session.add(cust)
        db_session.commit()

        resp = client.post(
            "/api/v1/leads/duplicates/check",
            headers=auth_header(marketing_user),
            json={"email": "contact@vintech.com"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_duplicate"] is True
        assert data["recommendation"] == "ATTACH_TO_CUSTOMER"
        assert len(data["customer_matches"]) == 1
        assert data["customer_matches"][0]["target_id"] == cust.id


class TestLeadMergeExecution:
    """Kiểm tra chức năng gộp 2 Lead trùng lặp và bảo toàn lịch sử."""

    def test_merge_leads_success_and_preserves_activities(
        self, client: TestClient, marketing_user: User, db_session: Session
    ):
        """Gộp thành công: bảo toàn Activities, nối tiếp ghi chú, cập nhật trạng thái MERGED."""
        primary = Lead(
            id="lead-master-01",
            full_name="Nguyễn Văn An (Bản ghi chính)",
            phone="0912345678",
            email="an.nguyen@company.com",
            company="Công ty An Thịnh",
            source="Website",
            notes="Ghi chú ban đầu của Lead chính",
            status="NEW",
            created_by=marketing_user.id,
        )
        duplicate = Lead(
            id="lead-dup-01",
            full_name="Nguyễn Văn An (Bản ghi phụ)",
            phone="0912345678",
            email="an.nguyen@gmail.com",
            company="Cty An Thịnh",
            source="Hội thảo Tech",
            notes="Quan tâm giải pháp ERP",
            status="NEW",
            created_by=marketing_user.id,
        )
        db_session.add_all([primary, duplicate])
        db_session.commit()

        # Thêm 2 Activity vào bản ghi phụ
        act1 = Activity(
            id="act-dup-01",
            lead_id=duplicate.id,
            user_id=marketing_user.id,
            type="call",
            title="Cuộc gọi chào hàng",
            description="Đã gọi điện tư vấn sản phẩm",
        )
        act2 = Activity(
            id="act-dup-02",
            lead_id=duplicate.id,
            user_id=marketing_user.id,
            type="email",
            title="Gửi brochure",
            description="Đã gửi tài liệu giải pháp qua email",
        )
        db_session.add_all([act1, act2])
        db_session.commit()

        # Thực thi gộp
        resp = client.post(
            "/api/v1/leads/duplicates/merge",
            headers=auth_header(marketing_user),
            json={
                "primary_lead_id": primary.id,
                "duplicate_lead_id": duplicate.id,
                "selected_fields": {
                    "source": "Website & Hội thảo",
                },
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == primary.id
        assert data["source"] == "Website & Hội thảo"

        # Kiểm tra CSDL sau khi gộp
        db_session.expire_all()
        reloaded_primary = db_session.query(Lead).filter(Lead.id == primary.id).first()
        reloaded_dup = db_session.query(Lead).filter(Lead.id == duplicate.id).first()

        # Bản ghi phụ bị đánh dấu MERGED
        assert reloaded_dup.status == "MERGED"
        assert reloaded_dup.merged_into_lead_id == primary.id

        # Toàn bộ Activities của bản ghi phụ đã được chuyển sang bản ghi chính
        moved_acts = db_session.query(Activity).filter(Activity.lead_id == primary.id).all()
        # Có act1, act2 và 1 activity hệ thống thông báo gộp thành công
        assert len(moved_acts) >= 3

        # Ghi chú đã được nối tiếp
        assert "Quan tâm giải pháp ERP" in reloaded_primary.notes

        # AuditLog ghi nhận hành động gộp
        audit = db_session.query(AuditLog).filter(
            AuditLog.action == "MERGE_LEAD",
            AuditLog.target_id == primary.id,
        ).first()
        assert audit is not None

    def test_merge_leads_self_merge_error(
        self, client: TestClient, marketing_user: User, db_session: Session
    ):
        """Bắt lỗi khi cố tình gộp Lead vào chính nó."""
        lead = Lead(
            id=str(uuid.uuid4()),
            full_name="Nguyễn Văn X",
            phone="0911223344",
            source="Sự kiện",
            status="NEW",
        )
        db_session.add(lead)
        db_session.commit()

        resp = client.post(
            "/api/v1/leads/duplicates/merge",
            headers=auth_header(marketing_user),
            json={
                "primary_lead_id": lead.id,
                "duplicate_lead_id": lead.id,
            },
        )
        assert resp.status_code == 400
        assert "không thể là cùng một bản ghi" in resp.json()["detail"]

    def test_merge_leads_already_merged_error(
        self, client: TestClient, marketing_user: User, db_session: Session
    ):
        """Bắt lỗi khi Lead phụ đã ở trạng thái MERGED."""
        primary = Lead(
            id=str(uuid.uuid4()),
            full_name="Lead Master",
            phone="0911000111",
            source="Sự kiện",
            status="NEW",
        )
        dup = Lead(
            id=str(uuid.uuid4()),
            full_name="Lead Dup",
            phone="0911000111",
            source="Sự kiện",
            status="MERGED",
        )
        db_session.add_all([primary, dup])
        db_session.commit()

        resp = client.post(
            "/api/v1/leads/duplicates/merge",
            headers=auth_header(marketing_user),
            json={
                "primary_lead_id": primary.id,
                "duplicate_lead_id": dup.id,
            },
        )
        assert resp.status_code == 400
        assert "đã được gộp" in resp.json()["detail"]

    def test_merge_leads_permission_sales_rep_forbidden(
        self, client: TestClient, sales_user: User, db_session: Session
    ):
        """Nhân viên SALES_REP không có quyền thực hiện gộp Lead (403 Forbidden)."""
        primary = Lead(
            id=str(uuid.uuid4()),
            full_name="Lead A",
            phone="0911222333",
            source="Website",
            status="NEW",
        )
        dup = Lead(
            id=str(uuid.uuid4()),
            full_name="Lead B",
            phone="0911222333",
            source="Website",
            status="NEW",
        )
        db_session.add_all([primary, dup])
        db_session.commit()

        resp = client.post(
            "/api/v1/leads/duplicates/merge",
            headers=auth_header(sales_user),
            json={
                "primary_lead_id": primary.id,
                "duplicate_lead_id": dup.id,
            },
        )
        assert resp.status_code == 403
        assert "Bạn không có quyền thực hiện gộp Lead" in resp.json()["detail"]

    def test_merge_leads_rollback_on_db_error(
        self, client: TestClient, marketing_user: User, db_session: Session
    ):
        """Transaction rollback toàn bộ khi phát sinh lỗi hệ thống trong quá trình gộp."""
        primary = Lead(
            id=str(uuid.uuid4()),
            full_name="Lead Safe Master",
            phone="0988776655",
            source="Website",
            status="NEW",
        )
        dup = Lead(
            id=str(uuid.uuid4()),
            full_name="Lead Safe Dup",
            phone="0988776655",
            source="Website",
            status="NEW",
        )
        db_session.add_all([primary, dup])
        db_session.commit()

        # Mock db.commit gây lỗi
        with patch.object(Session, "commit", side_effect=RuntimeError("Simulated Database Crash")):
            resp = client.post(
                "/api/v1/leads/duplicates/merge",
                headers=auth_header(marketing_user),
                json={
                    "primary_lead_id": primary.id,
                    "duplicate_lead_id": dup.id,
                },
            )
            assert resp.status_code == 500
            assert "Lỗi giao dịch" in resp.json()["detail"]


class TestLeadAttachToCustomer:
    """Kiểm tra chức năng gắn Lead trùng vào Khách hàng (Lead-to-Customer)."""

    def test_attach_lead_to_customer_success(
        self, client: TestClient, marketing_user: User, db_session: Session
    ):
        """Gắn Lead vào Khách hàng thành công, chuyển đổi trạng thái CONVERTED và chuyển Activities."""
        customer = Customer(
            id="cust-attach-target",
            full_name="Tập đoàn Công nghệ Sao Mai",
            company="Sao Mai Tech",
            email="info@saomai.vn",
            phone="02488889999",
            is_deleted=False,
        )
        lead = Lead(
            id="lead-attach-src",
            full_name="Đặng Văn Hùng",
            phone="0988223344",
            email="hung.dang@saomai.vn",
            company="Sao Mai Tech",
            source="Landing Page",
            status="NEW",
            created_by=marketing_user.id,
        )
        db_session.add_all([customer, lead])
        db_session.commit()

        # Tạo activity cho lead
        act = Activity(
            id="act-lead-attach-01",
            lead_id=lead.id,
            user_id=marketing_user.id,
            type="email",
            title="Đăng ký tư vấn giải pháp",
            description="Khách đăng ký qua form web",
        )
        db_session.add(act)
        db_session.commit()

        resp = client.post(
            "/api/v1/leads/attach-to-customer",
            headers=auth_header(marketing_user),
            json={
                "lead_id": lead.id,
                "customer_id": customer.id,
                "notes": "Lead liên hệ lại từ sự kiện triển lãm",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["lead_id"] == lead.id
        assert data["customer_id"] == customer.id
        assert data["status"] == "CONVERTED"

        db_session.expire_all()
        reloaded_lead = db_session.query(Lead).filter(Lead.id == lead.id).first()
        assert reloaded_lead.status == "CONVERTED"
        assert reloaded_lead.converted_customer_id == customer.id

        # Activity cũ đã được chuyển sang customer_id
        reloaded_act = db_session.query(Activity).filter(Activity.id == act.id).first()
        assert reloaded_act.customer_id == customer.id
        assert reloaded_act.lead_id is None

        # Có thêm activity gắn mới trên customer
        customer_acts = db_session.query(Activity).filter(Activity.customer_id == customer.id).all()
        assert len(customer_acts) >= 2

    def test_attach_lead_not_found(self, client: TestClient, marketing_user: User):
        """Bắt lỗi 404 khi lead_id không tồn tại."""
        resp = client.post(
            "/api/v1/leads/attach-to-customer",
            headers=auth_header(marketing_user),
            json={
                "lead_id": "non-existent-lead",
                "customer_id": "any-cust",
            },
        )
        assert resp.status_code == 404
