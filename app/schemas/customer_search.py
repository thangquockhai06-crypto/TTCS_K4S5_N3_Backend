from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CustomerFilterDefinition(BaseModel):
    q: Optional[str] = None
    status: List[str] = Field(default_factory=list)
    industry: List[str] = Field(default_factory=list)
    company_size: List[str] = Field(default_factory=list, alias="companySize")
    region: List[str] = Field(default_factory=list)
    owner: List[str] = Field(default_factory=list)
    sort: str = "created_at"
    descending: bool = True
    skip: int = Field(0, ge=0)
    limit: int = Field(50, ge=1, le=200)

    model_config = ConfigDict(populate_by_name=True)


class SavedFilterCreateDTO(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    filter_definition: CustomerFilterDefinition = Field(..., alias="filterDefinition")
    is_default: bool = Field(False, alias="isDefault")

    model_config = ConfigDict(populate_by_name=True)


class SavedFilterUpdateDTO(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    filter_definition: Optional[CustomerFilterDefinition] = Field(None, alias="filterDefinition")
    is_default: Optional[bool] = Field(None, alias="isDefault")

    model_config = ConfigDict(populate_by_name=True)


class SavedFilterDTO(BaseModel):
    id: str
    name: str
    filter_definition: CustomerFilterDefinition = Field(..., serialization_alias="filterDefinition")
    is_default: bool = Field(False, serialization_alias="isDefault")
    created_at: Optional[str] = Field(None, serialization_alias="createdAt")
    updated_at: Optional[str] = Field(None, serialization_alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)
