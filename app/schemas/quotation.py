from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.catalog_item import QuotationLineCreateDTO, QuotationLineDTO

class QuotationBase(BaseModel):
    quoteNumber: str = Field(..., serialization_alias="quoteNumber")
    title: str
    customerId: str = Field(..., serialization_alias="customerId")
    totalAmount: float = Field(0.0, serialization_alias="totalAmount")
    status: Optional[str] = "draft"
    validUntil: Optional[str] = Field(None, serialization_alias="validUntil")
    items: List[QuotationLineCreateDTO] = Field(default_factory=list)


class CreateQuotationDTO(QuotationBase):
    pass


class QuotationDTO(QuotationBase):
    id: str
    ownerId: str = Field(..., serialization_alias="ownerId")
    createdAt: Optional[str] = Field(None, serialization_alias="createdAt")
    items: List[QuotationLineDTO] = Field(default_factory=list)
    discount_approval_required: bool = Field(False, serialization_alias="requiresDiscountApproval")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)
