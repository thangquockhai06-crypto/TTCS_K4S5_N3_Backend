"""
Migration script cập nhật CSDL cho SCRUM-91: Bảng deal_histories.
Tương thích SQLAlchemy Async / Sync và Alembic migration standards.
"""
import sys
import os

# Thêm đường dẫn project
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text, inspect
from app.database import engine, Base
from app.models.deal_history import DealHistory


def upgrade(target_engine=None):
    """
    Tạo bảng deal_histories và các chỉ mục liên quan một cách an toàn và idempotent.
    """
    eng = target_engine or engine
    print(f"[MIGRATION] Dang kiem tra va nang cap bang deal_histories tren dialect: {eng.dialect.name}...")

    # 1. Đảm bảo cấu trúc bảng bằng metadata
    Base.metadata.create_all(bind=eng)

    inspector = inspect(eng)
    table_names = inspector.get_table_names()

    if "deal_histories" in table_names:
        print("[MIGRATION] Bang deal_histories da ton tai.")
    else:
        with eng.connect() as conn:
            is_mysql = eng.dialect.name == "mysql"
            if is_mysql:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS deal_histories (
                        id VARCHAR(36) PRIMARY KEY,
                        deal_id VARCHAR(36) NOT NULL,
                        field_name VARCHAR(50) NOT NULL,
                        old_value TEXT DEFAULT NULL,
                        new_value TEXT DEFAULT NULL,
                        changed_by VARCHAR(36) DEFAULT NULL,
                        changed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_deal_histories_deal (deal_id),
                        INDEX idx_deal_histories_field (field_name),
                        INDEX idx_deal_histories_changed_at (changed_at),
                        FOREIGN KEY (deal_id) REFERENCES deals(id) ON DELETE CASCADE,
                        FOREIGN KEY (changed_by) REFERENCES users(id) ON DELETE SET NULL
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                """))
            else:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS deal_histories (
                        id VARCHAR(36) PRIMARY KEY,
                        deal_id VARCHAR(36) NOT NULL,
                        field_name VARCHAR(50) NOT NULL,
                        old_value TEXT,
                        new_value TEXT,
                        changed_by VARCHAR(36),
                        changed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (deal_id) REFERENCES deals(id) ON DELETE CASCADE,
                        FOREIGN KEY (changed_by) REFERENCES users(id) ON DELETE SET NULL
                    );
                """))
            conn.commit()
            print("[MIGRATION] Da tao thanh cong bang deal_histories.")

    # 2. Tạo chỉ mục tối ưu hóa
    with eng.connect() as conn:
        indexes_to_create = [
            ("idx_deal_histories_deal", "CREATE INDEX idx_deal_histories_deal ON deal_histories(deal_id)"),
            ("idx_deal_histories_field", "CREATE INDEX idx_deal_histories_field ON deal_histories(field_name)"),
            ("idx_deal_histories_changed_at", "CREATE INDEX idx_deal_histories_changed_at ON deal_histories(changed_at)"),
            ("idx_deal_histories_deal_changed_at", "CREATE INDEX idx_deal_histories_deal_changed_at ON deal_histories(deal_id, changed_at)"),
            ("idx_deal_histories_deal_field", "CREATE INDEX idx_deal_histories_deal_field ON deal_histories(deal_id, field_name)"),
        ]
        for idx_name, idx_sql in indexes_to_create:
            try:
                conn.execute(text(idx_sql))
                conn.commit()
                print(f"  -> Da tao chi muc: {idx_name}")
            except Exception:
                pass

    print("[MIGRATION] Hoan tat nang cap CSDL cho SCRUM-91.")


def downgrade(target_engine=None):
    """
    Hạ cấp migration (Rollback).
    """
    eng = target_engine or engine
    with eng.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS deal_histories;"))
        conn.commit()
    print("[MIGRATION] Da xoa bang deal_histories.")


if __name__ == "__main__":
    upgrade()
