from typing import List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.plan_version import PlanVersion


class PlanVersionService:
    def __init__(self, db: Session):
        self.db = db

    def list_versions(
        self,
        *,
        user_id: int,
        plan_id: Optional[int] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[PlanVersion], int]:
        query = select(PlanVersion).where(PlanVersion.user_id == user_id)
        count_query = select(func.count(PlanVersion.id)).where(PlanVersion.user_id == user_id)

        if plan_id is not None:
            query = query.where(PlanVersion.plan_id == plan_id)
            count_query = count_query.where(PlanVersion.plan_id == plan_id)

        query = query.order_by(PlanVersion.created_at.desc()).limit(limit).offset(offset)

        items = list(self.db.execute(query).scalars().all())
        total = self.db.execute(count_query).scalar() or 0

        return items, total

    def get_version(self, *, user_id: int, version_id: int) -> Optional[PlanVersion]:
        query = select(PlanVersion).where(
            PlanVersion.id == version_id,
            PlanVersion.user_id == user_id,
        )
        return self.db.execute(query).scalar_one_or_none()

