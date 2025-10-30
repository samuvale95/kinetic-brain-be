from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Dict, Any
from datetime import datetime, timezone
from app.database import get_db
from app.schemas.user import (
    UserProfileCreate, UserProfileUpdate, UserProfileResponse,
    PerformanceMetricsCreate, PerformanceMetricsUpdate, PerformanceMetricsResponse
)
from app.schemas.statistics import ZonePreferenceRequest, ZonePreferenceResponse
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


@router.options("/zone-preference")
async def options_profile_zone_preference():
    """Handle OPTIONS request for CORS preflight"""
    return Response(status_code=200)


@router.get("", response_model=UserProfileResponse)
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
    
    # Ensure preferred_zone_type is set (for backward compatibility)
    if not profile.preferred_zone_type:
        profile.preferred_zone_type = 'hr'
        db.commit()
    
    return profile


@router.post("", response_model=UserProfileResponse, status_code=status.HTTP_201_CREATED)
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


@router.put("", response_model=UserProfileResponse)
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
    update_data = metrics_data.dict(exclude_unset=True, exclude_none=True)
    
    # Auto-calculate zones if needed based on source
    # HR zones
    if metrics_data.hr_zones_source == "auto" or (metrics_data.hr_zones_source is None and metrics_data.threshold_hr):
        try:
            if metrics_data.threshold_hr:
                hr_zones_data = CalculationService.calculate_zones_string_format(
                    metric_type="hr",
                    threshold_hr=metrics_data.threshold_hr,
                    hr_max=metrics_data.hr_max,
                    hr_rest=metrics_data.hr_rest
                )
                update_data.update(hr_zones_data)
                
                # Calculate HRR if we have both values
                if metrics_data.hr_max and metrics_data.hr_rest:
                    update_data['hrr'] = metrics_data.hr_max - metrics_data.hr_rest
        except (ValueError, TypeError):
            pass  # Skip if insufficient data
    
    # Pace zones
    if metrics_data.pace_zones_source == "auto" or (metrics_data.pace_zones_source is None and metrics_data.threshold_pace):
        try:
            pace_zones_data = CalculationService.calculate_zones_string_format(
                metric_type="pace",
                threshold_pace=metrics_data.threshold_pace
            )
            update_data.update(pace_zones_data)
        except (ValueError, TypeError):
            pass  # Skip if insufficient data
    
    # Power zones
    if metrics_data.power_zones_source == "auto" or (metrics_data.power_zones_source is None and metrics_data.ftp):
        try:
            power_zones_data = CalculationService.calculate_zones_string_format(
                metric_type="power",
                ftp=metrics_data.ftp
            )
            update_data.update(power_zones_data)
            
            # Calculate wkg if FTP and weight are available
            if metrics_data.ftp:
                profile = db.query(UserProfile).filter(
                    UserProfile.user_id == current_user["user_id"]
                ).first()
                if profile and profile.weight:
                    from app.utils.calculations import calculate_wkg
                    update_data["wkg"] = calculate_wkg(metrics_data.ftp, profile.weight)
        except (ValueError, TypeError):
            pass  # Skip if insufficient data
    
    metrics = PerformanceMetrics(
        user_id=current_user["user_id"],
        **update_data
    )
    
    db.add(metrics)
    db.commit()
    db.refresh(metrics)
    
    return metrics


