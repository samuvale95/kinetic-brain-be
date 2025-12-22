from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
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
    ) -> bool:
        """
        Send a single FCM message to a device token.
        
        Args:
            token: Device token
            platform: Platform (ios, android, web)
            title: Notification title
            body: Notification body
            data: Optional data payload
            
        Returns:
            bool: True if sent successfully, False otherwise
        """
        if not self.fcm_server_key:
            logger.error("Cannot send push notification - FCM_SERVER_KEY not configured")
            return False
        
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
                        return True
                    else:
                        error = result.get("results", [{}])[0].get("error")
                        logger.warning(f"FCM error for {platform} device: {error}")
                        
                        # Check for invalid token errors
                        if error in ["InvalidRegistration", "NotRegistered"]:
                            # Token is invalid, will be marked as inactive by caller
                            logger.info(f"Token is invalid for {platform} device: {error}")
                        
                        return False
                else:
                    logger.error(f"FCM API error: {response.status_code} - {response.text}")
                    return False
        
        except httpx.TimeoutException:
            logger.error(f"Timeout sending push notification to {platform} device")
            return False
        except Exception as e:
            logger.error(f"Error sending push notification to {platform} device: {e}")
            return False
    
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
            success = await self._send_fcm_message(
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
                # Check if token might be invalid (will be handled by checking FCM error in _send_fcm_message)
                # For now, we'll mark invalid tokens based on specific error codes
                # This is a simplified approach - in production, you might want to parse FCM response
                # and mark tokens as inactive based on specific error codes
        
        logger.info(
            f"Push notification results for user {user_id}: "
            f"sent={results['sent']}, failed={results['failed']}"
        )
        
        return results

