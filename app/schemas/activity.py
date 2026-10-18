from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class ActivityBase(BaseModel):
    customerId: Optional[str] = Field(None, serialization_alias="customerId")
    dealId: Optional[str] = Field(None, serialization_alias="dealId")
    type: str = Field(..., description="call, meeting, email, note, deal_change, status_change")
    title: str
    description: Optional[str] = ""
    notes: Optional[str] = None


class CreateActivityDTO(ActivityBase):
    pass


class ActivityDTO(ActivityBase):
    id: str
    userId: str = Field(..., serialization_alias="userId")
    userName: Optional[str] = Field(None, serialization_alias="userName")
    customerName: Optional[str] = Field(None, serialization_alias="customerName")
    dealTitle: Optional[str] = Field(None, serialization_alias="dealTitle")
    createdAt: Optional[str] = Field(None, serialization_alias="createdAt")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)
