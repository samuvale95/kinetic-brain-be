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


# WeeklySummaryResponse removed - now using daily metrics

