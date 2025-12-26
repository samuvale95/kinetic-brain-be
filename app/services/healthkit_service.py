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
            # Extract metrics
            avg_hr=metrics.get("avg_heart_rate"),
            max_hr=metrics.get("max_heart_rate"),
            avg_pace=self._convert_pace_to_min_per_km(metrics.get("avg_pace_seconds_per_km")),
            avg_power=metrics.get("avg_power")
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
        Returns structure compatible with Apple Watch HKWorkoutPlan.
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
        
        # Normalize workout type for Watch
        normalized_type = self._normalize_workout_type_for_watch(workout.type)
        normalized_sport = self._normalize_sport_type_for_watch(sport)
        
        # Format structure for Watch
        watch_structure = self._format_structure_for_watch(structure, perf_metrics, normalized_sport)
        
        # Format zones
        zones = self._format_zones_for_watch(perf_metrics, normalized_sport)
        
        return {
            "workout_id": workout.id,
            "title": workout.title,
            "type": normalized_type,
            "sport": normalized_sport,
            "duration_minutes": workout.duration_minutes,
            "structure": watch_structure,
            "zones": zones
        }
    
    def _format_structure_for_watch(self, structure: dict, perf_metrics, sport: str) -> dict:
        """
        Format workout structure for WatchOS.
        
        Returns structure with warmup (WorkoutPhase), main (Array<WorkoutInterval>), 
        and cooldown (WorkoutPhase).
        """
        segments = structure.get("segments", [])
        watch_structure = {
            "warmup": None,
            "main": [],
            "cooldown": None
        }
        
        for segment in segments:
            segment_type = segment.get("segment_type", "").lower()
            
            if segment_type == "warmup":
                watch_structure["warmup"] = self._format_phase_for_watch(segment, perf_metrics, sport)
            elif segment_type == "cooldown":
                watch_structure["cooldown"] = self._format_phase_for_watch(segment, perf_metrics, sport)
            elif segment_type == "main":
                # Main segment can have multiple intervals
                intervals = self._format_intervals_for_watch(segment, perf_metrics, sport)
                watch_structure["main"].extend(intervals)
        
        # Ensure warmup and cooldown exist (create defaults if missing)
        if not watch_structure["warmup"]:
            watch_structure["warmup"] = self._create_default_phase("Riscaldamento", sport)
        if not watch_structure["cooldown"]:
            watch_structure["cooldown"] = self._create_default_phase("Defaticamento", sport)
        
        # If no main intervals, create a default steady interval from total duration
        if not watch_structure["main"]:
            # Calculate remaining time after warmup and cooldown
            warmup_duration = watch_structure["warmup"].get("duration_seconds", 600)
            cooldown_duration = watch_structure["cooldown"].get("duration_seconds", 600)
            # Default main duration (will be adjusted if we have total duration)
            main_duration = max(1800, 3600 - warmup_duration - cooldown_duration)  # At least 30 min or remaining time
            watch_structure["main"] = [{
                "type": "steady",
                "duration_seconds": int(main_duration),
                "description": "Fase principale",
                "target_zone": "Z2"
            }]
        
        return watch_structure
    
    def _format_phase_for_watch(self, segment: dict, perf_metrics, sport: str) -> dict:
        """
        Format a phase (warmup/cooldown) for WatchOS.
        
        Returns WorkoutPhase with duration_seconds, description, target_zone,
        and optional target_hr_min/max, target_pace_min/max, target_power_min/max.
        """
        steps = segment.get("steps", [])
        
        # Calculate total duration from all steps
        total_duration = 0
        target_values = {}
        target_zone = None
        description = segment.get("name", "")
        
        # Aggregate duration and extract target from steps
        for step in steps:
            duration = step.get("duration", {})
            if isinstance(duration, dict) and duration.get("type") == "time":
                total_duration += duration.get("seconds", 0)
            
            # Extract target from step
            target = step.get("target", {})
            if isinstance(target, dict):
                step_target = self._extract_target_values(target, perf_metrics, sport)
                if step_target:
                    # Merge target values (prefer first non-None value)
                    if not target_zone and step_target.get("target_zone"):
                        target_zone = step_target["target_zone"]
                    for key in ["target_hr_min", "target_hr_max", "target_pace_min", 
                               "target_pace_max", "target_power_min", "target_power_max"]:
                        if key not in target_values and step_target.get(key) is not None:
                            target_values[key] = step_target[key]
        
        # Build phase response
        phase = {
            "duration_seconds": total_duration,
            "description": description or "Fase allenamento"
        }
        
        if target_zone:
            phase["target_zone"] = target_zone
        
        # Add target values (only if both min and max are present)
        if target_values.get("target_hr_min") is not None and target_values.get("target_hr_max") is not None:
            phase["target_hr_min"] = int(target_values["target_hr_min"])
            phase["target_hr_max"] = int(target_values["target_hr_max"])
        
        if target_values.get("target_pace_min") is not None and target_values.get("target_pace_max") is not None:
            phase["target_pace_min"] = int(target_values["target_pace_min"])
            phase["target_pace_max"] = int(target_values["target_pace_max"])
        
        if target_values.get("target_power_min") is not None and target_values.get("target_power_max") is not None:
            phase["target_power_min"] = int(target_values["target_power_min"])
            phase["target_power_max"] = int(target_values["target_power_max"])
        
        return phase
    
    def _format_intervals_for_watch(self, segment: dict, perf_metrics, sport: str) -> list:
        """
        Format main segment intervals for WatchOS.
        
        Returns array of WorkoutInterval (interval or steady type).
        """
        steps = segment.get("steps", [])
        intervals = []
        
        for step in steps:
            step_type = step.get("step_type", "").lower()
            
            if step_type == "repeat":
                # Convert repeat block to interval with reps
                interval = self._format_repeat_as_interval(step, perf_metrics, sport)
                if interval:
                    intervals.append(interval)
            elif step_type in ["interval", "steady", "tempo", "recovery"]:
                # Convert single step to interval
                interval = self._format_step_as_interval(step, step_type, perf_metrics, sport)
                if interval:
                    intervals.append(interval)
        
        return intervals
    
    def _format_repeat_as_interval(self, repeat_step: dict, perf_metrics, sport: str) -> Optional[dict]:
        """
        Convert a repeat step to an interval with reps.
        
        Returns interval with type="interval", reps, work_seconds, recovery_seconds.
        """
        nested_steps = repeat_step.get("steps", [])
        reps = repeat_step.get("repeat", 1)
        
        if not nested_steps or reps < 1:
            return None
        
        # Find work and recovery steps
        work_step = None
        recovery_step = None
        
        for step in nested_steps:
            step_type = step.get("step_type", "").lower()
            if step_type in ["interval", "tempo"]:
                work_step = step
            elif step_type in ["recovery", "rest"]:
                recovery_step = step
        
        # If no explicit work/recovery, use first two steps
        if not work_step and nested_steps:
            work_step = nested_steps[0]
        if not recovery_step and len(nested_steps) > 1:
            recovery_step = nested_steps[1]
        
        if not work_step:
            return None
        
        # Extract work duration
        work_duration = work_step.get("duration", {})
        work_seconds = 0
        if isinstance(work_duration, dict) and work_duration.get("type") == "time":
            work_seconds = work_duration.get("seconds", 0)
        
        # Extract recovery duration
        recovery_seconds = 0
        if recovery_step:
            recovery_duration = recovery_step.get("duration", {})
            if isinstance(recovery_duration, dict) and recovery_duration.get("type") == "time":
                recovery_seconds = recovery_duration.get("seconds", 0)
        
        # Extract target values from work step
        target = work_step.get("target", {})
        target_values = self._extract_target_values(target, perf_metrics, sport) if isinstance(target, dict) else {}
        
        # Build interval
        interval = {
            "type": "interval",
            "reps": int(reps),
            "work_seconds": int(work_seconds),
            "recovery_seconds": int(recovery_seconds)
        }
        
        # Add description
        description = work_step.get("notes") or work_step.get("name") or "Intervalli"
        if description:
            interval["description"] = description
        
        # Add target values
        if target_values.get("target_zone"):
            interval["target_zone"] = target_values["target_zone"]
        
        if target_values.get("target_hr_min") is not None and target_values.get("target_hr_max") is not None:
            interval["target_hr_min"] = int(target_values["target_hr_min"])
            interval["target_hr_max"] = int(target_values["target_hr_max"])
        
        if target_values.get("target_pace_min") is not None and target_values.get("target_pace_max") is not None:
            interval["target_pace_min"] = int(target_values["target_pace_min"])
            interval["target_pace_max"] = int(target_values["target_pace_max"])
        
        if target_values.get("target_power_min") is not None and target_values.get("target_power_max") is not None:
            interval["target_power_min"] = int(target_values["target_power_min"])
            interval["target_power_max"] = int(target_values["target_power_max"])
        
        return interval
    
    def _format_step_as_interval(self, step: dict, step_type: str, perf_metrics, sport: str) -> Optional[dict]:
        """
        Convert a single step to an interval (steady type).
        
        Returns interval with type="steady" or type matching step_type, duration_seconds.
        """
        duration = step.get("duration", {})
        duration_seconds = 0
        
        if isinstance(duration, dict):
            if duration.get("type") == "time":
                duration_seconds = duration.get("seconds", 0)
            elif duration.get("type") == "distance":
                # Convert distance to approximate time (simplified)
                meters = duration.get("meters", 0)
                # Rough estimate: 4 min/km = 240 sec/km
                duration_seconds = int(meters * 240 / 1000)
        
        if duration_seconds == 0:
            return None
        
        # Extract target values
        target = step.get("target", {})
        target_values = self._extract_target_values(target, perf_metrics, sport) if isinstance(target, dict) else {}
        
        # Determine interval type
        interval_type = "steady"
        if step_type in ["interval", "tempo", "recovery"]:
            interval_type = step_type
        
        # Build interval
        interval = {
            "type": interval_type,
            "duration_seconds": int(duration_seconds)
        }
        
        # Add description
        description = step.get("notes") or step.get("name") or "Fase allenamento"
        if description:
            interval["description"] = description
        
        # Add target values
        if target_values.get("target_zone"):
            interval["target_zone"] = target_values["target_zone"]
        
        if target_values.get("target_hr_min") is not None and target_values.get("target_hr_max") is not None:
            interval["target_hr_min"] = int(target_values["target_hr_min"])
            interval["target_hr_max"] = int(target_values["target_hr_max"])
        
        if target_values.get("target_pace_min") is not None and target_values.get("target_pace_max") is not None:
            interval["target_pace_min"] = int(target_values["target_pace_min"])
            interval["target_pace_max"] = int(target_values["target_pace_max"])
        
        if target_values.get("target_power_min") is not None and target_values.get("target_power_max") is not None:
            interval["target_power_min"] = int(target_values["target_power_min"])
            interval["target_power_max"] = int(target_values["target_power_max"])
        
        return interval
    
    def _extract_target_values(self, target: dict, perf_metrics, sport: str) -> dict:
        """
        Extract target values (zone, HR, pace, power) from target dict.
        
        Returns dict with target_zone, target_hr_min/max, target_pace_min/max, target_power_min/max.
        """
        result = {}
        target_type = target.get("type", "")
        
        if target_type == "zone":
            zone = target.get("zone")
            if zone:
                result["target_zone"] = zone
                # Get HR, pace, power ranges from zones
                if perf_metrics:
                    # HR zones
                    if perf_metrics.hr_zones:
                        hr_range = self._get_zone_range(perf_metrics.hr_zones, zone)
                        if hr_range:
                            result["target_hr_min"] = hr_range["min"]
                            result["target_hr_max"] = hr_range["max"]
                    
                    # Pace zones (for running)
                    if sport.lower() in ["run", "running"] and perf_metrics.pace_zones:
                        pace_range = self._get_zone_range(perf_metrics.pace_zones, zone)
                        if pace_range:
                            result["target_pace_min"] = pace_range["min"]
                            result["target_pace_max"] = pace_range["max"]
                    
                    # Power zones (for cycling)
                    if sport.lower() in ["bike", "cycling"] and perf_metrics.power_zones:
                        power_range = self._get_zone_range(perf_metrics.power_zones, zone)
                        if power_range:
                            result["target_power_min"] = power_range["min"]
                            result["target_power_max"] = power_range["max"]
        
        elif target_type == "heart_rate":
            min_val = target.get("min_value")
            max_val = target.get("max_value")
            if min_val is not None:
                result["target_hr_min"] = float(min_val)
            if max_val is not None:
                result["target_hr_max"] = float(max_val)
        
        elif target_type == "pace":
            min_val = target.get("min_value")
            max_val = target.get("max_value")
            # Convert pace to seconds per km if needed
            if min_val is not None:
                result["target_pace_min"] = self._convert_pace_to_seconds_per_km(min_val, target.get("units"))
            if max_val is not None:
                result["target_pace_max"] = self._convert_pace_to_seconds_per_km(max_val, target.get("units"))
        
        elif target_type == "power":
            min_val = target.get("min_value")
            max_val = target.get("max_value")
            if min_val is not None:
                result["target_power_min"] = float(min_val)
            if max_val is not None:
                result["target_power_max"] = float(max_val)
        
        return result
    
    def _get_zone_range(self, zones_dict: dict, zone: str) -> Optional[dict]:
        """Get min/max range for a zone from zones dict"""
        if not zones_dict or not zone:
            return None
        
        zone_key = zone.lower()
        range_str = zones_dict.get(zone_key)
        
        if isinstance(range_str, str):
            # Parse "120-135" format
            parts = range_str.split("-")
            if len(parts) == 2:
                try:
                    return {
                        "min": int(float(parts[0].strip())),
                        "max": int(float(parts[1].strip()))
                    }
                except ValueError:
                    pass
        
        return None
    
    def _convert_pace_to_seconds_per_km(self, pace_value: float, units: Optional[str] = None) -> int:
        """
        Convert pace value to seconds per km.
        
        Supports: min/km (e.g., 5.0 = 5:00/km = 300 sec/km),
                 sec/km (already in correct format),
                 min/mile (converted to sec/km).
        """
        if units == "sec/km" or units == "seconds_per_km":
            return int(pace_value)
        elif units == "min/mile" or units == "minutes_per_mile":
            # Convert min/mile to sec/km: 1 mile = 1.609344 km
            return int(pace_value * 60 * 1.609344)
        else:
            # Default: assume min/km
            return int(pace_value * 60)
    
    def _create_default_phase(self, description: str, sport: str) -> dict:
        """Create a default phase (warmup/cooldown) with minimal structure"""
        return {
            "duration_seconds": 600,  # 10 minutes default
            "description": description,
            "target_zone": "Z1"
        }
    
    def _normalize_workout_type_for_watch(self, workout_type: str) -> str:
        """
        Normalize workout type for Apple Watch.
        
        Returns: "running", "cycling", "swimming", "walking", "hiking"
        """
        type_lower = workout_type.lower()
        
        # Map to Watch-compatible types
        type_mapping = {
            "run": "running",
            "running": "running",
            "bike": "cycling",
            "cycling": "cycling",
            "bici": "cycling",
            "swim": "swimming",
            "swimming": "swimming",
            "walk": "walking",
            "walking": "walking",
            "hike": "hiking",
            "hiking": "hiking"
        }
        
        return type_mapping.get(type_lower, "running")  # Default to running
    
    def _normalize_sport_type_for_watch(self, sport: str) -> str:
        """Normalize sport type for Watch (same as workout type)"""
        return self._normalize_workout_type_for_watch(sport)
    
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
                    try:
                        parsed[zone] = {
                            "min": int(float(parts[0].strip())),
                            "max": int(float(parts[1].strip()))
                        }
                    except ValueError:
                        pass
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

