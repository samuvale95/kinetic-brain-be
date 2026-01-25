from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Body
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import func, select, and_, desc
from typing import List, Optional
from datetime import datetime, timedelta, date
from app.database import get_db
from app.schemas.workout import (
    WorkoutPlanCreate, WorkoutPlanUpdate, WorkoutPlanResponse,
    WorkoutCreate, WorkoutUpdate, WorkoutResponse,
    WorkoutSessionCreate, WorkoutSessionResponse,
    AIWorkoutPlanRequest, InstantWorkoutRequest
)
from app.schemas.healthkit import (
    WatchWorkoutFormatResponse,
    WatchSessionCreateRequest,
    WatchSessionCreateResponse
)
from app.models.workout import Workout, WorkoutSession, WorkoutPlan
from app.schemas.ai import (
    ProgressiveWorkoutPlanRequest, WeeklyPlanRequest, WeeklyPlanResponse,
    AdaptivePlanRequest, PerformanceAnalysisData
)
from app.services.workout_service import WorkoutService
from app.services.ai_service import AIService
from app.services.progressive_workout_service import ProgressiveWorkoutPlanService
from app.services.healthkit_service import HealthKitService
from app.api.auth import get_current_user
from loguru import logger
import json

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
from app.middleware.rate_limit_middleware import limiter, get_user_id_for_rate_limit
from slowapi.util import get_remote_address
from fastapi import Request

