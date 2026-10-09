from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.scope import DataScope, get_user_data_scope
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.repositories.customer_repository import CustomerRepository
from app.repositories.deal_repository import DealRepository
from app.services.kpi_service import KPIService

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


@router.get("/kpi/won-value", summary="Get won sales value for an owner and signed-date period")
def get_won_value(
    periodStart: date = Query(...),
    periodEnd: date = Query(...),
    ownerId: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    owner_id = ownerId or current_user.id
    scope = get_user_data_scope(current_user)
    target_owner = db.query(User).filter(User.id == owner_id).first()
    if target_owner is None:
        raise HTTPException(status_code=404, detail="Owner not found.")
    if scope == DataScope.OWN and owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="You cannot view another owner's KPI.")
    if scope == DataScope.TEAM and target_owner.team_id != current_user.team_id:
        raise HTTPException(status_code=403, detail="You cannot view KPI outside your team.")
    try:
        total = KPIService.get_won_value_for_owner(
            db=db,
            owner_id=owner_id,
            period_start=periodStart,
            period_end=periodEnd,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "ownerId": owner_id,
        "periodStart": periodStart.isoformat(),
        "periodEnd": periodEnd.isoformat(),
        "wonValue": total,
        "periodRule": "Inclusive signed_date range; reopened deals are excluded until closed again.",
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
