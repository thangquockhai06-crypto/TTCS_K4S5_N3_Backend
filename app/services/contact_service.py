import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.contact import Contact
from app.models.customer import Customer
from app.models.user import User
from app.models.activity import Activity
from app.models.audit_log import AuditLog
from app.schemas.contact import ContactCreateDTO, ContactUpdateDTO
from app.repositories.contact_repository import ContactRepository
from app.repositories.customer_repository import CustomerRepository


class ContactService:
    """
    Service quản lý Người liên hệ S3-02.
    Đảm bảo phân quyền phạm vi, vai trò ra quyết định (Decider, Influencer, ...),
    và nghiệp vụ điều chuyển công ty (transfer_contact) bảo toàn lịch sử.
    """

    @staticmethod
    def get_contacts_by_customer(
        db: Session,
        customer_id: str,
        user: User,
    ) -> List[Contact]:
        """Lấy danh sách người liên hệ thuộc khách hàng, kiểm tra Data Scope."""
        return ContactRepository.get_by_customer(db, customer_id, user)

    @staticmethod
    def get_contact_by_id(
        db: Session,
        contact_id: str,
        user: User,
    ) -> Contact:
        """Lấy chi tiết người liên hệ và kiểm tra quyền trên khách hàng sở hữu."""
        contact = ContactRepository.get_by_id(db, contact_id)
        if not contact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy người liên hệ.",
            )
        CustomerRepository.get_scoped_by_id(db, contact.customer_id, user)
        return contact

    @staticmethod
    def create_contact(
        db: Session,
        customer_id: str,
        dto: ContactCreateDTO,
        user: User,
    ) -> Contact:
        """Tạo người liên hệ mới cho khách hàng."""
        # Kiểm tra quyền trên khách hàng
        CustomerRepository.get_scoped_by_id(db, customer_id, user)

        # Nếu đặt làm người liên hệ chính, bỏ primary của các liên hệ khác
        if dto.isPrimary:
            existing_contacts = ContactRepository.get_by_customer(db, customer_id)
            for c in existing_contacts:
                if c.is_primary:
                    c.is_primary = False
            db.commit()

        new_contact = Contact(
            id=str(uuid.uuid4()),
            customer_id=customer_id,
            full_name=dto.fullName,
            email=dto.email,
            phone=dto.phone,
            position=dto.position or "",
            role=dto.role or "Decider",
            is_primary=dto.isPrimary,
            is_active=dto.isActive,
            notes=dto.notes,
        )
        return ContactRepository.create(db, new_contact)

    @staticmethod
    def update_contact(
        db: Session,
        contact_id: str,
        dto: ContactUpdateDTO,
        user: User,
    ) -> Contact:
        """Cập nhật thông tin người liên hệ."""
        contact = ContactService.get_contact_by_id(db, contact_id, user)

        # Nếu đổi sang is_primary = True, cập nhật các liên hệ khác
        if dto.isPrimary is True:
            existing_contacts = ContactRepository.get_by_customer(db, contact.customer_id)
            for c in existing_contacts:
                if c.id != contact.id and c.is_primary:
                    c.is_primary = False
            db.commit()

        update_dict: Dict[str, Any] = {}
        if dto.fullName is not None:
            update_dict["full_name"] = dto.fullName
        if dto.email is not None:
            update_dict["email"] = dto.email
        if dto.phone is not None:
            update_dict["phone"] = dto.phone
        if dto.position is not None:
            update_dict["position"] = dto.position
        if dto.role is not None:
            update_dict["role"] = dto.role
        if dto.isPrimary is not None:
            update_dict["is_primary"] = dto.isPrimary
        if dto.isActive is not None:
            update_dict["is_active"] = dto.isActive
        if dto.notes is not None:
            update_dict["notes"] = dto.notes

        return ContactRepository.update(db, contact, update_dict)

    @staticmethod
    def delete_contact(
        db: Session,
        contact_id: str,
        user: User,
    ) -> None:
        """Xóa người liên hệ."""
        contact = ContactService.get_contact_by_id(db, contact_id, user)
        ContactRepository.delete(db, contact)

    @staticmethod
    def transfer_contact(
        db: Session,
        contact_id: str,
        new_customer_id: str,
        user: User,
        reason: Optional[str] = None,
    ) -> Contact:
        """
        Nghiệp vụ chuyển người liên hệ sang doanh nghiệp khác (S3-02):
        - Kiểm tra quyền trên công ty cũ (source) và công ty mới (destination).
        - Bảo toàn toàn bộ thông tin và lịch sử liên hệ.
        - Ghi vết hoạt động (Activity) vào cả 2 công ty.
        - Ghi log kiểm toán (AuditLog).
        """
        contact = ContactService.get_contact_by_id(db, contact_id, user)
        old_customer_id = contact.customer_id

        if old_customer_id == new_customer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Doanh nghiệp mới phải khác doanh nghiệp hiện tại của người liên hệ.",
            )

        source_customer = CustomerRepository.get_scoped_by_id(db, old_customer_id, user)
        target_customer = CustomerRepository.get_scoped_by_id(db, new_customer_id, user)

        old_company_name = source_customer.company or source_customer.full_name
        new_company_name = target_customer.company or target_customer.full_name

        # 1. Điều chuyển liên hệ
        contact.customer_id = new_customer_id
        contact.is_primary = False  # Tránh xung đột primary ở công ty mới
        contact.updated_at = datetime.utcnow()

        # 2. Ghi Activity cho công ty nguồn (source)
        act_source = Activity(
            id=str(uuid.uuid4()),
            customer_id=old_customer_id,
            user_id=user.id,
            type="status_change",
            title=f"Điều chuyển người liên hệ: {contact.full_name}",
            description=(
                f"Người liên hệ '{contact.full_name}' ({contact.position or contact.role}) "
                f"đã được điều chuyển sang công ty '{new_company_name}'."
                + (f" Lý do: {reason}" if reason else "")
            ),
            created_at=datetime.utcnow(),
        )
        db.add(act_source)

        # 3. Ghi Activity cho công ty đích (target)
        act_target = Activity(
            id=str(uuid.uuid4()),
            customer_id=new_customer_id,
            user_id=user.id,
            type="status_change",
            title=f"Tiếp nhận người liên hệ: {contact.full_name}",
            description=(
                f"Tiếp nhận người liên hệ '{contact.full_name}' ({contact.position or contact.role}) "
                f"được chuyển từ công ty '{old_company_name}'."
                + (f" Lý do: {reason}" if reason else "")
            ),
            created_at=datetime.utcnow(),
        )
        db.add(act_target)

        # 4. Ghi AuditLog
        audit = AuditLog(
            id=str(uuid.uuid4()),
            user_id=user.id,
            action="TRANSFER_CONTACT",
            details=f"Chuyển người liên hệ {contact.full_name} (ID: {contact.id}) từ công ty {old_company_name} sang {new_company_name}",
            performed_by=user.full_name,
            user_name=user.full_name,
            user_email=user.email,
            target_type="Contact",
            target_id=contact.id,
            field_name="customer_id",
            old_value=old_customer_id,
            new_value=new_customer_id,
            created_at=datetime.utcnow(),
        )
        db.add(audit)

        db.commit()
        db.refresh(contact)
        return contact
