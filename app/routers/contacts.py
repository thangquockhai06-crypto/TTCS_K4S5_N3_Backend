from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.contact import Contact
from app.schemas.contact import (
    ContactDTO,
    ContactCreateDTO,
    ContactUpdateDTO,
    TransferContactDTO,
)
from app.services.contact_service import ContactService

router = APIRouter(tags=["Contacts Management (S3-02)"])


def _to_contact_dto(c: Contact) -> ContactDTO:
    return ContactDTO(
        id=c.id,
        customerId=c.customer_id,
        fullName=c.full_name,
        email=c.email,
        phone=c.phone,
        position=c.position,
        role=c.role,
        isPrimary=c.is_primary,
        isActive=c.is_active,
        notes=c.notes,
        createdAt=c.created_at.isoformat() if c.created_at else None,
        updatedAt=c.updated_at.isoformat() if c.updated_at else None,
    )


# Nested Customer Contact Routes
@router.get("/customers/{customer_id}/contacts", response_model=List[ContactDTO], summary="Lấy danh sách người liên hệ của khách hàng")
def get_customer_contacts(
    customer_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[ContactDTO]:
    contacts = ContactService.get_contacts_by_customer(
        db=db,
        customer_id=customer_id,
        user=current_user,
    )
    return [_to_contact_dto(c) for c in contacts]


@router.post("/customers/{customer_id}/contacts", response_model=ContactDTO, status_code=status.HTTP_201_CREATED, summary="Thêm người liên hệ mới")
def create_customer_contact(
    customer_id: str,
    dto: ContactCreateDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContactDTO:
    contact = ContactService.create_contact(
        db=db,
        customer_id=customer_id,
        dto=dto,
        user=current_user,
    )
    return _to_contact_dto(contact)


# Direct Contact Routes
@router.get("/contacts/{contact_id}", response_model=ContactDTO, summary="Chi tiết người liên hệ")
def get_contact_detail(
    contact_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContactDTO:
    contact = ContactService.get_contact_by_id(
        db=db,
        contact_id=contact_id,
        user=current_user,
    )
    return _to_contact_dto(contact)


@router.put("/contacts/{contact_id}", response_model=ContactDTO, summary="Cập nhật thông tin người liên hệ")
def update_contact(
    contact_id: str,
    dto: ContactUpdateDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContactDTO:
    contact = ContactService.update_contact(
        db=db,
        contact_id=contact_id,
        dto=dto,
        user=current_user,
    )
    return _to_contact_dto(contact)


@router.delete("/contacts/{contact_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Xóa người liên hệ")
def delete_contact(
    contact_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ContactService.delete_contact(
        db=db,
        contact_id=contact_id,
        user=current_user,
    )
    return None


@router.post("/contacts/{contact_id}/transfer", response_model=ContactDTO, summary="Điều chuyển người liên hệ sang doanh nghiệp khác (S3-02)")
def transfer_contact(
    contact_id: str,
    dto: TransferContactDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContactDTO:
    contact = ContactService.transfer_contact(
        db=db,
        contact_id=contact_id,
        new_customer_id=dto.newCustomerId,
        user=current_user,
        reason=dto.reason,
    )
    return _to_contact_dto(contact)
