from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import func, select, and_
from typing import List, Optional
from datetime import datetime
from app.database import get_db
from app.schemas.workout import (
    WorkoutPlanCreate, WorkoutPlanUpdate, WorkoutPlanResponse,
    WorkoutCreate, WorkoutUpdate, WorkoutResponse,
    WorkoutSessionCreate, WorkoutSessionResponse,
    AIWorkoutPlanRequest
)
from app.models.workout import Workout, WorkoutSession, WorkoutPlan
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
    # Add is_progressive field to each plan
    result = []
    for plan in plans:
        plan_dict = WorkoutPlanResponse.model_validate(plan).model_dump()
        plan_dict["is_progressive"] = workout_service._is_progressive_plan(plan)
        result.append(plan_dict)
    return result


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
    # Add is_progressive field
    plan_dict = WorkoutPlanResponse.model_validate(plan).model_dump()
    plan_dict["is_progressive"] = workout_service._is_progressive_plan(plan)
    return plan_dict


# Progressive Workout Plans - Specific routes must come before dynamic routes
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
    
    # Create workouts from first week plan
    workouts = workout_service.create_workouts_from_progressive_week(
        user_id=current_user["user_id"],
        plan_id=plan.id,
        week_data=first_week_plan
    )
    
    # Create calendar events from workouts
    calendar_events = workout_service.create_calendar_events_from_workouts(
        user_id=current_user["user_id"],
        workouts=workouts
    )
    
    # Convert SQLAlchemy model to Pydantic schema
    plan_response = WorkoutPlanResponse.model_validate(plan)
    
    return {
        "plan": plan_response.model_dump(),
        "first_week": first_week_plan,
        "target_date": request.target_date,
        "total_weeks": first_week_plan.get("weeks_remaining", 12),
        "workouts_created": len(workouts),
        "calendar_events_created": len(calendar_events)
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


@router.post("/plans/generate-ai", response_model=dict)
async def generate_ai_workout_plan(ai_request: AIWorkoutPlanRequest,
                                  current_user: dict = Depends(get_current_user),
                                  db: Session = Depends(get_db)):
    """Generate workout plan using AI - supports both traditional and progressive plans"""
    
    # Check if this is a progressive plan
    if ai_request.is_progressive and ai_request.target_date and ai_request.start_date:
        # Generate progressive workout plan
        from app.services.progressive_workout_service import ProgressiveWorkoutPlanService
        
        progressive_service = ProgressiveWorkoutPlanService(db)
        
        # Generate first week of progressive plan
        first_week_plan = progressive_service.generate_weekly_plan(
            user_id=current_user["user_id"],
            week_number=1,
            target_date=ai_request.target_date,
            current_fitness_level=ai_request.user_profile
        )
        
        # Create base plan in database
        workout_service = WorkoutService(db)
        plan_create = WorkoutPlanCreate(
            title=f"{ai_request.sport_type.title()} - {ai_request.goal}",
            description=f"Piano progressivo per {ai_request.goal} - Target: {ai_request.target_date}",
            start_date=datetime.strptime(ai_request.start_date, "%Y-%m-%d").date(),
            end_date=datetime.strptime(ai_request.target_date, "%Y-%m-%d").date(),
            goal=ai_request.goal,
            sport_type=ai_request.sport_type,
            level=ai_request.level
        )
        
        plan = workout_service.create_workout_plan(
            user_id=current_user["user_id"],
            plan_data=plan_create
        )
        
        # Create workouts from first week plan
        workouts = workout_service.create_workouts_from_progressive_week(
            user_id=current_user["user_id"],
            plan_id=plan.id,
            week_data=first_week_plan
        )
        
        # Create calendar events from workouts
        calendar_events = workout_service.create_calendar_events_from_workouts(
            user_id=current_user["user_id"],
            workouts=workouts
        )
        
        # Convert SQLAlchemy object to dict for serialization
        plan_dict = {
            "id": plan.id,
            "user_id": plan.user_id,
            "title": plan.title,
            "description": plan.description,
            "start_date": plan.start_date.isoformat() if plan.start_date else None,
            "end_date": plan.end_date.isoformat() if plan.end_date else None,
            "total_weeks": plan.total_weeks,
            "goal": plan.goal,
            "sport_type": plan.sport_type,
            "level": plan.level,
            "status": plan.status,
            "created_at": plan.created_at.isoformat() if plan.created_at else None,
            "updated_at": plan.updated_at.isoformat() if plan.updated_at else None
        }
        
        return {
            "plan": plan_dict,
            "first_week": first_week_plan,
            "target_date": ai_request.target_date,
            "total_weeks": first_week_plan.get("weeks_remaining", 12),
            "is_progressive": True,
            "workouts_created": len(workouts),
            "calendar_events_created": len(calendar_events)
        }
    
    else:
        # Generate traditional workout plan using AI
        ai_service = AIService()
        plan_data = ai_service.generate_workout_plan(ai_request)
        
        # Optionally save the generated plan
        if plan_data:
            workout_service = WorkoutService(db)
            # Convert AI response to WorkoutPlanCreate format
            plan_create = WorkoutPlanCreate(
                title=plan_data.get("title", "AI Generated Plan"),
                description=plan_data.get("description", ""),
                start_date=datetime.now().date() if not ai_request.start_date else datetime.strptime(ai_request.start_date, "%Y-%m-%d").date(),
                end_date=datetime.now().date() if not ai_request.target_date else datetime.strptime(ai_request.target_date, "%Y-%m-%d").date(),
                goal=ai_request.goal,
                sport_type=ai_request.sport_type,
                level=ai_request.level
            )
            
            # Create the plan in database
            plan = workout_service.create_workout_plan(
                user_id=current_user["user_id"],
                plan_data=plan_create
            )
            
            # Create individual workouts from AI plan data
            workouts = workout_service.create_workouts_from_ai_plan(
                user_id=current_user["user_id"],
                plan_id=plan.id,
                ai_plan_data=plan_data
            )
            
            # Create calendar events from workouts
            calendar_events = workout_service.create_calendar_events_from_workouts(
                user_id=current_user["user_id"],
                workouts=workouts
            )
            
            # Convert SQLAlchemy object to dict for serialization
            plan_dict = {
                "id": plan.id,
                "user_id": plan.user_id,
                "title": plan.title,
                "description": plan.description,
                "start_date": plan.start_date.isoformat() if plan.start_date else None,
                "end_date": plan.end_date.isoformat() if plan.end_date else None,
                "total_weeks": plan.total_weeks,
                "goal": plan.goal,
                "sport_type": plan.sport_type,
                "level": plan.level,
                "status": plan.status,
                "created_at": plan.created_at.isoformat() if plan.created_at else None,
                "updated_at": plan.updated_at.isoformat() if plan.updated_at else None
            }
            
            return {
                "plan": plan_dict, 
                "ai_data": plan_data, 
                "is_progressive": False,
                "workouts_created": len(workouts),
                "calendar_events_created": len(calendar_events)
            }
        
        return {"ai_data": plan_data, "is_progressive": False}


@router.get("/plans/{plan_id}")
async def get_workout_plan(plan_id: int,
                          current_user: dict = Depends(get_current_user),
                          db: Session = Depends(get_db)):
    """Get specific workout plan with all workouts, sessions, and Strava details"""
    try:
        workout_service = WorkoutService(db)
        plan_details = workout_service.get_workout_plan_with_details(plan_id, current_user["user_id"])
        
        if not plan_details:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workout plan not found"
            )
        
        return plan_details
    except Exception as e:
        print(f"Error in get_workout_plan: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


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
    
    # Add is_progressive field
    plan_dict = WorkoutPlanResponse.model_validate(plan).model_dump()
    plan_dict["is_progressive"] = workout_service._is_progressive_plan(plan)
    return plan_dict


@router.post("/plans/{plan_id}/archive")
async def archive_workout_plan(plan_id: int,
                              current_user: dict = Depends(get_current_user),
                              db: Session = Depends(get_db)):
    """Archive a workout plan"""
    workout_service = WorkoutService(db)
    
    # Get the plan
    plan = workout_service.get_workout_plan(plan_id, current_user["user_id"])
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout plan not found"
        )
    
    # Update status to archived
    plan.status = "archived"
    db.commit()
    
    return {
        "message": "Piano archiviato con successo",
        "plan_id": plan.id
    }


