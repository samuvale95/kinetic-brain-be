from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


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


class WeeklySummaryResponse(BaseModel):
    """Schema for weekly performance summary response"""
    
    id: int
    user_id: int
    week_start_date: str
    week_end_date: str
    
    weekly_tss: float = 0
    weekly_trimp: float = 0
    volume_hours: float = 0
    volume_kilometers: float = 0
    
    ctl: Optional[float] = None
    atl: Optional[float] = None
    tsb: Optional[float] = None
    
    workouts_completed: int = 0
    workouts_planned: int = 0
    completion_rate: Optional[float] = None
    avg_rpe: Optional[float] = None
    
    zone_distribution: Optional[Dict[str, Any]] = None
    
    avg_hr: Optional[float] = None
    max_hr: Optional[float] = None
    avg_pace: Optional[float] = None
    total_elevation_gain: Optional[float] = None
    
    class Config:
        from_attributes = True

