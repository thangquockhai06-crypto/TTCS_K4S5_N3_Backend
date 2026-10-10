from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, model_validator, ConfigDict


CAMPAIGN_STATUSES = {"PLANNING", "ACTIVE", "COMPLETED", "PAUSED"}


class CampaignCreateRequest(BaseModel):
    """
    Schema tạo mới Chiến dịch tiếp thị (SCRUM-44).
    Ràng buộc: end_date >= start_date, budget >= 0.
    """
    name: str = Field(..., min_length=2, max_length=200, description="Tên chiến dịch")
    channel: str = Field(..., min_length=1, max_length=100, description="Kênh tiếp thị (Facebook, Google Ads, Hội thảo, Email, Tiktok...)")
    budget: Decimal = Field(default=Decimal("0.00"), ge=0, description="Ngân sách dự kiến (>= 0)")
    start_date: date = Field(..., description="Ngày bắt đầu chiến dịch")
    end_date: date = Field(..., description="Ngày kết thúc chiến dịch")
    description: Optional[str] = Field(None, description="Mô tả chiến dịch")
    status: Optional[str] = Field("ACTIVE", description="Trạng thái chiến dịch: PLANNING, ACTIVE, COMPLETED, PAUSED")

    @model_validator(mode="after")
    def validate_dates_and_status(self):
        if self.end_date < self.start_date:
            raise ValueError("Ngày kết thúc (end_date) phải lớn hơn hoặc bằng ngày bắt đầu (start_date).")
        if self.status:
            upper_status = self.status.strip().upper()
            if upper_status not in CAMPAIGN_STATUSES:
                raise ValueError(f"Trạng thái không hợp lệ. Chọn một trong: {', '.join(CAMPAIGN_STATUSES)}")
            self.status = upper_status
        return self


class CampaignUpdateRequest(BaseModel):
    """Schema cập nhật Chiến dịch tiếp thị."""
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    channel: Optional[str] = Field(None, min_length=1, max_length=100)
    budget: Optional[Decimal] = Field(None, ge=0)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    description: Optional[str] = None
    status: Optional[str] = None

    @model_validator(mode="after")
    def validate_dates(self):
        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                raise ValueError("Ngày kết thúc (end_date) phải lớn hơn hoặc bằng ngày bắt đầu (start_date).")
        if self.status:
            upper_status = self.status.strip().upper()
            if upper_status not in CAMPAIGN_STATUSES:
                raise ValueError(f"Trạng thái không hợp lệ. Chọn một trong: {', '.join(CAMPAIGN_STATUSES)}")
            self.status = upper_status
        return self


class CampaignBaseResponse(BaseModel):
    """Thông tin cơ bản của chiến dịch."""
    id: str
    name: str
    channel: str
    budget: Decimal
    start_date: date
    end_date: date
    status: str
    description: Optional[str] = None
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CampaignMetricsResponse(CampaignBaseResponse):
    """
    Thông tin chiến dịch kèm chỉ số thống kê hiệu quả thời gian thực:
    - total_leads: Tổng số lead thuộc chiến dịch
    - total_deals: Tổng số cơ hội phát sinh từ chiến dịch
    - won_deals_count: Số cơ hội đã chốt thành công
    - total_revenue: Tổng doanh thu thực tế đã chốt
    - roi: Tỷ suất sinh lời (%)
    - profit: Chênh lệch doanh thu - ngân sách
    """
    total_leads: int = 0
    total_deals: int = 0
    won_deals_count: int = 0
    total_revenue: Decimal = Decimal("0.00")
    roi: Optional[float] = None
    profit: Decimal = Decimal("0.00")


class LeadSummaryDTO(BaseModel):
    """Tóm tắt Lead liên kết với chiến dịch."""
    id: str
    full_name: str
    phone: str
    email: Optional[str] = None
    company: Optional[str] = None
    source: str
    status: str
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DealSummaryDTO(BaseModel):
    """Tóm tắt Cơ hội bán hàng (Deal) liên kết với chiến dịch."""
    id: str
    title: str
    value: Decimal
    stage: str
    probability: int
    customer_id: str
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CampaignDetailResponse(CampaignMetricsResponse):
    """Chi tiết một chiến dịch kèm danh sách leads và deals liên kết."""
    leads: List[LeadSummaryDTO] = Field(default_factory=list)
    deals: List[DealSummaryDTO] = Field(default_factory=list)


class CampaignListResponse(BaseModel):
    """Danh sách chiến dịch có phân trang."""
    total: int
    page: int
    limit: int
    items: List[CampaignMetricsResponse]
