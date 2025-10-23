from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import Dict, Any, List
from datetime import date, datetime, timedelta
from app.database import get_db
from app.models.workout import Workout, WorkoutSession, WorkoutPlan
from app.models.calendar import CalendarEvent
from app.api.auth import get_current_user

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
async def get_dashboard_stats(current_user: dict = Depends(get_current_user),
                             db: Session = Depends(get_db)):
    """Get dashboard statistics"""
    user_id = current_user["user_id"]
    
    # Total workouts completed
    total_workouts = db.query(Workout).filter(
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
    
    return {
        "total_workouts": total_workouts,
        "workouts_this_week": workouts_this_week,
        "total_training_time_minutes": total_duration,
        "total_training_time_hours": round(total_duration / 60, 1),
        "active_plans": active_plans,
        "upcoming_workouts": upcoming_workouts
    }


@router.get("/upcoming")
async def get_upcoming_workouts(current_user: dict = Depends(get_current_user),
                               db: Session = Depends(get_db)):
    """Get upcoming workouts for the next 7 days"""
    user_id = current_user["user_id"]
    end_date = date.today() + timedelta(days=7)
    
    workouts = db.query(Workout).filter(
        and_(
            Workout.user_id == user_id,
            Workout.scheduled_date >= date.today(),
            Workout.scheduled_date <= end_date,
            Workout.status == "scheduled"
        )
    ).order_by(Workout.scheduled_date).all()
    
    return workouts


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
    """Get calendar events for dashboard"""
    user_id = current_user["user_id"]
    start_date = date.today()
    end_date = start_date + timedelta(days=30)  # Next 30 days
    
    events = db.query(CalendarEvent).filter(
        and_(
            CalendarEvent.user_id == user_id,
            CalendarEvent.scheduled_date >= start_date,
            CalendarEvent.scheduled_date <= end_date
        )
    ).order_by(CalendarEvent.scheduled_date).all()
    
    return events
