from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.custom_field import CustomField
from app.schemas.custom_field import (
    CustomFieldDTO,
    CreateCustomFieldDTO,
    UpdateCustomFieldDTO,
    SaveCustomFieldValuesDTO,
)

router = APIRouter(prefix="/custom-fields", tags=["Custom Fields Management (S2-08)"])


@router.get("", response_model=List[CustomFieldDTO], summary="Lấy danh sách các trường tùy chỉnh")
def get_custom_fields(
    entity_type: Optional[str] = Query(None, description="Lọc theo entity: customer | deal"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[CustomFieldDTO]:
    query = db.query(CustomField)
    if entity_type:
        query = query.filter(CustomField.entity_type == entity_type)
    records = query.order_by(CustomField.created_at.asc()).all()

    # Seed sample custom fields if empty
    if not records:
        sample_fields = [
            CustomField(
                entity_type="customer",
                field_name="tax_number",
                field_label="Mã số thuế doanh nghiệp",
                field_type="text",
                is_required=False,
            ),
            CustomField(
                entity_type="customer",
                field_name="annual_revenue",
                field_label="Doanh thu hàng năm (Tỷ VNĐ)",
                field_type="number",
                is_required=False,
            ),
            CustomField(
                entity_type="customer",
                field_name="customer_tier",
                field_label="Phân hạng khách hàng",
                field_type="select",
                options="Chiến lược (Tier 1),Tiềm năng (Tier 2),Tiêu chuẩn (Tier 3)",
                is_required=True,
                default_value="Tiêu chuẩn (Tier 3)",
            ),
            CustomField(
                entity_type="deal",
                field_name="decision_date",
                field_label="Hạn quyết định thầu",
                field_type="date",
                is_required=False,
            ),
        ]
        db.add_all(sample_fields)
        db.commit()
        records = db.query(CustomField).all()

    return [
        CustomFieldDTO(
            id=f.id,
            entity_type=f.entity_type,
            field_name=f.field_name,
            field_label=f.field_label,
            field_type=f.field_type,
            options=f.options,
            is_required=f.is_required,
            default_value=f.default_value,
        )
        for f in records
    ]


@router.post("", response_model=CustomFieldDTO, status_code=status.HTTP_201_CREATED, summary="Tạo mới trường tùy chỉnh")
def create_custom_field(
    dto: CreateCustomFieldDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CustomFieldDTO:
    cf = CustomField(
        entity_type=dto.entity_type,
        field_name=dto.field_name.strip().lower().replace(" ", "_"),
        field_label=dto.field_label.strip(),
        field_type=dto.field_type,
        options=dto.options,
        is_required=dto.is_required,
        default_value=dto.default_value,
    )
    db.add(cf)
    db.commit()
    db.refresh(cf)
    return CustomFieldDTO(
        id=cf.id,
        entity_type=cf.entity_type,
        field_name=cf.field_name,
        field_label=cf.field_label,
        field_type=cf.field_type,
        options=cf.options,
        is_required=cf.is_required,
        default_value=cf.default_value,
    )


@router.put("/{field_id}", response_model=CustomFieldDTO, summary="Cập nhật trường tùy chỉnh")
def update_custom_field(
    field_id: str,
    dto: UpdateCustomFieldDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CustomFieldDTO:
    cf = db.query(CustomField).filter(CustomField.id == field_id).first()
    if not cf:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy trường tùy chỉnh.")

    if dto.field_label is not None and dto.field_label.strip():
        cf.field_label = dto.field_label.strip()
    if dto.field_type is not None and dto.field_type.strip():
        cf.field_type = dto.field_type.strip()
    if dto.options is not None:
        cf.options = dto.options
    if dto.is_required is not None:
        cf.is_required = dto.is_required
    if dto.default_value is not None:
        cf.default_value = dto.default_value

    db.commit()
    db.refresh(cf)
    return CustomFieldDTO(
        id=cf.id,
        entity_type=cf.entity_type,
        field_name=cf.field_name,
        field_label=cf.field_label,
        field_type=cf.field_type,
        options=cf.options,
        is_required=cf.is_required,
        default_value=cf.default_value,
    )


@router.get("/values", summary="Lấy danh sách giá trị trường tùy chỉnh theo thực thể")
def get_custom_field_values(
    entity_type: str = Query("customer", description="Loại thực thể: customer | deal"),
    entity_id: str = Query("sample", description="Mã định danh thực thể"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.custom_field import CustomFieldValue
    records = db.query(CustomFieldValue).filter(
        CustomFieldValue.entity_type == entity_type,
        CustomFieldValue.entity_id == entity_id,
    ).all()
    values_dict = {r.field_name: r.value for r in records}
    return {"entity_type": entity_type, "entity_id": entity_id, "values": values_dict}


@router.post("/values", summary="Lưu giá trị các trường tùy chỉnh và xác thực dữ liệu")
def save_custom_field_values(
    dto: SaveCustomFieldValuesDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.custom_field import CustomFieldValue
    # 1. Load custom field definitions for this entity_type
    fields = db.query(CustomField).filter(CustomField.entity_type == dto.entity_type).all()
    field_map = {f.field_name: f for f in fields}

    # 2. Validate input against definitions
    for field_name, f_def in field_map.items():
        raw_val = dto.values.get(field_name)
        val_str = str(raw_val).strip() if raw_val is not None else ""

        # Validate required
        if f_def.is_required and not val_str:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Trường '{f_def.field_label}' là bắt buộc nhập.",
            )

        # Validate number
        if val_str and f_def.field_type == "number":
            try:
                float(val_str)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Giá trị của trường '{f_def.field_label}' phải là số hợp lệ.",
                )

        # Validate select
        if val_str and f_def.field_type == "select" and f_def.options:
            allowed = [opt.strip() for opt in f_def.options.split(",") if opt.strip()]
            if val_str not in allowed:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Giá trị '{val_str}' của trường '{f_def.field_label}' không nằm trong danh sách lựa chọn cho phép.",
                )

        # Validate date (YYYY-MM-DD)
        if val_str and f_def.field_type == "date":
            from datetime import datetime as dt
            try:
                dt.strptime(val_str, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Giá trị của trường '{f_def.field_label}' phải theo định dạng ngày YYYY-MM-DD.",
                )

    # 3. Save or update values
    saved_values = {}
    for f_name, raw_val in dto.values.items():
        val_str = str(raw_val).strip() if raw_val is not None else ""
        existing = db.query(CustomFieldValue).filter(
            CustomFieldValue.entity_type == dto.entity_type,
            CustomFieldValue.entity_id == dto.entity_id,
            CustomFieldValue.field_name == f_name,
        ).first()

        if existing:
            existing.value = val_str
        else:
            new_record = CustomFieldValue(
                entity_type=dto.entity_type,
                entity_id=dto.entity_id,
                field_name=f_name,
                value=val_str,
            )
            db.add(new_record)
        saved_values[f_name] = val_str

    db.commit()
    return {
        "message": "Đã lưu và xác thực thành công các giá trị trường tùy chỉnh.",
        "entity_type": dto.entity_type,
        "entity_id": dto.entity_id,
        "values": saved_values,
    }


@router.delete("/{field_id}", summary="Xóa trường tùy chỉnh (bảo toàn dữ liệu hiện có)")
def delete_custom_field(
    field_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cf = db.query(CustomField).filter(CustomField.id == field_id).first()
    if not cf:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy trường tùy chỉnh.")
    db.delete(cf)
    db.commit()
    return {"message": "Đã xóa trường tùy chỉnh thành công. Dữ liệu thực tế được bảo toàn."}
