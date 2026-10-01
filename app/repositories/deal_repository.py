from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.deal import Deal
from app.models.user import User
from app.repositories.base_repository import BaseRepository


class DealRepository(BaseRepository):
    """
    Tầng Repository xử lý truy vấn dữ liệu Cơ hội bán hàng (Kanban Deal / Opportunity Pipeline).
    Tích hợp Centralized Data Scope Filter ở mức CSDL.
    Tuân thủ Clean Layered Architecture & 100% Type Hints.
    """

    @staticmethod
    def get_all(
        db: Session,
        user: Optional[User] = None,
        search: Optional[str] = None,
        stage: Optional[str] = None,
        skip: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> List[Deal]:
        """Lấy danh sách deals thỏa mãn Data Scope của người dùng."""
        query = db.query(Deal)

        # 1. Lọc theo Data Scope
        if user is not None:
            query = BaseRepository.apply_data_scope_filter(query, user, Deal)

        # 2. Tìm kiếm từ khóa
        if search and search.strip():
            query = query.filter(Deal.title.ilike(f"%{search.strip()}%"))

        # 3. Lọc theo stage
        if stage and stage.lower() != "all":
            query = query.filter(Deal.stage == stage.lower())

        query = query.order_by(Deal.created_at.desc())

        if skip is not None:
            query = query.offset(skip)
        if limit is not None:
            query = query.limit(limit)

        return query.all()

    @staticmethod
    def get_all_for_export(
        db: Session,
        user: User,
        search: Optional[str] = None,
        stage: Optional[str] = None,
    ) -> List[Deal]:
        """Xuất danh sách Deals ra file Excel tuân thủ Data Scope."""
        query = db.query(Deal)
        query = BaseRepository.apply_data_scope_filter(query, user, Deal)

        if search and search.strip():
            query = query.filter(Deal.title.ilike(f"%{search.strip()}%"))

        if stage and stage.lower() != "all":
            query = query.filter(Deal.stage == stage.lower())

        return query.order_by(Deal.created_at.desc()).all()

    @staticmethod
    def get_by_id(db: Session, deal_id: str) -> Optional[Deal]:
        """Truy vấn deal theo ID không kiểm tra scope (Dùng nội bộ)."""
        return db.query(Deal).filter(Deal.id == deal_id).first()

    @staticmethod
    def get_scoped_by_id(db: Session, deal_id: str, user: User) -> Deal:
        """
        Truy vấn chi tiết Deal có bảo vệ Data Scope:
        - Không tồn tại -> HTTP 404
        - Tồn tại nhưng không thuộc quyền hạn -> HTTP 403 Forbidden
        """
        return BaseRepository.get_scoped_record_or_raise(
            db=db,
            model=Deal,
            record_id=deal_id,
            user=user,
            not_found_msg="Không tìm thấy cơ hội bán hàng.",
            forbidden_msg="Bạn không có quyền truy cập dữ liệu này.",
        )

    @staticmethod
    def create(db: Session, deal: Deal) -> Deal:
        db.add(deal)
        db.commit()
        db.refresh(deal)
        return deal

    @staticmethod
    def update_stage(db: Session, deal: Deal, new_stage: str) -> Deal:
        deal.stage = new_stage
        db.commit()
        db.refresh(deal)
        return deal

    @staticmethod
    def count_all(db: Session, user: Optional[User] = None) -> int:
        query = db.query(Deal)
        if user is not None:
            query = BaseRepository.apply_data_scope_filter(query, user, Deal)
        return query.count()

    @staticmethod
    def get_total_pipeline_value(db: Session, user: Optional[User] = None) -> float:
        query = db.query(func.sum(Deal.value))
        if user is not None:
            query = BaseRepository.apply_data_scope_filter(query, user, Deal)
        total = query.scalar()
        return float(total) if total is not None else 0.0
