from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.product import Product, PriceList
from app.models.quotation import Quotation


class ProductRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_products(
        self,
        search: Optional[str] = None,
        category: Optional[str] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Product], int]:
        query = self.db.query(Product)
        if search:
            pattern = f"%{search.strip()}%"
            query = query.filter(or_(Product.name.ilike(pattern), Product.code.ilike(pattern)))
        if category and category != "all":
            query = query.filter(Product.category == category)
        if is_active is not None:
            query = query.filter(Product.is_active == is_active)

        total = query.count()
        records = query.order_by(Product.code.asc()).offset(skip).limit(limit).all()
        return records, total

    def get_by_id(self, product_id: str) -> Optional[Product]:
        return self.db.query(Product).filter(Product.id == product_id).first()

    def get_by_code(self, code: str) -> Optional[Product]:
        return self.db.query(Product).filter(Product.code == code).first()

    def create(self, product: Product) -> Product:
        self.db.add(product)
        self.db.commit()
        self.db.refresh(product)
        return product

    def update(self, product: Product) -> Product:
        self.db.commit()
        self.db.refresh(product)
        return product

    def is_referenced_by_quotes(self, product_id: str, product_name: str) -> bool:
        """Kiểm tra sản phẩm có đang được tham chiếu trong bất kỳ báo giá nào không."""
        return self.count_quotes(product_id, product_name) > 0

    def count_quotes(self, product_id: str, product_name: str) -> int:
        """Đếm số lượng báo giá tham chiếu đến sản phẩm."""
        pattern = f"%{product_name}%"
        return self.db.query(Quotation).filter(Quotation.title.ilike(pattern)).count()

    def delete(self, product: Product) -> None:
        self.db.delete(product)
        self.db.commit()

    # Price Lists
    def get_price_lists(self) -> List[PriceList]:
        return self.db.query(PriceList).order_by(PriceList.is_default.desc(), PriceList.name.asc()).all()

    def create_price_list(self, price_list: PriceList) -> PriceList:
        self.db.add(price_list)
        self.db.commit()
        self.db.refresh(price_list)
        return price_list
