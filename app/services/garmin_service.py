from sqlalchemy.orm import Session
from sqlalchemy import select, and_, desc
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
from app.models.garmin import GarminAccount, GarminActivity
from app.models.workout import Workout, WorkoutSession
from loguru import logger
import requests
from urllib.parse import urlencode, parse_qs
from requests_oauthlib import OAuth1Session
import json


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
    
    def get_auth_url(self, user_id: int, redirect_uri: Optional[str] = None) -> Dict[str, Any]:
        """
        Get Garmin Connect OAuth authorization URL using OAuth 1.0a.
        
        Returns:
            Dict with 'auth_url' and 'oauth_token_secret' (to store temporarily)
        """
        from app.config import settings
        
        if not redirect_uri:
            redirect_uri = f"{settings.frontend_url}/settings?garmin=connected"
        
        # Get OAuth credentials from settings
        consumer_key = getattr(settings, 'GARMIN_CONSUMER_KEY', None)
        consumer_secret = getattr(settings, 'GARMIN_CONSUMER_SECRET', None)
        
        if not consumer_key or not consumer_secret:
            raise ValueError("Garmin OAuth credentials not configured. Set GARMIN_CONSUMER_KEY and GARMIN_CONSUMER_SECRET")
        
        try:
            # Step 1: Get request token
            oauth = OAuth1Session(
                consumer_key,
                client_secret=consumer_secret,
                callback_uri=redirect_uri
            )
            
            # Garmin uses a preauthorized token endpoint
            # Note: Garmin's OAuth flow may vary - this is a simplified version
            request_token_url = self.OAUTH_REQUEST_TOKEN_URL
            
            # For Garmin, we might need to use a different endpoint
            # Some implementations use: https://connect.garmin.com/oauth-service/oauth/preauthorized?ticket=...
            # This is a placeholder - actual Garmin OAuth may require different flow
            
            fetch_response = oauth.fetch_request_token(request_token_url)
            
            oauth_token = fetch_response.get('oauth_token')
            oauth_token_secret = fetch_response.get('oauth_token_secret')
            
            if not oauth_token:
                raise ValueError("Failed to get OAuth request token from Garmin")
            
            # Step 2: Build authorization URL
            authorization_url = oauth.authorization_url(self.OAUTH_AUTHORIZE_URL)
            
            # Store oauth_token_secret temporarily (in session or database)
            # For now, we'll return it to be stored by the caller
            
            logger.info(f"[GARMIN] Generated auth URL for user {user_id}")
            
            return {
                "auth_url": authorization_url,
                "oauth_token": oauth_token,
                "oauth_token_secret": oauth_token_secret,
            }
        except Exception as e:
            logger.error(f"[GARMIN] Error getting auth URL: {e}")
            # Fallback: return a basic URL structure
            # Note: Garmin OAuth 1.0a implementation may require specific endpoints
            return {
                "auth_url": f"{self.OAUTH_AUTHORIZE_URL}?oauth_callback={redirect_uri}",
                "oauth_token": None,
                "oauth_token_secret": None,
                "error": str(e)
            }
    
    def handle_callback(
        self,
        user_id: int,
        oauth_token: str,
        oauth_verifier: str,
        oauth_token_secret: Optional[str] = None
    ) -> GarminAccount:
        """
        Handle OAuth callback and exchange verifier for access tokens.
        Creates or updates Garmin account with access tokens.
        """
        from app.config import settings
        
        consumer_key = getattr(settings, 'GARMIN_CONSUMER_KEY', None)
        consumer_secret = getattr(settings, 'GARMIN_CONSUMER_SECRET', None)
        
        if not consumer_key or not consumer_secret:
            raise ValueError("Garmin OAuth credentials not configured")
        
        try:
            # Step 3: Exchange verifier for access token
            oauth = OAuth1Session(
                consumer_key,
                client_secret=consumer_secret,
                resource_owner_key=oauth_token,
                resource_owner_secret=oauth_token_secret or ""
            )
            
            # Exchange verifier for access token
            oauth_response = oauth.fetch_access_token(self.OAUTH_ACCESS_TOKEN_URL, verifier=oauth_verifier)
            
            access_token = oauth_response.get('oauth_token')
            access_token_secret = oauth_response.get('oauth_token_secret')
            
            if not access_token:
                raise ValueError("Failed to get access token from Garmin")
            
            # Check if account already exists
            account = self.db.execute(
                select(GarminAccount)
                .where(GarminAccount.user_id == user_id)
            ).scalar_one_or_none()
            
            if account:
                # Update existing account
                account.oauth_token = oauth_token
                account.oauth_token_secret = oauth_token_secret
                account.access_token = access_token
                account.access_token_secret = access_token_secret
                account.is_active = True
                account.disconnected_at = None
                account.updated_at = datetime.now(timezone.utc)
            else:
                # Create new account
                account = GarminAccount(
                    user_id=user_id,
                    oauth_token=oauth_token,
                    oauth_token_secret=oauth_token_secret,
                    access_token=access_token,
                    access_token_secret=access_token_secret,
                    is_active=True,
                    connected_at=datetime.now(timezone.utc)
                )
                self.db.add(account)
            
            self.db.commit()
            self.db.refresh(account)
            
            logger.info(f"[GARMIN] Connected account for user {user_id}")
            return account
        except Exception as e:
            logger.error(f"[GARMIN] Error handling callback: {e}")
            raise
    
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
        Sync activities from Garmin Connect API.
        
        Fetches activities from Garmin Connect and stores them in the database.
        Attempts to match activities with existing workouts.
        """
        from app.config import settings
        
        account = self.get_account(user_id)
        if not account:
            raise ValueError("Garmin account not connected")
        
        if not account.access_token or not account.access_token_secret:
            raise ValueError("Garmin account not properly authenticated")
        
        consumer_key = getattr(settings, 'GARMIN_CONSUMER_KEY', None)
        consumer_secret = getattr(settings, 'GARMIN_CONSUMER_SECRET', None)
        
        if not consumer_key or not consumer_secret:
            raise ValueError("Garmin OAuth credentials not configured")
        
        try:
            # Create OAuth session with access tokens
            oauth = OAuth1Session(
                consumer_key,
                client_secret=consumer_secret,
                resource_owner_key=account.access_token,
                resource_owner_secret=account.access_token_secret
            )
            
            # Fetch activities from Garmin Connect API
            # Note: Garmin API endpoint may vary - this is a common pattern
            start_date = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime('%Y-%m-%d')
            end_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
            
            # Garmin Connect API endpoint for activities
            # Actual endpoint may be: /activity-service/activity/searchActivities
            activities_url = f"{self.API_BASE_URL}/activity-service/activity/searchActivities"
            
            params = {
                'startDate': start_date,
                'endDate': end_date,
                'limit': 100
            }
            
            response = oauth.get(activities_url, params=params)
            response.raise_for_status()
            
            activities_data = response.json()
            
            # Parse and store activities
            synced_count = 0
            matched_count = 0
            
            # Garmin API response structure may vary
            activities_list = activities_data.get('activities', []) if isinstance(activities_data, dict) else activities_data
            
            for activity_data in activities_list:
                try:
                    # Create or update GarminActivity
                    garmin_activity_id = activity_data.get('activityId') or activity_data.get('id')
                    
                    if not garmin_activity_id:
                        continue
                    
                    # Check if activity already exists
                    existing = self.db.execute(
                        select(GarminActivity)
                        .where(
                            and_(
                                GarminActivity.garmin_activity_id == str(garmin_activity_id),
                                GarminActivity.user_id == user_id
                            )
                        )
                    ).scalar_one_or_none()
                    
                    if existing and not force_full:
                        continue  # Skip if already synced
                    
                    # Parse activity data
                    start_time_str = activity_data.get('startTimeGMT') or activity_data.get('startTime')
                    start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00')) if start_time_str else datetime.now(timezone.utc)
                    
                    activity = existing or GarminActivity(
                        user_id=user_id,
                        garmin_account_id=account.id,
                        garmin_activity_id=str(garmin_activity_id),
                        activity_type=activity_data.get('activityType', {}).get('typeKey', 'running'),
                        start_time=start_time,
                        duration_seconds=activity_data.get('duration', 0),
                        distance_meters=activity_data.get('distance', 0),
                        calories=activity_data.get('calories', 0),
                        avg_heart_rate=activity_data.get('averageHR', 0),
                        max_heart_rate=activity_data.get('maxHR', 0),
                        avg_pace=activity_data.get('averageSpeed', 0),
                        elevation_gain=activity_data.get('elevationGain', 0),
                        raw_data=json.dumps(activity_data)
                    )
                    
                    if not existing:
                        self.db.add(activity)
                    
                    # Try to match with existing workout
                    matched_workout = self._try_match_workout(activity, user_id)
                    if matched_workout:
                        activity.workout_id = matched_workout.id
                        matched_count += 1
                    
                    synced_count += 1
                except Exception as e:
                    logger.warning(f"[GARMIN] Error processing activity: {e}")
                    continue
            
            account.last_sync_at = datetime.now(timezone.utc)
            self.db.commit()
            
            logger.info(f"[GARMIN] Synced {synced_count} activities for user {user_id}, matched {matched_count}")
            
            return {
                "synced_count": synced_count,
                "matched_count": matched_count,
                "message": f"Synced {synced_count} activities from Garmin Connect ({matched_count} matched)"
            }
        except Exception as e:
            logger.error(f"[GARMIN] Error syncing activities: {e}")
            raise
    
    def _try_match_workout(self, activity: GarminActivity, user_id: int) -> Optional[Workout]:
        """Try to match Garmin activity with existing workout"""
        # Match by date (same day)
        activity_date = activity.start_time.date()
        
        workout = self.db.execute(
            select(Workout)
            .where(
                and_(
                    Workout.user_id == user_id,
                    Workout.scheduled_date >= datetime.combine(activity_date, datetime.min.time(), tzinfo=timezone.utc),
                    Workout.scheduled_date < datetime.combine(activity_date, datetime.min.time(), tzinfo=timezone.utc) + timedelta(days=1)
                )
            )
            .limit(1)
        ).scalar_one_or_none()
        
        return workout
    
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
    
    async def export_workout_to_garmin(
        self,
        user_id: int,
        workout_id: int
    ) -> Dict[str, Any]:
        """
        Export workout to Garmin Connect (sync bidirezionale).
        
        Converts workout to FIT/TCX format and uploads to Garmin Connect.
        """
        from app.config import settings
        from app.services.workout_export_service import WorkoutExportService
        
        account = self.get_account(user_id)
        if not account:
            raise ValueError("Garmin account not connected")
        
        if not account.access_token or not account.access_token_secret:
            raise ValueError("Garmin account not properly authenticated")
        
        # Get workout
        workout = self.db.execute(
            select(Workout)
            .where(
                and_(
                    Workout.id == workout_id,
                    Workout.user_id == user_id
                )
            )
        ).scalar_one_or_none()
        
        if not workout:
            raise ValueError("Workout not found")
        
        consumer_key = getattr(settings, 'GARMIN_CONSUMER_KEY', None)
        consumer_secret = getattr(settings, 'GARMIN_CONSUMER_SECRET', None)
        
        if not consumer_key or not consumer_secret:
            raise ValueError("Garmin OAuth credentials not configured")
        
        try:
            # Export workout to FIT format
            export_service = WorkoutExportService()
            try:
                fit_data = export_service.export_to_fit(workout, workout.structure_json)
                file_format = 'fit'
            except NotImplementedError:
                # Fallback to TCX if FIT not available
                tcx_data = export_service.export_to_tcx(workout, workout.structure_json)
                fit_data = tcx_data
                file_format = 'tcx'
            
            # Create OAuth session
            oauth = OAuth1Session(
                consumer_key,
                client_secret=consumer_secret,
                resource_owner_key=account.access_token,
                resource_owner_secret=account.access_token_secret
            )
            
            # Upload to Garmin Connect
            # Garmin API endpoint for uploading activities
            upload_url = f"{self.API_BASE_URL}/activity-service/activity/upload"
            
            files = {
                'file': (f'workout_{workout_id}.{file_format}', fit_data, f'application/{file_format}')
            }
            
            response = oauth.post(upload_url, files=files)
            response.raise_for_status()
            
            upload_result = response.json()
            garmin_activity_id = upload_result.get('activityId') or upload_result.get('id')
            
            if garmin_activity_id:
                # Store reference in database
                activity = GarminActivity(
                    user_id=user_id,
                    garmin_account_id=account.id,
                    garmin_activity_id=str(garmin_activity_id),
                    workout_id=workout_id,
                    activity_type=workout.plan.sport_type if workout.plan else 'running',
                    start_time=workout.scheduled_date or datetime.now(timezone.utc),
                    duration_seconds=workout.duration_minutes * 60,
                    raw_data=json.dumps(upload_result)
                )
                self.db.add(activity)
                self.db.commit()
            
            logger.info(f"[GARMIN] Exported workout {workout_id} to Garmin Connect (activity ID: {garmin_activity_id})")
            
            return {
                "success": True,
                "garmin_activity_id": garmin_activity_id,
                "message": f"Workout exported to Garmin Connect successfully"
            }
        except Exception as e:
            logger.error(f"[GARMIN] Error exporting workout to Garmin: {e}")
            raise
