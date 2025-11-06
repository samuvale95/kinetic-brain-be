from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List


class AIRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=15000)
    context: Optional[Dict[str, Any]] = None
    max_tokens: Optional[int] = Field(None, ge=1, le=4000)
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)


class AIResponse(BaseModel):
    response: str
    usage: Optional[Dict[str, Any]] = None
    model: str
    created_at: str


class WorkoutPlanGenerationRequest(BaseModel):
    sport_type: str = Field(..., min_length=1, max_length=50)
    level: str = Field(..., pattern="^(beginner|intermediate|advanced)$")
    goal: str = Field(..., min_length=1, max_length=200)
    duration_weeks: int = Field(..., ge=1, le=52)
    weekly_hours: Optional[float] = Field(None, gt=0, le=168, description="Ore settimanali disponibili (indicativo)")
    user_profile: Optional[Dict[str, Any]] = None
    preferences: Optional[Dict[str, Any]] = None


class WorkoutAnalysisRequest(BaseModel):
    workout_data: Dict[str, Any]
    performance_metrics: Optional[Dict[str, Any]] = None
    analysis_type: str = Field(..., pattern="^(performance|recovery|progression)$")


class WorkoutAnalysisResponse(BaseModel):
    analysis: str
    recommendations: List[str]
    score: Optional[float] = Field(None, ge=0.0, le=10.0)
    areas_for_improvement: List[str]
    next_steps: List[str]


class SuggestionRequest(BaseModel):
    context: str = Field(..., min_length=1, max_length=1000)
    suggestion_type: str = Field(..., pattern="^(workout|nutrition|recovery|equipment)$")
    user_profile: Optional[Dict[str, Any]] = None


# Progressive Workout Plan Schemas
class ProgressiveWorkoutPlanRequest(BaseModel):
    sport_type: str = Field(..., min_length=1, max_length=50)
    level: str = Field(..., pattern="^(beginner|intermediate|advanced)$")
    goal: str = Field(..., min_length=1, max_length=200)
    target_date: str = Field(..., description="Data obiettivo (es. gara) - formato YYYY-MM-DD")
    start_date: str = Field(..., description="Data inizio allenamento - formato YYYY-MM-DD")
    weekly_hours: Optional[float] = Field(None, gt=0, le=168, description="Ore settimanali disponibili (indicativo)")
    user_profile: Optional[Dict[str, Any]] = None
    preferences: Optional[Dict[str, Any]] = None


class WeeklyPlanRequest(BaseModel):
    week_number: int = Field(..., ge=1, le=52)
    target_date: str = Field(..., description="Data obiettivo finale - formato YYYY-MM-DD")
    previous_week_data: Optional[Dict[str, Any]] = None
    current_fitness_level: Optional[Dict[str, Any]] = None
    specific_adaptations: Optional[Dict[str, Any]] = None


class WeeklyPlanResponse(BaseModel):
    week: int
    focus: str
    adaptations: Dict[str, Any]
    workouts: List[Dict[str, Any]]
    recovery_notes: str
    next_week_preview: str
    generated_at: str
    adaptation_rationale: str
    week_start_date: str
    week_end_date: str


class PerformanceAnalysisData(BaseModel):
    completion_rate: float = Field(..., ge=0, le=100)
    intensity_trend: str = Field(..., pattern="^(increasing|decreasing|stable)$")
    recovery_indicators: Dict[str, Any]
    performance_improvement: float
    fatigue_level: str = Field(..., pattern="^(low|moderate|high|critical)$")
    avg_rpe: Optional[float] = Field(None, ge=1, le=10)
    consistency_score: float = Field(..., ge=0, le=100)


class AdaptivePlanRequest(BaseModel):
    target_date: str = Field(..., description="Data obiettivo finale - formato YYYY-MM-DD")
    force_regeneration: bool = Field(False, description="Forza rigenerazione completa del piano")
    specific_focus: Optional[str] = Field(None, description="Focus specifico per la settimana")
