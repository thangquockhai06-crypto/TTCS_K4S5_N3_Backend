import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, Enum, ForeignKey
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
    tax_code = Column(String(50), nullable=True)
    assigned_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    avatar_url = Column(Text, nullable=True)
    parent_id = Column(String(36), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    assigned_user = relationship("User", back_populates="customers")
    deals = relationship("Deal", back_populates="customer", cascade="all, delete-orphan")
    activities = relationship("Activity", back_populates="customer", cascade="all, delete-orphan")
    notes = relationship("Note", back_populates="customer", cascade="all, delete-orphan")

    # Self-referential hierarchy (SCRUM-63)
    parent = relationship("Customer", remote_side=[id], back_populates="subsidiaries", lazy="selectin")
    subsidiaries = relationship("Customer", back_populates="parent", lazy="selectin")
