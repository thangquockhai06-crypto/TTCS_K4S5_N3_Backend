import os
import sys
from typing import Generator, Dict, Any
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Thêm thư mục server vào sys.path
SERVER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

from app.database import Base, get_db
from app.main import app
from app.models.user import User
from app.models.customer import Customer
from app.models.deal import Deal
from app.models.activity import Activity
from app.models.quotation import Quotation
from app.core.security import hash_password, create_access_token

# Sử dụng SQLite in-memory với StaticPool cho tốc độ cao và cô lập tuyệt đối khi test
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def init_test_db():
    """Khởi tạo toàn bộ cấu trúc bảng trước khi chạy bộ test."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Cung cấp session CSDL cô lập cho mỗi test case."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """FastAPI TestClient với CSDL đã được override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# Sinh sẵn password hash một lần duy nhất cho toàn bộ session để tăng tốc độ chạy test
STATIC_TEST_PASSWORD_HASH = hash_password("Password123!")


@pytest.fixture
def seed_data(db_session: Session) -> Dict[str, Any]:
    """
    Nạp dữ liệu mẫu đại diện cho ma trận phân quyền:
    - Employee A (Team Alpha)
    - Employee B (Team Alpha)
    - Team Leader (Team Alpha)
    - Employee Beta (Team Beta - Cross Team)
    - Sales Director (ALL Scope)
    - Leader No Team (Edge case)
    """
    pwd = STATIC_TEST_PASSWORD_HASH

    # 1. Người dùng
    emp_a = User(
        id="usr-emp-a",
        email="emp_a@nexuscrm.vn",
        password_hash=pwd,
        full_name="Nguyễn Văn A (Nhân viên A)",
        role="Employee",
        team_id="team-alpha",
        department="Kinh Doanh 1",
    )
    emp_b = User(
        id="usr-emp-b",
        email="emp_b@nexuscrm.vn",
        password_hash=pwd,
        full_name="Trần Thị B (Nhân viên B)",
        role="Employee",
        team_id="team-alpha",
        department="Kinh Doanh 1",
    )
    team_leader = User(
        id="usr-team-lead",
        email="leader@nexuscrm.vn",
        password_hash=pwd,
        full_name="Lê Trưởng Nhóm Alpha",
        role="Team Leader",
        team_id="team-alpha",
        department="Kinh Doanh 1",
    )
    emp_beta = User(
        id="usr-emp-beta",
        email="emp_beta@nexuscrm.vn",
        password_hash=pwd,
        full_name="Phạm Đội Khác (Team Beta)",
        role="Employee",
        team_id="team-beta",
        department="Kinh Doanh 2",
    )
    sales_director = User(
        id="usr-sales-director",
        email="director@nexuscrm.vn",
        password_hash=pwd,
        full_name="Hoàng Giám Đốc Kinh Doanh",
        role="Sales Director",
        team_id=None,
        department="Ban Giám Đốc",
    )
    leader_no_team = User(
        id="usr-lead-no-team",
        email="no_team_lead@nexuscrm.vn",
        password_hash=pwd,
        full_name="Trưởng nhóm chưa gán team",
        role="Team Leader",
        team_id=None,
        department="Chưa xác định",
    )

    db_session.add_all([emp_a, emp_b, team_leader, emp_beta, sales_director, leader_no_team])
    db_session.commit()

    # 2. Khách hàng (Customers)
    cust_a = Customer(
        id="cust-emp-a",
        full_name="Khách Hàng Của A",
        email="khach_a@test.com",
        phone="0901000001",
        company="Công ty A Corp",
        status="active",
        health_score=90,
        assigned_user_id=emp_a.id,
    )
    cust_b = Customer(
        id="cust-emp-b",
        full_name="Khách Hàng Của B",
        email="khach_b@test.com",
        phone="0901000002",
        company="Công ty B Solution",
        status="lead",
        health_score=75,
        assigned_user_id=emp_b.id,
    )
    cust_beta = Customer(
        id="cust-emp-beta",
        full_name="Khách Hàng Đội Beta",
        email="khach_beta@test.com",
        phone="0901000003",
        company="Công ty Beta Tech",
        status="prospect",
        health_score=80,
        assigned_user_id=emp_beta.id,
    )
    cust_unassigned = Customer(
        id="cust-unassigned",
        full_name="Khách Hàng Chưa Gán",
        email="unassigned@test.com",
        phone="0901000004",
        company="Vô Chủ Corp",
        status="lead",
        health_score=60,
        assigned_user_id=None,
    )
    db_session.add_all([cust_a, cust_b, cust_beta, cust_unassigned])
    db_session.commit()

    # 3. Cơ hội bán hàng (Deals)
    deal_a = Deal(
        id="deal-emp-a",
        title="Hợp đồng CRM A",
        value=50000000.0,
        stage="proposal",
        probability=60,
        customer_id=cust_a.id,
        owner_id=emp_a.id,
    )
    deal_b = Deal(
        id="deal-emp-b",
        title="Hợp đồng CRM B",
        value=80000000.0,
        stage="negotiation",
        probability=80,
        customer_id=cust_b.id,
        owner_id=emp_b.id,
    )
    deal_beta = Deal(
        id="deal-emp-beta",
        title="Hợp đồng ERP Beta",
        value=120000000.0,
        stage="won",
        probability=100,
        customer_id=cust_beta.id,
        owner_id=emp_beta.id,
    )
    db_session.add_all([deal_a, deal_b, deal_beta])
    db_session.commit()

    # 4. Hoạt động (Activities)
    act_a = Activity(
        id="act-emp-a",
        customer_id=cust_a.id,
        user_id=emp_a.id,
        type="call",
        title="Cuộc gọi tư vấn KH A",
        description="Đã gọi giới thiệu tính năng",
    )
    act_b = Activity(
        id="act-emp-b",
        customer_id=cust_b.id,
        user_id=emp_b.id,
        type="meeting",
        title="Gặp mặt demo KH B",
        description="Demo trực tiếp tại văn phòng KH",
    )
    act_beta = Activity(
        id="act-emp-beta",
        customer_id=cust_beta.id,
        user_id=emp_beta.id,
        type="email",
        title="Gửi báo giá KH Beta",
        description="Đã gửi email kèm phụ lục hợp đồng",
    )
    db_session.add_all([act_a, act_b, act_beta])
    db_session.commit()

    # 5. Báo giá (Quotations)
    quote_a = Quotation(
        id="quote-emp-a",
        quote_number="BG-2026-001",
        title="Báo giá gói Enterprise cho KH A",
        customer_id=cust_a.id,
        owner_id=emp_a.id,
        total_amount=50000000.0,
        status="draft",
    )
    quote_b = Quotation(
        id="quote-emp-b",
        quote_number="BG-2026-002",
        title="Báo giá giải pháp cho KH B",
        customer_id=cust_b.id,
        owner_id=emp_b.id,
        total_amount=80000000.0,
        status="sent",
    )
    quote_beta = Quotation(
        id="quote-emp-beta",
        quote_number="BG-2026-003",
        title="Báo giá hệ thống cho KH Beta",
        customer_id=cust_beta.id,
        owner_id=emp_beta.id,
        total_amount=120000000.0,
        status="approved",
    )
    db_session.add_all([quote_a, quote_b, quote_beta])
    db_session.commit()

    # Sinh Bearer Token
    tokens = {
        "emp_a": create_access_token(emp_a.id, emp_a.email, emp_a.role),
        "emp_b": create_access_token(emp_b.id, emp_b.email, emp_b.role),
        "team_leader": create_access_token(team_leader.id, team_leader.email, team_leader.role),
        "emp_beta": create_access_token(emp_beta.id, emp_beta.email, emp_beta.role),
        "sales_director": create_access_token(sales_director.id, sales_director.email, sales_director.role),
        "leader_no_team": create_access_token(leader_no_team.id, leader_no_team.email, leader_no_team.role),
    }

    return {
        "users": {
            "emp_a": emp_a,
            "emp_b": emp_b,
            "team_leader": team_leader,
            "emp_beta": emp_beta,
            "sales_director": sales_director,
            "leader_no_team": leader_no_team,
        },
        "tokens": tokens,
        "customers": {
            "cust_a": cust_a,
            "cust_b": cust_b,
            "cust_beta": cust_beta,
            "cust_unassigned": cust_unassigned,
        },
        "deals": {
            "deal_a": deal_a,
            "deal_b": deal_b,
            "deal_beta": deal_beta,
        },
        "activities": {
            "act_a": act_a,
            "act_b": act_b,
            "act_beta": act_beta,
        },
        "quotations": {
            "quote_a": quote_a,
            "quote_b": quote_b,
            "quote_beta": quote_beta,
        },
    }
