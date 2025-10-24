from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.database import get_db
from app.schemas.workout import (
    WorkoutPlanCreate, WorkoutPlanUpdate, WorkoutPlanResponse,
    WorkoutCreate, WorkoutUpdate, WorkoutResponse,
    WorkoutSessionCreate, WorkoutSessionResponse,
    AIWorkoutPlanRequest
)
from app.schemas.ai import (
    ProgressiveWorkoutPlanRequest, WeeklyPlanRequest, WeeklyPlanResponse,
    AdaptivePlanRequest, PerformanceAnalysisData
)
from app.services.workout_service import WorkoutService
from app.services.ai_service import AIService
from app.services.progressive_workout_service import ProgressiveWorkoutPlanService
from app.api.auth import get_current_user

router = APIRouter(prefix="/workouts", tags=["workouts"])


# OPTIONS endpoints for CORS preflight
@router.options("/")
async def options_workouts():
    """Handle OPTIONS request for CORS preflight"""
    return Response(status_code=200)


@router.options("/plans")
async def options_workout_plans():
    """Handle OPTIONS request for CORS preflight"""
    return Response(status_code=200)


@router.options("/sessions")
async def options_workout_sessions():
    """Handle OPTIONS request for CORS preflight"""
    return Response(status_code=200)


# Workout Plans
@router.get("/plans", response_model=List[WorkoutPlanResponse])
async def get_workout_plans(skip: int = Query(0, ge=0),
                           limit: int = Query(100, ge=1, le=100),
                           current_user: dict = Depends(get_current_user),
                           db: Session = Depends(get_db)):
    """Get user's workout plans"""
    workout_service = WorkoutService(db)
    plans = workout_service.get_workout_plans(
        user_id=current_user["user_id"],
        skip=skip,
        limit=limit
    )
    return plans


@router.post("/plans", response_model=WorkoutPlanResponse, status_code=status.HTTP_201_CREATED)
async def create_workout_plan(plan_data: WorkoutPlanCreate,
                             current_user: dict = Depends(get_current_user),
                             db: Session = Depends(get_db)):
    """Create a new workout plan"""
    workout_service = WorkoutService(db)
    plan = workout_service.create_workout_plan(
        user_id=current_user["user_id"],
        plan_data=plan_data
    )
    return plan


@router.get("/plans/{plan_id}", response_model=WorkoutPlanResponse)
async def get_workout_plan(plan_id: int,
                          current_user: dict = Depends(get_current_user),
                          db: Session = Depends(get_db)):
    """Get specific workout plan"""
    workout_service = WorkoutService(db)
    plan = workout_service.get_workout_plan(plan_id, current_user["user_id"])
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout plan not found"
        )
    
    return plan


@router.put("/plans/{plan_id}", response_model=WorkoutPlanResponse)
async def update_workout_plan(plan_id: int,
                             plan_data: WorkoutPlanUpdate,
                             current_user: dict = Depends(get_current_user),
                             db: Session = Depends(get_db)):
    """Update workout plan"""
    workout_service = WorkoutService(db)
    plan = workout_service.update_workout_plan(
        plan_id=plan_id,
        user_id=current_user["user_id"],
        plan_data=plan_data
    )
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout plan not found"
        )
    
    return plan


@router.delete("/plans/{plan_id}")
async def delete_workout_plan(plan_id: int,
                             current_user: dict = Depends(get_current_user),
                             db: Session = Depends(get_db)):
    """Delete workout plan"""
    workout_service = WorkoutService(db)
    success = workout_service.delete_workout_plan(plan_id, current_user["user_id"])
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout plan not found"
        )
    
    return {"message": "Workout plan deleted successfully"}


