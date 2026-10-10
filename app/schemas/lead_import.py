import re
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr, field_validator, ConfigDict


# Regex kiểm tra định dạng số điện thoại Việt Nam chuẩn (10 chữ số)
VN_PHONE_REGEX = re.compile(r"^(?:0|\+84)(3|5|7|8|9)\d{8}$")


def clean_phone_number(v: str) -> str:
    """Loại bỏ ký tự phân cách khoảng trắng, dấu gạch nối, dấu chấm."""
    if not v:
        return ""
    cleaned = re.sub(r"[\s\.\-\(\)]", "", str(v).strip())
    return cleaned


class LeadCreateManualRequest(BaseModel):
    """
    Schema tạo thủ công 1 Lead từ sự kiện hoặc danh thiếp (SCRUM-40).
    Mọi lead nhập vào BẮT BUỘC phải có trường source (Nguồn lead).
    """
    full_name: str = Field(..., min_length=2, max_length=150, description="Họ và tên lead")
    phone: str = Field(..., description="Số điện thoại liên hệ (10 chữ số VN)")
    email: Optional[EmailStr] = Field(None, description="Email liên hệ")
    company: Optional[str] = Field(None, max_length=255, description="Công ty / Doanh nghiệp")
    interest_need: Optional[str] = Field(None, description="Nhu cầu quan tâm")
    source: str = Field(..., min_length=1, max_length=100, description="Nguồn lead bắt buộc (Hội thảo, Sự kiện, Danh thiếp, Giới thiệu...)")
    notes: Optional[str] = Field(None, description="Ghi chú thêm")
    campaign_id: Optional[str] = Field(None, description="ID chiến dịch liên kết (SCRUM-44)")


    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        s = v.strip()
        if len(s) < 2:
            raise ValueError("Họ và tên là bắt buộc (tối thiểu 2 ký tự).")
        return s

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Nguồn lead (source) là bắt buộc và không được để trống.")
        return v.strip()

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        cleaned = clean_phone_number(v)
        if not cleaned:
            raise ValueError("Số điện thoại là bắt buộc.")
        if not VN_PHONE_REGEX.match(cleaned):
            raise ValueError("Số điện thoại không đúng định dạng Việt Nam (10 chữ số, ví dụ: 0912345678 hoặc +84912345678).")
        return cleaned


class LeadResponse(BaseModel):
    """Thông tin Lead trả về cho client."""
    id: str
    full_name: str
    phone: str
    email: Optional[str] = None
    company: Optional[str] = None
    interest_need: Optional[str] = None
    source: str
    status: str
    notes: Optional[str] = None
    created_by: Optional[str] = None
    campaign_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class LeadImportRowValidation(BaseModel):
    """Kết quả kiểm tra tính hợp lệ của từng dòng trong tệp import."""
    row_number: int
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    interest_need: Optional[str] = None
    source: Optional[str] = None
    notes: Optional[str] = None
    campaign_id: Optional[str] = None
    is_valid: bool = True
    errors: List[str] = Field(default_factory=list)


class LeadImportPreviewResponse(BaseModel):
    """Kết quả xem trước (dry-run preview) tệp import."""
    total_rows: int
    valid_count: int
    invalid_count: int
    preview_rows: List[LeadImportRowValidation]


class LeadImportExecuteRequest(BaseModel):
    """Dữ liệu yêu cầu thực thi import vào CSDL."""
    rows: Optional[List[LeadImportRowValidation]] = Field(None, description="Danh sách các dòng đã validate để import")
    campaign_id: Optional[str] = Field(None, description="Gán chiến dịch mặc định cho toàn bộ danh sách nạp (nếu có)")
    skip_errors: bool = Field(True, description="Tự động bỏ qua các dòng lỗi")


class LeadImportExecuteResponse(BaseModel):
    """Kết quả tổng kết thực thi import hàng loạt."""
    total_rows: int
    imported_count: int
    failed_count: int
    details: List[Dict[str, Any]] = Field(default_factory=list)
