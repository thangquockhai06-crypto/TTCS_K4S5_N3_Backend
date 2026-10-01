from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.category import Category
from app.schemas.category import (
    CategoryDTO,
    CreateCategoryDTO,
    UpdateCategoryDTO,
    ReorderCategoriesDTO,
)

router = APIRouter(prefix="/categories", tags=["Common Categories Management (S2-07)"])


@router.get("", response_model=List[CategoryDTO], summary="Lấy danh mục theo loại (lead_source hoặc industry)")
def get_categories(
    type: Optional[str] = Query(None, description="Loại danh mục: lead_source | industry"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[CategoryDTO]:
    query = db.query(Category)
    if type and type != "all":
        query = query.filter(Category.type == type)
    records = query.order_by(Category.order_index.asc(), Category.created_at.asc()).all()

    # If empty, seed default items
    if not records and type:
        default_items = []
        if type == "lead_source":
            default_items = [
                ("WEBSITE", "Website Doanh Nghiệp"),
                ("REFERRAL", "Giới thiệu / Đối tác (Referral)"),
                ("EVENT", "Hội thảo / Sự kiện Triển lãm"),
                ("LINKEDIN", "Mạng xã hội LinkedIn B2B"),
                ("COLD_CALL", "Liên hệ Outbound / Telesales"),
            ]
        elif type == "industry":
            default_items = [
                ("TECH", "Công nghệ thông tin & Viễn thông"),
                ("FINANCE", "Tài chính - Ngân hàng - Bảo hiểm"),
                ("MANUFACTURING", "Sản xuất & Chế tạo công nghiệp"),
                ("RETAIL", "Bán lẻ & Thương mại điện tử"),
                ("REAL_ESTATE", "Bất động sản & Xây dựng"),
            ]
        for idx, (code, name) in enumerate(default_items):
            cat = Category(type=type, code=code, name=name, order_index=idx, is_system=True)
            db.add(cat)
        db.commit()
        records = db.query(Category).filter(Category.type == type).order_by(Category.order_index.asc()).all()

    return [
        CategoryDTO(
            id=c.id,
            type=c.type,
            code=c.code,
            name=c.name,
            order_index=c.order_index,
            is_system=c.is_system,
            usage_count=c.usage_count,
        )
        for c in records
    ]


@router.post("", response_model=CategoryDTO, status_code=status.HTTP_201_CREATED, summary="Tạo mới danh mục")
def create_category(
    dto: CreateCategoryDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CategoryDTO:
    cat = Category(
        type=dto.type.strip(),
        code=dto.code.strip().upper(),
        name=dto.name.strip(),
        order_index=dto.order_index or 0,
        is_system=False,
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return CategoryDTO(
        id=cat.id,
        type=cat.type,
        code=cat.code,
        name=cat.name,
        order_index=cat.order_index,
        is_system=cat.is_system,
        usage_count=cat.usage_count,
    )


@router.put("/reorder", summary="Cập nhật thứ tự sắp xếp kéo thả danh mục (S2-07)")
def reorder_categories(
    dto: ReorderCategoriesDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    for item in dto.items:
        cat = db.query(Category).filter(Category.id == item.id).first()
        if cat:
            cat.order_index = item.order_index
    db.commit()
    return {"message": "Cập nhật thứ tự hiển thị thành công."}


@router.delete("/{category_id}", summary="Xóa danh mục (ngăn chặn nếu đang được sử dụng)")
def delete_category(
    category_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy danh mục.")

    # QUY TẮC S2-07: Ngăn chặn xóa khi đang có dữ liệu sử dụng
    if cat.usage_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Không thể xóa danh mục '{cat.name}' vì đang có {cat.usage_count} khách hàng/cơ hội sử dụng.",
        )

    db.delete(cat)
    db.commit()
    return {"message": f"Đã xóa danh mục '{cat.name}' thành công."}
