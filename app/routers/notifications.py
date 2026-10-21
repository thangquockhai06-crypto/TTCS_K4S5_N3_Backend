from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.notification import NotificationDTO, NotificationListResponseDTO
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["In-App Notifications (S7-08)"])


@router.get("", response_model=NotificationListResponseDTO, summary="Lấy danh sách thông báo in-app kèm số lượng chưa đọc (S7-08)")
def get_my_notifications(
    unreadOnly: bool = Query(False, description="Chỉ lấy thông báo chưa đọc"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationListResponseDTO:
    items, unread_count, total = NotificationService.get_notifications(
        db=db,
        user=current_user,
        unread_only=unreadOnly,
        skip=skip,
        limit=limit,
    )
    return NotificationListResponseDTO(items=items, unreadCount=unread_count, total=total)


@router.get("/unread-count", summary="Lấy số lượng thông báo chưa đọc (S7-08)")
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _, unread_count, _ = NotificationService.get_notifications(
        db=db,
        user=current_user,
        unread_only=True,
        skip=0,
        limit=1,
    )
    return {"unreadCount": unread_count}


@router.post("/{notification_id}/read", response_model=NotificationDTO, summary="Đánh dấu một thông báo đã đọc (S7-08)")
def mark_notification_read(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationDTO:
    return NotificationService.mark_as_read(db=db, notification_id=notification_id, user=current_user)


@router.post("/mark-all-read", summary="Đánh dấu toàn bộ thông báo đã đọc (S7-08)")
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count = NotificationService.mark_all_read(db=db, user=current_user)
    return {"success": True, "markedCount": count}
