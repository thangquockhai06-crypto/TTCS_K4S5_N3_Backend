import os
from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
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
            mysql_engine = create_engine(
                settings.DATABASE_URL,
                pool_pre_ping=True,
                pool_recycle=3600,
                connect_args={"connect_timeout": 2},
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


def run_auto_migrations(target_engine=None):
    """
    Tự động kiểm tra và thêm các cột mới vào CSDL nếu bảng đã tồn tại từ trước (Auto-migration).
    Đảm bảo tính tương thích tuyệt đối cho SCRUM-89 mà không làm mất dữ liệu hiện có.
    Hỗ trợ cả MySQL và SQLite.
    """
    eng = target_engine or engine
    try:
        from sqlalchemy import inspect
        inspector = inspect(eng)
        existing_tables = inspector.get_table_names()

        with eng.begin() as conn:
            # 1. Bảng competitors
            if "competitors" in existing_tables:
                comp_cols = [c["name"] for c in inspector.get_columns("competitors")]
                if "pricing_tier" not in comp_cols:
                    conn.execute(text("ALTER TABLE competitors ADD COLUMN pricing_tier VARCHAR(100) DEFAULT 'Trung cấp'"))
                    print("[MIGRATION] Da tu dong bo sung cot 'pricing_tier' vao bang competitors.")
                if "is_active" not in comp_cols:
                    conn.execute(text("ALTER TABLE competitors ADD COLUMN is_active BOOLEAN DEFAULT 1"))
                    print("[MIGRATION] Da tu dong bo sung cot 'is_active' vao bang competitors.")
                if "updated_at" not in comp_cols:
                    conn.execute(text("ALTER TABLE competitors ADD COLUMN updated_at DATETIME"))
                    print("[MIGRATION] Da tu dong bo sung cot 'updated_at' vao bang competitors.")

            # 2. Bảng win_loss_reasons
            if "win_loss_reasons" in existing_tables:
                reason_cols = [c["name"] for c in inspector.get_columns("win_loss_reasons")]
                if "usage_count" not in reason_cols:
                    conn.execute(text("ALTER TABLE win_loss_reasons ADD COLUMN usage_count INTEGER DEFAULT 0"))
                    print("[MIGRATION] Da tu dong bo sung cot 'usage_count' vao bang win_loss_reasons.")
                if "updated_at" not in reason_cols:
                    conn.execute(text("ALTER TABLE win_loss_reasons ADD COLUMN updated_at DATETIME"))
                    print("[MIGRATION] Da tu dong bo sung cot 'updated_at' vao bang win_loss_reasons.")
    except Exception as exc:
        print(f"[MIGRATION WARNING] Khong the tu dong cap nhat cot CSDL: {exc}")

def ensure_schema_compatibility() -> None:
    """Add columns introduced after an existing database was initialized."""
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("users")}
    if "avatar_thumbnail_url" not in columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE users ADD COLUMN avatar_thumbnail_url TEXT"))

def get_db() -> Generator:
    """Dependency injects SQLAlchemy database session into FastAPI routes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
