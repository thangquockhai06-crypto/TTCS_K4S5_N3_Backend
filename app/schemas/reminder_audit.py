from pydantic import BaseModel
from typing import List
from datetime import datetime


class ReminderSettingAuditLogDTO(BaseModel):
    userId: str
    previousMilestones: List[int]
    newMilestones: List[int]
    changedBy: str
    changedAt: datetime
