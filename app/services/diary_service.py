from __future__ import annotations

from datetime import date as _date
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.services.advanced_metrics_service import AdvancedMetricsService


class DiaryService:
    """Servizio per creare/aggiornare voci di diario (readiness) giornaliere."""

    def __init__(self, db: Session):
        self.db = db
        self.advanced_service = AdvancedMetricsService(db)

    def upsert_readiness_entry(
        self,
        *,
        user_id: int,
        metric_date: _date,
        inputs: Optional[Dict[str, Any]] = None,
        notes: Optional[str] = None,
        perceived_exertion: Optional[int] = None,
    ):
        inputs = inputs or {}
        # Delego il calcolo e la persistenza alla AdvancedMetricsService
        record = self.advanced_service.compute_and_store_daily_readiness(
            user_id=user_id,
            metric_date=metric_date,
            inputs=inputs,
        )
        # Aggiorno eventuali note aggiuntive
        if notes is not None or perceived_exertion is not None:
            # Accodo RPE nelle note se fornito
            appended = []
            if record.notes:
                appended.append(record.notes)
            if perceived_exertion is not None:
                appended.append(f"RPE: {perceived_exertion}")
            if notes:
                appended.append(notes)
            record.notes = " | ".join(appended) if appended else None
            self.db.add(record)
            self.db.commit()
            self.db.refresh(record)
        return record


