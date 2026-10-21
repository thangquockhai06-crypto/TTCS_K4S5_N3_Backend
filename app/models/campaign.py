import uuid
from datetime import datetime
from sqlalchemy import Column, String, Numeric, Date, DateTime, Text
from sqlalchemy.orm import relationship
from app.database import Base


class Campaign(Base):
    """
    Model Chiến dịch Tiếp thị (Marketing Campaign - EP-04: S4-03).
    Dùng để liên kết các Đầu mối (Leads) và Cơ hội bán hàng (Deals).
    """
    __tablename__ = "campaigns"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200), nullable=False, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    type = Column(String(50), default="Web Form", nullable=False)  # Web Form, Google Ads, Email, Webinar, Event
    status = Column(String(30), default="Active", nullable=False, index=True)  # Planning, Active, Completed, Paused
    budget = Column(Numeric(15, 2), default=0.00, nullable=False)
    expected_revenue = Column(Numeric(15, 2), default=0.00, nullable=False)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    description = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    leads = relationship("Lead", back_populates="campaign", cascade="all, delete-orphan")
    deals = relationship("Deal", back_populates="campaign")
