"""
Statistics Service
Provides aggregated statistics and analytics for training data
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, func
from app.models.strava import StravaActivity
from app.models.workout import Workout, WorkoutSession
from app.models.daily_metrics import DailyPerformanceMetrics
from app.models.user import User
from app.services.metrics_calculation_service import MetricsCalculationService
from app.services.daily_metrics_service import DailyMetricsService


class StatisticsService:
    """Service for calculating and aggregating training statistics"""
    
    def __init__(self, db: Session):
        self.db = db
        self.metrics_service = MetricsCalculationService()
        self.daily_metrics_service = DailyMetricsService(db)
    
    def get_overview(self, user_id: int) -> Dict[str, Any]:
        """
        Get overview statistics for dashboard
        
        Returns total workouts, volume, current CTL/ATL/TSB, weekly TSS, zone distribution
        """
        # Get Strava account IDs for user
        strava_account_ids = self._get_strava_account_ids(user_id)
        
        # Total workouts
        total_workouts = 0
        if strava_account_ids:
            total_workouts = self.db.execute(
                select(func.count(StravaActivity.id))
                .where(StravaActivity.strava_account_id.in_(strava_account_ids))
            ).scalar() or 0
        
        # Total training hours
        total_training_hours = 0
        if strava_account_ids:
            total_training_hours = self.db.execute(
                select(func.sum(StravaActivity.moving_time))
                .where(StravaActivity.strava_account_id.in_(strava_account_ids))
            ).scalar() or 0
        total_training_hours = (total_training_hours or 0) / 3600  # Convert to hours
        
        # Get today's daily metrics (or calculate if missing)
        today = date.today()
        today_metrics = self.daily_metrics_service.get_current_metrics(user_id)
        
        # If no metrics for today, update them
        if not today_metrics:
            self.daily_metrics_service.update_daily_metrics(user_id, today)
            today_metrics = self.daily_metrics_service.get_current_metrics(user_id)
        
        # Get current week start for weekly TSS calculation
        week_start = today - timedelta(days=today.weekday())
        
        # Current metrics - use today's daily metrics
        if today_metrics:
            current_ctl = today_metrics.ctl
            current_atl = today_metrics.atl
            current_tsb = today_metrics.tsb
        else:
            # Fallback: calculate from activities if no daily metrics
            end_date = date.today()
            start_date = end_date - timedelta(days=41)

            activities = self.db.execute(
                select(StravaActivity)
                .where(and_(
                    StravaActivity.strava_account_id.in_(strava_account_ids),
                    StravaActivity.start_date >= start_date,
                    StravaActivity.tss.isnot(None)
                ))
                .order_by(StravaActivity.start_date)
            ).scalars().all()

            daily_tss = {}
            for activity in activities:
                activity_date = activity.start_date.date()
                daily_tss[activity_date] = daily_tss.get(activity_date, 0) + (activity.tss or 0)

            tss_list = []
            for i in range(42):
                day_date = end_date - timedelta(days=i)
                tss_for_day = daily_tss.get(day_date, 0)
                tss_list.append(tss_for_day)

            metrics = self.metrics_service.calculate_ctl_atl_tsb(tss_list)
            current_ctl = metrics.get('ctl')
            current_atl = metrics.get('atl')
            current_tsb = metrics.get('tsb')
        
        # TSB status
        tsb_status = "optimal"
        if current_tsb is not None:
            if current_tsb > 10:
                tsb_status = "fresh"
            elif current_tsb < -10:
                tsb_status = "fatigued"
        
        # Weekly TSS - calculate from activities this week
        week_end = min(week_start + timedelta(days=6), today)
        activities_week = self.db.execute(
            select(StravaActivity)
            .where(and_(
                StravaActivity.strava_account_id.in_(strava_account_ids),
                func.date(StravaActivity.start_date) >= week_start,
                func.date(StravaActivity.start_date) <= week_end,
                StravaActivity.tss.isnot(None)
            ))
        ).scalars().all()
        weekly_tss = sum(a.tss or 0 for a in activities_week)
        
        # Current week volume
        current_week_volume_hours = sum((a.moving_time or 0) for a in activities_week) / 3600.0
        
        # Zone distribution - calculate from this week's activities
        zone_distribution = None
        if activities_week:
            zone_time = {
                'z1': sum(a.time_in_zone_1 or 0 for a in activities_week),
                'z2': sum(a.time_in_zone_2 or 0 for a in activities_week),
                'z3': sum(a.time_in_zone_3 or 0 for a in activities_week),
                'z4': sum(a.time_in_zone_4 or 0 for a in activities_week),
                'z5': sum(a.time_in_zone_5 or 0 for a in activities_week)
            }
            total_zone_time = sum(zone_time.values())
            if total_zone_time > 0:
                zone_distribution = {
                    'z1': round((zone_time['z1'] / total_zone_time) * 100, 1),
                    'z2': round((zone_time['z2'] / total_zone_time) * 100, 1),
                    'z3': round((zone_time['z3'] / total_zone_time) * 100, 1),
                    'z4': round((zone_time['z4'] / total_zone_time) * 100, 1),
                    'z5': round((zone_time['z5'] / total_zone_time) * 100, 1)
                }
        
        # Completion rate - would need workout plans to calculate
        completion_rate = None
        
        return {
            'total_workouts': total_workouts,
            'total_training_hours': round(total_training_hours, 1),
            'current_ctl': current_ctl,
            'current_atl': current_atl,
            'current_tsb': current_tsb,
            'tsb_status': tsb_status,
            'weekly_tss': round(weekly_tss, 2),
            'current_week_volume_hours': round(current_week_volume_hours, 1),
            'zone_distribution_current_week': zone_distribution,
            'completion_rate_current_week': completion_rate
        }
    
    def get_performance_chart_data(self, user_id: int, weeks: int = 12) -> Dict[str, Any]:
        """
        Get performance chart data (CTL/ATL/TSB trends)
        
        Uses daily metrics and aggregates to weekly for backward compatibility
        
        Args:
            user_id: User ID
            weeks: Number of weeks to retrieve (default 12)
        
        Returns:
            Dictionary with weekly data points and trend analysis
            Aggregated from daily metrics
        """
        today = date.today()
        start_date = today - timedelta(weeks=weeks)
        
        # Get daily metrics for the period
        daily_metrics = self.daily_metrics_service.get_daily_metrics(user_id, start_date, today)
        
        # Group daily metrics by week
        weeks_data = []
        weekly_data = {}  # key: week_start_date
        
        for day_metric in daily_metrics:
            week_start = day_metric.metric_date - timedelta(days=day_metric.metric_date.weekday())
            
            if week_start not in weekly_data:
                weekly_data[week_start] = {
                    'week_start': week_start,
                    'week_end': week_start + timedelta(days=6),
                    'days': [],
                    'daily_tss_list': []
                }
            
            weekly_data[week_start]['days'].append(day_metric)
            weekly_data[week_start]['daily_tss_list'].append(day_metric.daily_tss)
        
        # Build weeks list with last day's CTL/ATL/TSB for each week
        for week_start in sorted(weekly_data.keys()):
            week_info = weekly_data[week_start]
            days = week_info['days']
            
            if days:
                # Use last day of week for CTL/ATL/TSB (most representative)
                last_day = days[-1]
                
                weeks_data.append({
                    'week_start': week_info['week_start'].isoformat(),
                    'week_end': week_info['week_end'].isoformat(),
                    'ctl': last_day.ctl,
                    'atl': last_day.atl,
                    'tsb': last_day.tsb,
                    'weekly_tss': sum(d.daily_tss for d in days),
                    'volume_hours': 0,  # Would need to calculate from activities
                    'workouts_completed': sum(d.activities_count for d in days),
                    'avg_rpe': None
                })
        
        # Ensure we have data up to today - add today's metrics if not in last week
        if weeks_data:
            last_week_start = date.fromisoformat(weeks_data[-1]['week_start'])
            if today > last_week_start + timedelta(days=6):
                # Today is in a new week, add it
                today_metric = self.daily_metrics_service.get_current_metrics(user_id)
                if not today_metric:
                    self.daily_metrics_service.update_daily_metrics(user_id, today)
                    today_metric = self.daily_metrics_service.get_current_metrics(user_id)
                
                if today_metric:
                    weeks_data.append({
                        'week_start': (today - timedelta(days=today.weekday())).isoformat(),
                        'week_end': (today - timedelta(days=today.weekday()) + timedelta(days=6)).isoformat(),
                        'ctl': today_metric.ctl,
                        'atl': today_metric.atl,
                        'tsb': today_metric.tsb,
                        'weekly_tss': today_metric.daily_tss,
                        'volume_hours': 0,
                        'workouts_completed': today_metric.activities_count,
                        'avg_rpe': None
                    })
        
        # Trend analysis
        trend_analysis = {}
        if len(weeks_data) >= 2:
            first_ctl = weeks_data[0].get('ctl', 0) or 0
            last_ctl = weeks_data[-1].get('ctl', 0) or 0
            
            if last_ctl > first_ctl + 5:
                trend_analysis['ctl_trend'] = 'increasing'
            elif last_ctl < first_ctl - 5:
                trend_analysis['ctl_trend'] = 'decreasing'
            else:
                trend_analysis['ctl_trend'] = 'stable'
            
            # Fitness change percentage
            if first_ctl > 0:
                fitness_change = ((last_ctl - first_ctl) / first_ctl) * 100
                trend_analysis['fitness_change_pct'] = round(fitness_change, 1)
            else:
                trend_analysis['fitness_change_pct'] = 0
            
            # Recommended next week TSS
            avg_recent_tss = sum(w['weekly_tss'] for w in weeks_data[-4:]) / min(4, len(weeks_data))
            trend_analysis['recommended_next_week_tss'] = round(avg_recent_tss * 1.1, 0)
        
        return {
            'weeks': weeks_data,
            'trend_analysis': trend_analysis
        }
    
    def get_zone_distribution(self, user_id: int, period: str = "month", 
                            sport_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Get zone distribution for a period
        
        Args:
            user_id: User ID
            period: "week", "month", or "year"
            sport_type: Optional sport filter
        
        Returns:
            Zone distribution with minutes and percentages
        """
        today = date.today()
        
        if period == "week":
            start_date = today - timedelta(days=today.weekday())
            end_date = start_date + timedelta(days=6)
        elif period == "month":
            start_date = date(today.year, today.month, 1)
            end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        else:  # year
            start_date = date(today.year, 1, 1)
            end_date = date(today.year, 12, 31)
        
        # Get activities with zones
        strava_account_ids = self._get_strava_account_ids(user_id)
        
        if not strava_account_ids:
            return self._empty_zone_distribution_response(period, start_date, end_date, sport_type)
        
        query = select(StravaActivity).where(
            and_(
                StravaActivity.strava_account_id.in_(strava_account_ids),
                StravaActivity.start_date >= start_date,
                StravaActivity.start_date <= end_date,
                StravaActivity.metrics_calculated == True
            )
        )
        
        if sport_type:
            # Normalize sport_type to lowercase and filter against both 'type' and 'sport_type'
            sport_norm = sport_type.lower()
            from sqlalchemy import or_
            query = query.where(
                or_(func.lower(StravaActivity.type) == sport_norm,
                    func.lower(StravaActivity.sport_type) == sport_norm)
            )
        
        activities = self.db.execute(query).scalars().all()
        
        # Aggregate zone time
        total_z1 = sum(a.time_in_zone_1 or 0 for a in activities)
        total_z2 = sum(a.time_in_zone_2 or 0 for a in activities)
        total_z3 = sum(a.time_in_zone_3 or 0 for a in activities)
        total_z4 = sum(a.time_in_zone_4 or 0 for a in activities)
        total_z5 = sum(a.time_in_zone_5 or 0 for a in activities)
        
        total_minutes = total_z1 + total_z2 + total_z3 + total_z4 + total_z5
        
        zone_dist = {
            'z1': {
                'minutes': total_z1,
                'percentage': (total_z1 / total_minutes * 100) if total_minutes > 0 else 0,
                'description': 'Recovery/Easy'
            },
            'z2': {
                'minutes': total_z2,
                'percentage': (total_z2 / total_minutes * 100) if total_minutes > 0 else 0,
                'description': 'Endurance'
            },
            'z3': {
                'minutes': total_z3,
                'percentage': (total_z3 / total_minutes * 100) if total_minutes > 0 else 0,
                'description': 'Tempo'
            },
            'z4': {
                'minutes': total_z4,
                'percentage': (total_z4 / total_minutes * 100) if total_minutes > 0 else 0,
                'description': 'Threshold'
            },
            'z5': {
                'minutes': total_z5,
                'percentage': (total_z5 / total_minutes * 100) if total_minutes > 0 else 0,
                'description': 'VO2 Max'
            }
        }
        
        # Zone balance assessment
        z1_pct = zone_dist['z1']['percentage']
        z2_pct = zone_dist['z2']['percentage']
        z3_pct = zone_dist['z3']['percentage']
        z4_pct = zone_dist['z4']['percentage']
        z5_pct = zone_dist['z5']['percentage']
        
        if (z1_pct + z2_pct) > 70 and (z4_pct + z5_pct) > 10:
            assessment = "Polarized training - Good balance"
        elif z2_pct > 50:
            assessment = "Pyramidal training - Endurance focused"
        elif (z4_pct + z5_pct) > 20:
            assessment = "Threshold training - High intensity focused"
        else:
            assessment = "Balanced training"
        
        # Recommendations
        recommendations = []
        if z1_pct < 10:
            recommendations.append("Consider adding more Z1 recovery work")
        if z2_pct < 30:
            recommendations.append("Increase endurance base (Z2 training)")
        if (z4_pct + z5_pct) > 25:
            recommendations.append("Reduce high-intensity volume to prevent overreaching")
        
        return {
            'period': period,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'sport_type': sport_type,
            'total_time_minutes': total_minutes,
            'zone_distribution': zone_dist,
            'zone_balance_assessment': assessment,
            'recommendations': recommendations
        }
    
    def _get_strava_account_ids(self, user_id: int) -> List[int]:
        """Helper to get Strava account IDs for user"""
        from app.models.strava import StravaAccount
        
        try:
            accounts = self.db.execute(
                select(StravaAccount.id)
                .where(StravaAccount.user_id == user_id)
            ).scalars().all()
            
            return list(accounts) if accounts else []
        except Exception:
            return []
    
    def _empty_zone_distribution_response(self, period: str, start_date: date, 
                                         end_date: date, sport_type: Optional[str]) -> Dict[str, Any]:
        """Return empty zone distribution response"""
        empty_zone = {
            'minutes': 0,
            'percentage': 0,
            'description': ''
        }
        
        return {
            'period': period,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'sport_type': sport_type,
            'total_time_minutes': 0,
            'zone_distribution': {
                'z1': empty_zone.copy(),
                'z2': empty_zone.copy(),
                'z3': empty_zone.copy(),
                'z4': empty_zone.copy(),
                'z5': empty_zone.copy()
            },
            'zone_balance_assessment': "No training data available",
            'recommendations': []
        }
    
    def _get_week_workouts(self, user_id: int, week_start: date, week_end: date) -> List[Dict[str, Any]]:
        """Get workouts for a specific week"""
        strava_account_ids = self._get_strava_account_ids(user_id)
        
        if not strava_account_ids:
            return []
        
        activities = self.db.execute(
            select(StravaActivity)
            .where(and_(
                StravaActivity.strava_account_id.in_(strava_account_ids),
                StravaActivity.start_date >= week_start,
                StravaActivity.start_date <= week_end
            ))
            .order_by(StravaActivity.start_date)
        ).scalars().all()
        
        workouts = []
        for activity in activities:
            workouts.append({
                'id': activity.id,
                'date': activity.start_date.isoformat(),
                'title': activity.name,
                'type': activity.type,
                'duration_minutes': (activity.moving_time or 0) // 60,
                'distance_km': (activity.distance or 0) / 1000 if activity.distance else None,
                'tss': activity.tss,
                'if': activity.intensity_factor,
                'trimp': activity.trimp,
                'avg_hr': activity.average_heartrate,
                'time_in_zones': {
                    'z1': activity.time_in_zone_1 or 0,
                    'z2': activity.time_in_zone_2 or 0,
                    'z3': activity.time_in_zone_3 or 0,
                    'z4': activity.time_in_zone_4 or 0,
                    'z5': activity.time_in_zone_5 or 0
                },
                'normalized_power': activity.normalized_power,
                'status': 'completed' if activity.is_synced else 'synced'
            })
        
        return workouts

