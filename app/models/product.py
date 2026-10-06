import uuid
from datetime import datetime
from sqlalchemy import CheckConstraint, Column, String, Numeric, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Product(Base):
    """
    Model đại diện cho Sản phẩm / Dịch vụ CRM.
    Quy tắc an ninh:
    - cost_price (Giá vốn): Chỉ Giám đốc (Director) / Admin mới được phép xem (S2-05).
    - Không thể xóa sản phẩm nếu đã được liên kết trong Báo giá (Quotation).
    """
    __tablename__ = "products"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    category = Column(String(100), default="Phần mềm", nullable=False)
    unit = Column(String(50), default="Gói/Năm", nullable=False)
    selling_price = Column(Numeric(15, 2), default=0.00, nullable=False)
    cost_price = Column(Numeric(15, 2), default=0.00, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Standard catalog / price-book fields.
    item_type = Column("type", String(30), default="ONE_TIME_PRODUCT", nullable=False)
    unit_of_measure = Column(String(50), default="unit", nullable=False)
    list_price = Column(Numeric(15, 2), default=0.00, nullable=False)
    floor_price = Column(Numeric(15, 2), default=0.00, nullable=False)
    status = Column(String(20), default="ACTIVE", nullable=False)
    currency = Column(String(3), default="VND", nullable=False)
    discontinued_at = Column(DateTime, nullable=True)
    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    quotation_lines = relationship("QuotationLine", back_populates="catalog_item")

    __table_args__ = (
        CheckConstraint("list_price >= 0", name="ck_product_list_price_non_negative"),
        CheckConstraint("floor_price >= 0", name="ck_product_floor_price_non_negative"),
        CheckConstraint("cost_price >= 0", name="ck_product_cost_price_non_negative"),
        CheckConstraint("floor_price <= list_price", name="ck_product_floor_le_list"),
    )


class PriceList(Base):
    """
    Model quản lý các Bảng giá tiêu chuẩn và chính sách chiết khấu.
    """
    __tablename__ = "price_lists"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(150), nullable=False)
    code = Column(String(50), unique=True, nullable=False, index=True)
    currency = Column(String(10), default="VND", nullable=False)
    discount_percent = Column(Numeric(5, 2), default=0.00, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
