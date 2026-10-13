"""
Unit Test & Integration Test cho SCRUM-48 (Sprint 4 / Epic Lead SCRUM-30):
Cấu hình chấm điểm Lead (Lead Scoring) và Tự động phân loại Nóng/Ấm/Lạnh.

Kiểm tra 100% Acceptance Criteria:
1. Quản lý danh mục quy tắc chấm điểm động theo 4 nhóm: INDUSTRY, COMPANY_SIZE, SOURCE, INTEREST_LEVEL.
2. Cấu hình ngưỡng nhiệt độ động: Nóng (HOT >= hot_threshold), Ấm (WARM >= warm_threshold), Lạnh (COLD < warm_threshold).
3. Validate ràng buộc nghiệp vụ hot_threshold > warm_threshold.
4. Phân quyền RBAC: Chỉ DIRECTOR và ADMIN có quyền cấu hình rules/settings và chạy recalculate; SALES_REP bị chặn (403).
5. Tự động tính điểm thời gian thực khi tạo lead mới qua POST /api/v1/leads/manual và cập nhật qua PUT /api/v1/leads/{id}.
6. Tự động tính lại điểm Lead chính sau khi gộp lead trùng lặp qua POST /api/v1/leads/duplicates/merge.
7. Chạy tác vụ tính toán lại hàng loạt qua POST /api/v1/leads/scoring/recalculate-all cho toàn bộ Lead hoạt động.
8. API danh sách Lead hỗ trợ sắp xếp ưu tiên theo điểm (sort_by=score&sort_order=desc) và lọc nhiệt độ (temperature=HOT,WARM,COLD).
9. Đảm bảo Lead có điểm số thấp hoặc nhiệt độ COLD tuyệt đối không bị xóa/loại bỏ.
"""
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.lead import Lead
from app.models.lead_scoring import LeadScoringRule, LeadScoringSettings
from app.core.security import hash_password, create_access_token


