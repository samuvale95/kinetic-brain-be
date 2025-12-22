from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class NotificationPreferencesResponse(BaseModel):
    """Response schema for notification preferences"""
    email_enabled: bool
    email_workout_reminders: bool
    email_new_workout: bool
    email_workout_completed: bool
    email_plan_updates: bool
    email_weekly_generation: bool
    push_enabled: bool
    push_workout_reminders: bool
    push_new_workout: bool
    push_workout_completed: bool
    push_plan_updates: bool
    push_weekly_generation: bool
    
    class Config:
        from_attributes = True


class NotificationPreferencesUpdate(BaseModel):
    """Update schema for notification preferences - all fields optional for partial updates"""
    email_enabled: Optional[bool] = None
    email_workout_reminders: Optional[bool] = None
    email_new_workout: Optional[bool] = None
    email_workout_completed: Optional[bool] = None
    email_plan_updates: Optional[bool] = None
    email_weekly_generation: Optional[bool] = None
    push_enabled: Optional[bool] = None
    push_workout_reminders: Optional[bool] = None
    push_new_workout: Optional[bool] = None
    push_workout_completed: Optional[bool] = None
    push_plan_updates: Optional[bool] = None
    push_weekly_generation: Optional[bool] = None


class DeviceTokenRegister(BaseModel):
    """Schema for device token registration"""
    device_token: str = Field(..., min_length=1, max_length=500, description="Device token for push notifications")
    platform: str = Field(..., pattern="^(ios|android|web)$", description="Platform: ios, android, or web")
    device_id: Optional[str] = Field(None, max_length=255, description="Unique device identifier (optional)")
    app_version: Optional[str] = Field(None, max_length=50, description="App version (optional, useful for debugging)")


class DeviceTokenResponse(BaseModel):
    """Response schema for device token"""
    id: int
    user_id: int
    device_token: str
    platform: str
    device_id: Optional[str] = None
    app_version: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class NotificationSendRequest(BaseModel):
    """Internal request schema for sending notifications"""
    user_id: int = Field(..., description="User ID to send notification to")
    notification_type: str = Field(
        ...,
        pattern="^(workout_reminder|new_workout|workout_completed|plan_updates|weekly_generation)$",
        description="Type of notification"
    )
    title: str = Field(..., min_length=1, max_length=200, description="Notification title")
    body: str = Field(..., min_length=1, max_length=1000, description="Notification body/message")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional data payload (optional)")
    channels: Optional[List[str]] = Field(
        None,
        description="Channels to send to (email, push). If not specified, uses user preferences"
    )


class NotificationSendResponse(BaseModel):
    """Response schema for notification send operation"""
    sent: Dict[str, bool] = Field(..., description="Whether notification was sent for each channel")
    skipped: Dict[str, bool] = Field(..., description="Whether notification was skipped for each channel")
    reason: Dict[str, Optional[str]] = Field(..., description="Reason if skipped (None if sent)")


class NotificationLogResponse(BaseModel):
    """Response schema for notification log entry"""
    id: int
    user_id: int
    notification_type: str
    channel: str
    title: str
    body: str
    data: Optional[Dict[str, Any]] = None
    status: str  # sent, failed, skipped
    error_message: Optional[str] = None
    sent_at: datetime
    
    class Config:
        from_attributes = True


class NotificationLogListResponse(BaseModel):
    """Response schema for notification log list"""
    logs: List[NotificationLogResponse]
    total: int
    skip: int
    limit: int

