from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import Any, Dict, Optional

from loguru import logger
from sqlalchemy.orm import Session

from app.models.metrics_job import MetricsPendingJob
from app.services.advanced_metrics_service import AdvancedMetricsService
from app.services.daily_metrics_service import DailyMetricsService


def _normalize_payload(payload: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Rende il payload JSON confrontabile e stabile per deduplication."""
    if payload is None:
        return None
    # Ensure payload is JSON-serializable with stable ordering
    return json.loads(json.dumps(payload, default=str, sort_keys=True))

def _find_existing_job(
    db: Session,
    *,
    job_type: str,
    user_id: int,
    payload: Optional[Dict[str, Any]],
):
    """Ritorna un job pendente/processing equivalente se esiste (idempotenza)."""
    normalized = _normalize_payload(payload)
    # Confronto semplice sul JSON serializzato
    stmt = (
        db.query(MetricsPendingJob)
        .filter(MetricsPendingJob.job_type == job_type)
        .filter(MetricsPendingJob.user_id == user_id)
        .filter(MetricsPendingJob.status.in_(["pending", "processing"]))
    )
    for candidate in stmt.all():
        if _normalize_payload(candidate.payload) == normalized:
            return candidate
    return None


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


def enqueue_daily_performance_job(
    db: Session,
    user_id: int,
    metric_date: date,
    priority: int = 0,
) -> MetricsPendingJob:
    """Enqueue idempotente del job daily_performance per utente/data."""
    service = AdvancedMetricsService(db)
    payload = _normalize_payload(
        {
            "metric_date": metric_date.isoformat(),
        }
    )
    existing = _find_existing_job(
        db,
        job_type="daily_performance",
        user_id=user_id,
        payload=payload,
    )
    if existing:
        return existing
    return service.enqueue_job("daily_performance", user_id, payload, priority=priority)

def process_metrics_jobs(db: Session, limit: int = 3) -> None:
    service = AdvancedMetricsService(db)
    daily_service = DailyMetricsService(db)
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
            elif job.job_type == "daily_performance":
                metric_date = date.fromisoformat(payload["metric_date"])
                # Calcolo giornaliero CTL/ATL/TSB senza bloccare e con propagazione
                daily_service.update_daily_metrics(
                    user_id=job.user_id,
                    activity_date=metric_date,
                    propagate=True,
                    skip_advanced_metrics=True,
                )
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

