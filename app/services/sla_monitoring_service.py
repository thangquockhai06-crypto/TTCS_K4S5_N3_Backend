from datetime import datetime, timedelta
from typing import List
from sqlalchemy.orm import Session
from app.models.task import Task


class SLAMonitoringService:
    @staticmethod
    def get_at_risk_tasks(db: Session, threshold_hours: int = 4) -> List[Task]:
        now = datetime.utcnow()
        limit_time = now + timedelta(hours=threshold_hours)
        return (
            db.query(Task)
            .filter(
                Task.status.notin_(["completed", "cancelled"]),
                Task.due_date.isnot(None),
                Task.due_date > now,
                Task.due_date <= limit_time,
            )
            .all()
        )
