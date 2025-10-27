from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class ZoneDistribution(BaseModel):
    """Schema for zone distribution"""
    
    minutes: float
    percentage: float
    description: str


class OverviewResponse(BaseModel):
    """Response for /statistics/overview"""
    
    total_workouts: int
    total_training_hours: float
    current_ctl: Optional[float] = None
    current_atl: Optional[float] = None
    current_tsb: Optional[float] = None
    tsb_status: str = Field(default="optimal", pattern="^(optimal|fatigued|fresh)$")
    weekly_tss: float = 0
    current_week_volume_hours: float = 0
    zone_distribution_current_week: Optional[Dict[str, float]] = None
    completion_rate_current_week: Optional[float] = None


class WeeklyDataPoint(BaseModel):
    """Single week data point for performance chart"""
    
    week_start: str
    week_end: str
    ctl: Optional[float] = None
    atl: Optional[float] = None
    tsb: Optional[float] = None
    weekly_tss: float = 0
    volume_hours: float = 0
    workouts_completed: int = 0
    avg_rpe: Optional[float] = None


class PerformanceChartResponse(BaseModel):
    """Response for /statistics/performance-chart"""
    
    weeks: List[WeeklyDataPoint]
    trend_analysis: Dict[str, Any] = Field(default_factory=dict)


class WorkoutSummary(BaseModel):
    """Single workout summary for weekly summary"""
    
    id: int
    date: str
    title: str
    type: str
    duration_minutes: int
    distance_km: Optional[float] = None
    tss: Optional[float] = None
    if_: Optional[float] = Field(None, alias="if")
    trimp: Optional[float] = None
    avg_hr: Optional[float] = None
    time_in_zones: Optional[Dict[str, int]] = None
    normalized_power: Optional[float] = None
    status: str


class WeeklySummaryResponse(BaseModel):
    """Response for /statistics/weekly-summary"""
    
    week_start: str
    week_end: str
    total_tss: float = 0
    total_volume_hours: float = 0
    avg_rpe: Optional[float] = None
    completion_rate: Optional[float] = None
    ctl: Optional[float] = None
    atl: Optional[float] = None
    tsb: Optional[float] = None
    workouts: List[WorkoutSummary] = Field(default_factory=list)
    zone_distribution: Optional[Dict[str, float]] = None


class ZoneDistributionResponse(BaseModel):
    """Response for /statistics/zone-distribution"""
    
    period: str
    start_date: str
    end_date: str
    sport_type: Optional[str] = None
    total_time_minutes: float
    zone_distribution: Dict[str, ZoneDistribution]
    zone_balance_assessment: str
    recommendations: List[str] = Field(default_factory=list)


class ProgressionDataPoint(BaseModel):
    """Single data point for progression chart"""
    
    week_start: str
    value: float
    change_pct: float


class ProgressionResponse(BaseModel):
    """Response for /statistics/progression"""
    
    metric: str
    weeks: int
    data_points: List[ProgressionDataPoint]
    overall_trend: str
    total_change_pct: float
    average_weekly_change: float
    best_week: Optional[Dict[str, Any]] = None


class TrainingLoadResponse(BaseModel):
    """Response for /statistics/training-load"""
    
    current_ctl: Optional[float] = None
    current_atl: Optional[float] = None
    current_tsb: Optional[float] = None
    tsb_status: str = Field(default="optimal")
    tsb_color: str = Field(default="yellow")
    acute_chronic_ratio: Optional[float] = None
    load_assessment: str
    recommendations: List[str] = Field(default_factory=list)
    weekly_tss_history: List[float] = Field(default_factory=list)
    recommended_next_week_tss: Optional[float] = None
    days_since_rest: Optional[int] = None
    form_trend: str


class RecalculateMetricsResponse(BaseModel):
    """Response for /strava/recalculate-metrics"""
    
    success: bool
    activities_processed: int
    metrics_calculated: Dict[str, int]
    weekly_summaries_created: int
    initial_ctl: Optional[float] = None
    initial_atl: Optional[float] = None
    initial_tsb: Optional[float] = None
    processing_time_seconds: float


class ZonePreferenceRequest(BaseModel):
    """Request for /profile/zone-preference"""
    
    preferred_zone_type: str = Field(..., pattern="^(hr|pace|power)$")


class ZonePreferenceResponse(BaseModel):
    """Response for /profile/zone-preference"""
    
    success: bool
    preferred_zone_type: str
    zones_calculated: bool
    current_zones: Optional[Dict[str, Dict[str, Any]]] = None

