import uuid
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base


class SavedFilter(Base):
    __tablename__ = "saved_filters"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_saved_filter_user_name"),)

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    filter_definition = Column(JSON, nullable=False)
    is_default = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User")
