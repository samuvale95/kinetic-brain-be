from sqlalchemy import Column, Integer, Float, ForeignKey, JSON, DateTime, Boolean
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

