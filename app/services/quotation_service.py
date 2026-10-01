import uuid
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.quotation import Quotation
from app.models.user import User
from app.schemas.quotation import CreateQuotationDTO
from app.repositories.quotation_repository import QuotationRepository
from app.repositories.customer_repository import CustomerRepository


class QuotationService:
    """
    Tầng Service xử lý nghiệp vụ Báo giá (Quotations).
    Tuân thủ Clean Layered Architecture, Data Scope Security & 100% Type Hints.
    """

    @staticmethod
    def get_quotations(
        db: Session,
        user: Optional[User] = None,
        search: Optional[str] = None,
        status: Optional[str] = None,
        customer_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Quotation], int]:
        """Lấy danh sách báo giá tuân thủ Data Scope."""
        return QuotationRepository.get_all(
            db=db,
            user=user,
            search=search,
            status=status,
            customer_id=customer_id,
            skip=skip,
            limit=limit,
        )

    @staticmethod
    def get_quotations_for_export(
        db: Session,
        user: User,
        search: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Quotation]:
        """Lấy danh sách báo giá trong Data Scope để xuất Excel."""
        return QuotationRepository.get_all_for_export(
            db=db,
            user=user,
            search=search,
            status=status,
        )

    @staticmethod
    def get_quotation_by_id(
        db: Session,
        quotation_id: str,
        user: Optional[User] = None,
    ) -> Optional[Quotation]:
        """
        Lấy chi tiết báo giá. Bắt buộc kiểm tra quyền (403 Forbidden nếu không có quyền).
        """
        if user is not None:
            return QuotationRepository.get_scoped_by_id(db, quotation_id, user)
        return QuotationRepository.get_by_id(db, quotation_id)

    @staticmethod
    def create_quotation(
        db: Session,
        dto: CreateQuotationDTO,
        user: User,
    ) -> Quotation:
        """
        Tạo mới báo giá.
        Xác thực quyền xem khách hàng trước và luôn gán owner_id = user.id.
        """
        # Xác thực quyền truy cập khách hàng trước
        CustomerRepository.get_scoped_by_id(db, dto.customerId, user)

        new_quotation = Quotation(
            id=str(uuid.uuid4()),
            quote_number=dto.quoteNumber,
            title=dto.title,
            customer_id=dto.customerId,
            owner_id=user.id,
            total_amount=dto.totalAmount,
            status=dto.status or "draft",
            valid_until=dto.validUntil,
        )
        return QuotationRepository.create(db, new_quotation)
