import uuid
from decimal import Decimal
from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.quotation import Quotation
from app.models.quotation_line import QuotationLine
from app.models.product import Product
from app.models.user import User
from app.schemas.quotation import CreateQuotationDTO
from app.repositories.quotation_repository import QuotationRepository
from app.repositories.customer_repository import CustomerRepository
from app.services.catalog_item_service import requires_discount_approval


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

        lines = []
        total_amount = Decimal("0.00")
        approval_required = False
        for line_dto in dto.items:
            item = db.query(Product).filter(Product.id == line_dto.product_id).first()
            if not item:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Không tìm thấy catalog item '{line_dto.product_id}'.")
            if item.status != "ACTIVE" or not item.is_active:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Catalog item '{item.code}' đã ngừng bán và không thể thêm vào báo giá mới.")
            unit_price = Decimal(str(line_dto.unit_price if line_dto.unit_price is not None else item.list_price))
            line_approval = requires_discount_approval(unit_price, item)
            approval_required = approval_required or line_approval
            total_amount += unit_price * Decimal(str(line_dto.quantity))
            lines.append(
                QuotationLine(
                    product_id=item.id,
                    product_code=item.code,
                    product_name=item.name,
                    quantity=line_dto.quantity,
                    unit_price=unit_price,
                    list_price_snapshot=item.list_price,
                    floor_price_snapshot=item.floor_price,
                    currency=item.currency or "VND",
                    discount_approval_required=line_approval,
                )
            )

        new_quotation = Quotation(
            id=str(uuid.uuid4()),
            quote_number=dto.quoteNumber,
            title=dto.title,
            customer_id=dto.customerId,
            owner_id=user.id,
            total_amount=total_amount if dto.items else dto.totalAmount,
            status=dto.status or "draft",
            valid_until=dto.validUntil,
            discount_approval_required=approval_required,
            lines=lines,
        )
        return QuotationRepository.create(db, new_quotation)
