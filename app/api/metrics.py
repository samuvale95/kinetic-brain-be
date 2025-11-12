from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database import get_db
from app.schemas.metrics import (
    GroupingGranularity,
    LoadMetricsResponse,
    ReadinessMetricsResponse,
)
from app.services.metrics_api_service import MetricsApiService

router = APIRouter(prefix="/metrics", tags=["metrics"])


def _default_start_date() -> date:
    return date.today() - timedelta(days=27)


def _default_end_date() -> date:
    return date.today()


@router.get("/load", response_model=LoadMetricsResponse)
def get_load_metrics(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    start_date: date = Query(default_factory=_default_start_date),
    end_date: date = Query(default_factory=_default_end_date),
    grouping: GroupingGranularity = Query(GroupingGranularity.week),
    sport: Optional[str] = Query(None, description="Filter by sport (e.g. run, cycling, swim). 'all' to include everything."),
) -> LoadMetricsResponse:
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
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    start_date: date = Query(default_factory=_default_start_date),
    end_date: date = Query(default_factory=_default_end_date),
    grouping: GroupingGranularity = Query(GroupingGranularity.day),
) -> ReadinessMetricsResponse:
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

