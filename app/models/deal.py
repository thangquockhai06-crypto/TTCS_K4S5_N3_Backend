import uuid
from datetime import datetime
from sqlalchemy import Column, String, Numeric, Integer, Date, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Deal(Base):
    __tablename__ = "deals"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    value = Column(Numeric(15, 2), default=0.00, nullable=False, index=True)
    stage = Column(
        Enum("lead", "contact", "proposal", "negotiation", "won", "lost", name="deal_stage_enum"),
        default="lead",
        nullable=False,
    )
    probability = Column(Integer, default=20, nullable=False)
    customer_id = Column(String(36), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    owner_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    campaign_id = Column(String(36), ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True, index=True)
    expected_close_date = Column(Date, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(
            "status IN ('OPEN', 'WON', 'LOST')",
            name="ck_deal_status_valid",
        ),
        CheckConstraint(
            """
            (
                status = 'OPEN'
                AND actual_value IS NULL
                AND signed_date IS NULL
                AND lost_reason_id IS NULL
                AND lost_reason_note IS NULL
                AND competitor_id IS NULL
                AND closed_at IS NULL
                AND closed_by IS NULL
            )
            OR (
                status = 'WON'
                AND actual_value IS NOT NULL
                AND actual_value > 0
                AND signed_date IS NOT NULL
                AND lost_reason_id IS NULL
                AND lost_reason_note IS NULL
                AND competitor_id IS NULL
                AND closed_at IS NOT NULL
                AND closed_by IS NOT NULL
            )
            OR (
                status = 'LOST'
                AND actual_value IS NULL
                AND signed_date IS NULL
                AND lost_reason_id IS NOT NULL
                AND closed_at IS NOT NULL
                AND closed_by IS NOT NULL
            )
            """,
            name="ck_deal_outcome_fields",
        ),
    )

    customer = relationship("Customer", back_populates="deals")
    owner = relationship("User", back_populates="deals")
    campaign = relationship("Campaign", back_populates="deals")
