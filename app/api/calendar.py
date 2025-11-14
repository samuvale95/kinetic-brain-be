from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_
from typing import List, Optional
from datetime import date, datetime
from app.database import get_db
from app.schemas.calendar import (
    CalendarEventCreate, CalendarEventUpdate, CalendarEventResponse,
    DragDropRequest, CalendarMonthRequest
)
from app.models.workout import Workout, WorkoutPlan, WorkoutSession
from app.services.workout_service import WorkoutService
from app.api.auth import get_current_user

router = APIRouter(prefix="/calendar", tags=["calendar"])


# OPTIONS endpoints for CORS preflight
@router.options("/")
async def options_calendar():
    """Handle OPTIONS request for CORS preflight"""
    return Response(status_code=200)


@router.options("/events")
async def options_calendar_events():
    """Handle OPTIONS request for CORS preflight"""
    return Response(status_code=200)


@router.get("/", response_model=List[CalendarEventResponse])
async def get_calendar_events(start_date: Optional[date] = Query(None),
                             end_date: Optional[date] = Query(None),
                             current_user: dict = Depends(get_current_user),
                             db: Session = Depends(get_db)):
    """Get calendar events for date range"""
    workout_service = WorkoutService(db)
    
    # Default to current month if no dates provided
    if not start_date:
        start_date = date.today().replace(day=1)
    if not end_date:
        from datetime import timedelta
        next_month = start_date.replace(day=28) + timedelta(days=4)
        end_date = next_month - timedelta(days=next_month.day)
    
    events = workout_service.get_calendar_events(
        user_id=current_user["user_id"],
        start_date=start_date,
        end_date=end_date
    )
    
    return events


@router.get("/{year}/{month}")
async def get_calendar_month(year: int, month: int,
                            current_user: dict = Depends(get_current_user),
                            db: Session = Depends(get_db)):
    """Get workouts for specific month (same format as upcoming/today-workouts)"""
    if month < 1 or month > 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid month"
        )
    
    if year < 2020 or year > 2030:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid year"
        )
    
    user_id = current_user["user_id"]
    
    # Calculate month boundaries
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1) - date.resolution
    else:
        end_date = date(year, month + 1, 1) - date.resolution
    
    # Convert to datetime for session queries
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())
    
    # Get workout IDs from inactive plans (same logic as /dashboard/upcoming)
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
    
    # Get workouts with scheduled_date in the month
    scheduled_workouts = db.execute(
        select(Workout)
        .where(
            and_(
                Workout.user_id == user_id,
                Workout.scheduled_date >= start_date,
                Workout.scheduled_date <= end_date,
                Workout.status.in_(["scheduled", "completed"])
            )
        )
    ).scalars().all()
    
    # Get workouts completed in the month (via WorkoutSession.actual_date)
    # This includes standalone workouts that were done but not scheduled for this month
    workouts_from_sessions = db.execute(
        select(Workout)
        .join(WorkoutSession, Workout.id == WorkoutSession.workout_id)
        .where(
            and_(
                WorkoutSession.user_id == user_id,
                WorkoutSession.actual_date >= start_datetime,
                WorkoutSession.actual_date <= end_datetime,
                # Include standalone workouts or workouts not from inactive plans
                or_(
                    Workout.plan_id.is_(None),  # Standalone workouts
                    ~Workout.id.in_(inactive_plan_workout_ids)  # Workouts from active plans
                )
            )
        )
        .distinct()
    ).scalars().all()
    
    # Combine both lists and remove duplicates
    all_workouts = list(scheduled_workouts) + list(workouts_from_sessions)
    unique_workouts = {}
    for workout in all_workouts:
        # Filter out workouts from inactive plans
        if workout.id not in inactive_plan_workout_ids:
            unique_workouts[workout.id] = workout
    
    # Sort by scheduled_date (use actual_date from session if scheduled_date is None or different)
    def get_display_date(w):
        # If workout has scheduled_date in the month, use it
        if w.scheduled_date and start_date <= w.scheduled_date <= end_date:
            return w.scheduled_date
        # Otherwise, try to get actual_date from the first session in the month
        sessions_in_month = db.execute(
            select(WorkoutSession)
            .where(
                and_(
                    WorkoutSession.workout_id == w.id,
                    WorkoutSession.actual_date >= start_datetime,
                    WorkoutSession.actual_date <= end_datetime
                )
            )
            .order_by(WorkoutSession.actual_date.asc())
        ).scalars().first()
        if sessions_in_month:
            return sessions_in_month.actual_date.date()
        return w.scheduled_date or date.min
    
    filtered_workouts = list(unique_workouts.values())
    filtered_workouts.sort(key=lambda w: (get_display_date(w), w.duration_minutes or 0))
    
    return filtered_workouts


@router.post("/events", response_model=CalendarEventResponse, status_code=status.HTTP_201_CREATED)
async def create_calendar_event(event_data: CalendarEventCreate,
                               current_user: dict = Depends(get_current_user),
                               db: Session = Depends(get_db)):
    """Create a new calendar event"""
    workout_service = WorkoutService(db)
    
    event = workout_service.create_calendar_event(
        user_id=current_user["user_id"],
        workout_id=event_data.workout_id,
        title=event_data.title,
        event_type=event_data.event_type,
        scheduled_date=event_data.scheduled_date,
        duration_minutes=event_data.duration_minutes,
        is_recurring=event_data.is_recurring
    )
    
    return event


@router.put("/events/{event_id}", response_model=CalendarEventResponse)
async def update_calendar_event(event_id: int,
                               event_data: CalendarEventUpdate,
                               current_user: dict = Depends(get_current_user),
                               db: Session = Depends(get_db)):
    """Update calendar event"""
    from app.models.calendar import CalendarEvent
    
    event = db.query(CalendarEvent).filter(
        CalendarEvent.id == event_id,
        CalendarEvent.user_id == current_user["user_id"]
    ).first()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Calendar event not found"
        )
    
    update_data = event_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(event, field, value)
    
    db.commit()
    db.refresh(event)
    
    return event


@router.delete("/events/{event_id}")
async def delete_calendar_event(event_id: int,
                               current_user: dict = Depends(get_current_user),
                               db: Session = Depends(get_db)):
    """Delete calendar event"""
    from app.models.calendar import CalendarEvent
    
    event = db.query(CalendarEvent).filter(
        CalendarEvent.id == event_id,
        CalendarEvent.user_id == current_user["user_id"]
    ).first()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Calendar event not found"
        )
    
    db.delete(event)
    db.commit()
    
    return {"message": "Calendar event deleted successfully"}


@router.post("/drag-drop")
async def handle_drag_drop(drag_data: DragDropRequest,
                          current_user: dict = Depends(get_current_user),
                          db: Session = Depends(get_db)):
    """Handle drag and drop calendar events"""
    from app.models.calendar import CalendarEvent
    
    event = db.query(CalendarEvent).filter(
        CalendarEvent.id == drag_data.event_id,
        CalendarEvent.user_id == current_user["user_id"]
    ).first()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Calendar event not found"
        )
    
    # Update event date and duration
    event.scheduled_date = drag_data.new_date
    if drag_data.new_duration_minutes:
        event.duration_minutes = drag_data.new_duration_minutes
    
    db.commit()
    db.refresh(event)
    
    return {"message": "Event updated successfully", "event": event}
