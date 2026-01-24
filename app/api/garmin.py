from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from fastapi.responses import Response, RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.api.auth import get_current_user
from app.services.garmin_service import GarminService
from app.schemas.garmin import (
    GarminAccountResponse,
    GarminAuthResponse,
    GarminCallbackRequest,
    GarminCallbackResponse,
    GarminActivityResponse,
    GarminSyncRequest,
    GarminSyncResponse,
)
from loguru import logger

router = APIRouter(prefix="/garmin", tags=["garmin"])


# OPTIONS endpoints for CORS preflight
@router.options("/")
async def options_garmin():
    """Handle OPTIONS request for CORS preflight"""
    return Response(status_code=200)


@router.get("/auth/url", response_model=GarminAuthResponse)
async def get_garmin_auth_url(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    redirect_uri: Optional[str] = Query(None, description="Optional redirect URI for mobile apps")
):
    """
    Get Garmin Connect OAuth authorization URL.
    
    Note: Garmin Connect uses OAuth 1.0a, which is more complex than OAuth 2.0.
    This endpoint initiates the OAuth flow.
    """
    garmin_service = GarminService(db)
    auth_url = garmin_service.get_auth_url(
        current_user["user_id"],
        redirect_uri=redirect_uri
    )
    
    return GarminAuthResponse(
        auth_url=auth_url,
        state=str(current_user["user_id"])
    )


@router.get("/auth/callback")
async def garmin_auth_callback(
    code: str = Query(...),
    state: str = Query(...),
    oauth_token: Optional[str] = Query(None),
    oauth_verifier: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Handle Garmin Connect OAuth callback.
    
    Note: Garmin Connect OAuth 1.0a flow requires oauth_token and oauth_verifier.
    """
    try:
        user_id = int(state)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state parameter"
        )
    
    garmin_service = GarminService(db)
    
    try:
        # Handle OAuth callback
        if oauth_token and oauth_verifier:
            account = garmin_service.handle_callback(user_id, oauth_token, oauth_verifier)
            logger.info(f"[GARMIN] Successfully connected account for user {user_id}")
            
            # Redirect to frontend
            from app.config import settings
            return RedirectResponse(
                url=f"{settings.frontend_url}/settings?garmin=connected"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing OAuth parameters"
            )
    except Exception as e:
        logger.error(f"[GARMIN] Error in callback for user {user_id}: {e}")
        from app.config import settings
        return RedirectResponse(
            url=f"{settings.frontend_url}/settings?garmin=error&message={str(e)}"
        )


@router.get("/account", response_model=GarminAccountResponse)
async def get_garmin_account(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get connected Garmin account"""
    garmin_service = GarminService(db)
    account = garmin_service.get_account(current_user["user_id"])
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Garmin account not connected"
        )
    
    return account


@router.post("/sync", response_model=GarminSyncResponse)
async def sync_garmin_activities(
    request: GarminSyncRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Sync activities from Garmin Connect.
    
    This endpoint triggers a sync of activities from the user's Garmin Connect account.
    Can be run in background for large syncs.
    """
    garmin_service = GarminService(db)
    
    try:
        result = await garmin_service.sync_activities(
            user_id=current_user["user_id"],
            days_back=request.days_back or 7,
            force_full=request.force_full or False
        )
        
        return GarminSyncResponse(
            success=True,
            synced_count=result["synced_count"],
            message=result["message"]
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"[GARMIN] Error syncing activities for user {current_user['user_id']}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error syncing activities: {str(e)}"
        )


@router.get("/activities", response_model=list[GarminActivityResponse])
async def get_garmin_activities(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get synced Garmin activities"""
    garmin_service = GarminService(db)
    activities = garmin_service.get_activities(
        user_id=current_user["user_id"],
        limit=limit,
        offset=offset
    )
    
    return activities


@router.delete("/account")
async def disconnect_garmin(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Disconnect Garmin Connect account"""
    garmin_service = GarminService(db)
    
    success = garmin_service.disconnect_account(current_user["user_id"])
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Garmin account not found"
        )
    
    return {"message": "Garmin account disconnected successfully"}


@router.patch("/account/auto-sync")
async def update_auto_sync(
    enabled: bool = Query(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update auto-sync setting for Garmin account"""
    garmin_service = GarminService(db)
    
    success = garmin_service.update_auto_sync(
        user_id=current_user["user_id"],
        enabled=enabled
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Garmin account not found"
        )
    
    return {"message": f"Auto-sync {'enabled' if enabled else 'disabled'}"}
