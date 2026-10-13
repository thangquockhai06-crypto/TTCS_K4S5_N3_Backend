"""
Pydantic v2 Schemas cho Cấu hình chấm điểm Lead (SCRUM-48 / Sprint 4).
Hỗ trợ:
- Định nghĩa quy tắc chấm điểm (ScoringRuleCreate, ScoringRuleUpdate, ScoringRuleResponse).
- Cấu hình ngưỡng nhiệt độ (ScoringSettingsUpdate, ScoringSettingsResponse).
- Thống kê tính toán lại điểm hàng loạt (BatchRecalculateResponse).
"""
from typing import Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, model_validator


CriteriaTypeEnum = Literal["INDUSTRY", "COMPANY_SIZE", "SOURCE", "INTEREST_LEVEL"]


class ScoringRuleCreate(BaseModel):
    """Yêu cầu tạo mới một quy tắc chấm điểm Lead."""
    criteria_type: CriteriaTypeEnum = Field(
        ...,
        description="Nhóm tiêu chí: INDUSTRY, COMPANY_SIZE, SOURCE, hoặc INTEREST_LEVEL"
    )
    criteria_value: str = Field(
        ...,
        min_length=1,
        max_length=150,
        description="Giá trị so sánh (ví dụ: 'Công nghệ thông tin', '>100', 'Website', 'HIGH')"
    )
    score: int = Field(
        ...,
        description="Số điểm cộng hoặc trừ cho tiêu chí (số nguyên)"
    )
    is_active: bool = Field(
        True,
        description="Trạng thái kích hoạt áp dụng quy tắc"
    )


class ScoringRuleUpdate(BaseModel):
    """Yêu cầu cập nhật quy tắc chấm điểm Lead."""
    criteria_type: Optional[CriteriaTypeEnum] = Field(
        None,
        description="Nhóm tiêu chí mới"
    )
    criteria_value: Optional[str] = Field(
        None,
        min_length=1,
        max_length=150,
        description="Giá trị so sánh mới"
    )
    score: Optional[int] = Field(
        None,
        description="Số điểm mới"
    )
    is_active: Optional[bool] = Field(
        None,
        description="Trạng thái kích hoạt"
    )


class ScoringRuleResponse(BaseModel):
    """Thông tin quy tắc chấm điểm trả về cho client."""
    id: str
    criteria_type: str
    criteria_value: str
    score: int
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ScoringSettingsUpdate(BaseModel):
    """Yêu cầu cập nhật ngưỡng nhiệt độ Lead (Hot/Warm/Cold)."""
    hot_threshold: int = Field(
        ...,
        ge=1,
        le=1000,
        description="Ngưỡng điểm tối thiểu để phân loại Nóng (HOT)"
    )
    warm_threshold: int = Field(
        ...,
        ge=0,
        le=1000,
        description="Ngưỡng điểm tối thiểu để phân loại Ấm (WARM)"
    )

    @model_validator(mode="after")
    def validate_thresholds(self) -> "ScoringSettingsUpdate":
        if self.hot_threshold <= self.warm_threshold:
            raise ValueError("Ngưỡng điểm Nóng (hot_threshold) phải lớn hơn ngưỡng điểm Ấm (warm_threshold).")
        return self


class ScoringSettingsResponse(BaseModel):
    """Thông tin cấu hình ngưỡng nhiệt độ hiện tại."""
    id: int
    hot_threshold: int
    warm_threshold: int
    updated_by: Optional[str] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class BatchRecalculateResponse(BaseModel):
    """Kết quả thống kê sau khi tính toán lại điểm số cho toàn bộ Lead."""
    total_leads_processed: int = Field(..., description="Tổng số lead đang hoạt động được tính lại điểm")
    hot_count: int = Field(..., description="Số lead phân loại Nóng (HOT)")
    warm_count: int = Field(..., description="Số lead phân loại Ấm (WARM)")
    cold_count: int = Field(..., description="Số lead phân loại Lạnh (COLD)")
    execution_time_seconds: float = Field(..., description="Thời gian thực thi (giây)")
