from typing import Optional, Any
from pydantic import BaseModel, Field, ConfigDict


class AutomationRuleDTO(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    isActive: bool = Field(True, serialization_alias="isActive")
    triggerEntity: str = Field(..., serialization_alias="triggerEntity")
    triggerEvent: str = Field(..., serialization_alias="triggerEvent")
    conditions: Optional[Any] = None
    actionType: str = Field(..., serialization_alias="actionType")
    actionConfig: Optional[Any] = Field(None, serialization_alias="actionConfig")
    createdAt: Optional[str] = Field(None, serialization_alias="createdAt")
    updatedAt: Optional[str] = Field(None, serialization_alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class CreateAutomationRuleDTO(BaseModel):
    name: str
    description: Optional[str] = None
    isActive: bool = Field(True, serialization_alias="isActive")
    triggerEntity: str = Field(..., serialization_alias="triggerEntity")
    triggerEvent: str = Field(..., serialization_alias="triggerEvent")
    conditions: Optional[Any] = None
    actionType: str = Field(..., serialization_alias="actionType")
    actionConfig: Any = Field(..., serialization_alias="actionConfig")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class UpdateAutomationRuleDTO(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    isActive: Optional[bool] = Field(None, serialization_alias="isActive")
    triggerEntity: Optional[str] = Field(None, serialization_alias="triggerEntity")
    triggerEvent: Optional[str] = Field(None, serialization_alias="triggerEvent")
    conditions: Optional[Any] = None
    actionType: Optional[str] = Field(None, serialization_alias="actionType")
    actionConfig: Optional[Any] = Field(None, serialization_alias="actionConfig")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class AutomationLogDTO(BaseModel):
    id: str
    ruleId: Optional[str] = Field(None, serialization_alias="ruleId")
    ruleName: str = Field(..., serialization_alias="ruleName")
    triggerEvent: str = Field(..., serialization_alias="triggerEvent")
    entityType: str = Field(..., serialization_alias="entityType")
    entityId: str = Field(..., serialization_alias="entityId")
    actionType: str = Field(..., serialization_alias="actionType")
    status: str
    details: Optional[str] = None
    executedAt: str = Field(..., serialization_alias="executedAt")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)
