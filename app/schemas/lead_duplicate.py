"""
Pydantic Schemas cho Phân hệ Phát hiện & Gộp Lead trùng lặp (SCRUM-175 / SCRUM-46 / Sprint 4).
Hỗ trợ:
- Kiểm tra trùng lặp đa tiêu chí (Email, Số điện thoại, Tên công ty) đối chiếu Lead và Customer.
- Gộp hai Lead trùng lặp (Merge Leads) bảo toàn trọn vẹn lịch sử.
- Gắn Lead trùng vào Khách hàng đã có (Attach Lead to Customer).
"""
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from app.schemas.lead_import import LeadResponse


class LeadDuplicateCheckRequest(BaseModel):
    """Yêu cầu kiểm tra trùng lặp thời gian thực hoặc trước khi lưu."""
    email: Optional[EmailStr] = Field(None, description="Email cần kiểm tra trùng lặp")
    phone: Optional[str] = Field(None, description="Số điện thoại cần kiểm tra trùng lặp")
    company: Optional[str] = Field(None, description="Tên công ty / Doanh nghiệp")
    exclude_lead_id: Optional[str] = Field(None, description="Bỏ qua chính Lead đang chỉnh sửa")


class DuplicateMatchItem(BaseModel):
    """Thông tin một bản ghi khớp trùng lặp (Lead hoặc Khách hàng)."""
    target_type: Literal["LEAD", "CUSTOMER"] = Field(..., description="Loại bản ghi khớp: LEAD hoặc CUSTOMER")
    target_id: str = Field(..., description="ID của bản ghi trùng lặp")
    name: str = Field(..., description="Họ và tên Lead hoặc Người đại diện / Tên Khách hàng")
    email: Optional[str] = Field(None, description="Địa chỉ email")
    phone: Optional[str] = Field(None, description="Số điện thoại")
    company: Optional[str] = Field(None, description="Tên công ty / Doanh nghiệp")
    owner_name: Optional[str] = Field(None, description="Người tạo Lead hoặc Người phụ trách Khách hàng")
    match_fields: List[str] = Field(default_factory=list, description="Danh sách các trường bị trùng: ['phone', 'email', 'company']")
    created_at: Optional[datetime] = Field(None, description="Thời điểm tạo bản ghi")

    model_config = ConfigDict(from_attributes=True)


class LeadDuplicateCheckResponse(BaseModel):
    """Kết quả phát hiện trùng lặp trả về cho người dùng."""
    is_duplicate: bool = Field(..., description="Có phát hiện trùng lặp hay không")
    matches_count: int = Field(0, description="Tổng số bản ghi phát hiện trùng lặp")
    lead_matches: List[DuplicateMatchItem] = Field(default_factory=list, description="Danh sách Lead trùng lặp")
    customer_matches: List[DuplicateMatchItem] = Field(default_factory=list, description="Danh sách Khách hàng hiện có trùng lặp")
    recommendation: Literal["NO_DUPLICATE", "MERGE_LEADS", "ATTACH_TO_CUSTOMER"] = Field(
        ...,
        description="Gợi ý hành động: NO_DUPLICATE, MERGE_LEADS, hoặc ATTACH_TO_CUSTOMER"
    )
    suggested_action: Optional[str] = Field(
        None,
        description="Mã gợi ý hành động bổ trợ: MERGE_DUPLICATE_LEADS hoặc MERGE_TO_EXISTING_CUSTOMER"
    )


class LeadMergeRequest(BaseModel):
    """Yêu cầu gộp 2 Lead trùng lặp."""
    primary_lead_id: str = Field(..., description="ID của Lead giữ lại làm bản ghi chính")
    duplicate_lead_id: str = Field(..., description="ID của Lead bị gộp vào (sẽ chuyển trạng thái MERGED)")
    selected_fields: Optional[Dict[str, Any]] = Field(
        None,
        description="Tùy chọn ghi đè trường thông tin (full_name, phone, email, company, source, interest_need, notes)"
    )


class LeadAttachToCustomerRequest(BaseModel):
    """Yêu cầu gắn Lead trùng vào một Khách hàng đã có trong CRM."""
    lead_id: str = Field(..., description="ID của Lead cần gắn vào Khách hàng")
    customer_id: str = Field(..., description="ID của Khách hàng hiện hữu cần liên kết")
    notes: Optional[str] = Field(None, description="Ghi chú bổ sung khi thực hiện gắn")


class LeadAttachToCustomerResponse(BaseModel):
    """Kết quả sau khi gắn Lead vào Khách hàng."""
    message: str = Field("Đã gắn Lead vào Khách hàng thành công.")
    lead_id: str
    customer_id: str
    status: str
    lead: Optional[LeadResponse] = None
