import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String, Boolean
from sqlalchemy.orm import relationship
from app.database import Base


class QuotationLine(Base):
    __tablename__ = "quotation_lines"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    quotation_id = Column(String(36), ForeignKey("quotations.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)
    product_code = Column(String(50), nullable=False)
    product_name = Column(String(255), nullable=False)
    quantity = Column(Numeric(15, 4), nullable=False)
    unit_price = Column(Numeric(15, 2), nullable=False)
    list_price_snapshot = Column(Numeric(15, 2), nullable=False)
    floor_price_snapshot = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="VND")
    discount_approval_required = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    quotation = relationship("Quotation", back_populates="lines")
    catalog_item = relationship("Product", back_populates="quotation_lines")
