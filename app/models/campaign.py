import uuid
from datetime import datetime, date
from sqlalchemy import Column, String, Numeric, Date, DateTime, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.database import Base


class Campaign(Base):
    """
    Mô hình Quản lý Chiến dịch Tiếp thị (Marketing Campaign) - SCRUM-44 / Sprint 4.
    Phục vụ: Nhân viên Marketing, Giám đốc kinh doanh, Quản trị viên.
    """
    __tablename__ = "campaigns"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200), nullable=False, index=True)
    channel = Column(String(100), nullable=False, index=True)
    budget = Column(Numeric(15, 2), default=0.00, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    status = Column(
        String(50),
        default="ACTIVE",
        nullable=False,
        index=True,
    )
    description = Column(Text, nullable=True)
    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    leads = relationship("Lead", back_populates="campaign", cascade="all")
    deals = relationship("Deal", back_populates="campaign", cascade="all")
