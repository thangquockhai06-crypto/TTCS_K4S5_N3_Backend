from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class ContractItemDTO(BaseModel):
    id: Optional[str] = None
    productId: Optional[str] = Field(None, serialization_alias="productId")
    productName: str = Field(..., serialization_alias="productName")
    quantity: int = 1
    unit: str = "Gói"
    unitPrice: float = Field(0.0, serialization_alias="unitPrice")
    discountAmount: float = Field(0.0, serialization_alias="discountAmount")
    lineTotal: float = Field(0.0, serialization_alias="lineTotal")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class CreateContractDTO(BaseModel):
    quotationId: str = Field(..., serialization_alias="quotationId")
    contractNumber: str = Field(..., serialization_alias="contractNumber")
    title: Optional[str] = None
    signingDate: str = Field(..., serialization_alias="signingDate")
    effectiveDate: str = Field(..., serialization_alias="effectiveDate")
    expiryDate: str = Field(..., serialization_alias="expiryDate")
    paymentTerms: Optional[str] = Field(None, serialization_alias="paymentTerms")
    deliveryTerms: Optional[str] = Field(None, serialization_alias="deliveryTerms")
    templateId: Optional[str] = Field(None, serialization_alias="templateId")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class ContractDTO(BaseModel):
    id: str
    contractNumber: str = Field(..., serialization_alias="contractNumber")
    title: str
    quotationId: str = Field(..., serialization_alias="quotationId")
    dealId: str = Field(..., serialization_alias="dealId")
    dealTitle: Optional[str] = Field(None, serialization_alias="dealTitle")
    customerId: str = Field(..., serialization_alias="customerId")
    customerName: Optional[str] = Field(None, serialization_alias="customerName")
    customerCompany: Optional[str] = Field(None, serialization_alias="customerCompany")
    customerTaxCode: Optional[str] = Field(None, serialization_alias="customerTaxCode")
    ownerId: str = Field(..., serialization_alias="ownerId")
    ownerName: Optional[str] = Field(None, serialization_alias="ownerName")

    totalValue: float = Field(0.0, serialization_alias="totalValue")
    totalInWords: Optional[str] = Field(None, serialization_alias="totalInWords")
    signingDate: str = Field(..., serialization_alias="signingDate")
    effectiveDate: str = Field(..., serialization_alias="effectiveDate")
    expiryDate: str = Field(..., serialization_alias="expiryDate")
    remainingDays: int = Field(0, serialization_alias="remainingDays")
    isExpiringSoon: bool = Field(False, serialization_alias="isExpiringSoon")
    isExpired: bool = Field(False, serialization_alias="isExpired")

    paymentTerms: Optional[str] = Field(None, serialization_alias="paymentTerms")
    deliveryTerms: Optional[str] = Field(None, serialization_alias="deliveryTerms")
    status: str = "active"
    templateId: Optional[str] = Field(None, serialization_alias="templateId")

    items: List[ContractItemDTO] = Field([], serialization_alias="items")
    createdAt: Optional[str] = Field(None, serialization_alias="createdAt")
    updatedAt: Optional[str] = Field(None, serialization_alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class ContractRenewalDTO(BaseModel):
    title: Optional[str] = None
    expectedCloseDate: Optional[str] = Field(None, serialization_alias="expectedCloseDate")
    notes: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)
