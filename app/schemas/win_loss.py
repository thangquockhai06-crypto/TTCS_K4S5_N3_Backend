from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


# --- 1. Schemas cho Lý do Thắng / Thua (Win/Loss Reasons) ---
class WinLossReasonDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    result_type: str  # 'WON' | 'LOST'
    code: str
    reason: str
    description: Optional[str] = None
    is_active: bool = True
    usage_count: int = 0


class CreateWinLossReasonDTO(BaseModel):
    result_type: str = Field(..., description="Loại kết quả: WON hoặc LOST")
    code: str = Field(..., min_length=1, max_length=50, description="Mã định danh lý do")
    reason: str = Field(..., min_length=1, max_length=255, description="Chi tiết lý do")
    description: Optional[str] = None
    is_active: Optional[bool] = True

    @field_validator("result_type")
    @classmethod
    def validate_result_type(cls, v: str) -> str:
        clean = v.strip().upper()
        if clean not in ["WON", "LOST"]:
            raise ValueError("Loại kết quả phải là 'WON' (Thành công) hoặc 'LOST' (Thất bại)")
        return clean

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        clean = v.strip().upper()
        if not clean:
            raise ValueError("Mã lý do không được để trống")
        return clean

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Nguyên nhân chi tiết không được để trống")
        return clean


class UpdateWinLossReasonDTO(BaseModel):
    result_type: Optional[str] = None
    code: Optional[str] = None
    reason: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("result_type")
    @classmethod
    def validate_result_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            clean = v.strip().upper()
            if clean not in ["WON", "LOST"]:
                raise ValueError("Loại kết quả phải là 'WON' hoặc 'LOST'")
            return clean
        return v

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            clean = v.strip().upper()
            if not clean:
                raise ValueError("Mã lý do không được để trống")
            return clean
        return v

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            clean = v.strip()
            if not clean:
                raise ValueError("Nguyên nhân chi tiết không được để trống")
            return clean
        return v


# --- 2. Schemas cho Đối thủ Cạnh tranh (Competitors) ---
class CompetitorDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    website: Optional[str] = None
    pricing_tier: Optional[str] = "Trung cấp"
    strengths: Optional[str] = None
    weaknesses: Optional[str] = None
    win_rate: float = 50.0
    is_active: bool = True


class CreateCompetitorDTO(BaseModel):
    name: str = Field(..., min_length=1, max_length=150, description="Tên đối thủ cạnh tranh")
    website: Optional[str] = None
    pricing_tier: Optional[str] = Field("Trung cấp", description="Phân khúc giá")
    strengths: Optional[str] = None
    weaknesses: Optional[str] = None
    win_rate: Optional[float] = Field(50.0, ge=0, le=100, description="Tỷ lệ thắng (0 - 100%)")
    is_active: Optional[bool] = True

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Tên đối thủ cạnh tranh không được để trống")
        return clean


class UpdateCompetitorDTO(BaseModel):
    name: Optional[str] = None
    website: Optional[str] = None
    pricing_tier: Optional[str] = None
    strengths: Optional[str] = None
    weaknesses: Optional[str] = None
    win_rate: Optional[float] = Field(None, ge=0, le=100, description="Tỷ lệ thắng (0 - 100%)")
    is_active: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            clean = v.strip()
            if not clean:
                raise ValueError("Tên đối thủ cạnh tranh không được để trống")
            return clean
        return v
