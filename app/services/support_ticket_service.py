import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.support_ticket import SupportTicket
from app.models.customer import Customer
from app.models.user import User
from app.schemas.support_ticket import CreateSupportTicketDTO, UpdateSupportTicketDTO
from app.repositories.support_ticket_repository import SupportTicketRepository
from app.repositories.customer_repository import CustomerRepository


class SupportTicketService:
    """
    Service quản lý Yêu cầu hỗ trợ (Support Ticket) & Tự động quét Cờ rủi ro S3-08.
    - Quản lý vòng đời ticket (tạo, cập nhật, phân công, trạng thái, quá hạn).
    - Tự động phát hiện rủi ro: Khách hàng có số lượng ticket quá hạn vượt ngưỡng (ngưỡng mặc định >= 2)
      sẽ tự động được bật cờ risk_flag = True và gán lý do rủi ro.
    """

    @staticmethod
    def get_tickets_by_customer(
        db: Session,
        customer_id: str,
        user: User,
    ) -> List[SupportTicket]:
        return SupportTicketRepository.get_by_customer(db, customer_id, user)

    @staticmethod
    def get_ticket_by_id(
        db: Session,
        ticket_id: str,
        user: User,
    ) -> SupportTicket:
        ticket = SupportTicketRepository.get_by_id(db, ticket_id)
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy yêu cầu hỗ trợ.",
            )
        CustomerRepository.get_scoped_by_id(db, ticket.customer_id, user)
        return ticket

    @staticmethod
    def create_ticket(
        db: Session,
        customer_id: str,
        dto: CreateSupportTicketDTO,
        user: User,
    ) -> SupportTicket:
        CustomerRepository.get_scoped_by_id(db, customer_id, user)

        ticket_code = f"TK-{uuid.uuid4().hex[:6].upper()}"
        due_date_val = None
        if dto.dueDate:
            try:
                due_date_val = datetime.fromisoformat(dto.dueDate.replace("Z", "+00:00"))
            except Exception:
                due_date_val = datetime.utcnow()

        new_ticket = SupportTicket(
            id=str(uuid.uuid4()),
            customer_id=customer_id,
            ticket_code=ticket_code,
            title=dto.title,
            description=dto.description,
            priority=dto.priority or "medium",
            status=dto.status or "open",
            due_date=due_date_val,
            assigned_user_id=dto.assignedUserId or user.id,
        )
        created = SupportTicketRepository.create(db, new_ticket)

        # Kiểm tra cập nhật cờ rủi ro ngay sau khi tạo ticket
        SupportTicketService._check_and_update_single_customer_risk(db, customer_id)

        return created

    @staticmethod
    def update_ticket(
        db: Session,
        ticket_id: str,
        dto: UpdateSupportTicketDTO,
        user: User,
    ) -> SupportTicket:
        ticket = SupportTicketService.get_ticket_by_id(db, ticket_id, user)

        update_dict: Dict[str, Any] = {}
        if dto.title is not None:
            update_dict["title"] = dto.title
        if dto.description is not None:
            update_dict["description"] = dto.description
        if dto.priority is not None:
            update_dict["priority"] = dto.priority
        if dto.status is not None:
            update_dict["status"] = dto.status
            if dto.status in ["resolved", "closed"]:
                update_dict["resolved_at"] = datetime.utcnow()
        if dto.dueDate is not None:
            try:
                update_dict["due_date"] = datetime.fromisoformat(dto.dueDate.replace("Z", "+00:00"))
            except Exception:
                pass
        if dto.assignedUserId is not None:
            update_dict["assigned_user_id"] = dto.assignedUserId

        updated = SupportTicketRepository.update(db, ticket, update_dict)

        # Tái kiểm tra cờ rủi ro cho khách hàng
        SupportTicketService._check_and_update_single_customer_risk(db, ticket.customer_id)

        return updated

    @staticmethod
    def delete_ticket(
        db: Session,
        ticket_id: str,
        user: User,
    ) -> None:
        ticket = SupportTicketService.get_ticket_by_id(db, ticket_id, user)
        cust_id = ticket.customer_id
        SupportTicketRepository.delete(db, ticket)
        SupportTicketService._check_and_update_single_customer_risk(db, cust_id)

    @staticmethod
    def _check_and_update_single_customer_risk(
        db: Session,
        customer_id: str,
        threshold: int = 2,
    ) -> None:
        """Đánh giá lại cờ rủi ro của 1 khách hàng cụ thể."""
        cust = db.query(Customer).filter(Customer.id == customer_id, Customer.is_deleted == False).first()
        if not cust:
            return

        overdue_count = SupportTicketRepository.count_overdue_by_customer(db, customer_id)
        if overdue_count >= threshold:
            cust.risk_flag = True
            cust.risk_reason = f"Vượt ngưỡng cảnh báo: {overdue_count} yêu cầu hỗ trợ quá hạn xử lý"
        else:
            # Nếu trước đó bị risk vì overdue tickets thì gỡ cờ
            if cust.risk_flag and cust.risk_reason and "yêu cầu hỗ trợ quá hạn" in cust.risk_reason:
                cust.risk_flag = False
                cust.risk_reason = None
        db.commit()

    @staticmethod
    def scan_and_update_all_risks(
        db: Session,
        threshold: int = 2,
    ) -> Dict[str, Any]:
        """
        Nhiệm vụ định kỳ (Cron / Celery Task) S3-08:
        Quét toàn bộ khách hàng và tự động kích hoạt risk_flag = True
        nếu số lượng ticket quá hạn >= threshold.
        """
        overdue_pairs = SupportTicketRepository.find_customers_exceeding_overdue_threshold(db, threshold)
        flagged_details: List[Dict[str, Any]] = []

        all_customers = db.query(Customer).filter(Customer.is_deleted == False).all()
        flagged_ids = {pair[0] for pair in overdue_pairs}

        for cust in all_customers:
            if cust.id in flagged_ids:
                count = next(pair[1] for pair in overdue_pairs if pair[0] == cust.id)
                cust.risk_flag = True
                cust.risk_reason = f"Cảnh báo rủi ro tự động: {count} yêu cầu hỗ trợ quá hạn (Ngưỡng >= {threshold})"
                flagged_details.append({
                    "customerId": cust.id,
                    "company": cust.company or cust.full_name,
                    "overdueTickets": count,
                })
            else:
                if cust.risk_flag and cust.risk_reason and "yêu cầu hỗ trợ quá hạn" in cust.risk_reason:
                    cust.risk_flag = False
                    cust.risk_reason = None

        db.commit()

        return {
            "scannedCount": len(all_customers),
            "flaggedCount": len(flagged_details),
            "threshold": threshold,
            "details": flagged_details,
        }
