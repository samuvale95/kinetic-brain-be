from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from app.models.notification import NotificationPreferences
from loguru import logger


class NotificationService:
    """Service for managing notification preferences and sending notifications"""
    
    # Mapping from notification_type to preference field name
    NOTIFICATION_TYPE_MAP = {
        "workout_reminder": "workout_reminders",
        "new_workout": "new_workout",
        "workout_completed": "workout_completed",
        "plan_updates": "plan_updates",
        "weekly_generation": "weekly_generation",
    }
    
    def __init__(self, db: Session):
        self.db = db
    
    def _get_preference_field_name(self, notification_type: str, channel: str) -> str:
        """
        Get the preference field name for a notification type and channel.
        
        Args:
            notification_type: Type of notification (e.g., "workout_reminder")
            channel: Channel (e.g., "email" or "push")
            
        Returns:
            str: Field name (e.g., "email_workout_reminders")
        """
        type_suffix = self.NOTIFICATION_TYPE_MAP.get(notification_type)
        if not type_suffix:
            raise ValueError(f"Unknown notification type: {notification_type}")
        
        return f"{channel}_{type_suffix}"
    
    def get_preferences(self, user_id: int) -> NotificationPreferences:
        """
        Get notification preferences for a user.
        Creates default preferences if they don't exist.
        
        Args:
            user_id: User ID
            
        Returns:
            NotificationPreferences: User's notification preferences
        """
        prefs = self.db.execute(
            select(NotificationPreferences).where(
                NotificationPreferences.user_id == user_id
            )
        ).scalar_one_or_none()
        
        if not prefs:
            # Create default preferences
            logger.info(f"Creating default notification preferences for user {user_id}")
            prefs = NotificationPreferences(
                user_id=user_id,
                email_enabled=True,
                email_workout_reminders=True,
                email_new_workout=True,
                email_workout_completed=True,
                email_plan_updates=True,
                email_weekly_generation=True,
                push_enabled=True,
                push_workout_reminders=True,
                push_new_workout=True,
                push_workout_completed=True,
                push_plan_updates=True,
                push_weekly_generation=True,
            )
            self.db.add(prefs)
            self.db.commit()
            self.db.refresh(prefs)
        
        return prefs
    
    def update_preferences(
        self,
        user_id: int,
        update_data: Dict[str, Any]
    ) -> NotificationPreferences:
        """
        Update notification preferences for a user.
        Only updates fields that are provided in update_data.
        
        Args:
            user_id: User ID
            update_data: Dictionary with fields to update (all optional)
            
        Returns:
            NotificationPreferences: Updated notification preferences
        """
        prefs = self.get_preferences(user_id)
        
        # Update only provided fields
        for key, value in update_data.items():
            if hasattr(prefs, key) and value is not None:
                setattr(prefs, key, value)
        
        prefs.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(prefs)
        
        logger.info(f"Updated notification preferences for user {user_id}")
        return prefs
    
    def can_send_notification(
        self,
        user_id: int,
        notification_type: str,
        channel: str
    ) -> bool:
        """
        Check if a notification can be sent to a user for a specific type and channel.
        
        Checks both the master switch ({channel}_enabled) and the specific preference
        ({channel}_{notification_type}).
        
        Args:
            user_id: User ID
            notification_type: Type of notification (e.g., "workout_reminder")
            channel: Channel ("email" or "push")
            
        Returns:
            bool: True if notification can be sent, False otherwise
        """
        prefs = self.get_preferences(user_id)
        
        # Check master switch
        channel_enabled = getattr(prefs, f"{channel}_enabled", False)
        if not channel_enabled:
            return False
        
        # Check specific preference
        preference_field = self._get_preference_field_name(notification_type, channel)
        type_preference = getattr(prefs, preference_field, False)
        
        return type_preference
    
    async def send_notification(
        self,
        user_id: int,
        notification_type: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        channels: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Send a notification to a user via specified channels.
        Respects user preferences - only sends if both master switch and specific preference are enabled.
        
        Args:
            user_id: User ID
            notification_type: Type of notification
            title: Notification title
            body: Notification body/message
            data: Optional additional data payload
            channels: List of channels to use (["email", "push"]). If None, uses user preferences.
            
        Returns:
            Dict with "sent", "skipped", and "reason" for each channel
        """
        if channels is None:
            channels = ["email", "push"]
        
        result = {
            "sent": {},
            "skipped": {},
            "reason": {}
        }
        
        # Check preferences for each channel
        for channel in channels:
            if channel not in ["email", "push"]:
                logger.warning(f"Unknown channel: {channel}")
                result["sent"][channel] = False
                result["skipped"][channel] = True
                result["reason"][channel] = f"Unknown channel: {channel}"
                continue
            
            can_send = self.can_send_notification(user_id, notification_type, channel)
            
            if not can_send:
                result["sent"][channel] = False
                result["skipped"][channel] = True
                result["reason"][channel] = f"User has disabled {notification_type} notifications for {channel}"
                logger.info(f"Skipping {channel} notification for user {user_id} - preference disabled")
                continue
            
            # Send notification
            try:
                if channel == "email":
                    from app.services.email_service import EmailService
                    from app.models.user import User
                    
                    # Get user email
                    user = self.db.execute(
                        select(User).where(User.id == user_id)
                    ).scalar_one_or_none()
                    
                    if not user:
                        result["sent"][channel] = False
                        result["skipped"][channel] = True
                        result["reason"][channel] = "User not found"
                        continue
                    
                    email_service = EmailService(self.db)
                    await email_service.send_notification_email(
                        user_email=user.email,
                        user_name=user.name,
                        title=title,
                        body=body,
                        notification_type=notification_type,
                        data=data
                    )
                    result["sent"][channel] = True
                    result["skipped"][channel] = False
                    result["reason"][channel] = None
                    logger.info(f"Sent email notification to user {user_id}")
                
                elif channel == "push":
                    from app.services.push_service import PushService
                    
                    push_service = PushService(self.db)
                    await push_service.send_push(
                        user_id=user_id,
                        title=title,
                        body=body,
                        data=data
                    )
                    result["sent"][channel] = True
                    result["skipped"][channel] = False
                    result["reason"][channel] = None
                    logger.info(f"Sent push notification to user {user_id}")
            
            except Exception as e:
                logger.error(f"Error sending {channel} notification to user {user_id}: {e}")
                result["sent"][channel] = False
                result["skipped"][channel] = True
                result["reason"][channel] = str(e)
        
        return result

