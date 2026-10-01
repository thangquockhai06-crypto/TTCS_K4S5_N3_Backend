from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.product import Product, PriceList
from app.repositories.product_repository import ProductRepository
from app.schemas.product import (
    ProductDTO,
    CreateProductDTO,
    UpdateProductDTO,
    PriceListDTO,
    CreatePriceListDTO,
)

DIRECTOR_ROLES = {"super admin", "admin", "quản trị viên", "sales director", "director", "vp of sales", "giám đốc kinh doanh"}


def is_director_or_admin(user: User) -> bool:
    role = (user.role or "").strip().lower()
    return role in DIRECTOR_ROLES or "director" in role or "admin" in role


class ProductService:
    def __init__(self, db: Session) -> None:
        self.repo = ProductRepository(db)

    def get_products(
        self,
        current_user: User,
        search: Optional[str] = None,
        category: Optional[str] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[ProductDTO], int]:
        records, total = self.repo.get_products(
            search=search, category=category, is_active=is_active, skip=skip, limit=limit
        )

        can_view_cost = is_director_or_admin(current_user)

        dtos = [
            ProductDTO(
                id=p.id,
                code=p.code,
                name=p.name,
                category=p.category,
                unit=p.unit,
                selling_price=float(p.selling_price),
                cost_price=float(p.cost_price) if can_view_cost else None,
                description=p.description,
                is_active=p.is_active,
                created_at=p.created_at,
            )
            for p in records
        ]
        return dtos, total

    def create_product(self, dto: CreateProductDTO, current_user: User) -> ProductDTO:
        existing = self.repo.get_by_code(dto.code.strip())
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Mã sản phẩm '{dto.code}' đã tồn tại trong hệ thống.",
            )

        product = Product(
            code=dto.code.strip().upper(),
            name=dto.name.strip(),
            category=dto.category.strip(),
            unit=dto.unit.strip(),
            selling_price=dto.selling_price,
            cost_price=dto.cost_price,
            description=dto.description,
            is_active=dto.is_active,
        )
        saved = self.repo.create(product)
        can_view_cost = is_director_or_admin(current_user)

        return ProductDTO(
            id=saved.id,
            code=saved.code,
            name=saved.name,
            category=saved.category,
            unit=saved.unit,
            selling_price=float(saved.selling_price),
            cost_price=float(saved.cost_price) if can_view_cost else None,
            description=saved.description,
            is_active=saved.is_active,
            created_at=saved.created_at,
        )

    def update_product(
        self, product_id: str, dto: UpdateProductDTO, current_user: User
    ) -> ProductDTO:
        product = self.repo.get_by_id(product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy sản phẩm yêu cầu.",
            )

        if dto.name is not None:
            product.name = dto.name.strip()
        if dto.category is not None:
            product.category = dto.category.strip()
        if dto.unit is not None:
            product.unit = dto.unit.strip()
        if dto.selling_price is not None:
            product.selling_price = dto.selling_price
        if dto.cost_price is not None:
            if not is_director_or_admin(current_user):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Chỉ Giám đốc (Director) mới có quyền chỉnh sửa Giá vốn sản phẩm.",
                )
            product.cost_price = dto.cost_price
        if dto.description is not None:
            product.description = dto.description
        if dto.is_active is not None:
            product.is_active = dto.is_active

        saved = self.repo.update(product)
        can_view_cost = is_director_or_admin(current_user)

        return ProductDTO(
            id=saved.id,
            code=saved.code,
            name=saved.name,
            category=saved.category,
            unit=saved.unit,
            selling_price=float(saved.selling_price),
            cost_price=float(saved.cost_price) if can_view_cost else None,
            description=saved.description,
            is_active=saved.is_active,
            created_at=saved.created_at,
        )

    def delete_product(self, product_id: str) -> None:
        product = self.repo.get_by_id(product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy sản phẩm yêu cầu.",
            )

        # QUY TẮC AN NINH S2-05: Ngăn chặn xóa sản phẩm đã có báo giá tham chiếu
        if self.repo.is_referenced_by_quotes(product_id, product.name):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Không thể xóa sản phẩm '{product.name}' vì đang được tham chiếu trong Báo giá.",
            )

        self.repo.delete(product)

    # Price Lists
    def get_price_lists(self) -> List[PriceListDTO]:
        records = self.repo.get_price_lists()
        return [
            PriceListDTO(
                id=p.id,
                name=p.name,
                code=p.code,
                currency=p.currency,
                discount_percent=float(p.discount_percent),
                is_default=p.is_default,
                description=p.description,
            )
            for p in records
        ]

    def create_price_list(self, dto: CreatePriceListDTO) -> PriceListDTO:
        pl = PriceList(
            name=dto.name.strip(),
            code=dto.code.strip().upper(),
            currency=dto.currency,
            discount_percent=dto.discount_percent,
            is_default=dto.is_default,
            description=dto.description,
        )
        saved = self.repo.create_price_list(pl)
        return PriceListDTO(
            id=saved.id,
            name=saved.name,
            code=saved.code,
            currency=saved.currency,
            discount_percent=float(saved.discount_percent),
            is_default=saved.is_default,
            description=saved.description,
        )
