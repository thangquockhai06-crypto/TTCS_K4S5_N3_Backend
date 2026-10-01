from typing import Dict, Any, List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.repositories.customer_repository import CustomerRepository
from app.repositories.deal_repository import DealRepository

router = APIRouter(prefix="/dashboard", tags=["Dashboard Statistics"])

@router.get("/stats", summary="Lấy số liệu tổng quan doanh thu và khách hàng")
def get_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    total_customers: int = CustomerRepository.count_all(db, user=current_user)
    active_customers: int = CustomerRepository.count_by_status(db, "active", user=current_user)
    total_deals: int = DealRepository.count_all(db, user=current_user)
    pipeline_value: float = DealRepository.get_total_pipeline_value(db, user=current_user)

    return {
        "totalCustomers": total_customers,
        "activeCustomers": active_customers,
        "totalDeals": total_deals,
        "pipelineValue": pipeline_value,
        "leadConversionRate": "34.8%",
        "averageHealthScore": 88,
    }

@router.get("/notifications", summary="Lấy danh sách thông báo")
def get_notifications(
    current_user: User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    return [
        {
            "id": "notif-01",
            "title": "Hệ thống bảo vệ phiên hoạt động",
            "message": "Cơ chế bảo vệ JWT và chống Brute-force (khóa 15 phút) đã sẵn sàng.",
            "type": "security",
            "timestamp": "Vừa xong",
            "isRead": False,
        },
        {
            "id": "notif-02",
            "title": "Phiên làm việc tự động gia hạn",
            "message": "Token sẽ tự động làm mới ngầm (Silent Refresh) để không gián đoạn công việc.",
            "type": "info",
            "timestamp": "5 phút trước",
            "isRead": True,
        },
    ]
