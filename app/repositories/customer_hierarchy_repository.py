from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.customer import Customer
from app.models.deal import Deal
from app.models.user import User
from app.repositories.base_repository import BaseRepository


class CustomerHierarchyRepository(BaseRepository):
    """
    Tầng Repository xử lý truy vấn dữ liệu cây phân cấp quan hệ công ty mẹ - con (SCRUM-63).
    Tuân thủ Clean Layered Architecture & Centralized Data Scope Protection.
    """

    @staticmethod
    def get_by_id(db: Session, customer_id: str) -> Optional[Customer]:
        """Truy vấn khách hàng theo ID không kiểm tra Data Scope (Dùng nội bộ kiểm tra tồn tại)."""
        stmt = select(Customer).where(Customer.id == customer_id)
        return db.scalars(stmt).first()

    @staticmethod
    def get_scoped_by_id(db: Session, customer_id: str, user: User) -> Customer:
        """
        Truy vấn chi tiết khách hàng có bảo vệ phân quyền phạm vi dữ liệu:
        - Không tồn tại -> HTTP 404 "Khách hàng không tồn tại"
        - Tồn tại nhưng không thuộc phạm vi quyền hạn -> HTTP 403 Forbidden
        """
        return BaseRepository.get_scoped_record_or_raise(
            db=db,
            model=Customer,
            record_id=customer_id,
            user=user,
            not_found_msg="Khách hàng không tồn tại",
            forbidden_msg="Bạn không có quyền truy cập dữ liệu này.",
        )

    @staticmethod
    def get_subsidiaries(db: Session, parent_id: str) -> List[Customer]:
        """Lấy danh sách các công ty con trực tiếp (parent_id == parent_id)."""
        stmt = (
            select(Customer)
            .where(Customer.parent_id == parent_id)
            .order_by(Customer.created_at.desc())
        )
        return list(db.scalars(stmt).all())

    @staticmethod
    def get_customer_deals(db: Session, customer_id: str) -> List[Deal]:
        """Lấy toàn bộ danh sách cơ hội bán hàng (deals) của khách hàng."""
        stmt = select(Deal).where(Deal.customer_id == customer_id)
        return list(db.scalars(stmt).all())

    @staticmethod
    def assign_parent(
        db: Session,
        customer: Customer,
        parent_id: Optional[str],
    ) -> Customer:
        """Cập nhật quan hệ công ty mẹ (parent_id) và commit session."""
        customer.parent_id = parent_id
        db.commit()
        db.refresh(customer)
        return customer
