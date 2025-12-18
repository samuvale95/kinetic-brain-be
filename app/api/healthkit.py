"""
HealthKit API endpoints for Apple HealthKit integration.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from typing import Optional, List
from datetime import datetime
from loguru import logger

from app.database import get_db
from app.api.auth import get_current_user
from app.schemas.healthkit import (
    HealthKitWorkoutsSyncRequest,
    HealthKitWorkoutsSyncResponse,
    HealthKitHealthDataRequest,
    HealthKitHealthDataResponse,
    HealthKitSyncStatusRequest,
    HealthKitSyncStatusResponse,
    HealthKitWorkoutResponse
)
from app.services.healthkit_service import HealthKitService
from app.models.healthkit import HealthKitWorkout
from app.models.user import UserProfile
from app.models.workout import WorkoutSession

router = APIRouter(prefix="/healthkit", tags=["healthkit"])


# OPTIONS endpoints for CORS preflight
@router.options("/workouts")
async def options_healthkit_workouts():
    """Handle OPTIONS request for CORS preflight"""
    return Response(status_code=200)


@router.options("/health-data")
async def options_healthkit_health_data():
    """Handle OPTIONS request for CORS preflight"""
    return Response(status_code=200)


@router.options("/sync-status")
async def options_healthkit_sync_status():
    """Handle OPTIONS request for CORS preflight"""
    return Response(status_code=200)


@router.post("/workouts", response_model=HealthKitWorkoutsSyncResponse)
async def sync_workouts(
    request: HealthKitWorkoutsSyncRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Synchronize workouts from Apple HealthKit.
    
    Accepts a list of workouts and syncs them to the database.
    Attempts to match workouts with planned workouts.
    Creates WorkoutSession records for matched workouts.
    """
    user_id = current_user["user_id"]
    service = HealthKitService(db)
    
    synced_count = 0
    matched_count = 0
    created_sessions_count = 0
    updated_sessions_count = 0
    
    try:
        for workout_data in request.workouts:
            try:
                # Create or update HealthKitWorkout
                # Convert Pydantic model to dict, handling alias for metadata -> hk_metadata
                workout_dict = workout_data.model_dump()
                # Map 'metadata' alias to 'hk_metadata' for database field
                if 'metadata' in workout_dict:
                    workout_dict['metadata'] = workout_dict.pop('metadata')
                healthkit_workout = service.create_or_update_workout(
                    user_id=user_id,
                    workout_data=workout_dict
                )
                synced_count += 1
                
                # Try to match with planned workout
                matched_workout = service.match_workout_to_planned(healthkit_workout)
                
                if matched_workout:
                    matched_count += 1
                    
                    # Check if session already exists
                    existing_session = db.execute(
                        select(WorkoutSession)
                        .where(
                            and_(
                                WorkoutSession.workout_id == matched_workout.id,
                                WorkoutSession.healthkit_uuid == healthkit_workout.hk_workout_uuid
                            )
                        )
                    ).scalar_one_or_none()
                    
                    if existing_session:
                        # Update existing session
                        # For now, we'll create a new one if metrics/intervals changed
                        # In production, you might want to update the existing one
                        updated_sessions_count += 1
                    else:
                        # Create new session
                        session = service.create_workout_session_from_healthkit(
                            healthkit_workout=healthkit_workout,
                            workout=matched_workout,
                            metrics=workout_data.metrics,
                            intervals=workout_data.intervals
                        )
                        created_sessions_count += 1
                else:
                    # No match found - still create session if we have enough data
                    if workout_data.metrics:
                        session = service.create_workout_session_from_healthkit(
                            healthkit_workout=healthkit_workout,
                            workout=None,
                            metrics=workout_data.metrics,
                            intervals=workout_data.intervals
                        )
                        created_sessions_count += 1
                
                db.commit()
                
            except Exception as e:
                logger.error(f"[HEALTHKIT] Error syncing workout {workout_data.hk_workout_uuid}: {e}")
                db.rollback()
                continue
        
        # Update sync anchor if provided
        new_anchor = None
        if request.sync_anchor:
            profile = db.execute(
                select(UserProfile)
                .where(UserProfile.user_id == user_id)
            ).scalar_one_or_none()
            
            if profile:
                profile.healthkit_workout_anchor = request.sync_anchor
                db.commit()
                new_anchor = request.sync_anchor
        
        return HealthKitWorkoutsSyncResponse(
            success=True,
            synced=synced_count,
            matched=matched_count,
            created_sessions=created_sessions_count,
            updated_sessions=updated_sessions_count,
            new_anchor=new_anchor
        )
        
    except Exception as e:
        logger.exception(f"[HEALTHKIT] Error in sync_workouts: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync workouts: {str(e)}"
        )


