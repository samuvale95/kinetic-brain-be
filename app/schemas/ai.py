from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Literal
from pydantic import model_validator


class AIRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=15000)
    context: Optional[Dict[str, Any]] = None
    max_tokens: Optional[int] = Field(None, ge=1, le=4000)
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    response_format: Optional[Dict[str, Any]] = None


class AIResponse(BaseModel):
    response: str
    usage: Optional[Dict[str, Any]] = None
    model: str
    created_at: str


class WorkoutPlanGenerationRequest(BaseModel):
    sport_type: str = Field(..., min_length=1, max_length=50)
    level: str = Field(..., pattern="^(beginner|intermediate|advanced)$")
    goal: str = Field(..., min_length=1, max_length=200)
    duration_weeks: Optional[int] = Field(None, ge=1, le=52)
    start_date: Optional[str] = Field(None, description="Data di inizio piano (YYYY-MM-DD)")
    target_date: Optional[str] = Field(None, description="Data obiettivo/fine piano (YYYY-MM-DD)")
    weekly_hours: Optional[float] = Field(None, gt=0, le=168, description="Ore settimanali disponibili (indicativo)")
    user_profile: Optional[Dict[str, Any]] = None
    preferences: Optional[Dict[str, Any]] = None
    race_distance_km: Optional[float] = Field(
        None,
        gt=0,
        description="Distanza gara in km per piani running/trail",
    )
    race_type: Optional[Literal["sprint", "olympic", "half_ironman", "ironman"]] = Field(
        None,
        description="Tipologia gara triathlon",
    )
    # Stretching and Strength flags
    include_stretching: bool = Field(False, description="Include stretching sessions in the plan")
    include_strength: bool = Field(False, description="Include strength training sessions in the plan")
    # Day constraints
    unavailable_days: Optional[List[str]] = Field(
        None,
        description="Days of the week when training is not available (e.g. ['Monday', 'Friday'])"
    )
    sport_specific_days: Optional[Dict[str, str]] = Field(
        None,
        description="Mapping of days to specific sports (e.g. {'Monday': 'run', 'Wednesday': 'bike'})"
    )

    @model_validator(mode="after")
    def validate_race_details(cls, values: "WorkoutPlanGenerationRequest") -> "WorkoutPlanGenerationRequest":
        sport = (values.sport_type or "").lower()
        if values.race_type and sport != "triathlon":
            raise ValueError("race_type è valido solo per piani triathlon")
        if values.race_distance_km and sport not in {"running", "run", "trail", "trail running"}:
            raise ValueError("race_distance_km è valido solo per piani running o trail")
        return values
    
    @model_validator(mode="after")
    def validate_day_constraints(cls, values: "WorkoutPlanGenerationRequest") -> "WorkoutPlanGenerationRequest":
        valid_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        valid_sports = ["run", "running", "bike", "cycling", "swim", "swimming", "triathlon"]
        
        # Validate unavailable_days
        if values.unavailable_days:
            invalid_days = [
                day for day in values.unavailable_days 
                if day.capitalize() not in valid_days
            ]
            if invalid_days:
                raise ValueError(
                    f"Invalid days in unavailable_days: {invalid_days}. "
                    f"Valid days are: {', '.join(valid_days)}"
                )
            # Normalize to capitalized format
            values.unavailable_days = [day.capitalize() for day in values.unavailable_days]
        
        # Validate sport_specific_days
        if values.sport_specific_days:
            invalid_days = [
                day for day in values.sport_specific_days.keys()
                if day.capitalize() not in valid_days
            ]
            if invalid_days:
                raise ValueError(
                    f"Invalid days in sport_specific_days: {invalid_days}. "
                    f"Valid days are: {', '.join(valid_days)}"
                )
            
            invalid_sports = [
                (day, sport) for day, sport in values.sport_specific_days.items()
                if sport.lower() not in valid_sports
            ]
            if invalid_sports:
                invalid_list = [f"{day}: {sport}" for day, sport in invalid_sports]
                raise ValueError(
                    f"Invalid sports in sport_specific_days: {', '.join(invalid_list)}. "
                    f"Valid sports are: {', '.join(valid_sports)}"
                )
            
            # Normalize keys to capitalized format
            normalized = {
                day.capitalize(): sport.lower() 
                for day, sport in values.sport_specific_days.items()
            }
            values.sport_specific_days = normalized
        
        return values


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
    # Stretching and Strength flags
    include_stretching: bool = Field(False, description="Include stretching sessions in the plan")
    include_strength: bool = Field(False, description="Include strength training sessions in the plan")
    # Day constraints
    unavailable_days: Optional[List[str]] = Field(
        None,
        description="Days of the week when training is not available (e.g. ['Monday', 'Friday'])"
    )
    sport_specific_days: Optional[Dict[str, str]] = Field(
        None,
        description="Mapping of days to specific sports (e.g. {'Monday': 'run', 'Wednesday': 'bike'})"
    )

    @model_validator(mode="after")
    def validate_day_constraints(cls, values: "ProgressiveWorkoutPlanRequest") -> "ProgressiveWorkoutPlanRequest":
        valid_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        valid_sports = ["run", "running", "bike", "cycling", "swim", "swimming", "triathlon"]
        
        # Validate unavailable_days
        if values.unavailable_days:
            invalid_days = [
                day for day in values.unavailable_days 
                if day.capitalize() not in valid_days
            ]
            if invalid_days:
                raise ValueError(
                    f"Invalid days in unavailable_days: {invalid_days}. "
                    f"Valid days are: {', '.join(valid_days)}"
                )
            # Normalize to capitalized format
            values.unavailable_days = [day.capitalize() for day in values.unavailable_days]
        
        # Validate sport_specific_days
        if values.sport_specific_days:
            invalid_days = [
                day for day in values.sport_specific_days.keys()
                if day.capitalize() not in valid_days
            ]
            if invalid_days:
                raise ValueError(
                    f"Invalid days in sport_specific_days: {invalid_days}. "
                    f"Valid days are: {', '.join(valid_days)}"
                )
            
            invalid_sports = [
                (day, sport) for day, sport in values.sport_specific_days.items()
                if sport.lower() not in valid_sports
            ]
            if invalid_sports:
                invalid_list = [f"{day}: {sport}" for day, sport in invalid_sports]
                raise ValueError(
                    f"Invalid sports in sport_specific_days: {', '.join(invalid_list)}. "
                    f"Valid sports are: {', '.join(valid_sports)}"
                )
            
            # Normalize keys to capitalized format
            normalized = {
                day.capitalize(): sport.lower() 
                for day, sport in values.sport_specific_days.items()
            }
            values.sport_specific_days = normalized
        
        return values


