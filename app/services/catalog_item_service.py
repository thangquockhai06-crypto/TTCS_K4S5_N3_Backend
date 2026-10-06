from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Tuple
import uuid

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.product import Product
from app.models.quotation_line import QuotationLine
from app.models.user import User
from app.schemas.catalog_item import CatalogItemCreateDTO, CatalogItemDTO, CatalogItemUpdateDTO


SALES_DIRECTOR_ROLES = {"sales director"}


def is_sales_director(user: User) -> bool:
    return (user.role or "").strip().lower() in SALES_DIRECTOR_ROLES


def requires_discount_approval(unit_price: Decimal, catalog_item: Product) -> bool:
    """Return true when the quoted unit price is below the catalog floor price."""
    floor_price = Decimal(str(catalog_item.floor_price or 0))
    return Decimal(str(unit_price)) < floor_price


def _money(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


def _item_dto(item: Product, include_cost: bool) -> CatalogItemDTO:
    return CatalogItemDTO(
        id=item.id,
        code=item.code,
        name=item.name,
        type=item.item_type or "ONE_TIME_PRODUCT",
        unit_of_measure=item.unit_of_measure or item.unit,
        list_price=_money(item.list_price if item.list_price is not None else item.selling_price),
        floor_price=_money(item.floor_price),
        cost_price=_money(item.cost_price) if include_cost else None,
        currency=item.currency or "VND",
        status=item.status or ("ACTIVE" if item.is_active else "DISCONTINUED"),
        discontinued_at=item.discontinued_at.isoformat() if item.discontinued_at else None,
        created_at=item.created_at.isoformat() if item.created_at else None,
        updated_at=item.updated_at.isoformat() if item.updated_at else None,
    )


def _audit(db: Session, user: User, item: Product, field: str, old, new) -> None:
    db.add(
        AuditLog(
            id=str(uuid.uuid4()),
            user_id=user.id,
            performed_by=user.id,
            user_name=user.full_name,
            user_email=user.email,
            action="CATALOG_ITEM_UPDATED",
            target_type="catalog_item",
            target_id=item.id,
            field_name=field,
            old_value=None if old is None else str(old),
            new_value=None if new is None else str(new),
            details=f"Catalog item {item.code} field {field} changed",
        )
    )


class CatalogItemService:
    def __init__(self, db: Session):
        self.db = db

    def list_items(
        self,
        user: User,
        search: Optional[str] = None,
        item_type: Optional[str] = None,
        item_status: Optional[str] = None,
        sort: str = "code",
        descending: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[CatalogItemDTO], int]:
        if sort.lower() in {"cost_price", "costprice", "costPrice"} and not is_sales_director(user):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Không được phép sắp xếp theo giá vốn.")
        sort_columns = {
            "code": Product.code,
            "name": Product.name,
            "list_price": Product.list_price,
            "listPrice": Product.list_price,
            "floor_price": Product.floor_price,
            "floorPrice": Product.floor_price,
            "status": Product.status,
            "created_at": Product.created_at,
            "cost_price": Product.cost_price,
            "costPrice": Product.cost_price,
        }
        sort_column = sort_columns.get(sort, Product.code)
        query = self.db.query(Product)
        if search and search.strip():
            pattern = f"%{search.strip()}%"
            query = query.filter(Product.code.ilike(pattern) | Product.name.ilike(pattern))
        if item_type:
            query = query.filter(Product.item_type == item_type)
        if item_status:
            query = query.filter(Product.status == item_status)
        total = query.count()
        ordering = sort_column.desc() if descending else sort_column.asc()
        records = query.order_by(ordering).offset(skip).limit(limit).all()
        return [_item_dto(item, is_sales_director(user)) for item in records], total

    def get_item(self, item_id: str, user: User) -> CatalogItemDTO:
        item = self.db.query(Product).filter(Product.id == item_id).first()
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy mục catalog.")
        return _item_dto(item, is_sales_director(user))

    def create_item(self, dto: CatalogItemCreateDTO, user: User) -> CatalogItemDTO:
        self._require_director(user)
        code = dto.code.strip().upper()
        if self.db.query(Product).filter(Product.code == code).first():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Mã catalog '{code}' đã tồn tại.")
        item = Product(
            id=str(uuid.uuid4()),
            code=code,
            name=dto.name.strip(),
            category="Catalog",
            unit=dto.unit_of_measure.strip(),
            unit_of_measure=dto.unit_of_measure.strip(),
            item_type=dto.type,
            selling_price=dto.list_price,
            list_price=dto.list_price,
            floor_price=dto.floor_price,
            cost_price=dto.cost_price,
            currency=dto.currency.upper(),
            status="ACTIVE",
            is_active=True,
            created_by=user.id,
            updated_by=user.id,
        )
        self.db.add(item)
        _audit(self.db, user, item, "list_price", None, dto.list_price)
        _audit(self.db, user, item, "floor_price", None, dto.floor_price)
        _audit(self.db, user, item, "cost_price", None, dto.cost_price)
        try:
            self.db.commit()
            self.db.refresh(item)
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Mã catalog đã tồn tại.")
        return _item_dto(item, True)

    def update_item(self, item_id: str, dto: CatalogItemUpdateDTO, user: User) -> CatalogItemDTO:
        self._require_director(user)
        item = self.db.query(Product).filter(Product.id == item_id).first()
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy mục catalog.")
        old_values = {
            "list_price": item.list_price,
            "floor_price": item.floor_price,
            "cost_price": item.cost_price,
        }
        if dto.name is not None:
            item.name = dto.name.strip()
        if dto.type is not None:
            item.item_type = dto.type
        if dto.unit_of_measure is not None:
            item.unit_of_measure = dto.unit_of_measure.strip()
            item.unit = item.unit_of_measure
        if dto.list_price is not None:
            item.list_price = dto.list_price
            item.selling_price = dto.list_price
        if dto.floor_price is not None:
            item.floor_price = dto.floor_price
        if dto.cost_price is not None:
            item.cost_price = dto.cost_price
        if dto.currency is not None:
            item.currency = dto.currency.upper()
        if item.floor_price > item.list_price:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="floorPrice phải nhỏ hơn hoặc bằng listPrice.")
        item.updated_by = user.id
        for field in ("list_price", "floor_price", "cost_price"):
            new_value = getattr(item, field)
            if _money(old_values[field]) != _money(new_value):
                _audit(self.db, user, item, field, old_values[field], new_value)
        self.db.commit()
        self.db.refresh(item)
        return _item_dto(item, True)

    def delete_item(self, item_id: str, user: User) -> None:
        self._require_director(user)
        item = self.db.query(Product).filter(Product.id == item_id).first()
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy mục catalog.")
        if self.is_used_in_quote(item_id):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Mục catalog đã xuất hiện trong báo giá; chỉ có thể ngừng bán.")
        self.db.delete(item)
        self.db.commit()

    def discontinue(self, item_id: str, user: User, reactivate: bool = False) -> CatalogItemDTO:
        self._require_director(user)
        item = self.db.query(Product).filter(Product.id == item_id).first()
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy mục catalog.")
        old_status = item.status
        item.status = "ACTIVE" if reactivate else "DISCONTINUED"
        item.is_active = reactivate
        item.discontinued_at = None if reactivate else datetime.utcnow()
        item.updated_by = user.id
        _audit(self.db, user, item, "status", old_status, item.status)
        self.db.commit()
        self.db.refresh(item)
        return _item_dto(item, True)

    def is_used_in_quote(self, item_id: str) -> bool:
        return self.db.query(QuotationLine.id).filter(QuotationLine.product_id == item_id).first() is not None

    @staticmethod
    def _require_director(user: User) -> None:
        if not is_sales_director(user):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Chỉ Sales Director được quản lý catalog.")
