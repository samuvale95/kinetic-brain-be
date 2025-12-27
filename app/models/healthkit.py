from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class HealthKitWorkout(Base):
    __tablename__ = "healthkit_workouts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    workout_id = Column(Integer, ForeignKey("workouts.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # HealthKit Identifiers
    hk_workout_uuid = Column(String(36), unique=True, nullable=False, index=True)
    hk_source_name = Column(String(255), nullable=True)
    
    # Workout Basic Info
    workout_type = Column(String(50), nullable=False, index=True)
    start_date = Column(DateTime(timezone=True), nullable=False, index=True)
    end_date = Column(DateTime(timezone=True), nullable=False)
    duration_seconds = Column(Integer, nullable=False)
    
    # Distance and Energy
    total_distance_meters = Column(Float, nullable=True)
    total_energy_burned_kcal = Column(Float, nullable=True)
    total_basal_energy_kcal = Column(Float, nullable=True)
    
    # Elevation
    elevation_gain_meters = Column(Float, nullable=True)
    elevation_loss_meters = Column(Float, nullable=True)
    
    # Metadata (renamed from 'metadata' to avoid SQLAlchemy reserved word conflict)
    hk_metadata = Column(JSON, nullable=True)
    
    # Sync Status
    sync_status = Column(String(20), default='pending', nullable=False, index=True)
    # Values: 'pending', 'synced', 'matched', 'ignored'
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="healthkit_workouts")
    workout = relationship("Workout", back_populates="healthkit_workouts")

