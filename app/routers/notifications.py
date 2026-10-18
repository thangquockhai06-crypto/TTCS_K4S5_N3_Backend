from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.dependencies import get_current_user
from app.models.user import User
from app.models.notification import Notification
from app.repositories.notification_repository import NotificationRepository
from app.core.websocket_manager import notification_manager
from app.core.security import decode_token
from app.schemas.task import NotificationDTO

router = APIRouter(prefix="/notifications", tags=["In-app Notifications & Alerts"])


@router.get("", response_model=List[NotificationDTO], summary="Lấy danh sách thông báo của người dùng")
def get_user_notifications(
    unreadOnly: bool = Query(False, description="Chỉ lấy thông báo chưa đọc"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[NotificationDTO]:
    notifs = NotificationRepository.get_user_notifications(
        db=db,
        user_id=current_user.id,
        unread_only=unreadOnly,
        skip=skip,
        limit=limit,
    )
    return [
        NotificationDTO(
            id=n.id,
            userId=n.user_id,
            taskId=n.task_id,
            title=n.title,
            message=n.message,
            type=n.type,
            isRead=n.is_read,
            readAt=n.read_at,
            milestone=n.milestone,
            createdAt=n.created_at,
        )
        for n in notifs
    ]


@router.get("/unread-count", summary="Lấy số lượng thông báo chưa đọc")
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, int]:
    count = NotificationRepository.count_unread(db=db, user_id=current_user.id)
    return {"unreadCount": count}


@router.patch("/{notification_id}/read", response_model=NotificationDTO, summary="Đánh dấu thông báo đã đọc")
def mark_notification_as_read(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationDTO:
    notif = NotificationRepository.mark_as_read(
        db=db,
        notification_id=notification_id,
        user_id=current_user.id,
    )
    if not notif:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy thông báo.")
    return NotificationDTO(
        id=notif.id,
        userId=notif.user_id,
        taskId=notif.task_id,
        title=notif.title,
        message=notif.message,
        type=notif.type,
        isRead=notif.is_read,
        readAt=notif.read_at,
        milestone=notif.milestone,
        createdAt=notif.created_at,
    )


@router.post("/mark-all-read", summary="Đánh dấu tất cả thông báo đã đọc")
def mark_all_notifications_as_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    count = NotificationRepository.mark_all_as_read(db=db, user_id=current_user.id)
    return {"status": "success", "markedCount": count}


@router.websocket("/ws")
async def websocket_notifications(websocket: WebSocket, token: Optional[str] = Query(None)):
    """
    Kênh WebSocket nhận thông báo Real-time trực tiếp trong ứng dụng.
    Xác thực qua query param ?token=<access_token>.
    """
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_id = payload.get("sub")
    if not user_id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await notification_manager.connect(websocket, user_id)
    try:
        while True:
            # Lắng nghe ping / heartbeat từ client
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        notification_manager.disconnect(websocket, user_id)
    except Exception:
        notification_manager.disconnect(websocket, user_id)

