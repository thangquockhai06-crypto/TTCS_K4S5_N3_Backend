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


STAGE_LABEL_MAP = {
    "lead": "Khách hàng tiềm năng",
    "contact": "Đã liên hệ",
    "contacted": "Đã liên hệ",
    "proposal": "Đề xuất / Báo giá",
    "negotiation": "Đang thương thảo",
    "won": "Thành công (Won)",
    "lost": "Thất bại (Lost)",
}


def get_field_label(field_name: str) -> str:
    """Trả về nhãn tiếng Việt thân thiện theo tên trường dữ liệu."""
    if not field_name:
        return ""
    return FIELD_LABEL_MAP.get(field_name.strip(), field_name.replace("_", " ").title())


def format_field_value_and_description(
    field_name: str,
    old_value: Optional[str],
    new_value: Optional[str],
) -> tuple[str, str, str]:
    """
    Trả về (old_display_value, new_display_value, change_description) tiếng Việt thân thiện.
    """
    fn = (field_name or "").strip().lower()
    old_disp = old_value or ""
    new_disp = new_value or ""

    if fn == "stage":
        old_disp = STAGE_LABEL_MAP.get(old_disp.lower(), old_disp)
        new_disp = STAGE_LABEL_MAP.get(new_disp.lower(), new_disp)
        desc = f"Chuyển giai đoạn từ '{old_disp or 'Chưa xác định'}' sang '{new_disp}'"
    elif fn in ("amount", "value"):
        try:
            old_num = float(old_disp)
            old_disp = f"{old_num:,.0f} đ".replace(",", ".")
        except (ValueError, TypeError):
            pass
        try:
            new_num = float(new_disp)
            new_disp = f"{new_num:,.0f} đ".replace(",", ".")
        except (ValueError, TypeError):
            pass
        desc = f"Cập nhật giá trị cơ hội từ {old_disp or '0 đ'} thành {new_disp or '0 đ'}"
    elif fn in ("expected_close_date", "expectedclosedate"):
        desc = f"Thay đổi ngày dự kiến chốt từ {old_disp or 'Chưa đặt'} thành {new_disp or 'Chưa đặt'}"
    elif fn in ("assigned_to", "owner_id", "assignedto", "ownerid"):
        desc = "Điều chuyển người phụ trách cơ hội bán hàng"
    else:
        label = get_field_label(field_name)
        desc = f"Cập nhật thông tin '{label}'"

    return old_disp, new_disp, desc


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
    old_display_value: Optional[str] = Field(
        None,
        validation_alias=AliasChoices("old_display_value", "oldDisplayValue"),
        serialization_alias="old_display_value",
    )
    new_display_value: Optional[str] = Field(
        None,
        validation_alias=AliasChoices("new_display_value", "newDisplayValue"),
        serialization_alias="new_display_value",
    )
    change_description: Optional[str] = Field(
        None,
        validation_alias=AliasChoices("change_description", "changeDescription"),
        serialization_alias="change_description",
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


class FieldChangeStat(BaseModel):
    """Thống kê số lần thay đổi theo từng trường dữ liệu."""
    field_name: str
    field_label: str
    count: int

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class OperatorChangeStat(BaseModel):
    """Thống kê số lượt thao tác theo nhân sự."""
    user_id: str
    user_name: str
    count: int

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class DealHistorySummaryResponse(BaseModel):
    """
    Schema thống kê tổng hợp lịch sử cơ hội bán hàng (SCRUM-91).
    Cung cấp các chỉ số audit: tổng số lần đổi, số lần chuyển stage, số lần đổi giá trị, thời điểm đầu/cuối và top người thao tác.
    """
    deal_id: str = Field(
        ...,
        validation_alias=AliasChoices("deal_id", "dealId"),
        serialization_alias="deal_id",
    )
    total_changes: int = 0
    stage_changes_count: int = 0
    amount_changes_count: int = 0
    expected_close_date_changes_count: int = 0
    assigned_to_changes_count: int = 0
    first_change_at: Optional[datetime] = None
    last_change_at: Optional[datetime] = None
    changes_by_field: List[FieldChangeStat] = Field(default_factory=list)
    top_operators: List[OperatorChangeStat] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)
