from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date
import re


class UserCreate(BaseModel):
    email: str = Field(..., pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    password: str = Field(..., min_length=8)
    name: str = Field(..., min_length=2, max_length=100)


class UserLogin(BaseModel):
    email: str = Field(..., pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    avatar_url: Optional[str] = None
    is_active: bool
    is_verified: bool
    auth_provider: str
    created_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UserProfileCreate(BaseModel):
    age: Optional[int] = Field(None, ge=13, le=100)
    gender: Optional[str] = Field(None, pattern="^(male|female|other)$")
    weight: Optional[float] = Field(None, gt=0, le=300)  # kg
    height: Optional[float] = Field(None, gt=0, le=250)  # cm
    sports: Optional[List[str]] = None
    experience_years: Optional[int] = Field(None, ge=0, le=50)
    weekly_hours: Optional[float] = Field(None, ge=0, le=168)
    main_goal: Optional[str] = Field(None, max_length=100)
    physical_notes: Optional[str] = None
    city: Optional[str] = Field(None, max_length=100)  # City for weather
    latitude: Optional[float] = Field(None, ge=-90, le=90)  # Latitude for weather
    longitude: Optional[float] = Field(None, ge=-180, le=180)  # Longitude for weather


class UserProfileUpdate(BaseModel):
    age: Optional[int] = Field(None, ge=13, le=100)
    gender: Optional[str] = Field(None, pattern="^(male|female|other)$")
    weight: Optional[float] = Field(None, gt=0, le=300)
    height: Optional[float] = Field(None, gt=0, le=250)
    sports: Optional[List[str]] = None
    experience_years: Optional[int] = Field(None, ge=0, le=50)
    weekly_hours: Optional[float] = Field(None, ge=0, le=168)
    main_goal: Optional[str] = Field(None, max_length=100)
    physical_notes: Optional[str] = None
    city: Optional[str] = Field(None, max_length=100)  # City for weather
    latitude: Optional[float] = Field(None, ge=-90, le=90)  # Latitude for weather
    longitude: Optional[float] = Field(None, ge=-180, le=180)  # Longitude for weather


class UserProfileResponse(BaseModel):
    id: int
    user_id: int
    age: Optional[int] = None
    gender: Optional[str] = None
    weight: Optional[float] = None
    height: Optional[float] = None
    sports: Optional[List[str]] = None
    experience_years: Optional[int] = None
    weekly_hours: Optional[float] = None
    main_goal: Optional[str] = None
    physical_notes: Optional[str] = None
    city: Optional[str] = None  # City for weather
    latitude: Optional[float] = None  # Latitude for weather
    longitude: Optional[float] = None  # Longitude for weather
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class PerformanceMetricsBase(BaseModel):
    test_date: Optional[date] = None
    
    # HR Metrics
    hr_max: Optional[float] = Field(None, gt=0, le=250)
    hr_rest: Optional[float] = Field(None, ge=0, le=150)
    threshold_hr: Optional[float] = Field(None, gt=0, le=250)
    hrr: Optional[float] = Field(None, ge=0)  # Heart Rate Reserve
    custom_threshold_hr: Optional[float] = Field(None, gt=0, le=250)
    
    # Pace Metrics
    threshold_pace: Optional[str] = Field(None, description="Format: mm:ss or mm.ss (e.g., '4:15' or '4.15')")
    critical_speed: Optional[float] = Field(None, gt=0)
    vla: Optional[float] = Field(None, gt=0)
    
    @field_validator('threshold_pace')
    @classmethod
    def validate_pace_format(cls, v):
        if v is None:
            return v
        # Validate format: mm:ss or mm.ss where seconds are 0-59
        pattern = r'^\d{1,2}[:.]\d{2}$'
        if not re.match(pattern, v):
            raise ValueError('threshold_pace must be in format "mm:ss" or "mm.ss" (e.g., "4:15" or "4.15")')
        
        # Extract minutes and seconds
        if ':' in v:
            parts = v.split(':')
        else:
            parts = v.split('.')
        
        try:
            minutes = int(parts[0])
            seconds = int(parts[1])
            if seconds < 0 or seconds >= 60:
                raise ValueError('Seconds must be between 00-59')
            if minutes < 0 or minutes > 60:
                raise ValueError('Minutes must be between 0-60')
        except (ValueError, IndexError):
            raise ValueError('Invalid pace format')
        
        return v
    
    # Power Metrics
    ftp: Optional[float] = Field(None, gt=0, description="Functional Threshold Power")
    wkg: Optional[float] = Field(None, gt=0, description="Watts per kilogram")
    
    # Advanced Metrics
    vo2max: Optional[float] = Field(None, gt=0, le=100)
    
    # Structured Zones
    hr_zones: Optional[Dict[str, str]] = Field(None, description="HR zones in format {'z1': '120-135', 'z2': '135-150', ...}")
    hr_zones_source: Optional[str] = Field(None, pattern="^(auto|manual)$")
    hr_threshold_used: Optional[float] = Field(None, gt=0)
    
    pace_zones: Optional[Dict[str, str]] = Field(None, description="Pace zones in format {'z1': '5:00-4:45', 'z2': '4:45-4:30', ...}")
    pace_zones_source: Optional[str] = Field(None, pattern="^(auto|manual)$")
    threshold_pace_used: Optional[str] = Field(None)
    
    power_zones: Optional[Dict[str, str]] = Field(None, description="Power zones in format {'z1': '0-165', 'z2': '166-225', ..., 'z7': '451-540'}")
    power_zones_source: Optional[str] = Field(None, pattern="^(auto|manual)$")
    ftp_used: Optional[float] = Field(None, gt=0)


class PerformanceMetricsCreate(PerformanceMetricsBase):
    pass


class PerformanceMetricsUpdate(PerformanceMetricsBase):
    """Update schema - same fields as Create but all optional"""
    pass


class PerformanceMetricsResponse(BaseModel):
    id: int
    user_id: int
    
    # HR Metrics
    hr_max: Optional[float] = None
    hr_rest: Optional[float] = None
    threshold_hr: Optional[float] = None
    hrr: Optional[float] = None
    custom_threshold_hr: Optional[float] = None
    
    # Pace Metrics
    threshold_pace: Optional[str] = None
    critical_speed: Optional[float] = None
    vla: Optional[float] = None
    
    # Power Metrics
    ftp: Optional[float] = None
    wkg: Optional[float] = None
    
    # Advanced Metrics
    vo2max: Optional[float] = None
    
    # Structured Zones
    hr_zones: Optional[Dict[str, str]] = None
    hr_zones_source: Optional[str] = None
    hr_threshold_used: Optional[float] = None
    
    pace_zones: Optional[Dict[str, str]] = None
    pace_zones_source: Optional[str] = None
    threshold_pace_used: Optional[str] = None
    
    power_zones: Optional[Dict[str, str]] = None
    power_zones_source: Optional[str] = None
    ftp_used: Optional[float] = None
    
    test_date: datetime
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True




# Google OAuth Schemas
class GoogleAuthRequest(BaseModel):
    code: str = Field(..., description="Authorization code from Google")
    redirect_uri: Optional[str] = None


class GoogleIdTokenRequest(BaseModel):
    id_token: str = Field(..., description="Google ID token from React Native")


class GoogleUserInfo(BaseModel):
    id: str
    email: str
    name: str
    picture: Optional[str] = None
    verified_email: bool = True


class OAuthAccountResponse(BaseModel):
    id: int
    user_id: int
    provider: str
    provider_account_id: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# Apple OAuth Schemas
class AppleAuthRequest(BaseModel):
    code: str = Field(..., description="Authorization code from Apple")
    redirect_uri: Optional[str] = None


class AppleIdTokenRequest(BaseModel):
    id_token: str = Field(..., description="Apple Identity Token from React Native or web")


class AppleUserInfo(BaseModel):
    id: str
    email: str
    name: Optional[str] = None
    email_verified: bool = True
