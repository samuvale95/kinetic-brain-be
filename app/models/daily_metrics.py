from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime, Date, String, Text
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


class DailyReadinessMetrics(Base):
    __tablename__ = "daily_readiness_metrics"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    metric_date = Column(Date, nullable=False)

    hrv_baseline = Column(Float)
    hrv_value = Column(Float)
    hrv_delta = Column(Float)

    rhr_baseline = Column(Float)
    rhr_value = Column(Float)
    rhr_delta = Column(Float)

    sleep_hours = Column(Float)
    sleep_quality_score = Column(Float)
    epoc = Column(Float)

    recovery_index = Column(Float)
    readiness_state = Column(String(32))

    hydration_status = Column(String(32))
    hydration_score = Column(Float)
    nutrition_score = Column(Float)
    weight_delta_kg = Column(Float)

    notes = Column(Text)
    
    # Source tracking
    source = Column(String(20), default='manual', nullable=False, index=True)
    # Values: 'manual', 'healthkit'
    
    # HealthKit sync fields
    healthkit_sync_date = Column(DateTime(timezone=True), nullable=True)
    healthkit_sync_anchor = Column(String(255), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="daily_readiness_metrics")

