from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database import get_db
from app.schemas.plan_version import PlanVersionDetail, PlanVersionListResponse
from app.services.plan_version_service import PlanVersionService

router = APIRouter(prefix="/plans/versions", tags=["plan_versions"])


@router.get("/", response_model=PlanVersionListResponse)
def list_plan_versions(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    plan_id: Optional[int] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> PlanVersionListResponse:
    service = PlanVersionService(db)
    items, total = service.list_versions(
        user_id=current_user["user_id"],
        plan_id=plan_id,
        limit=limit,
        offset=offset,
    )
    return PlanVersionListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{version_id}", response_model=PlanVersionDetail)
def get_plan_version(
    version_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PlanVersionDetail:
    service = PlanVersionService(db)
    version = service.get_version(user_id=current_user["user_id"], version_id=version_id)
    if not version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan version not found")
    return version

