from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.support_ticket import SupportTicket
from app.schemas.support_ticket import (
    SupportTicketDTO,
    CreateSupportTicketDTO,
    UpdateSupportTicketDTO,
)
from app.services.support_ticket_service import SupportTicketService

router = APIRouter(tags=["Support Tickets Management (S3-08)"])


def _to_ticket_dto(t: SupportTicket) -> SupportTicketDTO:
    now = datetime.utcnow()
    is_overdue = bool(t.due_date and t.due_date < now and t.status not in ["resolved", "closed"])
    return SupportTicketDTO(
        id=t.id,
        customerId=t.customer_id,
        ticketCode=t.ticket_code,
        title=t.title,
        description=t.description,
        priority=t.priority,
        status=t.status,
        dueDate=t.due_date.isoformat() if t.due_date else None,
        assignedUserId=t.assigned_user_id,
        assignedUserName=t.assigned_user.full_name if t.assigned_user else None,
        isOverdue=is_overdue,
        resolvedAt=t.resolved_at.isoformat() if t.resolved_at else None,
        createdAt=t.created_at.isoformat() if t.created_at else None,
        updatedAt=t.updated_at.isoformat() if t.updated_at else None,
    )


@router.get("/customers/{customer_id}/tickets", response_model=List[SupportTicketDTO], summary="Lấy danh sách ticket của khách hàng")
def get_customer_tickets(
    customer_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[SupportTicketDTO]:
    tickets = SupportTicketService.get_tickets_by_customer(
        db=db,
        customer_id=customer_id,
        user=current_user,
    )
    return [_to_ticket_dto(t) for t in tickets]


@router.post("/customers/{customer_id}/tickets", response_model=SupportTicketDTO, status_code=status.HTTP_201_CREATED, summary="Tạo yêu cầu hỗ trợ mới")
def create_customer_ticket(
    customer_id: str,
    dto: CreateSupportTicketDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SupportTicketDTO:
    ticket = SupportTicketService.create_ticket(
        db=db,
        customer_id=customer_id,
        dto=dto,
        user=current_user,
    )
    return _to_ticket_dto(ticket)


@router.put("/tickets/{ticket_id}", response_model=SupportTicketDTO, summary="Cập nhật yêu cầu hỗ trợ")
def update_ticket(
    ticket_id: str,
    dto: UpdateSupportTicketDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SupportTicketDTO:
    ticket = SupportTicketService.update_ticket(
        db=db,
        ticket_id=ticket_id,
        dto=dto,
        user=current_user,
    )
    return _to_ticket_dto(ticket)


@router.delete("/tickets/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Xóa yêu cầu hỗ trợ")
def delete_ticket(
    ticket_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    SupportTicketService.delete_ticket(
        db=db,
        ticket_id=ticket_id,
        user=current_user,
    )
    return None
