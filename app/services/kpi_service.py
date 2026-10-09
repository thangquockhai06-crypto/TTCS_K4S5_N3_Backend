from datetime import date
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.deal import Deal


class KPIService:
    """Query-time sales KPI aggregation; reopened deals naturally stop counting."""

    @staticmethod
    def get_won_value_for_owner(
        db: Session,
        owner_id: str,
        period_start: date,
        period_end: date,
    ) -> Decimal:
        if period_end < period_start:
            raise ValueError("period_end must not be before period_start")
        total = (
            db.query(func.coalesce(func.sum(Deal.actual_value), 0))
            .filter(
                Deal.owner_id == owner_id,
                Deal.status == "WON",
                Deal.signed_date >= period_start,
                Deal.signed_date <= period_end,
            )
            .scalar()
        )
        return Decimal(str(total or 0)).quantize(Decimal("0.01"))
