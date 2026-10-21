import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Text, DateTime
from app.database import Base


class CustomField(Base):
    """
    Model định nghĩa trường dữ liệu tùy chỉnh động (S2-08):
    - entity_type: 'customer' | 'deal'
    - field_type: 'text' | 'number' | 'date' | 'select'
    - options: Danh sách giá trị phân cách bằng dấu phẩy cho kiểu 'select'
    """
    __tablename__ = "custom_fields"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    entity_type = Column(String(50), default="customer", nullable=False, index=True)
    field_name = Column(String(100), nullable=False)
    field_label = Column(String(150), nullable=False)
    field_type = Column(String(50), default="text", nullable=False)
    options = Column(Text, nullable=True)
    is_required = Column(Boolean, default=False, nullable=False)
    default_value = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class CustomFieldValue(Base):
    """
    Lưu trữ giá trị nhập của các trường tùy chỉnh theo entity_type và entity_id
    """
    __tablename__ = "custom_field_values"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    entity_type = Column(String(50), nullable=False, index=True)
    entity_id = Column(String(36), default="sample", nullable=False, index=True)
    field_name = Column(String(100), nullable=False)
    value = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
