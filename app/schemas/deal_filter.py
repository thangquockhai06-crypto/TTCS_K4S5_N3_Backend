from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, ConfigDict, Field, field_validator


class DealFilterParams(BaseModel):
    """Tham số tìm kiếm và lọc cơ hội đa điều kiện (SCRUM-206)."""
    model_config = ConfigDict(populate_by_name=True)

    search: Optional[str] = None
    stages: Optional[List[str]] = None
    min_amount: Optional[Decimal] = Field(None, ge=0, alias="min_amount")
    max_amount: Optional[Decimal] = Field(None, ge=0, alias="max_amount")
    expected_close_from: Optional[date] = Field(None, alias="expected_close_from")
    expected_close_to: Optional[date] = Field(None, alias="expected_close_to")
    product_id: Optional[str] = Field(None, alias="product_id")
    product_ids: Optional[List[str]] = Field(None, alias="product_ids")
    owner_id: Optional[str] = Field(None, alias="owner_id")
    assigned_to: Optional[str] = Field(None, alias="assigned_to")
    sort_by: Optional[str] = Field("expected_close_date", alias="sort_by")
    sort_order: Optional[Literal["asc", "desc"]] = Field("asc", alias="sort_order")
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100, alias="page_size")
    saved_filter_id: Optional[str] = Field(None, alias="saved_filter_id")

    @field_validator("stages", mode="before")
    @classmethod
    def normalize_stages(cls, value: Any) -> Optional[List[str]]:
        if value is None:
            return None
        if isinstance(value, str):
            parts = [s.strip().lower() for s in value.split(",") if s.strip()]
            return parts if parts else None
        if isinstance(value, (list, tuple, set)):
            result = []
            for item in value:
                if isinstance(item, str):
                    for sub in item.split(","):
                        if sub.strip():
                            result.append(sub.strip().lower())
            return list(dict.fromkeys(result)) if result else None
        return value

    @field_validator("product_ids", mode="before")
    @classmethod
    def normalize_product_ids(cls, value: Any) -> Optional[List[str]]:
        if value is None:
            return None
        if isinstance(value, str):
            parts = [s.strip() for s in value.split(",") if s.strip()]
            return parts if parts else None
        if isinstance(value, (list, tuple, set)):
            result = []
            for item in value:
                if isinstance(item, str):
                    for sub in item.split(","):
                        if sub.strip():
                            result.append(sub.strip())
            return list(dict.fromkeys(result)) if result else None
        return value

    @field_validator("search")
    @classmethod
    def trim_search(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            clean = value.strip()
            return clean if clean else None
        return None

    @field_validator("sort_order")
    @classmethod
    def normalize_sort_order(cls, value: Optional[str]) -> str:
        if not value or str(value).strip().lower() == "asc":
            return "asc"
        return "desc"


class SavedDealFilterCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150, description="Tên bộ lọc hiển thị")
    filter_criteria: Dict[str, Any] = Field(..., description="Tổ hợp tham số bộ lọc")
    is_default: bool = Field(False, description="Đặt làm bộ lọc mặc định")

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("Tên bộ lọc không được để trống.")
        return clean


class SavedDealFilterUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    filter_criteria: Optional[Dict[str, Any]] = None
    is_default: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            clean = value.strip()
            if not clean:
                raise ValueError("Tên bộ lọc không được để trống.")
            return clean
        return None


class SavedDealFilterResponse(BaseModel):
    id: str
    name: str
    filter_criteria: Dict[str, Any]
    is_default: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DealResponseSchema(BaseModel):
    id: str
    title: str
    amount: Decimal = Field(..., alias="amount")
    value: Decimal
    stage: str
    probability: int
    customer_id: str = Field(..., alias="customerId")
    customer_name: Optional[str] = None
    owner_id: str = Field(..., alias="ownerId")
    owner_name: Optional[str] = None
    expected_close_date: Optional[date] = Field(None, alias="expectedCloseDate")
    status: str = "OPEN"
    created_at: Optional[datetime] = Field(None, alias="createdAt")
    updated_at: Optional[datetime] = Field(None, alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class DealFilterPaginatedResponse(BaseModel):
    total_items: int = Field(..., description="Tổng số cơ hội thỏa mãn điều kiện lọc")
    page: int = Field(..., description="Trang hiện tại (1-indexed)")
    page_size: int = Field(..., description="Số bản ghi trên mỗi trang")
    total_pages: int = Field(..., description="Tổng số trang")
    total_amount_sum: Decimal = Field(..., description="Tổng giá trị ngân sách của các deals thỏa mãn bộ lọc")
    items: List[DealResponseSchema] = Field(..., description="Danh sách các cơ hội bán hàng")

    model_config = ConfigDict(populate_by_name=True)
