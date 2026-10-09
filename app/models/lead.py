import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Lead(Base):
    """
    Model lưu trữ Khách hàng tiềm năng (Lead) thu thập từ các kênh (SCRUM-24 / EP-04).
    Tự động ghi nhận nguồn và trạng thái 'NEW' khi gửi từ biểu mẫu web.
    """
    __tablename__ = "leads"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    full_name = Column(String(150), nullable=False)
    email = Column(String(150), nullable=False, index=True)
    phone = Column(String(20), nullable=False)
    company = Column(String(255), nullable=True)
    interest_need = Column(Text, nullable=True)
    source = Column(String(100), nullable=False, default="Website Form")
    status = Column(String(50), nullable=False, default="NEW", index=True)
    form_id = Column(String(36), ForeignKey("web_forms.id", ondelete="SET NULL"), nullable=True, index=True)
    client_ip = Column(String(45), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    form = relationship("WebForm", back_populates="leads")
