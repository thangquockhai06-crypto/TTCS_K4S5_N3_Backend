from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

class SupportTicketBase(BaseModel):
    title: str
    description: Optional[str] = None
    priority: str = Field("medium", description="low, medium, high, urgent")
    status: str = Field("open", description="open, in_progress, resolved, closed")
    dueDate: Optional[str] = Field(None, serialization_alias="dueDate")
    assignedUserId: Optional[str] = Field(None, serialization_alias="assignedUserId")

class CreateSupportTicketDTO(SupportTicketBase):
    customerId: Optional[str] = Field(None, serialization_alias="customerId")

class UpdateSupportTicketDTO(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    dueDate: Optional[str] = None
    assignedUserId: Optional[str] = None
    resolvedAt: Optional[str] = None

class SupportTicketDTO(SupportTicketBase):
    id: str
    customerId: str = Field(..., serialization_alias="customerId")
    ticketCode: str = Field(..., serialization_alias="ticketCode")
    isOverdue: bool = Field(False, serialization_alias="isOverdue")
    assignedUserName: Optional[str] = Field(None, serialization_alias="assignedUserName")
    resolvedAt: Optional[str] = Field(None, serialization_alias="resolvedAt")
    createdAt: Optional[str] = Field(None, serialization_alias="createdAt")
    updatedAt: Optional[str] = Field(None, serialization_alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)