@pytest.fixture
def director_user(db_session: Session) -> User:
    """Tạo tài khoản Giám đốc kinh doanh (DIRECTOR)."""
    user = User(
        id="usr-director-scoring-test",
        email="director_scoring@nexuscrm.vn",
        password_hash=hash_password("DirectorPass123!"),
        full_name="Nguyễn Văn Giám Đốc",
        role="DIRECTOR",
        department="Ban Giám Đốc",
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
        id="usr-admin-scoring-test",
        email="admin_scoring@nexuscrm.vn",
        password_hash=hash_password("AdminPass123!"),
        full_name="Lê Quản Trị Viên",
        role="ADMIN",
        department="Phòng Công Nghệ",
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
        id="usr-sales-scoring-test",
        email="sales_scoring@nexuscrm.vn",
        password_hash=hash_password("SalesPass123!"),
        full_name="Trần Nhân Viên Sales",
        role="SALES_REP",
        department="Phòng Kinh Doanh",
        status="active",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def auth_header(user: User) -> dict:
    """Tạo Authorization Bearer Token header."""
    token = create_access_token(user_id=user.id, email=user.email, role=user.role)
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# 1. TEST CRUD QUY TẮC CHẤM ĐIỂM (SCORING RULES) & PHÂN QUYỀN
# ==============================================================================

class TestScoringRulesManagement:
    """Kiểm tra CRUD quy tắc chấm điểm và phân quyền RBAC."""

    def test_create_scoring_rule_success(self, client: TestClient, director_user: User):
        """DIRECTOR tạo mới quy tắc chấm điểm thành công."""
        payload = {
            "criteria_type": "INDUSTRY",
            "criteria_value": "Công nghệ thông tin",
            "score": 20,
            "is_active": True,
        }
        resp = client.post(
            "/api/v1/leads/scoring/rules",
            headers=auth_header(director_user),
            json=payload,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["criteria_type"] == "INDUSTRY"
        assert data["criteria_value"] == "Công nghệ thông tin"
        assert data["score"] == 20
        assert data["is_active"] is True
        assert "id" in data

    def test_get_scoring_rules_with_filters(self, client: TestClient, director_user: User):
        """DIRECTOR lấy danh sách quy tắc có áp dụng bộ lọc criteria_type và is_active."""
        # Tạo thêm 2 rule
        client.post(
            "/api/v1/leads/scoring/rules",
            headers=auth_header(director_user),
            json={"criteria_type": "SOURCE", "criteria_value": "Website Form", "score": 30, "is_active": True},
        )
        client.post(
            "/api/v1/leads/scoring/rules",
            headers=auth_header(director_user),
            json={"criteria_type": "COMPANY_SIZE", "criteria_value": ">100", "score": 25, "is_active": False},
        )

        # Lọc theo criteria_type=SOURCE
        resp = client.get(
            "/api/v1/leads/scoring/rules?criteria_type=SOURCE",
            headers=auth_header(director_user),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert any(r["criteria_type"] == "SOURCE" for r in data)
        assert all(r["criteria_type"] == "SOURCE" for r in data)

        # Lọc theo is_active=true
        resp_active = client.get(
            "/api/v1/leads/scoring/rules?is_active=true",
            headers=auth_header(director_user),
        )
        assert resp_active.status_code == 200
        active_rules = resp_active.json()
        assert all(r["is_active"] is True for r in active_rules)

    def test_update_scoring_rule(self, client: TestClient, director_user: User):
        """DIRECTOR cập nhật điểm số và trạng thái quy tắc chấm điểm."""
        # Tạo rule
        create_resp = client.post(
            "/api/v1/leads/scoring/rules",
            headers=auth_header(director_user),
            json={"criteria_type": "INTEREST_LEVEL", "criteria_value": "HIGH", "score": 25, "is_active": True},
        )
        rule_id = create_resp.json()["id"]

        # Cập nhật điểm thành 30
        update_resp = client.put(
            f"/api/v1/leads/scoring/rules/{rule_id}",
            headers=auth_header(director_user),
            json={"score": 30, "criteria_value": "VERY_HIGH"},
        )
        assert update_resp.status_code == 200
        updated_data = update_resp.json()
        assert updated_data["score"] == 30
        assert updated_data["criteria_value"] == "VERY_HIGH"

    def test_delete_scoring_rule(self, client: TestClient, director_user: User):
        """DIRECTOR xóa một quy tắc chấm điểm."""
        create_resp = client.post(
            "/api/v1/leads/scoring/rules",
            headers=auth_header(director_user),
            json={"criteria_type": "SOURCE", "criteria_value": "Tự tìm kiếm", "score": 5, "is_active": True},
        )
        rule_id = create_resp.json()["id"]

        # Xóa
        del_resp = client.delete(
            f"/api/v1/leads/scoring/rules/{rule_id}",
            headers=auth_header(director_user),
        )
        assert del_resp.status_code == 200

        # Cập nhật thử lại sau khi xóa -> 404
        update_resp = client.put(
            f"/api/v1/leads/scoring/rules/{rule_id}",
            headers=auth_header(director_user),
            json={"score": 10},
        )
        assert update_resp.status_code == 404

    def test_sales_rep_forbidden_on_rules(self, client: TestClient, sales_user: User):
        """SALES_REP không có quyền cấu hình rules (403 Forbidden)."""
        resp = client.get(
            "/api/v1/leads/scoring/rules",
            headers=auth_header(sales_user),
        )
        assert resp.status_code == 403

        resp_create = client.post(
            "/api/v1/leads/scoring/rules",
            headers=auth_header(sales_user),
            json={"criteria_type": "INDUSTRY", "criteria_value": "Giáo dục", "score": 10},
        )
        assert resp_create.status_code == 403


# ==============================================================================
# 2. TEST CẤU HÌNH NGƯỠNG NHIỆT ĐỘ (SCORING SETTINGS)
# ==============================================================================

class TestScoringSettingsManagement:
    """Kiểm tra quản lý cấu hình ngưỡng nhiệt độ và validation."""

    def test_get_default_scoring_settings(self, client: TestClient, director_user: User):
        """Lấy cấu hình ngưỡng mặc định (HOT >= 70, WARM >= 40)."""
        resp = client.get(
            "/api/v1/leads/scoring/settings",
            headers=auth_header(director_user),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["hot_threshold"] == 70
        assert data["warm_threshold"] == 40

    def test_update_scoring_settings_success(self, client: TestClient, admin_user: User):
        """ADMIN cập nhật ngưỡng nhiệt độ thành công."""
        payload = {"hot_threshold": 80, "warm_threshold": 50}
        resp = client.put(
            "/api/v1/leads/scoring/settings",
            headers=auth_header(admin_user),
            json=payload,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["hot_threshold"] == 80
        assert data["warm_threshold"] == 50

    def test_update_scoring_settings_validation_error(self, client: TestClient, director_user: User):
        """Ràng buộc hot_threshold phải lớn hơn warm_threshold (trả về 422)."""
        # hot <= warm
        invalid_payload = {"hot_threshold": 40, "warm_threshold": 50}
        resp = client.put(
            "/api/v1/leads/scoring/settings",
            headers=auth_header(director_user),
            json=invalid_payload,
        )
        assert resp.status_code == 422

        # hot == warm
        equal_payload = {"hot_threshold": 60, "warm_threshold": 60}
        resp2 = client.put(
            "/api/v1/leads/scoring/settings",
            headers=auth_header(director_user),
            json=equal_payload,
        )
        assert resp2.status_code == 422

    def test_sales_rep_forbidden_on_settings(self, client: TestClient, sales_user: User):
        """SALES_REP không có quyền chỉnh sửa ngưỡng nhiệt độ (403 Forbidden)."""
        resp = client.put(
            "/api/v1/leads/scoring/settings",
            headers=auth_header(sales_user),
            json={"hot_threshold": 75, "warm_threshold": 45},
        )
        assert resp.status_code == 403


# ==============================================================================
# 3. TEST TỰ ĐỘNG TÍNH ĐIỂM THỜI GIAN THỰC (REALTIME SCORING ENGINE)
# ==============================================================================

class TestRealtimeLeadScoringEngine:
    """Kiểm tra engine tính điểm tự động khi tạo, sửa, gộp Lead."""

    @pytest.fixture(autouse=True)
    def setup_rules_and_settings(self, db_session: Session):
        """Khởi tạo bộ quy tắc và ngưỡng chuẩn cho test suite."""
        # Reset settings
        settings = db_session.query(LeadScoringSettings).filter(LeadScoringSettings.id == 1).first()
        if not settings:
            settings = LeadScoringSettings(id=1, hot_threshold=70, warm_threshold=40)
            db_session.add(settings)
        else:
            settings.hot_threshold = 70
            settings.warm_threshold = 40
        db_session.commit()

        # Xóa rules cũ
        db_session.query(LeadScoringRule).delete()

        # Thêm các quy tắc mẫu theo mô tả AC
        sample_rules = [
            # Ngành nghề
            LeadScoringRule(id=str(uuid.uuid4()), criteria_type="INDUSTRY", criteria_value="Công nghệ thông tin", score=20, is_active=True),
            LeadScoringRule(id=str(uuid.uuid4()), criteria_type="INDUSTRY", criteria_value="Bán lẻ", score=15, is_active=True),
            # Quy mô
            LeadScoringRule(id=str(uuid.uuid4()), criteria_type="COMPANY_SIZE", criteria_value="Doanh nghiệp lớn", score=25, is_active=True),
            LeadScoringRule(id=str(uuid.uuid4()), criteria_type="COMPANY_SIZE", criteria_value="Doanh nghiệp vừa", score=15, is_active=True),
            # Nguồn
            LeadScoringRule(id=str(uuid.uuid4()), criteria_type="SOURCE", criteria_value="Website Form", score=30, is_active=True),
            LeadScoringRule(id=str(uuid.uuid4()), criteria_type="SOURCE", criteria_value="Giới thiệu", score=25, is_active=True),
            # Mức độ quan tâm
            LeadScoringRule(id=str(uuid.uuid4()), criteria_type="INTEREST_LEVEL", criteria_value="HIGH", score=30, is_active=True),
            LeadScoringRule(id=str(uuid.uuid4()), criteria_type="INTEREST_LEVEL", criteria_value="MEDIUM", score=15, is_active=True),
        ]
        db_session.add_all(sample_rules)
        db_session.commit()

    def test_create_lead_automatically_calculates_hot_score(self, client: TestClient, sales_user: User):
        """Tạo Lead mới có đủ tiêu chí đạt điểm cao -> Hệ thống tính score=105 và gán HOT."""
        # 20 (CNTT) + 25 (Doanh nghiệp lớn) + 30 (Website Form) + 30 (HIGH) = 105 >= 70 -> HOT
        lead_payload = {
            "full_name": "Nguyễn Hoàng Nam",
            "phone": "0912345678",
            "email": "nam.hoang@techcorp.vn",
            "company": "Tech Corp",
            "source": "Website Form",
            "industry": "Công nghệ thông tin",
            "company_size": "Doanh nghiệp lớn",
            "interest_level": "HIGH",
        }
        resp = client.post(
            "/api/v1/leads/manual",
            headers=auth_header(sales_user),
            json=lead_payload,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["score"] == 105
        assert data["temperature"] == "HOT"

    def test_create_lead_calculates_warm_score(self, client: TestClient, sales_user: User):
        """Tạo Lead có điểm trong khoảng [40, 70) -> Hệ thống gán WARM."""
        # 15 (Bán lẻ) + 30 (Website Form) = 45 -> 40 <= 45 < 70 -> WARM
        lead_payload = {
            "full_name": "Lê Văn Hùng",
            "phone": "0987654321",
            "source": "Website Form",
            "industry": "Bán lẻ",
        }
        resp = client.post(
            "/api/v1/leads/manual",
            headers=auth_header(sales_user),
            json=lead_payload,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["score"] == 45
        assert data["temperature"] == "WARM"

    def test_create_lead_calculates_cold_score(self, client: TestClient, sales_user: User):
        """Tạo Lead có điểm < 40 -> Hệ thống gán COLD."""
        # Chỉ có ngành Bán lẻ (+15), nguồn 'Sự kiện' (0) = 15 < 40 -> COLD
        lead_payload = {
            "full_name": "Phạm Thị Thảo",
            "phone": "0909112233",
            "source": "Sự kiện",
            "industry": "Bán lẻ",
        }
        resp = client.post(
            "/api/v1/leads/manual",
            headers=auth_header(sales_user),
            json=lead_payload,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["score"] == 15
        assert data["temperature"] == "COLD"

    def test_update_lead_recalculates_score_realtime(self, client: TestClient, sales_user: User):
        """Cập nhật thông tin Lead -> Tự động tính lại điểm và chuyển nhiệt độ sang HOT."""
        # 1. Tạo Lead ban đầu có điểm COLD: Nguồn 'Khác' (0), Ngành 'Bán lẻ' (15)
        create_resp = client.post(
            "/api/v1/leads/manual",
            headers=auth_header(sales_user),
            json={
                "full_name": "Trần Thị Lan",
                "phone": "0933445566",
                "source": "Khác",
                "industry": "Bán lẻ",
            },
        )
        assert create_resp.status_code == 201
        lead_id = create_resp.json()["id"]
        assert create_resp.json()["score"] == 15
        assert create_resp.json()["temperature"] == "COLD"

        # 2. Cập nhật Lead: bổ sung industry=CNTT (20), source=Website Form (30), interest_level=HIGH (30)
        # Tổng điểm mới: 20 + 30 + 30 = 80 >= 70 -> HOT
        update_resp = client.put(
            f"/api/v1/leads/{lead_id}",
            headers=auth_header(sales_user),
            json={
                "industry": "Công nghệ thông tin",
                "source": "Website Form",
                "interest_level": "HIGH",
            },
        )
        assert update_resp.status_code == 200
        updated = update_resp.json()
        assert updated["score"] == 80
        assert updated["temperature"] == "HOT"

    def test_merge_leads_recalculates_score_for_primary_lead(self, client: TestClient, director_user: User, db_session: Session):
        """Sau khi gộp Lead trùng lặp, Lead chính được tính lại điểm số tự động."""
        # 1. Tạo Lead chính: chỉ có nguồn Website Form (+30) -> Điểm 30 (COLD)
        primary = Lead(
            id=str(uuid.uuid4()),
            full_name="Nguyễn Văn Master",
            phone="0911223344",
            source="Website Form",
            score=30,
            temperature="COLD",
            status="NEW",
            created_by=director_user.id,
        )
        # 2. Tạo Lead phụ: có interest_level = HIGH (+30), industry = Công nghệ thông tin (+20)
        duplicate = Lead(
            id=str(uuid.uuid4()),
            full_name="Nguyễn Văn Master 2",
            phone="0911223344",
            source="Giới thiệu",
            industry="Công nghệ thông tin",
            interest_level="HIGH",
            score=50,
            temperature="WARM",
            status="NEW",
            created_by=director_user.id,
        )
        db_session.add_all([primary, duplicate])
        db_session.commit()

        # 3. Gộp lead: chọn giữ lại industry và interest_level từ duplicate sang primary
        merge_payload = {
            "primary_lead_id": primary.id,
            "duplicate_lead_id": duplicate.id,
            "selected_fields": {
                "industry": duplicate.industry,
                "interest_level": duplicate.interest_level,
            },
        }
        resp = client.post(
            "/api/v1/leads/duplicates/merge",
            headers=auth_header(director_user),
            json=merge_payload,
        )
        assert resp.status_code == 200
        merged_lead = resp.json()
        # Lead chính giờ có: source=Website Form (30) + industry=CNTT (20) + interest_level=HIGH (30) = 80 -> HOT
        assert merged_lead["score"] == 80
        assert merged_lead["temperature"] == "HOT"


# ==============================================================================
# 4. TEST TÍNH TOÁN LẠI ĐIỂM SỐ HÀNG LOẠT (BATCH RECALCULATE)
# ==============================================================================

class TestBatchRecalculateLeads:
    """Kiểm tra API chạy tính toán lại toàn bộ điểm cho Lead hiện hữu."""

    def test_batch_recalculate_all_leads(self, client: TestClient, director_user: User, db_session: Session):
        """DIRECTOR thực thi tác vụ tính lại điểm toàn bộ Lead hoạt động."""
        # Khởi tạo cấu hình và bộ rules
        settings = db_session.query(LeadScoringSettings).filter(LeadScoringSettings.id == 1).first()
        if not settings:
            settings = LeadScoringSettings(id=1, hot_threshold=70, warm_threshold=40)
            db_session.add(settings)
        else:
            settings.hot_threshold = 70
            settings.warm_threshold = 40

        db_session.query(LeadScoringRule).delete()
        sample_rules = [
            LeadScoringRule(id=str(uuid.uuid4()), criteria_type="INDUSTRY", criteria_value="Công nghệ thông tin", score=20, is_active=True),
            LeadScoringRule(id=str(uuid.uuid4()), criteria_type="INDUSTRY", criteria_value="Bán lẻ", score=15, is_active=True),
            LeadScoringRule(id=str(uuid.uuid4()), criteria_type="COMPANY_SIZE", criteria_value="Doanh nghiệp lớn", score=25, is_active=True),
            LeadScoringRule(id=str(uuid.uuid4()), criteria_type="SOURCE", criteria_value="Website Form", score=30, is_active=True),
            LeadScoringRule(id=str(uuid.uuid4()), criteria_type="SOURCE", criteria_value="Giới thiệu", score=25, is_active=True),
        ]
        db_session.add_all(sample_rules)
        db_session.commit()

        # Tạo 3 lead với các thuộc tính khác nhau
        # Lead 1: 30 (Website Form) + 20 (CNTT) + 25 (Doanh nghiệp lớn) = 75 -> HOT
        lead1 = Lead(
            id=str(uuid.uuid4()),
            full_name="Lead Hot Test",
            phone="0911111111",
            source="Website Form",
            industry="Công nghệ thông tin",
            company_size="Doanh nghiệp lớn",
            score=0,
            temperature="COLD",
            status="NEW",
        )
        # Lead 2: 25 (Giới thiệu) + 20 (CNTT) = 45 -> WARM
        lead2 = Lead(
            id=str(uuid.uuid4()),
            full_name="Lead Warm Test",
            phone="0922222222",
            source="Giới thiệu",
            industry="Công nghệ thông tin",
            score=0,
            temperature="COLD",
            status="NEW",
        )
        # Lead 3: 15 (Bán lẻ) -> COLD
        lead3 = Lead(
            id=str(uuid.uuid4()),
            full_name="Lead Cold Test",
            phone="0933333333",
            source="Tự tìm kiếm",
            industry="Bán lẻ",
            score=0,
            temperature="COLD",
            status="NEW",
        )
        # Lead 4: Đã gộp (status = 'MERGED') -> Không được tính
        lead4 = Lead(
            id=str(uuid.uuid4()),
            full_name="Lead Merged Test",
            phone="0944444444",
            source="Website Form",
            score=0,
            temperature="COLD",
            status="MERGED",
        )
        db_session.add_all([lead1, lead2, lead3, lead4])
        db_session.commit()

        # Thực hiện recalculate-all
        resp = client.post(
            "/api/v1/leads/scoring/recalculate-all",
            headers=auth_header(director_user),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_leads_processed"] >= 3
        assert data["hot_count"] >= 1
        assert data["warm_count"] >= 1
        assert data["cold_count"] >= 1
        assert data["execution_time_seconds"] >= 0

        # Kiểm tra dữ liệu trong DB đã được cập nhật
        db_session.refresh(lead1)
        assert lead1.score == 75
        assert lead1.temperature == "HOT"

        db_session.refresh(lead2)
        assert lead2.score == 45
        assert lead2.temperature == "WARM"

        db_session.refresh(lead3)
        assert lead3.score == 15
        assert lead3.temperature == "COLD"

    def test_sales_rep_forbidden_on_batch_recalculate(self, client: TestClient, sales_user: User):
        """SALES_REP không được phép kích hoạt tính toán lại hàng loạt (403 Forbidden)."""
        resp = client.post(
            "/api/v1/leads/scoring/recalculate-all",
            headers=auth_header(sales_user),
        )
        assert resp.status_code == 403


# ==============================================================================
# 5. TEST SẮP XẾP ƯU TIÊN VÀ BỘ LỌC NHIỆT ĐỘ (AC4)
# ==============================================================================

class TestLeadPrioritySortingAndFilter:
    """Kiểm tra API danh sách Lead hỗ trợ sắp xếp theo điểm và lọc theo nhiệt độ."""

    def test_priority_order_by_score_desc(self, client: TestClient, sales_user: User, db_session: Session):
        """Sắp xếp danh sách Lead theo điểm số giảm dần (sort_by=score&sort_order=desc)."""
        l1 = Lead(id=str(uuid.uuid4()), full_name="Lead Score 20", phone="0900000001", source="A", score=20, temperature="COLD", status="NEW")
        l2 = Lead(id=str(uuid.uuid4()), full_name="Lead Score 90", phone="0900000002", source="B", score=90, temperature="HOT", status="NEW")
        l3 = Lead(id=str(uuid.uuid4()), full_name="Lead Score 50", phone="0900000003", source="C", score=50, temperature="WARM", status="NEW")
        db_session.add_all([l1, l2, l3])
        db_session.commit()

        resp = client.get(
            "/api/v1/leads?sort_by=score&sort_order=desc",
            headers=auth_header(sales_user),
        )
        assert resp.status_code == 200
        leads = resp.json()
        scores = [l["score"] for l in leads]
        # Điểm phải theo thứ tự giảm dần
        assert scores == sorted(scores, reverse=True)
        assert scores[0] >= 90

    def test_filter_by_temperature(self, client: TestClient, sales_user: User, db_session: Session):
        """Lọc danh sách Lead theo nhiệt độ (temperature=HOT)."""
        l_hot = Lead(id=str(uuid.uuid4()), full_name="Hot Lead", phone="0911000001", source="Web", score=85, temperature="HOT", status="NEW")
        l_cold = Lead(id=str(uuid.uuid4()), full_name="Cold Lead", phone="0911000002", source="Event", score=10, temperature="COLD", status="NEW")
        db_session.add_all([l_hot, l_cold])
        db_session.commit()

        resp_hot = client.get(
            "/api/v1/leads?temperature=HOT",
            headers=auth_header(sales_user),
        )
        assert resp_hot.status_code == 200
        hot_leads = resp_hot.json()
        assert all(l["temperature"] == "HOT" for l in hot_leads)
        assert any(l["id"] == l_hot.id for l in hot_leads)
        assert not any(l["id"] == l_cold.id for l in hot_leads)

    def test_cold_leads_are_never_deleted_or_dropped(self, client: TestClient, sales_user: User, db_session: Session):
        """Nguyên tắc AC4: Lead điểm thấp/COLD tuyệt đối không bị tự động loại bỏ."""
        l_zero = Lead(id=str(uuid.uuid4()), full_name="Zero Score Lead", phone="0999888777", source="Manual", score=0, temperature="COLD", status="NEW")
        db_session.add(l_zero)
        db_session.commit()

        resp = client.get(
            f"/api/v1/leads/{l_zero.id}",
            headers=auth_header(sales_user),
        )
        assert resp.status_code == 200
        assert resp.json()["score"] == 0
        assert resp.json()["temperature"] == "COLD"
        assert resp.json()["status"] == "NEW"
