"""
SQLAlchemy Models cho Phân hệ Cấu hình chấm điểm Lead (SCRUM-48 / Sprint 4).
Hỗ trợ:
- Bảng lead_scoring_rules: Lưu trữ danh mục quy tắc chấm điểm Lead theo tiêu chí khai báo động.
- Bảng lead_scoring_settings: Lưu trữ cấu hình ngưỡng phân loại nhiệt độ Lead (Hot/Warm/Cold).
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class LeadScoringRule(Base):
    """
    Quy tắc chấm điểm Lead (Lead Scoring Rule).
    Tiêu chí khai báo: INDUSTRY, COMPANY_SIZE, SOURCE, INTEREST_LEVEL.
    """
    __tablename__ = "lead_scoring_rules"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    criteria_type = Column(String(50), nullable=False, index=True)
    criteria_value = Column(String(150), nullable=False)
    score = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class LeadScoringSettings(Base):
    """
    Cấu hình ngưỡng phân loại nhiệt độ Lead (Singleton ID=1).
    - Hot threshold (mặc định >= 70 điểm).
    - Warm threshold (mặc định >= 40 điểm).
    - Cold (điểm < warm_threshold).
    """
    __tablename__ = "lead_scoring_settings"

    id = Column(Integer, primary_key=True, default=1)
    hot_threshold = Column(Integer, nullable=False, default=70)
    warm_threshold = Column(Integer, nullable=False, default=40)
    updated_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    updater = relationship("User", foreign_keys=[updated_by])
