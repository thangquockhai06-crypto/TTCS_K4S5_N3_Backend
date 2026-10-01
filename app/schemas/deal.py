from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

class DealBase(BaseModel):
    title: str
    value: float
    stage: str = "lead"
    probability: Optional[int] = 20
    customerId: str = Field(..., serialization_alias="customerId")
    expectedCloseDate: Optional[str] = Field(None, serialization_alias="expectedCloseDate")

class CreateDealDTO(DealBase):
    pass

class MoveDealStageDTO(BaseModel):
    stage: str

class DealDTO(DealBase):
    id: str
    ownerId: str = Field(..., serialization_alias="ownerId")
    createdAt: Optional[str] = Field(None, serialization_alias="createdAt")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)
