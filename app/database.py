import os
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import declarative_base, sessionmaker

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


def run_ep06_migrations(target_engine=None):
    """
    Tự động nâng cấp lược đồ CSDL cho Sprint 6:
    - S6-05 & S6-08: Mở rộng bảng activities với deal_id và notes.
    - S6-06, S6-07, S6-09: Đảm bảo bảng tasks đã được tạo kèm chỉ mục tối ưu hóa.
    """
    eng = target_engine or engine
    Base.metadata.create_all(bind=eng)

    inspector = inspect(eng)
    table_names = inspector.get_table_names()

    with eng.connect() as conn:
        # 1. Bổ sung các cột mở rộng cho activities
        if "activities" in table_names:
            cols = {c["name"] for c in inspector.get_columns("activities")}
            activities_cols = [
                ("deal_id", "VARCHAR(36)"),
                ("notes", "TEXT"),
            ]
            for col_name, col_def in activities_cols:
                if col_name not in cols:
                    try:
                        conn.execute(text(f"ALTER TABLE activities ADD COLUMN {col_name} {col_def}"))
                        conn.commit()
                    except Exception:
                        pass

        # 2. Tạo chỉ mục tối ưu hóa cho Sprint 6
        indexes_to_create = [
            ("idx_activities_deal", "CREATE INDEX idx_activities_deal ON activities(deal_id)"),
            ("idx_tasks_assignee", "CREATE INDEX idx_tasks_assignee ON tasks(assignee_id)"),
            ("idx_tasks_status", "CREATE INDEX idx_tasks_status ON tasks(status)"),
            ("idx_tasks_due_date", "CREATE INDEX idx_tasks_due_date ON tasks(due_date)"),
            ("idx_tasks_is_completed", "CREATE INDEX idx_tasks_is_completed ON tasks(is_completed)"),
            ("idx_tasks_creator", "CREATE INDEX idx_tasks_creator ON tasks(creator_id)"),
        ]
        for idx_name, idx_sql in indexes_to_create:
            try:
                conn.execute(text(idx_sql))
                conn.commit()
            except Exception:
                pass


