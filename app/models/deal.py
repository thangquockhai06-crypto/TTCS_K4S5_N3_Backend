import uuid
from datetime import datetime
from sqlalchemy import Column, String, Numeric, Integer, Date, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Deal(Base):
    __tablename__ = "deals"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    value = Column(Numeric(15, 2), default=0.00, nullable=False)
    stage = Column(
        Enum("lead", "contact", "proposal", "negotiation", "won", "lost", name="deal_stage_enum"),
        default="lead",
        nullable=False,
    )
    probability = Column(Integer, default=20, nullable=False)
    customer_id = Column(String(36), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    owner_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expected_close_date = Column(Date, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    customer = relationship("Customer", back_populates="deals")
    owner = relationship("User", back_populates="deals")
