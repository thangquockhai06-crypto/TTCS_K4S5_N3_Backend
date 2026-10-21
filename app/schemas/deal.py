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
    stage: Optional[str] = None
    probability: Optional[int] = None
    customerId: Optional[str] = Field(None, alias="customerId")
    expectedCloseDate: Optional[str] = Field(None, alias="expectedCloseDate")
    campaignId: Optional[str] = Field(None, alias="campaignId")

    model_config = ConfigDict(populate_by_name=True)



class UpdateDealDTO(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    title: Optional[str] = None
    value: Optional[Decimal] = None
    stage: Optional[str] = None
    probability: Optional[int] = None
    customer_id: Optional[str] = Field(None, alias="customerId", serialization_alias="customerId")
    expected_close_date: Optional[date] = Field(
        None,
        alias="expectedCloseDate",
        serialization_alias="expectedCloseDate",
    )
    owner_id: Optional[str] = Field(None, alias="ownerId", serialization_alias="ownerId")

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not value.strip():
            raise ValueError("Title cannot be blank.")
        return value.strip() if value is not None else value

    @field_validator("value")
    @classmethod
    def validate_value(cls, value: Optional[Decimal]) -> Optional[Decimal]:
        if value is not None and value < 0:
            raise ValueError("Deal value cannot be negative.")
        return value


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



class CloseDealDTO(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    outcome: str
    actual_value: Optional[Decimal] = Field(None, alias="actualValue", serialization_alias="actualValue")
    signed_date: Optional[date] = Field(None, alias="signedDate", serialization_alias="signedDate")
    lost_reason_id: Optional[str] = Field(None, alias="lostReasonId", serialization_alias="lostReasonId")
    lost_reason_note: Optional[str] = Field(None, alias="lostReasonNote", serialization_alias="lostReasonNote")
    competitor_id: Optional[str] = Field(None, alias="competitorId", serialization_alias="competitorId")

    @field_validator("outcome")
    @classmethod
    def normalize_outcome(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in {"WON", "LOST"}:
            raise ValueError("Outcome must be WON or LOST.")
        return normalized

    @field_validator("lost_reason_note")
    @classmethod
    def normalize_note(cls, value: Optional[str]) -> Optional[str]:
        return value.strip() if value is not None else value

    @model_validator(mode="after")
    def validate_outcome_fields(self) -> "CloseDealDTO":
        if self.outcome == "WON":
            if self.actual_value is None:
                raise ValueError("actualValue is required when closing as WON.")
            if self.signed_date is None:
                raise ValueError("signedDate is required when closing as WON.")
            if self.actual_value <= 0:
                raise ValueError("actualValue must be greater than zero.")
            if any(
                value is not None
                for value in (self.lost_reason_id, self.lost_reason_note, self.competitor_id)
            ):
                raise ValueError("LOST-only fields are not allowed when closing as WON.")
        else:
            if self.lost_reason_id is None or not self.lost_reason_id.strip():
                raise ValueError("lostReasonId is required when closing as LOST.")
            if self.actual_value is not None or self.signed_date is not None:
                raise ValueError("WON-only fields are not allowed when closing as LOST.")
        return self


class ReopenDealDTO(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    reopen_reason: str = Field(..., alias="reopenReason", serialization_alias="reopenReason", min_length=5, max_length=2000)

    @field_validator("reopen_reason")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        clean = value.strip()
        if len(clean) < 5:
            raise ValueError("reopenReason must contain at least 5 non-whitespace characters.")
        return clean


class LostReasonSummaryDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    reason: str


class CompetitorSummaryDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str


class DealOutcomeHistoryDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    action: str
    outcome: str
    previous_status: str = Field(..., serialization_alias="previousStatus")
    resulting_status: str = Field(..., serialization_alias="resultingStatus")
    previous_stage: Optional[str] = Field(None, serialization_alias="previousStage")
    resulting_stage: Optional[str] = Field(None, serialization_alias="resultingStage")
    actor_id: Optional[str] = Field(None, serialization_alias="actorId")
    event_at: Optional[datetime] = Field(None, serialization_alias="eventAt")
    closed_at: Optional[datetime] = Field(None, serialization_alias="closedAt")
    closed_by: Optional[str] = Field(None, serialization_alias="closedBy")
    actual_value: Optional[Decimal] = Field(None, serialization_alias="actualValue")
    signed_date: Optional[date] = Field(None, serialization_alias="signedDate")
    lost_reason_id: Optional[str] = Field(None, serialization_alias="lostReasonId")
    lost_reason_note: Optional[str] = Field(None, serialization_alias="lostReasonNote")
    competitor_id: Optional[str] = Field(None, serialization_alias="competitorId")
    reopen_reason: Optional[str] = Field(None, serialization_alias="reopenReason")


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
