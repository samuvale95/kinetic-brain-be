import json
from datetime import datetime, timedelta, date, timezone
from typing import List, Optional, Dict, Any, Set

import requests
from loguru import logger
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import Session

from app.config import settings
from app.models.strava import (
    StravaAccount,
    StravaActivity,
    StravaWebhook,
    StravaSyncJob,
    StravaSyncJobStatus,
)
from app.models.training_metrics import TrainingMetrics
from app.models.user import User, UserProfile, PerformanceMetrics
from app.models.workout import Workout, WorkoutStatus
from app.services.metrics_calculation_service import MetricsCalculationService


class StravaService:
    def __init__(self, db: Session):
        self.db = db
        self.base_url = "https://www.strava.com/api/v3"
        self.auth_url = "https://www.strava.com/oauth"
        self.metrics_service = MetricsCalculationService()

    # ------------------------------------------------------------------
    # Sync job helpers
    # ------------------------------------------------------------------
    def create_sync_job(
        self,
        user_id: int,
        strava_account_id: int,
        job_type: str = "initial_sync",
        status_message: Optional[str] = None,
        requested_days_back: int = 30,
    ) -> StravaSyncJob:
        """Create a sync job entry that can be tracked by the frontend."""
        job = StravaSyncJob(
            user_id=user_id,
            strava_account_id=strava_account_id,
            job_type=job_type,
            status=StravaSyncJobStatus.PENDING,
            status_message=status_message,
            requested_days_back=requested_days_back,
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def get_sync_job(self, job_id: int) -> Optional[StravaSyncJob]:
        return self.db.get(StravaSyncJob, job_id)

    def get_latest_sync_jobs(self, user_id: int, limit: int = 5) -> List[StravaSyncJob]:
        return (
            self.db.query(StravaSyncJob)
            .filter(StravaSyncJob.user_id == user_id)
            .order_by(StravaSyncJob.created_at.desc())
            .limit(limit)
            .all()
        )

    def _update_sync_job(
        self,
        job: StravaSyncJob,
        *,
        status: Optional[str] = None,
        status_message: Optional[str] = None,
        total_activities: Optional[int] = None,
        processed_activities: Optional[int] = None,
        metrics_phase: Optional[int] = None,
        metrics_phases_total: Optional[int] = None,
        error: Optional[str] = None,
        started_at: Optional[datetime] = None,
        finished_at: Optional[datetime] = None,
        result: Optional[Dict[str, Any]] = None,
        commit: bool = True,
    ) -> StravaSyncJob:
        if status is not None:
            job.status = status
        if status_message is not None:
            job.status_message = status_message
        if total_activities is not None:
            job.total_activities = total_activities
        if processed_activities is not None:
            job.processed_activities = processed_activities
        if metrics_phase is not None:
            job.metrics_phase = metrics_phase
        if metrics_phases_total is not None:
            job.metrics_phases_total = metrics_phases_total
        if error is not None:
            job.error = error
        if started_at is not None:
            job.started_at = started_at
        if finished_at is not None:
            job.finished_at = finished_at
        if result is not None:
            job.result = result

        self.db.add(job)
        if commit:
            self.db.commit()
        else:
            self.db.flush()

        logger.bind(
            job_id=job.id,
            status=job.status,
            processed=job.processed_activities,
            total=job.total_activities,
            metrics_phase=job.metrics_phase,
            metrics_total=job.metrics_phases_total,
            error=job.error,
        ).debug("[STRAVA_SYNC] Sync job updated")
        return job

    
    def _parse_json_field(self, field_value) -> Optional[Dict[str, Any]]:
        """
        Safely parse a JSON field that might be a string or already a dict.
        Returns None if field is None or empty, a dict if successful.
        """
        if field_value is None:
            return None
        if isinstance(field_value, dict):
            return field_value
        if isinstance(field_value, str):
            try:
                return json.loads(field_value)
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Failed to parse JSON field: {str(field_value)[:50]}")
                return None
        return None
    
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
        
        masked_code = f"{code[:6]}..." if len(code) > 6 else code
        logger.info(
            f"[STRAVA_AUTH] Exchanging code for token (user={user_id}, code={masked_code})"
        )
        try:
            response = requests.post(
                f"{self.auth_url}/token",
                data=data,
                timeout=15,
            )
        except requests.exceptions.RequestException as exc:
            logger.exception(
                f"[STRAVA_AUTH] Token exchange request failed (user={user_id}): {exc}"
            )
            raise Exception("Failed to reach Strava API for token exchange") from exc
        
        if response.status_code != 200:
            logger.error(
                f"[STRAVA_AUTH] Token exchange returned {response.status_code} for user {user_id}: {response.text}"
            )
            raise Exception(f"Failed to exchange code: {response.text}")
        
        token_data = response.json()
        logger.debug(
            f"[STRAVA_AUTH] Token exchange successful for user {user_id}: "
            f"athlete_id={token_data.get('athlete', {}).get('id')}"
        )
        
        # Check if this is a reconnection (account already exists for this user)
        existing_account = self.db.execute(
            select(StravaAccount)
            .where(StravaAccount.user_id == user_id)
        ).scalar_one_or_none()
        
        is_first_connection = existing_account is None
        
        if existing_account:
            # Update existing account tokens
            logger.info(f"[STRAVA_AUTH] Reconnecting existing Strava account for user {user_id}")
            existing_account.access_token = token_data["access_token"]
            existing_account.refresh_token = token_data["refresh_token"]
            existing_account.token_expires_at = datetime.fromtimestamp(token_data["expires_at"])
            strava_account = existing_account
        else:
            # Create new Strava account (first connection)
            logger.info(f"[STRAVA_AUTH] First time connection for user {user_id}")
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
            "access_token": token_data["access_token"],
            "is_first_connection": is_first_connection,
            "initial_sync_required": is_first_connection,
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
        if datetime.now(timezone.utc) >= strava_account.token_expires_at:
            if not self.refresh_access_token(strava_account):
                return None
        
        return strava_account.access_token
    
    def fetch_athlete_activities(self, strava_account: StravaAccount, 
                                per_page: int = 200, page: int = 1,
                                timeout: int = 30) -> List[Dict[str, Any]]:
        """Fetch athlete activities from Strava"""
        access_token = self.get_valid_access_token(strava_account)
        if not access_token:
            raise Exception("Invalid access token")
        
        headers = {"Authorization": f"Bearer {access_token}"}
        params = {
            "per_page": per_page,
            "page": page
        }
        
        try:
            response = requests.get(f"{self.base_url}/athlete/activities", 
                                  headers=headers, params=params, timeout=timeout)
            
            if response.status_code != 200:
                raise Exception(f"Failed to fetch activities: {response.text}")
            
            return response.json()
        except requests.exceptions.Timeout:
            logger.error(f"Timeout fetching athlete activities (page {page})")
            raise Exception(f"Timeout fetching activities from Strava API")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error fetching activities: {e}")
            raise Exception(f"Failed to fetch activities: {str(e)}")
    
    def fetch_activity_details(self, strava_account: StravaAccount, 
                             activity_id: int,
                             timeout: int = 10) -> Dict[str, Any]:
        """Fetch detailed activity data from Strava"""
        access_token = self.get_valid_access_token(strava_account)
        if not access_token:
            raise Exception("Invalid access token")
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        try:
            response = requests.get(f"{self.base_url}/activities/{activity_id}", 
                                  headers=headers, timeout=timeout)
            
            if response.status_code != 200:
                raise Exception(f"Failed to fetch activity details: {response.text}")
            
            return response.json()
        except requests.exceptions.Timeout:
            logger.error(f"Timeout fetching activity details for activity {activity_id}")
            raise Exception(f"Timeout fetching activity details from Strava API")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error fetching activity details: {e}")
            raise Exception(f"Failed to fetch activity details: {str(e)}")
    
    def _calculate_lthr_zones(self, lthr: float) -> Dict[str, Dict[str, float]]:
        """
        Calculate HR zones based on LTHR using Joe Friel's formula
        
        Joe Friel's zones (Training Bible):
        - Zone 1: 65-80% of LTHR
        - Zone 2: 81-90% of LTHR
        - Zone 3: 91-100% of LTHR
        - Zone 4: 101-105% of LTHR
        - Zone 5: 106-125% of LTHR (we'll split this into Z5a/b/c later if needed)
        
        Args:
            lthr: Lactate Threshold Heart Rate
            
        Returns:
            Dictionary with zone boundaries
        """
        return {
            'z1': {'min': round(lthr * 0.65), 'max': round(lthr * 0.80)},
            'z2': {'min': round(lthr * 0.81), 'max': round(lthr * 0.90)},
            'z3': {'min': round(lthr * 0.91), 'max': round(lthr * 1.00)},
            'z4': {'min': round(lthr * 1.01), 'max': round(lthr * 1.05)},
            'z5': {'min': round(lthr * 1.06), 'max': round(lthr * 1.25)}
        }
    
    def _calculate_maxhr_zones(self, max_hr: float) -> Dict[str, Dict[str, float]]:
        """
        Calculate HR zones based on Max HR (fallback method)
        
        Standard % of max HR zones:
        - Zone 1: 50-60% of max HR
        - Zone 2: 60-70% of max HR
        - Zone 3: 70-80% of max HR
        - Zone 4: 80-90% of max HR
        - Zone 5: 90-100% of max HR
        
        Args:
            max_hr: Maximum Heart Rate
            
        Returns:
            Dictionary with zone boundaries
        """
        return {
            'z1': {'min': round(max_hr * 0.50), 'max': round(max_hr * 0.60)},
            'z2': {'min': round(max_hr * 0.60), 'max': round(max_hr * 0.70)},
            'z3': {'min': round(max_hr * 0.70), 'max': round(max_hr * 0.80)},
            'z4': {'min': round(max_hr * 0.80), 'max': round(max_hr * 0.90)},
            'z5': {'min': round(max_hr * 0.90), 'max': round(max_hr * 1.00)}
        }
    
    def fetch_activity_streams(self, strava_account: StravaAccount, 
                              activity_id: int, 
                              stream_types: List[str] = None,
                              timeout: int = 5) -> Dict[str, Any]:
        """
        Fetch activity streams (detailed data) from Strava
        
        Args:
            strava_account: Strava account
            activity_id: Activity ID
            stream_types: List of stream types to fetch (e.g., ['heartrate', 'time', 'distance'])
            timeout: Request timeout in seconds (default: 5)
        
        Returns:
            Dictionary with stream data
        """
        access_token = self.get_valid_access_token(strava_account)
        if not access_token:
            raise Exception("Invalid access token")
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Default stream types for HR zone calculation
        if stream_types is None:
            stream_types = ['heartrate', 'time', 'distance']
        
        params = {
            "keys": ",".join(stream_types),
            "key_by_type": "true"
        }
        
        try:
            response = requests.get(f"{self.base_url}/activities/{activity_id}/streams", 
                                  headers=headers, params=params, timeout=timeout)
            
            if response.status_code != 200:
                raise Exception(f"Failed to fetch activity streams: {response.text}")
            
            return response.json()
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout fetching streams for activity {activity_id}")
            raise Exception(f"Timeout fetching activity streams for activity {activity_id}")
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request error fetching streams for activity {activity_id}: {e}")
            raise Exception(f"Failed to fetch activity streams: {str(e)}")
    
    def sync_user_activities(
        self,
        user_id: int,
        days_back: int = 30,
        job: Optional[StravaSyncJob] = None,
    ) -> Dict[str, Any]:
        """Sync user's Strava activities"""
        logger.info(f"[SYNC] Starting sync for user {user_id}, days_back={days_back}")

        if job:
            self._update_sync_job(
                job,
                status=StravaSyncJobStatus.RUNNING,
                status_message=f"Fetching activities from Strava (last {days_back} days)",
                processed_activities=0,
                total_activities=0,
                metrics_phase=0,
                metrics_phases_total=0,
                error=None,
                result=None,
                started_at=datetime.now(timezone.utc),
            )
        
        # Get user's Strava account
        strava_account = self.db.execute(
            select(StravaAccount)
            .where(StravaAccount.user_id == user_id)
        ).scalar_one_or_none()
        
        if not strava_account:
            logger.error(f"[SYNC] No Strava account found for user {user_id}")
            if job:
                self._update_sync_job(
                    job,
                    status=StravaSyncJobStatus.FAILED,
                    status_message="No Strava account found",
                    finished_at=datetime.now(timezone.utc),
                    error="No Strava account found for user",
                )
            raise Exception("No Strava account found for user")
        
        logger.info(f"[SYNC] Found Strava account {strava_account.id} for user {user_id}")
        
        # Fetch activities
        logger.info(
            f"[SYNC] Fetching activities from Strava API (account={strava_account.id})"
        )
        activities = self.fetch_athlete_activities(strava_account)
        logger.info(f"[SYNC] Fetched {len(activities)} total activities from Strava")
        if job:
            self._update_sync_job(
                job,
                status_message=f"Fetched {len(activities)} activities. Filtering by date...",
            )
        
        # Filter activities by date
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
        recent_activities = [
            activity for activity in activities 
            if datetime.fromisoformat(activity["start_date"].replace("Z", "+00:00")) >= cutoff_date
        ]
        logger.info(f"[SYNC] Filtered to {len(recent_activities)} activities in last {days_back} days")
        if job:
            self._update_sync_job(
                job,
                total_activities=len(recent_activities),
                status_message=f"Processing {len(recent_activities)} activities from the last {days_back} days",
            )
        
        synced_count = 0
        updated_count = 0
        new_count = 0
        new_activities = []
        updated_activities = []
        
        total_recent = len(recent_activities)
        logger.info(f"[SYNC] Processing {total_recent} activities...")
        for idx, activity_data in enumerate(recent_activities, 1):
            # Check if activity already exists using strava_activity_id
            existing_activity = self.db.execute(
                select(StravaActivity)
                .where(StravaActivity.strava_activity_id == activity_data["id"])
            ).scalar_one_or_none()
            
            if idx % 50 == 0:
                logger.info(f"[SYNC] Processed {idx}/{len(recent_activities)} activities (new: {new_count}, updated: {updated_count}, synced: {synced_count})")
            
            if existing_activity:
                # Check if activity belongs to this user's account
                if existing_activity.strava_account_id != strava_account.id:
                    # If activity has NULL strava_account_id, it means account was disconnected
                    # Reconnect it to the current account
                    if existing_activity.strava_account_id is None:
                        existing_activity.strava_account_id = strava_account.id
                        logger.info(f"Reconnected activity {existing_activity.strava_activity_id} to account {strava_account.id}")
                    else:
                        # Activity exists but belongs to different account - skip
                        synced_count += 1
                        continue
                
                # Update existing activity if data might have changed
                # Strava allows editing activities, so we should refresh the data
                updated = self._update_strava_activity(existing_activity, activity_data)
                if updated:
                    updated_activities.append(existing_activity)
                    updated_count += 1
                else:
                    synced_count += 1
                if job:
                    commit_progress = idx % 5 == 0 or idx == total_recent
                    self._update_sync_job(
                        job,
                        processed_activities=idx,
                        status_message=f"Processing Strava activities ({idx}/{total_recent})",
                        commit=commit_progress,
                    )
                continue
            
            # Create new Strava activity
            strava_activity = self._create_strava_activity(strava_account, activity_data)
            self.db.add(strava_activity)
            new_activities.append(strava_activity)
            new_count += 1
            
            # Mark for metrics calculation (will be calculated in batch later)
            # We don't calculate here to avoid blocking the sync process

            if job:
                commit_progress = idx % 5 == 0 or idx == total_recent
                self._update_sync_job(
                    job,
                    processed_activities=idx,
                    status_message=f"Processing Strava activities ({idx}/{total_recent})",
                    commit=commit_progress,
                )

        
        # Commit activities first so we can calculate metrics
        logger.info(f"[SYNC] Committing {new_count} new and {updated_count} updated activities to database...")
        self.db.commit()
        logger.info(f"[SYNC] Activities committed successfully")
        
        # Calculate metrics automatically for new activities
        metrics_calculated = 0
        metrics_recalculated = 0
        metrics_errors = 0
        logger.info(f"[SYNC] Starting metrics calculation phase...")
        metrics_total = len(new_activities) + len(updated_activities)
        metrics_processed = 0
        if job:
            self._update_sync_job(
                job,
                status_message="Calculating metrics for synchronized activities",
                metrics_phase=metrics_processed,
                metrics_phases_total=metrics_total,
            )
        
        # Process new activities
        if new_activities:
            logger.info(f"[SYNC][METRICS] Calculating metrics for {len(new_activities)} new activities")
            for idx, strava_activity in enumerate(new_activities, 1):
                try:
                    # Refresh to get the ID from DB
                    self.db.refresh(strava_activity)
                    logger.debug(f"[SYNC][METRICS] Processing activity {idx}/{len(new_activities)}: {strava_activity.strava_activity_id} - {strava_activity.name}")
                    
                    # Calculate metrics for this activity
                    training_metrics = self.calculate_activity_metrics(strava_activity, user_id)
                    self.db.add(training_metrics)
                    metrics_calculated += 1
                    metrics_processed += 1
                    
                    # Log progress every 10 activities to show the process is working
                    if idx % 10 == 0:
                        logger.info(f"[SYNC][METRICS] Processed {idx}/{len(new_activities)} new activities (calculated: {metrics_calculated}, errors: {metrics_errors})")
                    if job:
                        commit_progress = (metrics_processed % 5 == 0) or (metrics_processed == metrics_total)
                        self._update_sync_job(
                            job,
                            status_message=f"Calculating metrics ({metrics_processed}/{metrics_total})",
                            metrics_phase=metrics_processed,
                            metrics_phases_total=metrics_total,
                            commit=commit_progress,
                        )
                except Exception as e:
                    logger.error(f"[SYNC][METRICS] Error calculating metrics for activity {strava_activity.strava_activity_id}: {e}")
                    metrics_errors += 1
                    continue
            logger.info(f"[SYNC][METRICS] Completed processing {len(new_activities)} new activities (calculated: {metrics_calculated}, errors: {metrics_errors})")
        
        # Recalculate metrics for updated activities (in case TSS changed)
        if updated_activities:
            logger.info(f"[SYNC][METRICS] Recalculating metrics for {len(updated_activities)} updated activities")
            for idx, strava_activity in enumerate(updated_activities, 1):
                try:
                    logger.debug(f"[SYNC][METRICS] Recalculating activity {idx}/{len(updated_activities)}: {strava_activity.strava_activity_id} - {strava_activity.name}")
                    
                    # Recalculate metrics
                    training_metrics = self.calculate_activity_metrics(strava_activity, user_id)
                    # Update existing training metrics or create new
                    existing_metrics = self.db.execute(
                        select(TrainingMetrics)
                        .where(TrainingMetrics.strava_activity_id == strava_activity.id)
                    ).scalar_one_or_none()
                    
                    if existing_metrics:
                        # Update existing metrics
                        for key, value in training_metrics.__dict__.items():
                            if not key.startswith('_') and key != 'id':
                                setattr(existing_metrics, key, value)
                        logger.debug(f"[SYNC][METRICS] Updated existing metrics for activity {strava_activity.id}")
                    else:
                        # Create new metrics
                        training_metrics.strava_activity_id = strava_activity.id
                        self.db.add(training_metrics)
                        logger.debug(f"[SYNC][METRICS] Created new metrics for activity {strava_activity.id}")
                    
                    metrics_recalculated += 1
                    metrics_processed += 1
                    
                    # Log progress every 10 activities to show the process is working
                    if idx % 10 == 0:
                        logger.info(f"[SYNC][METRICS] Processed {idx}/{len(updated_activities)} updated activities (recalculated: {metrics_recalculated}, errors: {metrics_errors})")
                    if job:
                        commit_progress = (metrics_processed % 5 == 0) or (metrics_processed == metrics_total)
                        self._update_sync_job(
                            job,
                            status_message=f"Calculating metrics ({metrics_processed}/{metrics_total})",
                            metrics_phase=metrics_processed,
                            metrics_phases_total=metrics_total,
                            commit=commit_progress,
                        )
                except Exception as e:
                    logger.error(f"[SYNC][METRICS] Error recalculating metrics for activity {strava_activity.strava_activity_id}: {e}")
                    metrics_errors += 1
                    continue
            logger.info(f"[SYNC][METRICS] Completed processing {len(updated_activities)} updated activities (recalculated: {metrics_recalculated}, errors: {metrics_errors})")
        
        # Commit metrics (for both new and updated activities)
        if metrics_calculated > 0 or metrics_recalculated > 0:
            logger.info(f"[SYNC][METRICS] Committing {metrics_calculated + metrics_recalculated} metrics to database...")
            self.db.commit()
            logger.info(f"[SYNC][METRICS] Successfully committed metrics ({metrics_calculated} new, {metrics_recalculated} updated)")
        else:
            logger.info(f"[SYNC][METRICS] No metrics to commit")
        if job:
            self._update_sync_job(
                job,
                status_message="Updating daily metrics",
                metrics_phase=metrics_total,
                metrics_phases_total=metrics_total,
            )
        
        # After sync, recalculate daily metrics for all affected dates
        # This ensures consistency after sync
        daily_metrics_updated = 0
        if new_activities or updated_activities:
            logger.info(f"[SYNC][DAILY] Starting daily metrics update...")
            from app.services.daily_metrics_service import DailyMetricsService
            daily_metrics_service = DailyMetricsService(self.db)
            
            # Get all unique dates from new and updated activities
            affected_dates = set()
            for activity in new_activities + updated_activities:
                if activity.start_date:
                    affected_dates.add(activity.start_date.date())
            
            logger.info(f"[SYNC][DAILY] Updating daily metrics for {len(affected_dates)} affected dates")
            daily_total = len(affected_dates)
            if job and daily_total:
                self._update_sync_job(
                    job,
                    status_message=f"Updating daily metrics (0/{daily_total})",
                )
            
            # Update daily metrics for all affected dates
            for idx, activity_date in enumerate(sorted(affected_dates), 1):
                try:
                    logger.debug(f"[SYNC][DAILY] Updating daily metrics for date {activity_date} ({idx}/{len(affected_dates)})")
                    daily_metrics_service.update_daily_metrics(user_id, activity_date)
                    daily_metrics_updated += 1
                    if job and daily_total:
                        commit_progress = (idx % 5 == 0) or (idx == daily_total)
                        self._update_sync_job(
                            job,
                            status_message=f"Updating daily metrics ({idx}/{daily_total})",
                            commit=commit_progress,
                        )
                except Exception as e:
                    logger.warning(f"[SYNC][DAILY] Failed to update daily metrics for {activity_date} after sync: {e}")
            
            if daily_metrics_updated > 0:
                logger.info(f"[SYNC][DAILY] Committing daily metrics updates...")
                self.db.commit()
                logger.info(f"[SYNC][DAILY] Updated daily metrics for {daily_metrics_updated} dates")
            else:
                logger.warning(f"[SYNC][DAILY] No daily metrics were updated")
        else:
            logger.info(f"[SYNC][DAILY] No activities to update daily metrics for")
        
        result = {
            "total_activities": len(recent_activities),
            "new_activities": new_count,
            "updated_activities": updated_count,
            "already_synced": synced_count,
            "metrics_calculated": metrics_calculated,
            "metrics_recalculated": metrics_recalculated,
            "metrics_errors": metrics_errors,
            "daily_metrics_updated": daily_metrics_updated
        }
        
        logger.info(f"[SYNC] Sync completed successfully: {result}")
        if job:
            self._update_sync_job(
                job,
                status=StravaSyncJobStatus.SUCCESS,
                status_message="Sync completed successfully",
                finished_at=datetime.now(timezone.utc),
                result=result,
            )
        return result
    
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
    
    def _update_strava_activity(self, existing_activity: StravaActivity, 
                               activity_data: Dict[str, Any]) -> bool:
        """
        Update existing Strava activity with fresh data from API
        Returns True if any fields were updated, False otherwise
        """
        start_date = datetime.fromisoformat(activity_data["start_date"].replace("Z", "+00:00"))
        start_date_local = datetime.fromisoformat(activity_data["start_date_local"].replace("Z", "+00:00"))
        
        updated = False
        
        # Update fields that might change on Strava
        fields_to_check = {
            'name': activity_data.get("name"),
            'type': activity_data.get("type"),
            'sport_type': activity_data.get("sport_type"),
            'start_date': start_date,
            'start_date_local': start_date_local,
            'timezone': activity_data.get("timezone"),
            'distance': activity_data.get("distance"),
            'moving_time': activity_data.get("moving_time"),
            'elapsed_time': activity_data.get("elapsed_time"),
            'total_elevation_gain': activity_data.get("total_elevation_gain"),
            'average_speed': activity_data.get("average_speed"),
            'max_speed': activity_data.get("max_speed"),
            'average_heartrate': activity_data.get("average_heartrate"),
            'max_heartrate': activity_data.get("max_heartrate"),
            'average_watts': activity_data.get("average_watts"),
            'max_watts': activity_data.get("max_watts"),
            'weighted_average_watts': activity_data.get("weighted_average_watts"),
            'average_cadence': activity_data.get("average_cadence"),
            'temperature': activity_data.get("temp"),
            'feels_like': activity_data.get("feels_like"),
            'calories': activity_data.get("calories"),
            'kilojoules': activity_data.get("kilojoules"),
            'raw_data': activity_data
        }
        
        for field, new_value in fields_to_check.items():
            old_value = getattr(existing_activity, field, None)
            if old_value != new_value:
                setattr(existing_activity, field, new_value)
                updated = True
        
        # If activity was updated and has metrics, mark for recalculation
        if updated and existing_activity.metrics_calculated:
            existing_activity.metrics_calculated = False
        
        return updated
    
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
    
    def calculate_activity_metrics(
        self, 
        strava_activity: StravaActivity, 
        user_id: int, 
        fetch_streams: bool = True,
        skip_daily_update: bool = False
    ) -> TrainingMetrics:
        """
        Calculate training metrics for a Strava activity
        
        Args:
            strava_activity: Strava activity to calculate metrics for
            user_id: User ID to get threshold values from
            fetch_streams: Whether to fetch detailed HR streams (default: True, set False for bulk operations)
        
        Returns:
            TrainingMetrics object with calculated values
        """
        logger.debug(f"[METRICS] Calculating metrics for activity {strava_activity.strava_activity_id} (fetch_streams={fetch_streams})")
        
        # Get user's latest performance metrics (new unified structure)
        latest_metrics = self.db.execute(
            select(PerformanceMetrics)
            .where(PerformanceMetrics.user_id == user_id)
            .order_by(desc(PerformanceMetrics.test_date))
        ).scalar_one_or_none()
        
        if not latest_metrics:
            logger.debug(f"[METRICS] No performance metrics found for user {user_id}, using defaults")
        
        # Extract zones from PerformanceMetrics if available
        # Safely parse hr_zones in case it's stored as a JSON string
        hr_zones = None
        if latest_metrics and latest_metrics.hr_zones:
            hr_zones = self._parse_json_field(latest_metrics.hr_zones)
            if hr_zones:
                logger.debug(f"[METRICS] Using HR zones from performance metrics")
            else:
                logger.debug(f"[METRICS] Failed to parse HR zones from performance metrics")
        
        # Get threshold values
        threshold_hr = latest_metrics.threshold_hr if latest_metrics else None
        threshold_power = latest_metrics.ftp if latest_metrics else None
        max_hr = latest_metrics.hr_max if latest_metrics else None
        resting_hr = latest_metrics.hr_rest if latest_metrics else None
        
        # If no zones provided, try to calculate them
        # Priority: LTHR > Max HR > skip (will use fallback in calculate_time_in_zones)
        if hr_zones is None and threshold_hr:
            # Use LTHR-based zones (Joe Friel's formula)
            hr_zones = self._calculate_lthr_zones(threshold_hr)
            logger.debug(f"[METRICS] Calculated LTHR-based zones (threshold_hr={threshold_hr})")
        elif hr_zones is None and max_hr:
            # Fallback to max HR-based zones if LTHR not available
            hr_zones = self._calculate_maxhr_zones(max_hr)
            logger.debug(f"[METRICS] Calculated Max HR-based zones (max_hr={max_hr})")
        elif hr_zones is None:
            logger.debug(f"[METRICS] No HR zones available, will use fallback in calculate_time_in_zones")
        
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
        
        # Calculate time in zones using real HR data from Strava streams
        time_in_zones = {}
        hr_data = None
        
        # Try to fetch detailed HR data from Strava streams
        # Skip during bulk recalculation to avoid blocking (can be slow with many activities)
        hr_data = None
        if fetch_streams and strava_activity.strava_account:
            logger.debug(f"[METRICS] Fetching HR streams for activity {strava_activity.strava_activity_id}...")
            try:
                streams = self.fetch_activity_streams(
                    strava_account=strava_activity.strava_account,
                    activity_id=strava_activity.strava_activity_id,
                    stream_types=['heartrate', 'time'],
                    timeout=3  # Short timeout to avoid blocking
                )
                
                if 'heartrate' in streams and streams['heartrate'].get('data'):
                    hr_data = streams['heartrate']['data']
                    logger.debug(f"[METRICS] Fetched {len(hr_data)} HR data points for activity {strava_activity.id}")
                else:
                    logger.debug(f"[METRICS] No HR data in streams response for activity {strava_activity.id}")
            except Exception as e:
                # Log but don't fail - we can still calculate zones with average HR
                logger.debug(f"[METRICS] Failed to fetch HR streams for activity {strava_activity.id}: {e}")
                hr_data = None
        elif not fetch_streams:
            logger.debug(f"[METRICS] Skipping HR streams fetch (fetch_streams=False) for activity {strava_activity.id}")
        elif not strava_activity.strava_account:
            logger.debug(f"[METRICS] Skipping HR streams fetch (no strava_account) for activity {strava_activity.id}")
        
        # Calculate zones with real HR data or fallback to average HR
        if strava_activity.average_heartrate:
            logger.debug(f"[METRICS] Calculating time in zones (avg_hr={strava_activity.average_heartrate}, duration={duration_seconds}s)")
            time_in_zones = self.metrics_service.calculate_time_in_zones(
                hr_data=hr_data,
                zones=hr_zones,
                duration_seconds=duration_seconds,
                avg_hr=strava_activity.average_heartrate
            )
            # Ensure time_in_zones is a dict (safety check)
            if not isinstance(time_in_zones, dict):
                logger.warning(f"[METRICS] time_in_zones is not a dict (type: {type(time_in_zones)}), using defaults")
                time_in_zones = {'z1': 0, 'z2': 0, 'z3': 0, 'z4': 0, 'z5': 0}
            logger.debug(f"[METRICS] Time in zones calculated: {time_in_zones}")
        else:
            logger.debug(f"[METRICS] No average HR available, skipping zone calculation")
            time_in_zones = {'z1': 0, 'z2': 0, 'z3': 0, 'z4': 0, 'z5': 0}
        
        # Get or create TrainingMetrics record (update if exists, create if not)
        existing_metrics = self.db.execute(
            select(TrainingMetrics)
            .where(TrainingMetrics.strava_activity_id == strava_activity.id)
        ).scalar_one_or_none()
        
        if existing_metrics:
            # Update existing metrics
            existing_metrics.tss = tss
            existing_metrics.normalized_power = strava_activity.weighted_average_watts
            existing_metrics.intensity_factor = intensity_factor
            existing_metrics.trimp = trimp
            existing_metrics.time_in_zone_1 = time_in_zones.get('z1', 0)
            existing_metrics.time_in_zone_2 = time_in_zones.get('z2', 0)
            existing_metrics.time_in_zone_3 = time_in_zones.get('z3', 0)
            existing_metrics.time_in_zone_4 = time_in_zones.get('z4', 0)
            existing_metrics.time_in_zone_5 = time_in_zones.get('z5', 0)
            existing_metrics.zone_distribution = {
                "z1": time_in_zones.get('z1', 0),
                "z2": time_in_zones.get('z2', 0),
                "z3": time_in_zones.get('z3', 0),
                "z4": time_in_zones.get('z4', 0),
                "z5": time_in_zones.get('z5', 0)
            }
            training_metrics = existing_metrics
        else:
            # Create new TrainingMetrics record
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
            self.db.add(training_metrics)
        
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
        
        # Update daily metrics for this activity's date (skip during bulk recalculation for performance)
        if not skip_daily_update and strava_activity.start_date:
            activity_date = strava_activity.start_date.date()
            from app.services.daily_metrics_service import DailyMetricsService
            daily_metrics_service = DailyMetricsService(self.db)
            try:
                logger.debug(f"[METRICS] Updating daily metrics for date {activity_date}")
                daily_metrics_service.update_daily_metrics(user_id, activity_date)
            except Exception as e:
                logger.warning(f"[METRICS] Failed to update daily metrics for {activity_date}: {e}")
        
        logger.debug(f"[METRICS] Completed metrics calculation for activity {strava_activity.strava_activity_id} (TSS={tss}, TRIMP={trimp}, IF={intensity_factor})")
        return training_metrics
    
    def recalculate_all_metrics(
        self, 
        user_id: int, 
        job: Optional[StravaSyncJob] = None,
        months_back: int = 12
    ) -> Dict[str, Any]:
        """
        Recalculate metrics for activities within the specified time window
        
        This is called on first Strava connection and when user explicitly requests recalculation
        
        Args:
            user_id: User ID to recalculate metrics for
            job: Optional job object to track progress
            months_back: Number of months to look back (default: 12)
        
        Returns:
            Dictionary with recalculation results
        """
        start_time = datetime.now()
        logger.info(f"[RECALC] Starting recalculation for user {user_id} at {start_time.isoformat()}")
        
        # Update job status if provided
        if job:
            self._update_sync_job(
                job,
                status=StravaSyncJobStatus.RUNNING,
                status_message="Recalculation started",
                started_at=datetime.now(timezone.utc),
            )
        
        # Get user's Strava account
        strava_account = self.db.execute(
            select(StravaAccount)
            .where(StravaAccount.user_id == user_id)
        ).scalar_one_or_none()
        
        if not strava_account:
            logger.error(f"[RECALC] No Strava account found for user {user_id}")
            error_msg = "No Strava account found for user"
            if job:
                self._update_sync_job(
                    job,
                    status=StravaSyncJobStatus.FAILED,
                    status_message=error_msg,
                    error=error_msg,
                    finished_at=datetime.now(timezone.utc),
                )
            raise Exception(error_msg)
        
        logger.info(f"[RECALC] Found Strava account {strava_account.id} for user {user_id}")
        
        # Calculate cutoff date based on months_back
        cutoff_date = datetime.now() - timedelta(days=months_back * 30)
        logger.info(f"[RECALC] Filtering activities from last {months_back} months (since {cutoff_date.date()})...")
        
        # Recalculate activities in the specified time window (force recalculation)
        logger.info(f"[RECALC] Fetching activities for recalculation (forcing recalculation of existing metrics)...")
        activities = self.db.execute(
            select(StravaActivity)
            .where(
                and_(
                    StravaActivity.strava_account_id == strava_account.id,
                    StravaActivity.start_date >= cutoff_date
                )
            )
            .order_by(StravaActivity.start_date)
        ).scalars().all()
        activities_count = len(activities)
        logger.info(f"[RECALC] Found {activities_count} activities to recalculate (last {months_back} months)")
        
        logger.info(f"[RECALC] Activities needing metrics: {activities_count}")
        
        # Update job with total activities
        if job:
            self._update_sync_job(
                job,
                total_activities=activities_count,
                status_message=f"Found {activities_count} activities to process",
            )
        
        if activities_count == 0:
            logger.info(f"[RECALC] No activities to process. Recalculation complete.")
            result = {
                "activities_processed": 0,
                "metrics_calculated": 0,
                "errors": 0,
                "duration_seconds": (datetime.now() - start_time).total_seconds()
            }
            if job:
                self._update_sync_job(
                    job,
                    status=StravaSyncJobStatus.SUCCESS,
                    status_message="No activities to process",
                    processed_activities=0,
                    result=result,
                    finished_at=datetime.now(timezone.utc),
                )
            return result
        
        metrics_calculated = {
            'tss_calculated': 0,
            'trimp_calculated': 0,
            'if_calculated': 0,
            'zones_calculated': 0
        }
        
        activities_processed = 0
        errors_count = 0
        
        logger.info(f"[RECALC] Processing {len(activities)} activities (fetch_streams=False for performance)...")
        
        for idx, activity in enumerate(activities, start=1):
            # Recalculate metrics for all activities (both with and without existing metrics)
            # Disable streams fetch during bulk recalculation to avoid blocking
            try:
                logger.debug(f"[RECALC] Processing activity {idx}/{len(activities)}: {activity.strava_activity_id} - {activity.name}")
                # Skip daily metrics update during bulk recalculation - will do batch update at the end
                self.calculate_activity_metrics(activity, user_id, fetch_streams=False, skip_daily_update=True)
                
                # Debug zones calculation
                if activity.average_heartrate:
                    zones_sum = (activity.time_in_zone_1 or 0) + (activity.time_in_zone_2 or 0) + \
                                (activity.time_in_zone_3 or 0) + (activity.time_in_zone_4 or 0) + (activity.time_in_zone_5 or 0)
                    if zones_sum == 0:
                        logger.warning(f"[RECALC][ZONES] Activity {activity.id} '{activity.name}' has HR={activity.average_heartrate} but zones are 0")
                
                metrics_calculated['tss_calculated'] += 1 if activity.tss else 0
                metrics_calculated['trimp_calculated'] += 1 if activity.trimp else 0
                metrics_calculated['if_calculated'] += 1 if activity.intensity_factor else 0
                metrics_calculated['zones_calculated'] += 1 if (activity.time_in_zone_1 or activity.time_in_zone_2 or activity.time_in_zone_3) else 0
                
                activities_processed += 1
                
                # Commit periodically to avoid memory issues with large datasets
                if idx % 50 == 0:
                    self.db.commit()
                    logger.debug(f"[RECALC] Committed progress at {idx}/{len(activities)}")
                
                # Update job progress every 25 activities
                if job and idx % 25 == 0:
                    self._update_sync_job(
                        job,
                        processed_activities=idx,
                        status_message=f"Processing activities: {idx}/{len(activities)}",
                        commit=False,  # Don't commit on every update to avoid overhead
                    )
                if idx % 25 == 0:
                    logger.info(f"[RECALC] Processed {idx}/{len(activities)} activities (tss={metrics_calculated['tss_calculated']}, trimp={metrics_calculated['trimp_calculated']}, if={metrics_calculated['if_calculated']}, zones={metrics_calculated['zones_calculated']})")
            except Exception as e:
                logger.error(f"[RECALC] Error calculating metrics for activity {activity.id}: {e}", exc_info=True)
                errors_count += 1
                # Continue with next activity even if one fails
                continue
        
        logger.info(f"[RECALC] Finished processing activities: {activities_processed} processed, {errors_count} errors")
        
        # Update job with activities processed
        if job:
            self._update_sync_job(
                job,
                processed_activities=activities_processed,
                metrics_phase=1,
                metrics_phases_total=3,
                status_message=f"Processed {activities_processed} activities, committing changes...",
            )
        
        # Commit all remaining changes (both new metrics added and existing ones updated)
        logger.info(f"[RECALC] Committing final metrics updates...")
        self.db.commit()
        logger.info(f"[RECALC] Metrics commit complete")
        
        # Calculate initial CTL/ATL/TSB
        logger.info(f"[RECALC] Calculating initial CTL/ATL/TSB (42-day window)...")
        if job:
            self._update_sync_job(
                job,
                metrics_phase=2,
                status_message="Calculating fitness metrics (CTL/ATL/TSB)...",
            )
        initial_metrics = self._calculate_initial_fitness_metrics(user_id)
        logger.info(f"[RECALC] Initial metrics calculated: {initial_metrics}")
        
        # Batch update daily metrics for all affected dates (more efficient than per-activity updates)
        logger.info(f"[RECALC] Creating/updating daily metrics in batch...")
        if job:
            self._update_sync_job(
                job,
                metrics_phase=3,
                status_message="Updating daily metrics (batch)...",
            )
        from app.services.daily_metrics_service import DailyMetricsService
        daily_metrics_service = DailyMetricsService(self.db)
        
        # Get all unique dates from activities in the time window that have metrics
        unique_dates = set()
        all_activities_with_metrics = self.db.execute(
            select(StravaActivity)
            .where(
                and_(
                    StravaActivity.strava_account_id == strava_account.id,
                    StravaActivity.start_date >= cutoff_date,
                    StravaActivity.tss.isnot(None)
                )
            )
        ).scalars().all()
        
        for activity in all_activities_with_metrics:
            if activity.start_date:
                activity_date = activity.start_date.date()
                unique_dates.add(activity_date)
        
        # Update daily metrics for each date (skip advanced metrics and propagation for speed)
        logger.info(f"[RECALC] Updating daily metrics for {len(unique_dates)} unique dates...")
        daily_metrics_updated = 0
        for idx, activity_date in enumerate(sorted(unique_dates), 1):
            try:
                logger.debug(f"[RECALC] Updating daily metrics for date {activity_date} ({idx}/{len(unique_dates)})")
                # Skip advanced metrics and propagation during bulk update - will do at end
                daily_metrics_service.update_daily_metrics(
                    user_id, 
                    activity_date, 
                    propagate=False, 
                    skip_advanced_metrics=True
                )
                daily_metrics_updated += 1
                
                # Update job progress periodically
                if job and idx % 10 == 0:
                    self._update_sync_job(
                        job,
                        status_message=f"Updating daily metrics ({idx}/{len(unique_dates)})...",
                    )
            except Exception as e:
                logger.warning(f"[RECALC] Failed to update daily metrics for {activity_date}: {e}")
        
        # After all dates updated, propagate forward once (from earliest date to today)
        # Skip advanced metrics during propagation for speed
        if unique_dates:
            earliest_date = min(unique_dates)
            logger.info(f"[RECALC] Propagating metrics forward from {earliest_date} to today...")
            if job:
                self._update_sync_job(
                    job,
                    status_message="Propagating metrics forward...",
                )
            daily_metrics_service._propagate_metrics_forward(
                user_id, 
                earliest_date, 
                date.today(),
                skip_advanced_metrics=True
            )
        
        if daily_metrics_updated > 0:
            self.db.commit()
        
        logger.info(f"[RECALC] Daily metrics updated: {daily_metrics_updated}/{len(unique_dates)}")
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        result = {
            'success': True,
            'activities_processed': activities_processed,
            'metrics_calculated': metrics_calculated,
            'daily_metrics_updated': daily_metrics_updated,
            'initial_ctl': initial_metrics.get('ctl'),
            'initial_atl': initial_metrics.get('atl'),
            'initial_tsb': initial_metrics.get('tsb'),
            'processing_time_seconds': round(processing_time, 2),
            'errors': errors_count
        }
        
        logger.info(f"[RECALC] Completed at {end_time.isoformat()} in {processing_time:.2f}s. Result: {result}")
        
        # Update job with final result
        if job:
            self._update_sync_job(
                job,
                status=StravaSyncJobStatus.SUCCESS,
                status_message=f"Recalculation complete: {activities_processed} activities processed",
                processed_activities=activities_processed,
                result=result,
                finished_at=datetime.now(timezone.utc),
            )
        
        return result
    
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
    
    # _create_weekly_summaries method removed - now using daily metrics instead

