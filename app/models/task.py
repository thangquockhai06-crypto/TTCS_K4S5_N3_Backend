import uuid
from datetime import datetime
from typing import Optional, List, Any
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    due_date = Column(DateTime, nullable=True, index=True)
    status = Column(String(50), nullable=False, default="pending", index=True)  # pending, in_progress, completed, overdue, cancelled
    priority = Column(String(20), nullable=False, default="medium")  # low, medium, high, urgent

    assignee_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    creator_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    customer_id = Column(String(36), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    deal_id = Column(String(36), ForeignKey("deals.id", ondelete="SET NULL"), nullable=True)

    # Flag/log danh sách các mốc đã gửi thông báo (ví dụ: ["1440m", "60m", "15m", "overdue"])
    # Đảm bảo không bao giờ gửi trùng lặp nhiều lần ở cùng một mốc
    reminded_milestones = Column(JSON, nullable=True, default=list)

    completed_at = Column(DateTime, nullable=True)
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
        if self.status in ["completed", "cancelled"]:
            return False
        if not self.due_date:
            return False
        return self.due_date < datetime.utcnow()

    @property
    def overdue_seconds(self) -> Optional[float]:
        if not self.is_overdue or not self.due_date:
            return None
        return max(0.0, (datetime.utcnow() - self.due_date).total_seconds())

    @property
    def time_remaining_seconds(self) -> Optional[float]:
        if not self.due_date or self.status in ["completed", "cancelled"]:
            return None
        return (self.due_date - datetime.utcnow()).total_seconds()

