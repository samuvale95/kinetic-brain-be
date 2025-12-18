"""
Service for matching activities (Strava, HealthKit) with planned workouts.
Reusable service that can be used by both StravaService and HealthKitService.
"""
from typing import Optional, List, Tuple
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_
from app.models.workout import Workout, WorkoutPlan, WorkoutStatus
from app.services.workout_parameters import normalize_sport_type
from loguru import logger


class WorkoutMatchingService:
    """Service for matching activities with planned workouts"""
    
    MATCH_THRESHOLD = 50  # Minimum score for a valid match
    
    @staticmethod
    def match_workout(
        activity_type: str,
        activity_date: datetime,
        activity_duration_seconds: Optional[int],
        activity_distance_meters: Optional[float],
        planned_workouts: List[Workout],
        db: Optional[Session] = None
    ) -> Optional[Tuple[Workout, float]]:
        """
        Find the best matching workout for an activity.
        
        Args:
            activity_type: Type of activity (e.g., "running", "cycling")
            activity_date: Date/time of the activity
            activity_duration_seconds: Duration in seconds (optional)
            activity_distance_meters: Distance in meters (optional)
            planned_workouts: List of planned workouts to match against
            db: Optional database session (for filtering active plans)
        
        Returns:
            Tuple of (matched_workout, score) or None if no match found
        """
        activity_date_only = activity_date.date() if isinstance(activity_date, datetime) else activity_date
        activity_type_lower = activity_type.lower()
        
        # Score potential matches
        best_match = None
        best_score = 0
        
        for workout in planned_workouts:
            if not workout.scheduled_date:
                continue
            
            # CRITICAL: Check sport type compatibility FIRST
            # Skip workout if types don't match (even if date matches)
            if not WorkoutMatchingService._are_sport_types_compatible(activity_type_lower, workout.type):
                continue
            
            score = 0
            
            # Date match (most important - 40% weight)
            date_diff_days = abs((workout.scheduled_date - activity_date_only).days)
            if date_diff_days == 0:
                score += 100  # Same day
            elif date_diff_days == 1:
                score += 50  # 1 day difference
            elif date_diff_days <= 3:
                score += 25  # 3 days difference
            else:
                continue  # Skip if too far apart
            
            # Type match (30% weight)
            workout_type_lower = workout.type.lower()
            if activity_type_lower == workout_type_lower:
                score += 30
            elif activity_type_lower in workout_type_lower or workout_type_lower in activity_type_lower:
                score += 20
            
            # Duration match (20% weight)
            if activity_duration_seconds and workout.duration_minutes:
                activity_duration_min = activity_duration_seconds / 60
                duration_diff = abs(activity_duration_min - workout.duration_minutes)
                duration_diff_percent = duration_diff / workout.duration_minutes if workout.duration_minutes > 0 else 1.0
                
                if duration_diff_percent < 0.05:  # < 5% difference
                    score += 20
                elif duration_diff_percent < 0.10:  # < 10% difference
                    score += 15
                elif duration_diff_percent < 0.20:  # < 20% difference
                    score += 10
            
            # Distance match (10% weight)
            if activity_distance_meters and workout.structure_json:
                # Try to extract target distance from structure_json
                # This is optional and may not always be available
                target_distance = WorkoutMatchingService._extract_target_distance(workout.structure_json)
                if target_distance:
                    distance_diff_percent = abs(activity_distance_meters - target_distance) / target_distance
                    if distance_diff_percent < 0.10:  # < 10% difference
                        score += 10
                    elif distance_diff_percent < 0.15:  # < 15% difference
                        score += 7
            
            if score > best_score:
                best_score = score
                best_match = workout
        
        # Only return match if score meets threshold
        if best_match and best_score >= WorkoutMatchingService.MATCH_THRESHOLD:
            return (best_match, best_score)
        
        return None
    
    @staticmethod
    def _are_sport_types_compatible(activity_type: str, workout_type: str) -> bool:
        """
        Check if activity and workout types are compatible using normalized sport types.
        
        Returns True only if the normalized sport types match exactly.
        This ensures that activities are only matched with workouts of the same sport type.
        """
        # Normalize both types
        normalized_activity_type = normalize_sport_type(activity_type)
        normalized_workout_type = normalize_sport_type(workout_type)
        
        # Types must match exactly after normalization
        return normalized_activity_type == normalized_workout_type
    
    @staticmethod
    def _extract_target_distance(structure_json: dict) -> Optional[float]:
        """Extract target distance from workout structure_json if available"""
        if not structure_json or not isinstance(structure_json, dict):
            return None
        
        try:
            segments = structure_json.get("segments", [])
            total_distance = 0.0
            
            for segment in segments:
                if isinstance(segment, dict):
                    steps = segment.get("steps", [])
                    for step in steps:
                        if isinstance(step, dict):
                            # Check for distance in step
                            distance = step.get("distance")
                            if distance:
                                if isinstance(distance, dict):
                                    total_distance += distance.get("value", 0)
                                elif isinstance(distance, (int, float)):
                                    total_distance += distance
            
            return total_distance if total_distance > 0 else None
        except Exception as e:
            logger.debug(f"Error extracting target distance: {e}")
            return None
    
    @staticmethod
    def get_planned_workouts_for_matching(
        db: Session,
        user_id: int,
        date_window_start: Optional[datetime] = None,
        date_window_end: Optional[datetime] = None,
        workout_type: Optional[str] = None
    ) -> List[Workout]:
        """
        Get planned workouts for matching, filtering by date window and type.
        
        Only includes workouts from active plans or standalone workouts.
        """
        from app.models.workout import WorkoutPlan
        
        # Default date window: ±3 days from today if not specified
        if date_window_start is None:
            date_window_start = datetime.now() - timedelta(days=3)
        if date_window_end is None:
            date_window_end = datetime.now() + timedelta(days=3)
        
        date_window_start_date = date_window_start.date() if isinstance(date_window_start, datetime) else date_window_start
        date_window_end_date = date_window_end.date() if isinstance(date_window_end, datetime) else date_window_end
        
        # Get workouts from active plans or standalone workouts
        query = (
            select(Workout)
            .outerjoin(WorkoutPlan, Workout.plan_id == WorkoutPlan.id)
            .where(
                and_(
                    Workout.user_id == user_id,
                    Workout.status == WorkoutStatus.SCHEDULED,
                    Workout.scheduled_date.isnot(None),
                    Workout.scheduled_date >= date_window_start_date,
                    Workout.scheduled_date <= date_window_end_date,
                    # Only include workouts from active plans or standalone workouts
                    or_(
                        Workout.plan_id.is_(None),  # Standalone workouts
                        WorkoutPlan.status == "active"  # Workouts from active plans only
                    )
                )
            )
        )
        
        # Filter by type if specified
        if workout_type:
            normalized_type = normalize_sport_type(workout_type)
            # This is a simplified filter - in practice, we'd need to check normalized types
            # For now, we'll filter in Python after fetching
            workouts = db.execute(query).scalars().all()
            # Filter by normalized type
            filtered_workouts = [
                w for w in workouts
                if normalize_sport_type(w.type) == normalized_type
            ]
            return filtered_workouts
        
        return db.execute(query).scalars().all()

