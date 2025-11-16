from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database import get_db
from app.schemas.metrics import (
    GroupingGranularity,
    LoadMetricsResponse,
    ReadinessMetricsResponse,
    DiaryEntryRequest,
    DiaryEntryResponse,
)
from app.services.metrics_api_service import MetricsApiService
from app.services.metrics_orchestrator import enqueue_daily_performance_job
from app.tasks.strava_tasks import run_metrics_jobs_once
from app.models.daily_metrics import DailyPerformanceMetrics
from sqlalchemy import select, and_

router = APIRouter(prefix="/metrics", tags=["metrics"])


def _default_start_date() -> date:
    return date.today() - timedelta(days=27)


def _default_end_date() -> date:
    return date.today()


@router.get("/load", response_model=LoadMetricsResponse)
def get_load_metrics(
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    start_date: date = Query(default_factory=_default_start_date),
    end_date: date = Query(default_factory=_default_end_date),
    grouping: GroupingGranularity = Query(GroupingGranularity.week),
    sport: Optional[str] = Query(None, description="Filter by sport (e.g. run, cycling, swim). 'all' to include everything."),
) -> LoadMetricsResponse:
    # Lazy compute guard: se manca il record di oggi, enqueua job non bloccante
    today = date.today()
    has_today = db.execute(
        select(DailyPerformanceMetrics).where(
            and_(
                DailyPerformanceMetrics.user_id == current_user["user_id"],
                DailyPerformanceMetrics.metric_date == today,
            )
        )
    ).scalar_one_or_none()
    if not has_today:
        enqueue_daily_performance_job(db, user_id=current_user["user_id"], metric_date=today)
        background_tasks.add_task(run_metrics_jobs_once, 1)

    service = MetricsApiService(db)
    if start_date > end_date:
        raise ValueError("start_date must be before end_date")

    series = service.get_load_series(
        user_id=current_user["user_id"],
        start_date=start_date,
        end_date=end_date,
        grouping=grouping,
        sport=sport if sport and sport != "all" else None,
    )

    return LoadMetricsResponse(
        metadata={
            "grouping": grouping,
            "start_date": start_date,
            "end_date": end_date,
            "sport": sport or "all",
        },
        series=series,
    )


@router.get("/readiness", response_model=ReadinessMetricsResponse)
def get_readiness_metrics(
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    start_date: date = Query(default_factory=_default_start_date),
    end_date: date = Query(default_factory=_default_end_date),
    grouping: GroupingGranularity = Query(GroupingGranularity.day),
) -> ReadinessMetricsResponse:
    # Lazy compute guard: assicura il calcolo giornaliero non bloccante
    today = date.today()
    has_today = db.execute(
        select(DailyPerformanceMetrics).where(
            and_(
                DailyPerformanceMetrics.user_id == current_user["user_id"],
                DailyPerformanceMetrics.metric_date == today,
            )
        )
    ).scalar_one_or_none()
    if not has_today:
        enqueue_daily_performance_job(db, user_id=current_user["user_id"], metric_date=today)
        background_tasks.add_task(run_metrics_jobs_once, 1)

    service = MetricsApiService(db)
    if start_date > end_date:
        raise ValueError("start_date must be before end_date")

    series = service.get_readiness_series(
        user_id=current_user["user_id"],
        start_date=start_date,
        end_date=end_date,
        grouping=grouping,
    )

    return ReadinessMetricsResponse(
        metadata={
            "grouping": grouping,
            "start_date": start_date,
            "end_date": end_date,
        },
        series=series,
    )


@router.post("/diary", response_model=DiaryEntryResponse)
def post_diary_entry(
    payload: DiaryEntryRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DiaryEntryResponse:
    """Inserisce/aggiorna una voce di diario per la giornata e calcola readiness."""
    from datetime import date as _date
    from app.services.diary_service import DiaryService

    metric_date = payload.date or _date.today()
    inputs = {
        "hrv_value": payload.hrv_value,
        "rhr_value": payload.rhr_value,
        "sleep_hours": payload.sleep_hours,
        "sleep_quality_score": payload.sleep_quality_score,
        "epoc": payload.epoc,
        "hydration_status": payload.hydration_status,
        "hydration_score": payload.hydration_score,
        "nutrition_score": payload.nutrition_score,
        "weight_delta_kg": payload.weight_delta_kg,
    }
    # Pulisci None
    inputs = {k: v for k, v in inputs.items() if v is not None}

    service = DiaryService(db)
    rec = service.upsert_readiness_entry(
        user_id=current_user["user_id"],
        metric_date=metric_date,
        inputs=inputs,
        notes=payload.notes,
        perceived_exertion=payload.perceived_exertion,
    )
    return DiaryEntryResponse(
        success=True,
        date=metric_date,
        readiness_state=rec.readiness_state,
        recovery_index=rec.recovery_index,
    )


@router.post("/recompute-today")
def recompute_today(
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    target_date: Optional[date] = Query(default=None, description="Data da ricalcolare; default oggi"),
):
    """Enqueue non bloccante del calcolo giornaliero (CTL/ATL/TSB) per oggi o per la data indicata."""
    metric_date = target_date or date.today()
    job = enqueue_daily_performance_job(db, user_id=current_user["user_id"], metric_date=metric_date)
    background_tasks.add_task(run_metrics_jobs_once, 1)
    return {
        "success": True,
        "job_id": job.id,
        "job_type": job.job_type,
        "status": job.status,
        "metric_date": metric_date.isoformat(),
    }

