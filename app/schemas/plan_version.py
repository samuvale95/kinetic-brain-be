from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class PlanVersionSummary(BaseModel):
    id: int
    created_at: datetime
    duration_weeks: int
    sport_type: Optional[str] = None
    level: Optional[str] = None
    version_label: Optional[str] = None
    description: Optional[str] = None

    class Config:
        from_attributes = True


class PlanVersionDetail(PlanVersionSummary):
    plan_id: Optional[int] = None
    plan_payload: Dict[str, Any]
    validator_violations: Optional[List[str]] = None


class PlanVersionListResponse(BaseModel):
    items: List[PlanVersionSummary]
    total: int
    limit: int
    offset: int

