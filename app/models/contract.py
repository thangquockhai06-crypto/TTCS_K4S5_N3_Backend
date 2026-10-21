import uuid
from datetime import datetime, date
from sqlalchemy import Column, String, Numeric, Integer, Date, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Contract(Base):
    """
    S7-04 & S7-07: Hợp đồng Kinh tế chuyển đổi từ Báo giá (Quotations).
    Lưu trữ số hợp đồng duy nhất, các mốc thời gian, giá trị thực tế, và điều khoản thanh toán.
    """
    __tablename__ = "contracts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    contract_number = Column(String(100), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    quotation_id = Column(String(36), ForeignKey("quotations.id", ondelete="CASCADE"), nullable=False, index=True)
    deal_id = Column(String(36), ForeignKey("deals.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = Column(String(36), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    owner_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    total_value = Column(Numeric(15, 2), default=0.00, nullable=False)
    signing_date = Column(Date, nullable=False)
    effective_date = Column(Date, nullable=False)
    expiry_date = Column(Date, nullable=False, index=True)
    payment_terms = Column(String(255), nullable=True)
    delivery_terms = Column(String(255), nullable=True)

    # Status: active, expiring_soon, expired, renewed, terminated
    status = Column(String(50), default="active", nullable=False, index=True)
    template_id = Column(String(36), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    quotation = relationship("Quotation")
    deal = relationship("Deal")
    customer = relationship("Customer")
    owner = relationship("User", foreign_keys=[owner_id])
    items = relationship("ContractItem", back_populates="contract", cascade="all, delete-orphan", lazy="joined")

    @property
    def remaining_days(self) -> int:
        """S7-07: Tính số ngày còn lại đến khi hợp đồng hết hạn."""
        if not self.expiry_date:
            return 0
        today = date.today()
        return (self.expiry_date - today).days


class ContractItem(Base):
    """
    S7-04: Dòng sản phẩm trong Hợp đồng (kế thừa nguyên vẹn từ Báo giá đã chốt).
    """
    __tablename__ = "contract_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    contract_id = Column(String(36), ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    product_name = Column(String(255), nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    unit = Column(String(50), default="Gói", nullable=False)
    unit_price = Column(Numeric(15, 2), default=0.00, nullable=False)
    discount_amount = Column(Numeric(15, 2), default=0.00, nullable=False)
    line_total = Column(Numeric(15, 2), default=0.00, nullable=False)

    contract = relationship("Contract", back_populates="items")
