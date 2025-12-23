from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List, Tuple
from app.services.device_token_service import DeviceTokenService
from app.config import settings
from loguru import logger
import httpx
import json
from google.oauth2 import service_account
from google.auth.transport import requests as google_requests


class PushService:
    """Service for sending push notifications via Firebase Cloud Messaging (FCM) API V1"""
    
    def __init__(self, db: Session):
        self.db = db
        self.fcm_project_id = settings.fcm_project_id
        self.fcm_service_account_json = settings.fcm_service_account_json
        self.device_token_service = DeviceTokenService(db)
        self._credentials = None
        self._access_token = None
        
        if not self.fcm_project_id or not self.fcm_service_account_json:
            logger.warning("FCM_PROJECT_ID or FCM_SERVICE_ACCOUNT_JSON not configured - push notifications will not work")
        else:
            self._initialize_credentials()
    
    def _initialize_credentials(self):
        """Initialize Google OAuth2 credentials from service account JSON"""
        try:
            # Parse service account JSON (can be a JSON string or dict)
            if isinstance(self.fcm_service_account_json, str):
                service_account_info = json.loads(self.fcm_service_account_json)
            else:
                service_account_info = self.fcm_service_account_json
            
            # Create credentials from service account info
            self._credentials = service_account.Credentials.from_service_account_info(
                service_account_info,
                scopes=['https://www.googleapis.com/auth/firebase.messaging']
            )
            logger.info("FCM credentials initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize FCM credentials: {e}")
            self._credentials = None
    
    async def _get_access_token(self) -> Optional[str]:
        """Get OAuth2 access token, refreshing if necessary"""
        if not self._credentials:
            return None
        
        try:
            # Refresh token if expired (using sync Request since credentials are sync)
            # Note: google-auth credentials are thread-safe but not async-native
            # We use run_in_executor would be ideal, but for simplicity we use sync refresh
            if not self._credentials.valid:
                request = google_requests.Request()
                self._credentials.refresh(request)
            
            return self._credentials.token
        except Exception as e:
            logger.error(f"Failed to get FCM access token: {e}")
            return None
    
    def _get_fcm_headers(self, access_token: str) -> Dict[str, str]:
        """Get headers for FCM API V1 requests"""
        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    
    def _get_fcm_api_url(self) -> str:
        """Get FCM API V1 endpoint URL"""
        return f"https://fcm.googleapis.com/v1/projects/{self.fcm_project_id}/messages:send"
    
    async def _send_fcm_message(
        self,
        token: str,
        platform: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Send a single FCM message to a device token using FCM API V1.
        
        Args:
            token: Device token
            platform: Platform (ios, android, web)
            title: Notification title
            body: Notification body
            data: Optional data payload
            
        Returns:
            Tuple of (success: bool, error_code: Optional[str])
            error_code will be one of: "INVALID_ARGUMENT", "UNREGISTERED", "PERMISSION_DENIED"
            if the token is invalid and should be deactivated
        """
        if not self.fcm_project_id or not self._credentials:
            logger.error("Cannot send push notification - FCM not configured")
            return False, None
        
        # Get OAuth2 access token
        access_token = await self._get_access_token()
        if not access_token:
            logger.error("Cannot send push notification - failed to get access token")
            return False, None
        
        # Prepare FCM V1 message payload
        message = {
            "token": token,
            "notification": {
                "title": title,
                "body": body
            }
        }
        
        # Add data payload if provided
        if data:
            message["data"] = {str(k): str(v) for k, v in data.items()}  # FCM requires string values
        
        # Platform-specific settings
        if platform == "ios":
            message["apns"] = {
                "payload": {
                    "aps": {
                        "alert": {
                            "title": title,
                            "body": body
                        },
                        "sound": "default",
                        "badge": 1
                    }
                }
            }
        elif platform == "android":
            message["android"] = {
                "priority": "high",
                "notification": {
                    "title": title,
                    "body": body,
                    "sound": "default",
                    "channel_id": "default"
                }
            }
        
        # FCM V1 API payload format
        fcm_payload = {
            "message": message
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self._get_fcm_api_url(),
                    json=fcm_payload,
                    headers=self._get_fcm_headers(access_token)
                )
                
                if response.status_code == 200:
                    logger.info(f"Push notification sent successfully to {platform} device")
                    return True, None
                else:
                    error_data = response.json()
                    error_code = error_data.get("error", {}).get("code")
                    error_message = error_data.get("error", {}).get("message", "")
                    
                    logger.warning(f"FCM error for {platform} device: {error_code} - {error_message}")
                    
                    # Check for invalid token errors that should result in deactivation
                    # FCM V1 uses different error codes than Legacy API
                    invalid_token_errors = [
                        "INVALID_ARGUMENT",  # Invalid token format
                        "UNREGISTERED",  # Token not registered
                        "PERMISSION_DENIED"  # Token from different project
                    ]
                    
                    if error_code in invalid_token_errors:
                        logger.info(f"Token is invalid for {platform} device (error: {error_code}), should be deactivated")
                        return False, error_code
                    else:
                        # Other errors (like "UNAVAILABLE", "INTERNAL") are temporary
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
        if not self.fcm_project_id or not self._credentials:
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
                
                # If token is invalid (INVALID_ARGUMENT, UNREGISTERED, PERMISSION_DENIED),
                # mark it as inactive
                invalid_token_errors = ["INVALID_ARGUMENT", "UNREGISTERED", "PERMISSION_DENIED"]
                if error_code in invalid_token_errors:
                    logger.info(f"Deactivating invalid token {token_obj.id} for user {user_id} (error: {error_code})")
                    self.device_token_service.deactivate_device(user_id, token_obj.id)
                    results["invalid_tokens"].append(token_obj.id)
        
        logger.info(
            f"Push notification results for user {user_id}: "
            f"sent={results['sent']}, failed={results['failed']}"
        )
        
        return results

