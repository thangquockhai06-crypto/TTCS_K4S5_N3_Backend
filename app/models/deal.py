import uuid
from datetime import datetime
from sqlalchemy import (
    CheckConstraint,
    Column,
    DDL,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    event,
    inspect,
)
from sqlalchemy.orm import relationship
from app.database import Base


class Deal(Base):
    __tablename__ = "deals"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    value = Column(Numeric(15, 2), default=0.00, nullable=False)
    stage = Column(
        Enum("lead", "contact", "proposal", "negotiation", "won", "lost", name="deal_stage_enum"),
        default="lead",
        nullable=False,
    )
    probability = Column(Integer, default=20, nullable=False)
    customer_id = Column(String(36), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    owner_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expected_close_date = Column(Date, nullable=True)

    # Outcome data is separate from the pipeline stage so reopening a deal is explicit.
    status = Column(String(10), default="OPEN", nullable=False, index=True)
    closed_at = Column(DateTime, nullable=True)
    closed_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    actual_value = Column(Numeric(15, 2), nullable=True)
    signed_date = Column(Date, nullable=True)
    lost_reason_id = Column(String(36), ForeignKey("win_loss_reasons.id", ondelete="RESTRICT"), nullable=True)
    lost_reason_note = Column(String(2000), nullable=True)
    competitor_id = Column(String(36), ForeignKey("competitors.id", ondelete="SET NULL"), nullable=True)
    reopened_at = Column(DateTime, nullable=True)
    reopened_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reopen_reason = Column(String(2000), nullable=True)
    last_open_stage = Column(String(30), nullable=True)

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
    owner = relationship("User", back_populates="deals", foreign_keys=[owner_id])
    lost_reason = relationship("WinLossReason", foreign_keys=[lost_reason_id])
    competitor = relationship("Competitor", foreign_keys=[competitor_id])
    outcome_history = relationship(
        "DealOutcomeHistory",
        back_populates="deal",
        cascade="all, delete-orphan",
        order_by="DealOutcomeHistory.event_at.asc()",
    )

    @property
    def is_closed(self) -> bool:
        return self.status in {"WON", "LOST"}


@event.listens_for(Deal, "before_update")
def _prevent_closed_deal_mutation(mapper, connection, target) -> None:
    """Protect closed deals even when an internal service forgets its guard."""
    state = inspect(target)
    old_status = state.attrs.status.history.deleted
    previous_status = old_status[0] if old_status else target.status
    if previous_status not in {"WON", "LOST"} or target.status != previous_status:
        return

    immutable_fields = {
        "title",
        "value",
        "stage",
        "probability",
        "customer_id",
        "owner_id",
        "expected_close_date",
    }
    if any(state.attrs[field].history.has_changes() for field in immutable_fields):
        raise ValueError("Closed opportunities cannot be edited.")


event.listen(
    Deal.__table__,
    "after_create",
    DDL(
        """
        CREATE TRIGGER IF NOT EXISTS prevent_closed_deal_update
        BEFORE UPDATE OF title, value, stage, probability, customer_id, owner_id, expected_close_date
        ON deals
        WHEN OLD.status IN ('WON', 'LOST') AND NEW.status = OLD.status
        BEGIN
            SELECT RAISE(ABORT, 'Closed opportunities cannot be edited.');
        END
        """
    ).execute_if(dialect="sqlite"),
)
