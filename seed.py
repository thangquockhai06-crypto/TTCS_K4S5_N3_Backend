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

from app.database import engine, SessionLocal, Base, run_auto_migrations
from app.models.user import User
from app.models.customer import Customer
from app.models.deal import Deal
from app.models.win_loss import WinLossReason, Competitor
from app.core.security import hash_password

def seed_database():
    print("[1/4] Kiem tra cau truc bang CSDL & Auto-migration...")
    Base.metadata.create_all(bind=engine)
    run_auto_migrations(target_engine=engine)

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

        print("[3/3] Nap du lieu mau khach hang & co hoi ban hang (Deals)...")
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
            print("  -> Da nap thanh cong 3 khach hang & 3 co hoi ban hang mau.")
        else:
            print("  -> Du lieu khach hang da co san.")

        print("[4/4] Nap du lieu danh muc Ly do Thang/Thua & Doi thu canh tranh (SCRUM-89)...")
        if db.query(WinLossReason).count() == 0:
            reasons = [
                WinLossReason(
                    result_type="WON",
                    code="PRICE_COMPETITIVE",
                    reason="Chính sách giá & Chiết khấu cạnh tranh vượt trội",
                    description="Báo giá tốt hơn đối thủ từ 10-15% kèm chính sách trả góp linh hoạt",
                    is_active=True,
                    usage_count=48,
                ),
                WinLossReason(
                    result_type="WON",
                    code="FEATURE_RICH",
                    reason="Tính năng phân quyền & Tùy biến đa cấp đáp ứng 100% nghiệp vụ",
                    description="Khách hàng đánh giá rất cao phân hệ trường tùy chỉnh và sơ đồ cây phòng ban",
                    is_active=True,
                    usage_count=36,
                ),
                WinLossReason(
                    result_type="WON",
                    code="SUPPORT_EXCELLENT",
                    reason="Dịch vụ Onboarding & Hỗ trợ kỹ thuật 24/7 tận tâm",
                    description="Cam kết SLA phản hồi dưới 15 phút và hỗ trợ trực tiếp tại doanh nghiệp",
                    is_active=True,
                    usage_count=24,
                ),
                WinLossReason(
                    result_type="LOST",
                    code="BUDGET_CUT",
                    reason="Khách hàng cắt giảm ngân sách đầu tư CNTT năm nay",
                    description="Dự án bị hoãn sang quý sau do biến động kinh doanh nội bộ khách hàng",
                    is_active=True,
                    usage_count=19,
                ),
                WinLossReason(
                    result_type="LOST",
                    code="CHOSE_COMPETITOR",
                    reason="Khách hàng chọn đối thủ có giá thành thấp hơn",
                    description="Khách hàng chấp nhận giải pháp ít tính năng hơn để tiết kiệm chi phí ban đầu",
                    is_active=True,
                    usage_count=14,
                ),
                WinLossReason(
                    result_type="LOST",
                    code="INTERNAL_BUILD",
                    reason="Khách hàng quyết định tự xây dựng phần mềm nội bộ (In-house)",
                    description="Đội ngũ IT nội bộ của khách hàng tiếp quản dự án",
                    is_active=True,
                    usage_count=5,
                ),
            ]
            db.add_all(reasons)
            db.commit()
            print("  -> Da nap thanh cong 6 ly do Thang/Thua mac dinh.")
        else:
            print("  -> Danh muc ly do Thang/Thua da co san.")
        required_lost_reasons = [
            ("PRICE_TOO_HIGH", "Giá quá cao", "Giá đề xuất vượt ngân sách hoặc kỳ vọng của khách hàng."),
            ("NO_DECISION", "Không có quyết định", "Khách hàng không ra quyết định trong thời hạn dự kiến."),
            ("BAD_TIMING", "Thời điểm không phù hợp", "Ngân sách hoặc ưu tiên của khách hàng chưa phù hợp."),
            ("PRODUCT_GAP", "Thiếu tính năng sản phẩm", "Sản phẩm chưa đáp ứng một yêu cầu quan trọng."),
            ("OTHER", "Khác", "Lý do khác; bắt buộc ghi chú chi tiết."),
        ]
        existing_reason_codes = {
            code
            for (code,) in db.query(WinLossReason.code)
            .filter(WinLossReason.result_type == "LOST")
            .all()
        }
        missing_reasons = [
            WinLossReason(
                result_type="LOST",
                code=code,
                reason=reason,
                description=description,
                is_active=True,
                usage_count=0,
            )
            for code, reason, description in required_lost_reasons
            if code not in existing_reason_codes
        ]
        if missing_reasons:
            db.add_all(missing_reasons)
            db.commit()


        if db.query(Competitor).count() == 0:
            competitors = [
                Competitor(
                    name="Salesforce CRM Enterprise",
                    website="https://www.salesforce.com",
                    pricing_tier="Rất cao (2.500.000đ/user/tháng)",
                    strengths="Thương hiệu toàn cầu, hệ sinh thái AppExchange phong phú",
                    weaknesses="Chi phí triển khai cực kỳ đắt đỏ, giao diện tiếng Anh khó sử dụng",
                    win_rate=68.0,
                    is_active=True,
                ),
                Competitor(
                    name="HubSpot Sales Hub",
                    website="https://www.hubspot.com",
                    pricing_tier="Trung bình - Cao (1.200.000đ/user/tháng)",
                    strengths="Marketing Automation mạnh mẽ, giao diện trực quan",
                    weaknesses="Tính năng phân quyền sâu và quản lý giá sàn còn hạn chế",
                    win_rate=74.0,
                    is_active=True,
                ),
                Competitor(
                    name="Zoho CRM Plus",
                    website="https://www.zoho.com",
                    pricing_tier="Trung bình (650.000đ/user/tháng)",
                    strengths="Nhiều phân hệ tích hợp, chi phí bản quyền ban đầu cạnh tranh",
                    weaknesses="Tốc độ tải chậm tại Việt Nam, quy trình tùy biến phễu phức tạp",
                    win_rate=82.0,
                    is_active=True,
                ),
            ]
            db.add_all(competitors)
            db.commit()
            print("  -> Da nap thanh cong 3 doi thu canh tranh mac dinh.")
        else:
            print("  -> Danh muc doi thu canh tranh da co san.")

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
