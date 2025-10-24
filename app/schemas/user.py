from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date


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
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class PerformanceMetricsCreate(BaseModel):
    metric_type: str = Field(..., pattern="^(hr|pace|power)$")
    threshold_value: float = Field(..., gt=0)
    max_value: Optional[float] = Field(None, gt=0)
    rest_value: Optional[float] = Field(None, ge=0)
    test_date: Optional[date] = None


class PerformanceMetricsResponse(BaseModel):
    id: int
    user_id: int
    metric_type: str
    threshold_value: float
    max_value: Optional[float] = None
    rest_value: Optional[float] = None
    zones_json: Optional[Dict[str, Any]] = None
    test_date: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True


class ZoneCalculationRequest(BaseModel):
    metric_type: str = Field(..., pattern="^(hr|pace|power)$")
    threshold_value: float = Field(..., gt=0)
    max_value: Optional[float] = Field(None, gt=0)
    rest_value: Optional[float] = Field(None, ge=0)


class ZoneCalculationResponse(BaseModel):
    zones: Dict[str, Dict[str, float]]
    calculated_at: datetime


# Google OAuth Schemas
class GoogleAuthRequest(BaseModel):
    code: str = Field(..., description="Authorization code from Google")
    redirect_uri: Optional[str] = None


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
