from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

from loguru import logger


class PlanValidationError(Exception):
    """Raised when a generated workout plan violates safety rules."""

    def __init__(self, violations: Iterable[str]):
        messages = list(violations)
        super().__init__("; ".join(messages))
        self.violations = messages


@dataclass(frozen=True)
class ValidationThresholds:
    """Thresholds derived from training load guidelines."""

    weekly_progression: float
    high_intensity_ratio: float
    max_high_intensity_sessions: int


DEFAULT_THRESHOLDS = {
    "beginner": ValidationThresholds(
        weekly_progression=0.15,
        high_intensity_ratio=0.25,
        max_high_intensity_sessions=2,
    ),
    "intermediate": ValidationThresholds(
        weekly_progression=0.10,
        high_intensity_ratio=0.30,
        max_high_intensity_sessions=3,
    ),
    "advanced": ValidationThresholds(
        weekly_progression=0.07,
        high_intensity_ratio=0.35,
        max_high_intensity_sessions=3,
    ),
}


class WorkoutPlanValidator:
    """Validate training plans against deterministic safety rules."""

    REST_DAY_REQUIRED = 1
    STRUCTURE_SEGMENTS_REQUIRED = {"warmup", "cooldown"}
    WEEKDAY_NAMES = {
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    }

    def __init__(
        self,
        thresholds: Optional[Dict[str, ValidationThresholds]] = None,
    ) -> None:
        self.thresholds = thresholds or DEFAULT_THRESHOLDS

    def validate(self, plan: Dict[str, Any], user_state: Optional[Dict[str, Any]] = None) -> None:
        violations: List[str] = []

        weeks = plan.get("weeks") or []
        if not weeks:
            raise PlanValidationError(["Plan contains no weeks"])

        requested_duration = plan.get("duration_weeks")
        if requested_duration and len(weeks) != requested_duration:
            violations.append(
                f"Plan duration mismatch: expected {requested_duration} weeks, got {len(weeks)}"
            )

        level = (plan.get("level") or "").lower()
        thresholds = self.thresholds.get(level, DEFAULT_THRESHOLDS["intermediate"])

        weekly_stats: List[Dict[str, Any]] = []

        for expected_week_number, week in enumerate(weeks, start=1):
            week_number = week.get("week")
            if week_number != expected_week_number:
                violations.append(
                    f"Week numbering must be sequential starting at 1 (found week={week_number}, expected {expected_week_number})"
                )

            workouts = week.get("workouts") or []
            if not isinstance(workouts, list):
                violations.append(f"Week {expected_week_number} workouts data malformed")
                continue

            stats = self._evaluate_week(
                week_index=expected_week_number,
                workouts=workouts,
                thresholds=thresholds,
            )
            weekly_stats.append(stats)
            violations.extend(stats["violations"])

        violations.extend(
            self._evaluate_progression(
                weekly_stats=weekly_stats,
                thresholds=thresholds,
            )
        )

        if user_state:
            readiness_state = user_state.get("readiness_state")
            recovery_index = user_state.get("recovery_index")
            injury_risk_score = user_state.get("injury_risk_score")
            hydration_score = user_state.get("hydration_score")

            if readiness_state == "rest":
                violations.append("Athlete readiness state requires rest before new plan")
            elif readiness_state == "caution" and recovery_index is not None and recovery_index < 0.6:
                violations.append("Athlete readiness indicates caution; recovery index too low for new load")

            if injury_risk_score is not None and injury_risk_score > 1.5:
                violations.append(f"Athlete injury risk score {injury_risk_score:.2f} exceeds safe threshold 1.50")

            if hydration_score is not None and hydration_score < 0.4:
                violations.append("Hydration score critically low; postpone plan generation")

        if violations:
            logger.warning(
                "[PLAN_VALIDATION] Plan rejected with violations: {}", violations
            )
            raise PlanValidationError(violations)

        logger.info(
            "[PLAN_VALIDATION] Plan validated successfully - weeks={}, level={}, thresholds={}",
            len(weekly_stats),
            level or "unspecified",
            thresholds,
        )

    def _evaluate_week(
        self,
        *,
        week_index: int,
        workouts: List[Dict[str, Any]],
        thresholds: ValidationThresholds,
    ) -> Dict[str, Any]:
        total_duration = 0.0
        high_intensity_duration = 0.0
        high_intensity_sessions = 0
        rest_days = self._count_rest_days(workouts)
        violations: List[str] = []

        for workout in workouts:
            duration_minutes = self._resolve_duration_minutes(workout)
            total_duration += duration_minutes

            if self._is_high_intensity(workout):
                high_intensity_duration += duration_minutes
                high_intensity_sessions += 1

            structure_violation = self._validate_structure(workout)
            if structure_violation:
                violations.append(
                    f"Week {week_index}: {structure_violation} (workout: {workout.get('day') or workout.get('type')})"
                )

        if rest_days < self.REST_DAY_REQUIRED:
            violations.append(
                f"Week {week_index}: requires at least {self.REST_DAY_REQUIRED} rest day(s)"
            )

        if total_duration > 0:
            high_intensity_ratio = high_intensity_duration / total_duration
            if high_intensity_ratio > thresholds.high_intensity_ratio:
                violations.append(
                    f"Week {week_index}: high-intensity volume ratio {high_intensity_ratio:.2f} exceeds limit {thresholds.high_intensity_ratio:.2f}"
                )

        if high_intensity_sessions > thresholds.max_high_intensity_sessions:
            violations.append(
                f"Week {week_index}: {high_intensity_sessions} high-intensity sessions exceed limit {thresholds.max_high_intensity_sessions}"
            )

        return {
            "week": week_index,
            "total_duration": total_duration,
            "high_intensity_duration": high_intensity_duration,
            "high_intensity_sessions": high_intensity_sessions,
            "rest_days": rest_days,
            "violations": violations,
        }

    def _evaluate_progression(
        self,
        *,
        weekly_stats: List[Dict[str, Any]],
        thresholds: ValidationThresholds,
    ) -> List[str]:
        violations: List[str] = []
        previous_duration: Optional[float] = None

        for stats in weekly_stats:
            total_duration = stats["total_duration"]
            if previous_duration is None:
                previous_duration = total_duration
                continue

            if previous_duration <= 0:
                previous_duration = total_duration
                continue

            allowed = previous_duration * (1 + thresholds.weekly_progression)

            # Add a small buffer (15 minutes) to avoid penalizing minor fluctuations
            allowed += 15

            if total_duration > allowed and total_duration - previous_duration > 15:
                growth = (
                    (total_duration - previous_duration)
                    / max(previous_duration, 1)
                )
                violations.append(
                    f"Week {stats['week']}: volume increase {growth:.2%} exceeds limit {thresholds.weekly_progression:.0%}"
                )

            previous_duration = total_duration

        return violations

    def _count_rest_days(self, workouts: List[Dict[str, Any]]) -> int:
        days_with_workouts = {
            (workout.get("day") or "").strip().lower() for workout in workouts
        }
        days_with_workouts.discard("")

        # If day labels are outside weekday names, fall back to count by entries
        if not days_with_workouts.issubset(self.WEEKDAY_NAMES):
            unique_days = len(days_with_workouts)
            if unique_days >= 7:
                return 0
            return max(0, 7 - unique_days)

        return max(0, 7 - len(days_with_workouts))

    def _resolve_duration_minutes(self, workout: Dict[str, Any]) -> float:
        duration = workout.get("duration_minutes")
        if isinstance(duration, (int, float)) and duration >= 0:
            return float(duration)

        structure = workout.get("structure") or {}
        segments = structure.get("segments") or []
        total_seconds = 0
        for segment in segments:
            steps = segment.get("steps") or []
            for step in steps:
                duration_data = step.get("duration") or {}
                if duration_data.get("type") == "time":
                    total_seconds += duration_data.get("seconds", 0)

        return total_seconds / 60 if total_seconds else 0.0

    def _is_high_intensity(self, workout: Dict[str, Any]) -> bool:
        zone = (workout.get("zone") or "").upper()
        intensity = (workout.get("intensity") or "").upper()
        rpe = workout.get("rpe_target")

        high_zone = any(token in zone for token in ("Z4", "Z5"))
        high_intensity = any(token in intensity for token in ("Z4", "Z5", "INTERVAL", "TEMPO", "RACE"))
        high_rpe = isinstance(rpe, (int, float)) and rpe >= 7

        if high_zone or high_intensity or high_rpe:
            return True

        structure = workout.get("structure") or {}
        segments = structure.get("segments") or []
        for segment in segments:
            steps = segment.get("steps") or []
            for step in steps:
                target = step.get("target") or {}
                target_zone = (target.get("zone") or "").upper()
                if "Z4" in target_zone or "Z5" in target_zone:
                    return True

        return False

    def _validate_structure(self, workout: Dict[str, Any]) -> Optional[str]:
        structure = workout.get("structure")
        if not structure:
            return "workout is missing structured segments"

        segments = structure.get("segments")
        if not isinstance(segments, list) or not segments:
            return "workout structure has no segments"

        segment_types = {segment.get("segment_type", "").lower() for segment in segments}
        missing_required = self.STRUCTURE_SEGMENTS_REQUIRED - segment_types
        if missing_required:
            return f"workout structure missing segments: {', '.join(sorted(missing_required))}"

        return None

