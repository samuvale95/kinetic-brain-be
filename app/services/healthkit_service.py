"""
Service for handling Apple HealthKit integration.
Manages HealthKit workouts, matching with planned workouts, and syncing health data.
"""
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_
from datetime import datetime, timedelta, date
from loguru import logger

from app.models.healthkit import HealthKitWorkout
from app.models.workout import Workout, WorkoutSession, WorkoutStatus
from app.models.daily_metrics import DailyReadinessMetrics
from app.models.user import UserProfile
from app.services.workout_matching_service import WorkoutMatchingService
from app.services.diary_service import DiaryService
from app.services.workout_parameters import normalize_sport_type


class HealthKitService:
    """Service for HealthKit integration"""
    
    # Mapping HealthKit workout types to app types
    HEALTHKIT_TYPE_MAPPING = {
        "running": "run",
        "cycling": "bike",
        "swimming": "swim",
        "walking": "walk",
        "hiking": "hike",
        "elliptical": "elliptical",
        "rowing": "row",
        "strengthTraining": "strength",
        "traditionalStrengthTraining": "strength",
        "yoga": "yoga",
        "pilates": "pilates",
        "coreTraining": "core"
    }
    
    def __init__(self, db: Session):
        self.db = db
        self.matching_service = WorkoutMatchingService()
        self.diary_service = DiaryService(db)
    
    def create_or_update_workout(self, user_id: int, workout_data: dict) -> HealthKitWorkout:
        """
        Create or update HealthKitWorkout.
        
        If workout with same UUID exists, update it.
        Otherwise, create new one.
        """
        hk_uuid = workout_data.get("hk_workout_uuid")
        
        if not hk_uuid:
            raise ValueError("hk_workout_uuid is required")
        
        # Check if workout already exists
        existing = self.db.execute(
            select(HealthKitWorkout)
            .where(HealthKitWorkout.hk_workout_uuid == hk_uuid)
        ).scalar_one_or_none()
        
        if existing:
            # Update existing workout
            logger.info(f"[HEALTHKIT] Updating existing workout {existing.id} with UUID {hk_uuid}")
            return self._update_workout(existing, workout_data)
        else:
            # Create new workout
            logger.info(f"[HEALTHKIT] Creating new workout with UUID {hk_uuid}")
            return self._create_workout(user_id, workout_data)
    
    def _create_workout(self, user_id: int, workout_data: dict) -> HealthKitWorkout:
        """Create new HealthKitWorkout"""
        # Convert HealthKit type to app type
        hk_type = workout_data.get("workout_type", "").lower()
        app_type = self._convert_healthkit_type_to_app_type(hk_type)
        
        workout = HealthKitWorkout(
            user_id=user_id,
            hk_workout_uuid=workout_data.get("hk_workout_uuid"),
            hk_source_name=workout_data.get("hk_source_name"),
            workout_type=app_type,
            start_date=workout_data.get("start_date"),
            end_date=workout_data.get("end_date"),
            duration_seconds=workout_data.get("duration_seconds"),
            total_distance_meters=workout_data.get("total_distance_meters"),
            total_energy_burned_kcal=workout_data.get("total_energy_burned_kcal"),
            total_basal_energy_kcal=workout_data.get("total_basal_energy_kcal"),
            elevation_gain_meters=workout_data.get("elevation_gain_meters"),
            elevation_loss_meters=workout_data.get("elevation_loss_meters"),
            hk_metadata=workout_data.get("metadata"),
            sync_status="pending"
        )
        
        self.db.add(workout)
        self.db.flush()
        
        return workout
    
    def _update_workout(self, workout: HealthKitWorkout, workout_data: dict) -> HealthKitWorkout:
        """Update existing HealthKitWorkout"""
        # Update fields if provided
        if "workout_type" in workout_data:
            hk_type = workout_data["workout_type"].lower()
            workout.workout_type = self._convert_healthkit_type_to_app_type(hk_type)
        
        if "start_date" in workout_data:
            workout.start_date = workout_data["start_date"]
        if "end_date" in workout_data:
            workout.end_date = workout_data["end_date"]
        if "duration_seconds" in workout_data:
            workout.duration_seconds = workout_data["duration_seconds"]
        if "total_distance_meters" in workout_data:
            workout.total_distance_meters = workout_data["total_distance_meters"]
        if "total_energy_burned_kcal" in workout_data:
            workout.total_energy_burned_kcal = workout_data["total_energy_burned_kcal"]
        if "total_basal_energy_kcal" in workout_data:
            workout.total_basal_energy_kcal = workout_data["total_basal_energy_kcal"]
        if "elevation_gain_meters" in workout_data:
            workout.elevation_gain_meters = workout_data["elevation_gain_meters"]
        if "elevation_loss_meters" in workout_data:
            workout.elevation_loss_meters = workout_data["elevation_loss_meters"]
        if "metadata" in workout_data:
            workout.hk_metadata = workout_data["metadata"]
        
        return workout
    
    def match_workout_to_planned(self, healthkit_workout: HealthKitWorkout) -> Optional[Workout]:
        """
        Find planned workout that matches this HealthKit workout.
        
        Uses WorkoutMatchingService for consistent matching logic.
        """
        # Get planned workouts for matching
        date_window_start = healthkit_workout.start_date - timedelta(days=3)
        date_window_end = healthkit_workout.start_date + timedelta(days=3)
        
        planned_workouts = WorkoutMatchingService.get_planned_workouts_for_matching(
            db=self.db,
            user_id=healthkit_workout.user_id,
            date_window_start=date_window_start,
            date_window_end=date_window_end,
            workout_type=healthkit_workout.workout_type
        )
        
        # Match using matching service
        match_result = WorkoutMatchingService.match_workout(
            activity_type=healthkit_workout.workout_type,
            activity_date=healthkit_workout.start_date,
            activity_duration_seconds=healthkit_workout.duration_seconds,
            activity_distance_meters=healthkit_workout.total_distance_meters,
            planned_workouts=planned_workouts
        )
        
        if match_result:
            matched_workout, score = match_result
            logger.info(
                f"[HEALTHKIT] Matched workout {healthkit_workout.id} "
                f"to planned workout {matched_workout.id} (score: {score})"
            )
            return matched_workout
        
        logger.debug(
            f"[HEALTHKIT] No match found for workout {healthkit_workout.id}"
        )
        return None
    
    def create_workout_session_from_healthkit(
        self,
        healthkit_workout: HealthKitWorkout,
        workout: Optional[Workout] = None,
        metrics: Optional[Dict[str, Any]] = None,
        intervals: Optional[Dict[str, Any]] = None
    ) -> WorkoutSession:
        """
        Create WorkoutSession from HealthKitWorkout.
        
        If workout is provided, link session to it.
        Otherwise, create standalone session.
        """
        # Extract metrics from healthkit_workout or provided metrics dict
        metrics = metrics or {}
        
        # Calculate duration in minutes
        duration_minutes = healthkit_workout.duration_seconds // 60
        
        # Create session
        session = WorkoutSession(
            workout_id=workout.id if workout else healthkit_workout.workout_id or 0,
            user_id=healthkit_workout.user_id,
            actual_date=healthkit_workout.start_date,
            duration_minutes=duration_minutes,
            source="healthkit",
            healthkit_workout_id=healthkit_workout.id,
            healthkit_uuid=healthkit_workout.hk_workout_uuid,
            # Extract metrics
            avg_hr=metrics.get("avg_heart_rate"),
            max_hr=metrics.get("max_heart_rate"),
            avg_pace=self._convert_pace_to_min_per_km(metrics.get("avg_pace_seconds_per_km")),
            avg_power=metrics.get("avg_power"),
            # HealthKit specific fields
            active_energy_kcal=healthkit_workout.total_energy_burned_kcal,
            basal_energy_kcal=healthkit_workout.total_basal_energy_kcal,
            vo2_max=metrics.get("vo2_max"),
            running_power_avg=metrics.get("running_power_avg"),
            running_power_max=metrics.get("running_power_max"),
            ground_contact_time_avg=metrics.get("ground_contact_time_avg"),
            vertical_oscillation_avg=metrics.get("vertical_oscillation_avg"),
            stride_length_avg=metrics.get("stride_length_avg"),
            intervals_data=intervals
        )
        
        self.db.add(session)
        self.db.flush()
        
        # Calculate advanced metrics
        try:
            self._calculate_and_store_metrics_for_session(session)
        except Exception as e:
            logger.warning(f"[HEALTHKIT] Failed to calculate metrics for session {session.id}: {e}")
        
        # Update workout status if matched
        if workout:
            workout.status = WorkoutStatus.COMPLETED
            healthkit_workout.workout_id = workout.id
            healthkit_workout.sync_status = "matched"
        else:
            healthkit_workout.sync_status = "synced"
        
        self.db.commit()
        self.db.refresh(session)
        
        return session
    
    def update_diary_entry_from_healthkit(
        self,
        user_id: int,
        date_str: str,
        metrics: dict
    ) -> DailyReadinessMetrics:
        """
        Update DailyReadinessMetrics with HealthKit data.
        
        Uses DiaryService to maintain consistency with manual entries.
        """
        # Parse date
        try:
            metric_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError(f"Invalid date format: {date_str}. Expected YYYY-MM-DD")
        
        # Prepare inputs for DiaryService
        inputs = {
            "hrv_value": metrics.get("hrv_value"),
            "rhr_value": metrics.get("rhr_value"),
            "sleep_hours": metrics.get("sleep_hours"),
            "sleep_quality_score": metrics.get("sleep_quality_score"),
            "epoc": metrics.get("epoc"),
            "hydration_status": metrics.get("hydration_status"),
            "hydration_score": metrics.get("hydration_score"),
            "nutrition_score": metrics.get("nutrition_score"),
            "weight_delta_kg": metrics.get("weight_kg")  # HealthKit provides weight, not delta
        }
        
        # Remove None values
        inputs = {k: v for k, v in inputs.items() if v is not None}
        
        # Use DiaryService to upsert
        record = self.diary_service.upsert_readiness_entry(
            user_id=user_id,
            metric_date=metric_date,
            inputs=inputs
        )
        
        # Update HealthKit sync fields
        record.source = "healthkit"
        record.healthkit_sync_date = datetime.now()
        if metrics.get("sync_anchor"):
            record.healthkit_sync_anchor = metrics.get("sync_anchor")
        
        self.db.commit()
        self.db.refresh(record)
        
        return record
    
    def format_workout_for_watch(self, workout: Workout, user_profile: UserProfile) -> dict:
        """
        Format workout for Apple Watch.
        
        Converts workout structure and zones to WatchOS format.
        """
        # Get user's performance metrics for zones
        from app.models.user import PerformanceMetrics
        perf_metrics = self.db.execute(
            select(PerformanceMetrics)
            .where(PerformanceMetrics.user_id == user_profile.user_id)
            .order_by(PerformanceMetrics.created_at.desc())
        ).scalar_first()
        
        # Parse workout structure
        structure = workout.structure_json or {}
        sport = structure.get("sport", workout.type)
        
        # Format structure for Watch
        watch_structure = self._format_structure_for_watch(structure, perf_metrics)
        
        # Format zones
        zones = self._format_zones_for_watch(perf_metrics, sport)
        
        return {
            "workout_id": workout.id,
            "title": workout.title,
            "type": workout.type,
            "sport": sport,
            "duration_minutes": workout.duration_minutes,
            "structure": watch_structure,
            "zones": zones
        }
    
    def _format_structure_for_watch(self, structure: dict, perf_metrics) -> dict:
        """Format workout structure for WatchOS"""
        segments = structure.get("segments", [])
        watch_structure = {}
        
        for segment in segments:
            segment_type = segment.get("segment_type", "").lower()
            steps = segment.get("steps", [])
            
            if segment_type == "warmup":
                watch_structure["warmup"] = self._format_segment_for_watch(segment, perf_metrics)
            elif segment_type == "cooldown":
                watch_structure["cooldown"] = self._format_segment_for_watch(segment, perf_metrics)
            elif segment_type == "main":
                # Main segment can have multiple intervals
                if "main" not in watch_structure:
                    watch_structure["main"] = []
                watch_structure["main"].append(self._format_segment_for_watch(segment, perf_metrics))
        
        return watch_structure
    
    def _format_segment_for_watch(self, segment: dict, perf_metrics) -> dict:
        """Format a single segment for WatchOS"""
        steps = segment.get("steps", [])
        
        # Calculate total duration
        total_duration = sum(
            step.get("duration", {}).get("value", 0) 
            for step in steps 
            if isinstance(step.get("duration"), dict)
        )
        
        # Extract target zone and HR from first step
        target_zone = None
        target_hr_min = None
        target_hr_max = None
        
        if steps:
            first_step = steps[0]
            target = first_step.get("target", {})
            if isinstance(target, dict):
                if target.get("type") == "zone":
                    target_zone = target.get("zone")
                    # Get HR range for zone
                    if perf_metrics and perf_metrics.hr_zones:
                        hr_zones = perf_metrics.hr_zones
                        if isinstance(hr_zones, dict) and target_zone:
                            zone_range = hr_zones.get(target_zone.lower(), "")
                            if zone_range:
                                # Parse range like "120-135"
                                parts = zone_range.split("-")
                                if len(parts) == 2:
                                    target_hr_min = float(parts[0])
                                    target_hr_max = float(parts[1])
        
        return {
            "duration_seconds": total_duration,
            "description": segment.get("name", ""),
            "target_zone": target_zone,
            "target_hr_min": target_hr_min,
            "target_hr_max": target_hr_max
        }
    
    def _format_zones_for_watch(self, perf_metrics, sport: str) -> dict:
        """Format training zones for WatchOS"""
        zones = {}
        
        if not perf_metrics:
            return zones
        
        # HR zones
        if perf_metrics.hr_zones:
            zones["hr"] = self._parse_zone_ranges(perf_metrics.hr_zones)
        
        # Pace zones (for running)
        if sport.lower() in ["run", "running"] and perf_metrics.pace_zones:
            zones["pace"] = self._parse_zone_ranges(perf_metrics.pace_zones)
        
        # Power zones (for cycling)
        if sport.lower() in ["bike", "cycling"] and perf_metrics.power_zones:
            zones["power"] = self._parse_zone_ranges(perf_metrics.power_zones)
        
        return zones
    
    def _parse_zone_ranges(self, zone_dict: dict) -> dict:
        """Parse zone ranges from string format to min/max dict"""
        parsed = {}
        for zone, range_str in zone_dict.items():
            if isinstance(range_str, str):
                parts = range_str.split("-")
                if len(parts) == 2:
                    parsed[zone] = {
                        "min": float(parts[0]),
                        "max": float(parts[1])
                    }
        return parsed
    
    def _convert_healthkit_type_to_app_type(self, hk_type: str) -> str:
        """Convert HealthKit workout type to app type"""
        hk_type_lower = hk_type.lower()
        return self.HEALTHKIT_TYPE_MAPPING.get(hk_type_lower, hk_type_lower)
    
    def _convert_pace_to_min_per_km(self, pace_seconds_per_km: Optional[float]) -> Optional[float]:
        """Convert pace from seconds/km to min/km"""
        if pace_seconds_per_km is None:
            return None
        return pace_seconds_per_km / 60.0
    
    def _calculate_and_store_metrics_for_session(self, session: WorkoutSession):
        """
        Calculate and store training metrics for a WorkoutSession.
        
        Creates TrainingMetrics record linked to the session.
        """
        from app.models.training_metrics import TrainingMetrics
        from app.models.user import PerformanceMetrics
        
        # Get user's performance metrics
        perf_metrics = self.db.execute(
            select(PerformanceMetrics)
            .where(PerformanceMetrics.user_id == session.user_id)
            .order_by(PerformanceMetrics.created_at.desc())
        ).scalar_first()
        
        if not perf_metrics:
            logger.warning(f"[HEALTHKIT] No performance metrics found for user {session.user_id}")
            return
        
        # Calculate TSS
        tss = None
        if session.avg_hr and perf_metrics.threshold_hr:
            # Use HR-based TSS
            intensity_factor = session.avg_hr / perf_metrics.threshold_hr if perf_metrics.threshold_hr > 0 else None
            if intensity_factor:
                duration_hours = session.duration_minutes / 60.0
                tss = duration_hours * (intensity_factor ** 2) * 100
        elif session.avg_power and perf_metrics.ftp:
            # Use power-based TSS
            intensity_factor = session.avg_power / perf_metrics.ftp if perf_metrics.ftp > 0 else None
            if intensity_factor:
                duration_hours = session.duration_minutes / 60.0
                tss = duration_hours * (intensity_factor ** 2) * 100
        
        # Calculate TRIMP
        trimp = None
        if session.avg_hr and perf_metrics.hr_max and perf_metrics.hr_rest:
            hr_reserve = (session.avg_hr - perf_metrics.hr_rest) / (perf_metrics.hr_max - perf_metrics.hr_rest)
            if 0 <= hr_reserve <= 1:
                import math
                trimp = session.duration_minutes * hr_reserve * 0.64 * math.exp(1.92 * hr_reserve)
        
        # Calculate zone distribution from intervals if available
        zone_distribution = None
        time_in_zones = [0, 0, 0, 0, 0]
        
        if session.intervals_data:
            zone_distribution = self._calculate_zone_distribution_from_intervals(
                session.intervals_data,
                perf_metrics
            )
            if zone_distribution:
                # Extract time in zones (in minutes)
                for i in range(1, 6):
                    zone_key = f"z{i}"
                    if zone_key in zone_distribution:
                        time_in_zones[i-1] = int(zone_distribution[zone_key].get("minutes", 0))
        
        # Create TrainingMetrics record
        training_metrics = TrainingMetrics(
            workout_session_id=session.id,
            tss=tss,
            intensity_factor=intensity_factor if 'intensity_factor' in locals() else None,
            trimp=trimp,
            time_in_zone_1=time_in_zones[0],
            time_in_zone_2=time_in_zones[1],
            time_in_zone_3=time_in_zones[2],
            time_in_zone_4=time_in_zones[3],
            time_in_zone_5=time_in_zones[4],
            zone_distribution=zone_distribution
        )
        
        self.db.add(training_metrics)
    
    def _calculate_zone_distribution_from_intervals(
        self,
        intervals_data: dict,
        perf_metrics
    ) -> Optional[dict]:
        """Calculate zone distribution from intervals data"""
        if not intervals_data or not perf_metrics:
            return None
        
        # This is a simplified version - in practice, you'd analyze each interval
        # and calculate time spent in each HR zone
        # For now, return None to indicate zones weren't calculated from intervals
        return None

