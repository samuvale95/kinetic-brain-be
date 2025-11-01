from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, select, or_
from typing import Dict, Any, List
from datetime import date, datetime, timedelta
from app.database import get_db
from app.models.workout import Workout, WorkoutSession, WorkoutPlan
from app.models.calendar import CalendarEvent
from app.api.auth import get_current_user

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.options("/stats")
async def options_dashboard_stats():
    """Handle OPTIONS request for CORS preflight"""
    return Response(status_code=200)


@router.options("/progress")
async def options_dashboard_progress():
    """Handle OPTIONS request for CORS preflight"""
    return Response(status_code=200)


@router.options("/upcoming")
async def options_dashboard_upcoming():
    """Handle OPTIONS request for CORS preflight"""
    return Response(status_code=200)


@router.options("/calendar-events")
async def options_dashboard_calendar_events():
    """Handle OPTIONS request for CORS preflight"""
    return Response(status_code=200)


@router.options("/today-workouts")
async def options_today_workouts():
    """Handle OPTIONS request for CORS preflight"""
    return Response(status_code=200)


@router.get("/today-workouts")
async def get_today_workouts(current_user: dict = Depends(get_current_user),
                             db: Session = Depends(get_db)):
    """Get today's scheduled workouts from active plans and standalone workouts"""
    user_id = current_user["user_id"]
    today = date.today()
    
    # Get workouts from active plans
    workouts_from_active_plans = db.execute(
        select(Workout)
        .join(WorkoutPlan, Workout.plan_id == WorkoutPlan.id)
        .where(
            and_(
                Workout.user_id == user_id,
                WorkoutPlan.user_id == user_id,
                WorkoutPlan.status == "active",
                Workout.scheduled_date == today,
                Workout.status.in_(["scheduled", "completed"])
            )
        )
    ).scalars().all()
    
    # Get standalone workouts (without plan_id)
    standalone_workouts = db.execute(
        select(Workout)
        .where(
            and_(
                Workout.user_id == user_id,
                Workout.plan_id.is_(None),
                Workout.scheduled_date == today,
                Workout.status.in_(["scheduled", "completed"])
            )
        )
    ).scalars().all()
    
    # Combine both lists
    workouts = list(workouts_from_active_plans) + list(standalone_workouts)
    
    # Sort by scheduled_date and duration
    workouts.sort(key=lambda w: (w.scheduled_date or date.min, w.duration_minutes or 0))
    
    # Deduplicate workouts: if multiple workouts have the same scheduled_date and similar type,
    # prefer completed workouts, then keep the one with the most recent creation date
    seen_workouts = {}
    deduplicated_workouts = []
    
    for workout in workouts:
        # Create a key based on scheduled_date and type similarity
        key = f"{workout.scheduled_date}-{workout.type.lower()}"
        
        if key not in seen_workouts:
            seen_workouts[key] = workout
            deduplicated_workouts.append(workout)
        else:
            # If we already have a workout for this date/type, decide which one to keep
            existing_workout = seen_workouts[key]
            
            # Prefer completed workouts if they exist
            if workout.status == "completed" and existing_workout.status != "completed":
                # Replace with completed workout
                index = deduplicated_workouts.index(existing_workout)
                deduplicated_workouts[index] = workout
                seen_workouts[key] = workout
            # If workout is more recent than existing one and both have same status
            elif workout.created_at and existing_workout.created_at and workout.created_at > existing_workout.created_at:
                index = deduplicated_workouts.index(existing_workout)
                deduplicated_workouts[index] = workout
                seen_workouts[key] = workout
    
    # Format response
    result = []
    for workout in deduplicated_workouts:
        # Determine emoji based on type
        emoji_map = {
            "run": "🏃",
            "ride": "🚴", 
            "swim": "🏊",
            "strength": "💪",
            "rest": "😴",
            "yoga": "🧘"
        }
        
        emoji = emoji_map.get(workout.type.lower(), "🏃")
        
        # Check if completed
        completed = workout.status == "completed"
        
        result.append({
            "id": workout.id,
            "title": workout.title,
            "duration": f"{workout.duration_minutes} min",
            "zone": workout.zone or "Z2",
            "emoji": emoji,
            "type": workout.type,
            "scheduled_date": workout.scheduled_date.isoformat() if workout.scheduled_date else None,
            "completed": completed
        })
    
    return result


