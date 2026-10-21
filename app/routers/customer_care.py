from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.customer_care import (
    CustomerCareFilterParams,
    CustomerCareListResponse,
    QuickContactRequest,
    QuickContactResponse,
)
from app.services.customer_care_service import CustomerCareService

router = APIRouter(prefix="/customer-care", tags=["Customer Care Management"])


@router.get(
    "/overdue-followups",
    response_model=CustomerCareListResponse,
    summary="Lấy danh sách khách hàng cần chăm sóc định kỳ (SCRUM-67)",
)
def get_overdue_followups(
    days_inactive: int = Query(30, ge=1, description="Số ngày không tương tác N"),
    search: Optional[str] = Query(None, description="Tìm theo tên khách hàng, mã số thuế hoặc SĐT"),
    page: int = Query(1, ge=1, description="Trang hiện tại"),
    page_size: int = Query(20, ge=1, le=100, description="Số lượng bản ghi trên một trang"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CustomerCareListResponse:
    """
    Trả về danh sách khách hàng đã ký hợp đồng nhưng chưa được tương tác trong N ngày.
    - Sắp xếp ưu tiên theo tổng giá trị hợp đồng giảm dần (`total_contract_value DESC`).
    - Phân quyền Record-level (RBAC):
      * CS, DIRECTOR: Toàn hệ thống.
      * TEAM_LEAD: Khách hàng trong nhóm.
      * SALES_REP: Khách hàng do mình trực tiếp phụ trách.
    """
    params = CustomerCareFilterParams(
        days_inactive=days_inactive,
        search=search,
        page=page,
        page_size=page_size,
    )
    return CustomerCareService.get_overdue_followups(
        db=db,
        current_user=current_user,
        filter_params=params,
    )


@router.post(
    "/{customer_id}/quick-contact",
    response_model=QuickContactResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Đánh dấu đã liên hệ nhanh trên danh sách (SCRUM-67)",
)
def record_quick_contact(
    customer_id: str,
    request: QuickContactRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QuickContactResponse:
    """
    Thao tác 1 chạm cho phép người dùng click nhanh 'Đã liên hệ' ngay tại dòng của khách hàng.
    - Tự động tạo một bản ghi Activity mới (`CALL`, `MEETING`, `NOTE`, `EMAIL`).
    - Gán `user_id = current_user.id`, thời gian là hiện tại.
    - Cập nhật lại mốc tương tác gần nhất, đưa khách hàng ra khỏi danh sách cần chăm sóc.
    """
    return CustomerCareService.record_quick_contact(
        db=db,
        current_user=current_user,
        customer_id=customer_id,
        request=request,
    )
