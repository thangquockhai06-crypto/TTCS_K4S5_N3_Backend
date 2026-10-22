from pydantic import BaseModel
from typing import Dict
class TaskStatusChartDTO(BaseModel):
    breakdown: Dict[str, int]
