from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, AliasChoices

FIELD_LABEL_MAP = {
    "stage": "Giai đoạn",
    "amount": "Giá trị",
    "value": "Giá trị",
    "expected_close_date": "Ngày chốt dự kiến",
    "expectedCloseDate": "Ngày chốt dự kiến",
    "assigned_to": "Người sở hữu",
    "owner_id": "Người sở hữu",
    "assignedTo": "Người sở hữu",
    "ownerId": "Người sở hữu",
}


def get_field_label(field_name: str) -> str:
    """Trả về nhãn tiếng Việt thân thiện theo tên trường dữ liệu."""
    if not field_name:
        return ""
    return FIELD_LABEL_MAP.get(field_name.strip(), field_name.replace("_", " ").title())


class DealHistoryItemResponse(BaseModel):
    """
    Schema phản hồi từng bản ghi lịch sử thay đổi của cơ hội bán hàng (SCRUM-91).
    """
    id: str | int
    deal_id: str | int = Field(
        ...,
        validation_alias=AliasChoices("deal_id", "dealId"),
        serialization_alias="deal_id",
    )
    field_name: str = Field(
        ...,
        validation_alias=AliasChoices("field_name", "fieldName"),
        serialization_alias="field_name",
    )
    field_label: str = Field(
        ...,
        validation_alias=AliasChoices("field_label", "fieldLabel"),
        serialization_alias="field_label",
    )
    old_value: Optional[str] = Field(
        None,
        validation_alias=AliasChoices("old_value", "oldValue"),
        serialization_alias="old_value",
    )
    new_value: Optional[str] = Field(
        None,
        validation_alias=AliasChoices("new_value", "newValue"),
        serialization_alias="new_value",
    )
    changed_by_id: str | int = Field(
        ...,
        validation_alias=AliasChoices("changed_by_id", "changedById"),
        serialization_alias="changed_by_id",
    )
    changed_by_name: str = Field(
        ...,
        validation_alias=AliasChoices("changed_by_name", "changedByName"),
        serialization_alias="changed_by_name",
    )
    changed_at: datetime = Field(
        ...,
        validation_alias=AliasChoices("changed_at", "changedAt"),
        serialization_alias="changed_at",
    )

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class DealHistoryListResponse(BaseModel):
    """
    Schema danh sách lịch sử thay đổi của Deal có phân trang (SCRUM-91).
    """
    deal_id: str | int = Field(
        ...,
        validation_alias=AliasChoices("deal_id", "dealId"),
        serialization_alias="deal_id",
    )
    total_changes: int = Field(
        ...,
        validation_alias=AliasChoices("total_changes", "totalChanges", "total"),
        serialization_alias="total_changes",
    )
    items: List[DealHistoryItemResponse] = Field(default_factory=list)
    page: Optional[int] = 1
    page_size: Optional[int] = 20

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)