@router.get("/stats")
async def get_dashboard_stats(current_user: dict = Depends(get_current_user),
                             db: Session = Depends(get_db)):
    """Get dashboard statistics"""
    from app.models.strava import StravaActivity
    from app.models.user import UserProfile
    
    user_id = current_user["user_id"]
    
    # Total workouts completed
    total_workouts = db.query(Workout).filter(
        and_(Workout.user_id == user_id, Workout.status == "completed")
    ).count()
    
    # Total completed workouts (all time)
    completed_workouts = db.query(Workout).filter(
        and_(Workout.user_id == user_id, Workout.status == "completed")
    ).count()
    
    # Workouts this week
    week_start = date.today() - timedelta(days=date.today().weekday())
    week_end = week_start + timedelta(days=6)
    
    workouts_this_week = db.query(Workout).filter(
        and_(
            Workout.user_id == user_id,
            Workout.scheduled_date >= week_start,
            Workout.scheduled_date <= week_end,
            Workout.status == "completed"
        )
    ).count()
    
    # Total training time this month
    month_start = date.today().replace(day=1)
    month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    
    total_duration = db.query(func.sum(WorkoutSession.duration_minutes)).filter(
        and_(
            WorkoutSession.user_id == user_id,
            WorkoutSession.actual_date >= month_start,
            WorkoutSession.actual_date <= month_end
        )
    ).scalar() or 0
    
    # Active workout plans
    active_plans = db.query(WorkoutPlan).filter(
        and_(
            WorkoutPlan.user_id == user_id,
            WorkoutPlan.status == "active"
        )
    ).count()
    
    # Upcoming workouts (next 7 days)
    upcoming_workouts = db.query(Workout).filter(
        and_(
            Workout.user_id == user_id,
            Workout.scheduled_date >= date.today(),
            Workout.scheduled_date <= date.today() + timedelta(days=7),
            Workout.status == "scheduled"
        )
    ).count()
    
    # Calculate average heart rate from sessions
    avg_heart_rate = db.query(func.avg(WorkoutSession.avg_hr)).filter(
        WorkoutSession.user_id == user_id
    ).scalar()
    avg_heart_rate = round(avg_heart_rate, 0) if avg_heart_rate else None
    
    # Calculate total distance from Strava activities
    total_distance = db.query(func.sum(StravaActivity.distance)).join(
        Workout, StravaActivity.workout_id == Workout.id
    ).filter(
        Workout.user_id == user_id
    ).scalar() or 0
    
    return {
        "total_workouts": total_workouts,
        "workouts_this_week": workouts_this_week,
        "total_training_time_minutes": total_duration,
        "total_training_time_hours": round(total_duration / 60, 1),
        "active_plans": active_plans,
        "upcoming_workouts": upcoming_workouts,
        "completed_workouts": completed_workouts,
        "avg_heart_rate": int(avg_heart_rate) if avg_heart_rate else None,
        "total_distance": int(total_distance)
    }


@router.get("/upcoming")
async def get_upcoming_workouts(current_user: dict = Depends(get_current_user),
                               db: Session = Depends(get_db)):
    """Get upcoming workouts for the next 7 days, excluding inactive plans"""
    user_id = current_user["user_id"]
    end_date = date.today() + timedelta(days=7)
    
    # Get workout IDs from inactive plans
    inactive_plan_workout_ids = db.execute(
        select(Workout.id)
        .join(WorkoutPlan, Workout.plan_id == WorkoutPlan.id)
        .where(
            and_(
                WorkoutPlan.user_id == user_id,
                WorkoutPlan.status != "active"
            )
        )
    ).scalars().all()
    inactive_plan_workout_ids = set(inactive_plan_workout_ids)
    
    workouts = db.query(Workout).filter(
        and_(
            Workout.user_id == user_id,
            Workout.scheduled_date >= date.today(),
            Workout.scheduled_date <= end_date,
            Workout.status == "scheduled"
        )
    ).order_by(Workout.scheduled_date).all()
    
    # Filter out workouts from inactive plans
    filtered_workouts = [w for w in workouts if w.id not in inactive_plan_workout_ids]
    
    return filtered_workouts


@router.get("/progress")
async def get_progress_data(current_user: dict = Depends(get_current_user),
                           db: Session = Depends(get_db)):
    """Get progress data for charts"""
    user_id = current_user["user_id"]
    
    # Last 12 weeks of data
    end_date = date.today()
    start_date = end_date - timedelta(weeks=12)
    
    # Weekly workout counts
    weekly_data = []
    for i in range(12):
        week_start = start_date + timedelta(weeks=i)
        week_end = week_start + timedelta(days=6)
        
        workout_count = db.query(Workout).filter(
            and_(
                Workout.user_id == user_id,
                Workout.scheduled_date >= week_start,
                Workout.scheduled_date <= week_end,
                Workout.status == "completed"
            )
        ).count()
        
        # Total duration for the week
        total_duration = db.query(func.sum(WorkoutSession.duration_minutes)).filter(
            and_(
                WorkoutSession.user_id == user_id,
                WorkoutSession.actual_date >= week_start,
                WorkoutSession.actual_date <= week_end
            )
        ).scalar() or 0
        
        weekly_data.append({
            "week": week_start.isoformat(),
            "workouts": workout_count,
            "duration_minutes": total_duration,
            "duration_hours": round(total_duration / 60, 1)
        })
    
    # Recent performance metrics (last 10 workouts)
    recent_sessions = db.query(WorkoutSession).filter(
        WorkoutSession.user_id == user_id
    ).order_by(WorkoutSession.actual_date.desc()).limit(10).all()
    
    performance_data = []
    for session in recent_sessions:
        performance_data.append({
            "date": session.actual_date.isoformat(),
            "duration_minutes": session.duration_minutes,
            "avg_hr": session.avg_hr,
            "max_hr": session.max_hr,
            "avg_pace": session.avg_pace,
            "avg_power": session.avg_power,
            "perceived_exertion": session.perceived_exertion
        })
    
    return {
        "weekly_data": weekly_data,
        "recent_performance": performance_data
    }


@router.get("/calendar-events")
async def get_dashboard_calendar_events(current_user: dict = Depends(get_current_user),
                                       db: Session = Depends(get_db)):
    """Get calendar events for dashboard, excluding inactive plans"""
    from app.models.workout import Workout, WorkoutPlan
    from app.services.workout_service import WorkoutService
    
    user_id = current_user["user_id"]
    start_date = date.today()
    end_date = start_date + timedelta(days=30)  # Next 30 days
    
    # Use the workout service method which already filters inactive plans
    workout_service = WorkoutService(db)
    events = workout_service.get_calendar_events(user_id, start_date, end_date)
    
    return events
