from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class HealthKitWorkoutCreate(BaseModel):
    hk_workout_uuid: str = Field(..., description="HealthKit workout UUID")
    workout_type: str = Field(..., description="Type of workout (running, cycling, etc.)")
    start_date: datetime = Field(..., description="Workout start date/time")
    end_date: datetime = Field(..., description="Workout end date/time")
    duration_seconds: int = Field(..., description="Workout duration in seconds")
    total_distance_meters: Optional[float] = Field(None, description="Total distance in meters")
    total_energy_burned_kcal: Optional[float] = Field(None, description="Total energy burned in kcal")
    total_basal_energy_kcal: Optional[float] = Field(None, description="Total basal energy in kcal")
    elevation_gain_meters: Optional[float] = Field(None, description="Elevation gain in meters")
    elevation_loss_meters: Optional[float] = Field(None, description="Elevation loss in meters")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    metrics: Optional[Dict[str, Any]] = Field(None, description="Workout metrics (HR, pace, power, etc.)")
    intervals: Optional[Dict[str, Any]] = Field(None, description="Workout intervals structure")
    
    class Config:
        populate_by_name = True


class HealthKitWorkoutsSyncRequest(BaseModel):
    workouts: List[HealthKitWorkoutCreate] = Field(..., description="List of workouts to sync")
    sync_anchor: Optional[str] = Field(None, description="Anchor for incremental sync")


class HealthKitWorkoutsSyncResponse(BaseModel):
    success: bool
    synced: int = Field(..., description="Number of workouts synced")
    matched: int = Field(..., description="Number of workouts matched to planned workouts")
    created_sessions: int = Field(..., description="Number of workout sessions created")
    updated_sessions: int = Field(..., description="Number of workout sessions updated")
    new_anchor: Optional[str] = Field(None, description="New anchor for next sync")


class HealthKitHealthDataRequest(BaseModel):
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    metrics: Dict[str, Any] = Field(..., description="Health metrics (HRV, RHR, sleep, weight, etc.)")
    sync_anchor: Optional[str] = Field(None, description="Anchor for incremental sync")


class HealthKitHealthDataResponse(BaseModel):
    success: bool
    diary_entry_updated: bool
    diary_entry_id: Optional[int] = None
    new_anchor: Optional[str] = None


class HealthKitSyncStatusRequest(BaseModel):
    last_sync_date: datetime = Field(..., description="Last sync date/time")
    synced_count: int = Field(..., description="Number of items synced")
    workout_anchor: Optional[str] = Field(None, description="Workout sync anchor")
    health_anchor: Optional[str] = Field(None, description="Health data sync anchor")


class HealthKitSyncStatusResponse(BaseModel):
    success: bool
    profile_updated: bool


class WatchWorkoutFormatResponse(BaseModel):
    workout_id: int
    title: str
    type: str
    sport: str
    duration_minutes: int
    structure: Dict[str, Any] = Field(..., description="Workout structure (warmup/main/cooldown)")
    zones: Dict[str, Any] = Field(..., description="Training zones (HR, pace, power)")


class WatchSessionCreateRequest(BaseModel):
    workout_id: int = Field(..., description="ID of the planned workout")
    start_time: datetime = Field(..., description="Session start time")
    end_time: datetime = Field(..., description="Session end time")
    duration_seconds: int = Field(..., description="Session duration in seconds")
    metrics: Dict[str, Any] = Field(..., description="Session metrics (HR, pace, distance, etc.)")
    intervals: Optional[Dict[str, Any]] = Field(None, description="Session intervals data")
    healthkit_uuid: Optional[str] = Field(None, description="HealthKit workout UUID if available")


class WatchSessionCreateResponse(BaseModel):
    success: bool
    session_id: int
    matched: bool = Field(..., description="Whether session was matched to planned workout")
    workout_matched_id: Optional[int] = Field(None, description="ID of matched workout if any")


class HealthKitWorkoutResponse(BaseModel):
    id: int
    user_id: int
    workout_id: Optional[int] = None
    hk_workout_uuid: str
    hk_source_name: Optional[str] = None
    workout_type: str
    start_date: datetime
    end_date: datetime
    duration_seconds: int
    total_distance_meters: Optional[float] = None
    total_energy_burned_kcal: Optional[float] = None
    total_basal_energy_kcal: Optional[float] = None
    elevation_gain_meters: Optional[float] = None
    elevation_loss_meters: Optional[float] = None
    hk_metadata: Optional[Dict[str, Any]] = Field(None, alias="metadata", description="Additional metadata from HealthKit")
    sync_status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

