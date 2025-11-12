from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, JSON, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=True)  # Nullable for OAuth users
    name = Column(String, nullable=False)
    avatar_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    last_login = Column(DateTime(timezone=True))
    auth_provider = Column(String, default="email")  # email, google, etc.
    
    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False)
    performance_metrics = relationship("PerformanceMetrics", back_populates="user")
    workout_plans = relationship("WorkoutPlan", back_populates="user")
    workouts = relationship("Workout", back_populates="user")
    workout_sessions = relationship("WorkoutSession", back_populates="user")
    calendar_events = relationship("CalendarEvent", back_populates="user")
    daily_metrics = relationship("DailyPerformanceMetrics", back_populates="user")
    daily_readiness_metrics = relationship("DailyReadinessMetrics", back_populates="user")
    weekly_training_summaries = relationship("WeeklyTrainingSummary", back_populates="user")
    # strava_account = relationship("StravaAccount", back_populates="user", uselist=False)  # Temporarily disabled


class UserProfile(Base):
    __tablename__ = "user_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    age = Column(Integer)
    gender = Column(String(10))  # male, female, other
    weight = Column(Float)  # kg
    height = Column(Float)  # cm
    sports = Column(JSON)  # List of sports
    experience_years = Column(Integer)
    weekly_hours = Column(Float)
    main_goal = Column(String(100))
    physical_notes = Column(Text)
    city = Column(String(100))  # City for weather
    latitude = Column(Float)  # Latitude for weather
    longitude = Column(Float)  # Longitude for weather
    preferred_zone_type = Column(String(10), default="hr")  # hr, pace, power
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="profile")


class PerformanceMetrics(Base):
    __tablename__ = "performance_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # HR Metrics
    hr_max = Column(Float)
    hr_rest = Column(Float)
    threshold_hr = Column(Float)
    hrr = Column(Float)  # Heart Rate Reserve
    custom_threshold_hr = Column(Float)
    
    # Pace Metrics
    threshold_pace = Column(String(10))  # Format: "mm:ss" or "mm.ss"
    critical_speed = Column(Float)
    vla = Column(Float)
    
    # Power Metrics
    ftp = Column(Float)  # Functional Threshold Power
    wkg = Column(Float)  # Watts per kilogram
    
    # Advanced Metrics
    vo2max = Column(Float)
    
    # Structured Zones (new format)
    hr_zones = Column(JSON)  # {"z1": "120-135", "z2": "135-150", ...}
    hr_zones_source = Column(String(10))  # "auto" | "manual"
    hr_threshold_used = Column(Float)
    
    pace_zones = Column(JSON)  # {"z1": "5:00-4:45", "z2": "4:45-4:30", ...}
    pace_zones_source = Column(String(10))  # "auto" | "manual"
    threshold_pace_used = Column(String(10))
    
    power_zones = Column(JSON)  # {"z1": "0-165", "z2": "166-225", ..., "z7": "451-540"}
    power_zones_source = Column(String(10))  # "auto" | "manual"
    ftp_used = Column(Float)
    
    test_date = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="performance_metrics")


class OAuthAccount(Base):
    __tablename__ = "oauth_accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    provider = Column(String, nullable=False)  # google, facebook, etc.
    provider_account_id = Column(String, nullable=False)
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User")
    
    # Unique constraint on provider + provider_account_id
    __table_args__ = (
        {"extend_existing": True}
    )
