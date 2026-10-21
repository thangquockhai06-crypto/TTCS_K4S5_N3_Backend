from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class WinLossReasonDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    result_type: str  # 'WON' | 'LOST'
    code: str
    reason: str
    description: Optional[str] = None
    is_active: bool


class CreateWinLossReasonDTO(BaseModel):
    result_type: str
    code: str
    reason: str
    description: Optional[str] = None


class UpdateWinLossReasonDTO(BaseModel):
    reason: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class CompetitorDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    website: Optional[str] = None
    strengths: Optional[str] = None
    weaknesses: Optional[str] = None
    win_rate: float


class CreateCompetitorDTO(BaseModel):
    name: str
    website: Optional[str] = None
    strengths: Optional[str] = None
    weaknesses: Optional[str] = None
    win_rate: Optional[float] = 50.0


class UpdateCompetitorDTO(BaseModel):
    name: Optional[str] = None
    website: Optional[str] = None
    strengths: Optional[str] = None
    weaknesses: Optional[str] = None
    win_rate: Optional[float] = None
