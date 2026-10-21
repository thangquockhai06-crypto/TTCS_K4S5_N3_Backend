import uuid
from datetime import datetime
from sqlalchemy import Column, String, Numeric, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class DealItem(Base):
    """
    Model Dòng sản phẩm / Dịch vụ thuộc Cơ hội bán hàng (EP-05: S5-03 Products and Deal Items).
    Hỗ trợ số lượng, chiết khấu và chu kỳ thanh toán gói dịch vụ hàng năm/tháng.
    """
    __tablename__ = "deal_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    deal_id = Column(String(36), ForeignKey("deals.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True)
    product_name = Column(String(255), nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    unit_price = Column(Numeric(15, 2), default=0.00, nullable=False)
    discount_percent = Column(Numeric(5, 2), default=0.00, nullable=False)
    billing_cycle = Column(String(50), default="annual", nullable=False)  # annual, monthly, one_off
    subtotal = Column(Numeric(15, 2), default=0.00, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    deal = relationship("Deal", back_populates="deal_items")
    product = relationship("Product")
