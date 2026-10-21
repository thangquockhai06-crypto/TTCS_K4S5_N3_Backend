from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr, ConfigDict, model_validator


class LeadBase(BaseModel):
    fullName: str = Field(..., serialization_alias="fullName", alias="fullName")
    email: str
    phone: Optional[str] = None
    company: Optional[str] = None
    jobTitle: Optional[str] = Field(None, serialization_alias="jobTitle", alias="jobTitle")
    source: str = "Web Form"
    campaignId: Optional[str] = Field(None, serialization_alias="campaignId", alias="campaignId")
    region: Optional[str] = "Miền Bắc"
    industry: Optional[str] = "Công nghệ"
    companySize: Optional[str] = Field("11-50", serialization_alias="companySize", alias="companySize")
    annualBudget: Optional[float] = Field(0.0, serialization_alias="annualBudget", alias="annualBudget")
    notes: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def normalize_lead_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "full_name" in data and "fullName" not in data:
                data["fullName"] = data["full_name"]
            elif ("first_name" in data or "last_name" in data) and "fullName" not in data:
                data["fullName"] = f"{data.get('last_name', '')} {data.get('first_name', '')}".strip() or "Khách hàng mới"
            if "company_name" in data and "company" not in data:
                data["company"] = data["company_name"]
            if "title" in data and "jobTitle" not in data:
                data["jobTitle"] = data["title"]
            elif "job_title" in data and "jobTitle" not in data:
                data["jobTitle"] = data["job_title"]
            if "campaign_id" in data and "campaignId" not in data:
                data["campaignId"] = data["campaign_id"]
        return data


class CreateLeadDTO(LeadBase):
    assignedUserId: Optional[str] = Field(None, serialization_alias="assignedUserId", alias="assignedUserId")


class UpdateLeadDTO(BaseModel):
    fullName: Optional[str] = Field(None, serialization_alias="fullName", alias="fullName")
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    jobTitle: Optional[str] = Field(None, serialization_alias="jobTitle", alias="jobTitle")
    source: Optional[str] = None
    campaignId: Optional[str] = Field(None, serialization_alias="campaignId", alias="campaignId")
    region: Optional[str] = None
    industry: Optional[str] = None
    companySize: Optional[str] = Field(None, serialization_alias="companySize", alias="companySize")
    annualBudget: Optional[float] = Field(None, serialization_alias="annualBudget", alias="annualBudget")
    status: Optional[str] = None
    assignedUserId: Optional[str] = Field(None, serialization_alias="assignedUserId", alias="assignedUserId")
    notes: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class PublicLeadSubmissionDTO(BaseModel):
    """S4-01: Form thu thập khách hàng tiềm năng nhúng công khai."""
    fullName: str = Field(..., alias="fullName")
    email: EmailStr
    phone: Optional[str] = None
    company: Optional[str] = None
    message: Optional[str] = None
    campaignCode: Optional[str] = Field(None, alias="campaignCode")
    recaptchaToken: Optional[str] = Field(None, alias="recaptchaToken")

    model_config = ConfigDict(populate_by_name=True)


class RejectLeadDTO(BaseModel):
    """S4-07: Từ chối lead kèm lý do bắt buộc."""
    rejectionReason: str = Field(..., alias="rejectionReason")

    model_config = ConfigDict(populate_by_name=True)


