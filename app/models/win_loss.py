import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Text, Numeric, DateTime
from app.database import Base


class WinLossReason(Base):
    """
    Model lý do Thắng / Thua cơ hội (S2-10):
    - result_type: 'WON' hoặc 'LOST'
    - reason: Tiêu đề lý do
    """
    __tablename__ = "win_loss_reasons"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    result_type = Column(String(10), nullable=False, index=True)  # 'WON' | 'LOST'
    code = Column(String(50), nullable=False)
    reason = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Competitor(Base):
    """
    Model đối thủ cạnh tranh (S2-10):
    - Tên, Website, Điểm mạnh, Điểm yếu, Tỷ lệ thắng đối đầu
    """
    __tablename__ = "competitors"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(150), nullable=False, unique=True, index=True)
    website = Column(String(255), nullable=True)
    strengths = Column(Text, nullable=True)
    weaknesses = Column(Text, nullable=True)
    win_rate = Column(Numeric(5, 2), default=50.00, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
