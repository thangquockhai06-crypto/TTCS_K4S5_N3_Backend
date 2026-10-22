import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Column, Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class DealOutcomeHistory(Base):
    """Append-only close/reopen history for a deal."""

    __tablename__ = "deal_outcome_history"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    deal_id = Column(String(36), ForeignKey("deals.id", ondelete="CASCADE"), nullable=False, index=True)
    action = Column(String(20), nullable=False)  # CLOSED | REOPENED
    outcome = Column(String(10), nullable=False)  # WON | LOST for the affected close
    previous_status = Column(String(10), nullable=False)
    resulting_status = Column(String(10), nullable=False)
    previous_stage = Column(String(30), nullable=True)
    resulting_stage = Column(String(30), nullable=True)
    actor_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    event_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    closed_at = Column(DateTime, nullable=True)
    closed_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    actual_value = Column(Numeric(15, 2), nullable=True)
    signed_date = Column(Date, nullable=True)
    lost_reason_id = Column(String(36), ForeignKey("win_loss_reasons.id", ondelete="SET NULL"), nullable=True)
    lost_reason_note = Column(Text, nullable=True)
    competitor_id = Column(String(36), ForeignKey("competitors.id", ondelete="SET NULL"), nullable=True)
    reopen_reason = Column(Text, nullable=True)

    deal = relationship("Deal", back_populates="outcome_history")

    @property
    def actual_value_decimal(self) -> Decimal | None:
        return Decimal(str(self.actual_value)) if self.actual_value is not None else None


__all__ = ["DealOutcomeHistory"]
