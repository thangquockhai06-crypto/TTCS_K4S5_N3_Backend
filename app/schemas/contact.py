from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

class ContactBase(BaseModel):
    fullName: str = Field(..., serialization_alias="fullName")
    email: Optional[str] = None
    phone: Optional[str] = None
    position: Optional[str] = None
    role: str = Field("Decider", description="Decider, Influencer, Buyer, Gatekeeper, User")
    isPrimary: bool = Field(False, serialization_alias="isPrimary")
    isActive: bool = Field(True, serialization_alias="isActive")
    notes: Optional[str] = None

class ContactCreateDTO(ContactBase):
    customerId: Optional[str] = Field(None, serialization_alias="customerId")

class ContactUpdateDTO(BaseModel):
    fullName: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    position: Optional[str] = None
    role: Optional[str] = None
    isPrimary: Optional[bool] = None
    isActive: Optional[bool] = None
    notes: Optional[str] = None

class TransferContactDTO(BaseModel):
    newCustomerId: str = Field(..., description="ID của khách hàng doanh nghiệp mới nhận người liên hệ này")
    reason: Optional[str] = Field(None, description="Lý do điều chuyển công tác/công ty")

class ContactDTO(ContactBase):
    id: str
    customerId: str = Field(..., serialization_alias="customerId")
    createdAt: Optional[str] = Field(None, serialization_alias="createdAt")
    updatedAt: Optional[str] = Field(None, serialization_alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)
