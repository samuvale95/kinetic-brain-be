from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List


class AIRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4000)
    context: Optional[Dict[str, Any]] = None
    max_tokens: Optional[int] = Field(None, ge=1, le=4000)
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)


class AIResponse(BaseModel):
    response: str
    usage: Optional[Dict[str, int]] = None
    model: str
    created_at: str


class WorkoutPlanGenerationRequest(BaseModel):
    sport_type: str = Field(..., min_length=1, max_length=50)
    level: str = Field(..., regex="^(beginner|intermediate|advanced)$")
    goal: str = Field(..., min_length=1, max_length=200)
    duration_weeks: int = Field(..., ge=1, le=52)
    weekly_hours: float = Field(..., gt=0, le=168)
    user_profile: Optional[Dict[str, Any]] = None
    preferences: Optional[Dict[str, Any]] = None


class WorkoutAnalysisRequest(BaseModel):
    workout_data: Dict[str, Any]
    performance_metrics: Optional[Dict[str, Any]] = None
    analysis_type: str = Field(..., regex="^(performance|recovery|progression)$")


class WorkoutAnalysisResponse(BaseModel):
    analysis: str
    recommendations: List[str]
    score: Optional[float] = Field(None, ge=0.0, le=10.0)
    areas_for_improvement: List[str]
    next_steps: List[str]


class SuggestionRequest(BaseModel):
    context: str = Field(..., min_length=1, max_length=1000)
    suggestion_type: str = Field(..., regex="^(workout|nutrition|recovery|equipment)$")
    user_profile: Optional[Dict[str, Any]] = None
