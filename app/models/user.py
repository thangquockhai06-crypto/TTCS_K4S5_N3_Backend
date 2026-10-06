import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(150), nullable=False)
    role = Column(String(50), nullable=False, default="Super Admin")
    title = Column(String(150), default="Quản trị viên hệ thống")
    department = Column(String(150), default="Ban Quản Trị & Vận Hành Doanh Thu")
    avatar_url = Column(Text, nullable=True)
    avatar_thumbnail_url = Column(Text, nullable=True)
    workspace_name = Column(String(150), default="NexusCRM Enterprise VN")

    # Brute-force protection fields (SCRUM-32 / SCRUM-101)
    failed_attempts = Column(Integer, default=0, nullable=False)
    lockout_until = Column(DateTime, nullable=True)

    # Data Scope & Team Management
    team_id = Column(String(50), nullable=True, index=True)
    data_scope = Column(String(20), nullable=True)
    status = Column(String(50), nullable=False, default="active", index=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    customers = relationship("Customer", back_populates="assigned_user")
    deals = relationship("Deal", back_populates="owner")
    roles = relationship("Role", secondary="user_roles", back_populates="users")
    teams = relationship("Team", secondary="user_teams", back_populates="users")