@router.post("/plans/generate-ai", response_model=dict)
async def generate_ai_workout_plan(ai_request: AIWorkoutPlanRequest,
                                  current_user: dict = Depends(get_current_user),
                                  db: Session = Depends(get_db)):
    """Generate workout plan using AI"""
    ai_service = AIService()
    plan_data = ai_service.generate_workout_plan(ai_request)
    
    # Optionally save the generated plan
    if plan_data:
        workout_service = WorkoutService(db)
        # Convert AI response to WorkoutPlanCreate format
        plan_create = WorkoutPlanCreate(
            title=plan_data.get("title", "AI Generated Plan"),
            description=plan_data.get("description", ""),
            start_date=ai_request.start_date if hasattr(ai_request, 'start_date') else None,
            end_date=ai_request.end_date if hasattr(ai_request, 'end_date') else None,
            goal=ai_request.goal,
            sport_type=ai_request.sport_type,
            level=ai_request.level
        )
        
        # Create the plan in database
        plan = workout_service.create_workout_plan(
            user_id=current_user["user_id"],
            plan_data=plan_create
        )
        
        return {"plan": plan, "ai_data": plan_data}
    
    return {"ai_data": plan_data}


# Progressive Workout Plans
@router.post("/plans/generate-progressive", response_model=dict)
async def generate_progressive_workout_plan(
    request: ProgressiveWorkoutPlanRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Genera piano di allenamento progressivo con data target"""
    progressive_service = ProgressiveWorkoutPlanService(db)
    
    # Genera prima settimana del piano progressivo
    first_week_plan = progressive_service.generate_weekly_plan(
        user_id=current_user["user_id"],
        week_number=1,
        target_date=request.target_date,
        current_fitness_level=request.user_profile
    )
    
    # Crea piano base nel database
    workout_service = WorkoutService(db)
    plan_create = WorkoutPlanCreate(
        title=f"{request.sport_type.title()} - {request.goal}",
        description=f"Piano progressivo per {request.goal} - Target: {request.target_date}",
        start_date=datetime.strptime(request.start_date, "%Y-%m-%d").date(),
        end_date=datetime.strptime(request.target_date, "%Y-%m-%d").date(),
        goal=request.goal,
        sport_type=request.sport_type,
        level=request.level
    )
    
    plan = workout_service.create_workout_plan(
        user_id=current_user["user_id"],
        plan_data=plan_create
    )
    
    return {
        "plan": plan,
        "first_week": first_week_plan,
        "target_date": request.target_date,
        "total_weeks": first_week_plan.get("weeks_remaining", 12)
    }


@router.post("/plans/generate-weekly", response_model=WeeklyPlanResponse)
async def generate_weekly_plan(
    request: WeeklyPlanRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Genera piano per una settimana specifica"""
    progressive_service = ProgressiveWorkoutPlanService(db)
    
    weekly_plan = progressive_service.generate_weekly_plan(
        user_id=current_user["user_id"],
        week_number=request.week_number,
        target_date=request.target_date,
        previous_week_data=request.previous_week_data,
        current_fitness_level=request.current_fitness_level
    )
    
    return WeeklyPlanResponse(**weekly_plan)


@router.post("/plans/adapt-next-week", response_model=WeeklyPlanResponse)
async def adapt_next_week_plan(
    request: AdaptivePlanRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Adatta automaticamente la prossima settimana basandosi sulle performance"""
    progressive_service = ProgressiveWorkoutPlanService(db)
    
    next_week_plan = progressive_service.adapt_next_week_plan(
        user_id=current_user["user_id"],
        target_date=request.target_date
    )
    
    return WeeklyPlanResponse(**next_week_plan)


@router.get("/plans/current-week", response_model=dict)
async def get_current_week_data(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Ottiene dati della settimana corrente"""
    progressive_service = ProgressiveWorkoutPlanService(db)
    
    current_week = progressive_service.get_current_week_data(current_user["user_id"])
    fitness_level = progressive_service.get_current_fitness_level(current_user["user_id"])
    
    return {
        "current_week": current_week,
        "fitness_level": fitness_level
    }


@router.get("/plans/performance-analysis", response_model=PerformanceAnalysisData)
async def get_performance_analysis(
    weeks_back: int = Query(4, ge=1, le=12),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Ottiene analisi delle performance dell'utente"""
    progressive_service = ProgressiveWorkoutPlanService(db)
    
    user_history = progressive_service._get_user_workout_history(
        current_user["user_id"], 
        weeks_back=weeks_back
    )
    performance_trends = progressive_service._analyze_performance_trends(user_history)
    
    return PerformanceAnalysisData(**performance_trends)


# Workouts
@router.get("/", response_model=List[WorkoutResponse])
async def get_workouts(skip: int = Query(0, ge=0),
                      limit: int = Query(100, ge=1, le=100),
                      plan_id: Optional[int] = Query(None),
                      current_user: dict = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    """Get user's workouts"""
    workout_service = WorkoutService(db)
    workouts = workout_service.get_workouts(
        user_id=current_user["user_id"],
        skip=skip,
        limit=limit,
        plan_id=plan_id
    )
    return workouts


@router.post("/", response_model=WorkoutResponse, status_code=status.HTTP_201_CREATED)
async def create_workout(workout_data: WorkoutCreate,
                        current_user: dict = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    """Create a new workout"""
    workout_service = WorkoutService(db)
    workout = workout_service.create_workout(
        user_id=current_user["user_id"],
        workout_data=workout_data
    )
    return workout


@router.get("/{workout_id}", response_model=WorkoutResponse)
async def get_workout(workout_id: int,
                     current_user: dict = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    """Get specific workout"""
    workout_service = WorkoutService(db)
    workout = workout_service.get_workout(workout_id, current_user["user_id"])
    
    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout not found"
        )
    
    return workout


@router.put("/{workout_id}", response_model=WorkoutResponse)
async def update_workout(workout_id: int,
                        workout_data: WorkoutUpdate,
                        current_user: dict = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    """Update workout"""
    workout_service = WorkoutService(db)
    workout = workout_service.update_workout(
        workout_id=workout_id,
        user_id=current_user["user_id"],
        workout_data=workout_data
    )
    
    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout not found"
        )
    
    return workout


@router.delete("/{workout_id}")
async def delete_workout(workout_id: int,
                        current_user: dict = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    """Delete workout"""
    workout_service = WorkoutService(db)
    success = workout_service.delete_workout(workout_id, current_user["user_id"])
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout not found"
        )
    
    return {"message": "Workout deleted successfully"}


@router.post("/{workout_id}/complete", response_model=WorkoutSessionResponse, status_code=status.HTTP_201_CREATED)
async def complete_workout(workout_id: int,
                          session_data: WorkoutSessionCreate,
                          current_user: dict = Depends(get_current_user),
                          db: Session = Depends(get_db)):
    """Complete a workout by creating a session"""
    workout_service = WorkoutService(db)
    
    # Verify workout exists and belongs to user
    workout = workout_service.get_workout(workout_id, current_user["user_id"])
    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout not found"
        )
    
    # Create workout session
    session = workout_service.create_workout_session(
        user_id=current_user["user_id"],
        session_data=session_data
    )
    
    # Update workout status
    workout.status = "completed"
    db.commit()
    
    return session


# Workout Sessions
@router.get("/sessions", response_model=List[WorkoutSessionResponse])
async def get_workout_sessions(skip: int = Query(0, ge=0),
                              limit: int = Query(100, ge=1, le=100),
                              workout_id: Optional[int] = Query(None),
                              current_user: dict = Depends(get_current_user),
                              db: Session = Depends(get_db)):
    """Get workout sessions"""
    workout_service = WorkoutService(db)
    sessions = workout_service.get_workout_sessions(
        user_id=current_user["user_id"],
        workout_id=workout_id,
        skip=skip,
        limit=limit
    )
    return sessions
