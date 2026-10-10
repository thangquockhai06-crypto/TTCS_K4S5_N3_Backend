from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class CustomFieldDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    entity_type: str
    field_name: str
    field_label: str
    field_type: str  # 'text' | 'number' | 'date' | 'select'
    options: Optional[str] = None
    is_required: bool
    default_value: Optional[str] = None



class CreateCustomFieldDTO(BaseModel):
    entity_type: str = "customer"
    field_name: str
    field_label: str
    field_type: str = "text"
    options: Optional[str] = None
    is_required: bool = False
    default_value: Optional[str] = None


class UpdateCustomFieldDTO(BaseModel):
    field_label: Optional[str] = None
    field_type: Optional[str] = None
    options: Optional[str] = None
    is_required: Optional[bool] = None
    default_value: Optional[str] = None


class SaveCustomFieldValuesDTO(BaseModel):
    entity_type: str
    entity_id: Optional[str] = "sample"
    values: dict[str, Optional[str]]
