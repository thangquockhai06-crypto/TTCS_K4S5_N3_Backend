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
