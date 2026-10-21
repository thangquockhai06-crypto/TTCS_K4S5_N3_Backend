import uuid
from datetime import datetime
from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship
from app.database import Base


class DealAttachment(Base):
    """
    Model quản lý tài liệu đính kèm trong Cơ hội bán hàng (Deal Attachments).
    Thuộc SCRUM-208 (Subtask của SCRUM-91 / Sprint 5: EP-05).
    """
    __tablename__ = "deal_attachments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    deal_id = Column(String(36), ForeignKey("deals.id", ondelete="CASCADE"), nullable=False, index=True)
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False, unique=True)
    file_path = Column(String(500), nullable=False)
    content_type = Column(String(150), nullable=True)
    file_size = Column(BigInteger, nullable=False)
    uploaded_by = Column(String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    deal = relationship("Deal", back_populates="attachments")
    uploader = relationship("User", foreign_keys=[uploaded_by], lazy="joined")