@router.post("/health-data", response_model=HealthKitHealthDataResponse)
async def sync_health_data(
    request: HealthKitHealthDataRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Synchronize health data from Apple HealthKit.
    
    Updates DailyReadinessMetrics with HealthKit data (HRV, RHR, sleep, etc.).
    """
    user_id = current_user["user_id"]
    service = HealthKitService(db)
    
    try:
        # Update diary entry
        diary_entry = service.update_diary_entry_from_healthkit(
            user_id=user_id,
            date_str=request.date,
            metrics=request.metrics
        )
        
        # Update sync anchor if provided
        new_anchor = None
        if request.sync_anchor:
            profile = db.execute(
                select(UserProfile)
                .where(UserProfile.user_id == user_id)
            ).scalar_one_or_none()
            
            if profile:
                profile.healthkit_health_anchor = request.sync_anchor
                db.commit()
                new_anchor = request.sync_anchor
        
        return HealthKitHealthDataResponse(
            success=True,
            diary_entry_updated=True,
            diary_entry_id=diary_entry.id,
            new_anchor=new_anchor
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.exception(f"[HEALTHKIT] Error in sync_health_data: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync health data: {str(e)}"
        )


@router.get("/workouts/pending", response_model=List[HealthKitWorkoutResponse])
async def get_pending_workouts(
    since: Optional[datetime] = Query(None, description="Return only workouts after this date"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get HealthKit workouts pending synchronization.
    
    Returns workouts with sync_status='pending'.
    Optionally filtered by 'since' date.
    """
    user_id = current_user["user_id"]
    
    query = (
        select(HealthKitWorkout)
        .where(
            and_(
                HealthKitWorkout.user_id == user_id,
                HealthKitWorkout.sync_status == "pending"
            )
        )
    )
    
    if since:
        query = query.where(HealthKitWorkout.start_date >= since)
    
    workouts = db.execute(query.order_by(HealthKitWorkout.start_date.desc())).scalars().all()
    
    return [HealthKitWorkoutResponse.model_validate(w) for w in workouts]


@router.post("/sync-status", response_model=HealthKitSyncStatusResponse)
async def update_sync_status(
    request: HealthKitSyncStatusRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update HealthKit sync status in user profile.
    
    Updates last sync date and anchor objects for incremental sync.
    """
    user_id = current_user["user_id"]
    
    try:
        profile = db.execute(
            select(UserProfile)
            .where(UserProfile.user_id == user_id)
        ).scalar_one_or_none()
        
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        
        # Update sync status
        profile.healthkit_enabled = True
        profile.healthkit_last_sync = request.last_sync_date
        
        if request.workout_anchor:
            profile.healthkit_workout_anchor = request.workout_anchor
        
        if request.health_anchor:
            profile.healthkit_health_anchor = request.health_anchor
        
        db.commit()
        db.refresh(profile)
        
        return HealthKitSyncStatusResponse(
            success=True,
            profile_updated=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"[HEALTHKIT] Error in update_sync_status: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update sync status: {str(e)}"
        )

