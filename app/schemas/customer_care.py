from datetime import datetime
from typing import Optional, List, Literal, Union
from pydantic import BaseModel, Field, ConfigDict


class CustomerCareFilterParams(BaseModel):
    days_inactive: int = Field(30, ge=1, description="Số ngày không tương tác N")
    search: Optional[str] = Field(None, description="Tìm theo tên khách hàng, mã số thuế hoặc SĐT")
    page: int = Field(1, ge=1, description="Số trang hiện tại")
    page_size: int = Field(20, ge=1, le=100, description="Số lượng bản ghi trên một trang")

    model_config = ConfigDict(populate_by_name=True)


class CustomerCareItemResponse(BaseModel):
    customer_id: Union[str, int]
    customer_name: str
    contact_person_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    assigned_to_name: Optional[str] = None
    total_contract_value: float = Field(0.0, description="Tổng giá trị hợp đồng đã ký")
    last_activity_date: Optional[datetime] = Field(None, description="Thời điểm tương tác gần nhất")
    days_without_contact: int = Field(0, description="Số ngày kể từ lần tương tác cuối")
    status: str

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class CustomerCareListResponse(BaseModel):
    total_items: int = Field(..., description="Tổng số khách hàng thỏa mãn điều kiện")
    page: int = Field(..., description="Trang hiện tại")
    page_size: int = Field(..., description="Kích thước trang")
    days_inactive_threshold: int = Field(..., description="Ngưỡng số ngày chưa tương tác N")
    items: List[CustomerCareItemResponse] = Field(default_factory=list, description="Danh sách khách hàng")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class QuickContactRequest(BaseModel):
    activity_type: Literal["CALL", "MEETING", "NOTE", "EMAIL"] = Field(
        "CALL", description="Loại hoạt động tương tác nhanh"
    )
    notes: str = Field("Đã liên hệ chăm sóc định kỳ", max_length=500, description="Ghi chú nội dung tương tác")

    model_config = ConfigDict(populate_by_name=True)


class QuickContactResponse(BaseModel):
    message: str = Field("Đã ghi nhận tương tác thành công", description="Thông báo kết quả")
    last_contacted_at: datetime = Field(..., description="Thời điểm vừa ghi nhận liên hệ")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
