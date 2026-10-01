from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.custom_field import CustomField
from app.schemas.custom_field import CustomFieldDTO, CreateCustomFieldDTO

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
