from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class DailyPerformanceMetrics(Base):
    __tablename__ = "daily_performance_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    metric_date = Column(Date, nullable=False)
    
    # Daily TSS (sum of all activities for this day)
    daily_tss = Column(Float, default=0)
    
    # Calculated metrics (incremental EMA)
    ctl = Column(Float)  # Chronic Training Load (fitness)
    atl = Column(Float)  # Acute Training Load (fatigue)
    tsb = Column(Float)  # Training Stress Balance (form)
    
    # Previous day values (for incremental calculation)
    prev_ctl = Column(Float)
    prev_atl = Column(Float)
    
    # Metadata
    activities_count = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="daily_metrics")

