from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from typing import List, Optional
from datetime import datetime, timezone
from app.models.notification import DeviceToken
from loguru import logger


class DeviceTokenService:
    """Service for managing device tokens for push notifications"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def register_device(
        self,
        user_id: int,
        device_token: str,
        platform: str,
        device_id: Optional[str] = None,
        app_version: Optional[str] = None
    ) -> DeviceToken:
        """
        Register or update a device token.
        
        If a device token with the same user_id, device_token, and platform exists,
        it will be updated. Otherwise, a new record is created.
        
        Args:
            user_id: User ID
            device_token: Device token string
            platform: Platform (ios, android, web)
            device_id: Optional device identifier
            app_version: Optional app version
            
        Returns:
            DeviceToken: The registered or updated device token
        """
        # Check if token already exists
        existing_token = self.db.execute(
            select(DeviceToken).where(
                and_(
                    DeviceToken.user_id == user_id,
                    DeviceToken.device_token == device_token,
                    DeviceToken.platform == platform
                )
            )
        ).scalar_one_or_none()
        
        now = datetime.now(timezone.utc)
        
        if existing_token:
            # Update existing token
            logger.info(f"Updating existing device token for user {user_id}, platform {platform}")
            existing_token.is_active = True
            existing_token.last_used_at = now
            if device_id is not None:
                existing_token.device_id = device_id
            if app_version is not None:
                existing_token.app_version = app_version
            self.db.commit()
            self.db.refresh(existing_token)
            return existing_token
        else:
            # Create new token
            logger.info(f"Registering new device token for user {user_id}, platform {platform}")
            new_token = DeviceToken(
                user_id=user_id,
                device_token=device_token,
                platform=platform,
                device_id=device_id,
                app_version=app_version,
                is_active=True,
                last_used_at=now
            )
            self.db.add(new_token)
            self.db.commit()
            self.db.refresh(new_token)
            return new_token
    
    def deactivate_device(self, user_id: int, token_id: int) -> bool:
        """
        Deactivate a device token (set is_active = false) without deleting it.
        
        Args:
            user_id: User ID (for security - ensures user owns the token)
            token_id: Device token ID to deactivate
            
        Returns:
            bool: True if token was found and deactivated, False otherwise
        """
        token = self.db.execute(
            select(DeviceToken).where(
                and_(
                    DeviceToken.id == token_id,
                    DeviceToken.user_id == user_id
                )
            )
        ).scalar_one_or_none()
        
        if not token:
            logger.warning(f"Device token {token_id} not found for user {user_id}")
            return False
        
        token.is_active = False
        self.db.commit()
        logger.info(f"Deactivated device token {token_id} for user {user_id}")
        return True
    
    def get_active_tokens(self, user_id: int) -> List[DeviceToken]:
        """
        Get all active device tokens for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List[DeviceToken]: List of active device tokens
        """
        tokens = self.db.execute(
            select(DeviceToken).where(
                and_(
                    DeviceToken.user_id == user_id,
                    DeviceToken.is_active == True
                )
            )
        ).scalars().all()
        
        return list(tokens)
    
    def mark_token_used(self, token_id: int):
        """
        Mark a token as used (update last_used_at timestamp).
        
        Args:
            token_id: Device token ID
        """
        token = self.db.execute(
            select(DeviceToken).where(DeviceToken.id == token_id)
        ).scalar_one_or_none()
        
        if token:
            token.last_used_at = datetime.now(timezone.utc)
            self.db.commit()

