from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, JSON, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    last_login = Column(DateTime(timezone=True))
    
    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False)
    performance_metrics = relationship("PerformanceMetrics", back_populates="user")
    workout_plans = relationship("WorkoutPlan", back_populates="user")
    workouts = relationship("Workout", back_populates="user")
    workout_sessions = relationship("WorkoutSession", back_populates="user")
    calendar_events = relationship("CalendarEvent", back_populates="user")


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
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="profile")


class PerformanceMetrics(Base):
    __tablename__ = "performance_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    metric_type = Column(String(20), nullable=False)  # hr, pace, power
    threshold_value = Column(Float, nullable=False)
    max_value = Column(Float)
    rest_value = Column(Float)
    zones_json = Column(JSON)  # Z1-Z5 zones with min/max values
    test_date = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="performance_metrics")
