from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.models.contact import Contact
from app.models.customer import Customer
from app.models.user import User
from app.repositories.base_repository import BaseRepository
from app.repositories.customer_repository import CustomerRepository


class ContactRepository(BaseRepository):
    """
    Repository quản lý Người liên hệ (Contact Management) S3-02.
    """

    @staticmethod
    def get_by_customer(
        db: Session,
        customer_id: str,
        user: Optional[User] = None,
    ) -> List[Contact]:
        """Lấy danh sách người liên hệ thuộc một khách hàng, có kiểm tra Data Scope trên khách hàng."""
        if user is not None:
            # Kiểm tra quyền truy cập vào khách hàng cha
            CustomerRepository.get_scoped_by_id(db, customer_id, user)

        return (
            db.query(Contact)
            .filter(Contact.customer_id == customer_id)
            .order_by(Contact.is_primary.desc(), Contact.created_at.asc())
            .all()
        )

    @staticmethod
    def get_by_id(db: Session, contact_id: str) -> Optional[Contact]:
        """Lấy thông tin người liên hệ theo ID."""
        return db.query(Contact).filter(Contact.id == contact_id).first()

    @staticmethod
    def create(db: Session, contact: Contact) -> Contact:
        """Tạo mới một người liên hệ."""
        db.add(contact)
        db.commit()
        db.refresh(contact)
        return contact

    @staticmethod
    def update(db: Session, contact: Contact, update_data: Dict[str, Any]) -> Contact:
        """Cập nhật thông tin người liên hệ."""
        for key, value in update_data.items():
            if hasattr(contact, key) and value is not None:
                setattr(contact, key, value)
        contact.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(contact)
        return contact

    @staticmethod
    def delete(db: Session, contact: Contact) -> None:
        """Xóa người liên hệ."""
        db.delete(contact)
        db.commit()
