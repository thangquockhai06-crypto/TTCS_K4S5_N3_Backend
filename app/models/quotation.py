import uuid
from datetime import datetime
from sqlalchemy import Column, String, Numeric, Integer, Boolean, Date, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Quotation(Base):
    __tablename__ = "quotations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    quote_number = Column(String(50), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    deal_id = Column(String(36), ForeignKey("deals.id", ondelete="CASCADE"), nullable=True, index=True)
    customer_id = Column(String(36), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    owner_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # S7-03: Versioning & Multi-version tracking
    version = Column(Integer, default=1, nullable=False)
    is_effective = Column(Boolean, default=True, nullable=False, index=True)
    parent_quote_id = Column(String(36), ForeignKey("quotations.id", ondelete="SET NULL"), nullable=True)

    # S7-01: Pricing and recalculations
    subtotal = Column(Numeric(15, 2), default=0.00, nullable=False)
    total_discount_amount = Column(Numeric(15, 2), default=0.00, nullable=False)
    total_discount_percent = Column(Numeric(5, 2), default=0.00, nullable=False)
    vat_amount = Column(Numeric(15, 2), default=0.00, nullable=False)
    grand_total = Column(Numeric(15, 2), default=0.00, nullable=False)
    total_amount = Column(Numeric(15, 2), default=0.00, nullable=False)  # Backward compatibility

    # S7-02: Multi-level approval thresholds
    discount_threshold_percent = Column(Numeric(5, 2), default=15.00, nullable=False)
    requires_approval = Column(Boolean, default=False, nullable=False)
    approval_level = Column(String(50), nullable=True)  # team_leader, director

    # S7-01: Terms and validity
    valid_until = Column(Date, nullable=True, index=True)
    payment_terms = Column(String(255), nullable=True)
    delivery_terms = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)

    status = Column(String(50), default="draft", nullable=False, index=True)  # draft, pending_approval, approved, sent, accepted, rejected, expired

    # S7-06: Customer public access link token
    access_token = Column(String(64), unique=True, nullable=True, index=True)

    # S7-05: PDF template binding
    template_id = Column(String(36), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    customer = relationship("Customer")
    owner = relationship("User", foreign_keys=[owner_id])
    deal = relationship("Deal")
    items = relationship("QuoteItem", back_populates="quote", cascade="all, delete-orphan", lazy="joined")
    approval_history = relationship(
        "QuoteApprovalHistory",
        back_populates="quote",
        cascade="all, delete-orphan",
        order_by="QuoteApprovalHistory.created_at.asc()",
        lazy="joined",
    )
    parent_quote = relationship("Quotation", remote_side=[id])


class QuoteItem(Base):
    """
    S7-01: Dòng sản phẩm trong Báo giá.
    Hỗ trợ chiết khấu phần trăm / số tiền tuyệt đối, giá sàn (floor price) và VAT.
    """
    __tablename__ = "quote_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    quote_id = Column(String(36), ForeignKey("quotations.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    product_code = Column(String(50), nullable=True)
    product_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    quantity = Column(Integer, default=1, nullable=False)
    unit = Column(String(50), default="Gói", nullable=False)
    unit_price = Column(Numeric(15, 2), default=0.00, nullable=False)
    discount_type = Column(String(20), default="percent", nullable=False)  # percent | amount
    discount_value = Column(Numeric(15, 2), default=0.00, nullable=False)
    discount_amount = Column(Numeric(15, 2), default=0.00, nullable=False)
    floor_price = Column(Numeric(15, 2), nullable=True)
    vat_rate = Column(Numeric(5, 2), default=10.00, nullable=False)
    vat_amount = Column(Numeric(15, 2), default=0.00, nullable=False)
    line_total = Column(Numeric(15, 2), default=0.00, nullable=False)

    quote = relationship("Quotation", back_populates="items")


class QuoteApprovalHistory(Base):
    """
    S7-02: Nhật ký Phê duyệt Báo giá Bất biến (Immutable Audit Log).
    Lưu vết đầy đủ: tự động duyệt, duyệt, từ chối, trả lại sửa, gửi khách.
    """
    __tablename__ = "quote_approval_history"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    quote_id = Column(String(36), ForeignKey("quotations.id", ondelete="CASCADE"), nullable=False, index=True)
    action = Column(String(50), nullable=False)  # auto_approved, approved, rejected, returned_for_edit, sent
    approval_level = Column(String(50), nullable=True)  # team_leader, director, system
    performed_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    performed_by_name = Column(String(100), nullable=False)
    performed_by_role = Column(String(100), nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    quote = relationship("Quotation", back_populates="approval_history")
