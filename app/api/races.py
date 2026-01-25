from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database import get_db
from app.services.race_service import RaceService
from loguru import logger

router = APIRouter(prefix="/races", tags=["races"])


@router.post("/predict", response_model=dict)
async def predict_race(
    race_date: str = Body(..., description="Race date (YYYY-MM-DD)"),
    race_distance_km: float = Body(..., ge=0.1, description="Distance in km"),
    target_time_minutes: Optional[float] = Body(None, description="Optional target time (min)"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Predict race time and tapering plan."""
    try:
        d = datetime.strptime(race_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date. Use YYYY-MM-DD",
        )
    user_id = current_user["user_id"]
    svc = RaceService(db)
    pred = svc.predict_race_time(user_id, d, race_distance_km, target_time_minutes)
    taper = svc.calculate_tapering_plan(user_id, d, race_distance_km)
    return {"prediction": pred, "tapering": taper}
