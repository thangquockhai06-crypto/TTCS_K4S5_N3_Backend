from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class CategoryDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    type: str  # 'lead_source' | 'industry'
    code: str
    name: str
    order_index: int
    is_system: bool
    usage_count: int



class CreateCategoryDTO(BaseModel):
    type: str
    code: str
    name: str
    order_index: Optional[int] = 0


class UpdateCategoryDTO(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    order_index: Optional[int] = None


class ReorderCategoryItem(BaseModel):
    id: str
    order_index: int


class ReorderCategoriesDTO(BaseModel):
    items: Optional[List[ReorderCategoryItem]] = None
    ordered_ids: Optional[List[str]] = None
