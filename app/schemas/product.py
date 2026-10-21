from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, model_validator


class ProductDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    sku: Optional[str] = None
    name: str
    category: str
    unit: str
    selling_price: float
    cost_price: Optional[float] = None  # None unless Director/Admin (S2-05)
    description: Optional[str] = None
    is_active: bool = True
    quote_count: int = 0
    created_at: Optional[datetime] = None

    @model_validator(mode="after")
    def sync_sku(self) -> "ProductDTO":
        if not self.sku:
            self.sku = self.code
        return self


class CreateProductDTO(BaseModel):
    code: Optional[str] = None
    sku: Optional[str] = None
    name: str
    category: str = "Phần mềm"
    unit: str = "Gói/Năm"
    selling_price: float = 0.0
    cost_price: Optional[float] = 0.0
    description: Optional[str] = None
    is_active: bool = True

    @model_validator(mode="after")
    def ensure_code(self) -> "CreateProductDTO":
        if not self.code and self.sku:
            self.code = self.sku
        elif not self.code and not self.sku:
            import time
            self.code = f"PRD-{int(time.time()) % 100000:05d}"
        if not self.sku and self.code:
            self.sku = self.code
        return self


class UpdateProductDTO(BaseModel):
    code: Optional[str] = None
    sku: Optional[str] = None
    name: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None
    selling_price: Optional[float] = None
    cost_price: Optional[float] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

    @model_validator(mode="after")
    def ensure_code(self) -> "UpdateProductDTO":
        if not self.code and self.sku:
            self.code = self.sku
        return self


class PriceListDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    code: str
    currency: str = "VND"
    discount_percent: float = 0.0
    multiplier: Optional[float] = 1.0
    is_default: bool = False
    is_active: bool = True
    description: Optional[str] = None
    created_at: Optional[datetime] = None

    @model_validator(mode="after")
    def compute_multiplier(self) -> "PriceListDTO":
        if self.multiplier is None or self.multiplier == 1.0:
            if self.discount_percent > 0:
                self.multiplier = round(1.0 - (self.discount_percent / 100.0), 4)
            else:
                self.multiplier = 1.0
        return self


class CreatePriceListDTO(BaseModel):
    name: str
    code: str
    currency: str = "VND"
    discount_percent: Optional[float] = 0.0
    multiplier: Optional[float] = 1.0
    is_default: bool = False
    is_active: bool = True
    description: Optional[str] = None

    @model_validator(mode="after")
    def sync_discount_and_multiplier(self) -> "CreatePriceListDTO":
        if (self.discount_percent is None or self.discount_percent == 0.0) and self.multiplier is not None and self.multiplier != 1.0:
            self.discount_percent = round((1.0 - self.multiplier) * 100.0, 2)
        elif self.discount_percent is not None and self.discount_percent > 0.0 and (self.multiplier is None or self.multiplier == 1.0):
            self.multiplier = round(1.0 - (self.discount_percent / 100.0), 4)
        return self
