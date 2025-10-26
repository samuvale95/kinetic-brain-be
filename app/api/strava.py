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
    strava_account = db.execute(
        select(StravaAccount)
        .where(StravaAccount.user_id == current_user["user_id"])
    ).scalar_one_or_none()
    
    if not strava_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No Strava account connected"
        )
    
    # Delete all associated activities
    from app.models.strava import StravaActivity
    db.execute(
        select(StravaActivity)
        .where(StravaActivity.strava_account_id == strava_account.id)
    ).scalars().all()
    
    # Delete Strava account
    db.delete(strava_account)
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
