from sqlalchemy.orm import Session
from sqlalchemy import select, and_, func
from datetime import date, timedelta
from typing import Optional, Dict, Any, List
from app.models.daily_metrics import DailyPerformanceMetrics
from app.models.strava import StravaActivity, StravaAccount
from app.services.metrics_calculation_service import MetricsCalculationService


class DailyMetricsService:
    """Service for managing daily CTL/ATL/TSB metrics"""
    
    def __init__(self, db: Session):
        self.db = db
        self.metrics_service = MetricsCalculationService()
    
    def update_daily_metrics(
        self,
        user_id: int,
        activity_date: date,
        propagate: bool = True
    ) -> DailyPerformanceMetrics:
        """
        Aggiorna i metric giornalieri quando viene aggiunta/modificata un'attività
        
        Questo viene chiamato:
        - Dopo ogni sync Strava
        - Dopo ogni calcolo metriche attività
        - Quando l'utente completa un workout
        """
        # 1. Calcola TSS totale per questo giorno
        strava_account_ids = self._get_strava_account_ids(user_id)
        
        activities = self.db.execute(
            select(StravaActivity)
            .where(
                and_(
                    StravaActivity.strava_account_id.in_(strava_account_ids),
                    func.date(StravaActivity.start_date) == activity_date,
                    StravaActivity.tss.isnot(None)
                )
            )
        ).scalars().all()
        
        daily_tss = sum(a.tss or 0 for a in activities)
        
        # 2. Recupera o calcola valori del giorno precedente
        prev_date = activity_date - timedelta(days=1)
        prev_record = self.db.execute(
            select(DailyPerformanceMetrics)
            .where(
                and_(
                    DailyPerformanceMetrics.user_id == user_id,
                    DailyPerformanceMetrics.metric_date == prev_date
                )
            )
        ).scalar_one_or_none()
        
        prev_ctl = prev_record.ctl if prev_record else None
        prev_atl = prev_record.atl if prev_record else None
        
        # Se non abbiamo valori precedenti, calcola dai 42 giorni precedenti
        if prev_ctl is None or prev_atl is None:
            prev_metrics = self._calculate_from_history(user_id, activity_date)
            prev_ctl = prev_metrics.get('ctl', 0.0)
            prev_atl = prev_metrics.get('atl', 0.0)
        
        # 3. Calcola metriche incrementali
        metrics = self.metrics_service.calculate_daily_metrics_incremental(
            daily_tss=daily_tss,
            prev_ctl=prev_ctl,
            prev_atl=prev_atl
        )
        
        # 4. Salva o aggiorna record giornaliero
        existing = self.db.execute(
            select(DailyPerformanceMetrics)
            .where(
                and_(
                    DailyPerformanceMetrics.user_id == user_id,
                    DailyPerformanceMetrics.metric_date == activity_date
                )
            )
        ).scalar_one_or_none()
        
        if existing:
            existing.daily_tss = daily_tss
            existing.ctl = metrics['ctl']
            existing.atl = metrics['atl']
            existing.tsb = metrics['tsb']
            existing.prev_ctl = metrics['prev_ctl']
            existing.prev_atl = metrics['prev_atl']
            existing.activities_count = len(activities)
            record = existing
        else:
            record = DailyPerformanceMetrics(
                user_id=user_id,
                metric_date=activity_date,
                daily_tss=daily_tss,
                ctl=metrics['ctl'],
                atl=metrics['atl'],
                tsb=metrics['tsb'],
                prev_ctl=metrics['prev_ctl'],
                prev_atl=metrics['prev_atl'],
                activities_count=len(activities)
            )
            self.db.add(record)
        
        self.db.commit()
        self.db.refresh(record)
        
        # 5. Propaga aggiornamento ai giorni successivi fino a oggi (solo se richiesto)
        # Questo assicura che tutti i giorni successivi siano aggiornati
        if propagate:
        self._propagate_metrics_forward(user_id, activity_date, date.today())
        
        return record
    
    def _propagate_metrics_forward(self, user_id: int, start_date: date, end_date: date):
        """Propaga aggiornamenti ai giorni successivi"""
        current_date = start_date + timedelta(days=1)
        
        while current_date <= end_date:
            # Prendi il giorno precedente
            prev_date = current_date - timedelta(days=1)
            prev_record = self.db.execute(
                select(DailyPerformanceMetrics)
                .where(
                    and_(
                        DailyPerformanceMetrics.user_id == user_id,
                        DailyPerformanceMetrics.metric_date == prev_date
                    )
                )
            ).scalar_one_or_none()
            
            if not prev_record:
                break
            
            # Ricalcola questo giorno
            self.update_daily_metrics(user_id, current_date, propagate=False)
            current_date += timedelta(days=1)
    
    def _calculate_from_history(self, user_id: int, target_date: date) -> Dict[str, float]:
        """Calcola CTL/ATL dalla storia se non abbiamo valori precedenti"""
        start_date = target_date - timedelta(days=42)
        
        strava_account_ids = self._get_strava_account_ids(user_id)
        activities = self.db.execute(
            select(StravaActivity)
            .where(
                and_(
                    StravaActivity.strava_account_id.in_(strava_account_ids),
                    StravaActivity.start_date >= start_date,
                    StravaActivity.start_date < target_date,
                    StravaActivity.tss.isnot(None)
                )
            )
            .order_by(StravaActivity.start_date)
        ).scalars().all()
        
        # Group TSS by date
        daily_tss = {}
        for activity in activities:
            activity_date = activity.start_date.date()
            daily_tss[activity_date] = daily_tss.get(activity_date, 0) + (activity.tss or 0)
        
        # Build complete list of ALL days
        tss_list = []
        for i in range(42):
            day_date = target_date - timedelta(days=42-i)
            tss_for_day = daily_tss.get(day_date, 0)
            tss_list.append(tss_for_day)
        
        # Reverse to get most recent first
        tss_list.reverse()
        
        # Calculate final metrics
        return self.metrics_service.calculate_ctl_atl_tsb(tss_list)
    
    def _get_strava_account_ids(self, user_id: int) -> List[int]:
        """Get Strava account IDs for user"""
        return self.db.execute(
            select(StravaAccount.id)
            .where(StravaAccount.user_id == user_id)
        ).scalars().all()
    
    def get_daily_metrics(self, user_id: int, start_date: date, end_date: date) -> List[DailyPerformanceMetrics]:
        """Get daily metrics for date range"""
        return self.db.execute(
            select(DailyPerformanceMetrics)
            .where(
                and_(
                    DailyPerformanceMetrics.user_id == user_id,
                    DailyPerformanceMetrics.metric_date >= start_date,
                    DailyPerformanceMetrics.metric_date <= end_date
                )
            )
            .order_by(DailyPerformanceMetrics.metric_date.asc())
        ).scalars().all()
    
    def get_current_metrics(self, user_id: int) -> Optional[DailyPerformanceMetrics]:
        """Get today's metrics"""
        today = date.today()
        return self.db.execute(
            select(DailyPerformanceMetrics)
            .where(
                and_(
                    DailyPerformanceMetrics.user_id == user_id,
                    DailyPerformanceMetrics.metric_date == today
                )
            )
        ).scalar_one_or_none()

