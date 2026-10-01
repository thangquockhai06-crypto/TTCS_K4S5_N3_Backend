from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services.product_service import ProductService
from app.schemas.product import (
    ProductDTO,
    CreateProductDTO,
    UpdateProductDTO,
    PriceListDTO,
    CreatePriceListDTO,
)

router = APIRouter(prefix="/products", tags=["Products & Price Lists Management (S2-05)"])


@router.get("", response_model=List[ProductDTO], summary="Lấy danh sách sản phẩm & dịch vụ")
def get_products(
    search: Optional[str] = Query(None, description="Tìm kiếm theo tên hoặc mã"),
    category: Optional[str] = Query(None, description="Lọc theo nhóm sản phẩm"),
    isActive: Optional[bool] = Query(None, description="Lọc theo trạng thái kinh doanh"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[ProductDTO]:
    service = ProductService(db)
    dtos, _ = service.get_products(
        current_user=current_user,
        search=search,
        category=category,
        is_active=isActive,
        skip=skip,
        limit=limit,
    )
    return dtos


@router.post("", response_model=ProductDTO, status_code=status.HTTP_201_CREATED, summary="Tạo mới sản phẩm")
def create_product(
    dto: CreateProductDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProductDTO:
    service = ProductService(db)
    return service.create_product(dto, current_user)


@router.put("/{product_id}", response_model=ProductDTO, summary="Cập nhật sản phẩm")
def update_product(
    product_id: str,
    dto: UpdateProductDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProductDTO:
    service = ProductService(db)
    return service.update_product(product_id, dto, current_user)


@router.delete("/{product_id}", status_code=status.HTTP_200_OK, summary="Xóa sản phẩm")
def delete_product(
    product_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ProductService(db)
    service.delete_product(product_id)
    return {"message": "Xóa sản phẩm thành công."}


@router.get("/price-lists", response_model=List[PriceListDTO], summary="Lấy danh sách các bảng giá")
def get_price_lists(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[PriceListDTO]:
    service = ProductService(db)
    return service.get_price_lists()


@router.post("/price-lists", response_model=PriceListDTO, status_code=status.HTTP_201_CREATED, summary="Tạo mới bảng giá")
def create_price_list(
    dto: CreatePriceListDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PriceListDTO:
    service = ProductService(db)
    return service.create_price_list(dto)
