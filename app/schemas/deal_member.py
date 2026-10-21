from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class DealMemberCreate(BaseModel):
    """Schema yêu cầu thêm thành viên phối hợp cơ hội bán hàng (SCRUM-207)."""
    user_id: str = Field(..., description="ID nhân viên phối hợp")
    role_in_deal: Optional[str] = Field("COLLABORATOR", max_length=50, description="Vai trò: COLLABORATOR, SUPPORT, PRE_SALES, CO_SALES")

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("user_id không được để trống.")
        return clean

    @field_validator("role_in_deal")
    @classmethod
    def normalize_role(cls, value: Optional[str]) -> str:
        if value and value.strip():
            return value.strip().upper()
        return "COLLABORATOR"


class DealMemberResponse(BaseModel):
    """Schema phản hồi thông tin thành viên phối hợp (SCRUM-207)."""
    id: str
    deal_id: str
    user_id: str
    user_name: str
    user_email: str
    role_in_deal: str
    added_by_name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class DealTransferOwnerRequest(BaseModel):
    """Schema yêu cầu chuyển quyền sở hữu cơ hội (SCRUM-207)."""
    new_owner_id: str = Field(..., description="ID của người nhận bàn giao chính")
    keep_old_owner_as_member: bool = Field(True, description="Giữ người sở hữu cũ làm thành viên tham gia")
    reason: Optional[str] = Field(None, max_length=255, description="Lý do bàn giao thương vụ")

    @field_validator("new_owner_id")
    @classmethod
    def validate_new_owner_id(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("new_owner_id không được để trống.")
        return clean


class DealActivityCreateDTO(BaseModel):
    """Schema tạo hoạt động gắn với cơ hội bán hàng (SCRUM-207)."""
    type: str = Field("call", description="Loại hoạt động: call, meeting, email, note...")
    title: str = Field(..., description="Tiêu đề hoạt động")
    description: Optional[str] = Field("", description="Mô tả chi tiết")
    customerId: Optional[str] = Field(None, description="Mã khách hàng (mặc định lấy theo Deal)")

    @field_validator("type")
    @classmethod
    def normalize_activity_type(cls, value: str) -> str:
        clean = (value or "call").strip().lower()
        valid_types = {"call", "meeting", "email", "deal_change", "status_change"}
        if clean not in valid_types:
            return "call"
        return clean


class DealHistoryResponse(BaseModel):
    """Schema phản hồi lịch sử thay đổi của Deal (Deal History / Audit Log)."""
    id: str
    deal_id: str
    field_name: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    changed_by: Optional[str] = None
    changed_by_name: Optional[str] = None
    changed_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
