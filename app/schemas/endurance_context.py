"""
Endurance-specific context schemas for Smart Context Building.
These schemas define the 3-layer information pyramid for efficient LLM prompting.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Literal
from datetime import date, datetime


# ============================================================================
# LAYER 1: CRITICAL Context (~500 tokens)
# Always included in every prompt
# ============================================================================

class CurrentFitnessState(BaseModel):
    """Current physiological metrics calculated from recent training."""
    ctl: float = Field(..., description="Chronic Training Load (42-day rolling avg)")
    atl: float = Field(..., description="Acute Training Load (7-day rolling avg)")
    tsb: float = Field(..., description="Training Stress Balance (CTL - ATL)")
    ramp_rate: float = Field(..., description="ATL/CTL ratio. >1.5 = high injury risk")
    hr_drift: Optional[float] = Field(None, description="HR drift % on last long run (>5% = aerobic deficit)")


class LastWorkoutSnapshot(BaseModel):
    """Most recent workout - critical for immediate context."""
    date: date
    sport: Literal["run", "bike", "swim"]
    type: str  # "intervals", "tempo", "long", "recovery"
    completion_rate: float = Field(..., ge=0.0, le=1.0, description="0.0-1.0, did they finish?")
    failure_point: Optional[str] = Field(None, description="e.g. 'Rep 5 of 8'")
    athlete_note: Optional[str] = None
    rpe: int = Field(..., ge=1, le=10)
    tss: float


class CriticalContext(BaseModel):
    """Layer 1: Must-have info for every generation."""
    current_fitness: CurrentFitnessState
    last_workout: LastWorkoutSnapshot
    current_phase: str = Field(..., description="e.g. 'Build Week 3', 'Taper Week 1'")
    weeks_to_race: Optional[int] = None
    injury_flags: List[str] = Field(default_factory=list, description="e.g. ['knee_right_minor']")
    skip_count_last_2weeks: int = Field(default=0, description="How many workouts skipped recently")


# ============================================================================
# LAYER 2: RELEVANT Context (~1000 tokens)
# Retrieved based on next workout type
# ============================================================================

class SimilarWorkoutSummary(BaseModel):
    """Summary of a past workout similar to the one being planned."""
    date: date
    sport: str
    workout_description: str = Field(..., description="e.g. '6x1000m @ 4:00/km'")
    completion_rate: float
    avg_hr: Optional[int] = None
    avg_pace: Optional[str] = None  # "4:15/km"
    avg_power: Optional[int] = None  # watts
    time_in_zone_target: int = Field(..., description="Seconds spent in target zone")
    rpe: int
    athlete_feedback: Optional[str] = None


class AerobicBaseReference(BaseModel):
    """Most recent long/easy session for aerobic capacity context."""
    last_long_session: SimilarWorkoutSummary
    avg_weekly_zone2_minutes: int = Field(..., description="Avg Z2 time over last 4 weeks")
    decoupling: Optional[float] = Field(None, description="HR/Pace decoupling % on long runs")


class RelevantContext(BaseModel):
    """Layer 2: Context tailored to the specific workout being generated."""
    similar_workouts: List[SimilarWorkoutSummary] = Field(
        default_factory=list,
        description="Last 3 workouts of the same type (e.g. last 3 VO2Max sessions)"
    )
    aerobic_base: AerobicBaseReference
    failure_pattern: Optional[str] = Field(
        None,
        description="e.g. 'Last 2 high-intensity incomplete due to pace degradation'"
    )
    progression_context: str = Field(
        ...,
        description="e.g. 'Long run progressed from 15km to 18km to 20km over 3 weeks'"
    )


# ============================================================================
# LAYER 3: BACKGROUND Context (~300 tokens)
# Pre-computed summaries, cached weekly
# ============================================================================

class MonthlyTrainingSummary(BaseModel):
    """Aggregate metrics over the last 30 days."""
    total_volume_km: float
    total_tss: float
    avg_sessions_per_week: float
    high_intensity_ratio: float = Field(..., description="% of time in Z4+")
    progress_trend: Literal["improving", "plateau", "declining"]
    compliance_rate: float = Field(..., description="% of planned workouts completed")


class AthleteProfileSummary(BaseModel):
    """Long-term athlete characteristics."""
    strengths: List[str] = Field(
        default_factory=list,
        description="e.g. ['aerobic_base', 'consistency']"
    )
    weaknesses: List[str] = Field(
        default_factory=list,
        description="e.g. ['vo2max', 'recovery', 'hill_climbing']"
    )
    injury_history: List[str] = Field(
        default_factory=list,
        description="e.g. ['knee_2023_q2', 'achilles_2022']"
    )
    preferred_training_times: Optional[str] = Field(None, description="e.g. 'morning'")
    equipment_limitations: List[str] = Field(default_factory=list)


class BackgroundContext(BaseModel):
    """Layer 3: Pre-computed context for efficiency."""
    monthly_summary: MonthlyTrainingSummary
    athlete_profile: AthleteProfileSummary
    cached_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# UNIFIED CONTEXT (All 3 layers combined)
# ============================================================================

class SmartEnduranceContext(BaseModel):
    """Complete context package for LLM prompt building."""
    user_id: int
    target_week_start: date
    
    # The 3 layers
    critical: CriticalContext
    relevant: RelevantContext
    background: BackgroundContext
    
    # Metadata
    total_estimated_tokens: int = Field(
        default=1800,
        description="Estimated token count for this context"
    )
