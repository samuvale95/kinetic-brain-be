from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class GarminAccountResponse(BaseModel):
    id: int
    user_id: int
    garmin_user_id: Optional[str] = None
    email: Optional[str] = None
    display_name: Optional[str] = None
    auto_sync_enabled: bool
    last_sync_at: Optional[datetime] = None
    is_active: bool
    connected_at: datetime

    class Config:
        from_orm = True


class GarminAuthResponse(BaseModel):
    auth_url: str
    state: str


class GarminCallbackRequest(BaseModel):
    code: str
    state: str


class GarminCallbackResponse(BaseModel):
    success: bool
    account: Optional[GarminAccountResponse] = None
    message: str


class GarminActivityResponse(BaseModel):
    id: int
    garmin_activity_id: str
    activity_type: str
    start_time: datetime
    duration_seconds: int
    distance_meters: Optional[float] = None
    calories: Optional[int] = None
    avg_hr: Optional[int] = None
    max_hr: Optional[int] = None
    match_status: str
    matched_workout_id: Optional[int] = None
    synced_at: datetime

    class Config:
        from_orm = True


class GarminSyncRequest(BaseModel):
    days_back: Optional[int] = Field(None, ge=1, le=365, description="Number of days to sync back")
    force_full: Optional[bool] = Field(False, description="Force full sync ignoring anchor")


class GarminSyncResponse(BaseModel):
    success: bool
    synced_count: int
    message: str
