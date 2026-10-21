import uuid
from datetime import datetime, date
from typing import Optional, List, Any
from sqlalchemy import Column, String, DateTime, Text, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base


class Task(Base):
    """
    Model Quản lý Công việc & Nhắc việc (Sprint 6 & Task Reminders).
    """
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(String(50), default="medium", nullable=False)  # low, medium, high, urgent
    status = Column(String(50), default="pending", nullable=False, index=True)  # pending, in_progress, completed, overdue, cancelled
    is_completed = Column(Boolean, default=False, nullable=False, index=True)
    due_date = Column(DateTime, nullable=True, index=True)
    completed_at = Column(DateTime, nullable=True)

    assignee_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    creator_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    customer_id = Column(String(36), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    deal_id = Column(String(36), ForeignKey("deals.id", ondelete="SET NULL"), nullable=True, index=True)

    # Flag/log danh sách các mốc đã gửi thông báo (ví dụ: ["1440m", "60m", "15m", "overdue"])
    reminded_milestones = Column(JSON, nullable=True, default=list)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    assignee = relationship("User", foreign_keys=[assignee_id], back_populates="assigned_tasks")
    creator = relationship("User", foreign_keys=[creator_id], back_populates="created_tasks")
    customer = relationship("Customer")
    deal = relationship("Deal")
    notifications = relationship("Notification", back_populates="task", cascade="all, delete-orphan")

    @property
    def is_overdue(self) -> bool:
        if self.status in ["completed", "cancelled"] or self.is_completed:
            return False
        if not self.due_date:
            return False
        due_dt = datetime.combine(self.due_date, datetime.min.time()) if isinstance(self.due_date, date) and not isinstance(self.due_date, datetime) else self.due_date
        return due_dt < datetime.utcnow()

    @property
    def overdue_seconds(self) -> Optional[float]:
        if not self.is_overdue or not self.due_date:
            return None
        due_dt = datetime.combine(self.due_date, datetime.min.time()) if isinstance(self.due_date, date) and not isinstance(self.due_date, datetime) else self.due_date
        return max(0.0, (datetime.utcnow() - due_dt).total_seconds())

    @property
    def time_remaining_seconds(self) -> Optional[float]:
        if not self.due_date or self.status in ["completed", "cancelled"] or self.is_completed:
            return None
        due_dt = datetime.combine(self.due_date, datetime.min.time()) if isinstance(self.due_date, date) and not isinstance(self.due_date, datetime) else self.due_date
        return (due_dt - datetime.utcnow()).total_seconds()
