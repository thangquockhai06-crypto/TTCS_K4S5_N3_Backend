from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.customer_hierarchy import (
    AssignParentRequest,
    AssignParentResponse,
    SubsidiaryItemResponse,
    GroupSummaryResponse,
)
from app.services.customer_hierarchy_service import CustomerHierarchyService

router = APIRouter(prefix="/customers", tags=["Customer Corporate Hierarchy (SCRUM-63)"])


@router.put(
    "/{customer_id}/parent",
    response_model=AssignParentResponse,
    status_code=status.HTTP_200_OK,
    summary="Gán hoặc Hủy công ty mẹ cho khách hàng (SCRUM-63)",
)
def assign_or_remove_parent(
    customer_id: str,
    request: AssignParentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssignParentResponse:
    """
    Thiết lập hoặc gỡ bỏ quan hệ công ty mẹ cho khách hàng:
    - `parent_id` = ID công ty mẹ: Gán khách hàng làm công ty con của công ty mẹ.
    - `parent_id` = null / rỗng: Gỡ bỏ liên kết quan hệ công ty mẹ.
    - Tự động kiểm tra và ngăn chặn chu trình lặp (Circular Dependency).
    """
    return CustomerHierarchyService.assign_parent(
        db=db,
        customer_id=customer_id,
        request=request,
        user=current_user,
    )


@router.get(
    "/{customer_id}/subsidiaries",
    response_model=List[SubsidiaryItemResponse],
    summary="Lấy danh sách các công ty con trực tiếp (SCRUM-63)",
)
def get_subsidiaries(
    customer_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[SubsidiaryItemResponse]:
    """
    Lấy danh sách các công ty con trực tiếp của khách hàng chỉ định,
    bao gồm mã, tên, người phụ trách, số lượng giao dịch và tổng giá trị giao dịch.
    """
    return CustomerHierarchyService.get_subsidiaries(
        db=db,
        customer_id=customer_id,
        user=current_user,
    )


@router.get(
    "/{customer_id}/group-summary",
    response_model=GroupSummaryResponse,
    summary="Lấy báo cáo tổng giá trị toàn bộ tập đoàn (Group Valuation Rollup - SCRUM-63)",
)
def get_group_summary(
    customer_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GroupSummaryResponse:
    """
    Tổng hợp giá trị toàn bộ tập đoàn (Group Rollup):
    - Doanh số riêng của công ty mẹ (own_deal_value).
    - Tổng doanh số của tất cả các công ty con (subsidiaries_deal_value).
    - Tổng giá trị toàn tập đoàn (total_group_value).
    - Danh sách chi tiết các công ty con thành viên.
    """
    return CustomerHierarchyService.get_group_summary(
        db=db,
        customer_id=customer_id,
        user=current_user,
    )
