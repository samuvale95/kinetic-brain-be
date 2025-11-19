from __future__ import annotations

import re
from datetime import date as _date
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models.daily_metrics import DailyReadinessMetrics
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

    def get_diary_entries(
        self,
        *,
        user_id: int,
        start_date: _date,
        end_date: _date,
    ) -> List[DailyReadinessMetrics]:
        """Recupera i record del diario per un range di date."""
        records = self.db.execute(
            select(DailyReadinessMetrics)
            .where(
                and_(
                    DailyReadinessMetrics.user_id == user_id,
                    DailyReadinessMetrics.metric_date >= start_date,
                    DailyReadinessMetrics.metric_date <= end_date,
                )
            )
            .order_by(DailyReadinessMetrics.metric_date.asc())
        ).scalars().all()
        return list(records)

    def get_all_diary_entries(
        self,
        *,
        user_id: int,
    ) -> List[DailyReadinessMetrics]:
        """
        Recupera TUTTI i record del diario compilati (solo giorni con dati inseriti).
        Un record è considerato "completato" se ha almeno uno dei seguenti campi compilati:
        - hrv_value, rhr_value, sleep_hours, sleep_quality_score, epoc
        - hydration_status, hydration_score, nutrition_score, weight_delta_kg
        - notes
        """
        records = self.db.execute(
            select(DailyReadinessMetrics)
            .where(
                and_(
                    DailyReadinessMetrics.user_id == user_id,
                    # Filtra solo record con almeno un dato inserito
                    or_(
                        DailyReadinessMetrics.hrv_value.isnot(None),
                        DailyReadinessMetrics.rhr_value.isnot(None),
                        DailyReadinessMetrics.sleep_hours.isnot(None),
                        DailyReadinessMetrics.sleep_quality_score.isnot(None),
                        DailyReadinessMetrics.epoc.isnot(None),
                        DailyReadinessMetrics.hydration_status.isnot(None),
                        DailyReadinessMetrics.hydration_score.isnot(None),
                        DailyReadinessMetrics.nutrition_score.isnot(None),
                        DailyReadinessMetrics.weight_delta_kg.isnot(None),
                        DailyReadinessMetrics.notes.isnot(None),
                    )
                )
            )
            .order_by(DailyReadinessMetrics.metric_date.desc())  # Più recenti prima
        ).scalars().all()
        return list(records)

    def get_diary_entry(
        self,
        *,
        user_id: int,
        metric_date: _date,
    ) -> Optional[DailyReadinessMetrics]:
        """Recupera un singolo record del diario per una data specifica."""
        return self.db.execute(
            select(DailyReadinessMetrics)
            .where(
                and_(
                    DailyReadinessMetrics.user_id == user_id,
                    DailyReadinessMetrics.metric_date == metric_date,
                )
            )
        ).scalar_one_or_none()

    @staticmethod
    def extract_perceived_exertion(notes: Optional[str]) -> Optional[int]:
        """Estrae il perceived_exertion dalle note se presente come 'RPE: X'."""
        if not notes:
            return None
        # Cerca pattern "RPE: X" nelle note
        match = re.search(r"RPE:\s*(\d+)", notes, re.IGNORECASE)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                return None
        return None

    @staticmethod
    def format_day_name(metric_date: _date) -> str:
        """
        Formatta il nome del giorno per il diario.
        Esempio: "Lunedì 16 Novembre 2025"
        """
        # Nomi dei giorni in italiano
        weekdays_it = [
            "Lunedì", "Martedì", "Mercoledì", "Giovedì",
            "Venerdì", "Sabato", "Domenica"
        ]
        
        # Nomi dei mesi in italiano
        months_it = [
            "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
            "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"
        ]
        
        weekday_name = weekdays_it[metric_date.weekday()]
        month_name = months_it[metric_date.month - 1]
        
        return f"{weekday_name} {metric_date.day} {month_name} {metric_date.year}"


