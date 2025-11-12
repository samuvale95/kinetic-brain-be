from sqlalchemy import Column, Integer, Float, ForeignKey, JSON, DateTime, Boolean, Date, UniqueConstraint, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class TrainingMetrics(Base):
    __tablename__ = "training_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    strava_activity_id = Column(Integer, ForeignKey("strava_activities.id", ondelete="CASCADE"), nullable=True)
    workout_session_id = Column(Integer, ForeignKey("workout_sessions.id", ondelete="CASCADE"), nullable=True)
    
    # Training Stress Score
    tss = Column(Float)
    normalized_power = Column(Float)
    intensity_factor = Column(Float)
    trimp = Column(Float)  # Training Impulse
    
    # Time in zones (minutes)
    time_in_zone_1 = Column(Integer, default=0)
    time_in_zone_2 = Column(Integer, default=0)
    time_in_zone_3 = Column(Integer, default=0)
    time_in_zone_4 = Column(Integer, default=0)
    time_in_zone_5 = Column(Integer, default=0)
    
    # Store zone distribution as JSON for flexibility
    zone_distribution = Column(JSON)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    strava_activity = relationship("StravaActivity", back_populates="training_metrics")
    workout_session = relationship("WorkoutSession", back_populates="training_metrics")


class WeeklyTrainingSummary(Base):
    __tablename__ = "weekly_training_summaries"
    __table_args__ = (
        UniqueConstraint("user_id", "week_start", name="uq_weekly_training_summary_user_week"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    week_start = Column(Date, nullable=False)
    week_end = Column(Date, nullable=False)

    total_duration_minutes = Column(Float)
    total_distance_km = Column(Float)
    total_tss = Column(Float)
    multi_sport_load = Column(Float)

    sport_breakdown = Column(JSON)  # {"run": {...}, "bike": {...}}
    zone_distribution = Column(JSON)  # {"z1": 0.7, "z4": 0.1, ...}

    high_intensity_ratio = Column(Float)
    high_intensity_sessions = Column(Integer)

    longest_workout_duration_minutes = Column(Float)
    longest_workout_distance_km = Column(Float)
    long_workout_progression_pct = Column(Float)

    readiness_score = Column(Float)
    injury_risk_score = Column(Float)
    compliance_score = Column(Float)
    hydration_score = Column(Float)

    plan_adherence_details = Column(JSON)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    notes = Column(Text)

    user = relationship("User", back_populates="weekly_training_summaries")

