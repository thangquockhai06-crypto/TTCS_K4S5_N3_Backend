import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id = Column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True)

    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    # Loại thông báo: task_reminder, task_overdue, task_assigned, system, info
    type = Column(String(50), nullable=False, default="task_reminder")

    is_read = Column(Boolean, nullable=False, default=False, index=True)
    read_at = Column(DateTime, nullable=True)

    # Mốc thời gian được kích hoạt: 15m, 60m, 1440m, overdue, v.v.
    milestone = Column(String(50), nullable=True)
    metadata_json = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    user = relationship("User", back_populates="notifications")
    task = relationship("Task", back_populates="notifications")

