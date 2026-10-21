from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from app.models.support_ticket import SupportTicket
from app.models.customer import Customer
from app.models.user import User
from app.repositories.base_repository import BaseRepository
from app.repositories.customer_repository import CustomerRepository


class SupportTicketRepository(BaseRepository):
    """
    Repository quản lý Yêu cầu hỗ trợ (Support Ticket) S3-08.
    """

    @staticmethod
    def get_by_customer(
        db: Session,
        customer_id: str,
        user: Optional[User] = None,
    ) -> List[SupportTicket]:
        """Lấy danh sách ticket của một khách hàng, kiểm tra Data Scope trên khách hàng."""
        if user is not None:
            CustomerRepository.get_scoped_by_id(db, customer_id, user)

        return (
            db.query(SupportTicket)
            .filter(SupportTicket.customer_id == customer_id)
            .order_by(SupportTicket.created_at.desc())
            .all()
        )

    @staticmethod
    def get_by_id(db: Session, ticket_id: str) -> Optional[SupportTicket]:
        return db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()

    @staticmethod
    def create(db: Session, ticket: SupportTicket) -> SupportTicket:
        db.add(ticket)
        db.commit()
        db.refresh(ticket)
        return ticket

    @staticmethod
    def update(db: Session, ticket: SupportTicket, update_data: Dict[str, Any]) -> SupportTicket:
        for key, value in update_data.items():
            if hasattr(ticket, key) and value is not None:
                setattr(ticket, key, value)
        ticket.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(ticket)
        return ticket

    @staticmethod
    def delete(db: Session, ticket: SupportTicket) -> None:
        db.delete(ticket)
        db.commit()

    @staticmethod
    def count_overdue_by_customer(db: Session, customer_id: str, now: Optional[datetime] = None) -> int:
        """Đếm số ticket quá hạn (due_date < now và chưa giải quyết/đóng)."""
        current_time = now or datetime.utcnow()
        return (
            db.query(SupportTicket)
            .filter(
                SupportTicket.customer_id == customer_id,
                SupportTicket.due_date < current_time,
                SupportTicket.status.notin_(["resolved", "closed"]),
            )
            .count()
        )

    @staticmethod
    def find_customers_exceeding_overdue_threshold(
        db: Session,
        threshold: int = 2,
        now: Optional[datetime] = None,
    ) -> List[Tuple[str, int]]:
        """
        Tìm danh sách (customer_id, count) có số ticket quá hạn >= threshold.
        """
        current_time = now or datetime.utcnow()
        results = (
            db.query(
                SupportTicket.customer_id,
                func.count(SupportTicket.id).label("overdue_count"),
            )
            .join(Customer, SupportTicket.customer_id == Customer.id)
            .filter(
                Customer.is_deleted == False,
                SupportTicket.due_date < current_time,
                SupportTicket.status.notin_(["resolved", "closed"]),
            )
            .group_by(SupportTicket.customer_id)
            .having(func.count(SupportTicket.id) >= threshold)
            .all()
        )
        return [(r[0], r[1]) for r in results]
