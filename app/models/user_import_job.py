import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text
from app.database import Base

class UserImportJob(Base):
    __tablename__ = "user_import_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String(255), nullable=False)
    file_type = Column(String(20), nullable=False, default="xlsx")
    file_size = Column(Integer, default=0)
    batch_size = Column(Integer, default=500)

    total_rows = Column(Integer, default=0)
    processed_rows = Column(Integer, default=0)
    successful_rows = Column(Integer, default=0)
    failed_rows = Column(Integer, default=0)
    duplicate_rows = Column(Integer, default=0)

    # Trạng thái: pending, processing, completed, failed
    status = Column(String(30), nullable=False, default="pending", index=True)
    
    # Chi tiết danh sách lỗi (JSON string) để xuất báo cáo CSV
    error_summary = Column(Text, nullable=True)

    created_by_user_id = Column(String(36), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
