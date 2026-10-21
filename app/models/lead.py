import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Lead(Base):
    """
    Mô hình quản lý Khách hàng tiềm năng (Lead) - SCRUM-40 / Sprint 4.
    Phục vụ: Nhân viên Marketing, Nhân viên Kinh doanh, Quản trị viên.
    """
    __tablename__ = "leads"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    full_name = Column(String(150), nullable=False)
    phone = Column(String(20), nullable=False, index=True)
    email = Column(String(150), nullable=True, index=True)
    company = Column(String(255), nullable=True, index=True)
    interest_need = Column(Text, nullable=True)
    source = Column(String(100), nullable=False, index=True)  # BẮT BUỘC THEO AC
    status = Column(String(50), default="NEW", nullable=False, index=True)  # NEW, CONTACTED, QUALIFIED, DISQUALIFIED, CONVERTED, MERGED
    notes = Column(Text, nullable=True)
    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    campaign_id = Column(String(36), ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True, index=True)
    merged_into_lead_id = Column(String(36), ForeignKey("leads.id", ondelete="SET NULL"), nullable=True, index=True)
    converted_customer_id = Column(String(36), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)

    # Tiêu chí & Điểm số (SCRUM-48 Lead Scoring)
    score = Column(Integer, default=0, nullable=False, index=True)
    temperature = Column(String(20), default="COLD", nullable=False, index=True)  # HOT, WARM, COLD
    industry = Column(String(100), nullable=True, index=True)
    company_size = Column(String(50), nullable=True)
    interest_level = Column(String(50), nullable=True)  # HIGH, MEDIUM, LOW

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Quan hệ
    creator = relationship("User", foreign_keys=[created_by])
    campaign = relationship("Campaign", back_populates="leads")
    merged_into_lead = relationship("Lead", remote_side=[id], foreign_keys=[merged_into_lead_id])
    converted_customer = relationship("Customer", foreign_keys=[converted_customer_id])
    activities = relationship("Activity", back_populates="lead", cascade="all, delete-orphan", foreign_keys="Activity.lead_id")