@router.post("/plans/generate-progressive", response_model=dict)
@limiter.limit("50/hour", key_func=lambda request: f"user:{get_user_id_for_rate_limit(request) or get_remote_address(request)}")
async def generate_progressive_workout_plan(
    request: ProgressiveWorkoutPlanRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Genera piano di allenamento progressivo con data target"""
    user_id = current_user["user_id"]
    logger.info(f"[API] POST /workouts/plans/generate-progressive - user_id: {user_id}")
    
    request_summary = {
        "sport_type": request.sport_type,
        "level": request.level,
        "goal": request.goal,
        "target_date": request.target_date,
        "start_date": request.start_date,
        "weekly_hours": request.weekly_hours,
        "has_user_profile": request.user_profile is not None,
        "has_preferences": request.preferences is not None
    }
    logger.debug(f"[API] Request body: {json.dumps(request_summary, indent=2, default=str)}")
    
    progressive_service = ProgressiveWorkoutPlanService(db)
    
    # Genera prima settimana del piano progressivo
    first_week_plan = progressive_service.generate_weekly_plan(
        user_id=current_user["user_id"],
        week_number=1,
        target_date=request.target_date,
        current_fitness_level=request.user_profile,
        include_stretching=request.include_stretching,
        include_strength=request.include_strength,
        unavailable_days=request.unavailable_days,
        sport_specific_days=request.sport_specific_days,
        start_date=request.start_date,
        sport_type=request.sport_type,
        level=request.level,
        goal=request.goal,
        weekly_hours=request.weekly_hours,
        available_equipment=request.available_equipment
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
    
    # Send notification for new workouts
    if workouts:
        try:
            from app.services.notification_service import NotificationService
            notification_service = NotificationService(db)
            await notification_service.send_notification(
                user_id=current_user["user_id"],
                notification_type="new_workout",
                title="Nuovo piano di allenamento creato!",
                body=f"Hai {len(workouts)} nuovi allenamenti nel tuo piano: {plan.title}",
                data={
                    "plan_id": plan.id,
                    "plan_title": plan.title,
                    "workouts_count": len(workouts)
                }
            )
        except Exception as e:
            logger.error(f"Error sending new_workout notification: {e}")
    
    # Convert SQLAlchemy model to Pydantic schema
    plan_response = WorkoutPlanResponse.model_validate(plan)
    
    result = {
        "plan": plan_response.model_dump(),
        "first_week": first_week_plan,
        "target_date": request.target_date,
        "total_weeks": first_week_plan.get("weeks_remaining", 12),
        "workouts_created": len(workouts),
        "calendar_events_created": len(calendar_events)
    }
    
    logger.info(f"[API] Progressive plan generated successfully - plan_id: {plan.id}, workouts: {len(workouts)}, events: {len(calendar_events)}")
    logger.debug(f"[API] Response summary: plan_id={plan.id}, total_weeks={result.get('total_weeks')}, workouts_created={len(workouts)}")
    return result


@router.post("/plans/generate-weekly", response_model=WeeklyPlanResponse)
async def generate_weekly_plan(
    request: WeeklyPlanRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Genera piano per una settimana specifica"""
    user_id = current_user["user_id"]
    logger.info(f"[API] POST /workouts/plans/generate-weekly - user_id: {user_id}, week_number: {request.week_number}")
    logger.debug(f"[API] Request: week_number={request.week_number}, target_date={request.target_date}, has_previous_week={request.previous_week_data is not None}, has_fitness_level={request.current_fitness_level is not None}")
    
    progressive_service = ProgressiveWorkoutPlanService(db)
    
    # Recupera piano attivo per ottenere sport_type, level, goal
    active_plan = db.execute(
        select(WorkoutPlan)
        .where(and_(
            WorkoutPlan.user_id == current_user["user_id"],
            WorkoutPlan.status == "active"
        ))
        .order_by(desc(WorkoutPlan.created_at))
    ).scalar_one_or_none()
    
    sport_type = active_plan.sport_type if active_plan else None
    level = active_plan.level if active_plan else None
    goal = active_plan.goal if active_plan else None
    
    weekly_plan = progressive_service.generate_weekly_plan(
        user_id=current_user["user_id"],
        week_number=request.week_number,
        target_date=request.target_date,
        previous_week_data=request.previous_week_data,
        current_fitness_level=request.current_fitness_level,
        include_stretching=request.include_stretching,
        include_strength=request.include_strength,
        unavailable_days=request.unavailable_days,
        sport_specific_days=request.sport_specific_days,
        sport_type=sport_type,
        level=level,
        goal=goal,
        weekly_hours=None,
        available_equipment=request.available_equipment
    )
    
    logger.info(f"[API] Weekly plan generated successfully - week: {weekly_plan.get('week')}, workouts: {len(weekly_plan.get('workouts', []))}")
    return WeeklyPlanResponse(**weekly_plan)


@router.post("/plans/adapt-next-week", response_model=WeeklyPlanResponse)
async def adapt_next_week_plan(
    request: AdaptivePlanRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Adatta automaticamente la prossima settimana basandosi sulle performance"""
    user_id = current_user["user_id"]
    logger.info(f"[API] POST /workouts/plans/adapt-next-week - user_id: {user_id}")
    logger.debug(f"[API] Request: target_date={request.target_date}, force_regeneration={request.force_regeneration}, specific_focus={request.specific_focus}")
    
    progressive_service = ProgressiveWorkoutPlanService(db)
    workout_service = WorkoutService(db)
    
    # Get the active plan for the user
    active_plan = db.execute(
        select(WorkoutPlan)
        .where(and_(
            WorkoutPlan.user_id == current_user["user_id"],
            WorkoutPlan.status == "active"
        ))
        .order_by(desc(WorkoutPlan.created_at))
    ).scalar_one_or_none()
    
    if not active_plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active workout plan found"
        )
    
    # Ensure current week exists before generating next week
    # This is transparent to the frontend - it automatically generates the current week
    # if it's missing, taking into account fitness decay (CTL/ATL/TSB)
    logger.info(f"[API] Ensuring current week exists before generating next week - user_id: {user_id}")
    current_week_result = progressive_service.ensure_current_week_exists(user_id)
    
    # If current week was just generated, save it to database
    if current_week_result.get("was_generated") and current_week_result.get("plan_data"):
        current_week_plan_data = current_week_result["plan_data"]
        logger.info(
            f"[API] Current week {current_week_result.get('week_number')} was generated, "
            "saving workouts to database"
        )
        current_workouts = workout_service.create_workouts_from_progressive_week(
            user_id=user_id,
            plan_id=active_plan.id,
            week_data=current_week_plan_data
        )
        # Create calendar events for current week workouts
        workout_service.create_calendar_events_from_workouts(
            user_id=user_id,
            workouts=current_workouts
        )
        # Refresh session to ensure next query sees the new workouts
        db.expire_all()
        logger.info(
            f"[API] Current week workouts saved - workouts_created: {len(current_workouts)}"
        )
    
    # Generate next week plan
    next_week_plan = progressive_service.adapt_next_week_plan(
        user_id=current_user["user_id"],
        target_date=request.target_date
    )
    
    # Save workouts from next week plan to database
    workouts = workout_service.create_workouts_from_progressive_week(
        user_id=current_user["user_id"],
        plan_id=active_plan.id,
        week_data=next_week_plan
    )
    
    # Create calendar events from workouts
    calendar_events = workout_service.create_calendar_events_from_workouts(
        user_id=current_user["user_id"],
        workouts=workouts
    )
    
    # Send notification for weekly generation
    if workouts:
        try:
            from app.services.notification_service import NotificationService
            notification_service = NotificationService(db)
            await notification_service.send_notification(
                user_id=current_user["user_id"],
                notification_type="weekly_generation",
                title="Settimana generata automaticamente",
                body=f"È stata generata la settimana {next_week_plan.get('week', 'successiva')} del tuo piano con {len(workouts)} allenamenti",
                data={
                    "plan_id": active_plan.id,
                    "plan_title": active_plan.title,
                    "week_number": next_week_plan.get('week'),
                    "workouts_count": len(workouts)
                }
            )
        except Exception as e:
            logger.error(f"Error sending weekly_generation notification: {e}")
    
    # Workouts and calendar events are now saved in the database
    logger.info(f"[API] Next week plan adapted successfully - week: {next_week_plan.get('week')}, workouts_created: {len(workouts)}, events_created: {len(calendar_events)}")
    # Return the plan response (without the extra metadata to match schema)
    return WeeklyPlanResponse(**next_week_plan)


@router.get("/plans/can-generate-next-week", response_model=dict)
async def can_generate_next_week(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Verifica se è possibile generare la prossima settimana"""
    from app.config import settings
    
    progressive_service = ProgressiveWorkoutPlanService(db)
    
    # Get current week data
    current_week_data = progressive_service.get_current_week_data(current_user["user_id"])
    
    # Get active plan
    active_plan = db.execute(
        select(WorkoutPlan)
        .where(and_(
            WorkoutPlan.user_id == current_user["user_id"],
            WorkoutPlan.status == "active"
        ))
        .order_by(desc(WorkoutPlan.created_at))
    ).scalar_one_or_none()
    
    if not active_plan:
        return {
            "can_generate": False,
            "reason": "No active plan found",
            "current_week": 1,
            "next_week": 2,
            "next_week_already_generated": False
        }
    
    current_week = current_week_data.get("week_number", 1)
    plan_start = active_plan.start_date
    
    # In mock mode, find the first week that hasn't been generated yet
    if settings.mock_progressive_always_allow_generation:
        # Check all weeks from current_week + 1 to total_weeks
        for week_to_check in range(current_week + 1, active_plan.total_weeks + 1):
            week_start = plan_start + timedelta(weeks=week_to_check - 1)
            week_end = week_start + timedelta(days=6)
            
            existing_workouts = db.execute(
                select(Workout)
                .where(and_(
                    Workout.user_id == current_user["user_id"],
                    Workout.plan_id == active_plan.id,
                    Workout.scheduled_date >= week_start,
                    Workout.scheduled_date <= week_end
                ))
            ).scalars().all()
            
            # Found a week that hasn't been generated yet
            if len(existing_workouts) == 0:
                return {
                    "can_generate": True,
                    "reason": "Mock mode - next ungenerated week found",
                    "current_week": current_week,
                    "next_week": week_to_check,
                    "next_week_already_generated": False,
                    "next_week_workouts_count": 0,
                    "next_week_start_date": week_start.isoformat(),
                    "next_week_end_date": week_end.isoformat()
                }
        
        # All weeks have been generated
        return {
            "can_generate": False,
            "reason": "All weeks already generated",
            "current_week": current_week,
            "next_week": current_week + 1,
            "next_week_already_generated": True,
            "next_week_workouts_count": 0,
            "next_week_start_date": None,
            "next_week_end_date": None
        }
    
    # Normal mode: check only the immediate next week
    next_week = current_week + 1
    
    # Check if next week already has workouts
    next_week_start = plan_start + timedelta(weeks=next_week - 1)
    next_week_end = next_week_start + timedelta(days=6)
    
    existing_workouts = db.execute(
        select(Workout)
        .where(and_(
            Workout.user_id == current_user["user_id"],
            Workout.plan_id == active_plan.id,
            Workout.scheduled_date >= next_week_start,
            Workout.scheduled_date <= next_week_end
        ))
    ).scalars().all()
    
    next_week_already_generated = len(existing_workouts) > 0
    
    return {
        "can_generate": not next_week_already_generated,
        "reason": "Next week already generated" if next_week_already_generated else "Next week not yet generated",
        "current_week": current_week,
        "next_week": next_week,
        "next_week_already_generated": next_week_already_generated,
        "next_week_workouts_count": len(existing_workouts),
        "next_week_start_date": next_week_start.isoformat(),
        "next_week_end_date": next_week_end.isoformat()
    }


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
@limiter.limit("100/hour", key_func=lambda request: f"user:{get_user_id_for_rate_limit(request) or get_remote_address(request)}")
async def generate_ai_workout_plan(ai_request: AIWorkoutPlanRequest,
                                  current_user: dict = Depends(get_current_user),
                                  db: Session = Depends(get_db)):
    """Generate workout plan using AI - supports both traditional and progressive plans"""
    user_id = current_user["user_id"]
    logger.info(f"[API] POST /workouts/plans/generate-ai - user_id: {user_id}")
    
    # Log request details (sanitize sensitive data)
    request_summary = {
        "sport_type": ai_request.sport_type,
        "level": ai_request.level,
        "goal": ai_request.goal,
        "weekly_hours": ai_request.weekly_hours,
        "duration_weeks": ai_request.duration_weeks,
        "is_progressive": ai_request.is_progressive,
        "target_date": ai_request.target_date,
        "start_date": ai_request.start_date,
        "has_user_profile": ai_request.user_profile is not None,
        "has_preferences": ai_request.preferences is not None
    }
    logger.debug(f"[API] Request body: {json.dumps(request_summary, indent=2, default=str)}")
    
    # Check if this is a progressive plan
    if ai_request.is_progressive and ai_request.target_date and ai_request.start_date:
        logger.info(f"[API] Generating PROGRESSIVE workout plan")
        # Generate progressive workout plan
        from app.services.progressive_workout_service import ProgressiveWorkoutPlanService
        
        progressive_service = ProgressiveWorkoutPlanService(db)
        
        # Generate first week of progressive plan
        first_week_plan = progressive_service.generate_weekly_plan(
            user_id=current_user["user_id"],
            week_number=1,
            target_date=ai_request.target_date,
            current_fitness_level=ai_request.user_profile,
            include_stretching=getattr(ai_request, 'include_stretching', False),
            include_strength=getattr(ai_request, 'include_strength', False),
            unavailable_days=getattr(ai_request, 'unavailable_days', None),
            sport_specific_days=getattr(ai_request, 'sport_specific_days', None),
            start_date=ai_request.start_date,
            sport_type=ai_request.sport_type,
            level=ai_request.level,
            goal=ai_request.goal,
            weekly_hours=ai_request.weekly_hours,
            available_equipment=getattr(ai_request, 'available_equipment', None)
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
            "title": plan.title or "",
            "description": plan.description or "",
            "start_date": plan.start_date.isoformat() if plan.start_date else None,
            "end_date": plan.end_date.isoformat() if plan.end_date else None,
            "total_weeks": total_weeks_calculated,
            "goal": plan.goal or "",
            "sport_type": plan.sport_type or "",
            "level": plan.level or "",
            "status": plan.status or "active",
            "created_at": plan.created_at.isoformat() if plan.created_at else None,
            "updated_at": plan.updated_at.isoformat() if plan.updated_at else None
        }
        
        # Ensure first_week_plan has all required fields
        if not isinstance(first_week_plan, dict):
            first_week_plan = {}
        
        result = {
            "plan": plan_dict,
            "first_week": first_week_plan or {},
            "target_date": ai_request.target_date or "",
            "total_weeks": total_weeks_calculated,
            "is_progressive": True,
            "workouts_created": len(workouts) if workouts else 0,
            "calendar_events_created": len(calendar_events) if calendar_events else 0
        }
        logger.info(f"[API] Progressive plan generated successfully - plan_id: {plan_dict.get('id')}, workouts: {len(workouts)}, events: {len(calendar_events)}")
        logger.debug(f"[API] Response summary: plan_id={plan_dict.get('id')}, total_weeks={result.get('total_weeks')}, is_progressive={result.get('is_progressive')}")
        return result
    
    else:
        # Generate traditional workout plan using AI
        logger.info(f"[API] Generating TRADITIONAL workout plan")
        
        # Convert AIWorkoutPlanRequest to WorkoutPlanGenerationRequest
        from app.schemas.ai import WorkoutPlanGenerationRequest
        
        workout_plan_request = WorkoutPlanGenerationRequest(
            sport_type=ai_request.sport_type,
            level=ai_request.level,
            goal=ai_request.goal,
            duration_weeks=ai_request.duration_weeks,
            start_date=ai_request.start_date,
            target_date=ai_request.target_date,
            weekly_hours=ai_request.weekly_hours,
            user_profile=ai_request.user_profile,
            preferences=ai_request.preferences,
            include_stretching=ai_request.include_stretching,
            include_strength=ai_request.include_strength,
            unavailable_days=ai_request.unavailable_days,
            sport_specific_days=ai_request.sport_specific_days
        )
        
        logger.debug(f"[API] Converted to WorkoutPlanGenerationRequest - has_preferences={workout_plan_request.preferences is not None}")
        
        ai_service = AIService(db)
        plan_data = ai_service.generate_workout_plan(
            workout_plan_request,
            user_id=current_user["user_id"],
        )
        
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
            
            result = {
                "plan": plan_dict, 
                "ai_data": plan_data, 
                "is_progressive": False,
                "workouts_created": len(workouts),
                "calendar_events_created": len(calendar_events)
            }
            logger.info(f"[API] Traditional plan generated successfully - plan_id: {plan_dict.get('id')}, workouts: {len(workouts)}, events: {len(calendar_events)}")
            logger.debug(f"[API] Response summary: plan_id={plan_dict.get('id')}, workouts_created={len(workouts)}, is_progressive={result.get('is_progressive')}")
            return result
        
        logger.warning(f"[API] Plan data is empty, returning only AI data")
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
    
    # Send notification for plan updates (only for active plans)
    if plan.status == "active":
        try:
            from app.services.notification_service import NotificationService
            notification_service = NotificationService(db)
            await notification_service.send_notification(
                user_id=current_user["user_id"],
                notification_type="plan_updates",
                title="Piano di allenamento aggiornato",
                body=f"Il tuo piano '{plan.title}' è stato aggiornato",
                data={
                    "plan_id": plan.id,
                    "plan_title": plan.title
                }
            )
        except Exception as e:
            logger.error(f"Error sending plan_updates notification: {e}")
    
    # Add is_progressive field
    plan_dict = WorkoutPlanResponse.model_validate(plan).model_dump()
    plan_dict["is_progressive"] = workout_service._is_progressive_plan(plan)
    return plan_dict


@router.post("/plans/{plan_id}/suspend")
async def suspend_workout_plan(plan_id: int,
                              current_user: dict = Depends(get_current_user),
                              db: Session = Depends(get_db)):
    """Suspend a workout plan"""
    workout_service = WorkoutService(db)
    
    # Get the plan
    plan = workout_service.get_workout_plan(plan_id, current_user["user_id"])
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout plan not found"
        )
    
    # Update status to suspended
    plan.status = "suspended"
    db.commit()
    
    return {
        "message": "Piano sospeso con successo",
        "plan_id": plan.id
    }


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


@router.post("/plans/{plan_id}/restart", response_model=WorkoutPlanResponse)
async def restart_workout_plan(
    plan_id: int,
    start_date: Optional[str] = Query(None, description="New start date (YYYY-MM-DD), defaults to today"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Restart a workout plan - creates a new plan with same structure but resets dates and status.
    """
    user_id = current_user["user_id"]
    workout_service = WorkoutService(db)
    
    # Get original plan
    original_plan = workout_service.get_workout_plan(plan_id, user_id)
    if not original_plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout plan not found"
        )
    
    # Parse start_date or use today
    if start_date:
        try:
            new_start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD"
            )
    else:
        new_start_date = date.today()
    
    # Calculate new end_date
    total_weeks = original_plan.total_weeks
    new_end_date = new_start_date + timedelta(weeks=total_weeks)
    
    # Archive original plan
    original_plan.status = "archived"
    db.commit()
    
    # Create new plan with same title + "(Restart)"
    new_plan = WorkoutPlan(
        user_id=user_id,
        title=f"{original_plan.title} (Restart)",
        description=original_plan.description,
        start_date=new_start_date,
        end_date=new_end_date,
        total_weeks=total_weeks,
        goal=original_plan.goal,
        sport_type=original_plan.sport_type,
        level=original_plan.level,
        status="active"
    )
    
    db.add(new_plan)
    db.flush()  # Get the new plan ID
    
    # Copy workouts from original plan (reset status to scheduled)
    original_workouts = db.query(Workout).filter(
        Workout.plan_id == plan_id,
        Workout.user_id == user_id
    ).all()
    
    for old_workout in original_workouts:
        # Calculate new scheduled_date based on day_number
        if old_workout.day_number:
            new_scheduled_date = new_start_date + timedelta(days=old_workout.day_number - 1)
        else:
            new_scheduled_date = new_start_date
        
        new_workout = Workout(
            user_id=user_id,
            plan_id=new_plan.id,
            title=old_workout.title,
            type=old_workout.type,
            day_number=old_workout.day_number,
            scheduled_date=new_scheduled_date,
            duration_minutes=old_workout.duration_minutes,
            intensity=old_workout.intensity,
            zone=old_workout.zone,
            structure_json=old_workout.structure_json,
            status=WorkoutStatus.SCHEDULED,  # Reset to scheduled
            notes=old_workout.notes
        )
        db.add(new_workout)
    
    # Create calendar events for new workouts
    workout_service.create_calendar_events_from_workouts(
        user_id=user_id,
        workouts=[w for w in db.query(Workout).filter(Workout.plan_id == new_plan.id).all()],
        plan_id=new_plan.id
    )
    
    db.commit()
    db.refresh(new_plan)
    
    logger.info(
        f"[API] Plan {plan_id} restarted as plan {new_plan.id} "
        f"by user {user_id}, start_date: {new_start_date}"
    )
    
    # Add is_progressive field
    plan_dict = WorkoutPlanResponse.model_validate(new_plan).model_dump()
    plan_dict["is_progressive"] = workout_service._is_progressive_plan(new_plan)
    
    return plan_dict


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


@router.get("/skips", response_model=List[dict])
async def get_workout_skips(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    plan_id: Optional[int] = Query(None, description="Filter by plan ID"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get workout skip history for the user."""
    from app.models.workout import WorkoutSkip

    user_id = current_user["user_id"]
    q = db.query(WorkoutSkip).filter(WorkoutSkip.user_id == user_id)
    if plan_id is not None:
        q = q.filter(WorkoutSkip.plan_id == plan_id)
    skips = q.order_by(desc(WorkoutSkip.skipped_at)).offset(skip).limit(limit).all()

    result = []
    for s in skips:
        w = db.query(Workout).filter(Workout.id == s.workout_id).first()
        result.append({
            "id": s.id,
            "workout_id": s.workout_id,
            "workout_title": w.title if w else None,
            "skipped_at": s.skipped_at.isoformat() if s.skipped_at else None,
            "reason": s.reason,
            "plan_id": s.plan_id,
        })
    return result


@router.get("/projections", response_model=dict)
async def get_ctl_atl_projections(
    weeks: int = Query(12, ge=1, le=52, description="Number of weeks to project"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get future CTL/ATL/TSB projections based on active plan."""
    workout_service = WorkoutService(db)
    return workout_service.calculate_future_projections(
        current_user["user_id"], weeks=weeks
    )


@router.get("/recovery", response_model=dict)
async def get_recovery_score(
    days: int = Query(30, ge=1, le=90, description="Number of days to retrieve"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get recovery score with HRV trend (combined HRV, sleep, TSB)."""
    from app.models.daily_metrics import DailyReadinessMetrics, DailyPerformanceMetrics

    user_id = current_user["user_id"]
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    readiness = (
        db.query(DailyReadinessMetrics)
        .filter(
            DailyReadinessMetrics.user_id == user_id,
            DailyReadinessMetrics.metric_date >= start_date,
            DailyReadinessMetrics.metric_date <= end_date,
        )
        .order_by(DailyReadinessMetrics.metric_date.asc())
        .all()
    )
    perf = (
        db.query(DailyPerformanceMetrics)
        .filter(
            DailyPerformanceMetrics.user_id == user_id,
            DailyPerformanceMetrics.metric_date >= start_date,
            DailyPerformanceMetrics.metric_date <= end_date,
        )
        .order_by(DailyPerformanceMetrics.metric_date.asc())
        .all()
    )

    recovery_data = []
    for r in readiness:
        p = next((x for x in perf if x.metric_date == r.metric_date), None)
        hrv_score = None
        if r.hrv_value and r.hrv_baseline and r.hrv_baseline > 0:
            ratio = r.hrv_value / r.hrv_baseline
            hrv_score = min(max(ratio, 0), 2.0) / 2.0
        sleep_score = None
        if r.sleep_hours is not None:
            sleep_score = min(max((r.sleep_hours - 4) / 4, 0), 1.0)
        if r.sleep_quality_score is not None:
            sleep_score = (sleep_score or 0.5) * r.sleep_quality_score
        tsb_score = None
        if p and p.tsb is not None:
            tsb_score = min(max((p.tsb + 30) / 60, 0), 1.0)
        scores, weights = [], []
        if hrv_score is not None:
            scores.append(hrv_score)
            weights.append(0.3)
        if sleep_score is not None:
            scores.append(sleep_score)
            weights.append(0.3)
        if tsb_score is not None:
            scores.append(tsb_score)
            weights.append(0.2)
        if r.recovery_index is not None:
            scores.append(r.recovery_index)
            weights.append(0.2)
        rec = None
        if scores and sum(weights) > 0:
            rec = sum(s * w for s, w in zip(scores, weights)) / sum(weights)
        recovery_data.append({
            "date": r.metric_date.isoformat(),
            "recovery_score": round(rec * 100, 1) if rec is not None else None,
            "hrv": {"value": r.hrv_value, "baseline": r.hrv_baseline, "delta": r.hrv_delta}
            if r.hrv_value else None,
            "sleep": {"hours": r.sleep_hours, "quality": r.sleep_quality_score}
            if r.sleep_hours is not None else None,
            "tsb": round(p.tsb, 1) if p and p.tsb is not None else None,
        })
    recent_hrv = [
        x.hrv_value for x in readiness
        if x.hrv_value and x.metric_date >= end_date - timedelta(days=30)
    ]
    baseline_hrv = sum(recent_hrv) / len(recent_hrv) if recent_hrv else None
    return {
        "recovery_data": recovery_data,
        "baseline_hrv": round(baseline_hrv, 2) if baseline_hrv else None,
        "current_recovery_score": recovery_data[-1]["recovery_score"] if recovery_data else None,
        "days": days,
    }


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


@router.post("/{workout_id}/complete")
async def complete_workout(
    workout_id: int,
    session_data: Optional[dict] = Body(None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark workout as completed and optionally create a workout session"""
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
    
    # Create workout session if session_data is provided
    session = None
    if session_data:
        # Ensure workout_id is set
        session_data['workout_id'] = workout_id
        # Convert datetime string to datetime if needed
        if 'actual_date' in session_data and isinstance(session_data['actual_date'], str):
            from datetime import datetime
            try:
                session_data['actual_date'] = datetime.fromisoformat(session_data['actual_date'].replace('Z', '+00:00'))
            except ValueError:
                # Try parsing without timezone
                session_data['actual_date'] = datetime.fromisoformat(session_data['actual_date'])
        
        session_create = WorkoutSessionCreate(**session_data)
        session = workout_service.create_workout_session(
            user_id=current_user["user_id"],
            session_data=session_create
        )
    
    db.commit()
    db.refresh(workout)
    
    # Send notification for workout completion
    try:
        from app.services.notification_service import NotificationService
        notification_service = NotificationService(db)
        await notification_service.send_notification(
            user_id=current_user["user_id"],
            notification_type="workout_completed",
            title="Allenamento completato!",
            body=f"Hai completato: {workout.title}",
            data={
                "workout_id": workout.id,
                "workout_title": workout.title,
                "completion_date": workout.updated_at.isoformat() if workout.updated_at else None
            }
        )
    except Exception as e:
        # Log error but don't fail the request
        from loguru import logger
        logger.error(f"Error sending workout_completed notification: {e}")
    
    return {
        "id": workout.id,
        "completed": True,
        "completed_at": workout.updated_at.isoformat() if workout.updated_at else None,
        "session_id": session.id if session else None
    }


@router.patch("/{workout_id}/skip")
async def skip_workout(
    workout_id: int,
    reason: Optional[str] = Query(None, description="Optional reason for skipping"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark workout as skipped and record in skip history."""
    from app.models.workout import WorkoutSkip

    workout_service = WorkoutService(db)
    workout = workout_service.get_workout(workout_id, current_user["user_id"])
    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout not found"
        )
    if workout.status != WorkoutStatus.SCHEDULED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot skip workout with status: {workout.status.value}"
        )

    workout.status = WorkoutStatus.SKIPPED
    skip_record = WorkoutSkip(
        user_id=current_user["user_id"],
        workout_id=workout_id,
        reason=reason,
        plan_id=workout.plan_id,
    )
    db.add(skip_record)
    db.commit()
    db.refresh(workout)
    db.refresh(skip_record)

    logger.info(
        f"[API] Workout {workout_id} skipped by user {current_user['user_id']}, "
        f"reason: {reason or 'Not specified'}"
    )

    return {
        "id": workout.id,
        "skipped": True,
        "skipped_at": skip_record.skipped_at.isoformat() if skip_record.skipped_at else None,
        "status": workout.status.value,
        "skip_id": skip_record.id,
    }


@router.patch("/{workout_id}/reschedule")
async def reschedule_workout(
    workout_id: int,
    new_date: str = Query(..., description="New scheduled date (YYYY-MM-DD)"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reschedule workout to a new date (for drag & drop reordering)"""
    workout_service = WorkoutService(db)
    
    # Verify workout exists and belongs to user
    workout = workout_service.get_workout(workout_id, current_user["user_id"])
    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout not found"
        )
    
    # Parse new date
    try:
        new_scheduled_date = datetime.strptime(new_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use YYYY-MM-DD"
        )
    
    # If workout is part of a plan, validate the new date is within plan range
    if workout.plan_id:
        plan = db.query(WorkoutPlan).filter(WorkoutPlan.id == workout.plan_id).first()
        if plan:
            if new_scheduled_date < plan.start_date or new_scheduled_date > plan.end_date:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"New date must be within plan range ({plan.start_date} to {plan.end_date})"
                )
            
            # Recalculate day_number based on plan start date
            days_diff = (new_scheduled_date - plan.start_date).days + 1
            workout.day_number = days_diff
    
    # Update scheduled_date
    old_date = workout.scheduled_date
    workout.scheduled_date = new_scheduled_date
    
    # Update calendar events if they exist
    from app.models.calendar import CalendarEvent
    calendar_events = db.query(CalendarEvent).filter(
        CalendarEvent.workout_id == workout_id
    ).all()
    
    for event in calendar_events:
        # Update event date (keep time if it exists)
        if event.event_date:
            old_datetime = event.event_date
            new_datetime = datetime.combine(new_scheduled_date, old_datetime.time())
            event.event_date = new_datetime
        else:
            event.event_date = datetime.combine(new_scheduled_date, datetime.min.time())
    
    db.commit()
    db.refresh(workout)
    
    logger.info(
        f"[API] Workout {workout_id} rescheduled from {old_date} to {new_scheduled_date} "
        f"by user {current_user['user_id']}"
    )
    
    return {
        "id": workout.id,
        "scheduled_date": workout.scheduled_date.isoformat(),
        "day_number": workout.day_number,
        "calendar_events_updated": len(calendar_events)
    }


@router.get("/{workout_id}/watch-format", response_model=WatchWorkoutFormatResponse)
async def get_workout_watch_format(
    workout_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get workout formatted for Apple Watch.
    
    Returns workout structure and zones in WatchOS-compatible format.
    """
    from app.models.user import UserProfile
    
    # Get workout
    workout = db.execute(
        select(Workout)
        .where(
            and_(
                Workout.id == workout_id,
                Workout.user_id == current_user["user_id"]
            )
        )
    ).scalar_one_or_none()
    
    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout not found"
        )
    
    # Get user profile
    profile = db.execute(
        select(UserProfile)
        .where(UserProfile.user_id == current_user["user_id"])
    ).scalar_one_or_none()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found"
        )
    
    # Format workout for watch
    service = HealthKitService(db)
    watch_format = service.format_workout_for_watch(workout, profile)
    
    return WatchWorkoutFormatResponse(**watch_format)


@router.post("/sessions/from-watch", response_model=WatchSessionCreateResponse)
async def create_session_from_watch(
    request: WatchSessionCreateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create WorkoutSession from Apple Watch.
    
    Creates a workout session with data recorded on Apple Watch.
    Links to HealthKit workout if healthkit_uuid is provided.
    """
    from app.models.healthkit import HealthKitWorkout
    
    service = HealthKitService(db)
    
    # Verify workout exists and belongs to user
    workout = db.execute(
        select(Workout)
        .where(
            and_(
                Workout.id == request.workout_id,
                Workout.user_id == current_user["user_id"]
            )
        )
    ).scalar_one_or_none()
    
    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout not found"
        )
    
    # Find HealthKit workout if UUID provided
    healthkit_workout = None
    if request.healthkit_uuid:
        healthkit_workout = db.execute(
            select(HealthKitWorkout)
            .where(
                and_(
                    HealthKitWorkout.hk_workout_uuid == request.healthkit_uuid,
                    HealthKitWorkout.user_id == current_user["user_id"]
                )
            )
        ).scalar_one_or_none()
    
    # Create session
    duration_minutes = request.duration_seconds // 60
    
    session = WorkoutSession(
        workout_id=request.workout_id,
        user_id=current_user["user_id"],
        actual_date=request.start_time,
        duration_minutes=duration_minutes,
        avg_hr=request.metrics.get("avg_heart_rate"),
        max_hr=request.metrics.get("max_heart_rate"),
        avg_pace=service._convert_pace_to_min_per_km(request.metrics.get("avg_pace_seconds_per_km")),
        avg_power=request.metrics.get("avg_power")
    )
    
    db.add(session)
    
    # Calculate metrics
    try:
        service._calculate_and_store_metrics_for_session(session)
    except Exception as e:
        logger.warning(f"[HEALTHKIT] Failed to calculate metrics for watch session: {e}")
    
    # Update workout status
    workout.status = "completed"
    
    db.commit()
    db.refresh(session)
    
    return WatchSessionCreateResponse(
        success=True,
        session_id=session.id,
        matched=True,
        workout_matched_id=request.workout_id
    )


# Export Workout to FIT/TCX
@router.get("/{workout_id}/export")
async def export_workout(
    workout_id: int,
    format: str = Query(..., pattern="^(fit|tcx)$", description="Export format: fit or tcx"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export workout to FIT or TCX format for Garmin, Zwift, etc.
    """
    from app.utils.fit_tcx_export import export_to_tcx, export_to_fit
    from app.services.profile_service import ProfileService
    
    # Get workout
    workout = db.execute(
        select(Workout)
        .where(
            and_(
                Workout.id == workout_id,
                Workout.user_id == current_user["user_id"]
            )
        )
    ).scalar_one_or_none()
    
    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout not found"
        )
    
    # Get user profile for zones
    profile_service = ProfileService(db)
    user_profile = profile_service.get_user_profile(current_user["user_id"])
    
    # Prepare workout data
    workout_data = {
        "id": workout.id,
        "title": workout.title,
        "sport_type": workout.plan.sport_type if workout.plan else "run",
        "duration_minutes": workout.duration_minutes,
        "intensity": workout.intensity,
        "zone": workout.zone,
        "structure_json": workout.structure_json,
    }
    
    # Export based on format
    if format == "tcx":
        file_content = export_to_tcx(workout_data, user_profile)
        filename = f"workout_{workout_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.tcx"
        media_type = "application/xml"
    elif format == "fit":
        file_content = export_to_fit(workout_data, user_profile)
        filename = f"workout_{workout_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.fit"
        media_type = "application/octet-stream"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid format. Use 'fit' or 'tcx'"
        )
    
    logger.info(f"[API] Exported workout {workout_id} to {format.upper()} format")
    
    return Response(
        content=file_content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


# Import Workout from FIT/TCX/GPX
@router.post("/import")
async def import_workout(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Import workout from FIT, TCX, or GPX file.
    Creates a WorkoutSession or matches with existing workout.
    """
    from fitparse import FitFile
    import gpxpy
    import xml.etree.ElementTree as ET
    
    user_id = current_user["user_id"]
    workout_service = WorkoutService(db)
    
    # Determine file type from extension
    filename = file.filename or "workout"
    file_ext = filename.lower().split('.')[-1] if '.' in filename else ''
    
    # Read file content
    file_content = await file.read()
    
    try:
        if file_ext == 'fit':
            # Parse FIT file
            fitfile = FitFile(file_content)
            
            # Extract workout data from FIT
            workout_data = {
                "sport_type": "run",  # Default, will be updated from FIT data
                "duration_seconds": 0,
                "distance_meters": 0,
                "avg_hr": None,
                "max_hr": None,
                "avg_power": None,
                "max_power": None,
                "start_time": None,
            }
            
            for record in fitfile.get_messages():
                if record.name == 'file_id':
                    for field in record:
                        if field.name == 'type' and field.value == 4:  # Activity file
                            pass
                
                if record.name == 'session':
                    for field in record:
                        if field.name == 'sport':
                            sport_map = {0: 'run', 1: 'bike', 2: 'swim'}
                            workout_data["sport_type"] = sport_map.get(field.value, 'run')
                        elif field.name == 'total_elapsed_time':
                            workout_data["duration_seconds"] = field.value
                        elif field.name == 'total_distance':
                            workout_data["distance_meters"] = field.value
                        elif field.name == 'avg_heart_rate':
                            workout_data["avg_hr"] = field.value
                        elif field.name == 'max_heart_rate':
                            workout_data["max_hr"] = field.value
                        elif field.name == 'avg_power':
                            workout_data["avg_power"] = field.value
                        elif field.name == 'max_power':
                            workout_data["max_power"] = field.value
                        elif field.name == 'timestamp':
                            workout_data["start_time"] = field.value
            
            # Create workout session
            if workout_data["start_time"]:
                actual_date = workout_data["start_time"]
            else:
                actual_date = datetime.now()
            
            duration_minutes = workout_data["duration_seconds"] // 60
            
            # Try to match with existing workout
            scheduled_date = actual_date.date() if isinstance(actual_date, datetime) else date.today()
            existing_workout = db.query(Workout).filter(
                Workout.user_id == user_id,
                Workout.scheduled_date == scheduled_date,
                Workout.status == WorkoutStatus.SCHEDULED
            ).first()
            
            if existing_workout:
                # Create session for existing workout
                session = WorkoutSession(
                    workout_id=existing_workout.id,
                    user_id=user_id,
                    actual_date=actual_date if isinstance(actual_date, datetime) else datetime.combine(scheduled_date, datetime.min.time()),
                    duration_minutes=duration_minutes,
                    avg_hr=workout_data.get("avg_hr"),
                    max_hr=workout_data.get("max_hr"),
                    avg_power=workout_data.get("avg_power"),
                    notes=f"Imported from FIT file: {filename}"
                )
                db.add(session)
                existing_workout.status = WorkoutStatus.COMPLETED
                db.commit()
                db.refresh(session)
                
                return {
                    "message": "Workout imported and matched to existing workout",
                    "workout_id": existing_workout.id,
                    "session_id": session.id,
                    "matched": True
                }
            else:
                # Create standalone session (no workout match)
                session = WorkoutSession(
                    workout_id=None,  # No workout match
                    user_id=user_id,
                    actual_date=actual_date if isinstance(actual_date, datetime) else datetime.combine(scheduled_date, datetime.min.time()),
                    duration_minutes=duration_minutes,
                    avg_hr=workout_data.get("avg_hr"),
                    max_hr=workout_data.get("max_hr"),
                    avg_power=workout_data.get("avg_power"),
                    notes=f"Imported from FIT file: {filename}"
                )
                db.add(session)
                db.commit()
                db.refresh(session)
                
                return {
                    "message": "Workout imported as standalone session",
                    "session_id": session.id,
                    "matched": False
                }
        
        elif file_ext == 'tcx':
            # Parse TCX file
            root = ET.fromstring(file_content)
            
            # Extract data from TCX
            workout_data = {
                "sport_type": "run",
                "duration_seconds": 0,
                "distance_meters": 0,
                "avg_hr": None,
                "start_time": None,
            }
            
            # Parse TCX structure
            activities = root.find("{http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2}Activities")
            if activities is not None:
                activity = activities.find("{http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2}Activity")
                if activity is not None:
                    sport = activity.get("Sport", "Running")
                    workout_data["sport_type"] = sport.lower()
                    
                    activity_id = activity.find("{http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2}Id")
                    if activity_id is not None and activity_id.text:
                        try:
                            workout_data["start_time"] = datetime.fromisoformat(activity_id.text.replace('Z', '+00:00'))
                        except:
                            workout_data["start_time"] = datetime.now()
                    
                    lap = activity.find("{http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2}Lap")
                    if lap is not None:
                        total_time = lap.find("{http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2}TotalTimeSeconds")
                        if total_time is not None and total_time.text:
                            workout_data["duration_seconds"] = int(float(total_time.text))
                        
                        distance = lap.find("{http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2}DistanceMeters")
                        if distance is not None and distance.text:
                            workout_data["distance_meters"] = float(distance.text)
                        
                        avg_hr_elem = lap.find("{http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2}AverageHeartRateBpm")
                        if avg_hr_elem is not None:
                            value = avg_hr_elem.find("{http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2}Value")
                            if value is not None and value.text:
                                workout_data["avg_hr"] = int(float(value.text))
            
            # Create session (similar to FIT)
            actual_date = workout_data.get("start_time") or datetime.now()
            duration_minutes = workout_data["duration_seconds"] // 60
            scheduled_date = actual_date.date() if isinstance(actual_date, datetime) else date.today()
            
            existing_workout = db.query(Workout).filter(
                Workout.user_id == user_id,
                Workout.scheduled_date == scheduled_date,
                Workout.status == WorkoutStatus.SCHEDULED
            ).first()
            
            if existing_workout:
                session = WorkoutSession(
                    workout_id=existing_workout.id,
                    user_id=user_id,
                    actual_date=actual_date if isinstance(actual_date, datetime) else datetime.combine(scheduled_date, datetime.min.time()),
                    duration_minutes=duration_minutes,
                    avg_hr=workout_data.get("avg_hr"),
                    notes=f"Imported from TCX file: {filename}"
                )
                db.add(session)
                existing_workout.status = WorkoutStatus.COMPLETED
                db.commit()
                db.refresh(session)
                
                return {
                    "message": "Workout imported and matched to existing workout",
                    "workout_id": existing_workout.id,
                    "session_id": session.id,
                    "matched": True
                }
            else:
                session = WorkoutSession(
                    workout_id=None,
                    user_id=user_id,
                    actual_date=actual_date if isinstance(actual_date, datetime) else datetime.combine(scheduled_date, datetime.min.time()),
                    duration_minutes=duration_minutes,
                    avg_hr=workout_data.get("avg_hr"),
                    notes=f"Imported from TCX file: {filename}"
                )
                db.add(session)
                db.commit()
                db.refresh(session)
                
                return {
                    "message": "Workout imported as standalone session",
                    "session_id": session.id,
                    "matched": False
                }
        
        elif file_ext == 'gpx':
            # Parse GPX file
            gpx = gpxpy.parse(file_content.decode('utf-8'))
            
            # Extract data from GPX
            workout_data = {
                "sport_type": "run",
                "duration_seconds": 0,
                "distance_meters": 0,
                "avg_hr": None,
                "start_time": None,
            }
            
            total_time = 0
            total_distance = 0
            points_with_hr = []
            start_time = None
            
            for track in gpx.tracks:
                for segment in track.segments:
                    for i, point in enumerate(segment.points):
                        if point.time:
                            if not start_time:
                                start_time = point.time
                                workout_data["start_time"] = point.time
                            total_time = (point.time - start_time).total_seconds()
                        
                        # Try to extract HR from extensions (if present)
                        if hasattr(point, 'extensions') and point.extensions:
                            try:
                                # GPX extensions can be complex, try to find HR
                                for ext in point.extensions:
                                    if hasattr(ext, 'tag') and 'hr' in ext.tag.lower():
                                        if hasattr(ext, 'text') and ext.text:
                                            points_with_hr.append(int(float(ext.text)))
                            except:
                                pass
                        
                        if i > 0:
                            prev_point = segment.points[i - 1]
                            total_distance += point.distance_2d(prev_point)
            
            workout_data["duration_seconds"] = int(total_time) if total_time > 0 else 0
            workout_data["distance_meters"] = total_distance
            workout_data["avg_hr"] = int(sum(points_with_hr) / len(points_with_hr)) if points_with_hr else None
            
            # Create session
            actual_date = workout_data.get("start_time") or datetime.now()
            duration_minutes = workout_data["duration_seconds"] // 60
            scheduled_date = actual_date.date() if isinstance(actual_date, datetime) else date.today()
            
            existing_workout = db.query(Workout).filter(
                Workout.user_id == user_id,
                Workout.scheduled_date == scheduled_date,
                Workout.status == WorkoutStatus.SCHEDULED
            ).first()
            
            if existing_workout:
                session = WorkoutSession(
                    workout_id=existing_workout.id,
                    user_id=user_id,
                    actual_date=actual_date if isinstance(actual_date, datetime) else datetime.combine(scheduled_date, datetime.min.time()),
                    duration_minutes=duration_minutes,
                    avg_hr=workout_data.get("avg_hr"),
                    notes=f"Imported from GPX file: {filename}"
                )
                db.add(session)
                existing_workout.status = WorkoutStatus.COMPLETED
                db.commit()
                db.refresh(session)
                
                return {
                    "message": "Workout imported and matched to existing workout",
                    "workout_id": existing_workout.id,
                    "session_id": session.id,
                    "matched": True
                }
            else:
                session = WorkoutSession(
                    workout_id=None,
                    user_id=user_id,
                    actual_date=actual_date if isinstance(actual_date, datetime) else datetime.combine(scheduled_date, datetime.min.time()),
                    duration_minutes=duration_minutes,
                    avg_hr=workout_data.get("avg_hr"),
                    notes=f"Imported from GPX file: {filename}"
                )
                db.add(session)
                db.commit()
                db.refresh(session)
                
                return {
                    "message": "Workout imported as standalone session",
                    "session_id": session.id,
                    "matched": False
                }
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format: {file_ext}. Supported formats: fit, tcx, gpx"
            )
    
    except Exception as e:
        logger.error(f"[API] Error importing workout file: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error parsing file: {str(e)}"
        )


# Daily Suggested Workout
@router.get("/suggested", response_model=dict)
async def get_suggested_workout(
    target_date: Optional[str] = Query(None, description="Target date (YYYY-MM-DD), defaults to today"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get suggested workout for today based on readiness metrics, CTL/ATL/TSB, HRV, sleep, and active plan.
    """
    user_id = current_user["user_id"]
    workout_service = WorkoutService(db)
    
    # Parse target_date if provided
    parsed_date = None
    if target_date:
        try:
            parsed_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD"
            )
    
    suggestion = workout_service.get_suggested_workout(user_id, parsed_date)
    
    if suggestion is None:
        return {
            "workout": None,
            "suggestion": "none",
            "reason": "Nessun suggerimento disponibile",
            "metrics": {}
        }
    
    return suggestion


@router.post("/suggested/accept")
async def accept_suggested_workout(
    target_date: Optional[str] = Query(None, description="Target date (YYYY-MM-DD), defaults to today"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Accept the suggested workout for today. If it's a scheduled workout, marks it as accepted.
    If it's a generated suggestion, creates an instant workout.
    """
    user_id = current_user["user_id"]
    workout_service = WorkoutService(db)
    
    # Parse target_date if provided
    parsed_date = None
    if target_date:
        try:
            parsed_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD"
            )
    else:
        parsed_date = date.today()
    
    suggestion = workout_service.get_suggested_workout(user_id, parsed_date)
    
    if not suggestion or not suggestion.get("workout"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No suggested workout found for this date"
        )
    
    workout_data = suggestion["workout"]
    
    # If it's a scheduled workout, just return it (user can start it)
    if workout_data.get("id"):
        return {
            "message": "Workout accettato",
            "workout_id": workout_data["id"],
            "action": "start_scheduled"
        }
    
    # If it's a generated suggestion, create an instant workout
    if workout_data.get("is_suggested"):
        from app.services.ai_service import AIService
        from app.services.profile_service import ProfileService
        
        ai_service = AIService(db)
        profile_service = ProfileService(db)
        user_profile = profile_service.get_user_profile(user_id)
        
        try:
            # Generate workout structure using AI
            workout_structure = await ai_service.generate_single_workout(
                sport_type=workout_data.get("sport_type", "run"),
                duration_minutes=workout_data.get("duration_minutes", 60),
                intensity=workout_data.get("intensity", "moderate"),
                goal=None,
                zone=workout_data.get("zone", "Z2"),
                user_profile=user_profile
            )
            
            # Create workout
            workout = Workout(
                user_id=user_id,
                plan_id=None,  # Standalone workout
                title=workout_data.get("title", "Workout Suggerito"),
                type=workout_data.get("type", "endurance"),
                scheduled_date=parsed_date,
                duration_minutes=workout_data.get("duration_minutes", 60),
                intensity=workout_data.get("intensity", "moderate"),
                zone=workout_data.get("zone", "Z2"),
                structure_json=workout_structure.get("structure"),
                status=WorkoutStatus.SCHEDULED,
                notes="Workout generato da suggerimento giornaliero"
            )
            
            db.add(workout)
            db.commit()
            db.refresh(workout)
            
            logger.info(f"[API] Accepted suggested workout created: workout_id={workout.id}")
            
            return {
                "message": "Workout accettato e creato",
                "workout_id": workout.id,
                "action": "created"
            }
        except Exception as e:
            logger.error(f"[API] Error creating accepted suggested workout: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Errore nella creazione del workout: {str(e)}"
            )
    
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Unable to accept this suggestion"
    )


@router.post("/suggested/reject")
async def reject_suggested_workout(
    target_date: Optional[str] = Query(None, description="Target date (YYYY-MM-DD), defaults to today"),
    reason: Optional[str] = Query(None, description="Reason for rejection"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Reject the suggested workout for today. This logs the rejection for future learning.
    """
    user_id = current_user["user_id"]
    
    # Parse target_date if provided
    parsed_date = None
    if target_date:
        try:
            parsed_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD"
            )
    else:
        parsed_date = date.today()
    
    # Log rejection (could be stored in a table for future ML improvements)
    logger.info(
        f"[API] User {user_id} rejected suggested workout for {parsed_date}. "
        f"Reason: {reason or 'Not specified'}"
    )
    
    # TODO: Store rejection in database for future learning
    # For now, just log it
    
    return {
        "message": "Suggerimento rifiutato",
        "date": parsed_date.isoformat(),
        "reason": reason
    }


# Instant Workout (TrainNow)
@router.post("/instant", response_model=dict)
@limiter.limit("10/hour", key_func=lambda request: f"user:{get_user_id_for_rate_limit(request) or get_remote_address(request)}")
async def create_instant_workout(
    request: Request,
    instant_request: InstantWorkoutRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate instant workout on-demand (TrainNow feature).
    Creates a standalone workout without a plan.
    """
    user_id = current_user["user_id"]
    logger.info(f"[API] POST /workouts/instant - user_id: {user_id}, sport: {instant_request.sport_type}, duration: {instant_request.duration_minutes}")
    
    workout_service = WorkoutService(db)
    ai_service = AIService(db)
    
    # Get user profile for context
    from app.services.profile_service import ProfileService
    profile_service = ProfileService(db)
    user_profile = profile_service.get_user_profile(user_id)
    
    # Generate workout using AI
    try:
        # Use AI service to generate workout structure
        workout_data = await ai_service.generate_single_workout(
            sport_type=instant_request.sport_type,
            duration_minutes=instant_request.duration_minutes,
            intensity=instant_request.intensity or "moderate",
            goal=instant_request.goal,
            zone=instant_request.zone,
            user_profile=user_profile
        )
        
        # Create workout (standalone, no plan_id)
        workout = Workout(
            user_id=user_id,
            plan_id=None,  # Standalone workout
            title=workout_data.get("title", f"{instant_request.sport_type.capitalize()} Workout"),
            type=workout_data.get("type", "endurance"),
            scheduled_date=date.today(),  # Today
            duration_minutes=instant_request.duration_minutes,
            intensity=instant_request.intensity or "moderate",
            zone=instant_request.zone or workout_data.get("zone", "Z2"),
            structure_json=workout_data.get("structure"),
            status=WorkoutStatus.SCHEDULED,
            notes=f"Instant workout generated on-demand"
        )
        
        db.add(workout)
        db.commit()
        db.refresh(workout)
        
        logger.info(f"[API] Instant workout created: workout_id={workout.id}")
        
        return {
            "workout": {
                "id": workout.id,
                "title": workout.title,
                "type": workout.type,
                "sport_type": instant_request.sport_type,
                "duration_minutes": workout.duration_minutes,
                "intensity": workout.intensity,
                "zone": workout.zone,
                "structure_json": workout.structure_json,
                "scheduled_date": workout.scheduled_date.isoformat() if workout.scheduled_date else None,
                "status": workout.status.value,
                "is_instant": True
            },
            "message": "Workout generato con successo"
        }
        
    except Exception as e:
        logger.error(f"[API] Error generating instant workout: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore nella generazione del workout: {str(e)}"
        )
