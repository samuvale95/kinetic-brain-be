from datetime import date
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field
from datetime import datetime


class TrainingMetricsResponse(BaseModel):
    """Schema for training metrics response"""
    
    id: int
    strava_activity_id: Optional[int] = None
    workout_session_id: Optional[int] = None
    
    tss: Optional[float] = None
    normalized_power: Optional[float] = None
    intensity_factor: Optional[float] = None
    trimp: Optional[float] = None
    
    time_in_zone_1: int = 0
    time_in_zone_2: int = 0
    time_in_zone_3: int = 0
    time_in_zone_4: int = 0
    time_in_zone_5: int = 0
    
    zone_distribution: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


class GroupingGranularity(str, Enum):
    day = "day"
    week = "week"
    month = "month"
    year = "year"


class MetricsLoadMetadata(BaseModel):
    grouping: GroupingGranularity
    start_date: date
    end_date: date
    sport: Optional[str] = None


class PlanAdherenceSummary(BaseModel):
    planned: int
    completed_sessions: int
    scheduled_completed: int
    scheduled_skipped: int


class LoadLongWorkout(BaseModel):
    duration_minutes: Optional[float] = None
    distance_km: Optional[float] = None
    progression_pct: Optional[float] = None


class LoadSeriesPoint(BaseModel):
    period_start: date
    period_end: date
    total_duration_minutes: Optional[float] = None
    total_distance_km: Optional[float] = None
    total_tss: Optional[float] = None
    multi_sport_load: Optional[float] = None
    ct_load: Optional[float] = None
    acute_load: Optional[float] = None
    training_stress_balance: Optional[float] = None
    sport_breakdown: Optional[Dict[str, Dict[str, Any]]] = None
    high_intensity_ratio: Optional[float] = None
    high_intensity_sessions: Optional[int] = None
    long_workout: Optional[LoadLongWorkout] = None
    compliance_score: Optional[float] = None
    plan_adherence: Optional[PlanAdherenceSummary] = None


class LoadMetricsResponse(BaseModel):
    metadata: MetricsLoadMetadata
    series: list[LoadSeriesPoint]


class ReadinessPointHR(BaseModel):
    baseline: Optional[float] = None
    value: Optional[float] = None
    delta: Optional[float] = None


class ReadinessSeriesPoint(BaseModel):
    period_start: date
    period_end: date
    recovery_index: Optional[float] = None
    readiness_state: Optional[str] = None
    hydration_score: Optional[float] = None
    nutrition_score: Optional[float] = None
    hrv: Optional[ReadinessPointHR] = None
    rhr: Optional[ReadinessPointHR] = None
    sleep_hours: Optional[float] = None
    sleep_quality_score: Optional[float] = None
    epoc: Optional[float] = None
    injury_risk_score: Optional[float] = None


class ReadinessMetadata(BaseModel):
    grouping: GroupingGranularity
    start_date: date
    end_date: date


class ReadinessMetricsResponse(BaseModel):
    metadata: ReadinessMetadata
    series: list[ReadinessSeriesPoint]


class DiaryEntryRequest(BaseModel):
    """Input per creare/aggiornare il diario giornaliero (readiness)."""
    date: Optional[date] = Field(default=None, description="Data del diario; default oggi (timezone server)")
    hrv_value: Optional[float] = None
    rhr_value: Optional[float] = None
    sleep_hours: Optional[float] = None
    sleep_quality_score: Optional[float] = None
    epoc: Optional[float] = None
    hydration_status: Optional[str] = None
    hydration_score: Optional[float] = None
    nutrition_score: Optional[float] = None
    weight_delta_kg: Optional[float] = None
    perceived_exertion: Optional[int] = Field(default=None, ge=1, le=10)
    notes: Optional[str] = None

class DiaryEntryResponse(BaseModel):
    """Risposta minimale per il diario."""
    success: bool
    date: date
    readiness_state: Optional[str] = None
    recovery_index: Optional[float] = None

