from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from typing import List, Optional
from datetime import datetime
from app.database import get_db
from app.config import settings
from app.schemas.strava import (
    StravaAccountResponse, StravaActivityResponse, StravaSyncRequest,
    StravaSyncResponse, StravaMatchResponse, StravaAuthResponse,
    StravaCallbackRequest, StravaCallbackResponse
)
from app.services.strava_service import StravaService
from app.api.auth import get_current_user
from app.models.strava import StravaAccount
from sqlalchemy import select

router = APIRouter(prefix="/strava", tags=["strava"])


# OPTIONS endpoints for CORS preflight
@router.options("/")
async def options_strava():
    """Handle OPTIONS request for CORS preflight"""
    return Response(status_code=200)


@router.options("/auth/url")
async def options_strava_auth_url():
    """Handle OPTIONS request for CORS preflight"""
    return Response(status_code=200)


@router.options("/auth/callback")
async def options_strava_callback():
    """Handle OPTIONS request for CORS preflight"""
    return Response(status_code=200)


@router.options("/activities")
async def options_strava_activities():
    """Handle OPTIONS request for CORS preflight"""
    return Response(status_code=200)


# Strava OAuth
@router.get("/auth/url", response_model=StravaAuthResponse)
async def get_strava_auth_url(current_user: dict = Depends(get_current_user),
                             db: Session = Depends(get_db)):
    """Get Strava OAuth authorization URL"""
    strava_service = StravaService(db)
    auth_url = strava_service.get_auth_url(current_user["user_id"])
    
    return StravaAuthResponse(
        auth_url=auth_url,
        state=str(current_user["user_id"])
    )


@router.get("/auth/callback")
async def strava_auth_callback_get(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db)
):
    """Handle Strava OAuth callback (GET request)"""
    try:
        strava_service = StravaService(db)
        result = strava_service.exchange_code_for_token(
            code=code,
            user_id=int(state)
        )
        
        # Redirect to frontend with success message
        from fastapi.responses import RedirectResponse
        return RedirectResponse(
            url=f"http://localhost:8080/auth/callback?success=true&strava_connected=true"
        )
    except Exception as e:
        # Redirect to frontend with error message
        from fastapi.responses import RedirectResponse
        return RedirectResponse(
            url=f"http://localhost:8080/auth/callback?success=false&error={str(e)}"
        )


@router.post("/auth/callback", response_model=StravaCallbackResponse)
async def strava_auth_callback(request: StravaCallbackRequest,
                              db: Session = Depends(get_db)):
    """Handle Strava OAuth callback (POST request)"""
    try:
        strava_service = StravaService(db)
        result = strava_service.exchange_code_for_token(
            code=request.code,
            user_id=int(request.state)
        )
        
        return StravaCallbackResponse(
            success=True,
            message="Strava account connected successfully",
            strava_account_id=result["strava_account_id"],
            athlete=result["athlete"]
        )
    except Exception as e:
        return StravaCallbackResponse(
            success=False,
            message=f"Failed to connect Strava account: {str(e)}"
        )


# Strava Account Management
@router.get("/account", response_model=StravaAccountResponse)
async def get_strava_account(current_user: dict = Depends(get_current_user),
                           db: Session = Depends(get_db)):
    """Get user's Strava account"""
    strava_account = db.execute(
        select(StravaAccount)
        .where(StravaAccount.user_id == current_user["user_id"])
    ).scalar_one_or_none()
    
    if not strava_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No Strava account connected"
        )
    
    return strava_account


@router.delete("/account")
async def disconnect_strava_account(current_user: dict = Depends(get_current_user),
                                  db: Session = Depends(get_db)):
    """Disconnect Strava account"""
    from app.models.strava import StravaActivity
    from sqlalchemy import func
    from datetime import date
    import logging
    
    logger = logging.getLogger(__name__)
    
    strava_account = db.execute(
        select(StravaAccount)
        .where(StravaAccount.user_id == current_user["user_id"])
    ).scalar_one_or_none()
    
    if not strava_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No Strava account connected"
        )
    
    user_id = current_user["user_id"]
    
    # Get all activity dates before deletion to recalculate daily metrics
    activity_dates = db.execute(
        select(func.date(StravaActivity.start_date).distinct())
        .where(StravaActivity.strava_account_id == strava_account.id)
    ).scalars().all()
    
    # Delete Strava account (activities will be deleted by CASCADE)
    db.delete(strava_account)
    db.commit()
    
    # Recalculate daily metrics for all dates that had activities
    # This will set TSS to 0 for days that had only Strava activities
    from app.services.daily_metrics_service import DailyMetricsService
    daily_metrics_service = DailyMetricsService(db)
    
    for activity_date in activity_dates:
        try:
            daily_metrics_service.update_daily_metrics(user_id, activity_date)
        except Exception as e:
            logger.warning(f"Failed to update daily metrics for {activity_date} after disconnect: {e}")
    
    db.commit()
    
    return {"message": "Strava account disconnected successfully"}


