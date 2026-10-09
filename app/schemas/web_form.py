import re
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

# Regex kiểm tra số điện thoại di động Việt Nam (10 số, đầu số 03, 05, 07, 08, 09)
VN_PHONE_REGEX = re.compile(r"^(03|05|07|08|09)\d{8}$")


def normalize_and_validate_vn_phone(val: str) -> str:
    """Chuẩn hóa và kiểm tra số điện thoại chuẩn di động Việt Nam."""
    if not val:
        raise ValueError("Số điện thoại không được để trống.")
    cleaned = re.sub(r"[\s\.\-\(\)]", "", str(val).strip())
    if cleaned.startswith("+84"):
        cleaned = "0" + cleaned[3:]
    elif cleaned.startswith("84") and len(cleaned) == 11:
        cleaned = "0" + cleaned[2:]
    if not VN_PHONE_REGEX.match(cleaned):
        raise ValueError(
            "Số điện thoại không hợp lệ. Vui lòng nhập đúng chuẩn di động Việt Nam (10 chữ số, bắt đầu bằng 03, 05, 07, 08 hoặc 09)."
        )
    return cleaned


# ==========================================
# WebForm Schemas (SCRUM-24)
# ==========================================

class WebFormCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200, description="Tên biểu mẫu nhúng")
    lead_source: str = Field("Website Form", max_length=100, description="Nguồn gắn cho Lead khi thu thập")
    is_active: bool = Field(True, description="Trạng thái kích hoạt")


class WebFormUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    lead_source: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None


class WebFormResponse(BaseModel):
    id: str
    name: str
    form_key: str
    lead_source: str
    is_active: bool
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    embed_code: Optional[str] = None
    iframe_code: Optional[str] = None
    total_leads: int = 0

    model_config = ConfigDict(from_attributes=True)


class WebFormEmbedCodeResponse(BaseModel):
    form_id: str
    form_name: str
    form_key: str
    lead_source: str
    is_active: bool
    embed_code: str
    iframe_code: str
    direct_submit_url: str


# ==========================================
# Public Lead Submit Schemas (SCRUM-24)
# ==========================================

class PublicLeadSubmitRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=150, description="Họ và tên khách hàng")
    email: EmailStr = Field(..., description="Địa chỉ Email hợp lệ")
    phone: str = Field(..., description="Số điện thoại di động Việt Nam")
    company: Optional[str] = Field(None, max_length=255, description="Tên công ty / Doanh nghiệp")
    interest_need: Optional[str] = Field(None, description="Nhu cầu hoặc lời nhắn của khách hàng")
    
    # Honeypot spam protection fields
    # Bot tự động điền trường này sẽ bị hệ thống âm thầm chặn
    hp: Optional[str] = Field(None, alias="_hp", description="Honeypot field ẩn chống bot spam")
    website_hp: Optional[str] = Field(None, description="Honeypot field ẩn phụ")

    model_config = ConfigDict(populate_by_name=True)

    @property
    def is_bot_spam(self) -> bool:
        """Kiểm tra bot dựa trên honeypot field."""
        return bool(self.hp or self.website_hp)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return normalize_and_validate_vn_phone(v)

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        cleaned = v.strip()
        if len(cleaned) < 2:
            raise ValueError("Họ và tên phải có tối thiểu 2 ký tự.")
        return cleaned


class PublicLeadSubmitResponse(BaseModel):
    success: bool
    message: str
    lead_id: Optional[str] = None


# ==========================================
# Lead Management Schemas (EP-04)
# ==========================================

class LeadResponse(BaseModel):
    id: str
    full_name: str
    email: str
    phone: str
    company: Optional[str] = None
    interest_need: Optional[str] = None
    source: str
    status: str
    form_id: Optional[str] = None
    form_name: Optional[str] = None
    client_ip: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class LeadStatusUpdate(BaseModel):
    status: str = Field(..., description="Trạng thái mới: NEW, CONTACTED, QUALIFIED, CONVERTED, REJECTED")


class LeadListResponse(BaseModel):
    items: List[LeadResponse]
    total: int
    page: int
    limit: int
    total_pages: int
