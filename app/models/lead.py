import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Numeric, Boolean, DateTime, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.database import Base


class Lead(Base):
    """
    Model Quản lý Đầu mối bán hàng (Lead Management - EP-04: S4-01 -> S4-09).
    Hỗ trợ luồng:
    UNASSIGNED -> ASSIGNED -> CONTACTED -> QUALIFIED / REJECTED / CONVERTED.
    """
    __tablename__ = "leads"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    full_name = Column(String(150), nullable=False, index=True)
    first_name = Column(String(75), nullable=True)
    last_name = Column(String(75), nullable=True)
    email = Column(String(120), nullable=False, index=True)
    phone = Column(String(30), nullable=True, index=True)
    company = Column(String(150), nullable=True, index=True)
    job_title = Column(String(100), nullable=True)

    source = Column(String(50), default="Web Form", nullable=False, index=True)
    campaign_id = Column(String(36), ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True, index=True)

    region = Column(String(50), default="Miền Bắc", nullable=True, index=True)
    industry = Column(String(100), default="Công nghệ", nullable=True, index=True)
    company_size = Column(String(50), default="11-50", nullable=True)
    annual_budget = Column(Numeric(15, 2), default=0.00, nullable=True)

    score = Column(Integer, default=50, nullable=False, index=True)
    score_grade = Column(String(20), default="Warm", nullable=False, index=True)  # Hot (>=70), Warm (40-69), Cold (<40)

    # Trạng thái vòng đời Lead (S4-07)
    status = Column(
        String(30),
        default="UNASSIGNED",
        nullable=False,
        index=True,
    )  # UNASSIGNED, ASSIGNED, CONTACTED, QUALIFIED, UNQUALIFIED, REJECTED, CONVERTED

    assigned_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    assigned_at = Column(DateTime, nullable=True)
    rejection_reason = Column(String(255), nullable=True)

    # SLA Tracking (S4-07)
    sla_deadline = Column(DateTime, nullable=True, index=True)
    sla_overdue = Column(Boolean, default=False, nullable=False, index=True)
    sla_responded_at = Column(DateTime, nullable=True)

    # Lead Conversion Tracking (S4-08)
    converted_customer_id = Column(String(36), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    converted_contact_id = Column(String(36), ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True)
    converted_deal_id = Column(String(36), ForeignKey("deals.id", ondelete="SET NULL"), nullable=True)
    converted_at = Column(DateTime, nullable=True)

    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    campaign = relationship("Campaign", back_populates="leads")
    assigned_user = relationship("User", foreign_keys=[assigned_user_id])
    converted_customer = relationship("Customer", foreign_keys=[converted_customer_id])


class LeadRoutingRule(Base):
    """
    Quy tắc tự động phân bổ Lead (S4-06):
    Thứ tự ưu tiên: 1. Region, 2. Industry, 3. Round-Robin.
    """
    __tablename__ = "lead_routing_rules"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    priority = Column(Integer, default=1, nullable=False)  # 1: Cao nhất (Region), 2: Industry, 3: Round-Robin
    rule_type = Column(String(30), default="REGION", nullable=False)  # REGION, INDUSTRY, ROUND_ROBIN
    criterion_value = Column(String(100), nullable=True)  # ví dụ: "Miền Bắc", "Công nghệ"
    target_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    target_team_id = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