# Activity Synchronization
@router.post("/sync", response_model=StravaSyncResponse)
async def sync_strava_activities(request: StravaSyncRequest,
                                current_user: dict = Depends(get_current_user),
                                db: Session = Depends(get_db)):
    """Sync Strava activities"""
    try:
        strava_service = StravaService(db)
        result = strava_service.sync_user_activities(
            user_id=current_user["user_id"],
            days_back=request.days_back
        )
        
        return StravaSyncResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to sync activities: {str(e)}"
        )


@router.post("/match", response_model=StravaMatchResponse)
async def match_activities_with_workouts(current_user: dict = Depends(get_current_user),
                                        db: Session = Depends(get_db)):
    """Match Strava activities with scheduled workouts"""
    try:
        strava_service = StravaService(db)
        result = strava_service.match_activities_with_workouts(
            user_id=current_user["user_id"]
        )
        
        return StravaMatchResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to match activities: {str(e)}"
        )


# Activity Management
@router.get("/activities", response_model=List[StravaActivityResponse])
async def get_strava_activities(limit: int = Query(50, ge=1, le=200),
                               offset: int = Query(0, ge=0),
                               current_user: dict = Depends(get_current_user),
                               db: Session = Depends(get_db)):
    """Get user's Strava activities"""
    try:
        strava_service = StravaService(db)
        activities = strava_service.get_user_activities(
            user_id=current_user["user_id"],
            limit=limit,
            offset=offset
        )
        
        return activities
    except Exception as e:
        print(f"Error in get_strava_activities: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to get activities: {str(e)}"
        )


@router.get("/activities/{activity_id}", response_model=StravaActivityResponse)
async def get_strava_activity(activity_id: int,
                             current_user: dict = Depends(get_current_user),
                             db: Session = Depends(get_db)):
    """Get specific Strava activity"""
    from app.models.strava import StravaActivity
    
    # Get user's Strava account
    strava_account = db.execute(
        select(StravaAccount)
        .where(StravaAccount.user_id == current_user["user_id"])
    ).scalar_one_or_none()
    
    if not strava_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No Strava account connected"
        )
    
    # Get activity
    activity = db.execute(
        select(StravaActivity)
        .where(and_(
            StravaActivity.id == activity_id,
            StravaActivity.strava_account_id == strava_account.id
        ))
    ).scalar_one_or_none()
    
    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Activity not found"
        )
    
    return activity


@router.put("/activities/{activity_id}/sync-status")
async def update_activity_sync_status(activity_id: int,
                                     sync_status: str = Query(..., regex="^(matched|manual|ignored)$"),
                                     current_user: dict = Depends(get_current_user),
                                     db: Session = Depends(get_db)):
    """Update activity sync status"""
    from app.models.strava import StravaActivity
    from sqlalchemy import and_
    
    # Get user's Strava account
    strava_account = db.execute(
        select(StravaAccount)
        .where(StravaAccount.user_id == current_user["user_id"])
    ).scalar_one_or_none()
    
    if not strava_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No Strava account connected"
        )
    
    # Get activity
    activity = db.execute(
        select(StravaActivity)
        .where(and_(
            StravaActivity.id == activity_id,
            StravaActivity.strava_account_id == strava_account.id
        ))
    ).scalar_one_or_none()
    
    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Activity not found"
        )
    
    # Update sync status
    activity.sync_status = sync_status
    activity.is_synced = sync_status in ["matched", "manual"]
    
    db.commit()
    
    return {"message": f"Activity sync status updated to {sync_status}"}


# Webhook endpoint for Strava
@router.post("/webhook")
async def strava_webhook(request: dict, db: Session = Depends(get_db)):
    """Handle Strava webhook notifications"""
    # Verify webhook
    if request.get("verify_token") != settings.strava_webhook_verify_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook verification token"
        )
    
    # Handle subscription verification
    if request.get("hub.mode") == "subscribe":
        challenge = request.get("hub.challenge")
        verify_token = request.get("hub.verify_token")
        
        if verify_token == settings.strava_webhook_verify_token:
            return {"hub.challenge": challenge}
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid verification token"
            )
    
    # Handle activity updates
    if request.get("object_type") == "activity":
        from app.models.strava import StravaWebhook
        
        webhook = StravaWebhook(
            object_type=request.get("object_type"),
            object_id=request.get("object_id"),
            aspect_type=request.get("aspect_type"),
            event_time=request.get("event_time"),
            owner_id=request.get("owner_id"),
            subscription_id=request.get("subscription_id"),
            raw_data=request
        )
        
        db.add(webhook)
        db.commit()
        
        # Process webhook asynchronously (in production, use a task queue)
        # For now, we'll just mark it as processed
        webhook.is_processed = True
        webhook.processed_at = datetime.now()
        db.commit()
    
    return {"status": "ok"}


# Debug endpoint to manually trigger weekly summary creation
@router.post("/create-weekly-summaries")
async def create_weekly_summaries(current_user: dict = Depends(get_current_user),
                                  db: Session = Depends(get_db)):
    """Manually create weekly summaries - useful for testing"""
    try:
        from app.services.strava_service import StravaService
        strava_service = StravaService(db)
        
        summaries_created = strava_service._create_weekly_summaries(current_user["user_id"])
        
        return {
            "success": True,
            "weekly_summaries_created": summaries_created,
            "message": f"Created {summaries_created} weekly summaries"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create weekly summaries: {str(e)}"
        )


