from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import Any, Dict, Optional

from loguru import logger
from sqlalchemy.orm import Session

from app.models.metrics_job import MetricsPendingJob
from app.services.advanced_metrics_service import AdvancedMetricsService


def _normalize_payload(payload: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if payload is None:
        return None
    # Ensure payload is JSON-serializable with stable ordering
    return json.loads(json.dumps(payload, default=str, sort_keys=True))


def enqueue_daily_readiness_job(
    db: Session,
    user_id: int,
    metric_date: date,
    inputs: Optional[Dict[str, Any]] = None,
    priority: int = 0,
) -> MetricsPendingJob:
    service = AdvancedMetricsService(db)
    payload = _normalize_payload(
        {
            "metric_date": metric_date.isoformat(),
            "inputs": inputs or {},
        }
    )
    return service.enqueue_job("daily_readiness", user_id, payload, priority=priority)


def enqueue_weekly_summary_job(
    db: Session,
    user_id: int,
    week_start: date,
    priority: int = 0,
) -> MetricsPendingJob:
    service = AdvancedMetricsService(db)
    payload = _normalize_payload(
        {
            "week_start": week_start.isoformat(),
        }
    )
    return service.enqueue_job("weekly_summary", user_id, payload, priority=priority)


def process_metrics_jobs(db: Session, limit: int = 3) -> None:
    service = AdvancedMetricsService(db)
    jobs = service.fetch_next_jobs(limit=limit)

    for job in jobs:
        job.status = "processing"
        job.attempts = (job.attempts or 0) + 1
        job.updated_at = datetime.utcnow()
        db.add(job)
        db.commit()

        try:
            payload = job.payload or {}
            if job.job_type == "daily_readiness":
                metric_date = date.fromisoformat(payload["metric_date"])
                inputs = payload.get("inputs") or {}
                service.compute_and_store_daily_readiness(job.user_id, metric_date, inputs)
            elif job.job_type == "weekly_summary":
                week_start = date.fromisoformat(payload["week_start"])
                service.compute_and_store_weekly_summary(job.user_id, week_start)
            else:
                raise ValueError(f"Unknown metrics job type '{job.job_type}'")

            job.status = "completed"
            job.last_error = None
        except Exception as exc:
            logger.exception("[ADV_METRICS] Job id={} type={} failed: {}", job.id, job.job_type, exc)
            job.status = "failed"
            job.last_error = str(exc)
            job.available_at = datetime.utcnow() + timedelta(minutes=5)
        finally:
            job.updated_at = datetime.utcnow()
            db.add(job)
            db.commit()

