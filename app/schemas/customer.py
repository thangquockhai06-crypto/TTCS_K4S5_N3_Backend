from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

class CustomerBase(BaseModel):
    fullName: str = Field(..., serialization_alias="fullName")
    email: str
    phone: str
    company: Optional[str] = ""
    status: Optional[str] = "lead"
    healthScore: Optional[int] = Field(85, serialization_alias="healthScore")
    industry: Optional[str] = None
    companySize: Optional[str] = Field(None, serialization_alias="companySize")
    region: Optional[str] = None
    taxCode: Optional[str] = Field(None, serialization_alias="taxCode")
    website: Optional[str] = None

class CreateCustomerDTO(CustomerBase):
    contacts: List["ContactCreateDTO"] = Field(default_factory=list)

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

class ContactCreateDTO(BaseModel):
    fullName: str = Field(..., min_length=1, max_length=150)
    phone: str = Field(..., min_length=1, max_length=30)
    email: Optional[str] = None
    isPrimary: bool = Field(False, serialization_alias="isPrimary")

    model_config = ConfigDict(populate_by_name=True)


class ContactDTO(BaseModel):
    id: str
    fullName: str = Field(..., serialization_alias="fullName")
    phone: str
    email: Optional[str] = None
    isPrimary: bool = Field(False, serialization_alias="isPrimary")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

class AssignedUserDTO(BaseModel):
    id: str
    fullName: str = Field(..., serialization_alias="fullName")
    avatarThumbnailUrl: Optional[str] = Field(None, serialization_alias="avatarThumbnailUrl")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class CustomerDTO(CustomerBase):
    id: str
    assignedUserId: Optional[str] = Field(None, serialization_alias="assignedUserId")
    assignedUser: Optional[AssignedUserDTO] = Field(None, serialization_alias="assignedUser")
    avatarUrl: Optional[str] = Field(None, serialization_alias="avatarUrl")
    contacts: List[ContactDTO] = Field(default_factory=list)
    primaryContact: Optional[ContactDTO] = Field(None, serialization_alias="primaryContact")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)
