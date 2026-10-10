import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey
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
    company = Column(String(255), nullable=True)
    interest_need = Column(Text, nullable=True)
    source = Column(String(100), nullable=False, index=True)  # BẮT BUỘC THEO AC
    status = Column(String(50), default="NEW", nullable=False, index=True)
    notes = Column(Text, nullable=True)
    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Quan hệ với người dùng tạo
    creator = relationship("User", foreign_keys=[created_by])
