import uuid
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.deal import Deal
from app.models.user import User
from app.schemas.deal import CreateDealDTO
from app.repositories.deal_repository import DealRepository


class DealService:
    """
    Tầng Service xử lý nghiệp vụ Quản lý Cơ hội bán hàng (Kanban Deal / Opportunity Pipeline).
    Tuân thủ Clean Layered Architecture, Data Scope Security & 100% Type Hints.
    """

    @staticmethod
    def get_deals(
        db: Session,
        user: Optional[User] = None,
        search: Optional[str] = None,
        stage: Optional[str] = None,
        skip: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> List[Deal]:
        """Lấy danh sách Deals thỏa mãn Data Scope của người dùng."""
        return DealRepository.get_all(
            db=db,
            user=user,
            search=search,
            stage=stage,
            skip=skip,
            limit=limit,
        )

    @staticmethod
    def get_deals_for_export(
        db: Session,
        user: User,
        search: Optional[str] = None,
        stage: Optional[str] = None,
    ) -> List[Deal]:
        """Lấy toàn bộ Deals trong Data Scope để xuất file Excel."""
        return DealRepository.get_all_for_export(
            db=db,
            user=user,
            search=search,
            stage=stage,
        )

    @staticmethod
    def get_deal_by_id(
        db: Session,
        deal_id: str,
        user: Optional[User] = None,
    ) -> Optional[Deal]:
        """
        Lấy chi tiết Deal. Nếu có user, bắt buộc kiểm tra quyền (403 Forbidden nếu không có quyền).
        """
        if user is not None:
            return DealRepository.get_scoped_by_id(db, deal_id, user)
        return DealRepository.get_by_id(db, deal_id)

    @staticmethod
    def create_deal(
        db: Session,
        dto: CreateDealDTO,
        user: User,
    ) -> Deal:
        """
        Tạo mới cơ hội bán hàng.
        Luôn gán owner_id = user.id phía máy chủ, không tin tưởng client input.
        """
        new_deal: Deal = Deal(
            id=str(uuid.uuid4()),
            title=dto.title,
            value=dto.value,
            stage=dto.stage,
            probability=dto.probability or 20,
            customer_id=dto.customerId,
            owner_id=user.id,
            expected_close_date=dto.expectedCloseDate,
        )
        return DealRepository.create(db, new_deal)

    @staticmethod
    def move_stage(
        db: Session,
        deal_id: str,
        new_stage: str,
        user: Optional[User] = None,
    ) -> Optional[Deal]:
        """Cập nhật stage của deal (kiểm tra quyền truy cập bản ghi trước)."""
        if user is not None:
            deal = DealRepository.get_scoped_by_id(db, deal_id, user)
        else:
            deal = DealRepository.get_by_id(db, deal_id)

        if not deal:
            return None
        return DealRepository.update_stage(db, deal, new_stage)
