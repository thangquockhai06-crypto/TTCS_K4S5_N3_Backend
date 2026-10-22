import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base


class ReminderSetting(Base):
    __tablename__ = "reminder_settings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # user_id = NULL biểu thị cấu hình mặc định chung của hệ thống
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, unique=True, index=True)

    # Danh sách các mốc thời gian nhắc trước hạn (tính bằng phút)
    # Ví dụ mặc định: [15, 60, 1440] -> Nhắc trước 15 phút, 1 giờ (60m), 1 ngày (1440m)
    remind_before_minutes = Column(JSON, nullable=False, default=lambda: [15, 60, 1440])

    notify_on_overdue = Column(Boolean, nullable=False, default=True)
    enable_in_app = Column(Boolean, nullable=False, default=True)
    enable_email = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    user = relationship("User", back_populates="reminder_setting")

