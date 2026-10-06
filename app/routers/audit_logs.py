from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services.audit_log_service import AuditLogService
from app.schemas.audit_log import AuditLogPaginatedResponse
from app.services.catalog_item_service import is_sales_director

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


@router.get("", response_model=AuditLogPaginatedResponse, summary="Xem nhật ký kiểm toán hệ thống (S2-04)")
def get_audit_logs(
    performed_by: Optional[str] = Query(None, description="Lọc theo người thực hiện (ID, Tên hoặc Email)"),
    target_type: Optional[str] = Query(None, description="Lọc theo loại đối tượng (deal, customer, user, quota, all)"),
    start_date: Optional[datetime] = Query(None, description="Lọc từ ngày (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="Lọc đến ngày (ISO format)"),
    page: int = Query(1, ge=1, description="Trang hiện tại"),
    limit: int = Query(20, ge=1, le=100, description="Số bản ghi mỗi trang"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AuditLogPaginatedResponse:
    service = AuditLogService(db)
    return service.get_audit_logs(
        performed_by=performed_by,
        target_type=target_type,
        start_date=start_date,
        end_date=end_date,
        page=page,
        limit=limit,
        include_cost_fields=is_sales_director(current_user),
    )
