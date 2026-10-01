from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class ActivityBase(BaseModel):
    customerId: str = Field(..., serialization_alias="customerId")
    type: str
    title: str
    description: Optional[str] = ""


class CreateActivityDTO(ActivityBase):
    pass


class ActivityDTO(ActivityBase):
    id: str
    userId: str = Field(..., serialization_alias="userId")
    createdAt: Optional[str] = Field(None, serialization_alias="createdAt")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)
