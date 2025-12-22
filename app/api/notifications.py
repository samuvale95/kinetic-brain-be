from fastapi import APIRouter, Depends, HTTPException, status, Header, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date, timedelta
from app.database import get_db
from app.api.auth import get_current_user
from app.config import settings
from app.schemas.notification import (
    NotificationPreferencesResponse,
    NotificationPreferencesUpdate,
    DeviceTokenRegister,
    DeviceTokenResponse,
    NotificationSendRequest,
    NotificationSendResponse
)
from app.services.notification_service import NotificationService
from app.services.device_token_service import DeviceTokenService
from app.services.workout_reminder_service import WorkoutReminderService
from loguru import logger

router = APIRouter(prefix="/notifications", tags=["notifications"])


# OPTIONS endpoints for CORS preflight
@router.options("/register-device")
async def options_register_device():
    """Handle OPTIONS request for CORS preflight"""
    return Response(status_code=200)


@router.options("/register-device/{token_id}")
async def options_register_device_delete(token_id: int):
    """Handle OPTIONS request for CORS preflight"""
    return Response(status_code=200)


@router.post("/register-device", response_model=DeviceTokenResponse, status_code=status.HTTP_200_OK)
async def register_device(
    device_data: DeviceTokenRegister,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Register or update a device token for push notifications.
    
    If a device token with the same user_id, device_token, and platform exists,
    it will be updated. Otherwise, a new record is created.
    """
    device_token_service = DeviceTokenService(db)
    
    token = device_token_service.register_device(
        user_id=current_user["user_id"],
        device_token=device_data.device_token,
        platform=device_data.platform,
        device_id=device_data.device_id,
        app_version=device_data.app_version
    )
    
    return token


@router.delete("/register-device/{token_id}", status_code=status.HTTP_200_OK)
async def deactivate_device(
    token_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Deactivate a device token (logout or app uninstall).
    
    The token is not deleted but marked as inactive for audit trail purposes.
    """
    device_token_service = DeviceTokenService(db)
    
    success = device_token_service.deactivate_device(
        user_id=current_user["user_id"],
        token_id=token_id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device token not found or does not belong to user"
        )
    
    return {"message": "Device token disattivato"}


@router.post("/send", response_model=NotificationSendResponse, status_code=status.HTTP_200_OK)
async def send_notification(
    notification_data: NotificationSendRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Internal endpoint for sending notifications.
    
    Note: In production, this should be protected with admin authentication
    or an internal API key. For now, it requires user authentication.
    """
    notification_service = NotificationService(db)
    
    result = await notification_service.send_notification(
        user_id=notification_data.user_id,
        notification_type=notification_data.notification_type,
        title=notification_data.title,
        body=notification_data.body,
        data=notification_data.data,
        channels=notification_data.channels
    )
    
    return NotificationSendResponse(**result)


async def verify_internal_api_secret(x_internal_api_secret: Optional[str] = Header(None)):
    """
    Dependency to verify internal API secret for cron job endpoints.
    
    This protects internal endpoints from unauthorized access.
    Set INTERNAL_API_SECRET in your environment variables.
    """
    if not settings.internal_api_secret:
        logger.warning("INTERNAL_API_SECRET not configured - internal endpoints are disabled")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Internal API secret not configured"
        )
    
    if not x_internal_api_secret or x_internal_api_secret != settings.internal_api_secret:
        logger.warning(f"Invalid internal API secret provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing internal API secret"
        )
    
    return True


@router.post("/cron/send-workout-reminders", status_code=status.HTTP_200_OK)
async def send_workout_reminders_cron(
    reminder_date: Optional[str] = Query(
        None,
        description="Date to send reminders for (YYYY-MM-DD). Defaults to tomorrow."
    ),
    _verified: bool = Depends(verify_internal_api_secret),
    db: Session = Depends(get_db)
):
    """
    Internal cron endpoint to send workout reminder notifications.
    
    This endpoint is protected with an internal API secret and should be called
    by Render Cron Jobs (or similar scheduled task service) when using
    scheduled_tasks_provider="render_cron".
    
    When using scheduled_tasks_provider="apscheduler", this endpoint can still
    be called manually for testing or as a fallback.
    
    By default, sends reminders for workouts scheduled tomorrow.
    
    Example Render Cron Job configuration:
    - Schedule: 0 8 * * * (every day at 8:00 AM UTC)
    - Command: curl -X POST "https://your-app.onrender.com/notifications/cron/send-workout-reminders" -H "X-Internal-API-Secret: YOUR_SECRET"
    """
    try:
        # Parse reminder_date or use tomorrow
        if reminder_date:
            target_date = date.fromisoformat(reminder_date)
        else:
            target_date = date.today() + timedelta(days=1)
        
        logger.info(f"[CRON] Starting workout reminder job for date: {target_date}")
        
        reminder_service = WorkoutReminderService(db)
        stats = await reminder_service.send_reminders_for_date(
            reminder_date=target_date,
            only_scheduled=True
        )
        
        logger.info(f"[CRON] Workout reminder job completed: {stats}")
        
        return {
            "success": True,
            "reminder_date": target_date.isoformat(),
            "stats": stats,
            "provider": "render_cron"
        }
    
    except ValueError as e:
        logger.error(f"[CRON] Invalid date format: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format. Use YYYY-MM-DD format. Error: {e}"
        )
    except Exception as e:
        logger.exception(f"[CRON] Error in workout reminder job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error sending workout reminders: {str(e)}"
        )


@router.get("/scheduler/status", status_code=status.HTTP_200_OK)
async def get_scheduler_status(
    current_user: dict = Depends(get_current_user)
):
    """
    Get status of the scheduled tasks system.
    
    Returns information about which provider is configured and
    (if using APScheduler) the status of scheduled jobs.
    """
    from app.config import settings
    from app.services.scheduler_service import SchedulerService
    
    response = {
        "provider": settings.scheduled_tasks_provider,
        "apscheduler_enabled": SchedulerService.is_apscheduler_enabled(),
    }
    
    if SchedulerService.is_apscheduler_enabled():
        scheduler = SchedulerService.get_scheduler()
        jobs = scheduler.get_jobs()
        response["jobs"] = [
            {
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            }
            for job in jobs
        ]
    else:
        response["message"] = "Using external cron jobs (Render Cron Jobs). Configure in Render dashboard."
        response["endpoint"] = "/notifications/cron/send-workout-reminders"
    
    return response

