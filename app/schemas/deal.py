from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class DealItemDTO(BaseModel):
    id: str
    dealId: str = Field(..., serialization_alias="dealId", alias="dealId")
    productId: Optional[str] = Field(None, serialization_alias="productId", alias="productId")
    productName: str = Field(..., serialization_alias="productName", alias="productName")
    quantity: int = 1
    unitPrice: float = Field(0.0, serialization_alias="unitPrice", alias="unitPrice")
    discountPercent: float = Field(0.0, serialization_alias="discountPercent", alias="discountPercent")
    billingCycle: str = Field("annual", serialization_alias="billingCycle", alias="billingCycle")
    subtotal: float = 0.0

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class CreateDealItemDTO(BaseModel):
    productId: Optional[str] = Field(None, alias="productId")
    productName: Optional[str] = Field(None, alias="productName")
    quantity: int = Field(1, ge=1, alias="quantity")
    unitPrice: Optional[float] = Field(None, alias="unitPrice")
    discountPercent: float = Field(0.0, ge=0, le=100, alias="discountPercent")
    billingCycle: str = Field("annual", alias="billingCycle")

    model_config = ConfigDict(populate_by_name=True)


class DealBase(BaseModel):
    title: str
    value: float = 0.0
    stage: str = "lead"
    probability: Optional[int] = 20
    customerId: str = Field(..., serialization_alias="customerId", alias="customerId")
    expectedCloseDate: Optional[str] = Field(None, serialization_alias="expectedCloseDate", alias="expectedCloseDate")
    campaignId: Optional[str] = Field(None, serialization_alias="campaignId", alias="campaignId")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class CreateDealDTO(DealBase):
    items: Optional[List[CreateDealItemDTO]] = None


class UpdateDealDTO(BaseModel):
    title: Optional[str] = None
    value: Optional[float] = None
    amount: Optional[float] = None  # Alias cho value
    stage: Optional[str] = None
    probability: Optional[int] = None
    customerId: Optional[str] = Field(None, alias="customerId")
    expectedCloseDate: Optional[str] = Field(None, alias="expectedCloseDate")
    expected_close_date: Optional[str] = Field(None, alias="expected_close_date")
    campaignId: Optional[str] = Field(None, alias="campaignId")
    assigned_to: Optional[str] = Field(None, alias="assigned_to")
    assignedTo: Optional[str] = Field(None, alias="assignedTo")
    owner_id: Optional[str] = Field(None, alias="owner_id")
    ownerId: Optional[str] = Field(None, alias="ownerId")

    model_config = ConfigDict(populate_by_name=True)


class MoveDealStageDTO(BaseModel):
    stage: str
    override: bool = False  # Quyền vượt qua Exit Conditions dành cho Team Leader / Admin


class CloseDealDTO(BaseModel):
    """S5-05: Đóng Deal dạng Won hoặc Lost."""
    stage: str = Field(..., description="'won' hoặc 'lost'")
    actualValue: Optional[float] = Field(None, alias="actualValue")
    signingDate: Optional[str] = Field(None, alias="signingDate")
    lossReason: Optional[str] = Field(None, alias="lossReason")
    lossCompetitor: Optional[str] = Field(None, alias="lossCompetitor")

    model_config = ConfigDict(populate_by_name=True)


class BulkReassignDealsDTO(BaseModel):
    """S5-08: Tái phân bổ hàng loạt cơ hội bán hàng."""
    dealIds: List[str] = Field(..., alias="dealIds")
    newOwnerId: str = Field(..., alias="newOwnerId")
    reason: str = Field(..., min_length=3, alias="reason")

    model_config = ConfigDict(populate_by_name=True)


class DealDTO(DealBase):
    id: str
    ownerId: str = Field(..., serialization_alias="ownerId", alias="ownerId")
    ownerName: Optional[str] = Field(None, serialization_alias="ownerName", alias="ownerName")
    customerName: Optional[str] = Field(None, serialization_alias="customerName", alias="customerName")
    campaignName: Optional[str] = Field(None, serialization_alias="campaignName", alias="campaignName")
    closeDate: Optional[str] = Field(None, serialization_alias="closeDate", alias="closeDate")
    actualValue: Optional[float] = Field(None, serialization_alias="actualValue", alias="actualValue")
    lossReason: Optional[str] = Field(None, serialization_alias="lossReason", alias="lossReason")
    lossCompetitor: Optional[str] = Field(None, serialization_alias="lossCompetitor", alias="lossCompetitor")
    isStalled: bool = Field(False, serialization_alias="isStalled", alias="isStalled")
    lastActivityAt: Optional[str] = Field(None, serialization_alias="lastActivityAt", alias="lastActivityAt")
    reassignmentReason: Optional[str] = Field(None, serialization_alias="reassignmentReason", alias="reassignmentReason")
    items: Optional[List[DealItemDTO]] = Field(default_factory=list, serialization_alias="items", alias="items")
    createdAt: Optional[str] = Field(None, serialization_alias="createdAt", alias="createdAt")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class ForecastPeriodSummary(BaseModel):
    period: str
    dealCount: int
    totalValue: float
    weightedValue: float


class SalesForecastDTO(BaseModel):
    """S5-06: Dự báo doanh thu bán hàng theo trọng số xác suất."""
    totalPipelineValue: float
    totalWeightedForecast: float
    activeDealsCount: int
    periods: List[ForecastPeriodSummary]
    stageBreakdowns: List[Dict[str, Any]]
