from pydantic import BaseModel
class TeamPerformanceSummaryDTO(BaseModel):
    teamId: str
    score: float
