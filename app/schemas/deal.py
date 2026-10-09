from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class DealBase(BaseModel):
    title: str
    value: float
    stage: str = "lead"
    probability: Optional[int] = 20
    customerId: str = Field(..., serialization_alias="customerId")
    expectedCloseDate: Optional[str] = Field(None, serialization_alias="expectedCloseDate")


class CreateDealDTO(DealBase):
    pass


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
    ownerId: str = Field(..., serialization_alias="ownerId")
    createdAt: Optional[str] = Field(None, serialization_alias="createdAt")
    outcome: str = "OPEN"
    status: str = "OPEN"
    closedAt: Optional[str] = Field(None, serialization_alias="closedAt")
    closedBy: Optional[str] = Field(None, serialization_alias="closedBy")
    actualValue: Optional[Decimal] = Field(None, serialization_alias="actualValue")
    signedDate: Optional[str] = Field(None, serialization_alias="signedDate")
    lostReasonId: Optional[str] = Field(None, serialization_alias="lostReasonId")
    lostReason: Optional[LostReasonSummaryDTO] = Field(None, serialization_alias="lostReason")
    lostReasonNote: Optional[str] = Field(None, serialization_alias="lostReasonNote")
    competitorId: Optional[str] = Field(None, serialization_alias="competitorId")
    competitor: Optional[CompetitorSummaryDTO] = None
    reopenedAt: Optional[str] = Field(None, serialization_alias="reopenedAt")
    reopenedBy: Optional[str] = Field(None, serialization_alias="reopenedBy")
    reopenReason: Optional[str] = Field(None, serialization_alias="reopenReason")
    history: list[DealOutcomeHistoryDTO] = []

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)
