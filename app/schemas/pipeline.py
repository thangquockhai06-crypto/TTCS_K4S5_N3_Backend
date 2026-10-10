from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class PipelineStageDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    stage_key: str
    order_index: int
    probability: int
    exit_rules: Optional[str] = None
    color: str
    is_won: bool
    is_lost: bool



class CreatePipelineStageDTO(BaseModel):
    name: str
    stage_key: str
    order_index: Optional[int] = 0
    probability: int = 20
    exit_rules: Optional[str] = None
    color: str = "#2563eb"
    is_won: bool = False
    is_lost: bool = False


class UpdatePipelineStageDTO(BaseModel):
    name: Optional[str] = None
    probability: Optional[int] = None
    exit_rules: Optional[str] = None
    color: Optional[str] = None


class ReorderStageItem(BaseModel):
    id: str
    order_index: int


class ReorderStagesDTO(BaseModel):
    items: Optional[List[ReorderStageItem]] = None
    ordered_stage_ids: Optional[List[str]] = None
