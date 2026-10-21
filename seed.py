"""
Database Seeder Script for NexusCRM
Run this script to seed default admin account and sample data:
python seed.py
"""
import sys
import os

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Them thu muc hien tai vao sys.path de import duoc app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import engine, SessionLocal, Base
from app.models.user import User
from app.models.customer import Customer
from app.models.deal import Deal
from app.models.deal_item import DealItem
from app.models.task import Task
from app.models.activity import Activity
from app.core.security import hash_password

def seed_database():
    print("[1/3] Kiem tra cau truc bang CSDL...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        print("[2/3] Nap tai khoan nguoi dung he thong...")
        default_pwd = hash_password("Password123!")
        sample_users = [
            User(
                id="usr-admin-01",
                email="admin@nexuscrm.vn",
                password_hash=hash_password("Admin@2026"),
                full_name="Quản Trị Viên Hệ Thống",
                role="Super Admin",
                title="Quản trị viên cấp cao (System Admin)",
                department="Ban Quản Trị & Vận Hành Doanh Thu",
                workspace_name="NexusCRM Enterprise VN",
                avatar_url="https://api.dicebear.com/7.x/initials/svg?seed=QuanTriVien",
                failed_attempts=0,
                lockout_until=None,
                status="active",
                team_id="Ban Quản trị & Vận hành Doanh thu",
            ),
            User(
                id="usr-director-01",
                email="director@nexuscrm.vn",
                password_hash=default_pwd,
                full_name="Nguyễn Tuấn Anh",
                role="VP of Sales",
                title="Giám đốc Kinh doanh Toàn quốc",
                department="Khối Kinh Doanh Toàn Quốc",
                workspace_name="NexusCRM Enterprise VN",
                avatar_url="https://api.dicebear.com/7.x/initials/svg?seed=NguyenTuanAnh",
                failed_attempts=0,
                lockout_until=None,
                status="active",
                team_id="Ban Quản trị & Vận hành Doanh thu",
            ),
            User(
                id="usr-lead-01",
                email="leader@nexuscrm.vn",
                password_hash=default_pwd,
                full_name="Trần Thị Mai Phương",
                role="Sales Manager",
                title="Trưởng nhóm Kinh doanh Miền Bắc",
                department="Phòng Kinh Doanh Miền Bắc",
                workspace_name="NexusCRM Enterprise VN",
                avatar_url="https://api.dicebear.com/7.x/initials/svg?seed=TranThiMaiPhuong",
                failed_attempts=0,
                lockout_until=None,
                status="active",
                team_id="Miền Bắc (Hà Nội)",
            ),
            User(
                id="usr-sales-01",
                email="sales1@nexuscrm.vn",
                password_hash=default_pwd,
                full_name="Lê Hoàng Phúc",
                role="Account Executive",
                title="Chuyên viên Kinh doanh Doanh nghiệp",
                department="Phòng Kinh Doanh Miền Bắc",
                workspace_name="NexusCRM Enterprise VN",
                avatar_url="https://api.dicebear.com/7.x/initials/svg?seed=LeHoangPhuc",
                failed_attempts=0,
                lockout_until=None,
                status="active",
                team_id="Miền Bắc (Hà Nội)",
            ),
            User(
                id="usr-sales-02",
                email="sales2@nexuscrm.vn",
                password_hash=default_pwd,
                full_name="Vũ Hải Đăng",
                role="Account Executive",
                title="Chuyên viên Kinh doanh Khách hàng Lớn",
                department="Phòng Kinh Doanh Miền Nam",
                workspace_name="NexusCRM Enterprise VN",
                avatar_url="https://api.dicebear.com/7.x/initials/svg?seed=VuHaiDang",
                failed_attempts=0,
                lockout_until=None,
                status="active",
                team_id="Miền Nam (TP. Hồ Chí Minh)",
            ),
            User(
                id="usr-sales-03",
                email="sales3@nexuscrm.vn",
                password_hash=default_pwd,
                full_name="Đỗ Ngọc Lan",
                role="Account Executive",
                title="Chuyên viên Kinh doanh Miền Trung",
                department="Phòng Kinh Doanh Miền Trung",
                workspace_name="NexusCRM Enterprise VN",
                avatar_url="https://api.dicebear.com/7.x/initials/svg?seed=DoNgocLan",
                failed_attempts=0,
                lockout_until=None,
                status="active",
                team_id="Miền Trung (Đà Nẵng)",
            ),
            User(
                id="usr-revops-01",
                email="revops@nexuscrm.vn",
                password_hash=default_pwd,
                full_name="Hoàng Thu Trang",
                role="RevOps Lead",
                title="Trưởng bộ phận Vận hành Doanh thu",
                department="Ban Quản Trị & Vận Hành Doanh Thu",
                workspace_name="NexusCRM Enterprise VN",
                avatar_url="https://api.dicebear.com/7.x/initials/svg?seed=HoangThuTrang",
                failed_attempts=0,
                lockout_until=None,
                status="active",
                team_id="Doanh nghiệp FDI & Toàn cầu",
            ),
            User(
                id="usr-intern-01",
                email="intern@nexuscrm.vn",
                password_hash=default_pwd,
                full_name="Phạm Minh Khôi",
                role="Account Executive",
                title="Thực tập sinh Phát triển Thị trường",
                department="Kinh doanh Trực tuyến & SMB",
                workspace_name="NexusCRM Enterprise VN",
                avatar_url="https://api.dicebear.com/7.x/initials/svg?seed=PhamMinhKhoi",
                failed_attempts=0,
                lockout_until=None,
                status="active",
                team_id="Kinh doanh Trực tuyến & SMB",
            ),
        ]

        admin = None
        for u in sample_users:
            existing = db.query(User).filter(User.email == u.email).first()
            if not existing:
                db.add(u)
                db.commit()
                db.refresh(u)
                if u.email == "admin@nexuscrm.vn":
                    admin = u
                print(f"  -> Da tao tai khoan: {u.email} ({u.role})")
            else:
                if u.email == "admin@nexuscrm.vn":
                    admin = existing
                print(f"  -> Tai khoan {u.email} da ton tai.")

        print("[3/3] Nap du lieu mau khach hang, co hoi ban hang & dau moi...")
        from app.models.campaign import Campaign
        from app.models.lead import Lead, LeadRoutingRule
        from app.models.deal_item import DealItem
        from datetime import date, datetime, timedelta

        if db.query(Customer).count() == 0:
            sample_customers = [
                Customer(
                    id="cust-01",
                    full_name="Nguyen Van An",
                    email="an.nguyen@vinacorp.vn",
                    phone="0912345678",
                    company="Tap Doan VinaCorp",
                    status="active",
                    health_score=92,
                    assigned_user_id=admin.id,
                    avatar_url="https://api.dicebear.com/7.x/initials/svg?seed=NguyenVanAn",
                ),
                Customer(
                    id="cust-02",
                    full_name="Tran Thi Bich",
                    email="bich.tran@techglobal.vn",
                    phone="0987654321",
                    company="TechGlobal Solutions",
                    status="lead",
                    health_score=85,
                    assigned_user_id=admin.id,
                    avatar_url="https://api.dicebear.com/7.x/initials/svg?seed=TranThiBich",
                ),
                Customer(
                    id="cust-03",
                    full_name="Le Hoang Cuong",
                    email="cuong.le@vietlogistics.com",
                    phone="0903112233",
                    company="VietLogistics Express",
                    status="prospect",
                    health_score=78,
                    assigned_user_id=admin.id,
                    avatar_url="https://api.dicebear.com/7.x/initials/svg?seed=LeHoangCuong",
                ),
            ]
            db.add_all(sample_customers)
            db.commit()
            print("  -> Da nap 3 khach hang mau.")

        if db.query(Deal).count() == 0:
            sample_deals = [
                Deal(
                    id="deal-01",
                    title="Goi CRM Enterprise 50 Nguoi dung",
                    value=150000000.0,
                    stage="negotiation",
                    probability=80,
                    customer_id="cust-01",
                    owner_id=admin.id,
                ),
                Deal(
                    id="deal-02",
                    title="Tich hop Tong dai VoIP Doanh nghiep",
                    value=45000000.0,
                    stage="proposal",
                    probability=60,
                    customer_id="cust-02",
                    owner_id=admin.id,
                ),
                Deal(
                    id="deal-03",
                    title="Phan mem Quan ly Kho van & Van tai",
                    value=80000000.0,
                    stage="lead",
                    probability=30,
                    customer_id="cust-03",
                    owner_id=admin.id,
                ),
            ]
            db.add_all(sample_deals)
            db.commit()
            print("  -> Da nap 3 co hoi ban hang mau.")

        # Seed Campaigns
        camp1 = db.query(Campaign).filter(Campaign.id == "camp-01").first()
        if not camp1:
            camp1 = Campaign(
                id="camp-01",
                name="Chiến dịch Chuyển đổi số Doanh nghiệp 2026",
                code="CAMP-DX-2026",
                type="Google Ads",
                status="Active",
                budget=50000000.0,
                expected_revenue=300000000.0,
                start_date=date(2026, 1, 1),
                end_date=date(2026, 12, 31),
                description="Chiến dịch quảng cáo tìm kiếm Google Ads và Hội thảo Chuyển đổi số B2B.",
            )
            camp2 = Campaign(
                id="camp-02",
                name="Email Marketing Khách hàng Doanh nghiệp Vừa & Nhỏ",
                code="CAMP-EMAIL-SME",
                type="Email",
                status="Active",
                budget=15000000.0,
                expected_revenue=120000000.0,
                start_date=date(2026, 6, 1),
                end_date=date(2026, 12, 31),
                description="Chuỗi bài viết giải pháp CRM tinh gọn cho doanh nghiệp vừa và nhỏ.",
            )
            db.add_all([camp1, camp2])
            db.commit()
            print("  -> Da nap 2 chien dich tiep thi mau.")

        # Seed Routing Rules
        if db.query(LeadRoutingRule).count() == 0:
            r1 = LeadRoutingRule(
                id="rule-01",
                name="Ưu tiên Phụ trách Khu vực Miền Bắc",
                priority=1,
                rule_type="REGION",
                criterion_value="Miền Bắc",
                target_user_id=admin.id,
                is_active=True,
            )
            r2 = LeadRoutingRule(
                id="rule-02",
                name="Phân bổ Xoay vòng Round-Robin Toàn quốc",
                priority=3,
                rule_type="ROUND_ROBIN",
                target_user_id=None,
                is_active=True,
            )
            db.add_all([r1, r2])
            db.commit()
            print("  -> Da nap 2 quy tac dinh tuyen lead mau.")

        # Seed Sample Leads
        if db.query(Lead).count() == 0:
            now = datetime.utcnow()
            camp_id = camp1.id if camp1 else None
            sample_leads = [
                Lead(
                    id="lead-01",
                    full_name="Nguyễn Văn Hùng",
                    email="hung.nguyen@vinasupply.vn",
                    phone="0912888999",
                    company="Công ty CP Chuỗi Cung Ứng VinaSupply",
                    job_title="Giám Đốc Công Nghệ (CTO)",
                    source="Web Form",
                    campaign_id=camp_id,
                    region="Miền Bắc",
                    industry="Công nghệ",
                    company_size="51-200",
                    annual_budget=80000000.0,
                    score=85,
                    score_grade="Hot",
                    status="UNASSIGNED",
                    sla_deadline=now + timedelta(hours=18),
                    sla_overdue=False,
                    notes="Cần tư vấn triển khai phần mềm CRM tích hợp phân hệ kho vận trong tháng tới.",
                    created_at=now - timedelta(hours=6),
                ),
                Lead(
                    id="lead-02",
                    full_name="Phạm Thu Hương",
                    email="huong.pham@fintrade.com",
                    phone="0988776655",
                    company="Tập đoàn Đầu tư FinTrade",
                    job_title="Trưởng Phòng Kinh Doanh",
                    source="Google Ads",
                    campaign_id=camp_id,
                    region="Miền Bắc",
                    industry="Tài chính",
                    company_size="201-500",
                    annual_budget=150000000.0,
                    score=90,
                    score_grade="Hot",
                    status="ASSIGNED",
                    assigned_user_id=admin.id,
                    assigned_at=now - timedelta(hours=4),
                    sla_deadline=now + timedelta(hours=20),
                    sla_overdue=False,
                    notes="Quan tâm giải pháp CRM Cloud bảo mật và quản lý phễu cơ hội Kanban.",
                    created_at=now - timedelta(hours=4),
                ),
                Lead(
                    id="lead-03",
                    full_name="Đặng Quốc Bảo",
                    email="bao.dang@vietcargo.vn",
                    phone="0909123456",
                    company="Công ty Vận Tải VietCargo",
                    job_title="Chuyên viên Điều phối",
                    source="Excel Import",
                    campaign_id=camp_id,
                    region="Miền Nam",
                    industry="Vận tải",
                    company_size="11-50",
                    annual_budget=30000000.0,
                    score=55,
                    score_grade="Warm",
                    status="CONTACTED",
                    assigned_user_id=admin.id,
                    assigned_at=now - timedelta(days=1),
                    sla_deadline=now - timedelta(hours=2),
                    sla_overdue=True,
                    notes="Đã gọi điện lần 1, khách hàng hẹn trao đổi lại vào thứ Sáu.",
                    created_at=now - timedelta(days=2),
                ),
                Lead(
                    id="lead-04",
                    full_name="Trần Thị Lan",
                    email="lan.tran@vietnamfresh.com",
                    phone="0933221100",
                    company="Nông Sản Sạch Vietnam Fresh",
                    job_title="Giám Đốc Bán Hàng",
                    source="Web Form",
                    campaign_id=camp_id,
                    region="Miền Trung",
                    industry="Nông nghiệp",
                    company_size="11-50",
                    annual_budget=45000000.0,
                    score=65,
                    score_grade="Warm",
                    status="QUALIFIED",
                    assigned_user_id=admin.id,
                    assigned_at=now - timedelta(days=2),
                    sla_deadline=now + timedelta(hours=10),
                    sla_overdue=False,
                    notes="Đã thẩm định nhu cầu giải pháp, chuẩn bị chuyển đổi thành cơ hội bán hàng.",
                    created_at=now - timedelta(days=3),
                ),
            ]
            db.add_all(sample_leads)
            db.commit()
            print("  -> Da nap 4 dau moi (Leads) mau.")

        # Seed Deal Items for deal-01
        if db.query(DealItem).count() == 0:
            item1 = DealItem(
                id="item-01",
                deal_id="deal-01",
                product_name="Gói NexusCRM Enterprise 50 Người dùng",
                quantity=1,
                unit_price=150000000.0,
                discount_percent=0.0,
                billing_cycle="annual",
                subtotal=150000000.0,
            )
            db.add(item1)
            db.commit()
            print("  -> Da nap san pham co hoi ban hang (Deal Items) mau.")

        # Seed Tasks (Sprint 6: S6-06, S6-07, S6-09)
        if db.query(Task).count() == 0:
            today = date.today()
            sample_tasks = [
                Task(
                    id="task-01",
                    title="Chuẩn bị hợp đồng dịch vụ CRM Enterprise Q4",
                    description="Soạn thảo và rà soát các điều khoản thanh toán, bảo hành và phân quyền hệ thống.",
                    priority="high",
                    status="in_progress",
                    is_completed=False,
                    due_date=today + timedelta(days=3),
                    assignee_id="usr-admin-01",
                    creator_id="usr-admin-01",
                    customer_id="cust-01",
                    deal_id="deal-01",
                ),
                Task(
                    id="task-02",
                    title="Gọi điện tư vấn giải pháp tích hợp VoIP cho khách hàng",
                    description="Liên hệ trực tiếp giám đốc CNTT để thống nhất kiến trúc kết nối API tổng đài.",
                    priority="urgent",
                    status="pending",
                    is_completed=False,
                    due_date=today,
                    assignee_id="usr-sales-01",
                    creator_id="usr-lead-01",
                    customer_id="cust-01",
                ),
                Task(
                    id="task-03",
                    title="Gửi tài liệu kỹ thuật bảo mật & chứng chỉ ISO 27001",
                    description="Đã hoàn tất gửi tài liệu qua email cho phòng thẩm định rủi ro.",
                    priority="medium",
                    status="completed",
                    is_completed=True,
                    due_date=today - timedelta(days=2),
                    completed_at=now - timedelta(days=1),
                    assignee_id="usr-sales-01",
                    creator_id="usr-sales-01",
                    customer_id="cust-01",
                ),
                Task(
                    id="task-04",
                    title="Theo dõi phản hồi đề xuất giá phần mềm kho vận",
                    description="Nhắc nhở khách hàng về thời hạn hiệu lực của bảng chào giá ưu đãi.",
                    priority="high",
                    status="pending",
                    is_completed=False,
                    due_date=today - timedelta(days=4),
                    assignee_id="usr-sales-01",
                    creator_id="usr-lead-01",
                    deal_id="deal-01",
                ),
                Task(
                    id="task-05",
                    title="Duyệt mức chiết khấu thương vụ cho khối Doanh nghiệp FDI",
                    description="Kiểm tra tỷ suất lợi nhuận trước khi phê duyệt điều kiện chiết khấu 12%.",
                    priority="urgent",
                    status="in_progress",
                    is_completed=False,
                    due_date=today + timedelta(days=1),
                    assignee_id="usr-lead-01",
                    creator_id="usr-lead-01",
                    deal_id="deal-01",
                ),
            ]
            db.add_all(sample_tasks)
            db.commit()
            print("  -> Da nap 5 cong viec (Tasks) mau cho Sprint 6.")

        # Seed Activities (Sprint 6: S6-05)
        if db.query(Activity).count() == 0:
            sample_activities = [
                Activity(
                    id="act-01",
                    customer_id="cust-01",
                    deal_id="deal-01",
                    user_id="usr-admin-01",
                    type="call",
                    title="Cuộc gọi tư vấn quy mô 50 người dùng",
                    description="Khách hàng đồng ý lịch hẹn demo trực tiếp tuần tới.",
                    notes="Khách hàng yêu cầu hỗ trợ thêm tính năng báo cáo theo thời gian thực.",
                    created_at=now - timedelta(hours=3),
                ),
                Activity(
                    id="act-02",
                    customer_id="cust-01",
                    deal_id="deal-01",
                    user_id="usr-admin-01",
                    type="meeting",
                    title="Họp đàm phán hợp đồng triển khai giai đoạn 2",
                    description="Thống nhất phạm vi triển khai và tiến độ bàn giao trong vòng 45 ngày.",
                    notes="Phía đối tác cần bổ sung cam kết SLA 99.9% trong phụ lục hợp đồng.",
                    created_at=now - timedelta(days=1),
                ),
                Activity(
                    id="act-03",
                    customer_id="cust-01",
                    deal_id="deal-01",
                    user_id="usr-admin-01",
                    type="email",
                    title="Gửi dự thảo hợp đồng & phương án bảo mật dữ liệu",
                    description="Đã chuyển email đính kèm file PDF bản thảo hợp đồng.",
                    notes="Chờ xác nhận từ bộ phận pháp chế của khách hàng.",
                    created_at=now - timedelta(days=2),
                ),
                Activity(
                    id="act-04",
                    customer_id="cust-01",
                    deal_id="deal-01",
                    user_id="usr-lead-01",
                    type="deal_change",
                    title="Chuyển trạng thái Deal sang Đàm phán hợp đồng",
                    description="Giai đoạn được cập nhật sau buổi làm việc với Ban Giám đốc khách hàng.",
                    notes="Xác suất thành công ước tính đạt 80%.",
                    created_at=now - timedelta(days=3),
                ),
            ]
            db.add_all(sample_activities)
            db.commit()
            print("  -> Da nap 4 hoat dong (Activities) mau cho Sprint 6.")

        print("\n=======================================================")
        print(" THANH CONG: Co so du lieu nexuscrm_db da san sang! ")
        print(" Tai khoan test:")
        print("   - Email: admin@nexuscrm.vn")
        print("   - Mat khau: Admin@2026")
        print("=======================================================")

    except Exception as e:
        print(f"\n[LOI NAP DU LIEU]: {e}")
        print("Vui long kiem tra file .env xem mat khau MySQL da dung chua.")
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