class WeeklyPlanRequest(BaseModel):
    week_number: int = Field(..., ge=1, le=52)
    target_date: str = Field(..., description="Data obiettivo finale - formato YYYY-MM-DD")
    previous_week_data: Optional[Dict[str, Any]] = None
    current_fitness_level: Optional[Dict[str, Any]] = None
    specific_adaptations: Optional[Dict[str, Any]] = None
    # Stretching and Strength flags
    include_stretching: bool = Field(False, description="Include stretching sessions in the plan")
    include_strength: bool = Field(False, description="Include strength training sessions in the plan")
    # Day constraints
    unavailable_days: Optional[List[str]] = Field(
        None,
        description="Days of the week when training is not available (e.g. ['Monday', 'Friday'])"
    )
    sport_specific_days: Optional[Dict[str, str]] = Field(
        None,
        description="Mapping of days to specific sports (e.g. {'Monday': 'run', 'Wednesday': 'bike'})"
    )

    @model_validator(mode="after")
    def validate_day_constraints(cls, values: "WeeklyPlanRequest") -> "WeeklyPlanRequest":
        valid_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        valid_sports = ["run", "running", "bike", "cycling", "swim", "swimming", "triathlon"]
        
        # Validate unavailable_days
        if values.unavailable_days:
            invalid_days = [
                day for day in values.unavailable_days 
                if day.capitalize() not in valid_days
            ]
            if invalid_days:
                raise ValueError(
                    f"Invalid days in unavailable_days: {invalid_days}. "
                    f"Valid days are: {', '.join(valid_days)}"
                )
            # Normalize to capitalized format
            values.unavailable_days = [day.capitalize() for day in values.unavailable_days]
        
        # Validate sport_specific_days
        if values.sport_specific_days:
            invalid_days = [
                day for day in values.sport_specific_days.keys()
                if day.capitalize() not in valid_days
            ]
            if invalid_days:
                raise ValueError(
                    f"Invalid days in sport_specific_days: {invalid_days}. "
                    f"Valid days are: {', '.join(valid_days)}"
                )
            
            invalid_sports = [
                (day, sport) for day, sport in values.sport_specific_days.items()
                if sport.lower() not in valid_sports
            ]
            if invalid_sports:
                invalid_list = [f"{day}: {sport}" for day, sport in invalid_sports]
                raise ValueError(
                    f"Invalid sports in sport_specific_days: {', '.join(invalid_list)}. "
                    f"Valid sports are: {', '.join(valid_sports)}"
                )
            
            # Normalize keys to capitalized format
            normalized = {
                day.capitalize(): sport.lower() 
                for day, sport in values.sport_specific_days.items()
            }
            values.sport_specific_days = normalized
        
        return values


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


class ClaudeReviewResponse(BaseModel):
    approved: bool = Field(..., description="Whether the plan is approved or needs improvement")
    improved_plan: Optional[Dict[str, Any]] = Field(None, description="Improved version of the plan if changes were made")
    review_notes: str = Field(..., description="Review notes explaining the evaluation")
    changelog: Optional[List[str]] = Field(None, description="List of changes made to the plan")
    model: str = Field(..., description="Claude model used for review")
    usage: Optional[Dict[str, Any]] = Field(None, description="Token usage information")
