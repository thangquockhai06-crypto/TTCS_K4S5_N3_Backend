from datetime import date, datetime, time, timedelta
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.deal import Deal
from app.models.user import User
from app.repositories.base_repository import BaseRepository


class DealRepository(BaseRepository):
    """Deal queries with centralized data-scope enforcement."""

    @staticmethod
    def get_all(
        db: Session,
        user: Optional[User] = None,
        search: Optional[str] = None,
        stage: Optional[str] = None,
        outcome: Optional[str] = None,
        closed_from: Optional[date] = None,
        closed_to: Optional[date] = None,
        signed_from: Optional[date] = None,
        signed_to: Optional[date] = None,
        lost_reason_id: Optional[str] = None,
        skip: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> List[Deal]:
        query = db.query(Deal)
        if user is not None:
            query = BaseRepository.apply_data_scope_filter(query, user, Deal)
        if search and search.strip():
            query = query.filter(Deal.title.ilike(f"%{search.strip()}%"))
        if stage and stage.lower() != "all":
            query = query.filter(Deal.stage == stage.lower())
        if outcome and outcome.upper() != "ALL":
            query = query.filter(Deal.status == outcome.upper())
        if closed_from:
            query = query.filter(Deal.closed_at >= datetime.combine(closed_from, time.min))
        if closed_to:
            query = query.filter(Deal.closed_at < datetime.combine(closed_to + timedelta(days=1), time.min))
        if signed_from:
            query = query.filter(Deal.signed_date >= signed_from)
        if signed_to:
            query = query.filter(Deal.signed_date <= signed_to)
        if lost_reason_id:
            query = query.filter(Deal.lost_reason_id == lost_reason_id)

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
        outcome: Optional[str] = None,
    ) -> List[Deal]:
        return DealRepository.get_all(
            db=db,
            user=user,
            search=search,
            stage=stage,
            outcome=outcome,
        )

    @staticmethod
    def get_by_id(db: Session, deal_id: str) -> Optional[Deal]:
        return db.query(Deal).filter(Deal.id == deal_id).first()

    @staticmethod
    def get_scoped_by_id(db: Session, deal_id: str, user: User) -> Deal:
        return BaseRepository.get_scoped_record_or_raise(
            db=db,
            model=Deal,
            record_id=deal_id,
            user=user,
            not_found_msg="Không tìm thấy cơ hội bán hàng.",
            forbidden_msg="Bạn không có quyền truy cập dữ liệu này.",
        )

    @staticmethod
    def get_for_update(db: Session, deal_id: str) -> Optional[Deal]:
        return db.query(Deal).filter(Deal.id == deal_id).with_for_update().first()

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
    def update(db: Session, deal: Deal) -> Deal:
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