class MergeLeadsDTO(BaseModel):
    """S4-04: Gộp 2 hồ sơ lead trùng lặp."""
    primaryLeadId: str = Field(..., alias="primaryLeadId")
    duplicateLeadId: Optional[str] = Field(None, alias="duplicateLeadId")
    keepFields: Optional[Dict[str, str]] = Field(default_factory=dict, alias="keepFields")

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="before")
    @classmethod
    def normalize_merge(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "primary_lead_id" in data and "primaryLeadId" not in data:
                data["primaryLeadId"] = data["primary_lead_id"]
            if "duplicate_lead_ids" in data and "duplicateLeadId" not in data:
                ids = data.get("duplicate_lead_ids") or []
                if isinstance(ids, list) and len(ids) > 0:
                    data["duplicateLeadId"] = ids[0]
            elif "duplicate_lead_id" in data and "duplicateLeadId" not in data:
                data["duplicateLeadId"] = data["duplicate_lead_id"]
        return data


class ConvertLeadDTO(BaseModel):
    """S4-08: Chuyển đổi Lead thành Customer, Contact và Deal."""
    existingCustomerId: Optional[str] = Field(None, alias="existingCustomerId")
    customerName: Optional[str] = Field(None, alias="customerName")
    taxCode: Optional[str] = Field(None, alias="taxCode")
    createDeal: bool = Field(True, alias="createDeal")
    dealTitle: Optional[str] = Field(None, alias="dealTitle")
    dealValue: Optional[float] = Field(None, alias="dealValue")
    expectedCloseDate: Optional[str] = Field(None, alias="expectedCloseDate")

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="before")
    @classmethod
    def normalize_convert(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "create_deal" in data and "createDeal" not in data:
                data["createDeal"] = data["create_deal"]
            if "deal_title" in data and "dealTitle" not in data:
                data["dealTitle"] = data["deal_title"]
            if "deal_value" in data and "dealValue" not in data:
                data["dealValue"] = data["deal_value"]
            if "expected_close_date" in data and "expectedCloseDate" not in data:
                data["expectedCloseDate"] = data["expected_close_date"]
            if "existing_customer_id" in data and "existingCustomerId" not in data:
                data["existingCustomerId"] = data["existing_customer_id"]
            if "customer_name" in data and "customerName" not in data:
                data["customerName"] = data["customer_name"]
            if "tax_code" in data and "taxCode" not in data:
                data["taxCode"] = data["tax_code"]
        return data


class LeadDTO(LeadBase):
    id: str
    score: int = 50
    scoreGrade: str = Field("Warm", serialization_alias="scoreGrade", alias="scoreGrade")
    status: str = "UNASSIGNED"
    assignedUserId: Optional[str] = Field(None, serialization_alias="assignedUserId", alias="assignedUserId")
    assignedUserName: Optional[str] = Field(None, serialization_alias="assignedUserName", alias="assignedUserName")
    assignedAt: Optional[str] = Field(None, serialization_alias="assignedAt", alias="assignedAt")
    rejectionReason: Optional[str] = Field(None, serialization_alias="rejectionReason", alias="rejectionReason")
    slaDeadline: Optional[str] = Field(None, serialization_alias="slaDeadline", alias="slaDeadline")
    slaOverdue: bool = Field(False, serialization_alias="slaOverdue", alias="slaOverdue")
    slaRemainingHours: Optional[float] = Field(None, serialization_alias="slaRemainingHours", alias="slaRemainingHours")
    convertedCustomerId: Optional[str] = Field(None, serialization_alias="convertedCustomerId", alias="convertedCustomerId")
    convertedDealId: Optional[str] = Field(None, serialization_alias="convertedDealId", alias="convertedDealId")
    convertedAt: Optional[str] = Field(None, serialization_alias="convertedAt", alias="convertedAt")
    campaignName: Optional[str] = Field(None, serialization_alias="campaignName", alias="campaignName")
    createdAt: Optional[str] = Field(None, serialization_alias="createdAt", alias="createdAt")
    updatedAt: Optional[str] = Field(None, serialization_alias="updatedAt", alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class LeadRoutingRuleDTO(BaseModel):
    id: str
    name: str
    priority: int
    ruleType: str = Field(..., serialization_alias="ruleType", alias="ruleType")
    criterionValue: Optional[str] = Field(None, serialization_alias="criterionValue", alias="criterionValue")
    targetUserId: Optional[str] = Field(None, serialization_alias="targetUserId", alias="targetUserId")
    targetTeamId: Optional[str] = Field(None, serialization_alias="targetTeamId", alias="targetTeamId")
    isActive: bool = Field(True, serialization_alias="isActive", alias="isActive")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)
