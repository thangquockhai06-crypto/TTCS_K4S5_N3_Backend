import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database import Base


class DealHistory(Base):
    """
    Model ghi nhận lịch sử thay đổi của Cơ hội bán hàng (Deal History / Audit Log).
    Thuộc SCRUM-91 / Sprint 5 (EP-05: Cơ hội bán hàng & Pipeline Kanban).
    Tính bất biến (Audit Immutability): chỉ hỗ trợ INSERT và SELECT, không hỗ trợ UPDATE/DELETE.
    """
    __tablename__ = "deal_histories"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    deal_id = Column(String(36), ForeignKey("deals.id", ondelete="CASCADE"), nullable=False, index=True)
    field_name = Column(String(50), nullable=False, index=True)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    changed_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    changed_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    deal = relationship("Deal", back_populates="deal_histories")
    user = relationship("User", foreign_keys=[changed_by], lazy="joined")
