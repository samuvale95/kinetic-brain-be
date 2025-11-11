from __future__ import annotations

from pydantic import BaseModel, Field, validator, model_validator
from typing import Optional, List, Dict, Any, Literal
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
    is_progressive: Optional[bool] = None  # Calculated field
    
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
    zone: Optional[str] = Field(None, pattern="^(Z1|Z2|Z3|Z4|Z5|Z6|Z7)$")
    structure_json: Optional["WorkoutStructure"] = None
    notes: Optional[str] = None


class WorkoutUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    type: Optional[str] = Field(None, min_length=1, max_length=50)
    day_number: Optional[int] = Field(None, ge=1)
    scheduled_date: Optional[date] = None
    duration_minutes: Optional[int] = Field(None, gt=0, le=1440)
    intensity: Optional[str] = Field(None, pattern="^(easy|moderate|hard)$")
    zone: Optional[str] = Field(None, pattern="^(Z1|Z2|Z3|Z4|Z5|Z6|Z7)$")
    structure_json: Optional["WorkoutStructure"] = None
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
    structure_json: Optional["WorkoutStructure"] = None
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


RUN_ZONES = {"Z1", "Z2", "Z3", "Z4", "Z5"}
BIKE_ZONES = {"Z1", "Z2", "Z3", "Z4", "Z5", "Z6", "Z7"}


class WorkoutDuration(BaseModel):
    type: Literal["time", "distance", "repetitions"]
    seconds: Optional[int] = Field(None, gt=0)
    meters: Optional[int] = Field(None, gt=0)
    repetitions: Optional[int] = Field(None, gt=0)

    @model_validator(mode="after")
    def validate_payload(cls, values: "WorkoutDuration") -> "WorkoutDuration":
        if values.type == "time":
            if values.seconds is None:
                raise ValueError("seconds is required when duration type is 'time'")
        elif values.type == "distance":
            if values.meters is None:
                raise ValueError("meters is required when duration type is 'distance'")
        elif values.type == "repetitions":
            if values.repetitions is None:
                raise ValueError("repetitions is required when duration type is 'repetitions'")
        return values


class WorkoutTarget(BaseModel):
    type: Literal["zone", "heart_rate", "power", "pace", "cadence", "rpe"]
    zone: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    units: Optional[str] = None
    notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_target(cls, values: "WorkoutTarget") -> "WorkoutTarget":
        if values.type == "zone":
            if not values.zone:
                raise ValueError("zone is required when target type is 'zone'")
        elif values.type == "rpe":
            if values.min_value is None and values.max_value is None:
                raise ValueError("min_value or max_value required when target type is 'rpe'")
        else:
            if values.min_value is None and values.max_value is None:
                raise ValueError("min_value or max_value is required for numeric targets")
        return values


class WorkoutSegmentStep(BaseModel):
    step_type: Literal["steady", "interval", "recovery", "rest", "drill", "technique", "strength", "repeat"]
    name: Optional[str] = Field(None, max_length=100)
    duration: Optional[WorkoutDuration] = None
    target: Optional[WorkoutTarget] = None
    notes: Optional[str] = Field(None, max_length=500)
    repeat: Optional[int] = Field(None, gt=0)
    steps: Optional[List["WorkoutSegmentStep"]] = None

    @model_validator(mode="after")
    def validate_step(cls, values: "WorkoutSegmentStep") -> "WorkoutSegmentStep":
        if values.step_type == "repeat":
            if values.repeat is None or not values.steps:
                raise ValueError("repeat steps must include repeat count and nested steps")
        else:
            if values.duration is None:
                raise ValueError("duration is required for non-repeat steps")
        return values


class WorkoutSegment(BaseModel):
    segment_type: Literal["warmup", "main", "cooldown", "brick", "technique", "optional"]
    name: Optional[str] = Field(None, max_length=100)
    steps: List[WorkoutSegmentStep]
    notes: Optional[str] = Field(None, max_length=500)

    @validator("steps")
    def validate_steps(cls, steps: List[WorkoutSegmentStep]) -> List[WorkoutSegmentStep]:
        if not steps:
            raise ValueError("segment must contain at least one step")
        return steps


class WorkoutStructureMetadata(BaseModel):
    focus: Optional[str] = Field(None, max_length=200)
    rpe_target: Optional[int] = Field(None, ge=1, le=10)
    description: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = Field(None, max_length=500)


class WorkoutStructure(BaseModel):
    sport: str = Field(..., min_length=1, max_length=50)
    segments: List[WorkoutSegment]
    metadata: Optional[WorkoutStructureMetadata] = None
    equipment: Optional[List[str]] = None

    @validator("sport")
    def normalize_sport(cls, sport: str) -> str:
        return sport.lower()

    @validator("segments")
    def ensure_segments(cls, segments: List[WorkoutSegment]) -> List[WorkoutSegment]:
        if not segments:
            raise ValueError("structure must include at least one segment")
        return segments

    @model_validator(mode="after")
    def validate_zone_ranges(cls, values: "WorkoutStructure") -> "WorkoutStructure":
        sport = values.sport or "run"

        if sport in {"cycling", "bike", "bici"}:
            allowed_zones = BIKE_ZONES
        else:
            allowed_zones = RUN_ZONES

        def check_step(step: WorkoutSegmentStep) -> None:
            target = step.target
            if target and target.type == "zone" and target.zone:
                zone = target.zone.upper()
                if zone not in allowed_zones:
                    raise ValueError(f"zone '{zone}' not allowed for sport '{sport}'")
            if step.step_type == "repeat" and step.steps:
                for nested in step.steps:
                    check_step(nested)

        for segment in values.segments:
            for step in segment.steps:
                check_step(step)

        return values


WorkoutSegmentStep.update_forward_refs()
WorkoutSegment.update_forward_refs()
WorkoutStructure.update_forward_refs()


class AIWorkoutPlanRequest(BaseModel):
    sport_type: str = Field(..., min_length=1, max_length=50)
    level: str = Field(..., pattern="^(beginner|intermediate|advanced)$")
    goal: str = Field(..., min_length=1, max_length=200)
    weekly_hours: Optional[float] = Field(None, gt=0, le=168, description="Ore settimanali disponibili (indicativo)")
    user_profile: Optional[Dict[str, Any]] = None
    preferences: Optional[Dict[str, Any]] = None
    
    # Parametri per piani tradizionali
    duration_weeks: Optional[int] = Field(None, ge=1, le=52)
    
    # Parametri per piani progressivi
    is_progressive: Optional[bool] = Field(False, description="Se true, crea un piano progressivo")
    target_date: Optional[str] = Field(None, description="Data obiettivo per piano progressivo (YYYY-MM-DD)")
    start_date: Optional[str] = Field(None, description="Data inizio per piano progressivo (YYYY-MM-DD)")
