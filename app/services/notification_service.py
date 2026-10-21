import uuid
from datetime import datetime
from typing import List, Tuple, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import NotificationDTO, CreateNotificationDTO


def calculate_time_ago(dt: datetime) -> str:
    now = datetime.utcnow()
    diff = now - dt
    seconds = int(diff.total_seconds())
    if seconds < 60:
        return "Vừa xong"
    elif seconds < 3600:
        return f"{seconds // 60} phút trước"
    elif seconds < 86400:
        return f"{seconds // 3600} giờ trước"
    elif seconds < 604800:
        return f"{seconds // 86400} ngày trước"
    return dt.strftime("%d/%m/%Y")


class NotificationService:
    """
    S7-08: Dịch vụ Thông báo In-App Bất đồng bộ.
    Phát thông báo cho các sự kiện: phân bổ lead, duyệt báo giá, phản hồi báo giá,
    giao việc và cơ hội bị ứ đọng.
    """

    @staticmethod
    def create_notification(
        db: Session,
        user_id: str,
        notif_type: str,
        title: str,
        description: str,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        link_url: Optional[str] = None,
    ) -> Notification:
        notif = Notification(
            id=str(uuid.uuid4()),
            user_id=user_id,
            type=notif_type,
            title=title,
            description=description,
            target_type=target_type,
            target_id=target_id,
            link_url=link_url,
            is_read=False,
            created_at=datetime.utcnow(),
        )
        db.add(notif)
        db.commit()
        db.refresh(notif)
        return notif

    @classmethod
    def notify_lead_assigned(cls, db: Session, lead_id: str, lead_name: str, assignee_id: str, assigner_name: str):
        return cls.create_notification(
            db=db,
            user_id=assignee_id,
            notif_type="lead_assigned",
            title="Bạn được phân bổ Lead mới",
            description=f"{assigner_name} vừa phân bổ khách hàng tiềm năng '{lead_name}' cho bạn.",
            target_type="lead",
            target_id=lead_id,
            link_url=f"/leads/{lead_id}/edit",
        )

    @classmethod
    def notify_quote_pending_approval(cls, db: Session, quote_id: str, quote_number: str, title: str, approval_level: str, creator_name: str):
        # Tìm những người có quyền duyệt (Team Leader hoặc Director/Admin)
        role_search = "Leader" if approval_level == "team_leader" else "Director"
        approvers = db.query(User).filter(
            (User.role.ilike(f"%{role_search}%")) | (User.role.ilike("%Admin%"))
        ).all()
        for appr in approvers:
            cls.create_notification(
                db=db,
                user_id=appr.id,
                notif_type="quote_pending_approval",
                title=f"Báo giá {quote_number} cần phê duyệt",
                description=f"{creator_name} đã đệ trình báo giá '{title}' vượt mức chiết khấu thông thường. Cần cấp {approval_level} duyệt.",
                target_type="quotation",
                target_id=quote_id,
                link_url="/quotes/approvals",
            )

    @classmethod
    def notify_quote_customer_response(cls, db: Session, quote_id: str, quote_number: str, owner_id: str, action: str, comment: Optional[str]):
        act_text = "CHẤP NHẬN" if action == "accepted" else "TỪ CHỐI"
        desc = f"Khách hàng vừa phản hồi {act_text} báo giá {quote_number}."
        if comment:
            desc += f" Ý kiến: '{comment}'"
        return cls.create_notification(
            db=db,
            user_id=owner_id,
            notif_type="quote_customer_response",
            title=f"Khách hàng {act_text} báo giá {quote_number}",
            description=desc,
            target_type="quotation",
            target_id=quote_id,
            link_url=f"/deals",
        )

    @classmethod
    def notify_task_assigned(cls, db: Session, task_id: str, task_title: str, assignee_id: str, creator_name: str):
        return cls.create_notification(
            db=db,
            user_id=assignee_id,
            notif_type="task_assigned",
            title="Bạn được giao một nhiệm vụ mới",
            description=f"{creator_name} vừa phân công nhiệm vụ: '{task_title}' cho bạn.",
            target_type="task",
            target_id=task_id,
            link_url="/tasks",
        )

    @classmethod
    def notify_stalled_deal(cls, db: Session, deal_id: str, deal_title: str, owner_id: str):
        return cls.create_notification(
            db=db,
            user_id=owner_id,
            notif_type="stalled_opportunity",
            title="Cảnh báo: Cơ hội bán hàng bị ứ đọng",
            description=f"Cơ hội '{deal_title}' không có tương tác nào trong hơn 14 ngày qua. Hãy kết nối lại với khách hàng ngay.",
            target_type="deal",
            target_id=deal_id,
            link_url="/deals",
        )

    @classmethod
    def notify_contract_expiring(cls, db: Session, contract_id: str, contract_number: str, customer_name: str, owner_id: str, remaining_days: int):
        return cls.create_notification(
            db=db,
            user_id=owner_id,
            notif_type="contract_expiring",
            title=f"Hợp đồng {contract_number} sắp hết hạn",
            description=f"Hợp đồng của khách hàng '{customer_name}' chỉ còn {remaining_days} ngày hiệu lực. Hãy liên hệ tái ký hợp đồng.",
            target_type="contract",
            target_id=contract_id,
            link_url="/contracts",
        )

    @staticmethod
    def get_notifications(
        db: Session,
        user: User,
        unread_only: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[NotificationDTO], int, int]:
        query = db.query(Notification).filter(Notification.user_id == user.id)
        if unread_only:
            query = query.filter(Notification.is_read == False)

        total = query.count()
        unread_count = db.query(Notification).filter(
            Notification.user_id == user.id,
            Notification.is_read == False,
        ).count()

        items = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit).all()
        dto_list = [
            NotificationDTO(
                id=item.id,
                userId=item.user_id,
                type=item.type,
                title=item.title,
                description=item.description,
                targetType=item.target_type,
                targetId=item.target_id,
                linkUrl=item.link_url,
                isRead=item.is_read,
                createdAt=item.created_at.isoformat(),
                timeAgo=calculate_time_ago(item.created_at),
            )
            for item in items
        ]
        return dto_list, unread_count, total

    @staticmethod
    def mark_as_read(db: Session, notification_id: str, user: User) -> NotificationDTO:
        notif = db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == user.id,
        ).first()
        if not notif:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy thông báo.")
        notif.is_read = True
        db.commit()
        db.refresh(notif)
        return NotificationDTO(
            id=notif.id,
            userId=notif.user_id,
            type=notif.type,
            title=notif.title,
            description=notif.description,
            targetType=notif.target_type,
            targetId=notif.target_id,
            linkUrl=notif.link_url,
            isRead=notif.is_read,
            createdAt=notif.created_at.isoformat(),
            timeAgo=calculate_time_ago(notif.created_at),
        )

    @staticmethod
    def mark_all_read(db: Session, user: User) -> int:
        count = db.query(Notification).filter(
            Notification.user_id == user.id,
            Notification.is_read == False,
        ).update({"is_read": True})
        db.commit()
        return count
