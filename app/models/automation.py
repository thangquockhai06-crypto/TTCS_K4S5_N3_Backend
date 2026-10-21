import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class AutomationRule(Base):
    """
    S7-09: Động cơ Quy tắc Tự động hóa IF–THEN (Automation Rules Engine).
    Kích hoạt theo thay đổi trạng thái (status change) hoặc điều kiện thời gian (time condition).
    Hành động hỗ trợ: tạo nhiệm vụ (create_task), gửi thông báo (send_notification), chuyển người phụ trách (change_owner).
    """
    __tablename__ = "automation_rules"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Trigger
    trigger_entity = Column(String(50), nullable=False, index=True)  # deal, lead, quotation, contract
    trigger_event = Column(String(50), nullable=False)  # status_changed, time_condition, created
    conditions = Column(Text, nullable=True)  # JSON String: {"field": "status", "operator": "equals", "value": "won"}

    # Action
    action_type = Column(String(50), nullable=False)  # create_task, send_notification, change_owner
    action_config = Column(Text, nullable=False)  # JSON String: {"task_title": "...", "due_days": 2, ...}

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    logs = relationship("AutomationLog", back_populates="rule", cascade="all, delete-orphan", order_by="AutomationLog.executed_at.desc()")


class AutomationLog(Base):
    """
    S7-09: Nhật ký Thực thi Quy tắc Tự động hóa (Automation Execution Logs).
    Ghi nhận chi tiết kết quả xử lý của từng rule: thời gian, đối tượng, kết quả thành công/thất bại.
    """
    __tablename__ = "automation_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    rule_id = Column(String(36), ForeignKey("automation_rules.id", ondelete="SET NULL"), nullable=True, index=True)
    rule_name = Column(String(255), nullable=False)
    trigger_event = Column(String(100), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(36), nullable=False)
    action_type = Column(String(50), nullable=False)
    status = Column(String(50), default="success", nullable=False)  # success | failed | skipped
    details = Column(Text, nullable=True)
    executed_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    rule = relationship("AutomationRule", back_populates="logs")
