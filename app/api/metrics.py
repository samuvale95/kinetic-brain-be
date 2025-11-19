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
    DiaryEntryDetailResponse,
    DiaryEntriesResponse,
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


@router.get("/load")
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

    return {
        "metadata": {
            "grouping": grouping,
            "start_date": start_date,
            "end_date": end_date,
            "sport": sport or "all",
        },
        "series": series,
    }


@router.get("/readiness")
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

    return {
        "metadata": {
            "grouping": grouping,
            "start_date": start_date,
            "end_date": end_date,
        },
        "series": series,
    }


@router.post("/diary", response_model=DiaryEntryResponse)
def post_diary_entry(
    payload: DiaryEntryRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DiaryEntryResponse:
    """
    Inserisce/aggiorna una voce di diario per la giornata e calcola readiness.
    IMPORTANTE: Solo il giorno di oggi può essere modificato. I giorni passati sono in sola lettura.
    """
    from datetime import date as _date
    from app.services.diary_service import DiaryService
    from fastapi import HTTPException, status

    # Convert string date to date object if provided
    if payload.date:
        try:
            metric_date = _date.fromisoformat(payload.date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    else:
        metric_date = _date.today()
    
    # Verifica che non si stia cercando di modificare un giorno passato
    today = _date.today()
    if metric_date < today:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cannot modify diary entries for past dates. Only today ({today}) can be edited."
        )
    
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


@router.get("/diary", response_model=DiaryEntriesResponse)
def get_diary_entries(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DiaryEntriesResponse:
    """
    Recupera TUTTI i record del diario compilati (solo giorni con dati inseriti).
    I record sono ordinati dal più recente al più vecchio per permettere lo scorrimento come un diario.
    Solo il record di oggi (se presente) è modificabile, gli altri sono in sola lettura.
    """
    from app.services.diary_service import DiaryService
    
    service = DiaryService(db)
    today = date.today()
    
    # Recupera tutti i record del diario (senza filtri di data, solo quelli compilati)
    records = service.get_all_diary_entries(user_id=current_user["user_id"])
    
    # Converti i record in response models, estraendo perceived_exertion dalle note
    # e aggiungendo il nome del giorno e il flag di editabilità
    entries = []
    for record in records:
        is_today = record.metric_date == today
        perceived_exertion = DiaryService.extract_perceived_exertion(record.notes)
        day_name = DiaryService.format_day_name(record.metric_date)
        
        entry_dict = {
            "date": record.metric_date,
            "day_name": day_name,
            "is_editable": is_today,
            "hrv_value": record.hrv_value,
            "hrv_baseline": record.hrv_baseline,
            "hrv_delta": record.hrv_delta,
            "rhr_value": record.rhr_value,
            "rhr_baseline": record.rhr_baseline,
            "rhr_delta": record.rhr_delta,
            "sleep_hours": record.sleep_hours,
            "sleep_quality_score": record.sleep_quality_score,
            "epoc": record.epoc,
            "hydration_status": record.hydration_status,
            "hydration_score": record.hydration_score,
            "nutrition_score": record.nutrition_score,
            "weight_delta_kg": record.weight_delta_kg,
            "perceived_exertion": perceived_exertion,
            "notes": record.notes,
            "recovery_index": record.recovery_index,
            "readiness_state": record.readiness_state,
        }
        entries.append(DiaryEntryDetailResponse(**entry_dict))
    
    return DiaryEntriesResponse(
        entries=entries,
        total_entries=len(entries),
    )


@router.get("/diary/{target_date}", response_model=DiaryEntryDetailResponse)
def get_diary_entry(
    target_date: date,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DiaryEntryDetailResponse:
    """Recupera un singolo record del diario per una data specifica."""
    from app.services.diary_service import DiaryService
    
    service = DiaryService(db)
    record = service.get_diary_entry(
        user_id=current_user["user_id"],
        metric_date=target_date,
    )
    
    if not record:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"No diary entry found for date {target_date}")
    
    today = date.today()
    is_today = record.metric_date == today
    perceived_exertion = DiaryService.extract_perceived_exertion(record.notes)
    day_name = DiaryService.format_day_name(record.metric_date)
    
    entry_dict = {
        "date": record.metric_date,
        "day_name": day_name,
        "is_editable": is_today,
        "hrv_value": record.hrv_value,
        "hrv_baseline": record.hrv_baseline,
        "hrv_delta": record.hrv_delta,
        "rhr_value": record.rhr_value,
        "rhr_baseline": record.rhr_baseline,
        "rhr_delta": record.rhr_delta,
        "sleep_hours": record.sleep_hours,
        "sleep_quality_score": record.sleep_quality_score,
        "epoc": record.epoc,
        "hydration_status": record.hydration_status,
        "hydration_score": record.hydration_score,
        "nutrition_score": record.nutrition_score,
        "weight_delta_kg": record.weight_delta_kg,
        "perceived_exertion": perceived_exertion,
        "notes": record.notes,
        "recovery_index": record.recovery_index,
        "readiness_state": record.readiness_state,
    }
    
    return DiaryEntryDetailResponse(**entry_dict)


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

