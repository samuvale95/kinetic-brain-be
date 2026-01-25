from datetime import date, timedelta
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.workout import Workout, WorkoutPlan
from app.models.daily_metrics import DailyPerformanceMetrics
from loguru import logger


class RaceService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def predict_race_time(
        self,
        user_id: int,
        race_date: date,
        race_distance_km: float,
        target_time_minutes: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Predict race time from CTL and simple model."""
        today = date.today()
        days = (race_date - today).days
        if days < 0:
            return {"error": "Race date is in the past", "predicted_time_minutes": None, "confidence": 0}

        m = (
            self.db.query(DailyPerformanceMetrics)
            .filter(
                DailyPerformanceMetrics.user_id == user_id,
                DailyPerformanceMetrics.metric_date <= today,
            )
            .order_by(DailyPerformanceMetrics.metric_date.desc())
            .first()
        )
        if not m or m.ctl is None:
            return {
                "error": "Insufficient training data",
                "predicted_time_minutes": None,
                "confidence": 0,
            }

        ctl = float(m.ctl)
        weeks = max(0, days / 7.0)
        projected_ctl = ctl + weeks * 0.5

        bases = {5: 4.0, 10: 4.2, 21.097: 4.5, 42.195: 5.0}
        dist = min(bases.keys(), key=lambda d: abs(d - race_distance_km))
        base_pace = bases[dist]
        imp = min((projected_ctl - 50) / 200, 0.2)
        pace = base_pace * (1 - imp)
        pred_min = round(pace * race_distance_km, 1)

        n = (
            self.db.query(DailyPerformanceMetrics)
            .filter(
                DailyPerformanceMetrics.user_id == user_id,
                DailyPerformanceMetrics.ctl.isnot(None),
            )
            .count()
        )
        confidence = min(n / 30.0, 1.0)

        return {
            "predicted_time_minutes": pred_min,
            "predicted_time_formatted": f"{int(pred_min // 60)}h {int(pred_min % 60)} min",
            "predicted_pace_per_km": round(pace, 2),
            "confidence": round(confidence, 2),
            "projected_ctl": round(projected_ctl, 1),
            "current_ctl": round(ctl, 1),
            "days_until_race": days,
            "race_distance_km": race_distance_km,
        }

    def calculate_tapering_plan(
        self, user_id: int, race_date: date, race_distance_km: float
    ) -> Dict[str, Any]:
        """Simple tapering: reduce volume 30–50% in last 2 weeks."""
        today = date.today()
        days = (race_date - today).days
        if days < 14:
            return {"error": "Race too soon (< 2 weeks)", "tapering_plan": None}

        plan = (
            self.db.query(WorkoutPlan)
            .filter(
                WorkoutPlan.user_id == user_id,
                WorkoutPlan.status == "active",
            )
            .first()
        )
        hours = 5.0
        if plan:
            start = today
            end = today + timedelta(days=7)
            ws = (
                self.db.query(Workout)
                .filter(
                    Workout.user_id == user_id,
                    Workout.plan_id == plan.id,
                    Workout.scheduled_date >= start,
                    Workout.scheduled_date < end,
                )
                .all()
            )
            if ws:
                hours = sum(w.duration_minutes or 0 for w in ws) / 60.0

        taper_start = race_date - timedelta(days=14)
        week_before = race_date - timedelta(days=7)
        plan_dict = {
            "peak_week": {
                "week_start": (race_date - timedelta(days=21)).isoformat(),
                "volume_reduction": "0%",
                "weekly_hours": round(hours, 1),
                "focus": "Peak training",
            },
            "taper_week_1": {
                "week_start": taper_start.isoformat(),
                "volume_reduction": "30%",
                "weekly_hours": round(hours * 0.7, 1),
                "focus": "Reduce volume 30%, keep intensity",
            },
            "taper_week_2": {
                "week_start": week_before.isoformat(),
                "volume_reduction": "50%",
                "weekly_hours": round(hours * 0.5, 1),
                "focus": "Easy runs, rest 2–3 days before race",
            },
        }
        return {
            "tapering_plan": plan_dict,
            "current_weekly_hours": round(hours, 1),
            "days_until_race": days,
            "race_date": race_date.isoformat(),
            "race_distance_km": race_distance_km,
        }
