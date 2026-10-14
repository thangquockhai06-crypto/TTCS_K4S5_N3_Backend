from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_, desc

from app.models.deal import Deal
from app.models.deal_item import DealItem
from app.models.user import User
from app.models.pipeline_stage import PipelineStage
from app.repositories.base_repository import BaseRepository


class DealRepository(BaseRepository):
    """
    Tầng Repository xử lý truy vấn dữ liệu Cơ hội bán hàng (Kanban Deal / Opportunity Pipeline).
    Tích hợp Centralized Data Scope Filter ở mức CSDL và hỗ trợ EP-05.
    """

    @staticmethod
    def get_all(
        db: Session,
        user: Optional[User] = None,
        search: Optional[str] = None,
        stage: Optional[str] = None,
        is_stalled: Optional[bool] = None,
        campaign_id: Optional[str] = None,
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

        # 4. Lọc theo trạng thái ứ đọng (stalled)
        if is_stalled is not None:
            query = query.filter(Deal.is_stalled == is_stalled)

        # 5. Lọc theo chiến dịch
        if campaign_id:
            query = query.filter(Deal.campaign_id == campaign_id)

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
    def update(db: Session, deal: Deal) -> Deal:
        deal.updated_at = datetime.utcnow()
        deal.last_activity_at = datetime.utcnow()
        db.commit()
        db.refresh(deal)
        return deal

    @staticmethod
    def update_stage(db: Session, deal: Deal, new_stage: str) -> Deal:
        deal.stage = new_stage
        deal.updated_at = datetime.utcnow()
        deal.last_activity_at = datetime.utcnow()
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

    @staticmethod
    def get_items(db: Session, deal_id: str) -> List[DealItem]:
        return db.query(DealItem).filter(DealItem.deal_id == deal_id).all()

    @staticmethod
    def add_item(db: Session, item: DealItem) -> DealItem:
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    @staticmethod
    def delete_item(db: Session, item_id: str) -> bool:
        item = db.query(DealItem).filter(DealItem.id == item_id).first()
        if item:
            db.delete(item)
            db.commit()
            return True
        return False

    @staticmethod
    def recalculate_deal_value(db: Session, deal_id: str) -> float:
        """
        S5-03: Tính lại giá trị tổng Deal chuẩn xác trên backend dựa trên tổng các DealItem.
        """
        items = db.query(DealItem).filter(DealItem.deal_id == deal_id).all()
        deal = db.query(Deal).filter(Deal.id == deal_id).first()
        if deal:
            if items:
                total_val = sum(float(i.subtotal) for i in items)
                deal.value = total_val
            deal.updated_at = datetime.utcnow()
            deal.last_activity_at = datetime.utcnow()
            db.commit()
            db.refresh(deal)
            return float(deal.value)
        return 0.0
