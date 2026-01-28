"""
Endurance Training Validation Layer.
Implements safety rules to prevent injury and overtraining.
AI-generated plans MUST pass these checks before being approved.
"""
from typing import List, Optional, Dict, Tuple
from datetime import date, timedelta
from pydantic import BaseModel
from loguru import logger

from app.schemas.agentic_coach import AgenticWeeklyPlan, GeneratedWorkout


class ValidationError(BaseModel):
    """A validation rule violation."""
    severity: str  # "error" | "warning"
    rule: str
    message: str
    affected_workouts: List[str] = []


class ValidationResult(BaseModel):
    """Result of plan validation."""
    is_valid: bool
    errors: List[ValidationError] = []
    warnings: List[ValidationError] = []
    
    def add_error(self, rule: str, message: str, workouts: List[str] = None):
        self.errors.append(ValidationError(
            severity="error",
            rule=rule,
            message=message,
            affected_workouts=workouts or []
        ))
        self.is_valid = False
    
    def add_warning(self, rule: str, message: str, workouts: List[str] = None):
        self.warnings.append(ValidationError(
            severity="warning",
            rule=rule,
            message=message,
            affected_workouts=workouts or []
        ))


class EnduranceValidationRules:
    """
    Safety rules for endurance training plans.
    These rules are based on sports science principles.
    """
    
    # Rule thresholds
    MAX_WEEKLY_VOLUME_INCREASE = 0.10  # 10% max volume increase
    MAX_WEEKLY_TSS_INCREASE = 50  # Max +50 TSS per week
    MIN_HIGH_INTENSITY_SPACING_HOURS = 48  # 48h between Z4+ sessions
    MAX_CONSECUTIVE_HARD_DAYS = 2  # Max 2 consecutive hard days
    MIN_RECOVERY_RATIO = 0.60  # At least 60% of time in Z1-Z2
    MAX_RECOVERY_RATIO = 0.85  # No more than 85% recovery (need stimulus)
    MAX_WEEKLY_TSS = 800  # Hard cap on weekly TSS for safety
    MIN_WEEKLY_TSS = 100  # Minimum to maintain fitness
    
    def __init__(self):
        self.logger = logger
    
    def validate_plan(
        self,
        plan: AgenticWeeklyPlan,
        previous_week_volume_km: Optional[float] = None,
        previous_week_tss: Optional[float] = None,
        athlete_max_weekly_tss: Optional[float] = None
    ) -> ValidationResult:
        """
        Main validation entry point.
        
        Args:
            plan: The AI-generated plan
            previous_week_volume_km: Volume in km from last week
            previous_week_tss: TSS from last week
            athlete_max_weekly_tss: Historical max TSS for this athlete
        """
        result = ValidationResult(is_valid=True)
        
        # Run all validation rules
        self._check_progressive_overload(plan, previous_week_volume_km, previous_week_tss, result)
        self._check_high_intensity_spacing(plan, result)
        self._check_consecutive_hard_days(plan, result)
        self._check_recovery_balance(plan, result)
        self._check_weekly_tss_bounds(plan, athlete_max_weekly_tss, result)
        self._check_workout_duration_sanity(plan, result)
        
        # Log results
        if not result.is_valid:
            self.logger.warning(f"Plan validation FAILED with {len(result.errors)} errors")
        elif result.warnings:
            self.logger.info(f"Plan validation PASSED with {len(result.warnings)} warnings")
        else:
            self.logger.info("Plan validation PASSED with no issues")
        
        return result
    
    def _check_progressive_overload(
        self,
        plan: AgenticWeeklyPlan,
        previous_volume: Optional[float],
        previous_tss: Optional[float],
        result: ValidationResult
    ):
        """Rule: Weekly volume and TSS should not increase by more than 10%."""
        
        # Calculate current week's totals
        current_volume = sum(w.duration_minutes * 0.15 for w in plan.workouts)  # Rough km estimate
        current_tss = sum(getattr(w, 'tss', 50.0) for w in plan.workouts if w.type != 'rest')
        
        # Check volume progression
        if previous_volume and previous_volume > 0:
            volume_increase_pct = (current_volume - previous_volume) / previous_volume
            
            if volume_increase_pct > self.MAX_WEEKLY_VOLUME_INCREASE:
                result.add_error(
                    rule="progressive_overload_volume",
                    message=f"Volume increase {volume_increase_pct:.0%} exceeds safe limit of {self.MAX_WEEKLY_VOLUME_INCREASE:.0%} ({previous_volume:.1f}km → {current_volume:.1f}km)",
                    workouts=[w.day for w in plan.workouts if w.type != 'rest']
                )
            elif volume_increase_pct > self.MAX_WEEKLY_VOLUME_INCREASE * 0.8:
                result.add_warning(
                    rule="progressive_overload_volume",
                    message=f"Volume increase {volume_increase_pct:.0%} is approaching limit (safe: <{self.MAX_WEEKLY_VOLUME_INCREASE:.0%})"
                )
        
        # Check TSS progression
        if previous_tss and previous_tss > 0:
            tss_increase = current_tss - previous_tss
            
            if tss_increase > self.MAX_WEEKLY_TSS_INCREASE:
                result.add_error(
                    rule="progressive_overload_tss",
                    message=f"TSS increase {tss_increase:.0f} exceeds safe limit of {self.MAX_WEEKLY_TSS_INCREASE} ({previous_tss:.0f} → {current_tss:.0f})",
                    workouts=[w.day for w in plan.workouts if w.type != 'rest']
                )
    
    def _check_high_intensity_spacing(self, plan: AgenticWeeklyPlan, result: ValidationResult):
        """Rule: High-intensity sessions (Z4+) must have at least 48h spacing."""
        
        high_intensity_types = ['intervals', 'tempo', 'vo2max', 'threshold', 'race']
        high_intensity_workouts = [
            w for w in plan.workouts 
            if any(hi_type in w.type.lower() for hi_type in high_intensity_types)
        ]
        
        # Sort by date
        high_intensity_workouts.sort(key=lambda w: w.date)
        
        # Check spacing
        for i in range(len(high_intensity_workouts) - 1):
            current = high_intensity_workouts[i]
            next_workout = high_intensity_workouts[i + 1]
            
            days_between = (next_workout.date - current.date).days
            hours_between = days_between * 24
            
            if hours_between < self.MIN_HIGH_INTENSITY_SPACING_HOURS:
                result.add_error(
                    rule="high_intensity_spacing",
                    message=f"Only {hours_between}h between high-intensity sessions ({current.day} → {next_workout.day}). Minimum: {self.MIN_HIGH_INTENSITY_SPACING_HOURS}h",
                    workouts=[current.day, next_workout.day]
                )
    
    def _check_consecutive_hard_days(self, plan: AgenticWeeklyPlan, result: ValidationResult):
        """Rule: No more than 2 consecutive hard training days."""
        
        hard_types = ['intervals', 'tempo', 'long', 'vo2max', 'threshold', 'race']
        
        # Sort workouts by date
        sorted_workouts = sorted(plan.workouts, key=lambda w: w.date)
        
        consecutive_count = 0
        consecutive_days = []
        
        for workout in sorted_workouts:
            is_hard = any(ht in workout.type.lower() for ht in hard_types) or workout.rpe_target >= 7
            
            if is_hard:
                consecutive_count += 1
                consecutive_days.append(workout.day)
                
                if consecutive_count > self.MAX_CONSECUTIVE_HARD_DAYS:
                    result.add_error(
                        rule="consecutive_hard_days",
                        message=f"{consecutive_count} consecutive hard days detected: {', '.join(consecutive_days)}. Max allowed: {self.MAX_CONSECUTIVE_HARD_DAYS}",
                        workouts=consecutive_days
                    )
                    break
            else:
                # Reset counter on easy/rest day
                consecutive_count = 0
                consecutive_days = []
    
    def _check_recovery_balance(self, plan: AgenticWeeklyPlan, result: ValidationResult):
        """Rule: 60-85% of training time should be in recovery zones (Z1-Z2)."""
        
        total_duration = sum(w.duration_minutes for w in plan.workouts if w.type != 'rest')
        
        # Estimate recovery time (workouts with RPE < 5 or type 'recovery'/'easy')
        recovery_duration = sum(
            w.duration_minutes for w in plan.workouts 
            if w.rpe_target < 5 or any(rt in w.type.lower() for rt in ['recovery', 'easy', 'base'])
        )
        
        if total_duration > 0:
            recovery_ratio = recovery_duration / total_duration
            
            if recovery_ratio < self.MIN_RECOVERY_RATIO:
                result.add_error(
                    rule="recovery_balance",
                    message=f"Recovery time {recovery_ratio:.0%} is too low. Should be {self.MIN_RECOVERY_RATIO:.0%}-{self.MAX_RECOVERY_RATIO:.0%} for sustainable training.",
                    workouts=[w.day for w in plan.workouts if w.rpe_target >= 7]
                )
            elif recovery_ratio > self.MAX_RECOVERY_RATIO:
                result.add_warning(
                    rule="recovery_balance",
                    message=f"Recovery time {recovery_ratio:.0%} is very high. May lack sufficient training stimulus."
                )
    
    def _check_weekly_tss_bounds(
        self,
        plan: AgenticWeeklyPlan,
        athlete_max_tss: Optional[float],
        result: ValidationResult
    ):
        """Rule: Weekly TSS should be within reasonable bounds."""
        
        weekly_tss = sum(getattr(w, 'tss', 50.0) for w in plan.workouts if w.type != 'rest')
        
        # Hard cap
        if weekly_tss > self.MAX_WEEKLY_TSS:
            result.add_error(
                rule="weekly_tss_max",
                message=f"Weekly TSS {weekly_tss:.0f} exceeds safety limit of {self.MAX_WEEKLY_TSS}",
                workouts=[w.day for w in plan.workouts if w.type != 'rest']
            )
        
        # Minimum stimulus
        if weekly_tss < self.MIN_WEEKLY_TSS:
            result.add_warning(
                rule="weekly_tss_min",
                message=f"Weekly TSS {weekly_tss:.0f} is below effective training threshold ({self.MIN_WEEKLY_TSS})"
            )
        
        # Check against athlete's historical max
        if athlete_max_tss and weekly_tss > athlete_max_tss * 1.2:
            result.add_error(
                rule="weekly_tss_athlete_max",
                message=f"Weekly TSS {weekly_tss:.0f} is 20% above athlete's historical max ({athlete_max_tss:.0f}). High injury risk.",
                workouts=[w.day for w in plan.workouts if w.type != 'rest']
            )
    
    def _check_workout_duration_sanity(self, plan: AgenticWeeklyPlan, result: ValidationResult):
        """Rule: Individual workout durations should be reasonable."""
        
        MAX_SINGLE_WORKOUT_DURATION = 300  # 5 hours (for ultra endurance)
        MIN_EFFECTIVE_DURATION = 15  # 15 minutes minimum
        
        for workout in plan.workouts:
            if workout.type == 'rest':
                continue
            
            if workout.duration_minutes > MAX_SINGLE_WORKOUT_DURATION:
                result.add_error(
                    rule="workout_duration_max",
                    message=f"{workout.day}: {workout.duration_minutes}min exceeds max duration ({MAX_SINGLE_WORKOUT_DURATION}min)",
                    workouts=[workout.day]
                )
            
            if workout.duration_minutes < MIN_EFFECTIVE_DURATION and workout.type not in ['recovery', 'rest']:
                result.add_warning(
                    rule="workout_duration_min",
                    message=f"{workout.day}: {workout.duration_minutes}min is too short for effective training",
                    workouts=[workout.day]
                )


def validate_endurance_plan(
    plan: AgenticWeeklyPlan,
    previous_week_stats: Optional[Dict] = None,
    athlete_profile: Optional[Dict] = None
) -> ValidationResult:
    """
    Convenience function for plan validation.
    
    Args:
        plan: AI-generated weekly plan
        previous_week_stats: Dict with 'volume_km', 'tss'
        athlete_profile: Dict with 'max_weekly_tss'
    
    Returns:
        ValidationResult with errors and warnings
    """
    validator = EnduranceValidationRules()
    
    prev_volume = previous_week_stats.get('volume_km') if previous_week_stats else None
    prev_tss = previous_week_stats.get('tss') if previous_week_stats else None
    max_tss = athlete_profile.get('max_weekly_tss') if athlete_profile else None
    
    return validator.validate_plan(plan, prev_volume, prev_tss, max_tss)
