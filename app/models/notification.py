import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Notification(Base):
    """
    S7-08: Hệ thống Thông báo In-App Bất đồng bộ.
    Hỗ trợ các sự kiện: phân bổ lead, báo giá chờ duyệt, khách hàng phản hồi báo giá,
    giao việc/nhiệm vụ mới, cơ hội bán hàng bị ứ đọng (stalled), hợp đồng sắp hết hạn.
    """
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(50), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    target_type = Column(String(50), nullable=True)  # lead, deal, quotation, task, contract
    target_id = Column(String(36), nullable=True)
    link_url = Column(String(255), nullable=True)
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    user = relationship("User", foreign_keys=[user_id])
