from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.task import Task


class TeamWorkloadBalancer:
    @staticmethod
    def get_team_workload_distribution(db: Session, team_id: str) -> List[Dict[str, Any]]:
        members = db.query(User).filter(User.team_id == team_id).all()
        distribution = []
        for m in members:
            count = db.query(Task).filter(
                Task.assignee_id == m.id,
                Task.status.notin_(["completed", "cancelled"]),
            ).count()
            distribution.append({
                "userId": m.id,
                "fullName": m.full_name,
                "openTasksCount": count,
            })
        return sorted(distribution, key=lambda x: x["openTasksCount"], reverse=True)
