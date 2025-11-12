from __future__ import annotations

import enum
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Tuple

from loguru import logger
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models.daily_metrics import DailyPerformanceMetrics, DailyReadinessMetrics
from app.models.strava import StravaAccount, StravaActivity
from app.models.training_metrics import WeeklyTrainingSummary


class GroupingGranularity(str, enum.Enum):
    day = "day"
    week = "week"
    month = "month"
    year = "year"


@dataclass(frozen=True)
class Period:
    start: date
    end: date


class MetricsApiService:
    """Provide aggregated metrics for API consumption with flexible grouping."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Public load endpoints
    # ------------------------------------------------------------------
    def get_load_series(
        self,
        *,
        user_id: int,
        start_date: date,
        end_date: date,
        grouping: GroupingGranularity,
        sport: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        logger.bind(user_id=user_id, grouping=grouping.value).info(
            "[METRICS][LOAD] Building load series"
        )

        periods = self._generate_periods(start_date, end_date, grouping)
        if not periods:
            return []

        if grouping == GroupingGranularity.week:
            summaries = self._fetch_weekly_summaries(
                user_id=user_id, start_date=periods[0].start, end_date=periods[-1].end, sport=sport
            )
            return [self._serialize_weekly_summary(summary) for summary in summaries]

        activities = self._fetch_activities(user_id=user_id, start=start_date, end=end_date, sport=sport)
        daily_metrics = self._fetch_daily_performance_metrics(user_id=user_id, start=start_date, end=end_date)
        weekly_summaries = self._fetch_weekly_summaries(
            user_id=user_id, start_date=start_date, end_date=end_date, sport=sport
        )

        if grouping == GroupingGranularity.day:
            return [
                self._aggregate_load_for_period(
                    activities=activities,
                    daily_metrics=daily_metrics,
                    weekly_summaries=weekly_summaries,
                    period=period,
                    include_compliance=False,
                )
                for period in periods
            ]

        # month / year -> aggregate from weekly summaries & activities
        return [
            self._aggregate_load_for_period(
                activities=activities,
                daily_metrics=daily_metrics,
                weekly_summaries=weekly_summaries,
                period=period,
                include_compliance=True,
            )
            for period in periods
        ]

    # ------------------------------------------------------------------
    # Public readiness endpoints
    # ------------------------------------------------------------------
    def get_readiness_series(
        self,
        *,
        user_id: int,
        start_date: date,
        end_date: date,
        grouping: GroupingGranularity,
    ) -> List[Dict[str, Any]]:
        logger.bind(user_id=user_id, grouping=grouping.value).info(
            "[METRICS][READINESS] Building readiness series"
        )

        periods = self._generate_periods(start_date, end_date, grouping)
        if not periods:
            return []

        readiness_records = self._fetch_readiness_metrics(user_id=user_id, start=start_date, end=end_date)
        weekly_summaries = self._fetch_weekly_summaries(
            user_id=user_id,
            start_date=periods[0].start,
            end_date=periods[-1].end,
            sport=None,
        )

        readiness_by_date = defaultdict(list)
        for record in readiness_records:
            readiness_by_date[record.metric_date].append(record)

        summaries_by_week_start = {summary.week_start: summary for summary in weekly_summaries}

        response = []
        for period in periods:
            entries = self._collect_records_in_period(readiness_by_date, period.start, period.end)
            if not entries:
                response.append(
                    {
                        "period_start": period.start,
                        "period_end": period.end,
                        "recovery_index": None,
                        "readiness_state": None,
                        "hydration_score": None,
                        "nutrition_score": None,
                        "hrv": None,
                        "rhr": None,
                        "sleep_hours": None,
                        "sleep_quality_score": None,
                        "epoc": None,
                        "injury_risk_score": self._lookup_injury_risk(period, summaries_by_week_start),
                    }
                )
                continue

            recovery_index = self._average(
                entry.recovery_index for entry in entries if entry.recovery_index is not None
            )
            readiness_state = self._mode(
                entry.readiness_state for entry in entries if entry.readiness_state
            )
            hydration_score = self._average(
                entry.hydration_score for entry in entries if entry.hydration_score is not None
            )
            nutrition_score = self._average(
                entry.nutrition_score for entry in entries if entry.nutrition_score is not None
            )
            hrv_baseline = self._average(
                entry.hrv_baseline for entry in entries if entry.hrv_baseline is not None
            )
            hrv_value = self._average(
                entry.hrv_value for entry in entries if entry.hrv_value is not None
            )
            hrv_delta = None
            if hrv_value is not None and hrv_baseline is not None:
                hrv_delta = round(hrv_value - hrv_baseline, 4)

            rhr_baseline = self._average(
                entry.rhr_baseline for entry in entries if entry.rhr_baseline is not None
            )
            rhr_value = self._average(
                entry.rhr_value for entry in entries if entry.rhr_value is not None
            )
            rhr_delta = None
            if rhr_value is not None and rhr_baseline is not None:
                rhr_delta = round(rhr_value - rhr_baseline, 4)

            sleep_hours = self._average(entry.sleep_hours for entry in entries if entry.sleep_hours is not None)
            sleep_quality = self._average(
                entry.sleep_quality_score for entry in entries if entry.sleep_quality_score is not None
            )
            epoc = self._average(entry.epoc for entry in entries if entry.epoc is not None)

            response.append(
                {
                    "period_start": period.start,
                    "period_end": period.end,
                    "recovery_index": recovery_index,
                    "readiness_state": readiness_state,
                    "hydration_score": hydration_score,
                    "nutrition_score": nutrition_score,
                    "hrv": {
                        "baseline": hrv_baseline,
                        "value": hrv_value,
                        "delta": hrv_delta,
                    },
                    "rhr": {
                        "baseline": rhr_baseline,
                        "value": rhr_value,
                        "delta": rhr_delta,
                    },
                    "sleep_hours": sleep_hours,
                    "sleep_quality_score": sleep_quality,
                    "epoc": epoc,
                    "injury_risk_score": self._lookup_injury_risk(period, summaries_by_week_start),
                }
            )

        return response

    # ------------------------------------------------------------------
    # Load helpers
    # ------------------------------------------------------------------
    def _aggregate_load_for_period(
        self,
        *,
        activities: List[StravaActivity],
        daily_metrics: Dict[date, DailyPerformanceMetrics],
        weekly_summaries: List[WeeklyTrainingSummary],
        period: Period,
        include_compliance: bool,
    ) -> Dict[str, Any]:
        period_activities = [
            activity
            for activity in activities
            if period.start <= activity.start_date.date() <= period.end
        ]

        sport_breakdown: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"sessions": 0, "duration_minutes": 0.0, "distance_km": 0.0, "tss": 0.0, "max_duration_minutes": 0.0, "max_distance_km": 0.0}
        )
        total_duration_minutes = 0.0
        total_distance_km = 0.0
        total_tss = 0.0
        high_intensity_time = 0.0
        total_zone_time = 0.0
        high_intensity_sessions = 0

        for activity in period_activities:
            sport = self._normalize_sport(activity.sport_type or activity.type)
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
            sport_stats["max_duration_minutes"] = max(sport_stats["max_duration_minutes"], duration_minutes)
            sport_stats["max_distance_km"] = max(sport_stats["max_distance_km"], distance_km)

            has_high_intensity = False
            for zone_key in ("time_in_zone_4", "time_in_zone_5"):
                value = getattr(activity, zone_key, None)
                if value:
                    has_high_intensity = True
                    high_intensity_time += value / 60.0
            if has_high_intensity:
                high_intensity_sessions += 1

            for zone_key in ("time_in_zone_1", "time_in_zone_2", "time_in_zone_3", "time_in_zone_4", "time_in_zone_5"):
                value = getattr(activity, zone_key, None)
                if value:
                    total_zone_time += value / 60.0

        zone_distribution = None
        if total_zone_time:
            zone_totals = defaultdict(float)
            for activity in period_activities:
                for zone_key in ("time_in_zone_1", "time_in_zone_2", "time_in_zone_3", "time_in_zone_4", "time_in_zone_5"):
                    value = getattr(activity, zone_key, None)
                    if value:
                        zone_totals[zone_key] += value / 60.0
            zone_distribution = {
                zone.replace("time_in_", ""): round(minutes / total_zone_time, 4)
                for zone, minutes in zone_totals.items()
            }

        daily_summary = [
            daily_metrics.get(day)
            for day in self._iterate_dates(period.start, period.end)
            if day in daily_metrics
        ]

        ctl = self._average(metric.ctl for metric in daily_summary if metric and metric.ctl is not None)
        atl = self._average(metric.atl for metric in daily_summary if metric and metric.atl is not None)
        tsb = self._average(metric.tsb for metric in daily_summary if metric and metric.tsb is not None)

        multi_sport_load = total_tss if total_tss else total_duration_minutes
        high_intensity_ratio = None
        if total_zone_time:
            high_intensity_ratio = round(high_intensity_time / total_zone_time, 4)

        result: Dict[str, Any] = {
            "period_start": period.start,
            "period_end": period.end,
            "total_duration_minutes": round(total_duration_minutes, 2),
            "total_distance_km": round(total_distance_km, 2),
            "total_tss": round(total_tss, 2),
            "multi_sport_load": round(multi_sport_load, 2) if multi_sport_load else None,
            "ct_load": ctl,
            "acute_load": atl,
            "training_stress_balance": tsb,
            "sport_breakdown": {sport: self._round_dict(values) for sport, values in sport_breakdown.items()},
            "high_intensity_ratio": high_intensity_ratio,
            "high_intensity_sessions": high_intensity_sessions,
            "long_workout": self._extract_long_workout(sport_breakdown),
            "compliance_score": None,
            "plan_adherence": None,
        }

        if include_compliance:
            summaries_in_period = [
                summary for summary in weekly_summaries if period.start <= summary.week_start <= period.end
            ]
            if summaries_in_period:
                compliance_values = [summary.compliance_score for summary in summaries_in_period if summary.compliance_score is not None]
                result["compliance_score"] = self._average(compliance_values)
                adherence_accumulator = {
                    "planned": 0,
                    "completed_sessions": 0,
                    "scheduled_completed": 0,
                    "scheduled_skipped": 0,
                }
                for summary in summaries_in_period:
                    if summary.plan_adherence_details:
                        for key in adherence_accumulator.keys():
                            adherence_accumulator[key] += summary.plan_adherence_details.get(key, 0)
                if any(adherence_accumulator.values()):
                    result["plan_adherence"] = adherence_accumulator

        return result

    def _serialize_weekly_summary(self, summary: WeeklyTrainingSummary) -> Dict[str, Any]:
        return {
            "period_start": summary.week_start,
            "period_end": summary.week_end,
            "total_duration_minutes": summary.total_duration_minutes,
            "total_distance_km": summary.total_distance_km,
            "total_tss": summary.total_tss,
            "multi_sport_load": summary.multi_sport_load,
            "sport_breakdown": summary.sport_breakdown,
            "high_intensity_ratio": summary.high_intensity_ratio,
            "high_intensity_sessions": summary.high_intensity_sessions,
            "long_workout": {
                "duration_minutes": summary.longest_workout_duration_minutes,
                "distance_km": summary.longest_workout_distance_km,
                "progression_pct": summary.long_workout_progression_pct,
            },
            "compliance_score": summary.compliance_score,
            "plan_adherence": summary.plan_adherence_details,
        }

    # ------------------------------------------------------------------
    # Data fetchers
    # ------------------------------------------------------------------
    def _fetch_activities(
        self, *, user_id: int, start: date, end: date, sport: Optional[str]
    ) -> List[StravaActivity]:
        stmt = (
            select(StravaActivity)
            .join(StravaAccount, StravaActivity.strava_account_id == StravaAccount.id)
            .where(StravaAccount.user_id == user_id)
            .where(StravaActivity.start_date >= datetime.combine(start, datetime.min.time()))
            .where(StravaActivity.start_date <= datetime.combine(end, datetime.max.time()))
        )
        if sport and sport != "all":
            stmt = stmt.where(
                func.lower(StravaActivity.sport_type) == sport.lower()
            )

        activities = list(self.db.execute(stmt).scalars())
        logger.debug(f"[METRICS] Loaded {len(activities)} activities for load aggregation")
        return activities

    def _fetch_daily_performance_metrics(
        self, *, user_id: int, start: date, end: date
    ) -> Dict[date, DailyPerformanceMetrics]:
        stmt = (
            select(DailyPerformanceMetrics)
            .where(DailyPerformanceMetrics.user_id == user_id)
            .where(DailyPerformanceMetrics.metric_date >= start)
            .where(DailyPerformanceMetrics.metric_date <= end)
        )
        records = list(self.db.execute(stmt).scalars())
        return {record.metric_date: record for record in records}

    def _fetch_weekly_summaries(
        self,
        *,
        user_id: int,
        start_date: date,
        end_date: date,
        sport: Optional[str],
    ) -> List[WeeklyTrainingSummary]:
        stmt = (
            select(WeeklyTrainingSummary)
            .where(WeeklyTrainingSummary.user_id == user_id)
            .where(WeeklyTrainingSummary.week_start >= start_date - timedelta(days=7))
            .where(WeeklyTrainingSummary.week_end <= end_date + timedelta(days=7))
            .order_by(WeeklyTrainingSummary.week_start.asc())
        )
        summaries = list(self.db.execute(stmt).scalars())
        if sport and sport != "all":
            filtered = []
            for summary in summaries:
                breakdown = summary.sport_breakdown or {}
                if sport in breakdown:
                    filtered.append(summary)
            return filtered
        return summaries

    def _fetch_readiness_metrics(
        self, *, user_id: int, start: date, end: date
    ) -> List[DailyReadinessMetrics]:
        stmt = (
            select(DailyReadinessMetrics)
            .where(DailyReadinessMetrics.user_id == user_id)
            .where(DailyReadinessMetrics.metric_date >= start)
            .where(DailyReadinessMetrics.metric_date <= end)
        )
        records = list(self.db.execute(stmt).scalars())
        logger.debug(f"[METRICS] Loaded {len(records)} readiness records")
        return records

    # ------------------------------------------------------------------
    # Utility functions
    # ------------------------------------------------------------------
    def _generate_periods(
        self, start_date: date, end_date: date, grouping: GroupingGranularity
    ) -> List[Period]:
        if start_date > end_date:
            return []

        periods: List[Period] = []
        current_start = start_date

        while current_start <= end_date:
            if grouping == GroupingGranularity.day:
                current_end = current_start
            elif grouping == GroupingGranularity.week:
                current_end = current_start + timedelta(days=(6 - current_start.weekday()))
            elif grouping == GroupingGranularity.month:
                next_month = (current_start.replace(day=1) + timedelta(days=32)).replace(day=1)
                current_end = next_month - timedelta(days=1)
            else:  # year
                current_end = current_start.replace(month=12, day=31)

            if current_end > end_date:
                current_end = end_date

            periods.append(Period(start=current_start, end=current_end))

            if grouping == GroupingGranularity.day:
                current_start += timedelta(days=1)
            elif grouping == GroupingGranularity.week:
                current_start = current_end + timedelta(days=1)
            elif grouping == GroupingGranularity.month:
                current_start = (current_start.replace(day=1) + timedelta(days=32)).replace(day=1)
            else:
                current_start = (current_start.replace(month=1, day=1) + timedelta(days=366)).replace(month=1, day=1)

        return periods

    @staticmethod
    def _normalize_sport(value: Optional[str]) -> str:
        if not value:
            return "other"
        value = value.lower()
        mapping = {
            "run": "running",
            "running": "running",
            "trail": "running",
            "trail running": "running",
            "ride": "cycling",
            "bike": "cycling",
            "cycling": "cycling",
            "virtualride": "cycling",
            "swim": "swim",
            "swimming": "swim",
            "triathlon": "triathlon",
        }
        return mapping.get(value, value)

    @staticmethod
    def _round_dict(values: Dict[str, Any]) -> Dict[str, Any]:
        rounded = {}
        for key, value in values.items():
            if isinstance(value, float):
                rounded[key] = round(value, 2)
            else:
                rounded[key] = value
        return rounded

    @staticmethod
    def _extract_long_workout(breakdown: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        longest_duration = None
        longest_distance = None
        for stats in breakdown.values():
            duration = stats.get("max_duration_minutes")
            distance = stats.get("max_distance_km")
            if duration is not None:
                longest_duration = max(longest_duration or 0.0, duration)
            if distance is not None:
                longest_distance = max(longest_distance or 0.0, distance)

        if longest_duration is None and longest_distance is None:
            return None

        return {
            "duration_minutes": round(longest_duration, 2) if longest_duration is not None else None,
            "distance_km": round(longest_distance, 2) if longest_distance is not None else None,
        }

    @staticmethod
    def _iterate_dates(start: date, end: date) -> Iterable[date]:
        current = start
        while current <= end:
            yield current
            current += timedelta(days=1)

    @staticmethod
    def _average(values: Iterable[Optional[float]]) -> Optional[float]:
        cleaned = [value for value in values if value is not None]
        if not cleaned:
            return None
        return round(sum(cleaned) / len(cleaned), 4)

    @staticmethod
    def _mode(values: Iterable[str]) -> Optional[str]:
        cleaned = [value for value in values if value]
        if not cleaned:
            return None
        counter = Counter(cleaned)
        return counter.most_common(1)[0][0]

    @staticmethod
    def _collect_records_in_period(source: Dict[date, List[Any]], start: date, end: date) -> List[Any]:
        entries: List[Any] = []
        for current in MetricsApiService._iterate_dates(start, end):
            entries.extend(source.get(current, []))
        return entries

    @staticmethod
    def _lookup_injury_risk(
        period: Period, summaries_by_week_start: Dict[date, WeeklyTrainingSummary]
    ) -> Optional[float]:
        relevant_scores = []
        for week_start, summary in summaries_by_week_start.items():
            if period.start <= week_start <= period.end and summary.injury_risk_score is not None:
                relevant_scores.append(summary.injury_risk_score)
        if not relevant_scores:
            return None
        return round(sum(relevant_scores) / len(relevant_scores), 4)

