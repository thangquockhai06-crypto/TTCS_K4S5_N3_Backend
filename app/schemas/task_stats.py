from pydantic import BaseModel, ConfigDict
from typing import List, Optional


class TaskCompletionRateDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    totalTasks: int
    completedTasks: int
    overdueTasks: int
    inProgressTasks: int
    completionRatePercentage: float


class MemberWorkloadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    userId: str
    fullName: str
    activeTasksCount: int
    overdueCount: int
    riskLevel: str  # low, medium, high, critical
