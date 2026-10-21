from pydantic import BaseModel
from typing import List
class TaskBulkActionDTO(BaseModel):
    taskIds: List[str]
    action: str
