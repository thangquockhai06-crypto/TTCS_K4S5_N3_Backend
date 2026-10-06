import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Text, Numeric, DateTime, Integer
from app.database import Base


class WinLossReason(Base):
    """
    Model lý do Thắng / Thua cơ hội (S2-10 / SCRUM-89):
    - result_type: 'WON' hoặc 'LOST'
    - code: Mã định danh duy nhất (PRICE_COMPETITIVE, BUDGET_CUT,...)
    - reason: Tiêu đề nguyên nhân chi tiết
    - description: Ghi chú giải thích / hướng dẫn phân loại
    - is_active: Trạng thái kích hoạt
    - usage_count: Số lần lý do được sử dụng trong các cơ hội bán hàng
    """
    __tablename__ = "win_loss_reasons"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    result_type = Column(String(10), nullable=False, index=True)  # 'WON' | 'LOST'
    code = Column(String(50), nullable=False, unique=True, index=True)
    reason = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    usage_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Competitor(Base):
    """
    Model đối thủ cạnh tranh (S2-10 / SCRUM-89):
    - Tên, Website, Phân khúc giá, Điểm mạnh, Điểm yếu, Tỷ lệ thắng đối đầu, Trạng thái kích hoạt
    """
    __tablename__ = "competitors"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(150), nullable=False, unique=True, index=True)
    website = Column(String(255), nullable=True)
    pricing_tier = Column(String(100), nullable=True, default="Trung cấp")
    strengths = Column(Text, nullable=True)
    weaknesses = Column(Text, nullable=True)
    win_rate = Column(Numeric(5, 2), default=50.00, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
