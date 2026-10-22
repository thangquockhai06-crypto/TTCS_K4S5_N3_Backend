from pydantic import BaseModel
from datetime import datetime
class TaskHistoryDTO(BaseModel):
    taskId: str
    oldStatus: str
    newStatus: str
    updatedAt: datetime
