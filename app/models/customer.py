import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, Enum, ForeignKey, Boolean, event
from sqlalchemy.orm import relationship
from app.database import Base
from app.core.customer_search import normalize_phone, normalize_tax_code, normalize_text

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
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    industry = Column(String(50), nullable=True, index=True)
    company_size = Column(String(30), nullable=True, index=True)
    region = Column(String(100), nullable=True, index=True)
    tax_code = Column(String(50), nullable=True)
    website = Column(String(255), nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    merged_into_id = Column(String(36), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    normalized_name = Column(String(255), nullable=False, default="", index=True)
    normalized_tax_code = Column(String(50), nullable=False, default="", index=True)
    normalized_phone = Column(String(30), nullable=False, default="", index=True)

    # Relationships
    assigned_user = relationship("User", back_populates="customers")
    contacts = relationship("Contact", back_populates="customer", cascade="all, delete-orphan", order_by="Contact.is_primary.desc(), Contact.created_at.asc()")
    deals = relationship("Deal", back_populates="customer", cascade="all, delete-orphan")
    activities = relationship("Activity", back_populates="customer", cascade="all, delete-orphan")
    notes = relationship("Note", back_populates="customer", cascade="all, delete-orphan")
    merged_into = relationship("Customer", remote_side=[id], foreign_keys=[merged_into_id])



class Contact(Base):
    __tablename__ = "customer_contacts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = Column(String(36), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    full_name = Column(String(150), nullable=False)
    phone = Column(String(30), nullable=False)
    normalized_phone = Column(String(30), nullable=False, index=True)
    email = Column(String(120), nullable=True)
    is_primary = Column(Integer, nullable=False, default=0, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    customer = relationship("Customer", back_populates="contacts")


@event.listens_for(Customer, "before_insert")
@event.listens_for(Customer, "before_update")
def _sync_customer_search_fields(mapper, connection, target: Customer) -> None:
    target.normalized_name = normalize_text(f"{target.full_name or ''} {target.company or ''}")
    target.normalized_tax_code = normalize_tax_code(target.tax_code or "")
    target.normalized_phone = normalize_phone(target.phone or "")


@event.listens_for(Contact, "before_insert")
@event.listens_for(Contact, "before_update")
def _sync_contact_search_fields(mapper, connection, target: Contact) -> None:
    target.normalized_phone = normalize_phone(target.phone or "")
