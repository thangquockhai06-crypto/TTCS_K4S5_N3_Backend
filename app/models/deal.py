import uuid
from datetime import datetime
from sqlalchemy import Column, String, Numeric, Integer, Date, DateTime, Enum, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.database import Base


class Deal(Base):
    """
    Model Cơ hội bán hàng (EP-05: Deal Management: S5-01 -> S5-08).
    Hỗ trợ luồng phễu: lead -> contact -> proposal -> negotiation -> won / lost.
    """
    __tablename__ = "deals"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    value = Column(Numeric(15, 2), default=0.00, nullable=False)
    stage = Column(
        String(50),
        default="lead",
        nullable=False,
        index=True,
    )
    probability = Column(Integer, default=20, nullable=False)
    customer_id = Column(String(36), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    owner_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    expected_close_date = Column(Date, nullable=True, index=True)

    # EP-05 Extensions:
    campaign_id = Column(String(36), ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True, index=True)
    close_date = Column(Date, nullable=True)
    actual_value = Column(Numeric(15, 2), nullable=True)
    loss_reason = Column(String(255), nullable=True)
    loss_competitor = Column(String(255), nullable=True)

    # Stalled Deals Tracking (S5-07)
    is_stalled = Column(Boolean, default=False, nullable=False, index=True)
    last_activity_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Deal Reassignment Tracking (S5-08)
    reassignment_reason = Column(String(255), nullable=True)
    reassigned_from_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    customer = relationship("Customer", back_populates="deals")
    owner = relationship("User", foreign_keys=[owner_id], back_populates="deals")
    reassigned_from = relationship("User", foreign_keys=[reassigned_from_id])
    campaign = relationship("Campaign", back_populates="deals")
    deal_items = relationship("DealItem", back_populates="deal", cascade="all, delete-orphan")
    deal_histories = relationship(
        "DealHistory",
        back_populates="deal",
        cascade="all, delete-orphan",
        order_by="desc(DealHistory.changed_at)",
    )
