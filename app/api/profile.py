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
from app.schemas.notification import (
    NotificationPreferencesResponse,
    NotificationPreferencesUpdate
)
from app.models.user import UserProfile, PerformanceMetrics
from app.services.calculation_service import CalculationService
from app.services.notification_service import NotificationService
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


@router.options("/notification-preferences")
async def options_profile_notification_preferences():
    """Handle OPTIONS request for CORS preflight"""
    return Response(status_code=200)


@router.get("", response_model=UserProfileResponse)
@router.get("/", response_model=UserProfileResponse)
async def get_profile(current_user: dict = Depends(get_current_user), 
                     db: Session = Depends(get_db)):
    """Get user profile. Creates an empty profile if one doesn't exist."""
    profile = db.query(UserProfile).filter(
        UserProfile.user_id == current_user["user_id"]
    ).first()
    
    # Create empty profile if it doesn't exist
    if not profile:
        profile = UserProfile(
            user_id=current_user["user_id"],
            preferred_zone_type='hr'  # Default zone preference
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
    
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
    
    # Calculate HRR if we have both values (simple calculation, not zone calculation)
    if metrics_data.hr_max and metrics_data.hr_rest:
        update_data['hrr'] = metrics_data.hr_max - metrics_data.hr_rest
    
    # Calculate wkg if FTP and weight are available (simple calculation, not zone calculation)
    if metrics_data.ftp:
        profile = db.query(UserProfile).filter(
            UserProfile.user_id == current_user["user_id"]
        ).first()
        if profile and profile.weight:
            from app.utils.calculations import calculate_wkg
            update_data["wkg"] = calculate_wkg(metrics_data.ftp, profile.weight)
    
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
    
    # Calculate HRR if we have both values (simple calculation, not zone calculation)
    hr_max_val = metrics_data.hr_max or (metrics.hr_max if metrics else None)
    hr_rest_val = metrics_data.hr_rest or (metrics.hr_rest if metrics else None)
    if hr_max_val and hr_rest_val:
        update_data['hrr'] = hr_max_val - hr_rest_val
    
    # Calculate wkg if FTP and weight are available (simple calculation, not zone calculation)
    if metrics_data.ftp:
        profile = db.query(UserProfile).filter(
            UserProfile.user_id == current_user["user_id"]
        ).first()
        if profile and profile.weight:
            from app.utils.calculations import calculate_wkg
            update_data["wkg"] = calculate_wkg(metrics_data.ftp, profile.weight)
    
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


@router.get("/notification-preferences", response_model=NotificationPreferencesResponse)
async def get_notification_preferences(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get notification preferences for the authenticated user.
    Creates default preferences if they don't exist.
    """
    notification_service = NotificationService(db)
    prefs = notification_service.get_preferences(current_user["user_id"])
    
    return NotificationPreferencesResponse(
        email_enabled=prefs.email_enabled,
        email_workout_reminders=prefs.email_workout_reminders,
        email_new_workout=prefs.email_new_workout,
        email_workout_completed=prefs.email_workout_completed,
        email_plan_updates=prefs.email_plan_updates,
        email_weekly_generation=prefs.email_weekly_generation,
        push_enabled=prefs.push_enabled,
        push_workout_reminders=prefs.push_workout_reminders,
        push_new_workout=prefs.push_new_workout,
        push_workout_completed=prefs.push_workout_completed,
        push_plan_updates=prefs.push_plan_updates,
        push_weekly_generation=prefs.push_weekly_generation,
    )


@router.put("/notification-preferences", response_model=NotificationPreferencesResponse)
async def update_notification_preferences(
    preferences: NotificationPreferencesUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update notification preferences for the authenticated user.
    Only provided fields will be updated (partial update).
    """
    notification_service = NotificationService(db)
    
    # Convert Pydantic model to dict, excluding None values
    update_data = preferences.model_dump(exclude_unset=True, exclude_none=True)
    
    prefs = notification_service.update_preferences(
        user_id=current_user["user_id"],
        update_data=update_data
    )
    
    return NotificationPreferencesResponse(
        email_enabled=prefs.email_enabled,
        email_workout_reminders=prefs.email_workout_reminders,
        email_new_workout=prefs.email_new_workout,
        email_workout_completed=prefs.email_workout_completed,
        email_plan_updates=prefs.email_plan_updates,
        email_weekly_generation=prefs.email_weekly_generation,
        push_enabled=prefs.push_enabled,
        push_workout_reminders=prefs.push_workout_reminders,
        push_new_workout=prefs.push_new_workout,
        push_workout_completed=prefs.push_workout_completed,
        push_plan_updates=prefs.push_plan_updates,
        push_weekly_generation=prefs.push_weekly_generation,
    )
