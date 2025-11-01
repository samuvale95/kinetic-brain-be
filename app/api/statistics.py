from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date, datetime, timedelta
from app.database import get_db
from app.api.auth import get_current_user
from app.services.statistics_service import StatisticsService
from app.schemas.statistics import (
    OverviewResponse, PerformanceChartResponse,
    ZoneDistributionResponse
)
from app.services.daily_metrics_service import DailyMetricsService

router = APIRouter(prefix="/statistics", tags=["statistics"])


@router.options("/overview")
async def options_overview():
    """Handle OPTIONS request for CORS preflight"""
    return Response(status_code=200)


@router.options("/performance-chart")
async def options_performance_chart():
    """Handle OPTIONS request for CORS preflight"""
    return Response(status_code=200)


@router.options("/daily-metrics")
async def options_daily_metrics():
    """Handle OPTIONS request for CORS preflight"""
    return Response(status_code=200)


@router.options("/zone-distribution")
async def options_zone_distribution():
    """Handle OPTIONS request for CORS preflight"""
    return Response(status_code=200)


@router.options("/training-load")
async def options_training_load():
    """Handle OPTIONS request for CORS preflight"""
    return Response(status_code=200)


@router.get("/overview", response_model=OverviewResponse)
async def get_overview(current_user: dict = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    """Get overview statistics for dashboard"""
    statistics_service = StatisticsService(db)
    overview = statistics_service.get_overview(current_user["user_id"])
    return overview


@router.get("/performance-chart", response_model=PerformanceChartResponse)
async def get_performance_chart(weeks: int = Query(12, ge=1, le=52),
                               current_user: dict = Depends(get_current_user),
                               db: Session = Depends(get_db)):
    """Get performance chart data (CTL/ATL/TSB trends)"""
    statistics_service = StatisticsService(db)
    chart_data = statistics_service.get_performance_chart_data(
        current_user["user_id"],
        weeks=weeks
    )
    return chart_data


@router.get("/daily-metrics")
async def get_daily_metrics(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD), default: 84 days ago"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD), default: today"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get daily performance metrics (CTL/ATL/TSB) for a date range"""
    daily_metrics_service = DailyMetricsService(db)
    user_id = current_user["user_id"]
    
    # Parse dates or use defaults
    today = date.today()
    if end_date:
        try:
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid end_date format. Use YYYY-MM-DD"
            )
    else:
        end = today
    
    if start_date:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid start_date format. Use YYYY-MM-DD"
            )
    else:
        # Default: 84 days ago (12 weeks)
        start = today - timedelta(days=84)
    
    if start > end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be before or equal to end_date"
        )
    
    metrics = daily_metrics_service.get_daily_metrics(user_id, start, end)
    
    return {
        'start_date': start.isoformat(),
        'end_date': end.isoformat(),
        'metrics': [
            {
                'date': m.metric_date.isoformat(),
                'daily_tss': m.daily_tss,
                'ctl': m.ctl,
                'atl': m.atl,
                'tsb': m.tsb,
                'activities_count': m.activities_count
            }
            for m in metrics
        ]
    }


@router.get("/zone-distribution", response_model=ZoneDistributionResponse)
async def get_zone_distribution(period: str = Query(..., pattern="^(week|month|year)$"),
                               sport_type: Optional[str] = Query(None),
                               current_user: dict = Depends(get_current_user),
                               db: Session = Depends(get_db)):
    """Get zone distribution for a period"""
    statistics_service = StatisticsService(db)
    distribution = statistics_service.get_zone_distribution(
        current_user["user_id"],
        period=period,
        sport_type=sport_type
    )
    return distribution


@router.get("/training-load")
async def get_training_load(current_user: dict = Depends(get_current_user),
                           db: Session = Depends(get_db)):
    """Get current training load status and recommendations"""
    statistics_service = StatisticsService(db)
    
    # Get overview for current metrics
    overview = statistics_service.get_overview(current_user["user_id"])
    
    ctl = overview.get('current_ctl')
    atl = overview.get('current_atl')
    tsb = overview.get('current_tsb')
    tsb_status = overview.get('tsb_status', 'optimal')
    
    # Calculate acute/chronic ratio
    # ATL = Acute (fatigue), CTL = Chronic (fitness)
    # Ratio > 1.3 = high injury risk, < 0.8 = can increase load
    acute_chronic_ratio = None
    if ctl is not None and atl is not None and ctl > 0:
        # Calculate ratio even if ATL is 0 (e.g., after rest periods)
        acute_chronic_ratio = round(atl / ctl, 2) if atl is not None else 0.0
    
    # Get TS B color
    tsb_color = "yellow"
    if tsb is not None:
        if tsb > 10:
            tsb_color = "green"
        elif tsb < -10:
            tsb_color = "red"
    
    # Load assessment
    load_assessment = "Optimal training load"
    if acute_chronic_ratio and acute_chronic_ratio > 1.3:
        load_assessment = "High risk of overreaching - reduce load immediately"
    elif acute_chronic_ratio and acute_chronic_ratio > 1.15:
        load_assessment = "Slightly overreaching - monitor recovery"
    elif acute_chronic_ratio and acute_chronic_ratio < 0.8:
        load_assessment = "Low training load - can increase volume"
    
    # Get recommendations
    recommendations = []
    if tsb is not None:
        if tsb < -15:
            recommendations.append("Take 2-3 days completely off")
        elif tsb < -10:
            recommendations.append("Consider a recovery week in the next 7 days")
            recommendations.append("Keep intensity low for next 2-3 workouts")
        elif tsb > 15:
            recommendations.append("Good opportunity for high-intensity training")
    
    if acute_chronic_ratio and acute_chronic_ratio > 1.3:
        recommendations.append("Immediately reduce training volume by 40-50%")
    
    recommendations.append("Ensure 8+ hours of sleep nightly")
    
    # Get last 4 weeks TSS
    chart_data = statistics_service.get_performance_chart_data(current_user["user_id"], weeks=4)
    weekly_tss_history = [w.get('weekly_tss', 0) for w in chart_data.get('weeks', [])]
    
    # Recommended next week TSS
    recommended_next_week_tss = None
    if weekly_tss_history and tsb is not None and len(weekly_tss_history) > 0:
        if tsb < -10:
            # Reduce by 30%
            recommended_next_week_tss = round(max(weekly_tss_history) * 0.7, 0)
        elif tsb > 10:
            # Can increase by 10%
            recommended_next_week_tss = round(max(weekly_tss_history) * 1.1, 0)
        else:
            recommended_next_week_tss = round(sum(weekly_tss_history) / len(weekly_tss_history), 0)
    
    # Form trend
    form_trend = "stable"
    if len(chart_data.get('weeks', [])) >= 2:
        tsb_values = [w.get('tsb') for w in chart_data['weeks'] if w.get('tsb') is not None]
        if len(tsb_values) >= 2:
            if tsb_values[-1] > tsb_values[0] + 3:
                form_trend = "improving"
            elif tsb_values[-1] < tsb_values[0] - 3:
                form_trend = "declining"
    
    return {
        'current_ctl': ctl,
        'current_atl': atl,
        'current_tsb': tsb,
        'tsb_status': tsb_status,
        'tsb_color': tsb_color,
        'acute_chronic_ratio': acute_chronic_ratio,
        'load_assessment': load_assessment,
        'recommendations': recommendations,
        'weekly_tss_history': [round(tss, 0) for tss in weekly_tss_history[-4:]],
        'recommended_next_week_tss': recommended_next_week_tss,
        'days_since_rest': None,  # Would need to track this separately
        'form_trend': form_trend
    }

