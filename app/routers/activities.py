from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.activity import Activity
from app.schemas.activity import ActivityDTO, CreateActivityDTO
from app.services.activity_service import ActivityService
from app.core.export import export_to_excel

router = APIRouter(prefix="/activities", tags=["Activities Management"])


@router.get("", response_model=List[ActivityDTO], summary="Lấy danh sách các hoạt động")
def get_activities(
    search: Optional[str] = Query(None, description="Tìm kiếm theo tiêu đề hoặc mô tả"),
    type: Optional[str] = Query(None, description="Lọc theo loại: call, meeting, email, deal_change, status_change"),
    customerId: Optional[str] = Query(None, description="Lọc theo khách hàng"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[ActivityDTO]:
    activities, _ = ActivityService.get_activities(
        db=db,
        user=current_user,
        search=search,
        activity_type=type,
        customer_id=customerId,
        skip=skip,
        limit=limit,
    )
    return [
        ActivityDTO(
            id=a.id,
            customerId=a.customer_id,
            userId=a.user_id,
            type=a.type,
            title=a.title,
            description=a.description,
            createdAt=a.created_at.isoformat() if a.created_at else None,
        )
        for a in activities
    ]


@router.get("/export", summary="Xuất danh sách hoạt động ra Excel (.xlsx)")
def export_activities(
    search: Optional[str] = Query(None, description="Tìm kiếm theo tiêu đề hoặc mô tả"),
    type: Optional[str] = Query(None, description="Lọc theo loại hoạt động"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Xuất danh sách hoạt động ra Excel tuân thủ Data Scope."""
    activities = ActivityService.get_activities_for_export(
        db=db,
        user=current_user,
        search=search,
        activity_type=type,
    )
    headers = ["Mã Hoạt Động", "Mã KH", "Người thực hiện", "Loại", "Tiêu đề", "Mô tả", "Thời gian"]
    rows = [
        [
            a.id,
            a.customer_id,
            a.user_id,
            a.type,
            a.title,
            a.description or "",
            a.created_at.strftime("%Y-%m-%d %H:%M:%S") if a.created_at else "",
        ]
        for a in activities
    ]
    return export_to_excel(
        sheet_title="HoatDong",
        headers=headers,
        rows=rows,
        filename="danh_sach_hoat_dong.xlsx",
    )


@router.post("", response_model=ActivityDTO, status_code=status.HTTP_201_CREATED, summary="Tạo mới hoạt động")
def create_activity(
    dto: CreateActivityDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ActivityDTO:
    activity: Activity = ActivityService.create_activity(db=db, dto=dto, user=current_user)
    return ActivityDTO(
        id=activity.id,
        customerId=activity.customer_id,
        userId=activity.user_id,
        type=activity.type,
        title=activity.title,
        description=activity.description,
        createdAt=activity.created_at.isoformat() if activity.created_at else None,
    )


@router.get("/{activity_id}", response_model=ActivityDTO, summary="Xem chi tiết hoạt động")
def get_activity_detail(
    activity_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ActivityDTO:
    activity: Optional[Activity] = ActivityService.get_activity_by_id(
        db=db,
        activity_id=activity_id,
        user=current_user,
    )
    if not activity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy hoạt động.")
    return ActivityDTO(
        id=activity.id,
        customerId=activity.customer_id,
        userId=activity.user_id,
        type=activity.type,
        title=activity.title,
        description=activity.description,
        createdAt=activity.created_at.isoformat() if activity.created_at else None,
    )
