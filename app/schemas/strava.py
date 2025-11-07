from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date


class StravaAccountResponse(BaseModel):
    id: int
    user_id: int
    strava_id: int
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    profile_medium: Optional[str] = None
    profile: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    sex: Optional[str] = None
    premium: bool = False
    summit: bool = False
    created_at: datetime
    
    class Config:
        from_attributes = True


class StravaActivityResponse(BaseModel):
    id: int
    strava_activity_id: int
    name: str
    type: str
    sport_type: Optional[str] = None
    start_date: datetime
    start_date_local: datetime
    timezone: Optional[str] = None
    distance: Optional[float] = None
    moving_time: Optional[int] = None
    elapsed_time: Optional[int] = None
    total_elevation_gain: Optional[float] = None
    average_speed: Optional[float] = None
    max_speed: Optional[float] = None
    average_heartrate: Optional[float] = None
    max_heartrate: Optional[float] = None
    average_watts: Optional[float] = None
    max_watts: Optional[float] = None
    weighted_average_watts: Optional[float] = None
    average_cadence: Optional[float] = None
    temperature: Optional[float] = None
    feels_like: Optional[float] = None
    calories: Optional[float] = None
    kilojoules: Optional[float] = None
    is_synced: bool = False
    sync_status: str = "pending"
    workout_match: Optional[Dict[str, Any]] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class StravaSyncRequest(BaseModel):
    days_back: int = Field(30, ge=1, le=365, description="Number of days to sync back")


class StravaSyncResponse(BaseModel):
    total_activities: int
    new_activities: int
    updated_activities: int = 0
    already_synced: int
    metrics_calculated: int = 0
    metrics_recalculated: int = 0
    metrics_errors: int = 0
    daily_metrics_updated: int = 0


class StravaMatchResponse(BaseModel):
    total_unmatched: int
    matched_count: int
    matches: List[Dict[str, Any]]


class StravaAuthResponse(BaseModel):
    auth_url: str
    state: str


class StravaCallbackRequest(BaseModel):
    code: str
    state: str


class StravaCallbackResponse(BaseModel):
    success: bool
    message: str
    strava_account_id: Optional[int] = None
    athlete: Optional[Dict[str, Any]] = None
    sync_job_id: Optional[int] = None
    sync_job_status: Optional[str] = None


class StravaSyncJobResponse(BaseModel):
    id: int
    user_id: int
    strava_account_id: int
    job_type: str
    status: str
    status_message: Optional[str] = None
    total_activities: int
    processed_activities: int
    metrics_phase: int
    metrics_phases_total: int
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    requested_days_back: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class StravaSyncJobListResponse(BaseModel):
    jobs: List[StravaSyncJobResponse]



