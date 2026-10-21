from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class CampaignBase(BaseModel):
    name: str
    code: str
    type: str = "Web Form"
    status: str = "Active"
    budget: float = 0.0
    expectedRevenue: float = Field(0.0, serialization_alias="expectedRevenue", alias="expectedRevenue")
    startDate: Optional[str] = Field(None, serialization_alias="startDate", alias="startDate")
    endDate: Optional[str] = Field(None, serialization_alias="endDate", alias="endDate")
    description: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class CreateCampaignDTO(CampaignBase):
    pass


class UpdateCampaignDTO(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    budget: Optional[float] = None
    expectedRevenue: Optional[float] = Field(None, serialization_alias="expectedRevenue", alias="expectedRevenue")
    startDate: Optional[str] = Field(None, serialization_alias="startDate", alias="startDate")
    endDate: Optional[str] = Field(None, serialization_alias="endDate", alias="endDate")
    description: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class CampaignDTO(CampaignBase):
    id: str
    totalLeads: int = Field(0, serialization_alias="totalLeads", alias="totalLeads")
    totalDeals: int = Field(0, serialization_alias="totalDeals", alias="totalDeals")
    actualRevenue: float = Field(0.0, serialization_alias="actualRevenue", alias="actualRevenue")
    leads_count: int = 0
    deals_count: int = 0
    actual_revenue: float = 0.0
    expected_revenue: float = 0.0
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    created_at: Optional[str] = None
    createdAt: Optional[str] = Field(None, serialization_alias="createdAt", alias="createdAt")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)
