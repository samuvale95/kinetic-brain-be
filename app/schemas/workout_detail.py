from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from app.schemas.workout import WorkoutStatus, WorkoutStructure


class StravaActivityDetail(BaseModel):
    """Dettagli completi dell'attività Strava"""
    id: int
    strava_activity_id: int
    name: str
    type: str
    sport_type: Optional[str] = None
    start_date: datetime
    start_date_local: datetime
    timezone: Optional[str] = None
    distance: Optional[float] = None  # metri
    moving_time: Optional[int] = None  # secondi
    elapsed_time: Optional[int] = None  # secondi
    total_elevation_gain: Optional[float] = None  # metri
    average_speed: Optional[float] = None  # m/s
    max_speed: Optional[float] = None  # m/s
    average_heartrate: Optional[float] = None  # bpm
    max_heartrate: Optional[float] = None  # bpm
    average_watts: Optional[float] = None  # watt
    max_watts: Optional[float] = None  # watt
    weighted_average_watts: Optional[float] = None  # watt
    average_cadence: Optional[float] = None  # rpm
    temperature: Optional[float] = None  # celsius
    feels_like: Optional[float] = None  # celsius
    calories: Optional[float] = None
    kilojoules: Optional[float] = None
    is_synced: bool = False
    sync_status: str = "pending"
    splits_metric: Optional[Dict[str, Any]] = None
    splits_standard: Optional[Dict[str, Any]] = None
    best_efforts: Optional[Dict[str, Any]] = None
    segment_efforts: Optional[Dict[str, Any]] = None
    raw_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class WorkoutSessionDetail(BaseModel):
    """Dettagli completi della sessione di allenamento"""
    id: int
    workout_id: int
    user_id: int
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    rpe: Optional[int] = None  # Rate of Perceived Exertion (1-10)
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class WorkoutDetail(BaseModel):
    """Dettagli completi dell'allenamento con sessioni e dati Strava"""
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
    structure_json: Optional[WorkoutStructure] = None
    status: WorkoutStatus
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Dettagli aggiuntivi
    sessions: List[WorkoutSessionDetail] = []
    strava_activity: Optional[StravaActivityDetail] = None
    
    class Config:
        from_attributes = True


class WorkoutPlanDetail(BaseModel):
    """Piano di allenamento con tutti gli allenamenti e dettagli"""
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
    
    # Lista completa degli allenamenti
    workouts: List[WorkoutDetail] = []
    
    # Statistiche del piano
    total_workouts: int = 0
    completed_workouts: int = 0
    skipped_workouts: int = 0
    scheduled_workouts: int = 0
    workouts_with_strava: int = 0
    
    class Config:
        from_attributes = True



