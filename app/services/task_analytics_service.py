from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.models.task import Task
from app.schemas.task_stats import TaskCompletionRateDTO


class TaskAnalyticsService:
    @staticmethod
    def calculate_completion_rate(db: Session, user_id: str) -> TaskCompletionRateDTO:
        tasks = db.query(Task).filter(Task.assignee_id == user_id).all()
        total = len(tasks)
        completed = sum(1 for t in tasks if t.status == "completed" or t.is_completed)
        overdue = sum(1 for t in tasks if t.is_overdue)
        in_progress = sum(1 for t in tasks if t.status == "in_progress")

        rate = (completed / total * 100.0) if total > 0 else 0.0
        return TaskCompletionRateDTO(
            totalTasks=total,
            completedTasks=completed,
            overdueTasks=overdue,
            inProgressTasks=in_progress,
            completionRatePercentage=round(rate, 2),
        )
