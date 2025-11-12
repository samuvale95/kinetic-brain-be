from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Tuple

from loguru import logger
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.daily_metrics import DailyPerformanceMetrics, DailyReadinessMetrics
from app.models.metrics_job import MetricsPendingJob
from app.models.training_metrics import WeeklyTrainingSummary
from app.models.strava import StravaAccount, StravaActivity
from app.models.workout import Workout, WorkoutSession, WorkoutStatus


def _start_of_week(target_date: date) -> date:
    return target_date - timedelta(days=target_date.weekday())


class AdvancedMetricsService:
    """Compute advanced daily and weekly training metrics."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def compute_and_store_daily_readiness(
        self,
        user_id: int,
        metric_date: date,
        inputs: Optional[Dict[str, Any]] = None,
    ) -> DailyReadinessMetrics:
        """Compute the daily readiness entry for a user and persist it."""
        inputs = inputs or {}

        historical = self._fetch_recent_readiness(user_id=user_id, before_date=metric_date, days=7)
        baseline_hrv = self._resolve_baseline(inputs.get("hrv_baseline"), [entry.hrv_value for entry in historical])
        baseline_rhr = self._resolve_baseline(inputs.get("rhr_baseline"), [entry.rhr_value for entry in historical])

        hrv_value = self._ensure_float(inputs.get("hrv_value"))
        rhr_value = self._ensure_float(inputs.get("rhr_value"))
        sleep_hours = self._ensure_float(inputs.get("sleep_hours"))
        sleep_quality_score = self._ensure_float(inputs.get("sleep_quality_score"))
        epoc = self._ensure_float(inputs.get("epoc"))
        hydration_score = self._ensure_float(inputs.get("hydration_score"))
        nutrition_score = self._ensure_float(inputs.get("nutrition_score"))
        weight_delta_kg = self._ensure_float(inputs.get("weight_delta_kg"))

        hrv_delta = self._safe_delta(hrv_value, baseline_hrv)
        rhr_delta = self._safe_delta(rhr_value, baseline_rhr)

        ctl, atl, tsb = self._fetch_daily_performance_load(user_id, metric_date)

        recovery_index = self._calculate_recovery_index(
            hrv_value=hrv_value,
            baseline_hrv=baseline_hrv,
            rhr_value=rhr_value,
            baseline_rhr=baseline_rhr,
            sleep_hours=sleep_hours,
            sleep_quality_score=sleep_quality_score,
            epoc=epoc,
            ctl=ctl,
            atl=atl,
            tsb=tsb,
        )
        readiness_state = self._classify_readiness(recovery_index)

        record = (
            self.db.query(DailyReadinessMetrics)
            .filter(
                DailyReadinessMetrics.user_id == user_id,
                DailyReadinessMetrics.metric_date == metric_date,
            )
            .one_or_none()
        )

        if record is None:
            record = DailyReadinessMetrics(user_id=user_id, metric_date=metric_date)

        record.hrv_baseline = baseline_hrv
        record.hrv_value = hrv_value
        record.hrv_delta = hrv_delta

        record.rhr_baseline = baseline_rhr
        record.rhr_value = rhr_value
        record.rhr_delta = rhr_delta

        record.sleep_hours = sleep_hours
        record.sleep_quality_score = sleep_quality_score
        record.epoc = epoc

        record.recovery_index = recovery_index
        record.readiness_state = readiness_state

        record.hydration_status = inputs.get("hydration_status")
        record.hydration_score = hydration_score
        record.nutrition_score = nutrition_score
        record.weight_delta_kg = weight_delta_kg
        record.notes = inputs.get("notes")

        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)

        logger.info(
            "[ADV_METRICS] Stored daily readiness for user={}, date={}, readiness_state={}",
            user_id,
            metric_date,
            readiness_state,
        )

        return record

    def compute_and_store_weekly_summary(
        self,
        user_id: int,
        week_start: date,
    ) -> WeeklyTrainingSummary:
        """Compute weekly aggregates and persist summary."""
        week_start = _start_of_week(week_start)
        week_end = week_start + timedelta(days=6)

        activities = self._fetch_weekly_activities(user_id, week_start, week_end)
        readiness_records = self._fetch_readiness_range(user_id, week_start, week_end)
        previous_summary = self._fetch_previous_summary(user_id, week_start)

        (total_duration_minutes, total_distance_km, total_tss, sport_breakdown,) = self._aggregate_activity_volume(activities)
        multi_sport_load = self._compute_multi_sport_load(total_tss, total_duration_minutes)

        zone_distribution, high_intensity_ratio, high_intensity_sessions = self._aggregate_intensity_metrics(activities)

        current_longest_duration = self._largest_by_key(sport_breakdown, "max_duration")
        current_longest_distance = self._largest_by_key(sport_breakdown, "max_distance")
        (
            longest_duration,
            longest_distance,
            long_progression_pct,
        ) = self._compute_long_workout_progression(
            current_longest_duration_minutes=current_longest_duration,
            current_longest_distance_km=current_longest_distance,
            previous_summary=previous_summary,
        )

        readiness_score = self._average([record.recovery_index for record in readiness_records])
        hydration_score = self._average([record.hydration_score for record in readiness_records])

        injury_risk_score = self._compute_injury_risk(
            weekly_progression_pct=self._compute_weekly_progression_pct(previous_summary, total_duration_minutes),
            high_intensity_ratio=high_intensity_ratio,
            readiness_score=readiness_score,
        )

        compliance_score, adherence_details = self._compute_plan_compliance(
            user_id=user_id,
            week_start=week_start,
            week_end=week_end,
        )

        record = (
            self.db.query(WeeklyTrainingSummary)
            .filter(
                WeeklyTrainingSummary.user_id == user_id,
                WeeklyTrainingSummary.week_start == week_start,
            )
            .one_or_none()
        )
        if record is None:
            record = WeeklyTrainingSummary(user_id=user_id, week_start=week_start, week_end=week_end)

        record.week_end = week_end
        record.total_duration_minutes = total_duration_minutes
        record.total_distance_km = total_distance_km
        record.total_tss = total_tss
        record.multi_sport_load = multi_sport_load
        record.sport_breakdown = sport_breakdown or None
        record.zone_distribution = zone_distribution or None
        record.high_intensity_ratio = high_intensity_ratio
        record.high_intensity_sessions = high_intensity_sessions
        record.longest_workout_duration_minutes = longest_duration
        record.longest_workout_distance_km = longest_distance
        record.long_workout_progression_pct = long_progression_pct
        record.readiness_score = readiness_score
        record.injury_risk_score = injury_risk_score
        record.compliance_score = compliance_score
        record.hydration_score = hydration_score
        record.plan_adherence_details = adherence_details or None

        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)

        logger.info(
            "[ADV_METRICS] Stored weekly summary for user={}, week_start={}, total_tss={}, injury_risk={}",
            user_id,
            week_start,
            total_tss,
            injury_risk_score,
        )

        return record

    def enqueue_job(self, job_type: str, user_id: Optional[int], payload: Optional[Dict[str, Any]] = None, priority: int = 0) -> MetricsPendingJob:
        job = MetricsPendingJob(
            job_type=job_type,
            user_id=user_id,
            payload=payload,
            priority=priority,
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        logger.debug("[ADV_METRICS] Enqueued job type={} id={}", job_type, job.id)
        return job

    def fetch_next_jobs(self, limit: int = 5) -> List[MetricsPendingJob]:
        stmt = (
            select(MetricsPendingJob)
            .where(MetricsPendingJob.status == "pending")
            .order_by(MetricsPendingJob.priority.desc(), MetricsPendingJob.available_at.asc())
            .limit(limit)
        )
        jobs = list(self.db.execute(stmt).scalars())
        return jobs

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _fetch_recent_readiness(self, user_id: int, before_date: date, days: int) -> List[DailyReadinessMetrics]:
        start_date = before_date - timedelta(days=days)
        return (
            self.db.query(DailyReadinessMetrics)
            .filter(
                DailyReadinessMetrics.user_id == user_id,
                DailyReadinessMetrics.metric_date >= start_date,
                DailyReadinessMetrics.metric_date < before_date,
            )
            .order_by(DailyReadinessMetrics.metric_date.desc())
            .all()
        )

    def _fetch_daily_performance_load(self, user_id: int, metric_date: date) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        metrics = (
            self.db.query(DailyPerformanceMetrics)
            .filter(
                DailyPerformanceMetrics.user_id == user_id,
                DailyPerformanceMetrics.metric_date == metric_date,
            )
            .one_or_none()
        )
        if metrics:
            return metrics.ctl, metrics.atl, metrics.tsb
        return None, None, None

    def _fetch_weekly_activities(self, user_id: int, week_start: date, week_end: date) -> List[StravaActivity]:
        stmt = (
            self.db.query(StravaActivity)
            .join(StravaAccount, StravaActivity.strava_account_id == StravaAccount.id)
            .filter(StravaAccount.user_id == user_id)
            .filter(StravaActivity.start_date >= datetime.combine(week_start, datetime.min.time()))
            .filter(StravaActivity.start_date <= datetime.combine(week_end, datetime.max.time()))
        )
        return stmt.all()

    def _fetch_readiness_range(self, user_id: int, start: date, end: date) -> List[DailyReadinessMetrics]:
        return (
            self.db.query(DailyReadinessMetrics)
            .filter(
                DailyReadinessMetrics.user_id == user_id,
                DailyReadinessMetrics.metric_date >= start,
                DailyReadinessMetrics.metric_date <= end,
            )
            .all()
        )

    def _fetch_previous_summary(self, user_id: int, week_start: date) -> Optional[WeeklyTrainingSummary]:
        previous_week_start = week_start - timedelta(days=7)
        return (
            self.db.query(WeeklyTrainingSummary)
            .filter(
                WeeklyTrainingSummary.user_id == user_id,
                WeeklyTrainingSummary.week_start == previous_week_start,
            )
            .one_or_none()
        )

    # ------------------------------------------------------------------
    # Calculation helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _resolve_baseline(explicit_baseline: Optional[float], historical_values: Iterable[Optional[float]]) -> Optional[float]:
        explicit = AdvancedMetricsService._ensure_float(explicit_baseline)
        if explicit is not None:
            return explicit
        clean_values = [value for value in historical_values if value is not None]
        if not clean_values:
            return None
        return sum(clean_values) / len(clean_values)

    @staticmethod
    def _ensure_float(value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _safe_delta(value: Optional[float], baseline: Optional[float]) -> Optional[float]:
        if value is None or baseline is None:
            return None
        return value - baseline

    def _calculate_recovery_index(
        self,
        *,
        hrv_value: Optional[float],
        baseline_hrv: Optional[float],
        rhr_value: Optional[float],
        baseline_rhr: Optional[float],
        sleep_hours: Optional[float],
        sleep_quality_score: Optional[float],
        epoc: Optional[float],
        ctl: Optional[float],
        atl: Optional[float],
        tsb: Optional[float],
    ) -> Optional[float]:
        components: List[float] = []

        if hrv_value is not None and baseline_hrv:
            ratio = min(max(hrv_value / baseline_hrv, 0), 2)
            components.append(ratio)

        if rhr_value is not None and baseline_rhr:
            ratio = baseline_rhr / rhr_value if rhr_value else None
            if ratio is not None:
                components.append(min(max(ratio, 0), 2))

        if sleep_hours is not None:
            components.append(min(sleep_hours / 8.0, 1.2))

        if sleep_quality_score is not None:
            components.append(min(max(sleep_quality_score / 100.0, 0), 1.2))

        if epoc is not None:
            normalized_epoc = max(0.0, min(1.0, 1 - (epoc / 100.0)))
            components.append(normalized_epoc)

        if ctl is not None and atl is not None and ctl > 0:
            acwr = atl / ctl
            components.append(max(0.0, min(1.5, 1.5 - abs(acwr - 1.0))))

        if tsb is not None:
            tsb_component = max(0.0, min(1.5, (tsb + 20) / 40))
            components.append(tsb_component)

        if not components:
            return None

        recovery_index = sum(components) / len(components)
        return round(recovery_index, 4)

    @staticmethod
    def _classify_readiness(recovery_index: Optional[float]) -> Optional[str]:
        if recovery_index is None:
            return None
        if recovery_index >= 1.0:
            return "ready"
        if recovery_index >= 0.7:
            return "caution"
        return "rest"

    def _aggregate_activity_volume(
        self,
        activities: Iterable[StravaActivity],
    ) -> Tuple[float, float, float, Dict[str, Dict[str, Any]]]:
        total_duration_minutes = 0.0
        total_distance_km = 0.0
        total_tss = 0.0
        sport_breakdown: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "sessions": 0,
            "duration_minutes": 0.0,
            "distance_km": 0.0,
            "tss": 0.0,
            "max_duration": 0.0,
            "max_distance": 0.0,
        })

        for activity in activities:
            sport = (activity.sport_type or activity.type or "other").lower()
            duration_minutes = (activity.moving_time or 0) / 60.0
            distance_km = (activity.distance or 0) / 1000.0
            tss = activity.tss or 0.0

            total_duration_minutes += duration_minutes
            total_distance_km += distance_km
            total_tss += tss

            sport_stats = sport_breakdown[sport]
            sport_stats["sessions"] += 1
            sport_stats["duration_minutes"] += duration_minutes
            sport_stats["distance_km"] += distance_km
            sport_stats["tss"] += tss
            sport_stats["max_duration"] = max(sport_stats["max_duration"], duration_minutes)
            sport_stats["max_distance"] = max(sport_stats["max_distance"], distance_km)

        return (
            round(total_duration_minutes, 2),
            round(total_distance_km, 2),
            round(total_tss, 2),
            {sport: {key: round(value, 2) if isinstance(value, float) else value for key, value in stats.items()} for sport, stats in sport_breakdown.items()},
        )

    @staticmethod
    def _compute_multi_sport_load(total_tss: float, total_duration_minutes: float) -> Optional[float]:
        if total_tss:
            return round(total_tss, 2)
        if total_duration_minutes:
            return round(total_duration_minutes, 2)
        return None

    def _aggregate_intensity_metrics(
        self,
        activities: Iterable[StravaActivity],
    ) -> Tuple[Optional[Dict[str, float]], Optional[float], int]:
        zone_totals = defaultdict(float)
        high_intensity_time = 0.0
        total_zone_time = 0.0
        high_intensity_sessions = 0

        for activity in activities:
            has_high_intensity = False

            for zone_key in ("time_in_zone_1", "time_in_zone_2", "time_in_zone_3", "time_in_zone_4", "time_in_zone_5"):
                seconds = getattr(activity, zone_key, None)
                if seconds:
                    minutes = seconds / 60.0
                    zone_totals[zone_key] += minutes
                    total_zone_time += minutes
                    if zone_key in ("time_in_zone_4", "time_in_zone_5"):
                        high_intensity_time += minutes
                        has_high_intensity = True

            if not has_high_intensity:
                if (activity.zone_distribution or {}).get("z4") or (activity.zone_distribution or {}).get("z5"):
                    high_intensity_sessions += 1
            else:
                high_intensity_sessions += 1

        if total_zone_time == 0 and zone_totals:
            total_zone_time = sum(zone_totals.values())

        zone_distribution = None
        if total_zone_time:
            zone_distribution = {
                zone.replace("time_in_", ""): round(minutes / total_zone_time, 4)
                for zone, minutes in zone_totals.items()
            }

        high_intensity_ratio = None
        if total_zone_time:
            high_intensity_ratio = round(high_intensity_time / total_zone_time, 4)

        return zone_distribution, high_intensity_ratio, high_intensity_sessions

    def _compute_long_workout_progression(
        self,
        *,
        current_longest_duration_minutes: Optional[float],
        current_longest_distance_km: Optional[float],
        previous_summary: Optional[WeeklyTrainingSummary],
    ) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        longest_duration = round(current_longest_duration_minutes, 2) if current_longest_duration_minutes is not None else None
        longest_distance = round(current_longest_distance_km, 2) if current_longest_distance_km is not None else None

        previous_long = previous_summary.longest_workout_duration_minutes if previous_summary else None
        if previous_long and longest_duration is not None and previous_long > 0:
            long_progression_pct = round((longest_duration - previous_long) / previous_long * 100, 2)
        else:
            long_progression_pct = None

        return longest_duration, longest_distance, long_progression_pct

    @staticmethod
    def _largest_by_key(sport_breakdown: Dict[str, Dict[str, Any]], key: str) -> Optional[float]:
        values = [stats.get(key) for stats in sport_breakdown.values() if stats.get(key)]
        if not values:
            return None
        return max(values)

    def _compute_weekly_progression_pct(
        self,
        previous_summary: Optional[WeeklyTrainingSummary],
        current_total_duration_minutes: Optional[float],
    ) -> Optional[float]:
        if previous_summary is None:
            return None
        previous_total = previous_summary.total_duration_minutes or 0
        current_total = current_total_duration_minutes or 0
        if previous_total <= 0:
            return None
        progression = (current_total - previous_total) / previous_total
        return round(progression * 100, 2)

    @staticmethod
    def _compute_injury_risk(
        *,
        weekly_progression_pct: Optional[float],
        high_intensity_ratio: Optional[float],
        readiness_score: Optional[float],
    ) -> Optional[float]:
        components: List[float] = []

        if weekly_progression_pct is not None:
            components.append(min(max(weekly_progression_pct / 20.0, 0), 2))

        if high_intensity_ratio is not None:
            components.append(min(max(high_intensity_ratio / 0.3, 0), 2))

        if readiness_score is not None:
            components.append(max(0.0, min(2.0, 1.5 - readiness_score)))

        if not components:
            return None

        risk = sum(components) / len(components)
        return round(min(risk, 2.0), 4)

    def _compute_plan_compliance(
        self,
        *,
        user_id: int,
        week_start: date,
        week_end: date,
    ) -> Tuple[Optional[float], Optional[Dict[str, Any]]]:
        planned_workouts = (
            self.db.query(Workout)
            .filter(
                Workout.user_id == user_id,
                Workout.scheduled_date >= week_start,
                Workout.scheduled_date <= week_end,
            )
            .all()
        )
        planned_count = len(planned_workouts)
        if planned_count == 0:
            return None, None

        completed_sessions = (
            self.db.query(WorkoutSession)
            .filter(
                WorkoutSession.user_id == user_id,
                WorkoutSession.actual_date >= datetime.combine(week_start, datetime.min.time()),
                WorkoutSession.actual_date <= datetime.combine(week_end, datetime.max.time()),
            )
            .all()
        )
        completed_count = len(completed_sessions)

        scheduled_completed = sum(
            1 for workout in planned_workouts if workout.status == WorkoutStatus.COMPLETED
        )
        scheduled_skipped = sum(
            1 for workout in planned_workouts if workout.status == WorkoutStatus.SKIPPED
        )

        compliance_score = completed_count / planned_count if planned_count else None
        if compliance_score is not None:
            compliance_score = round(compliance_score, 4)

        details = {
            "planned": planned_count,
            "completed_sessions": completed_count,
            "scheduled_completed": scheduled_completed,
            "scheduled_skipped": scheduled_skipped,
        }
        return compliance_score, details

    @staticmethod
    def _average(values: Iterable[Optional[float]]) -> Optional[float]:
        clean = [value for value in values if value is not None]
        if not clean:
            return None
        return round(sum(clean) / len(clean), 4)

