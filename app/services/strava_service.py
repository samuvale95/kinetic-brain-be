import requests
import json
from datetime import datetime, timedelta, date
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_, func, desc
from app.models.strava import StravaAccount, StravaActivity, StravaWebhook
from app.models.workout import Workout, WorkoutStatus
from app.models.user import User, UserProfile, PerformanceMetrics
from app.models.training_metrics import TrainingMetrics
from app.models.weekly_summary import WeeklyPerformanceSummary
from app.services.metrics_calculation_service import MetricsCalculationService
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class StravaService:
    def __init__(self, db: Session):
        self.db = db
        self.base_url = "https://www.strava.com/api/v3"
        self.auth_url = "https://www.strava.com/oauth"
        self.metrics_service = MetricsCalculationService()
    
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
    
    def calculate_activity_metrics(self, strava_activity: StravaActivity, user_id: int) -> TrainingMetrics:
        """
        Calculate training metrics for a Strava activity
        
        Args:
            strava_activity: Strava activity to calculate metrics for
            user_id: User ID to get threshold values from
        
        Returns:
            TrainingMetrics object with calculated values
        """
        # Get user's performance thresholds
        hr_metrics = self.db.execute(
            select(PerformanceMetrics)
            .where(and_(
                PerformanceMetrics.user_id == user_id,
                PerformanceMetrics.metric_type == "hr"
            ))
            .order_by(desc(PerformanceMetrics.test_date))
        ).scalar_one_or_none()
        
        power_metrics = self.db.execute(
            select(PerformanceMetrics)
            .where(and_(
                PerformanceMetrics.user_id == user_id,
                PerformanceMetrics.metric_type == "power"
            ))
            .order_by(desc(PerformanceMetrics.test_date))
        ).scalar_one_or_none()
        
        # Extract zones
        hr_zones = None
        if hr_metrics and hr_metrics.zones_json:
            hr_zones = hr_metrics.zones_json
        
        # Get threshold values
        threshold_hr = hr_metrics.threshold_value if hr_metrics else None
        threshold_power = power_metrics.threshold_value if power_metrics else None
        max_hr = hr_metrics.max_value if hr_metrics else None
        resting_hr = hr_metrics.rest_value if hr_metrics else None
        
        # Calculate duration
        duration_seconds = strava_activity.moving_time or strava_activity.elapsed_time or 0
        
        # Calculate Intensity Factor
        intensity_factor = None
        if strava_activity.weighted_average_watts and threshold_power:
            intensity_factor = self.metrics_service.calculate_intensity_factor(
                normalized_power=strava_activity.weighted_average_watts,
                threshold_power=threshold_power
            )
        elif strava_activity.average_watts and threshold_power:
            intensity_factor = self.metrics_service.calculate_intensity_factor(
                avg_power=strava_activity.average_watts,
                threshold_power=threshold_power
            )
        elif strava_activity.average_heartrate and threshold_hr:
            intensity_factor = self.metrics_service.calculate_intensity_factor(
                avg_hr=strava_activity.average_heartrate,
                threshold_hr=threshold_hr
            )
        
        # Calculate TSS
        tss = self.metrics_service.calculate_tss(
            duration_seconds=duration_seconds,
            intensity_factor=intensity_factor,
            normalized_power=strava_activity.weighted_average_watts,
            threshold_power=threshold_power
        )
        
        # Calculate TRIMP
        trimp = 0
        if strava_activity.average_heartrate and max_hr:
            trimp = self.metrics_service.calculate_trimp(
                duration_seconds=duration_seconds,
                avg_hr=strava_activity.average_heartrate,
                max_hr=max_hr,
                resting_hr=resting_hr
            )
        
        # Calculate time in zones
        time_in_zones = {}
        if strava_activity.average_heartrate and hr_zones:
            time_in_zones = self.metrics_service.calculate_time_in_zones(
                hr_data=None,
                zones=hr_zones,
                duration_seconds=duration_seconds,
                avg_hr=strava_activity.average_heartrate
            )
        
        # Create TrainingMetrics record
        training_metrics = TrainingMetrics(
            strava_activity_id=strava_activity.id,
            tss=tss,
            normalized_power=strava_activity.weighted_average_watts,
            intensity_factor=intensity_factor,
            trimp=trimp,
            time_in_zone_1=time_in_zones.get('z1', 0),
            time_in_zone_2=time_in_zones.get('z2', 0),
            time_in_zone_3=time_in_zones.get('z3', 0),
            time_in_zone_4=time_in_zones.get('z4', 0),
            time_in_zone_5=time_in_zones.get('z5', 0),
            zone_distribution={
                "z1": time_in_zones.get('z1', 0),
                "z2": time_in_zones.get('z2', 0),
                "z3": time_in_zones.get('z3', 0),
                "z4": time_in_zones.get('z4', 0),
                "z5": time_in_zones.get('z5', 0)
            }
        )
        
        # Update StravaActivity with denormalized values for quick access
        strava_activity.tss = tss
        strava_activity.normalized_power = strava_activity.weighted_average_watts
        strava_activity.intensity_factor = intensity_factor
        strava_activity.trimp = trimp
        strava_activity.time_in_zone_1 = time_in_zones.get('z1', 0)
        strava_activity.time_in_zone_2 = time_in_zones.get('z2', 0)
        strava_activity.time_in_zone_3 = time_in_zones.get('z3', 0)
        strava_activity.time_in_zone_4 = time_in_zones.get('z4', 0)
        strava_activity.time_in_zone_5 = time_in_zones.get('z5', 0)
        strava_activity.metrics_calculated = True
        strava_activity.zone_distribution = training_metrics.zone_distribution
        
        return training_metrics
    
    def recalculate_all_metrics(self, user_id: int) -> Dict[str, Any]:
        """
        Recalculate metrics for all existing activities for a user
        
        This is called on first Strava connection and when user explicitly requests recalculation
        
        Args:
            user_id: User ID to recalculate metrics for
        
        Returns:
            Dictionary with recalculation results
        """
        start_time = datetime.now()
        
        # Get user's Strava account
        strava_account = self.db.execute(
            select(StravaAccount)
            .where(StravaAccount.user_id == user_id)
        ).scalar_one_or_none()
        
        if not strava_account:
            raise Exception("No Strava account found for user")
        
        # Get all activities
        activities = self.db.execute(
            select(StravaActivity)
            .where(StravaActivity.strava_account_id == strava_account.id)
            .order_by(StravaActivity.start_date)
        ).scalars().all()
        
        metrics_calculated = {
            'tss_calculated': 0,
            'trimp_calculated': 0,
            'if_calculated': 0,
            'zones_calculated': 0
        }
        
        activities_processed = 0
        metrics_to_update = []
        
        for activity in activities:
            # Check if metrics already exist
            existing_metrics = self.db.execute(
                select(TrainingMetrics)
                .where(TrainingMetrics.strava_activity_id == activity.id)
            ).scalar_one_or_none()
            
            # Always recalculate metrics to ensure accuracy
            # Don't skip - force recalculation
            
            # Calculate new metrics
            try:
                metrics = self.calculate_activity_metrics(activity, user_id)
                
                # Update existing or add new
                if existing_metrics:
                    # Update existing - just update fields, don't add new record
                    existing_metrics.tss = metrics.tss
                    existing_metrics.normalized_power = metrics.normalized_power
                    existing_metrics.intensity_factor = metrics.intensity_factor
                    existing_metrics.trimp = metrics.trimp
                    existing_metrics.time_in_zone_1 = metrics.time_in_zone_1
                    existing_metrics.time_in_zone_2 = metrics.time_in_zone_2
                    existing_metrics.time_in_zone_3 = metrics.time_in_zone_3
                    existing_metrics.time_in_zone_4 = metrics.time_in_zone_4
                    existing_metrics.time_in_zone_5 = metrics.time_in_zone_5
                    existing_metrics.zone_distribution = metrics.zone_distribution
                    # Don't append to metrics_to_update since we're updating, not inserting
                else:
                    # Add new to list for bulk insert (only if it doesn't exist)
                    metrics_to_update.append(metrics)
                
                metrics_calculated['tss_calculated'] += 1 if metrics.tss else 0
                metrics_calculated['trimp_calculated'] += 1 if metrics.trimp else 0
                metrics_calculated['if_calculated'] += 1 if metrics.intensity_factor else 0
                metrics_calculated['zones_calculated'] += 1 if metrics.time_in_zone_1 or metrics.time_in_zone_2 else 0
                
                activities_processed += 1
            except Exception as e:
                logger.error(f"Error calculating metrics for activity {activity.id}: {e}")
                continue
        
        # Bulk add new metrics only
        if metrics_to_update:
            self.db.add_all(metrics_to_update)
        
        # Commit all changes
        self.db.commit()
        
        # Calculate initial CTL/ATL/TSB
        initial_metrics = self._calculate_initial_fitness_metrics(user_id)
        
        # Create weekly summaries
        weekly_summaries_created = self._create_weekly_summaries(user_id)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return {
            'success': True,
            'activities_processed': activities_processed,
            'metrics_calculated': metrics_calculated,
            'weekly_summaries_created': weekly_summaries_created,
            'initial_ctl': initial_metrics.get('ctl'),
            'initial_atl': initial_metrics.get('atl'),
            'initial_tsb': initial_metrics.get('tsb'),
            'processing_time_seconds': round(processing_time, 2)
        }
    
    def _calculate_initial_fitness_metrics(self, user_id: int) -> Dict[str, float]:
        """
        Calculate initial CTL/ATL/TSB based on historical data
        
        IMPORTANT: This includes ALL 42 days in the period, even days with no activity (TSS=0).
        This is crucial for the exponential decay calculation - rest days cause fitness/fatigue to decay.
        """
        from datetime import date
        
        # Get last 42 days (for CTL)
        end_date = date.today()
        start_date = end_date - timedelta(days=41)  # 42 days total (including today)
        
        # Get activities with metrics in this period
        activities = self.db.execute(
            select(StravaActivity)
            .where(and_(
                StravaActivity.strava_account_id == (
                    select(StravaAccount.id)
                    .where(StravaAccount.user_id == user_id)
                    .scalar_subquery()
                ),
                StravaActivity.start_date >= start_date,
                StravaActivity.tss.isnot(None)
            ))
            .order_by(StravaActivity.start_date)
        ).scalars().all()
        
        # Group TSS by date
        daily_tss = {}
        for activity in activities:
            activity_date = activity.start_date.date()
            daily_tss[activity_date] = daily_tss.get(activity_date, 0) + (activity.tss or 0)
        
        # Build complete list of ALL days in period (most recent first)
        # This is critical: we include days with 0 TSS (rest days)
        tss_list = []
        for i in range(42):
            day_date = end_date - timedelta(days=i)
            tss_for_day = daily_tss.get(day_date, 0)  # 0 for rest days
            tss_list.append(tss_for_day)
        
        # Calculate CTL/ATL/TSB with all days
        # The exponential decay happens on EVERY day, including rest days
        metrics = self.metrics_service.calculate_ctl_atl_tsb(tss_list)
        
        return metrics
    
    def _create_weekly_summaries(self, user_id: int) -> int:
        """
        Create weekly summaries for historical data
        
        This creates weekly summaries for all weeks with activities in the last 12 weeks
        """
        from app.models.weekly_summary import WeeklyPerformanceSummary
        
        end_date = date.today()
        start_date = end_date - timedelta(weeks=12)
        
        # Get all activities in the period
        strava_account_ids = self.db.execute(
            select(StravaAccount.id)
            .where(StravaAccount.user_id == user_id)
        ).scalars().all()
        
        print(f"DEBUG: Found {len(strava_account_ids)} strava accounts for user {user_id}")
        
        if not strava_account_ids:
            return 0
        
        # Remove metrics_calculated filter for now - include all activities
        activities = self.db.execute(
            select(StravaActivity)
            .where(and_(
                StravaActivity.strava_account_id.in_(strava_account_ids),
                StravaActivity.start_date >= start_date
            ))
            .order_by(StravaActivity.start_date)
        ).scalars().all()
        
        if not activities:
            return 0
        
        # Group activities by week
        weekly_data = {}
        for activity in activities:
            activity_date = activity.start_date.date()
            week_start = activity_date - timedelta(days=activity_date.weekday())
            
            if week_start not in weekly_data:
                weekly_data[week_start] = {
                    'activities': [],
                    'total_tss': 0,
                    'total_trimp': 0,
                    'total_duration': 0,
                    'total_distance': 0
                }
            
            weekly_data[week_start]['activities'].append(activity)
            # Use TSS from activity if available, otherwise calculate from duration
            activity_tss = activity.tss or 0
            if activity_tss == 0 and activity.moving_time:
                # Rough estimate: 1 hour at Z2 = ~50 TSS
                activity_tss = (activity.moving_time / 3600) * 50
            
            weekly_data[week_start]['total_tss'] += activity_tss
            weekly_data[week_start]['total_trimp'] += activity.trimp or 0
            weekly_data[week_start]['total_duration'] += activity.moving_time or 0
            weekly_data[week_start]['total_distance'] += activity.distance or 0
        
        # Create weekly summaries (without CTL/ATL/TSB for now)
        summaries_created = 0
        for week_start, data in weekly_data.items():
            week_end = week_start + timedelta(days=6)
            
            # Check if summary already exists
            existing = self.db.execute(
                select(WeeklyPerformanceSummary)
                .where(and_(
                    WeeklyPerformanceSummary.user_id == user_id,
                    WeeklyPerformanceSummary.week_start_date == week_start
                ))
            ).scalar_one_or_none()
            
            # Calculate aggregate metrics
            total_duration_seconds = data.get('total_duration', 0) or 0
            total_minutes = total_duration_seconds / 60
            volume_hours = total_minutes / 60 if total_minutes else 0
            total_distance_meters = data.get('total_distance', 0) or 0
            volume_km = total_distance_meters / 1000
            
            # Update existing or create new
            if existing:
                # Update existing summary
                existing.weekly_tss = data['total_tss']
                existing.workouts_completed = len(data['activities'])
                existing.volume_hours = round(volume_hours, 2)
                existing.volume_kilometers = volume_km
                continue
            
            # Get average HR if available
            activities_with_hr = [a for a in data['activities'] if a.average_heartrate]
            avg_hr = sum(a.average_heartrate for a in activities_with_hr) / len(activities_with_hr) if activities_with_hr else None
            
            # Get max HR
            max_hr = max((a.max_heartrate for a in data['activities'] if a.max_heartrate), default=None)
            
            # Calculate zone distribution
            zone_time = {
                'z1': sum(a.time_in_zone_1 or 0 for a in data['activities']),
                'z2': sum(a.time_in_zone_2 or 0 for a in data['activities']),
                'z3': sum(a.time_in_zone_3 or 0 for a in data['activities']),
                'z4': sum(a.time_in_zone_4 or 0 for a in data['activities']),
                'z5': sum(a.time_in_zone_5 or 0 for a in data['activities'])
            }
            
            total_zone_time = sum(zone_time.values())
            if total_zone_time > 0:
                zone_distribution = {
                    'z1': round((zone_time['z1'] / total_zone_time) * 100, 1),
                    'z2': round((zone_time['z2'] / total_zone_time) * 100, 1),
                    'z3': round((zone_time['z3'] / total_zone_time) * 100, 1),
                    'z4': round((zone_time['z4'] / total_zone_time) * 100, 1),
                    'z5': round((zone_time['z5'] / total_zone_time) * 100, 1)
                }
            else:
                zone_distribution = None
            
            # Create weekly summary
            weekly_summary = WeeklyPerformanceSummary(
                user_id=user_id,
                week_start_date=week_start,
                week_end_date=week_end,
                weekly_tss=data['total_tss'],
                weekly_trimp=data['total_trimp'],
                volume_hours=round(volume_hours, 2),
                volume_kilometers=round(volume_km, 2),
                workouts_completed=len(data['activities']),
                avg_hr=avg_hr,
                max_hr=max_hr,
                zone_distribution=zone_distribution
            )
            
            self.db.add(weekly_summary)
            summaries_created += 1
        
        # Commit summaries first
        self.db.commit()
        
        # Now update CTL/ATL/TSB for ALL summaries using direct SQL UPDATE
        all_summaries = self.db.execute(
            select(WeeklyPerformanceSummary)
            .where(and_(
                WeeklyPerformanceSummary.user_id == user_id,
                WeeklyPerformanceSummary.week_start_date >= start_date
            ))
        ).scalars().all()
        
        print(f"DEBUG: Found {len(all_summaries)} summaries to update with CTL/ATL/TSB")
        
        if len(all_summaries) == 0:
            print("DEBUG: No summaries found to update! Something is wrong.")
            self.db.commit()
            return summaries_created
        
        from sqlalchemy import update
        
        updates_made = 0
        for summary in all_summaries:
            week_start = summary.week_start_date
            
            # Calculate CTL/ATL/TSB
            tss_list = []
            activities_found_count = 0
            for i in range(41, -1, -1):
                check_date = week_start - timedelta(days=42-i)
                # Debug first and last dates being checked
                if i == 41 or i == 0:
                    print(f"  Checking date {check_date} (i={i}, days_back={42-i})")
                # Check if activities exist for this day by testing with broader range first
                all_activities_this_day = self.db.execute(
                    select(StravaActivity)
                    .where(and_(
                        StravaActivity.strava_account_id.in_(strava_account_ids),
                        StravaActivity.start_date >= check_date,
                        StravaActivity.start_date < check_date + timedelta(days=1)
                    ))
                ).scalars().all()
                
                if len(all_activities_this_day) > 0:
                    print(f"  Day {i} ({check_date}): Found {len(all_activities_this_day)} activities with broader query")
                
                # Use the broader query results (all_activities_this_day) instead of the narrow ±12h query
                day_tss = sum(a.tss or 0 for a in all_activities_this_day)
                
                if len(all_activities_this_day) > 0:
                    activities_found_count += 1
                    if i >= 38:  # Debug only for first few days
                        print(f"  Day {i}: found {len(all_activities_this_day)} activities on {check_date}, first tss={all_activities_this_day[0].tss if all_activities_this_day else 'N/A'}")
                tss_list.append(day_tss)
            
            print(f"DEBUG Week {week_start}: found activities on {activities_found_count}/42 days")
            
            print(f"DEBUG Week {week_start}: tss_list length={len(tss_list)}, sum={sum(tss_list):.1f}, first_10=[{', '.join([str(round(t, 1)) for t in tss_list[:10]])}]")
            
            metrics = self.metrics_service.calculate_ctl_atl_tsb(tss_list)
            print(f"DEBUG Week {week_start}: metrics calculated = {metrics}")
            
            # Direct SQL UPDATE
            self.db.execute(
                update(WeeklyPerformanceSummary)
                .where(WeeklyPerformanceSummary.id == summary.id)
                .values(ctl=metrics['ctl'], atl=metrics['atl'], tsb=metrics['tsb'])
            )
            print(f"DEBUG Week {week_start}: UPDATE executed with values ctl={metrics['ctl']}, atl={metrics['atl']}, tsb={metrics['tsb']}")
            updates_made += 1
        
        self.db.commit()
        print(f"DEBUG: Created {summaries_created} and updated CTL/ATL/TSB for {updates_made} summaries")
        
        return summaries_created

