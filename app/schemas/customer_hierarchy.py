from typing import Optional, List, Union
from pydantic import BaseModel, ConfigDict, Field


class AssignParentRequest(BaseModel):
    parent_id: Optional[Union[str, int]] = Field(
        None, description="ID của công ty mẹ, truyền null để gỡ liên kết"
    )

    model_config = ConfigDict(from_attributes=True)


class AssignParentResponse(BaseModel):
    message: str = Field(..., description="Thông báo kết quả thực hiện")
    customer_id: Union[str, int] = Field(..., description="ID của khách hàng")
    parent_id: Optional[Union[str, int]] = Field(None, description="ID của công ty mẹ sau khi cập nhật")

    model_config = ConfigDict(from_attributes=True)


class SubsidiaryItemResponse(BaseModel):
    id: Union[str, int] = Field(..., description="Mã định danh công ty con")
    name: str = Field(..., description="Tên pháp nhân công ty con")
    tax_code: Optional[str] = Field(None, description="Mã số thuế của công ty con")
    status: str = Field(..., description="Trạng thái khách hàng")
    assigned_to_name: Optional[str] = Field(None, description="Họ tên người phụ trách")
    deals_count: int = Field(0, description="Số lượng cơ hội/hợp đồng giao dịch")
    total_deal_value: float = Field(0.0, description="Tổng giá trị giao dịch của công ty con")

    model_config = ConfigDict(from_attributes=True)


class GroupSummaryResponse(BaseModel):
    parent_company_id: Union[str, int] = Field(..., description="Mã định danh công ty mẹ")
    parent_company_name: str = Field(..., description="Tên công ty mẹ / Holding")
    total_subsidiaries: int = Field(0, description="Tổng số lượng công ty con trực thuộc")
    own_deal_value: float = Field(0.0, description="Giá trị giao dịch riêng của công ty mẹ")
    subsidiaries_deal_value: float = Field(0.0, description="Tổng giá trị giao dịch của các công ty con")
    total_group_value: float = Field(0.0, description="Tổng giá trị toàn bộ tập đoàn (own + subsidiaries)")
    subsidiaries: List[SubsidiaryItemResponse] = Field(
        default_factory=list, description="Danh sách chi tiết các công ty con"
    )

    model_config = ConfigDict(from_attributes=True)