def run_ep07_migrations(target_engine=None):
    """
    Tự động nâng cấp lược đồ CSDL cho Sprint 7 (S7-01 -> S7-09):
    - Đảm bảo các bảng mới: quote_items, quote_approval_history, contracts, contract_items,
      pdf_templates, notifications, automation_rules, automation_logs đã được tạo.
    - Bổ sung các cột mở rộng cho bảng quotations: deal_id, version, is_effective, parent_quote_id,
      subtotal, total_discount_amount, total_discount_percent, vat_amount, grand_total,
      discount_threshold_percent, requires_approval, approval_level, payment_terms, delivery_terms,
      notes, access_token, template_id.
    - Thêm chỉ mục tối ưu hóa tốc độ tìm kiếm và toàn vẹn dữ liệu.
    - Nạp sẵn các mẫu PDF và quy tắc tự động hóa IF–THEN mặc định nếu chưa có.
    """
    eng = target_engine or engine
    Base.metadata.create_all(bind=eng)

    inspector = inspect(eng)
    table_names = inspector.get_table_names()

    with eng.connect() as conn:
        # 1. Bổ sung các cột cho bảng quotations
        if "quotations" in table_names:
            cols = {c["name"] for c in inspector.get_columns("quotations")}
            quotations_cols = [
                ("deal_id", "VARCHAR(36)"),
                ("version", "INTEGER DEFAULT 1"),
                ("is_effective", "BOOLEAN DEFAULT 1"),
                ("parent_quote_id", "VARCHAR(36)"),
                ("subtotal", "DECIMAL(15, 2) DEFAULT 0.00"),
                ("total_discount_amount", "DECIMAL(15, 2) DEFAULT 0.00"),
                ("total_discount_percent", "DECIMAL(5, 2) DEFAULT 0.00"),
                ("vat_amount", "DECIMAL(15, 2) DEFAULT 0.00"),
                ("grand_total", "DECIMAL(15, 2) DEFAULT 0.00"),
                ("discount_threshold_percent", "DECIMAL(5, 2) DEFAULT 15.00"),
                ("requires_approval", "BOOLEAN DEFAULT 0"),
                ("approval_level", "VARCHAR(50)"),
                ("payment_terms", "VARCHAR(255)"),
                ("delivery_terms", "VARCHAR(255)"),
                ("notes", "TEXT"),
                ("access_token", "VARCHAR(64)"),
                ("template_id", "VARCHAR(36)"),
            ]
            for col_name, col_def in quotations_cols:
                if col_name not in cols:
                    try:
                        conn.execute(text(f"ALTER TABLE quotations ADD COLUMN {col_name} {col_def}"))
                        conn.commit()
                    except Exception:
                        pass

        # 2. Tạo chỉ mục tối ưu hóa Sprint 7
        indexes_to_create = [
            ("idx_quotations_deal", "CREATE INDEX idx_quotations_deal ON quotations(deal_id)"),
            ("idx_quotations_token", "CREATE UNIQUE INDEX idx_quotations_token ON quotations(access_token)"),
            ("idx_quotations_version", "CREATE INDEX idx_quotations_version ON quotations(version)"),
            ("idx_quotations_effective", "CREATE INDEX idx_quotations_effective ON quotations(is_effective)"),
            ("idx_contracts_number", "CREATE UNIQUE INDEX idx_contracts_number ON contracts(contract_number)"),
            ("idx_contracts_expiry", "CREATE INDEX idx_contracts_expiry ON contracts(expiry_date)"),
            ("idx_contracts_customer", "CREATE INDEX idx_contracts_customer ON contracts(customer_id)"),
            ("idx_contracts_deal", "CREATE INDEX idx_contracts_deal ON contracts(deal_id)"),
            ("idx_notifications_user", "CREATE INDEX idx_notifications_user ON notifications(user_id)"),
            ("idx_notifications_unread", "CREATE INDEX idx_notifications_unread ON notifications(user_id, is_read)"),
            ("idx_automation_rules_active", "CREATE INDEX idx_automation_rules_active ON automation_rules(is_active)"),
        ]
        for idx_name, idx_sql in indexes_to_create:
            try:
                conn.execute(text(idx_sql))
                conn.commit()
            except Exception:
                pass

        # 3. Nạp mẫu PDF cấu hình mặc định (S7-05) nếu bảng chưa có bản ghi
        try:
            res = conn.execute(text("SELECT COUNT(*) FROM pdf_templates")).scalar()
            if res == 0:
                conn.execute(text("""
                    INSERT INTO pdf_templates (
                        id, name, template_type, logo_url, company_name, company_tax_code,
                        company_address, company_phone, company_email, company_bank_account,
                        header_text, footer_text, terms_and_conditions, is_default, created_at, updated_at
                    ) VALUES (
                        'tpl-quote-default',
                        'Mẫu Báo giá Doanh nghiệp Chuẩn 2026',
                        'quotation',
                        '/assets/logo.svg',
                        'CÔNG TY CỔ PHẦN CÔNG NGHỆ NEXUS VIỆT NAM',
                        '0108889999',
                        'Tòa nhà Nexus Tower, 180 Cầu Giấy, Hà Nội',
                        '1900 6868 - 024 3799 8888',
                        'contact@nexuscrm.vn',
                        '19036888899999 - Techcombank Chi nhánh Thăng Long',
                        'BÁO GIÁ GIẢI PHÁP PHẦN MỀM & DỊCH VỤ CÔNG NGHỆ THÔNG TIN',
                        'Báo giá có giá trị theo thời hạn ghi trên văn bản. Mọi thắc mắc xin vui lòng liên hệ chuyên viên phụ trách.',
                        '1. Báo giá đã bao gồm thuế GTGT theo quy định hiện hành.\n2. Phương thức thanh toán: Chuyển khoản ngân hàng 100% trong vòng 15 ngày kể từ ngày ký biên bản nghiệm thu.\n3. Thời gian triển khai: Trong vòng 05 ngày làm việc kể từ khi ký kết hợp đồng.',
                        1,
                        CURRENT_TIMESTAMP,
                        CURRENT_TIMESTAMP
                    ),
                    (
                        'tpl-contract-default',
                        'Mẫu Hợp đồng Kinh tế & Dịch vụ Phần mềm',
                        'contract',
                        '/assets/logo.svg',
                        'CÔNG TY CỔ PHẦN CÔNG NGHỆ NEXUS VIỆT NAM',
                        '0108889999',
                        'Tòa nhà Nexus Tower, 180 Cầu Giấy, Hà Nội',
                        '1900 6868 - 024 3799 8888',
                        'contact@nexuscrm.vn',
                        '19036888899999 - Techcombank Chi nhánh Thăng Long',
                        'CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nĐộc lập - Tự do - Hạnh phúc\n---\nHỢP ĐỒNG CUNG CẤP DỊCH VỤ PHẦN MỀM',
                        'Hợp đồng được lập thành 02 bản có giá trị pháp lý như nhau, mỗi bên giữ 01 bản.',
                        '1. Bên B cam kết bảo mật 100% dữ liệu của Bên A trên hạ tầng đạt chuẩn ISO 27001.\n2. Hai bên cam kết thực hiện đúng các điều khoản trong hợp đồng. Mọi tranh chấp sẽ được giải quyết tại Tòa án nhân dân có thẩm quyền tại Hà Nội.',
                        1,
                        CURRENT_TIMESTAMP,
                        CURRENT_TIMESTAMP
                    )
                """))
                conn.commit()
        except Exception:
            pass

        # 4. Nạp quy tắc tự động hóa IF–THEN mẫu (S7-09) nếu bảng chưa có bản ghi
        try:
            rule_cnt = conn.execute(text("SELECT COUNT(*) FROM automation_rules")).scalar()
            if rule_cnt == 0:
                conn.execute(text("""
                    INSERT INTO automation_rules (
                        id, name, description, is_active, trigger_entity, trigger_event,
                        conditions, action_type, action_config, created_at, updated_at
                    ) VALUES (
                        'rule-01-deal-won',
                        'Tự động tạo nhiệm vụ bàn giao khi Deal thành công (Won)',
                        'Khi cơ hội bán hàng chuyển sang giai đoạn Won, hệ thống tự động tạo nhiệm vụ chuẩn bị hợp đồng và triển khai.',
                        1,
                        'deal',
                        'status_changed',
                        '{"field": "stage", "operator": "equals", "value": "won"}',
                        'create_task',
                        '{"title": "Chuẩn bị hợp đồng & Bàn giao kỹ thuật", "priority": "high", "due_days": 2, "description": "Deal đã thắng. Tiến hành lập hợp đồng và liên hệ khách hàng khởi tạo hệ thống."}',
                        CURRENT_TIMESTAMP,
                        CURRENT_TIMESTAMP
                    ),
                    (
                        'rule-02-quote-approved',
                        'Tự động gửi thông báo khi Báo giá được phê duyệt',
                        'Khi báo giá được Trưởng nhóm hoặc Giám đốc duyệt, gửi thông báo ngay cho chuyên viên phụ trách để gửi khách hàng.',
                        1,
                        'quotation',
                        'status_changed',
                        '{"field": "status", "operator": "equals", "value": "approved"}',
                        'send_notification',
                        '{"title": "Báo giá {quote_number} đã được duyệt thành công", "description": "Báo giá của bạn đã được phê duyệt. Bạn có thể phát hành và gửi link truy cập cho khách hàng."}',
                        CURRENT_TIMESTAMP,
                        CURRENT_TIMESTAMP
                    ),
                    (
                        'rule-03-deal-stalled',
                        'Cảnh báo cơ hội bán hàng ứ đọng quá 14 ngày',
                        'Khi cơ hội không có tương tác nào trong hơn 14 ngày, tự động nhắc nhở chuyên viên kinh doanh cập nhật tiến độ.',
                        1,
                        'deal',
                        'time_condition',
                        '{"field": "is_stalled", "operator": "equals", "value": true}',
                        'send_notification',
                        '{"title": "Cơ hội {title} đang bị ứ đọng", "description": "Cơ hội này chưa có hoạt động nào trong 14 ngày qua. Vui lòng liên hệ lại khách hàng hoặc cập nhật trạng thái."}',
                        CURRENT_TIMESTAMP,
                        CURRENT_TIMESTAMP
                    )
                """))
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

