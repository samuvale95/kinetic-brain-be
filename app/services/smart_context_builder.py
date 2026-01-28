"""
Smart Context Builder for Endurance Training.
Implements the 3-layer information pyramid to efficiently build LLM prompts.
"""
from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, desc, func
from loguru import logger

from app.models.workout import Workout, WorkoutSession
from app.models.training_metrics import TrainingMetrics, WeeklyTrainingSummary
from app.schemas.endurance_context import (
    SmartEnduranceContext,
    CriticalContext,
    RelevantContext,
    BackgroundContext,
    CurrentFitnessState,
    LastWorkoutSnapshot,
    SimilarWorkoutSummary,
    AerobicBaseReference,
    MonthlyTrainingSummary,
    AthleteProfileSummary,
)


class SmartContextBuilder:
    """
    Builds efficient context for LLM by selecting only relevant information.
    Uses 3-layer pyramid: Critical (always) + Relevant (retrieved) + Background (cached).
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def build_context(
        self,
        user_id: int,
        target_week_start: date,
        next_workout_type: Optional[str] = None,
        next_sport: Optional[str] = None
    ) -> SmartEnduranceContext:
        """
        Main entry point: builds complete 3-layer context.
        
        Args:
            user_id: User ID
            target_week_start: Start date of the week being planned
            next_workout_type: Type of next workout (for smart retrieval)
            next_sport: Sport of next workout (run/bike/swim)
        """
        logger.info(f"Building smart context for user {user_id}, week {target_week_start}")
        
        # Layer 1: CRITICAL (always needed)
        critical = self._build_critical_context(user_id)
        
        # Layer 2: RELEVANT (smart retrieval based on next workout)
        relevant = self._build_relevant_context(
            user_id, 
            next_workout_type or "intervals",  # Default
            next_sport or "run"
        )
        
        # Layer 3: BACKGROUND (cached summaries)
        background = self._build_background_context(user_id)
        
        return SmartEnduranceContext(
            user_id=user_id,
            target_week_start=target_week_start,
            critical=critical,
            relevant=relevant,
            background=background
        )
    
    # ========================================================================
    # LAYER 1: CRITICAL Context
    # ========================================================================
    
    def _build_critical_context(self, user_id: int) -> CriticalContext:
        """Build Layer 1: must-have info."""
        
        # Get fitness metrics (CTL/ATL/TSB)
        fitness = self._calculate_current_fitness(user_id)
        
        # Get most recent workout
        last_workout = self._get_last_workout(user_id)
        
        # Count recent skips
        skip_count = self._count_recent_skips(user_id, days=14)
        
        return CriticalContext(
            current_fitness=fitness,
            last_workout=last_workout,
            current_phase="Build",  # TODO: determine from plan
            weeks_to_race=None,  # TODO: calculate from user's next race
            injury_flags=[],  # TODO: extract from coach_memories
            skip_count_last_2weeks=skip_count
        )
    
    def _calculate_current_fitness(self, user_id: int) -> CurrentFitnessState:
        """Calculate CTL/ATL/TSB from recent training."""
        
        # Get last 42 days of TSS data
        end_date = datetime.utcnow()
        start_ctl = end_date - timedelta(days=42)
        start_atl = end_date - timedelta(days=7)
        
        # Query TSS from workout sessions with training metrics
        sessions = self.db.execute(
            select(WorkoutSession)
            .join(TrainingMetrics, WorkoutSession.id == TrainingMetrics.workout_session_id)
            .where(
                and_(
                    WorkoutSession.user_id == user_id,
                    WorkoutSession.actual_date >= start_ctl
                )
            )
        ).scalars().all()
        
        # Calculate CTL (42-day exponential weighted average)
        ctl_sum = sum(s.training_metrics.tss for s in sessions if s.training_metrics and s.training_metrics.tss)
        ctl = ctl_sum / 42.0 if sessions else 0.0
        
        # Calculate ATL (7-day exponential weighted average)
        recent_sessions = [s for s in sessions if s.actual_date >= start_atl]
        atl_sum = sum(s.training_metrics.tss for s in recent_sessions if s.training_metrics and s.training_metrics.tss)
        atl = atl_sum / 7.0 if recent_sessions else 0.0
        
        # TSB = CTL - ATL
        tsb = ctl - atl
        
        # Ramp Rate = ATL / CTL (injury risk if >1.5)
        ramp_rate = atl / ctl if ctl > 0 else 0.0
        
        return CurrentFitnessState(
            ctl=round(ctl, 1),
            atl=round(atl, 1),
            tsb=round(tsb, 1),
            ramp_rate=round(ramp_rate, 2),
            hr_drift=None  # TODO: calculate from last long run
        )
    
    def _get_last_workout(self, user_id: int) -> LastWorkoutSnapshot:
        """Get the most recent completed workout."""
        
        session = self.db.execute(
            select(WorkoutSession)
            .join(Workout, WorkoutSession.workout_id == Workout.id)
            .where(WorkoutSession.user_id == user_id)
            .order_by(desc(WorkoutSession.actual_date))
            .limit(1)
        ).scalar_one_or_none()
        
        if not session:
            # Return a dummy workout if no history
            return LastWorkoutSnapshot(
                date=date.today() - timedelta(days=7),
                sport="run",
                type="recovery",
                completion_rate=1.0,
                rpe=3,
                tss=30.0,
                athlete_note="No recent workouts"
            )
        
        # Calculate completion rate (actual vs planned duration)
        planned_duration = session.workout.duration_minutes if session.workout else session.duration_minutes
        actual_duration = session.duration_minutes
        completion_rate = min(actual_duration / planned_duration, 1.0) if planned_duration > 0 else 1.0
        
        # Get TSS from training metrics
        tss = session.training_metrics.tss if session.training_metrics else 0.0
        
        return LastWorkoutSnapshot(
            date=session.actual_date.date(),
            sport=session.workout.type if session.workout else "run",
            type=session.workout.type if session.workout else "unknown",
            completion_rate=round(completion_rate, 2),
            failure_point=None,  # TODO: extract from notes
            athlete_note=session.notes,
            rpe=session.perceived_exertion or 5,
            tss=tss
        )
    
    def _count_recent_skips(self, user_id: int, days: int = 14) -> int:
        """Count skipped workouts in recent period."""
        # TODO: Query WorkoutSkip table
        return 0
    
    # ========================================================================
    # LAYER 2: RELEVANT Context (Smart Retrieval)
    # ========================================================================
    
    def _build_relevant_context(
        self,
        user_id: int,
        next_workout_type: str,
        next_sport: str
    ) -> RelevantContext:
        """
        Build Layer 2: retrieve only workouts RELEVANT to next planned session.
        """
        
        # Get last 3 similar workouts (same type + sport)
        similar = self._get_similar_workouts(user_id, next_workout_type, next_sport, limit=3)
        
        # Get aerobic base reference (last long run)
        aerobic_base = self._get_aerobic_base_reference(user_id, next_sport)
        
        # Analyze failure patterns
        failure_pattern = self._analyze_failure_pattern(similar)
        
        # Progression context
        progression = self._build_progression_context(similar)
        
        return RelevantContext(
            similar_workouts=similar,
            aerobic_base=aerobic_base,
            failure_pattern=failure_pattern,
            progression_context=progression
        )
    
    def _get_similar_workouts(
        self,
        user_id: int,
        workout_type: str,
        sport: str,
        limit: int = 3
    ) -> List[SimilarWorkoutSummary]:
        """Retrieve last N workouts of the same type."""
        
        sessions = self.db.execute(
            select(WorkoutSession)
            .join(Workout, WorkoutSession.workout_id == Workout.id)
            .where(
                and_(
                    WorkoutSession.user_id == user_id,
                    Workout.type.ilike(f"%{workout_type}%")  # Fuzzy match
                    # TODO: filter by sport
                )
            )
            .order_by(desc(WorkoutSession.actual_date))
            .limit(limit)
        ).scalars().all()
        
        return [self._session_to_summary(s) for s in sessions]
    
    def _session_to_summary(self, session: WorkoutSession) -> SimilarWorkoutSummary:
        """Convert WorkoutSession to SimilarWorkoutSummary."""
        
        planned_duration = session.workout.duration_minutes if session.workout else session.duration_minutes
        completion_rate = min(session.duration_minutes / planned_duration, 1.0) if planned_duration > 0 else 1.0
        
        # Get time in target zone from training metrics
        time_in_target = 0
        if session.training_metrics and session.training_metrics.zone_distribution:
            # Assume target zone is the highest intensity zone with significant time
            zones = session.training_metrics.zone_distribution
            time_in_target = max(zones.values()) if isinstance(zones, dict) else 0
        
        return SimilarWorkoutSummary(
            date=session.actual_date.date(),
            sport=session.workout.type if session.workout else "run",
            workout_description=session.workout.title if session.workout else "Unknown",
            completion_rate=round(completion_rate, 2),
            avg_hr=int(session.avg_hr) if session.avg_hr else None,
            avg_pace=f"{session.avg_pace:.2f}/km" if session.avg_pace else None,
            avg_power=int(session.avg_power) if session.avg_power else None,
            time_in_zone_target=int(time_in_target),
            rpe=session.perceived_exertion or 5,
            athlete_feedback=session.notes
        )
    
    def _get_aerobic_base_reference(self, user_id: int, sport: str) -> AerobicBaseReference:
        """Get last long/easy session for aerobic context."""
        
        # Find last "long" or "endurance" workout
        session = self.db.execute(
            select(WorkoutSession)
            .join(Workout, WorkoutSession.workout_id == Workout.id)
            .where(
                and_(
                    WorkoutSession.user_id == user_id,
                    Workout.type.in_(["long", "endurance", "Long Run", "Endurance"])
                )
            )
            .order_by(desc(WorkoutSession.actual_date))
            .limit(1)
        ).scalar_one_or_none()
        
        if session:
            last_long = self._session_to_summary(session)
        else:
            # Dummy fallback
            last_long = SimilarWorkoutSummary(
                date=date.today() - timedelta(days=14),
                sport=sport,
                workout_description="No long run history",
                completion_rate=1.0,
                time_in_zone_target=0,
                rpe=5
            )
        
        # TODO: Calculate avg weekly Z2 time
        avg_weekly_zone2 = 180  # Placeholder: 3 hours
        
        return AerobicBaseReference(
            last_long_session=last_long,
            avg_weekly_zone2_minutes=avg_weekly_zone2,
            decoupling=None  # TODO: calculate HR/pace decoupling
        )
    
    def _analyze_failure_pattern(self, similar_workouts: List[SimilarWorkoutSummary]) -> Optional[str]:
        """Detect if there's a pattern in incomplete workouts."""
        
        incomplete = [w for w in similar_workouts if w.completion_rate < 0.9]
        
        if len(incomplete) >= 2:
            return f"Last {len(incomplete)} sessions incomplete (avg completion: {sum(w.completion_rate for w in incomplete) / len(incomplete):.0%})"
        
        return None
    
    def _build_progression_context(self, similar_workouts: List[SimilarWorkoutSummary]) -> str:
        """Describe progression trend across similar workouts."""
        
        if len(similar_workouts) < 2:
            return "Insufficient history for progression analysis"
        
        # Simple trend based on completion rates
        rates = [w.completion_rate for w in similar_workouts]
        avg_early = sum(rates[-2:]) / 2
        avg_recent = rates[0]
        
        if avg_recent > avg_early + 0.1:
            return "Improving trend: recent sessions more complete than earlier"
        elif avg_recent < avg_early - 0.1:
            return "Declining trend: recent sessions less complete"
        else:
            return "Stable performance on similar workouts"
    
    # ========================================================================
    # LAYER 3: BACKGROUND Context (Cached Summaries)
    # ========================================================================
    
    def _build_background_context(self, user_id: int) -> BackgroundContext:
        """Build Layer 3: pre-computed summaries."""
        
        monthly = self._get_monthly_summary(user_id)
        profile = self._get_athlete_profile(user_id)
        
        return BackgroundContext(
            monthly_summary=monthly,
            athlete_profile=profile
        )
    
    def _get_monthly_summary(self, user_id: int) -> MonthlyTrainingSummary:
        """Get or compute 30-day training summary."""
        
        # TODO: Cache this in WeeklyTrainingSummary or a dedicated table
        # For now, compute on-the-fly
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)
        
        sessions = self.db.execute(
            select(WorkoutSession)
            .where(
                and_(
                    WorkoutSession.user_id == user_id,
                    WorkoutSession.actual_date >= start_date
                )
            )
        ).scalars().all()
        
        total_tss = sum(s.training_metrics.tss for s in sessions if s.training_metrics and s.training_metrics.tss)
        total_km = sum(s.workout.duration_minutes * 0.15 for s in sessions if s.workout)  # Rough estimate
        
        return MonthlyTrainingSummary(
            total_volume_km=round(total_km, 1),
            total_tss=round(total_tss, 1),
            avg_sessions_per_week=len(sessions) / 4.3,  # ~4.3 weeks in 30 days
            high_intensity_ratio=0.2,  # TODO: calculate from zone distribution
            progress_trend="improving",  # TODO: trend analysis
            compliance_rate=0.85  # TODO: planned vs completed
        )
    
    def _get_athlete_profile(self, user_id: int) -> AthleteProfileSummary:
        """Get long-term athlete characteristics."""
        
        # TODO: Extract from coach_memories or compute from history
        
        return AthleteProfileSummary(
            strengths=["consistency", "aerobic_base"],
            weaknesses=["recovery", "high_intensity"],
            injury_history=[],
            preferred_training_times=None,
            equipment_limitations=[]
        )