# DEBUG: Show activities in database (NO AUTH REQUIRED)
@router.get("/debug/activities")
async def debug_activities(db: Session = Depends(get_db)):
    """DEBUG ONLY - Show activities in database"""
    from app.models.strava import StravaActivity, StravaAccount
    from app.models.user import User
    
    user = db.execute(select(User)).scalar_one_or_none()
    if not user:
        return {"error": "No users found"}
    
    accounts = db.execute(
        select(StravaAccount).where(StravaAccount.user_id == user.id)
    ).scalars().all()
    
    if not accounts:
        return {"error": "No Strava accounts found"}
    
    activities = db.execute(
        select(StravaActivity)
        .where(StravaActivity.strava_account_id == accounts[0].id)
        .order_by(StravaActivity.start_date.asc())  # Oldest first
    ).scalars().all()
    
    result = []
    for act in activities:
        result.append({
            "id": act.id,
            "name": act.name,
            "start_date": act.start_date.isoformat() if act.start_date else None,
            "tss": act.tss,
            "moving_time": act.moving_time,
            "distance": act.distance
        })
    
    return {
        "user_id": user.id,
        "strava_account_id": accounts[0].id,
        "activities_found": len(activities),
        "sample_activities": result
    }


# DEBUG: Temporary endpoint without auth for testing
@router.post("/debug/create-summaries")
async def debug_create_summaries(db: Session = Depends(get_db)):
    """DEBUG ONLY - No auth required - Create weekly summaries with logging"""
    from app.services.strava_service import StravaService
    from app.models.user import User
    
    # Get first user (for debugging only)
    user = db.execute(select(User)).scalar_one_or_none()
    if not user:
        return {"error": "No users found"}
    
    strava_service = StravaService(db)
    summaries_created = strava_service._create_weekly_summaries(user.id)
    
    return {
        "success": True,
        "user_id": user.id,
        "weekly_summaries_created": summaries_created
    }


# Debug endpoint to show current CTL/ATL/TSB values
@router.get("/debug/daily-metrics")
async def debug_daily_metrics(current_user: dict = Depends(get_current_user),
                                 db: Session = Depends(get_db)):
    """Debug endpoint to see CTL/ATL/TSB values in database"""
    from app.models.daily_metrics import DailyPerformanceMetrics
    from app.services.daily_metrics_service import DailyMetricsService
    from sqlalchemy import select, and_, desc
    from datetime import date, timedelta
    
    end_date = date.today()
    start_date = end_date - timedelta(days=84)
    
    daily_metrics_service = DailyMetricsService(db)
    metrics = daily_metrics_service.get_daily_metrics(
        current_user["user_id"],
        start_date,
        end_date
    )
    
    # Get last 30 days
    recent_metrics = sorted(metrics, key=lambda m: m.metric_date, reverse=True)[:30]
    
    result = []
    for metric in recent_metrics:
        result.append({
            "date": metric.metric_date.isoformat(),
            "ctl": metric.ctl,
            "atl": metric.atl,
            "tsb": metric.tsb,
            "daily_tss": metric.daily_tss,
            "activities_count": metric.activities_count
        })
    
    return {
        "count": len(recent_metrics),
        "metrics": result
    }

@router.get("/debug/hr-streams/{activity_id}")
async def debug_hr_streams(activity_id: int,
                          current_user: dict = Depends(get_current_user),
                          db: Session = Depends(get_db)):
    """Debug endpoint to test HR streams fetching"""
    from app.models.strava import StravaActivity, StravaAccount
    from sqlalchemy import select, and_
    
    # Get the activity
    activity = db.execute(
        select(StravaActivity)
        .where(and_(
            StravaActivity.id == activity_id,
            StravaActivity.strava_account.has(StravaAccount.user_id == current_user["user_id"])
        ))
    ).scalar_one_or_none()
    
    if not activity:
        return {"error": "Activity not found"}
    
    # Get Strava account
    strava_account = db.execute(
        select(StravaAccount)
        .where(StravaAccount.id == activity.strava_account_id)
    ).scalar_one_or_none()
    
    if not strava_account:
        return {"error": "Strava account not found"}
    
    # Fetch HR streams
    try:
        from app.services.strava_service import StravaService
        strava_service = StravaService(db)
        
        streams = strava_service.fetch_activity_streams(
            strava_account=strava_account,
            activity_id=activity.strava_activity_id,
            stream_types=['heartrate', 'time']
        )
        
        hr_data = streams.get('heartrate', {}).get('data', [])
        
        return {
            "activity_id": activity_id,
            "strava_activity_id": activity.strava_activity_id,
            "activity_name": activity.name,
            "average_heartrate": activity.average_heartrate,
            "hr_data_points": len(hr_data),
            "hr_data_sample": hr_data[:10] if hr_data else [],
            "streams_available": list(streams.keys())
        }
        
    except Exception as e:
        return {"error": str(e)}

