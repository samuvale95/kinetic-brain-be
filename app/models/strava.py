from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON, Float, Boolean, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class StravaAccount(Base):
    __tablename__ = "strava_accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    strava_id = Column(BigInteger, unique=True, nullable=False)  # Strava athlete ID
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=False)
    token_expires_at = Column(DateTime, nullable=False)
    firstname = Column(String(100))
    lastname = Column(String(100))
    profile_medium = Column(String(500))  # Profile picture URL
    profile = Column(String(500))  # Profile picture URL
    city = Column(String(100))
    state = Column(String(100))
    country = Column(String(100))
    sex = Column(String(10))
    premium = Column(Boolean, default=False)
    summit = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    # user = relationship("User", back_populates="strava_account")  # Temporarily disabled
    activities = relationship("StravaActivity", back_populates="strava_account")


class StravaActivity(Base):
    __tablename__ = "strava_activities"
    
    id = Column(Integer, primary_key=True, index=True)
    strava_account_id = Column(Integer, ForeignKey("strava_accounts.id"), nullable=True)  # Nullable to preserve activities when account is disconnected
    strava_activity_id = Column(BigInteger, unique=True, nullable=False)  # Strava activity ID
    workout_id = Column(Integer, ForeignKey("workouts.id"), nullable=True)  # Matched workout
    
    # Basic activity info
    name = Column(String(200), nullable=False)
    type = Column(String(50), nullable=False)  # Run, Ride, Swim, etc.
    sport_type = Column(String(50))  # More specific sport type
    
    # Dates and times
    start_date = Column(DateTime, nullable=False)
    start_date_local = Column(DateTime, nullable=False)
    timezone = Column(String(100))
    
    # Distance and duration
    distance = Column(Float)  # meters
    moving_time = Column(Integer)  # seconds
    elapsed_time = Column(Integer)  # seconds
    
    # Elevation and pace
    total_elevation_gain = Column(Float)  # meters
    average_speed = Column(Float)  # meters per second
    max_speed = Column(Float)  # meters per second
    
    # Heart rate data
    average_heartrate = Column(Float)  # bpm
    max_heartrate = Column(Float)  # bpm
    
    # Power data (for cycling)
    average_watts = Column(Float)
    max_watts = Column(Float)
    weighted_average_watts = Column(Float)
    
    # Cadence
    average_cadence = Column(Float)  # rpm
    
    # Temperature and weather
    temperature = Column(Float)  # celsius
    feels_like = Column(Float)  # celsius
    
    # Additional data
    calories = Column(Float)
    kilojoules = Column(Float)
    
    # Detailed data (JSON)
    splits_metric = Column(JSON)  # Split times
    splits_standard = Column(JSON)  # Standard splits
    best_efforts = Column(JSON)  # Best efforts (1k, 5k, etc.)
    segment_efforts = Column(JSON)  # Segment efforts
    
    # Status
    is_synced = Column(Boolean, default=False)  # Synced with workout plan
    sync_status = Column(String(50), default="pending")  # pending, matched, manual, ignored
    
    # Calculated metrics (denormalized for quick access)
    tss = Column(Float)  # Training Stress Score
    normalized_power = Column(Float)
    intensity_factor = Column(Float)
    trimp = Column(Float)  # Training Impulse
    time_in_zone_1 = Column(Integer, default=0)
    time_in_zone_2 = Column(Integer, default=0)
    time_in_zone_3 = Column(Integer, default=0)
    time_in_zone_4 = Column(Integer, default=0)
    time_in_zone_5 = Column(Integer, default=0)
    metrics_calculated = Column(Boolean, default=False)
    zone_distribution = Column(JSON)  # JSON with zone distribution
    
    # Raw Strava data
    raw_data = Column(JSON)  # Complete Strava response
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    strava_account = relationship("StravaAccount", back_populates="activities")
    workout = relationship("Workout", back_populates="strava_activity")
    training_metrics = relationship("TrainingMetrics", back_populates="strava_activity", uselist=False)


class StravaWebhook(Base):
    __tablename__ = "strava_webhooks"
    
    id = Column(Integer, primary_key=True, index=True)
    object_type = Column(String(50), nullable=False)  # activity, athlete
    object_id = Column(BigInteger, nullable=False)  # activity_id or athlete_id
    aspect_type = Column(String(50), nullable=False)  # create, update, delete
    event_time = Column(BigInteger, nullable=False)  # Unix timestamp
    owner_id = Column(BigInteger, nullable=False)  # Strava athlete ID
    subscription_id = Column(Integer, nullable=False)
    
    # Processing status
    is_processed = Column(Boolean, default=False)
    processing_error = Column(Text)
    
    # Raw webhook data
    raw_data = Column(JSON)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True))
