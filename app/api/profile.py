from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.schemas.user import (
    UserProfileCreate, UserProfileUpdate, UserProfileResponse,
    PerformanceMetricsCreate, PerformanceMetricsResponse,
    ZoneCalculationRequest, ZoneCalculationResponse
)
from app.models.user import UserProfile, PerformanceMetrics
from app.services.calculation_service import CalculationService
from app.api.auth import get_current_user

router = APIRouter(prefix="/profile", tags=["profile"])


# OPTIONS endpoints for CORS preflight
@router.options("/")
async def options_profile():
    """Handle OPTIONS request for CORS preflight"""
    return Response(status_code=200)


@router.options("/performance")
async def options_profile_performance():
    """Handle OPTIONS request for CORS preflight"""
    return Response(status_code=200)


@router.options("/calculate-zones")
async def options_profile_calculate_zones():
    """Handle OPTIONS request for CORS preflight"""
    return Response(status_code=200)


@router.get("/", response_model=UserProfileResponse)
async def get_profile(current_user: dict = Depends(get_current_user), 
                     db: Session = Depends(get_db)):
    """Get user profile"""
    profile = db.query(UserProfile).filter(
        UserProfile.user_id == current_user["user_id"]
    ).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    return profile


@router.post("/", response_model=UserProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(profile_data: UserProfileCreate,
                        current_user: dict = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    """Create user profile"""
    # Check if profile already exists
    existing_profile = db.query(UserProfile).filter(
        UserProfile.user_id == current_user["user_id"]
    ).first()
    
    if existing_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profile already exists"
        )
    
    profile = UserProfile(
        user_id=current_user["user_id"],
        **profile_data.dict()
    )
    
    db.add(profile)
    db.commit()
    db.refresh(profile)
    
    return profile


@router.put("/", response_model=UserProfileResponse)
async def update_profile(profile_data: UserProfileUpdate,
                        current_user: dict = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    """Update user profile"""
    profile = db.query(UserProfile).filter(
        UserProfile.user_id == current_user["user_id"]
    ).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    update_data = profile_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)
    
    db.commit()
    db.refresh(profile)
    
    return profile


@router.get("/performance", response_model=List[PerformanceMetricsResponse])
async def get_performance_metrics(current_user: dict = Depends(get_current_user),
                                 db: Session = Depends(get_db)):
    """Get user performance metrics"""
    metrics = db.query(PerformanceMetrics).filter(
        PerformanceMetrics.user_id == current_user["user_id"]
    ).all()
    
    return metrics


@router.post("/performance", response_model=PerformanceMetricsResponse, status_code=status.HTTP_201_CREATED)
async def create_performance_metrics(metrics_data: PerformanceMetricsCreate,
                                    current_user: dict = Depends(get_current_user),
                                    db: Session = Depends(get_db)):
    """Create performance metrics"""
    # Calculate zones
    zones = CalculationService.calculate_zones(
        metric_type=metrics_data.metric_type,
        threshold_value=metrics_data.threshold_value,
        max_value=metrics_data.max_value,
        rest_value=metrics_data.rest_value
    )
    
    metrics = PerformanceMetrics(
        user_id=current_user["user_id"],
        **metrics_data.dict(),
        zones_json=zones["zones"]
    )
    
    db.add(metrics)
    db.commit()
    db.refresh(metrics)
    
    return metrics


@router.post("/calculate-zones", response_model=ZoneCalculationResponse)
async def calculate_zones(zone_request: ZoneCalculationRequest):
    """Calculate training zones"""
    zones = CalculationService.calculate_zones(
        metric_type=zone_request.metric_type,
        threshold_value=zone_request.threshold_value,
        max_value=zone_request.max_value,
        rest_value=zone_request.rest_value
    )
    
    return ZoneCalculationResponse(
        zones=zones["zones"],
        calculated_at=zones["calculated_at"]
    )
