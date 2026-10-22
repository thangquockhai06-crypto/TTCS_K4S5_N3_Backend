from pydantic import BaseModel
class TaskPriorityUpdateDTO(BaseModel):
    priority: str
