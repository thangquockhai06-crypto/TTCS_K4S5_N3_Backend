import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base


class DealMember(Base):
    """
    Model quản lý thành viên cùng tham gia cơ hội bán hàng (Deal Members / Collaborators).
    Thuộc SCRUM-207 / Sprint 5 (EP-05: Cơ hội bán hàng & Pipeline Kanban).
    """
    __tablename__ = "deal_members"
    __table_args__ = (
        UniqueConstraint("deal_id", "user_id", name="uq_deal_member"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    deal_id = Column(String(36), ForeignKey("deals.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role_in_deal = Column(String(50), default="COLLABORATOR", nullable=False)
    added_by = Column(String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    deal = relationship("Deal", back_populates="members")
    user = relationship("User", foreign_keys=[user_id], lazy="joined")
    added_by_user = relationship("User", foreign_keys=[added_by], lazy="joined")
