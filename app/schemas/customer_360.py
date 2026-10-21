from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.customer import CustomerDTO, CustomerHierarchyDTO
from app.schemas.contact import ContactDTO
from app.schemas.support_ticket import SupportTicketDTO

class Customer360ActivityItem(BaseModel):
    id: str
    type: str
    title: str
    description: Optional[str] = None
    createdAt: str
    userName: Optional[str] = None

class Customer360DealItem(BaseModel):
    id: str
    title: str
    value: float
    stage: str
    probability: int
    expectedCloseDate: Optional[str] = None
    createdAt: str

class Customer360NoteItem(BaseModel):
    id: str
    content: str
    authorName: Optional[str] = None
    createdAt: str

class Customer360DocumentItem(BaseModel):
    id: str
    name: str
    size: str
    type: str
    uploadedAt: str
    uploadedBy: str

class Customer360DTO(BaseModel):
    customer: CustomerDTO
    contacts: List[ContactDTO] = Field(default_factory=list)
    deals: List[Customer360DealItem] = Field(default_factory=list)
    activities: List[Customer360ActivityItem] = Field(default_factory=list)
    notes: List[Customer360NoteItem] = Field(default_factory=list)
    tickets: List[SupportTicketDTO] = Field(default_factory=list)
    documents: List[Customer360DocumentItem] = Field(default_factory=list)
    corporateHierarchy: Optional[CustomerHierarchyDTO] = None
    totalContractValue: float = 0.0
    groupContractValue: float = 0.0
    riskFlag: bool = False
    riskReason: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)
