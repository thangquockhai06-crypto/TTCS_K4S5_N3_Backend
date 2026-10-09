import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from app.database import Base

class WebForm(Base):
    """
    Model quản lý biểu mẫu nhúng trên website (SCRUM-24 / S4-01).
    Hỗ trợ sinh mã nhúng, lưu nguồn khách hàng tiềm năng và liên kết với Leads.
    """
    __tablename__ = "web_forms"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200), nullable=False)
    form_key = Column(String(64), unique=True, nullable=False, index=True)
    lead_source = Column(String(100), default="Website Form", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_by = Column(String(36), nullable=True)  # User ID của nhân viên Marketing tạo form
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    leads = relationship("Lead", back_populates="form", cascade="all, delete-orphan")
