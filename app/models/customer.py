import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, Enum, ForeignKey, Numeric, Boolean
from sqlalchemy.orm import relationship
from app.database import Base

class Customer(Base):
    __tablename__ = "customers"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    full_name = Column(String(150), nullable=False)
    email = Column(String(120), nullable=False)
    phone = Column(String(30), nullable=False)
    company = Column(String(150), default="")
    status = Column(
        Enum("lead", "prospect", "active", "inactive", name="customer_status_enum"),
        default="lead",
        nullable=False,
    )
    health_score = Column(Integer, default=85, nullable=False)
    assigned_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    avatar_url = Column(Text, nullable=True)

    # EP-03 Extensions
    tax_code = Column(String(50), unique=True, index=True, nullable=True)
    parent_customer_id = Column(String(36), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    total_contract_value = Column(Numeric(15, 2), default=0.00, nullable=False)
    last_interaction_at = Column(DateTime, nullable=True, index=True)
    risk_flag = Column(Boolean, default=False, nullable=False, index=True)
    risk_reason = Column(String(255), nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    industry = Column(String(100), default="", nullable=True)
    tier = Column(String(50), default="Enterprise", nullable=True)
    location = Column(String(200), default="", nullable=True)
    website = Column(String(150), default="", nullable=True)
    notes_summary = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    assigned_user = relationship("User", back_populates="customers")
    parent = relationship("Customer", remote_side=[id], backref="children")
    contacts = relationship("Contact", back_populates="customer", cascade="all, delete-orphan")
    deals = relationship("Deal", back_populates="customer", cascade="all, delete-orphan")
    activities = relationship("Activity", back_populates="customer", cascade="all, delete-orphan")
    notes = relationship("Note", back_populates="customer", cascade="all, delete-orphan")
    support_tickets = relationship("SupportTicket", back_populates="customer", cascade="all, delete-orphan")