@router.put("/performance", response_model=PerformanceMetricsResponse)
async def update_performance_metrics(metrics_data: PerformanceMetricsUpdate,
                                    current_user: dict = Depends(get_current_user),
                                    db: Session = Depends(get_db)):
    """Update or create performance metrics (upsert)"""
    # Find existing metrics - we'll store all metrics in one record per user
    # Or create a new one if none exists
    metrics = db.query(PerformanceMetrics).filter(
        PerformanceMetrics.user_id == current_user["user_id"]
    ).order_by(PerformanceMetrics.test_date.desc()).first()
    
    update_data = metrics_data.dict(exclude_unset=True, exclude_none=True)
    
    # Auto-calculate zones if source is "auto" or not set and threshold values provided
    # HR zones
    if (metrics_data.hr_zones_source == "auto" or 
        (metrics_data.hr_zones_source is None and (metrics_data.threshold_hr or (metrics and metrics.threshold_hr)))):
        try:
            threshold_hr = metrics_data.threshold_hr or (metrics.threshold_hr if metrics else None)
            hr_max = metrics_data.hr_max or (metrics.hr_max if metrics else None)
            hr_rest = metrics_data.hr_rest or (metrics.hr_rest if metrics else None)
            
            if threshold_hr:
                hr_zones_data = CalculationService.calculate_zones_string_format(
                    metric_type="hr",
                    threshold_hr=threshold_hr,
                    hr_max=hr_max,
                    hr_rest=hr_rest
                )
                update_data.update(hr_zones_data)
                
                # Calculate HRR if we have both values
                if (metrics_data.hr_max or (metrics and metrics.hr_max)) and (metrics_data.hr_rest or (metrics and metrics.hr_rest)):
                    hr_max_val = metrics_data.hr_max or (metrics.hr_max if metrics else None)
                    hr_rest_val = metrics_data.hr_rest or (metrics.hr_rest if metrics else None)
                    if hr_max_val and hr_rest_val:
                        update_data['hrr'] = hr_max_val - hr_rest_val
        except (ValueError, TypeError, AttributeError):
            pass  # Skip if insufficient data
    
    # Pace zones
    if (metrics_data.pace_zones_source == "auto" or 
        (metrics_data.pace_zones_source is None and metrics_data.threshold_pace)):
        try:
            pace_zones_data = CalculationService.calculate_zones_string_format(
                metric_type="pace",
                threshold_pace=metrics_data.threshold_pace
            )
            update_data.update(pace_zones_data)
        except (ValueError, TypeError):
            pass  # Skip if insufficient data
    
    # Power zones
    if (metrics_data.power_zones_source == "auto" or 
        (metrics_data.power_zones_source is None and metrics_data.ftp)):
        try:
            power_zones_data = CalculationService.calculate_zones_string_format(
                metric_type="power",
                ftp=metrics_data.ftp
            )
            update_data.update(power_zones_data)
            
            # Calculate wkg if FTP and weight are available
            if metrics_data.ftp:
                profile = db.query(UserProfile).filter(
                    UserProfile.user_id == current_user["user_id"]
                ).first()
                if profile and profile.weight:
                    from app.utils.calculations import calculate_wkg
                    update_data["wkg"] = calculate_wkg(metrics_data.ftp, profile.weight)
        except (ValueError, TypeError):
            pass  # Skip if insufficient data
    
    if metrics:
        # Update existing metrics
        for field, value in update_data.items():
            setattr(metrics, field, value)
        metrics.updated_at = datetime.now(timezone.utc)
    else:
        # Create new metrics
        metrics = PerformanceMetrics(
            user_id=current_user["user_id"],
            **update_data
        )
        db.add(metrics)
    
    db.commit()
    db.refresh(metrics)
    
    return metrics




@router.put("/zone-preference", response_model=ZonePreferenceResponse)
async def update_zone_preference(request: ZonePreferenceRequest,
                                 current_user: dict = Depends(get_current_user),
                                 db: Session = Depends(get_db)):
    """Update user's preferred zone type"""
    profile = db.query(UserProfile).filter(
        UserProfile.user_id == current_user["user_id"]
    ).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    # Update preferred zone type
    profile.preferred_zone_type = request.preferred_zone_type
    db.commit()
    db.refresh(profile)
    
    # Get current zones based on preference
    current_zones = None
    if request.preferred_zone_type in ["hr", "pace", "power"]:
        # Get the latest performance metrics
        metrics = db.query(PerformanceMetrics).filter(
            PerformanceMetrics.user_id == current_user["user_id"]
        ).order_by(PerformanceMetrics.test_date.desc()).first()
        
        if metrics:
            if request.preferred_zone_type == "hr" and metrics.hr_zones:
                current_zones = CalculationService.convert_zones_to_structured("hr", metrics.hr_zones)
            elif request.preferred_zone_type == "pace" and metrics.pace_zones:
                current_zones = CalculationService.convert_zones_to_structured("pace", metrics.pace_zones)
            elif request.preferred_zone_type == "power" and metrics.power_zones:
                current_zones = CalculationService.convert_zones_to_structured("power", metrics.power_zones)
    
    return {
        'success': True,
        'preferred_zone_type': request.preferred_zone_type,
        'zones_calculated': current_zones is not None,
        'current_zones': current_zones
    }
