from sqlalchemy.orm import Session
from sqlalchemy import select, and_, desc
from typing import Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from app.models.garmin import GarminAccount, GarminActivity
from app.models.workout import Workout, WorkoutSession
from loguru import logger
import requests
from urllib.parse import urlencode


class GarminService:
    """Service for Garmin Connect integration"""
    
    # Garmin Connect API endpoints (OAuth 1.0a)
    OAUTH_REQUEST_TOKEN_URL = "https://connect.garmin.com/oauth-service/oauth/preauthorized"
    OAUTH_AUTHORIZE_URL = "https://connect.garmin.com/oauthConfirm"
    OAUTH_ACCESS_TOKEN_URL = "https://connect.garmin.com/oauth-service/oauth/exchange/user/2.0"
    API_BASE_URL = "https://connectapi.garmin.com"
    
    def __init__(self, db: Session):
        self.db = db
        # Note: Garmin Connect API requires OAuth 1.0a which is more complex
        # This is a simplified implementation - full OAuth 1.0a requires additional libraries
    
    def get_auth_url(self, user_id: int, redirect_uri: Optional[str] = None) -> str:
        """
        Get Garmin Connect OAuth authorization URL.
        
        Note: Garmin Connect uses OAuth 1.0a, which requires:
        1. Request token
        2. User authorization
        3. Access token exchange
        
        This is a simplified version - full implementation would require
        OAuth 1.0a library like requests-oauthlib.
        """
        from app.config import settings
        
        # For now, return a placeholder URL
        # Full implementation would:
        # 1. Get request token from Garmin
        # 2. Store token/secret temporarily
        # 3. Return authorization URL with callback
        
        if not redirect_uri:
            redirect_uri = f"{settings.frontend_url}/settings?garmin=connected"
        
        # Simplified OAuth flow (would need proper OAuth 1.0a implementation)
        params = {
            "oauth_callback": redirect_uri,
            "user_id": str(user_id),
        }
        
        # In production, this would make actual OAuth 1.0a request
        auth_url = f"{self.OAUTH_AUTHORIZE_URL}?{urlencode(params)}"
        
        logger.info(f"[GARMIN] Generated auth URL for user {user_id}")
        return auth_url
    
    def handle_callback(
        self,
        user_id: int,
        oauth_token: str,
        oauth_verifier: str
    ) -> GarminAccount:
        """
        Handle OAuth callback and create/update Garmin account.
        
        Note: This is a simplified version. Full OAuth 1.0a implementation
        would exchange the verifier for access tokens.
        """
        # Check if account already exists
        account = self.db.execute(
            select(GarminAccount)
            .where(GarminAccount.user_id == user_id)
        ).scalar_one_or_none()
        
        if account:
            # Update existing account
            account.oauth_token = oauth_token
            account.is_active = True
            account.disconnected_at = None
            account.updated_at = datetime.now(timezone.utc)
        else:
            # Create new account
            account = GarminAccount(
                user_id=user_id,
                oauth_token=oauth_token,
                is_active=True,
                connected_at=datetime.now(timezone.utc)
            )
            self.db.add(account)
        
        self.db.commit()
        self.db.refresh(account)
        
        logger.info(f"[GARMIN] Connected account for user {user_id}")
        return account
    
    def get_account(self, user_id: int) -> Optional[GarminAccount]:
        """Get Garmin account for user"""
        return self.db.execute(
            select(GarminAccount)
            .where(
                and_(
                    GarminAccount.user_id == user_id,
                    GarminAccount.is_active == True
                )
            )
        ).scalar_one_or_none()
    
    async def sync_activities(
        self,
        user_id: int,
        days_back: int = 7,
        force_full: bool = False
    ) -> Dict[str, Any]:
        """
        Sync activities from Garmin Connect.
        
        Note: This is a placeholder implementation.
        Full implementation would:
        1. Authenticate with Garmin API using OAuth tokens
        2. Fetch activities from Garmin Connect API
        3. Parse and store activities
        4. Match with existing workouts
        """
        account = self.get_account(user_id)
        if not account:
            raise ValueError("Garmin account not connected")
        
        if not account.oauth_token:
            raise ValueError("Garmin account not properly authenticated")
        
        # Placeholder: In production, this would:
        # 1. Make authenticated request to Garmin API
        # 2. Fetch activities
        # 3. Store in GarminActivity table
        # 4. Attempt to match with workouts
        
        synced_count = 0
        
        # Example API call (would need proper OAuth 1.0a signing):
        # activities = await self._fetch_garmin_activities(account, days_back)
        # for activity_data in activities:
        #     activity = self._create_activity_from_garmin(user_id, account.id, activity_data)
        #     self._try_match_workout(activity)
        #     synced_count += 1
        
        account.last_sync_at = datetime.now(timezone.utc)
        self.db.commit()
        
        logger.info(f"[GARMIN] Synced {synced_count} activities for user {user_id}")
        
        return {
            "synced_count": synced_count,
            "message": f"Synced {synced_count} activities from Garmin Connect"
        }
    
    def disconnect_account(self, user_id: int) -> bool:
        """Disconnect Garmin account"""
        account = self.get_account(user_id)
        if not account:
            return False
        
        account.is_active = False
        account.disconnected_at = datetime.now(timezone.utc)
        account.oauth_token = None
        account.oauth_token_secret = None
        account.access_token = None
        account.refresh_token = None
        
        self.db.commit()
        
        logger.info(f"[GARMIN] Disconnected account for user {user_id}")
        return True
    
    def get_activities(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[GarminActivity]:
        """Get synced Garmin activities for user"""
        return list(self.db.execute(
            select(GarminActivity)
            .where(GarminActivity.user_id == user_id)
            .order_by(desc(GarminActivity.start_time))
            .limit(limit)
            .offset(offset)
        ).scalars().all())
    
    def update_auto_sync(self, user_id: int, enabled: bool) -> bool:
        """Update auto-sync setting"""
        account = self.get_account(user_id)
        if not account:
            return False
        
        account.auto_sync_enabled = enabled
        self.db.commit()
        
        return True
