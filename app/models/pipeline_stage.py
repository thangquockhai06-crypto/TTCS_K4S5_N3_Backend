import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, Text, DateTime
from app.database import Base


class PipelineStage(Base):
    """
    Model cấu hình phễu bán hàng (S2-09):
    - order_index: Thứ tự kéo thả.
    - probability: Tỷ lệ thành công (0 đến 100).
    - exit_rules: Cấu hình điều kiện chuyển giai đoạn dạng JSON string.
    - Không làm hỏng các Deal đang hoạt động khi cấu hình pipeline thay đổi.
    """
    __tablename__ = "pipeline_stages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    stage_key = Column(String(50), nullable=False, unique=True, index=True)
    order_index = Column(Integer, default=0, nullable=False)
    probability = Column(Integer, default=20, nullable=False)
    exit_rules = Column(Text, nullable=True)  # JSON text
    color = Column(String(20), default="#2563eb", nullable=False)
    is_won = Column(Boolean, default=False, nullable=False)
    is_lost = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
