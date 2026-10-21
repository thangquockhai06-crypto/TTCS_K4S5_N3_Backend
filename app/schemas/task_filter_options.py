from pydantic import BaseModel
class TaskFilterOptionsDTO(BaseModel):
    search: str = ''
