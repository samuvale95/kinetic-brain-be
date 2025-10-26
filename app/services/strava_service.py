import requests
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_
from app.models.strava import StravaAccount, StravaActivity, StravaWebhook
from app.models.workout import Workout, WorkoutStatus
from app.models.user import User
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class StravaService:
    def __init__(self, db: Session):
        self.db = db
        self.base_url = "https://www.strava.com/api/v3"
        self.auth_url = "https://www.strava.com/oauth"
    
    def get_auth_url(self, user_id: int) -> str:
        """Generate Strava OAuth authorization URL"""
        params = {
            "client_id": settings.strava_client_id,
            "redirect_uri": settings.strava_redirect_uri,
            "response_type": "code",
            "scope": "read,activity:read_all,activity:write",
            "state": str(user_id)  # Pass user_id in state
        }
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{self.auth_url}/authorize?{query_string}"
    
    def exchange_code_for_token(self, code: str, user_id: int) -> Dict[str, Any]:
        """Exchange authorization code for access token"""
        data = {
            "client_id": settings.strava_client_id,
            "client_secret": settings.strava_client_secret,
            "code": code,
            "grant_type": "authorization_code"
        }
        
        response = requests.post(f"{self.auth_url}/token", data=data)
        
        if response.status_code != 200:
            raise Exception(f"Failed to exchange code: {response.text}")
        
        token_data = response.json()
        
        # Save Strava account
        strava_account = StravaAccount(
            user_id=user_id,
            strava_id=token_data["athlete"]["id"],
            access_token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            token_expires_at=datetime.fromtimestamp(token_data["expires_at"]),
            firstname=token_data["athlete"].get("firstname"),
            lastname=token_data["athlete"].get("lastname"),
            profile_medium=token_data["athlete"].get("profile_medium"),
            profile=token_data["athlete"].get("profile"),
            city=token_data["athlete"].get("city"),
            state=token_data["athlete"].get("state"),
            country=token_data["athlete"].get("country"),
            sex=token_data["athlete"].get("sex"),
            premium=token_data["athlete"].get("premium", False),
            summit=token_data["athlete"].get("summit", False)
        )
        
        self.db.add(strava_account)
        self.db.commit()
        self.db.refresh(strava_account)
        
        return {
            "strava_account_id": strava_account.id,
            "athlete": token_data["athlete"],
            "access_token": token_data["access_token"]
        }
    
    def refresh_access_token(self, strava_account: StravaAccount) -> bool:
        """Refresh Strava access token"""
        data = {
            "client_id": settings.strava_client_id,
            "client_secret": settings.strava_client_secret,
            "refresh_token": strava_account.refresh_token,
            "grant_type": "refresh_token"
        }
        
        response = requests.post(f"{self.auth_url}/token", data=data)
        
        if response.status_code != 200:
            logger.error(f"Failed to refresh token: {response.text}")
            return False
        
        token_data = response.json()
        
        # Update tokens
        strava_account.access_token = token_data["access_token"]
        strava_account.refresh_token = token_data["refresh_token"]
        strava_account.token_expires_at = datetime.fromtimestamp(token_data["expires_at"])
        
        self.db.commit()
        return True
    
    def get_valid_access_token(self, strava_account: StravaAccount) -> Optional[str]:
        """Get valid access token, refreshing if necessary"""
        from datetime import timezone
        if datetime.now(timezone.utc) >= strava_account.token_expires_at:
            if not self.refresh_access_token(strava_account):
                return None
        
        return strava_account.access_token
    
    def fetch_athlete_activities(self, strava_account: StravaAccount, 
                                per_page: int = 200, page: int = 1) -> List[Dict[str, Any]]:
        """Fetch athlete activities from Strava"""
        access_token = self.get_valid_access_token(strava_account)
        if not access_token:
            raise Exception("Invalid access token")
        
        headers = {"Authorization": f"Bearer {access_token}"}
        params = {
            "per_page": per_page,
            "page": page
        }
        
        response = requests.get(f"{self.base_url}/athlete/activities", 
                              headers=headers, params=params)
        
        if response.status_code != 200:
            raise Exception(f"Failed to fetch activities: {response.text}")
        
        return response.json()
    
    def fetch_activity_details(self, strava_account: StravaAccount, 
                             activity_id: int) -> Dict[str, Any]:
        """Fetch detailed activity data from Strava"""
        access_token = self.get_valid_access_token(strava_account)
        if not access_token:
            raise Exception("Invalid access token")
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        response = requests.get(f"{self.base_url}/activities/{activity_id}", 
                              headers=headers)
        
        if response.status_code != 200:
            raise Exception(f"Failed to fetch activity details: {response.text}")
        
        return response.json()
    
    def sync_user_activities(self, user_id: int, days_back: int = 30) -> Dict[str, Any]:
        """Sync user's Strava activities"""
        # Get user's Strava account
        strava_account = self.db.execute(
            select(StravaAccount)
            .where(StravaAccount.user_id == user_id)
        ).scalar_one_or_none()
        
        if not strava_account:
            raise Exception("No Strava account found for user")
        
        # Fetch activities
        activities = self.fetch_athlete_activities(strava_account)
        
        # Filter activities by date
        from datetime import timezone
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
        recent_activities = [
            activity for activity in activities 
            if datetime.fromisoformat(activity["start_date"].replace("Z", "+00:00")) >= cutoff_date
        ]
        
        synced_count = 0
        new_count = 0
        
        for activity_data in recent_activities:
            # Check if activity already exists
            existing_activity = self.db.execute(
                select(StravaActivity)
                .where(StravaActivity.strava_activity_id == activity_data["id"])
            ).scalar_one_or_none()
            
            if existing_activity:
                synced_count += 1
                continue
            
            # Create new Strava activity
            strava_activity = self._create_strava_activity(strava_account, activity_data)
            self.db.add(strava_activity)
            new_count += 1
        
        self.db.commit()
        
        return {
            "total_activities": len(recent_activities),
            "new_activities": new_count,
            "already_synced": synced_count
        }
    
    def _create_strava_activity(self, strava_account: StravaAccount, 
                               activity_data: Dict[str, Any]) -> StravaActivity:
        """Create StravaActivity from Strava API data"""
        start_date = datetime.fromisoformat(activity_data["start_date"].replace("Z", "+00:00"))
        start_date_local = datetime.fromisoformat(activity_data["start_date_local"].replace("Z", "+00:00"))
        
        return StravaActivity(
            strava_account_id=strava_account.id,
            strava_activity_id=activity_data["id"],
            name=activity_data["name"],
            type=activity_data["type"],
            sport_type=activity_data.get("sport_type"),
            start_date=start_date,
            start_date_local=start_date_local,
            timezone=activity_data.get("timezone"),
            distance=activity_data.get("distance"),
            moving_time=activity_data.get("moving_time"),
            elapsed_time=activity_data.get("elapsed_time"),
            total_elevation_gain=activity_data.get("total_elevation_gain"),
            average_speed=activity_data.get("average_speed"),
            max_speed=activity_data.get("max_speed"),
            average_heartrate=activity_data.get("average_heartrate"),
            max_heartrate=activity_data.get("max_heartrate"),
            average_watts=activity_data.get("average_watts"),
            max_watts=activity_data.get("max_watts"),
            weighted_average_watts=activity_data.get("weighted_average_watts"),
            average_cadence=activity_data.get("average_cadence"),
            temperature=activity_data.get("temp"),
            feels_like=activity_data.get("feels_like"),
            calories=activity_data.get("calories"),
            kilojoules=activity_data.get("kilojoules"),
            raw_data=activity_data
        )
    
    def match_activities_with_workouts(self, user_id: int) -> Dict[str, Any]:
        """Match Strava activities with scheduled workouts"""
        # Get user's Strava account
        strava_account = self.db.execute(
            select(StravaAccount)
            .where(StravaAccount.user_id == user_id)
        ).scalar_one_or_none()
        
        if not strava_account:
            raise Exception("No Strava account found for user")
        
        # Get unmatched Strava activities
        unmatched_activities = self.db.execute(
            select(StravaActivity)
            .where(and_(
                StravaActivity.strava_account_id == strava_account.id,
                StravaActivity.workout_id.is_(None)
            ))
        ).scalars().all()
        
        # Get scheduled workouts for the user
        scheduled_workouts = self.db.execute(
            select(Workout)
            .where(and_(
                Workout.user_id == user_id,
                Workout.status == WorkoutStatus.SCHEDULED,
                Workout.scheduled_date.isnot(None)
            ))
        ).scalars().all()
        
        matched_count = 0
        matches = []
        
        for activity in unmatched_activities:
            best_match = self._find_best_workout_match(activity, scheduled_workouts)
            
            if best_match:
                # Match found
                activity.workout_id = best_match.id
                activity.is_synced = True
                activity.sync_status = "matched"
                
                # Update workout status
                best_match.status = WorkoutStatus.COMPLETED
                
                matches.append({
                    "activity_id": activity.id,
                    "activity_name": activity.name,
                    "workout_id": best_match.id,
                    "workout_title": best_match.title,
                    "date": activity.start_date_local.date().isoformat()
                })
                
                matched_count += 1
        
        self.db.commit()
        
        return {
            "total_unmatched": len(unmatched_activities),
            "matched_count": matched_count,
            "matches": matches
        }
    
    def _find_best_workout_match(self, activity: StravaActivity, 
                               workouts: List[Workout]) -> Optional[Workout]:
        """Find the best matching workout for a Strava activity"""
        activity_date = activity.start_date_local.date()
        activity_type = activity.type.lower()
        
        # Score potential matches
        best_match = None
        best_score = 0
        
        for workout in workouts:
            if not workout.scheduled_date:
                continue
            
            score = 0
            
            # Date match (most important)
            if workout.scheduled_date == activity_date:
                score += 100
            elif abs((workout.scheduled_date - activity_date).days) == 1:
                score += 50  # Allow 1 day difference
            elif abs((workout.scheduled_date - activity_date).days) <= 3:
                score += 25  # Allow 3 days difference
            else:
                continue  # Skip if too far apart
            
            # Type match
            workout_type = workout.type.lower()
            if activity_type in workout_type or workout_type in activity_type:
                score += 30
            elif self._is_similar_sport_type(activity_type, workout_type):
                score += 20
            
            # Duration match (if available)
            if activity.moving_time and workout.duration_minutes:
                activity_duration_min = activity.moving_time / 60
                duration_diff = abs(activity_duration_min - workout.duration_minutes)
                if duration_diff <= 10:  # Within 10 minutes
                    score += 20
                elif duration_diff <= 30:  # Within 30 minutes
                    score += 10
            
            if score > best_score:
                best_score = score
                best_match = workout
        
        # Only return match if score is high enough
        return best_match if best_score >= 50 else None
    
    def _is_similar_sport_type(self, activity_type: str, workout_type: str) -> bool:
        """Check if activity and workout types are similar"""
        similar_types = {
            "run": ["running", "jog", "trail"],
            "ride": ["cycling", "bike", "bicycle"],
            "swim": ["swimming", "pool", "open water"],
            "walk": ["walking", "hike", "trek"]
        }
        
        for sport, variations in similar_types.items():
            if sport in activity_type.lower():
                return any(var in workout_type.lower() for var in variations)
        
        return False
    
    def get_user_activities(self, user_id: int, limit: int = 50, 
                          offset: int = 0) -> List[Dict[str, Any]]:
        """Get user's Strava activities with workout matches"""
        strava_account = self.db.execute(
            select(StravaAccount)
            .where(StravaAccount.user_id == user_id)
        ).scalar_one_or_none()
        
        if not strava_account:
            return []
        
        activities = self.db.execute(
            select(StravaActivity)
            .where(StravaActivity.strava_account_id == strava_account.id)
            .order_by(StravaActivity.start_date.desc())
            .offset(offset)
            .limit(limit)
        ).scalars().all()
        
        result = []
        for activity in activities:
            activity_data = {
                "id": activity.id,
                "strava_activity_id": activity.strava_activity_id,
                "name": activity.name,
                "type": activity.type,
                "sport_type": activity.sport_type,
                "start_date": activity.start_date,
                "start_date_local": activity.start_date_local,
                "timezone": activity.timezone,
                "distance": activity.distance,
                "moving_time": activity.moving_time,
                "elapsed_time": activity.elapsed_time,
                "total_elevation_gain": activity.total_elevation_gain,
                "average_speed": activity.average_speed,
                "max_speed": activity.max_speed,
                "average_heartrate": activity.average_heartrate,
                "max_heartrate": activity.max_heartrate,
                "average_watts": activity.average_watts,
                "max_watts": activity.max_watts,
                "weighted_average_watts": activity.weighted_average_watts,
                "average_cadence": activity.average_cadence,
                "temperature": activity.temperature,
                "feels_like": activity.feels_like,
                "calories": activity.calories,
                "kilojoules": activity.kilojoules,
                "is_synced": activity.is_synced,
                "sync_status": activity.sync_status,
                "workout_match": None,
                "created_at": activity.created_at
            }
            
            if activity.workout_id:
                workout = self.db.execute(
                    select(Workout)
                    .where(Workout.id == activity.workout_id)
                ).scalar_one_or_none()
                
                if workout:
                    activity_data["workout_match"] = {
                        "id": workout.id,
                        "title": workout.title,
                        "type": workout.type,
                        "scheduled_date": workout.scheduled_date.isoformat() if workout.scheduled_date else None
                    }
            
            result.append(activity_data)
        
        return result

