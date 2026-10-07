import re
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator

def validate_vietnamese_mst(mst: Optional[str]) -> Optional[str]:
    """
    Xác thực Mã Số Thuế (MST) doanh nghiệp Việt Nam:
    - Chuẩn MST gồm 10 chữ số (doanh nghiệp) hoặc 13 chữ số (10 số + dấu gạch nối + 3 số chi nhánh, hoặc 13 số liền nhau).
    """
    if not mst or not str(mst).strip():
        return None
    cleaned = str(mst).strip().replace(" ", "")
    # Format 10 chữ số: ^\d{10}$ hoặc 13 chữ số: ^\d{10}-\d{3}$ hoặc ^\d{13}$
    if not re.match(r"^(\d{10}|\d{10}-\d{3}|\d{13})$", cleaned):
        raise ValueError("Mã số thuế (MST) không đúng định dạng. MST chuẩn gồm 10 chữ số hoặc 13 chữ số (VD: 0101234567 hoặc 0101234567-001).")
    return cleaned

class CustomerBase(BaseModel):
    fullName: str = Field(..., serialization_alias="fullName")
    email: str
    phone: str
    company: Optional[str] = ""
    status: Optional[str] = "lead"
    healthScore: Optional[int] = Field(85, serialization_alias="healthScore")

    # EP-03 Fields
    taxCode: Optional[str] = Field(None, serialization_alias="taxCode")
    parentCustomerId: Optional[str] = Field(None, serialization_alias="parentCustomerId")
    totalContractValue: Optional[float] = Field(0.0, serialization_alias="totalContractValue")
    lastInteractionAt: Optional[str] = Field(None, serialization_alias="lastInteractionAt")
    riskFlag: Optional[bool] = Field(False, serialization_alias="riskFlag")
    riskReason: Optional[str] = Field(None, serialization_alias="riskReason")
    industry: Optional[str] = ""
    tier: Optional[str] = "Enterprise"
    location: Optional[str] = ""
    website: Optional[str] = ""
    notesSummary: Optional[str] = Field(None, serialization_alias="notesSummary")

class CreateCustomerDTO(CustomerBase):
    ownerName: Optional[str] = None
    tags: Optional[List[str]] = Field(default_factory=list)
    summary: Optional[str] = None

    @field_validator("taxCode")
    @classmethod
    def check_tax_code(cls, v: Optional[str]) -> Optional[str]:
        return validate_vietnamese_mst(v)

class UpdateCustomerDTO(BaseModel):
    fullName: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    status: Optional[str] = None
    healthScore: Optional[int] = None
    taxCode: Optional[str] = None
    parentCustomerId: Optional[str] = None
    totalContractValue: Optional[float] = None
    riskFlag: Optional[bool] = None
    riskReason: Optional[str] = None
    industry: Optional[str] = None
    tier: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None
    notesSummary: Optional[str] = None

    @field_validator("taxCode")
    @classmethod
    def check_tax_code(cls, v: Optional[str]) -> Optional[str]:
        return validate_vietnamese_mst(v)

class UpdateCustomerStatusDTO(BaseModel):
    status: str

class CustomerNoteCreateDTO(BaseModel):
    content: str
    authorName: Optional[str] = "Admin"

class CustomerActivityCreateDTO(BaseModel):
    type: str
    title: str
    description: Optional[str] = ""
    authorName: Optional[str] = "Admin"

class CustomerDTO(CustomerBase):
    id: str
    avatarUrl: Optional[str] = Field(None, serialization_alias="avatarUrl")
    assignedUserId: Optional[str] = Field(None, serialization_alias="assignedUserId")
    ownerName: Optional[str] = Field(None, serialization_alias="ownerName")
    createdAt: Optional[str] = Field(None, serialization_alias="createdAt")
    updatedAt: Optional[str] = Field(None, serialization_alias="updatedAt")
    contactsCount: Optional[int] = Field(0, serialization_alias="contactsCount")
    dealsCount: Optional[int] = Field(0, serialization_alias="dealsCount")
    openTicketsCount: Optional[int] = Field(0, serialization_alias="openTicketsCount")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

class CustomerMergeDTO(BaseModel):
    masterId: str = Field(..., description="ID của khách hàng chính giữ lại")
    duplicateId: str = Field(..., description="ID của khách hàng trùng lặp cần gộp vào")
    fieldOverrides: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Bảng ánh xạ các trường được ghi đè từ khách hàng trùng vào khách hàng chính"
    )

class CustomerHierarchyDTO(BaseModel):
    id: str
    fullName: str
    company: str
    taxCode: Optional[str] = None
    tier: Optional[str] = None
    status: str
    totalContractValue: float
    groupContractValue: float
    children: List["CustomerHierarchyDTO"] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

class StagnantCustomerDTO(BaseModel):
    id: str
    fullName: str
    company: str
    phone: str
    email: str
    status: str
    ownerName: Optional[str] = "Chưa gán"
    lastInteractionAt: Optional[str] = None
    daysInactive: int
    totalContractValue: float
    riskFlag: bool

class RiskScanResultDTO(BaseModel):
    scannedCount: int
    flaggedCount: int
    threshold: int
    details: List[Dict[str, Any]]
