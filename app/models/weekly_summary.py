from sqlalchemy import Column, Integer, Float, ForeignKey, JSON, DateTime, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class WeeklyPerformanceSummary(Base):
    __tablename__ = "weekly_performance_summary"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    week_start_date = Column(Date, nullable=False)
    week_end_date = Column(Date, nullable=False)
    
    # Training metrics
    weekly_tss = Column(Float, default=0)
    weekly_trimp = Column(Float, default=0)
    volume_hours = Column(Float, default=0)
    volume_kilometers = Column(Float, default=0)
    
    # Performance metrics (CTL/ATL/TSB)
    ctl = Column(Float)  # Chronic Training Load (fitness)
    atl = Column(Float)  # Acute Training Load (fatigue)
    tsb = Column(Float)  # Training Stress Balance (form)
    
    # Workout statistics
    workouts_completed = Column(Integer, default=0)
    workouts_planned = Column(Integer, default=0)
    completion_rate = Column(Float)
    avg_rpe = Column(Float)
    
    # Zone distribution
    zone_distribution = Column(JSON)
    
    # Additional metrics
    avg_hr = Column(Float)
    max_hr = Column(Float)
    avg_pace = Column(Float)
    total_elevation_gain = Column(Float)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="weekly_summaries")

