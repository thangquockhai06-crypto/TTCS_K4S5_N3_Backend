from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class ProductDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    name: str
    category: str
    unit: str
    selling_price: float
    cost_price: Optional[float] = None  # None unless Director/Admin (S2-05)
    description: Optional[str] = None
    is_active: bool
    created_at: Optional[datetime] = None


class CreateProductDTO(BaseModel):
    code: str
    name: str
    category: str = "Phần mềm"
    unit: str = "Gói/Năm"
    selling_price: float
    cost_price: float
    description: Optional[str] = None
    is_active: bool = True


class UpdateProductDTO(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None
    selling_price: Optional[float] = None
    cost_price: Optional[float] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class PriceListDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    code: str
    currency: str = "VND"
    discount_percent: float = 0.0
    is_default: bool = False
    description: Optional[str] = None



class CreatePriceListDTO(BaseModel):
    name: str
    code: str
    currency: str = "VND"
    discount_percent: float = 0.0
    is_default: bool = False
    description: Optional[str] = None
