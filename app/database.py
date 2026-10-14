import os
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import declarative_base, sessionmaker
from typing import Generator
from app.config import settings

def create_robust_engine():
    """
    Khởi tạo SQLAlchemy Engine:
    - Thử kết nối tới MySQL theo cấu hình settings.DATABASE_URL
    - Nếu MySQL không khả dụng (chưa bật MySQL service), tự động chuyển sang SQLite cục bộ
      để đảm bảo hệ thống luôn hoạt động mà không bị lỗi 500.
    """
    if settings.DATABASE_URL.startswith("mysql"):
        try:
            # Fast socket check to immediately fallback if MySQL server is not running
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            host = "127.0.0.1"
            port = 3306
            if "@" in settings.DATABASE_URL:
                hp = settings.DATABASE_URL.split("@")[1].split("/")[0]
                if ":" in hp:
                    host, p_str = hp.split(":")
                    port = int(p_str)
                else:
                    host = hp
            res = sock.connect_ex((host, port))
            sock.close()
            if res != 0:
                raise ConnectionRefusedError(f"MySQL port not open at {host}:{port}")

            mysql_engine = create_engine(
                settings.DATABASE_URL,
                pool_pre_ping=True,
                pool_recycle=3600,
                connect_args={"connect_timeout": 1},
                echo=False,
            )
            with mysql_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            try:
                print("[DATABASE] Ket noi thanh cong toi MySQL Server.")
            except Exception:
                pass
            return mysql_engine
        except Exception as exc:
            try:
                print(f"[DATABASE WARNING] Khong the ket noi toi MySQL ({exc.__class__.__name__}).")
                print("[DATABASE INFO] Dang chuyen sang SQLite du phong (server/nexuscrm.db)...")
            except Exception:
                pass

    server_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sqlite_path = os.path.join(server_dir, "nexuscrm.db")
    return create_engine(
        f"sqlite:///{sqlite_path}",
        connect_args={"check_same_thread": False},
        echo=False,
    )

engine = create_robust_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def run_ep03_migrations(target_engine=None):
    """
    Tự động nâng cấp lược đồ CSDL cho Sprint 3 (EP-03) một cách an toàn và idempotent:
    - Bổ sung các cột mở rộng cho bảng customers: tax_code (UNIQUE), parent_customer_id,
      total_contract_value, last_interaction_at, risk_flag, risk_reason, is_deleted,
      industry, tier, location, website, notes_summary.
    - Thêm các chỉ mục tăng tốc truy vấn.
    - Tuyệt đối không xóa hay reset dữ liệu Sprint 1 & Sprint 2 hiện có.
    """
    eng = target_engine or engine
    inspector = inspect(eng)
    table_names = inspector.get_table_names()

    if "customers" in table_names:
        cols = {c["name"] for c in inspector.get_columns("customers")}
        with eng.connect() as conn:
            # 1. Bổ sung các cột nếu chưa có
            columns_to_add = [
                ("tax_code", "VARCHAR(50)"),
                ("parent_customer_id", "VARCHAR(36)"),
                ("total_contract_value", "DECIMAL(15, 2) DEFAULT 0.00"),
                ("last_interaction_at", "DATETIME"),
                ("risk_flag", "BOOLEAN DEFAULT 0"),
                ("risk_reason", "VARCHAR(255)"),
                ("is_deleted", "BOOLEAN DEFAULT 0"),
                ("industry", "VARCHAR(100) DEFAULT ''"),
                ("tier", "VARCHAR(50) DEFAULT 'Enterprise'"),
                ("location", "VARCHAR(200) DEFAULT ''"),
                ("website", "VARCHAR(150) DEFAULT ''"),
                ("notes_summary", "TEXT"),
            ]

            is_mysql = eng.dialect.name == "mysql"

            for col_name, col_def in columns_to_add:
                if col_name not in cols:
                    try:
                        conn.execute(text(f"ALTER TABLE customers ADD COLUMN {col_name} {col_def}"))
                        conn.commit()
                    except Exception as err:
                        pass

            # Cập nhật mã số thuế mẫu cho khách hàng cũ nếu còn null
            try:
                conn.execute(text("UPDATE customers SET tax_code = '0101234567' WHERE id = 'cust-01' AND tax_code IS NULL"))
                conn.execute(text("UPDATE customers SET tax_code = '0309876543' WHERE id = 'cust-02' AND tax_code IS NULL"))
                conn.execute(text("UPDATE customers SET tax_code = '0401122334' WHERE id = 'cust-03' AND tax_code IS NULL"))
                conn.execute(text("UPDATE customers SET total_contract_value = 150000000.0 WHERE id = 'cust-01' AND (total_contract_value IS NULL OR total_contract_value = 0)"))
                conn.execute(text("UPDATE customers SET total_contract_value = 45000000.0 WHERE id = 'cust-02' AND (total_contract_value IS NULL OR total_contract_value = 0)"))
                conn.execute(text("UPDATE customers SET total_contract_value = 80000000.0 WHERE id = 'cust-03' AND (total_contract_value IS NULL OR total_contract_value = 0)"))
                conn.commit()
            except Exception:
                pass

            # 2. Tạo chỉ mục
            indexes_to_create = [
                ("idx_customers_tax_code_uq", "CREATE UNIQUE INDEX idx_customers_tax_code_uq ON customers(tax_code)"),
                ("idx_customers_parent", "CREATE INDEX idx_customers_parent ON customers(parent_customer_id)"),
                ("idx_customers_last_interaction", "CREATE INDEX idx_customers_last_interaction ON customers(last_interaction_at)"),
                ("idx_customers_risk", "CREATE INDEX idx_customers_risk ON customers(risk_flag)"),
                ("idx_customers_is_deleted", "CREATE INDEX idx_customers_is_deleted ON customers(is_deleted)"),
            ]
            for idx_name, idx_sql in indexes_to_create:
                try:
                    conn.execute(text(idx_sql))
                    conn.commit()
                except Exception:
                    pass


