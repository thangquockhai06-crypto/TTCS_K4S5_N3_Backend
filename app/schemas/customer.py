from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

class CustomerBase(BaseModel):
    fullName: str = Field(..., serialization_alias="fullName")
    email: str
    phone: str
    company: Optional[str] = ""
    status: Optional[str] = "lead"
    healthScore: Optional[int] = Field(85, serialization_alias="healthScore")

class CreateCustomerDTO(CustomerBase):
    pass

class UpdateCustomerStatusDTO(BaseModel):
    status: str

class CustomerNoteCreateDTO(BaseModel):
    content: str
    authorName: Optional[str] = "Admin"

class CustomerActivityCreateDTO(BaseModel):
    type: str
    title: str
    description: Optional[str] = ""
    authorName: Optional[str] = "Admin"

class CustomerDTO(CustomerBase):
    id: str
    avatarUrl: Optional[str] = Field(None, serialization_alias="avatarUrl")
    createdAt: Optional[str] = Field(None, serialization_alias="createdAt")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)
