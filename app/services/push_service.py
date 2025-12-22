from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List, Tuple
from app.services.device_token_service import DeviceTokenService
from app.config import settings
from loguru import logger
import httpx


class PushService:
    """Service for sending push notifications via Firebase Cloud Messaging (FCM)"""
    
    FCM_API_URL = "https://fcm.googleapis.com/fcm/send"
    
    def __init__(self, db: Session):
        self.db = db
        self.fcm_server_key = settings.fcm_server_key
        self.device_token_service = DeviceTokenService(db)
        
        if not self.fcm_server_key:
            logger.warning("FCM_SERVER_KEY not configured - push notifications will not work")
    
    def _get_fcm_headers(self) -> Dict[str, str]:
        """Get headers for FCM API requests"""
        return {
            "Authorization": f"key={self.fcm_server_key}",
            "Content-Type": "application/json"
        }
    
    async def _send_fcm_message(
        self,
        token: str,
        platform: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Send a single FCM message to a device token.
        
        Args:
            token: Device token
            platform: Platform (ios, android, web)
            title: Notification title
            body: Notification body
            data: Optional data payload
            
        Returns:
            Tuple of (success: bool, error_code: Optional[str])
            error_code will be one of: "InvalidRegistration", "NotRegistered", "MismatchSenderId"
            if the token is invalid and should be deactivated
        """
        if not self.fcm_server_key:
            logger.error("Cannot send push notification - FCM_SERVER_KEY not configured")
            return False, None
        
        # Prepare notification payload
        notification_payload = {
            "to": token,
            "notification": {
                "title": title,
                "body": body,
                "sound": "default",
            },
        }
        
        # Add data payload if provided
        if data:
            notification_payload["data"] = data
        
        # Platform-specific settings
        if platform == "ios":
            # iOS-specific APNs configuration
            notification_payload["notification"]["sound"] = "default"
            notification_payload["apns"] = {
                "payload": {
                    "aps": {
                        "sound": "default",
                        "badge": 1
                    }
                }
            }
        elif platform == "android":
            # Android-specific settings
            notification_payload["priority"] = "high"
            notification_payload["android"] = {
                "priority": "high",
                "notification": {
                    "sound": "default",
                    "channel_id": "default"
                }
            }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.FCM_API_URL,
                    json=notification_payload,
                    headers=self._get_fcm_headers()
                )
                
                if response.status_code == 200:
                    result = response.json()
                    # Check if message was sent successfully
                    if result.get("success") == 1:
                        logger.info(f"Push notification sent successfully to {platform} device")
                        return True, None
                    else:
                        # FCM v1 API returns results array
                        results = result.get("results", [])
                        if results:
                            error_code = results[0].get("error")
                            logger.warning(f"FCM error for {platform} device: {error_code}")
                            
                            # Check for invalid token errors that should result in deactivation
                            invalid_token_errors = ["InvalidRegistration", "NotRegistered", "MismatchSenderId"]
                            if error_code in invalid_token_errors:
                                logger.info(f"Token is invalid for {platform} device (error: {error_code}), should be deactivated")
                                return False, error_code
                            else:
                                # Other errors (like "Unavailable", "InternalServerError") are temporary
                                return False, None
                        else:
                            logger.warning(f"FCM returned failure but no error details for {platform} device")
                            return False, None
                else:
                    logger.error(f"FCM API error: {response.status_code} - {response.text}")
                    return False, None
        
        except httpx.TimeoutException:
            logger.error(f"Timeout sending push notification to {platform} device")
            return False, None
        except Exception as e:
            logger.error(f"Error sending push notification to {platform} device: {e}")
            return False, None
    
    async def send_push(
        self,
        user_id: int,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send push notification to all active device tokens for a user.
        
        Args:
            user_id: User ID
            title: Notification title
            body: Notification body
            data: Optional data payload
            
        Returns:
            Dict with results: {"sent": int, "failed": int, "invalid_tokens": List[int]}
        """
        if not self.fcm_server_key:
            logger.warning(f"Cannot send push notification to user {user_id} - FCM not configured")
            return {"sent": 0, "failed": 0, "invalid_tokens": []}
        
        # Get all active tokens for user
        tokens = self.device_token_service.get_active_tokens(user_id)
        
        if not tokens:
            logger.info(f"No active device tokens found for user {user_id}")
            return {"sent": 0, "failed": 0, "invalid_tokens": []}
        
        results = {
            "sent": 0,
            "failed": 0,
            "invalid_tokens": []
        }
        
        # Send to each token
        for token_obj in tokens:
            success, error_code = await self._send_fcm_message(
                token=token_obj.device_token,
                platform=token_obj.platform,
                title=title,
                body=body,
                data=data
            )
            
            if success:
                results["sent"] += 1
                # Update last_used_at timestamp
                self.device_token_service.mark_token_used(token_obj.id)
            else:
                results["failed"] += 1
                
                # If token is invalid (InvalidRegistration, NotRegistered, MismatchSenderId),
                # mark it as inactive
                if error_code in ["InvalidRegistration", "NotRegistered", "MismatchSenderId"]:
                    logger.info(f"Deactivating invalid token {token_obj.id} for user {user_id} (error: {error_code})")
                    self.device_token_service.deactivate_device(user_id, token_obj.id)
                    results["invalid_tokens"].append(token_obj.id)
        
        logger.info(
            f"Push notification results for user {user_id}: "
            f"sent={results['sent']}, failed={results['failed']}"
        )
        
        return results