def run_ep04_ep05_migrations(target_engine=None):
    """
    Tự động nâng cấp lược đồ CSDL cho Sprint 4 & Sprint 5 (EP-04 Lead & EP-05 Deal Management):
    - Đảm bảo các bảng mới: leads, campaigns, deal_items, lead_routing_rules đã được tạo.
    - Bổ sung các cột mở rộng cho bảng deals: campaign_id, close_date, actual_value,
      loss_reason, loss_competitor, is_stalled, last_activity_at, reassignment_reason, reassigned_from_id.
    - Bổ sung các cột mở rộng cho bảng user_import_jobs: skipped_rows, started_at, duplicate_strategy.
    - Thêm các chỉ mục tối ưu hóa tốc độ tìm kiếm.
    """
    eng = target_engine or engine
    # Tạo các bảng mới nếu chưa tồn tại
    Base.metadata.create_all(bind=eng)

    inspector = inspect(eng)
    table_names = inspector.get_table_names()

    with eng.connect() as conn:
        # 1. Bổ sung các cột mở rộng cho deals
        if "deals" in table_names:
            cols = {c["name"] for c in inspector.get_columns("deals")}
            deals_cols_to_add = [
                ("campaign_id", "VARCHAR(36)"),
                ("close_date", "DATE"),
                ("actual_value", "DECIMAL(15, 2)"),
                ("loss_reason", "VARCHAR(255)"),
                ("loss_competitor", "VARCHAR(255)"),
                ("is_stalled", "BOOLEAN DEFAULT 0"),
                ("last_activity_at", "DATETIME"),
                ("reassignment_reason", "VARCHAR(255)"),
                ("reassigned_from_id", "VARCHAR(36)"),
            ]
            for col_name, col_def in deals_cols_to_add:
                if col_name not in cols:
                    try:
                        conn.execute(text(f"ALTER TABLE deals ADD COLUMN {col_name} {col_def}"))
                        conn.commit()
                    except Exception:
                        pass

        # 2. Bổ sung các cột mở rộng cho user_import_jobs
        if "user_import_jobs" in table_names:
            cols = {c["name"] for c in inspector.get_columns("user_import_jobs")}
            jobs_cols_to_add = [
                ("skipped_rows", "INTEGER DEFAULT 0"),
                ("started_at", "DATETIME"),
                ("duplicate_strategy", "VARCHAR(20) DEFAULT 'skip'"),
            ]
            for col_name, col_def in jobs_cols_to_add:
                if col_name not in cols:
                    try:
                        conn.execute(text(f"ALTER TABLE user_import_jobs ADD COLUMN {col_name} {col_def}"))
                        conn.commit()
                    except Exception:
                        pass

        # 3. Tạo chỉ mục tối ưu hóa
        indexes_to_create = [
            ("idx_deals_campaign", "CREATE INDEX idx_deals_campaign ON deals(campaign_id)"),
            ("idx_deals_is_stalled", "CREATE INDEX idx_deals_is_stalled ON deals(is_stalled)"),
            ("idx_deals_last_activity", "CREATE INDEX idx_deals_last_activity ON deals(last_activity_at)"),
            ("idx_leads_email", "CREATE INDEX idx_leads_email ON leads(email)"),
            ("idx_leads_phone", "CREATE INDEX idx_leads_phone ON leads(phone)"),
            ("idx_leads_status", "CREATE INDEX idx_leads_status ON leads(status)"),
            ("idx_leads_score", "CREATE INDEX idx_leads_score ON leads(score)"),
            ("idx_leads_sla_overdue", "CREATE INDEX idx_leads_sla_overdue ON leads(sla_overdue)"),
            ("idx_leads_campaign", "CREATE INDEX idx_leads_campaign ON leads(campaign_id)"),
            ("idx_leads_assigned", "CREATE INDEX idx_leads_assigned ON leads(assigned_user_id)"),
        ]
        for idx_name, idx_sql in indexes_to_create:
            try:
                conn.execute(text(idx_sql))
                conn.commit()
            except Exception:
                pass


def get_db() -> Generator:
    """Dependency injects SQLAlchemy database session into FastAPI routes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

