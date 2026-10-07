from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class QuotationBase(BaseModel):
    quoteNumber: str = Field(..., serialization_alias="quoteNumber")
    title: str
    customerId: str = Field(..., serialization_alias="customerId")
    totalAmount: float = Field(0.0, serialization_alias="totalAmount")
    status: Optional[str] = "draft"
    validUntil: Optional[str] = Field(None, serialization_alias="validUntil")


class CreateQuotationDTO(QuotationBase):
    pass


class QuotationDTO(QuotationBase):
    id: str
    ownerId: str = Field(..., serialization_alias="ownerId")
    createdAt: Optional[str] = Field(None, serialization_alias="createdAt")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)
