import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime
from app.database import Base


class Category(Base):
    """
    Model danh mục dùng chung (S2-07):
    - type: 'lead_source' (Nguồn khách hàng/cơ hội) hoặc 'industry' (Ngành nghề).
    - order_index: Thứ tự hiển thị kéo thả.
    - usage_count: Số lượng bản ghi khách hàng/cơ hội đang tham chiếu (ngăn chặn xóa khi > 0).
    """
    __tablename__ = "categories"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    type = Column(String(50), nullable=False, index=True)
    code = Column(String(50), nullable=False)
    name = Column(String(150), nullable=False)
    order_index = Column(Integer, default=0, nullable=False)
    is_system = Column(Boolean, default=False, nullable=False)
    usage_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
