from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.notification import Notification


class NotificationRepository:

    @staticmethod
    def create(db: Session, notification: Notification) -> Notification:
        db.add(notification)
        db.commit()
        db.refresh(notification)
        return notification

    @staticmethod
    def get_user_notifications(
        db: Session,
        user_id: str,
        unread_only: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Notification]:
        query = db.query(Notification).filter(Notification.user_id == user_id)
        if unread_only:
            query = query.filter(Notification.is_read.is_(False))
        return query.order_by(desc(Notification.created_at)).offset(skip).limit(limit).all()

    @staticmethod
    def count_unread(db: Session, user_id: str) -> int:
        return db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        ).count()

    @staticmethod
    def mark_as_read(db: Session, notification_id: str, user_id: str) -> Optional[Notification]:
        notification = db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        ).first()
        if notification and not notification.is_read:
            notification.is_read = True
            notification.read_at = datetime.utcnow()
            db.commit()
            db.refresh(notification)
        return notification

    @staticmethod
    def mark_all_as_read(db: Session, user_id: str) -> int:
        count = db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        ).update(
            {"is_read": True, "read_at": datetime.utcnow()},
            synchronize_session=False,
        )
        db.commit()
        return count