@router.get("/plans/{plan_id}/statistics")
async def get_plan_statistics(plan_id: int,
                              current_user: dict = Depends(get_current_user),
                              db: Session = Depends(get_db)):
    """Get plan statistics"""
    from app.models.strava import StravaActivity
    from datetime import timedelta
    
    user_id = current_user["user_id"]
    
    # Get the plan
    workout_service = WorkoutService(db)
    plan = workout_service.get_workout_plan(plan_id, user_id)
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout plan not found"
        )
    
    # Get all workouts for this plan
    workouts = db.query(Workout).filter(
        Workout.plan_id == plan_id
    ).all()
    
    # Calculate duration in days
    if plan.start_date and plan.end_date:
        duration_days = (plan.end_date - plan.start_date).days
    else:
        duration_days = 0
    
    # Total workouts
    total_workouts = len(workouts)
    
    # Completed workouts
    completed_workouts = len([w for w in workouts if w.status == "completed"])
    
    # Total distance from Strava
    workout_ids = [w.id for w in workouts]
    total_distance = 0
    if workout_ids:
        total_distance = db.query(func.sum(StravaActivity.distance)).filter(
            StravaActivity.workout_id.in_(workout_ids)
        ).scalar() or 0
    
    # Total time from sessions
    sessions = db.query(WorkoutSession).filter(
        WorkoutSession.workout_id.in_(workout_ids)
    ).all()
    total_time = sum([s.duration_minutes for s in sessions]) * 60  # Convert to seconds
    
    # Average heart rate
    avg_heart_rate = db.query(func.avg(WorkoutSession.avg_hr)).filter(
        WorkoutSession.workout_id.in_(workout_ids)
    ).scalar()
    avg_heart_rate = round(avg_heart_rate, 0) if avg_heart_rate else None
    
    # Average power (for cycling)
    avg_power = db.query(func.avg(WorkoutSession.avg_power)).filter(
        WorkoutSession.workout_id.in_(workout_ids)
    ).scalar()
    avg_power = round(avg_power, 0) if avg_power else None
    
    # Simple improvements (placeholder - can be enhanced with AI)
    improvements = []
    if completed_workouts > 0:
        improvements.append(f"Completati {completed_workouts} allenamenti")
    if avg_heart_rate and avg_heart_rate > 150:
        improvements.append(f"Medio FC {avg_heart_rate} bpm")
    
    return {
        "duration_days": duration_days,
        "total_workouts": total_workouts,
        "completed_workouts": completed_workouts,
        "total_distance": int(total_distance),
        "total_time": total_time,
        "avg_heart_rate": int(avg_heart_rate) if avg_heart_rate else None,
        "avg_power": int(avg_power) if avg_power else None,
        "improvements": improvements
    }


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


