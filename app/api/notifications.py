from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.api.auth import get_current_user
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

