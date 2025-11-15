from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, and_, or_, desc
from typing import List, Optional
from datetime import date, datetime
from app.database import get_db
from app.schemas.calendar import (
    CalendarEventCreate, CalendarEventUpdate, CalendarEventResponse,
    DragDropRequest, CalendarMonthRequest
)
from app.schemas.workout import CalendarWorkoutResponse, StravaActivitySummary
from app.models.workout import Workout, WorkoutPlan, WorkoutSession, WorkoutStatus
from app.models.strava import StravaActivity, StravaAccount
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


@router.get("/debug/today-activities")
async def debug_today_activities(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Debug endpoint per verificare attività e workout di oggi"""
    from datetime import date, datetime, timedelta
    
    user_id = current_user["user_id"]
    today = date.today()
    start_datetime = datetime.combine(today, datetime.min.time())
    end_datetime = datetime.combine(today, datetime.max.time())
    
    result = {
        "date": today.isoformat(),
        "strava_activities": [],
        "workouts": []
    }
    
    # Trova attività Strava di oggi
    strava_account_ids = db.execute(
        select(StravaAccount.id).where(StravaAccount.user_id == user_id)
    ).scalars().all()
    
    if strava_account_ids:
        activities_today = db.execute(
            select(StravaActivity)
            .where(
                and_(
                    StravaActivity.strava_account_id.in_(strava_account_ids),
                    StravaActivity.start_date >= start_datetime,
                    StravaActivity.start_date <= end_datetime
                )
            )
            .order_by(desc(StravaActivity.start_date))
        ).scalars().all()
        
        for activity in activities_today:
            workout_info = None
            if activity.workout_id:
                workout = db.execute(
                    select(Workout).where(Workout.id == activity.workout_id)
                ).scalar_one_or_none()
                
                if workout:
                    # Verifica relazione caricata
                    workout_with_rel = db.execute(
                        select(Workout)
                        .options(joinedload(Workout.strava_activity))
                        .where(Workout.id == workout.id)
                    ).unique().scalar_one_or_none()
                    
                    workout_info = {
                        "id": workout.id,
                        "title": workout.title,
                        "status": workout.status.value if isinstance(workout.status, WorkoutStatus) else workout.status,
                        "scheduled_date": workout.scheduled_date.isoformat() if workout.scheduled_date else None,
                        "has_strava_activity_loaded": workout_with_rel.strava_activity is not None if workout_with_rel else False,
                        "strava_activity_id_in_relation": workout_with_rel.strava_activity.id if workout_with_rel and workout_with_rel.strava_activity else None
                    }
            
            result["strava_activities"].append({
                "id": activity.id,
                "strava_activity_id": activity.strava_activity_id,
                "name": activity.name,
                "type": activity.type,
                "start_date": activity.start_date_local.isoformat() if activity.start_date_local else None,
                "workout_id": activity.workout_id,
                "matched_workout": workout_info
            })
    
    # Trova workout di oggi
    workouts_today = db.execute(
        select(Workout)
        .where(
            and_(
                Workout.user_id == user_id,
                Workout.scheduled_date == today,
                Workout.status.in_(["scheduled", "completed"])
            )
        )
        .options(joinedload(Workout.strava_activity))
    ).unique().scalars().all()
    
    for workout in workouts_today:
        strava_info = None
        if workout.strava_activity:
            strava_info = {
                "id": workout.strava_activity.id,
                "strava_activity_id": workout.strava_activity.strava_activity_id,
                "name": workout.strava_activity.name,
                "workout_id": workout.strava_activity.workout_id
            }
        
        result["workouts"].append({
            "id": workout.id,
            "title": workout.title,
            "status": workout.status.value if isinstance(workout.status, WorkoutStatus) else workout.status,
            "scheduled_date": workout.scheduled_date.isoformat() if workout.scheduled_date else None,
            "plan_id": workout.plan_id,
            "has_strava_activity": workout.strava_activity is not None,
            "strava_activity": strava_info
        })
    
    return result


@router.get("/{year}/{month}", response_model=List[CalendarWorkoutResponse])
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
    
    # Get workouts with scheduled_date in the month (eager load Strava activity)
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
        .options(joinedload(Workout.strava_activity))
    ).unique().scalars().all()
    
    # Get workouts completed in the month (via WorkoutSession.actual_date)
    # This includes standalone workouts that were done but not scheduled for this month
    # Note: We don't use DISTINCT here because PostgreSQL can't handle DISTINCT on JSON columns.
    # Deduplication is handled in Python below.
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
        .options(joinedload(Workout.strava_activity))
    ).unique().scalars().all()
    
    # Get Strava activities for the month that don't belong to any plan
    # (workout_id is NULL or workout is standalone)
    strava_account_ids = db.execute(
        select(StravaAccount.id)
        .where(StravaAccount.user_id == user_id)
    ).scalars().all()
    
    strava_activities = []
    if strava_account_ids:
        # Get Strava activities in the month
        strava_activities_query = (
            select(StravaActivity)
            .where(
                and_(
                    StravaActivity.strava_account_id.in_(strava_account_ids),
                    StravaActivity.start_date >= start_datetime,
                    StravaActivity.start_date <= end_datetime
                )
            )
        )
        
        all_strava_activities = db.execute(strava_activities_query).scalars().all()
        
        # Filter to only include activities that don't have a workout_id (NULL)
        # Activities with workout_id are already included via workouts_from_sessions
        for activity in all_strava_activities:
            if activity.workout_id is None:
                # Activity not linked to any workout - include it
                strava_activities.append(activity)
    
    # Convert Strava activities to Workout dicts with Strava data
    def strava_to_workout_dict(activity: StravaActivity) -> dict:
        """Convert StravaActivity to a Workout dict with Strava data"""
        duration_minutes = int(activity.moving_time / 60) if activity.moving_time else 0
        
        type_mapping = {
            "Run": "run",
            "Ride": "ride",
            "VirtualRide": "ride",
            "Swim": "swim",
            "Walk": "run",
            "Hike": "run",
        }
        workout_type = type_mapping.get(activity.type, activity.type.lower())
        
        activity_date = activity.start_date_local.date() if activity.start_date_local else activity.start_date.date()
        
        # Create workout dict with Strava data
        workout_dict = {
            "id": -activity.id,  # Negative ID to distinguish
            "plan_id": None,
            "user_id": user_id,
            "title": activity.name,
            "type": workout_type,
            "day_number": None,
            "scheduled_date": activity_date,
            "duration_minutes": duration_minutes,
            "intensity": None,
            "zone": None,
            "structure_json": None,
            "status": WorkoutStatus.COMPLETED.value,
            "notes": None,
            "created_at": activity.created_at if activity.created_at else datetime.now(),
            "updated_at": activity.updated_at if activity.updated_at else datetime.now(),
            # Include Strava data
            "strava_activity": {
                "id": activity.id,
                "strava_activity_id": activity.strava_activity_id,
                "distance": activity.distance,
                "moving_time": activity.moving_time,
                "elapsed_time": activity.elapsed_time,
                "total_elevation_gain": activity.total_elevation_gain,
                "average_speed": activity.average_speed,
                "max_speed": activity.max_speed,
                "average_heartrate": activity.average_heartrate,
                "max_heartrate": activity.max_heartrate,
                "average_watts": activity.average_watts,
                "max_watts": activity.max_watts,
                "weighted_average_watts": activity.weighted_average_watts,  # Potenza normalizzata da Strava
                "average_cadence": activity.average_cadence,
                "temperature": activity.temperature,
                "calories": activity.calories,
                "start_date": activity.start_date,
                "start_date_local": activity.start_date_local,
                # Training metrics (calcolate dall'applicazione)
                "tss": activity.tss,
                "normalized_power": activity.normalized_power,
                "intensity_factor": activity.intensity_factor,
                "trimp": activity.trimp,
                # Time in zones (minuti)
                "time_in_zone_1": activity.time_in_zone_1,
                "time_in_zone_2": activity.time_in_zone_2,
                "time_in_zone_3": activity.time_in_zone_3,
                "time_in_zone_4": activity.time_in_zone_4,
                "time_in_zone_5": activity.time_in_zone_5,
                # Zone distribution (JSON)
                "zone_distribution": activity.zone_distribution,
                "metrics_calculated": activity.metrics_calculated,
            }
        }
        return workout_dict
    
    # Convert regular workouts to dict format
    def workout_to_dict(workout: Workout) -> dict:
        """Convert Workout to dict format, including Strava data if matched"""
        # Check if workout has associated Strava activity
        strava_data = None
        if workout.strava_activity:
            activity = workout.strava_activity
            strava_data = {
                "id": activity.id,
                "strava_activity_id": activity.strava_activity_id,
                "distance": activity.distance,
                "moving_time": activity.moving_time,
                "elapsed_time": activity.elapsed_time,
                "total_elevation_gain": activity.total_elevation_gain,
                "average_speed": activity.average_speed,
                "max_speed": activity.max_speed,
                "average_heartrate": activity.average_heartrate,
                "max_heartrate": activity.max_heartrate,
                "average_watts": activity.average_watts,
                "max_watts": activity.max_watts,
                "weighted_average_watts": activity.weighted_average_watts,
                "average_cadence": activity.average_cadence,
                "temperature": activity.temperature,
                "calories": activity.calories,
                "start_date": activity.start_date,
                "start_date_local": activity.start_date_local,
                # Training metrics (calcolate dall'applicazione)
                "tss": activity.tss,
                "normalized_power": activity.normalized_power,
                "intensity_factor": activity.intensity_factor,
                "trimp": activity.trimp,
                # Time in zones (minuti)
                "time_in_zone_1": activity.time_in_zone_1,
                "time_in_zone_2": activity.time_in_zone_2,
                "time_in_zone_3": activity.time_in_zone_3,
                "time_in_zone_4": activity.time_in_zone_4,
                "time_in_zone_5": activity.time_in_zone_5,
                # Zone distribution (JSON)
                "zone_distribution": activity.zone_distribution,
                "metrics_calculated": activity.metrics_calculated,
            }
        
        workout_dict = {
            "id": workout.id,
            "plan_id": workout.plan_id,
            "user_id": workout.user_id,
            "title": workout.title,
            "type": workout.type,
            "day_number": workout.day_number,
            "scheduled_date": workout.scheduled_date,
            "duration_minutes": workout.duration_minutes,
            "intensity": workout.intensity,
            "zone": workout.zone,
            "structure_json": workout.structure_json,
            "status": workout.status.value if isinstance(workout.status, WorkoutStatus) else workout.status,
            "notes": workout.notes,
            "created_at": workout.created_at,
            "updated_at": workout.updated_at,
            "strava_activity": strava_data  # Include Strava data if matched
        }
        return workout_dict
    
    # Helper to get display date from dict
    def get_display_date_from_dict(w: dict) -> date:
        if w.get("scheduled_date") and start_date <= w["scheduled_date"] <= end_date:
            return w["scheduled_date"]
        if w.get("id", 0) > 0:  # Only for real workouts
            sessions_in_month = db.execute(
                select(WorkoutSession)
                .where(
                    and_(
                        WorkoutSession.workout_id == w["id"],
                        WorkoutSession.actual_date >= start_datetime,
                        WorkoutSession.actual_date <= end_datetime
                    )
                )
                .order_by(WorkoutSession.actual_date.asc())
            ).scalars().first()
            if sessions_in_month:
                return sessions_in_month.actual_date.date()
        return w.get("scheduled_date") or date.min
    
    # Combine all workouts and remove duplicates
    all_workouts = list(scheduled_workouts) + list(workouts_from_sessions)
    unique_workouts = {}
    
    for workout in all_workouts:
        # Filter out workouts from inactive plans
        if workout.id not in inactive_plan_workout_ids:
            unique_workouts[workout.id] = workout
    
    # Convert Strava activities to workout dicts
    strava_workouts_dicts = [strava_to_workout_dict(activity) for activity in strava_activities]
    
    # Convert regular workouts to dicts
    regular_workouts_dicts = [workout_to_dict(w) for w in unique_workouts.values()]
    
    # Combine and sort
    all_workouts_dicts = regular_workouts_dicts + strava_workouts_dicts
    
    # Remove duplicates by ID (for Strava activities, use date+type as key)
    seen_strava_activities = set()
    final_workouts_dicts = []
    seen_ids = set()
    
    for w in all_workouts_dicts:
        if w["id"] < 0:
            # Strava activity - check by date/type to avoid duplicates
            key = (w["scheduled_date"], w["type"])
            if key not in seen_strava_activities:
                seen_strava_activities.add(key)
                final_workouts_dicts.append(w)
        else:
            # Regular workout - check by ID
            if w["id"] not in seen_ids:
                seen_ids.add(w["id"])
                final_workouts_dicts.append(w)
    
    # Sort
    final_workouts_dicts.sort(key=lambda w: (get_display_date_from_dict(w), w.get("duration_minutes", 0)))
    
    # Return as CalendarWorkoutResponse objects
    return [CalendarWorkoutResponse(**w) for w in final_workouts_dicts]


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
