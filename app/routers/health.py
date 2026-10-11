"""API endpoint kiểm tra trạng thái hoạt động của hệ thống NexusCRM."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.db_health import check_db_health

router = APIRouter(prefix="/health", tags=["Health"])

@router.get("")
def health_check(db: Session = Depends(get_db)):
    db_status = check_db_health(db)
    return {
        "status": "ok" if db_status.get("status") == "healthy" else "degraded",
        "service": "NexusCRM FastAPI Backend",
        "database": db_status
    }
