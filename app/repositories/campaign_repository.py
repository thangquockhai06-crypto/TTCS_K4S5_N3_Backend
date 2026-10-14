import uuid
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from app.models.campaign import Campaign
from app.models.lead import Lead
from app.models.deal import Deal


class CampaignRepository:
    """
    Repository truy vấn bảng campaigns và tính toán số liệu tổng hợp thời gian thực.
    """

    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 100) -> List[Campaign]:
        return (
            db.query(Campaign)
            .order_by(desc(Campaign.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_by_id(db: Session, campaign_id: str) -> Optional[Campaign]:
        return db.query(Campaign).filter(Campaign.id == campaign_id).first()

    @staticmethod
    def get_by_code(db: Session, code: str) -> Optional[Campaign]:
        return db.query(Campaign).filter(Campaign.code == code).first()

    @staticmethod
    def create(db: Session, campaign: Campaign) -> Campaign:
        db.add(campaign)
        db.commit()
        db.refresh(campaign)
        return campaign

    @staticmethod
    def update(db: Session, campaign: Campaign) -> Campaign:
        db.commit()
        db.refresh(campaign)
        return campaign

    @staticmethod
    def get_campaign_metrics(db: Session, campaign_id: str) -> dict:
        lead_count = db.query(func.count(Lead.id)).filter(Lead.campaign_id == campaign_id).scalar() or 0
        deal_count = db.query(func.count(Deal.id)).filter(Deal.campaign_id == campaign_id).scalar() or 0
        actual_won_revenue = (
            db.query(func.sum(Deal.value))
            .filter(Deal.campaign_id == campaign_id, Deal.stage == "won")
            .scalar()
            or 0.0
        )
        return {
            "total_leads": int(lead_count),
            "total_deals": int(deal_count),
            "actual_revenue": float(actual_won_revenue),
        }
