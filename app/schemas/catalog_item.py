from decimal import Decimal
from typing import Optional, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


CatalogItemType = Literal["ONE_TIME_PRODUCT", "RECURRING_SERVICE"]
CatalogItemStatus = Literal["ACTIVE", "DISCONTINUED"]


class CatalogItemCreateDTO(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    type: CatalogItemType
    unit_of_measure: str = Field(..., min_length=1, max_length=50, alias="unitOfMeasure")
    list_price: Decimal = Field(..., ge=0, alias="listPrice")
    floor_price: Decimal = Field(..., ge=0, alias="floorPrice")
    cost_price: Decimal = Field(..., ge=0, alias="costPrice")
    currency: str = Field("VND", min_length=3, max_length=3)

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="after")
    def validate_price_order(self):
        if self.floor_price > self.list_price:
            raise ValueError("floorPrice must be less than or equal to listPrice")
        return self


class CatalogItemUpdateDTO(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    type: Optional[CatalogItemType] = None
    unit_of_measure: Optional[str] = Field(None, min_length=1, max_length=50, alias="unitOfMeasure")
    list_price: Optional[Decimal] = Field(None, ge=0, alias="listPrice")
    floor_price: Optional[Decimal] = Field(None, ge=0, alias="floorPrice")
    cost_price: Optional[Decimal] = Field(None, ge=0, alias="costPrice")
    currency: Optional[str] = Field(None, min_length=3, max_length=3)

    model_config = ConfigDict(populate_by_name=True)


class CatalogItemDTO(BaseModel):
    id: str
    code: str
    name: str
    type: CatalogItemType
    unit_of_measure: str = Field(..., serialization_alias="unitOfMeasure")
    list_price: Decimal = Field(..., serialization_alias="listPrice")
    floor_price: Decimal = Field(..., serialization_alias="floorPrice")
    cost_price: Optional[Decimal] = Field(None, serialization_alias="costPrice")
    currency: str
    status: CatalogItemStatus
    discontinued_at: Optional[str] = Field(None, serialization_alias="discontinuedAt")
    created_at: Optional[str] = Field(None, serialization_alias="createdAt")
    updated_at: Optional[str] = Field(None, serialization_alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class QuotationLineCreateDTO(BaseModel):
    product_id: str = Field(..., alias="productId")
    quantity: Decimal = Field(..., gt=0)
    unit_price: Optional[Decimal] = Field(None, ge=0, alias="unitPrice")

    model_config = ConfigDict(populate_by_name=True)


class QuotationLineDTO(BaseModel):
    id: str
    product_id: str = Field(..., serialization_alias="productId")
    product_code: str = Field(..., serialization_alias="productCode")
    product_name: str = Field(..., serialization_alias="productName")
    quantity: Decimal
    unit_price: Decimal = Field(..., serialization_alias="unitPrice")
    list_price_snapshot: Decimal = Field(..., serialization_alias="listPriceSnapshot")
    floor_price_snapshot: Decimal = Field(..., serialization_alias="floorPriceSnapshot")
    currency: str
    requires_discount_approval: bool = Field(False, serialization_alias="requiresDiscountApproval")
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)
