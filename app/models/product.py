import uuid
from datetime import datetime
from sqlalchemy import Column, String, Numeric, Boolean, Text, DateTime
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
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


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
