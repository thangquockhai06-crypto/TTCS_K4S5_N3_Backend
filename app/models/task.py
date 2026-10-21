import uuid
from datetime import datetime
from sqlalchemy import Column, String, Date, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Task(Base):
    """
    Model Quản lý Công việc (Sprint 6: S6-06, S6-07, S6-09).
    Hỗ trợ theo dõi tiêu đề, mô tả, mức ưu tiên, người phụ trách, hạn xử lý và trạng thái hoàn thành.
    """
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(String(50), default="medium", nullable=False)  # low, medium, high, urgent
    status = Column(String(50), default="pending", nullable=False, index=True)  # pending, in_progress, completed, cancelled
    is_completed = Column(Boolean, default=False, nullable=False, index=True)
    due_date = Column(Date, nullable=True, index=True)
    completed_at = Column(DateTime, nullable=True)

    assignee_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    creator_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    customer_id = Column(String(36), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    deal_id = Column(String(36), ForeignKey("deals.id", ondelete="SET NULL"), nullable=True, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    assignee = relationship("User", foreign_keys=[assignee_id])
    creator = relationship("User", foreign_keys=[creator_id])
    customer = relationship("Customer")
    deal = relationship("Deal")
