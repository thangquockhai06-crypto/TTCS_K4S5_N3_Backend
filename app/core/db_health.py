"""Kiểm tra sức khỏe kết nối cơ sở dữ liệu và đo lường độ trễ."""
import time
from sqlalchemy import text
from sqlalchemy.orm import Session

def check_db_health(db: Session) -> dict:
    start_time = time.time()
    try:
        db.execute(text("SELECT 1"))
        latency_ms = (time.time() - start_time) * 1000
        return {
            "status": "healthy",
            "latency_ms": round(latency_ms, 2),
            "database": "sqlite_crm"
        }
    except Exception as exc:
        return {
            "status": "unhealthy",
            "error": str(exc)
        }
