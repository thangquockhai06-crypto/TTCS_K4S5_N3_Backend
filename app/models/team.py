import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from app.database import Base

user_teams = Table(
    "user_teams",
    Base.metadata,
    Column("user_id", String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("team_id", String(36), ForeignKey("teams.id", ondelete="CASCADE"), primary_key=True),
    Column("created_at", DateTime, default=datetime.utcnow),
)


class Team(Base):
    __tablename__ = "teams"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(String(255), nullable=True)
    parent_id = Column(String(36), ForeignKey("teams.id", ondelete="SET NULL"), nullable=True)
    leader_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    leader_name = Column(String(150), nullable=True)
    region = Column(String(100), default="Toàn quốc", nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    users = relationship("User", secondary=user_teams, back_populates="teams")
    sub_teams = relationship("Team", backref="parent_team", remote_side=[id])
