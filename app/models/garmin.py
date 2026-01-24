from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, JSON, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from datetime import datetime, timezone


class GarminAccount(Base):
    """Model for Garmin Connect account integration"""
    __tablename__ = "garmin_accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    
    # OAuth tokens (Garmin uses OAuth 1.0a)
    oauth_token = Column(String(500), nullable=True)
    oauth_token_secret = Column(String(500), nullable=True)
    access_token = Column(String(500), nullable=True)  # For OAuth 2.0 if available
    refresh_token = Column(String(500), nullable=True)
    
    # Account info
    garmin_user_id = Column(String(100), nullable=True)
    email = Column(String(255), nullable=True)
    display_name = Column(String(255), nullable=True)
    
    # Sync settings
    auto_sync_enabled = Column(Boolean, default=True, nullable=False)
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    sync_anchor = Column(String(255), nullable=True)  # For incremental sync
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    connected_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    disconnected_at = Column(DateTime(timezone=True), nullable=True)
    
    # Error tracking
    last_error = Column(Text, nullable=True)
    error_count = Column(Integer, default=0, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="garmin_account")


class GarminActivity(Base):
    """Model for synced Garmin activities"""
    __tablename__ = "garmin_activities"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    garmin_account_id = Column(Integer, ForeignKey("garmin_accounts.id"), nullable=False)
    
    # Garmin activity data
    garmin_activity_id = Column(String(100), nullable=False, unique=True, index=True)
    activity_type = Column(String(50), nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    duration_seconds = Column(Integer, nullable=False)
    distance_meters = Column(Float, nullable=True)
    calories = Column(Integer, nullable=True)
    
    # Metrics
    avg_hr = Column(Integer, nullable=True)
    max_hr = Column(Integer, nullable=True)
    avg_power = Column(Integer, nullable=True)
    max_power = Column(Integer, nullable=True)
    avg_speed = Column(Float, nullable=True)
    max_speed = Column(Float, nullable=True)
    elevation_gain = Column(Float, nullable=True)
    
    # Raw data
    raw_data = Column(JSON, nullable=True)  # Full Garmin activity JSON
    
    # Matching
    matched_workout_id = Column(Integer, ForeignKey("workouts.id"), nullable=True)
    matched_session_id = Column(Integer, ForeignKey("workout_sessions.id"), nullable=True)
    match_status = Column(String(50), default="unmatched")  # unmatched, matched, manual, ignored
    
    synced_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    # Relationships
    user = relationship("User")
    garmin_account = relationship("GarminAccount")
    matched_workout = relationship("Workout", foreign_keys=[matched_workout_id])
    matched_session = relationship("WorkoutSession", foreign_keys=[matched_session_id])
