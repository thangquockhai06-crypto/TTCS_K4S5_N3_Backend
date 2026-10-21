from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class DuplicateCheckRequest(BaseModel):
    """Payload yêu cầu kiểm tra và tìm kiếm khách hàng trùng lặp."""
    customer_id: Optional[str] = Field(None, description="ID khách hàng có sẵn cần quét trùng")
    name: Optional[str] = Field(None, description="Tên công ty hoặc họ tên người đại diện cần kiểm tra")
    tax_code: Optional[str] = Field(None, description="Mã số thuế doanh nghiệp")
    website: Optional[str] = Field(None, description="Địa chỉ website / domain công ty")
    phone: Optional[str] = Field(None, description="Số điện thoại liên hệ")

    model_config = ConfigDict(populate_by_name=True)


class DuplicateMatchItem(BaseModel):
    """Thông tin một khách hàng bị phát hiện trùng khớp."""
    id: str
    name: str = Field(..., description="Tên hiển thị chính (Công ty hoặc họ tên)")
    full_name: str
    company: Optional[str] = None
    tax_code: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    assigned_to_id: Optional[str] = None
    assigned_to_name: Optional[str] = None
    status: Optional[str] = None
    match_reasons: List[str] = Field(default_factory=list, description="Danh sách các lý do phát hiện trùng")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Độ tương đồng cao nhất (0.0 - 1.0)")
    created_at: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


class CustomerCompareDetailsDTO(BaseModel):
    """Chi tiết đầy đủ của một khách hàng trong màn hình so sánh cạnh nhau."""
    id: str
    fullName: str
    company: Optional[str] = None
    email: str
    phone: str
    website: Optional[str] = None
    taxCode: Optional[str] = None
    status: str
    healthScore: int = 85
    industry: Optional[str] = None
    companySize: Optional[str] = None
    region: Optional[str] = None
    assignedUserId: Optional[str] = None
    assignedUserName: Optional[str] = None
    contactsCount: int = 0
    dealsCount: int = 0
    activitiesCount: int = 0
    contacts: List[Dict[str, Any]] = Field(default_factory=list)
    deals: List[Dict[str, Any]] = Field(default_factory=list)
    activities: List[Dict[str, Any]] = Field(default_factory=list)
    createdAt: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


class CustomerCompareResponse(BaseModel):
    """Response cho API so sánh cạnh nhau 2 khách hàng trước khi gộp."""
    primary_customer: CustomerCompareDetailsDTO
    duplicate_customer: CustomerCompareDetailsDTO
    field_differences: List[str] = Field(
        default_factory=list,
        description="Danh sách các trường có dữ liệu khác biệt giữa hai bên",
    )

    model_config = ConfigDict(populate_by_name=True)


class CustomerMergeOverrideDTO(BaseModel):
    """Dữ liệu tùy chọn ghi đè lên bản ghi chính khi gộp."""
    full_name: Optional[str] = None
    company: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    tax_code: Optional[str] = None
    industry: Optional[str] = None
    region: Optional[str] = None
    status: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


class CustomerMergeRequest(BaseModel):
    """Payload thực hiện gộp khách hàng."""
    target_customer_id: str = Field(..., description="ID khách hàng chính (giữ lại)")
    source_customer_id: str = Field(..., description="ID khách hàng phụ (sẽ bị gộp và vô hiệu hóa)")
    merged_data: Optional[CustomerMergeOverrideDTO] = Field(
        None,
        description="Tùy chọn ghi đè một số trường thông tin lên bản ghi chính",
    )

    model_config = ConfigDict(populate_by_name=True)


class CustomerMergeResponse(BaseModel):
    """Response kết quả gộp khách hàng."""
    success: bool = True
    message: str
    target_customer_id: str
    source_customer_id: str
    transferred_contacts_count: int
    transferred_deals_count: int
    transferred_activities_count: int
    merged_at: str

    model_config = ConfigDict(populate_by_name=True)
