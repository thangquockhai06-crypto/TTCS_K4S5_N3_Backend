from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

class CreateSavedFilterDTO(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    entityType: Optional[str] = Field("customer", serialization_alias="entityType")
    filterCriteria: str = Field(..., description="Chuỗi JSON tiêu chí lọc")
    isDefault: Optional[bool] = Field(False, serialization_alias="isDefault")

class SavedFilterPresetDTO(BaseModel):
    id: str
    userId: str = Field(..., serialization_alias="userId")
    name: str
    entityType: str = Field(..., serialization_alias="entityType")
    filterCriteria: str = Field(..., serialization_alias="filterCriteria")
    isDefault: bool = Field(False, serialization_alias="isDefault")
    createdAt: Optional[str] = Field(None, serialization_alias="createdAt")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)
