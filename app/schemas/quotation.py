from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class QuoteLineItemDTO(BaseModel):
    id: Optional[str] = None
    productId: Optional[str] = Field(None, serialization_alias="productId")
    productCode: Optional[str] = Field(None, serialization_alias="productCode")
    productName: str = Field(..., serialization_alias="productName")
    description: Optional[str] = None
    quantity: int = 1
    unit: str = "Gói"
    unitPrice: float = Field(0.0, serialization_alias="unitPrice")
    discountType: str = Field("percent", serialization_alias="discountType")  # 'percent' | 'amount'
    discountValue: float = Field(0.0, serialization_alias="discountValue")
    discountAmount: float = Field(0.0, serialization_alias="discountAmount")
    floorPrice: Optional[float] = Field(None, serialization_alias="floorPrice")
    vatRate: float = Field(10.0, serialization_alias="vatRate")
    vatAmount: float = Field(0.0, serialization_alias="vatAmount")
    lineTotal: float = Field(0.0, serialization_alias="lineTotal")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class QuoteApprovalHistoryDTO(BaseModel):
    id: str
    action: str
    approvalLevel: Optional[str] = Field(None, serialization_alias="approvalLevel")
    performedById: Optional[str] = Field(None, serialization_alias="performedById")
    performedByName: str = Field(..., serialization_alias="performedByName")
    performedByRole: str = Field(..., serialization_alias="performedByRole")
    comment: Optional[str] = None
    createdAt: str = Field(..., serialization_alias="createdAt")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class CreateQuotationDTO(BaseModel):
    dealId: Optional[str] = Field(None, serialization_alias="dealId")
    quoteNumber: Optional[str] = Field(None, serialization_alias="quoteNumber")
    title: str
    customerId: str = Field(..., serialization_alias="customerId")
    items: List[QuoteLineItemDTO] = []
    validUntil: Optional[str] = Field(None, serialization_alias="validUntil")
    paymentTerms: Optional[str] = Field(None, serialization_alias="paymentTerms")
    deliveryTerms: Optional[str] = Field(None, serialization_alias="deliveryTerms")
    notes: Optional[str] = None
    status: Optional[str] = "draft"
    discountThresholdPercent: Optional[float] = Field(15.0, serialization_alias="discountThresholdPercent")
    templateId: Optional[str] = Field(None, serialization_alias="templateId")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class UpdateQuotationDTO(BaseModel):
    title: Optional[str] = None
    items: Optional[List[QuoteLineItemDTO]] = None
    validUntil: Optional[str] = Field(None, serialization_alias="validUntil")
    paymentTerms: Optional[str] = Field(None, serialization_alias="paymentTerms")
    deliveryTerms: Optional[str] = Field(None, serialization_alias="deliveryTerms")
    notes: Optional[str] = None
    status: Optional[str] = None
    templateId: Optional[str] = Field(None, serialization_alias="templateId")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class QuoteApprovalDecisionDTO(BaseModel):
    action: str = Field(..., description="approved | rejected | returned_for_edit")
    comment: Optional[str] = Field(None, description="Bắt buộc khi từ chối hoặc yêu cầu sửa đổi")


class QuotationDTO(BaseModel):
    id: str
    quoteNumber: str = Field(..., serialization_alias="quoteNumber")
    title: str
    dealId: Optional[str] = Field(None, serialization_alias="dealId")
    dealTitle: Optional[str] = Field(None, serialization_alias="dealTitle")
    customerId: str = Field(..., serialization_alias="customerId")
    customerName: Optional[str] = Field(None, serialization_alias="customerName")
    customerCompany: Optional[str] = Field(None, serialization_alias="customerCompany")
    customerEmail: Optional[str] = Field(None, serialization_alias="customerEmail")
    customerPhone: Optional[str] = Field(None, serialization_alias="customerPhone")
    customerAddress: Optional[str] = Field(None, serialization_alias="customerAddress")
    customerTaxCode: Optional[str] = Field(None, serialization_alias="customerTaxCode")
    ownerId: str = Field(..., serialization_alias="ownerId")
    ownerName: Optional[str] = Field(None, serialization_alias="ownerName")

    # S7-03: Versioning
    version: int = 1
    isEffective: bool = Field(True, serialization_alias="isEffective")
    parentQuoteId: Optional[str] = Field(None, serialization_alias="parentQuoteId")

    # S7-01: Pricing
    items: List[QuoteLineItemDTO] = []
    subtotal: float = 0.0
    totalDiscountAmount: float = Field(0.0, serialization_alias="totalDiscountAmount")
    totalDiscountPercent: float = Field(0.0, serialization_alias="totalDiscountPercent")
    vatAmount: float = Field(0.0, serialization_alias="vatAmount")
    grandTotal: float = Field(0.0, serialization_alias="grandTotal")
    totalAmount: float = Field(0.0, serialization_alias="totalAmount")
    totalInWords: Optional[str] = Field(None, serialization_alias="totalInWords")

    # S7-02: Approvals
    discountThresholdPercent: float = Field(15.0, serialization_alias="discountThresholdPercent")
    requiresApproval: bool = Field(False, serialization_alias="requiresApproval")
    approvalLevel: Optional[str] = Field(None, serialization_alias="approvalLevel")
    approvalHistory: List[QuoteApprovalHistoryDTO] = Field([], serialization_alias="approvalHistory")

    # Terms & Status
    status: str = "draft"
    validUntil: Optional[str] = Field(None, serialization_alias="validUntil")
    paymentTerms: Optional[str] = Field(None, serialization_alias="paymentTerms")
    deliveryTerms: Optional[str] = Field(None, serialization_alias="deliveryTerms")
    notes: Optional[str] = None

    # S7-06: Share Link
    accessToken: Optional[str] = Field(None, serialization_alias="accessToken")
    shareUrl: Optional[str] = Field(None, serialization_alias="shareUrl")
    templateId: Optional[str] = Field(None, serialization_alias="templateId")

    createdAt: Optional[str] = Field(None, serialization_alias="createdAt")
    updatedAt: Optional[str] = Field(None, serialization_alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class QuoteCompareDTO(BaseModel):
    versionA: QuotationDTO = Field(..., serialization_alias="versionA")
    versionB: QuotationDTO = Field(..., serialization_alias="versionB")
    priceDifference: float = Field(0.0, serialization_alias="priceDifference")
    discountDifference: float = Field(0.0, serialization_alias="discountDifference")
    itemsModified: bool = Field(False, serialization_alias="itemsModified")
    termsModified: bool = Field(False, serialization_alias="termsModified")
    summary: str

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class PublicQuoteResponseDTO(BaseModel):
    action: str = Field(..., description="accepted | rejected")
    comment: Optional[str] = None
    signerName: Optional[str] = Field(None, serialization_alias="signerName")
