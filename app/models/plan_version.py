from sqlalchemy import Column, Integer, ForeignKey, DateTime, JSON, String, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class PlanVersion(Base):
    __tablename__ = "plan_versions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    plan_id = Column(Integer, ForeignKey("workout_plans.id", ondelete="CASCADE"), nullable=True)

    version_label = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)

    duration_weeks = Column(Integer, nullable=False)
    sport_type = Column(String(50), nullable=True)
    level = Column(String(20), nullable=True)

    plan_payload = Column(JSON, nullable=False)
    validator_violations = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="plan_versions")
    plan = relationship("WorkoutPlan", back_populates="versions")
