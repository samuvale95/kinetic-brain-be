from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON, Float, Date, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class WorkoutStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class WorkoutPlan(Base):
    __tablename__ = "workout_plans"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    total_weeks = Column(Integer, nullable=False)
    goal = Column(String(200))
    sport_type = Column(String(50))
    level = Column(String(20))  # beginner, intermediate, advanced
    status = Column(String(20), default="active")  # active, completed, paused
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="workout_plans")
    workouts = relationship("Workout", back_populates="plan")
    versions = relationship("PlanVersion", back_populates="plan")


class Workout(Base):
    __tablename__ = "workouts"
    
    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("workout_plans.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    type = Column(String(50), nullable=False)  # endurance, interval, strength, etc.
    day_number = Column(Integer)  # Day within the plan
    scheduled_date = Column(Date)
    duration_minutes = Column(Integer, nullable=False)
    intensity = Column(String(20))  # easy, moderate, hard
    zone = Column(String(10))  # Z1, Z2, Z3, Z4, Z5
    structure_json = Column(JSON)  # warmup/main/cooldown structure
    status = Column(Enum(WorkoutStatus), default=WorkoutStatus.SCHEDULED)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    plan = relationship("WorkoutPlan", back_populates="workouts")
    user = relationship("User", back_populates="workouts")
    sessions = relationship("WorkoutSession", back_populates="workout")
    strava_activity = relationship("StravaActivity", back_populates="workout", uselist=False)


class WorkoutSession(Base):
    __tablename__ = "workout_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    workout_id = Column(Integer, ForeignKey("workouts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    actual_date = Column(DateTime(timezone=True), nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    avg_hr = Column(Float)  # Average heart rate
    max_hr = Column(Float)  # Maximum heart rate
    avg_pace = Column(Float)  # Average pace in min/km
    avg_power = Column(Float)  # Average power in watts
    perceived_exertion = Column(Integer)  # RPE scale 1-10
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    workout = relationship("Workout", back_populates="sessions")
    user = relationship("User", back_populates="workout_sessions")
    training_metrics = relationship("TrainingMetrics", back_populates="workout_session", uselist=False)