# Workout Sessions - MUST be defined BEFORE /{workout_id} route
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


# Workouts
@router.get("/", response_model=List[WorkoutResponse])
async def get_workouts(skip: int = Query(0, ge=0),
                      limit: int = Query(100, ge=1, le=100),
                      plan_id: Optional[int] = Query(None),
                      current_user: dict = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    """Get user's workouts, excluding inactive plans"""
    workout_service = WorkoutService(db)
    workouts = workout_service.get_workouts(
        user_id=current_user["user_id"],
        skip=skip,
        limit=limit,
        plan_id=plan_id
    )
    
    # Filter out workouts from inactive plans
    if workouts:
        inactive_plan_workout_ids = db.execute(
            select(Workout.id)
            .join(WorkoutPlan, Workout.plan_id == WorkoutPlan.id)
            .where(
                and_(
                    WorkoutPlan.user_id == current_user["user_id"],
                    WorkoutPlan.status != "active"
                )
            )
        ).scalars().all()
        inactive_plan_workout_ids = set(inactive_plan_workout_ids)
        
        workouts = [w for w in workouts if w.id not in inactive_plan_workout_ids]
    
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


@router.patch("/{workout_id}/complete")
async def complete_workout(workout_id: int,
                          current_user: dict = Depends(get_current_user),
                          db: Session = Depends(get_db)):
    """Mark workout as completed"""
    workout_service = WorkoutService(db)
    
    # Verify workout exists and belongs to user
    workout = workout_service.get_workout(workout_id, current_user["user_id"])
    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout not found"
        )
    
    # Update workout status to completed
    workout.status = "completed"
    db.commit()
    db.refresh(workout)
    
    return {
        "id": workout.id,
        "completed": True,
        "completed_at": workout.updated_at.isoformat() if workout.updated_at else None
    }
