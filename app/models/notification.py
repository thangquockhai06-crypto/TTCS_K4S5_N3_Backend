import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base


class Notification(Base):
    """
    Hệ thống Thông báo In-App Bất đồng bộ:
    - Hỗ trợ sự kiện hệ thống (S7-08): phân bổ lead, báo giá chờ duyệt, khách hàng phản hồi báo giá,
      giao việc mới, cơ hội bán hàng bị ứ đọng (stalled), hợp đồng sắp hết hạn.
    - Hỗ trợ nhắc việc sắp đến hạn & việc quá hạn (Task Reminders / Overdue).
    """
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id = Column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True, index=True)

    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=True)
    description = Column(Text, nullable=True)

    # Loại thông báo: task_reminder, task_overdue, task_assigned, lead_assigned, quote_pending, etc.
    type = Column(String(50), nullable=False, default="task_reminder", index=True)
    target_type = Column(String(50), nullable=True)  # lead, deal, quotation, task, contract
    target_id = Column(String(36), nullable=True)
    link_url = Column(String(255), nullable=True)

    is_read = Column(Boolean, default=False, nullable=False, index=True)
    read_at = Column(DateTime, nullable=True)

    # Mốc thời gian được kích hoạt: 15m, 60m, 1440m, overdue, v.v.
    milestone = Column(String(50), nullable=True)
    metadata_json = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="notifications")
    task = relationship("Task", foreign_keys=[task_id], back_populates="notifications")

    def __init__(self, **kwargs):
        # Đồng bộ message và description nếu 1 trong 2 được cung cấp
        if "message" in kwargs and not kwargs.get("description"):
            kwargs["description"] = kwargs["message"]
        elif "description" in kwargs and not kwargs.get("message"):
            kwargs["message"] = kwargs["description"]
        super().__init__(**kwargs)
