from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum


class WorkoutStatus(str, Enum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class WorkoutPlanCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    start_date: date
    end_date: date
    goal: Optional[str] = Field(None, max_length=200)
    sport_type: Optional[str] = Field(None, max_length=50)
    level: Optional[str] = Field(None, pattern="^(beginner|intermediate|advanced)$")


class WorkoutPlanUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    goal: Optional[str] = Field(None, max_length=200)
    sport_type: Optional[str] = Field(None, max_length=50)
    level: Optional[str] = Field(None, pattern="^(beginner|intermediate|advanced)$")
    status: Optional[str] = Field(None, pattern="^(active|completed|paused)$")


class WorkoutPlanResponse(BaseModel):
    id: int
    user_id: int
    title: str
    description: Optional[str] = None
    start_date: date
    end_date: date
    total_weeks: int
    goal: Optional[str] = None
    sport_type: Optional[str] = None
    level: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class WorkoutCreate(BaseModel):
    plan_id: Optional[int] = None
    title: str = Field(..., min_length=1, max_length=200)
    type: str = Field(..., min_length=1, max_length=50)
    day_number: Optional[int] = Field(None, ge=1)
    scheduled_date: Optional[date] = None
    duration_minutes: int = Field(..., gt=0, le=1440)  # Max 24 hours
    intensity: Optional[str] = Field(None, pattern="^(easy|moderate|hard)$")
    zone: Optional[str] = Field(None, pattern="^(Z1|Z2|Z3|Z4|Z5)$")
    structure_json: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


class WorkoutUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    type: Optional[str] = Field(None, min_length=1, max_length=50)
    day_number: Optional[int] = Field(None, ge=1)
    scheduled_date: Optional[date] = None
    duration_minutes: Optional[int] = Field(None, gt=0, le=1440)
    intensity: Optional[str] = Field(None, pattern="^(easy|moderate|hard)$")
    zone: Optional[str] = Field(None, pattern="^(Z1|Z2|Z3|Z4|Z5)$")
    structure_json: Optional[Dict[str, Any]] = None
    status: Optional[WorkoutStatus] = None
    notes: Optional[str] = None


class WorkoutResponse(BaseModel):
    id: int
    plan_id: Optional[int] = None
    user_id: int
    title: str
    type: str
    day_number: Optional[int] = None
    scheduled_date: Optional[date] = None
    duration_minutes: int
    intensity: Optional[str] = None
    zone: Optional[str] = None
    structure_json: Optional[Dict[str, Any]] = None
    status: WorkoutStatus
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class WorkoutSessionCreate(BaseModel):
    workout_id: int
    actual_date: datetime
    duration_minutes: int = Field(..., gt=0, le=1440)
    avg_hr: Optional[float] = Field(None, gt=0, le=300)
    max_hr: Optional[float] = Field(None, gt=0, le=300)
    avg_pace: Optional[float] = Field(None, gt=0)  # min/km
    avg_power: Optional[float] = Field(None, gt=0)  # watts
    perceived_exertion: Optional[int] = Field(None, ge=1, le=10)
    notes: Optional[str] = None


class WorkoutSessionResponse(BaseModel):
    id: int
    workout_id: int
    user_id: int
    actual_date: datetime
    duration_minutes: int
    avg_hr: Optional[float] = None
    max_hr: Optional[float] = None
    avg_pace: Optional[float] = None
    avg_power: Optional[float] = None
    perceived_exertion: Optional[int] = None
    notes: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class WorkoutStructure(BaseModel):
    warmup: Optional[Dict[str, Any]] = None
    main: Optional[Dict[str, Any]] = None
    cooldown: Optional[Dict[str, Any]] = None


class AIWorkoutPlanRequest(BaseModel):
    sport_type: str = Field(..., min_length=1, max_length=50)
    level: str = Field(..., pattern="^(beginner|intermediate|advanced)$")
    goal: str = Field(..., min_length=1, max_length=200)
    weekly_hours: float = Field(..., gt=0, le=168)
    user_profile: Optional[Dict[str, Any]] = None
    
    # Parametri per piani tradizionali
    duration_weeks: Optional[int] = Field(None, ge=1, le=52)
    
    # Parametri per piani progressivi
    is_progressive: Optional[bool] = Field(False, description="Se true, crea un piano progressivo")
    target_date: Optional[str] = Field(None, description="Data obiettivo per piano progressivo (YYYY-MM-DD)")
    start_date: Optional[str] = Field(None, description="Data inizio per piano progressivo (YYYY-MM-DD)")
