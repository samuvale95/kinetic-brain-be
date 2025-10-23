from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date


class CalendarEventCreate(BaseModel):
    workout_id: Optional[int] = None
    title: str = Field(..., min_length=1, max_length=200)
    event_type: str = Field(..., min_length=1, max_length=50)
    scheduled_date: date
    duration_minutes: int = Field(..., gt=0, le=1440)
    is_recurring: bool = False


class CalendarEventUpdate(BaseModel):
    workout_id: Optional[int] = None
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    event_type: Optional[str] = Field(None, min_length=1, max_length=50)
    scheduled_date: Optional[date] = None
    duration_minutes: Optional[int] = Field(None, gt=0, le=1440)
    is_recurring: Optional[bool] = None


class CalendarEventResponse(BaseModel):
    id: int
    user_id: int
    workout_id: Optional[int] = None
    title: str
    event_type: str
    scheduled_date: date
    duration_minutes: int
    is_recurring: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class DragDropRequest(BaseModel):
    event_id: int
    new_date: date
    new_duration_minutes: Optional[int] = None


class CalendarMonthRequest(BaseModel):
    year: int = Field(..., ge=2020, le=2030)
    month: int = Field(..., ge=1, le=12)
