from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_
from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
from app.models.workout import WorkoutPlan, Workout, WorkoutSession, WorkoutStatus
from app.models.calendar import CalendarEvent
from app.models.strava import StravaActivity
from app.schemas.workout import (
    WorkoutPlanCreate, WorkoutPlanUpdate, 
    WorkoutCreate, WorkoutUpdate,
    WorkoutSessionCreate
)


class WorkoutService:
    def __init__(self, db: Session):
        self.db = db
    
    # Workout Plans
    def create_workout_plan(self, user_id: int, plan_data: WorkoutPlanCreate) -> WorkoutPlan:
        """Create a new workout plan with maximum 2 plans per user limit"""
        # First, deactivate all existing active plans for this user
        existing_active_plans = self.db.execute(
            select(WorkoutPlan)
            .where(and_(WorkoutPlan.user_id == user_id, WorkoutPlan.status == "active"))
        ).scalars().all()
        
        for plan in existing_active_plans:
            plan.status = "paused"
        
        # Check total number of plans for this user
        all_user_plans = self.db.execute(
            select(WorkoutPlan)
            .where(WorkoutPlan.user_id == user_id)
            .order_by(WorkoutPlan.created_at.desc())
        ).scalars().all()
        
        # If user has 2 or more plans, delete the oldest ones (keep only the 2 most recent)
        if len(all_user_plans) >= 2:
            plans_to_delete = all_user_plans[1:]  # Keep the first (most recent), delete the rest
            
            for old_plan in plans_to_delete:
                # Move workouts to historical status before deleting plan
                self._archive_workouts_from_plan(old_plan.id)
                
                # Delete calendar events for workouts in this plan
                workout_ids = self.db.execute(
                    select(Workout.id)
                    .where(Workout.plan_id == old_plan.id)
                ).scalars().all()
                
                if workout_ids:
                    self.db.execute(
                        select(CalendarEvent)
                        .where(CalendarEvent.workout_id.in_(workout_ids))
                    ).scalars().all()
                    
                    # Delete the calendar events
                    self.db.query(CalendarEvent).filter(
                        CalendarEvent.workout_id.in_(workout_ids)
                    ).delete(synchronize_session=False)
                
                # Delete the plan
                self.db.delete(old_plan)
        
        self.db.commit()
        
        # Create new plan
        db_plan = WorkoutPlan(
            user_id=user_id,
            **plan_data.dict()
        )
        
        # Calculate total weeks
        delta = plan_data.end_date - plan_data.start_date
        db_plan.total_weeks = delta.days // 7
        
        self.db.add(db_plan)
        self.db.commit()
        self.db.refresh(db_plan)
        
        return db_plan
    
    def _archive_workouts_from_plan(self, plan_id: int):
        """Archive workouts from a plan before deleting it"""
        # Get all workouts for this plan
        workouts = self.db.execute(
            select(Workout)
            .where(Workout.plan_id == plan_id)
        ).scalars().all()
        
        # Update workouts to historical status (remove from plan but keep in history)
        for workout in workouts:
            workout.plan_id = None  # Remove from plan
            workout.status = WorkoutStatus.COMPLETED  # Mark as completed for history
            # Keep the workout in the database for historical purposes
    
    def create_workouts_from_ai_plan(self, user_id: int, plan_id: int, ai_plan_data: Dict[str, Any]) -> List[Workout]:
        """Create individual workouts from AI plan data"""
        workouts = []
        
        if "weeks" not in ai_plan_data:
            return workouts
        
        # Get the plan to get start date
        plan = self.get_workout_plan(plan_id, user_id)
        if not plan:
            return workouts
        
        current_date = plan.start_date
        
        for week_data in ai_plan_data["weeks"]:
            week_number = week_data.get("week", 1)
            week_workouts = week_data.get("workouts", [])
            
            for workout_data in week_workouts:
                # Calculate scheduled date
                day_mapping = {
                    "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3,
                    "Friday": 4, "Saturday": 5, "Sunday": 6
                }
                day_offset = day_mapping.get(workout_data.get("day", "Monday"), 0)
                scheduled_date = current_date + timedelta(days=day_offset)
                
                # Create workout
                workout = Workout(
                    plan_id=plan_id,
                    user_id=user_id,
                    title=workout_data.get("type", "Workout"),
                    type=workout_data.get("type", "endurance"),
                    day_number=len(workouts) + 1,
                    scheduled_date=scheduled_date,
                    duration_minutes=workout_data.get("duration_minutes", 60),
                    intensity=workout_data.get("intensity", "moderate"),
                    zone=workout_data.get("intensity", "Z2"),
                    structure_json={
                        "description": workout_data.get("description", ""),
                        "rpe_target": workout_data.get("rpe_target", 6),
                        "focus": week_data.get("focus", "Base Building")
                    },
                    status=WorkoutStatus.SCHEDULED
                )
                
                self.db.add(workout)
                workouts.append(workout)
            
            # Move to next week
            current_date += timedelta(days=7)
        
        self.db.commit()
        return workouts
    
    def create_calendar_events_from_workouts(self, user_id: int, workouts: List[Workout]) -> List[CalendarEvent]:
        """Create calendar events from workouts"""
        events = []
        
        for workout in workouts:
            if not workout.scheduled_date:
                continue
                
            # Create calendar event for workout
            event = CalendarEvent(
                user_id=user_id,
                workout_id=workout.id,
                title=workout.title,
                event_type="workout",
                scheduled_date=workout.scheduled_date,
                duration_minutes=workout.duration_minutes,
                is_recurring=False
            )
            
            self.db.add(event)
            events.append(event)
        
        self.db.commit()
        return events
    
    def get_workout_plans(self, user_id: int, skip: int = 0, limit: int = 100) -> List[WorkoutPlan]:
        """Get user's workout plans"""
        return self.db.execute(
            select(WorkoutPlan)
            .where(WorkoutPlan.user_id == user_id)
            .offset(skip)
            .limit(limit)
        ).scalars().all()
    
    def get_workout_plan(self, plan_id: int, user_id: int) -> Optional[WorkoutPlan]:
        """Get specific workout plan"""
        return self.db.execute(
            select(WorkoutPlan)
            .where(and_(WorkoutPlan.id == plan_id, WorkoutPlan.user_id == user_id))
        ).scalar_one_or_none()
    
    def update_workout_plan(self, plan_id: int, user_id: int, plan_data: WorkoutPlanUpdate) -> Optional[WorkoutPlan]:
        """Update workout plan"""
        plan = self.get_workout_plan(plan_id, user_id)
        if not plan:
            return None
        
        update_data = plan_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(plan, field, value)
        
        self.db.commit()
        self.db.refresh(plan)
        return plan
    
    def delete_workout_plan(self, plan_id: int, user_id: int) -> bool:
        """Delete workout plan"""
        plan = self.get_workout_plan(plan_id, user_id)
        if not plan:
            return False
        
        self.db.delete(plan)
        self.db.commit()
        return True
    
    # Workouts
    def create_workout(self, user_id: int, workout_data: WorkoutCreate) -> Workout:
        """Create a new workout"""
        db_workout = Workout(
            user_id=user_id,
            **workout_data.dict()
        )
        
        self.db.add(db_workout)
        self.db.commit()
        self.db.refresh(db_workout)
        
        return db_workout
    
    def get_workouts(self, user_id: int, skip: int = 0, limit: int = 100, 
                    plan_id: Optional[int] = None) -> List[Workout]:
        """Get user's workouts"""
        query = select(Workout).where(Workout.user_id == user_id)
        
        if plan_id:
            query = query.where(Workout.plan_id == plan_id)
        
        return self.db.execute(
            query.offset(skip).limit(limit)
        ).scalars().all()
    
    def get_workout(self, workout_id: int, user_id: int) -> Optional[Workout]:
        """Get specific workout"""
        return self.db.execute(
            select(Workout)
            .where(and_(Workout.id == workout_id, Workout.user_id == user_id))
        ).scalar_one_or_none()
    
    def update_workout(self, workout_id: int, user_id: int, workout_data: WorkoutUpdate) -> Optional[Workout]:
        """Update workout"""
        workout = self.get_workout(workout_id, user_id)
        if not workout:
            return None
        
        update_data = workout_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(workout, field, value)
        
        self.db.commit()
        self.db.refresh(workout)
        return workout
    
    def delete_workout(self, workout_id: int, user_id: int) -> bool:
        """Delete workout"""
        workout = self.get_workout(workout_id, user_id)
        if not workout:
            return False
        
        self.db.delete(workout)
        self.db.commit()
        return True
    
    # Workout Sessions
    def create_workout_session(self, user_id: int, session_data: WorkoutSessionCreate) -> WorkoutSession:
        """Create a new workout session"""
        db_session = WorkoutSession(
            user_id=user_id,
            **session_data.dict()
        )
        
        self.db.add(db_session)
        self.db.commit()
        self.db.refresh(db_session)
        
        return db_session
    
    def get_workout_sessions(self, user_id: int, workout_id: Optional[int] = None,
                           skip: int = 0, limit: int = 100) -> List[WorkoutSession]:
        """Get workout sessions"""
        query = select(WorkoutSession).where(WorkoutSession.user_id == user_id)
        
        if workout_id:
            query = query.where(WorkoutSession.workout_id == workout_id)
        
        return self.db.execute(
            query.offset(skip).limit(limit)
        ).scalars().all()
    
    def get_workout_session(self, session_id: int, user_id: int) -> Optional[WorkoutSession]:
        """Get specific workout session"""
        return self.db.execute(
            select(WorkoutSession)
            .where(and_(WorkoutSession.id == session_id, WorkoutSession.user_id == user_id))
        ).scalar_one_or_none()
    
    # Calendar Integration
    def create_calendar_event(self, user_id: int, workout_id: Optional[int], 
                            title: str, event_type: str, scheduled_date: date,
                            duration_minutes: int, is_recurring: bool = False) -> CalendarEvent:
        """Create calendar event for workout"""
        db_event = CalendarEvent(
            user_id=user_id,
            workout_id=workout_id,
            title=title,
            event_type=event_type,
            scheduled_date=scheduled_date,
            duration_minutes=duration_minutes,
            is_recurring=is_recurring
        )
        
        self.db.add(db_event)
        self.db.commit()
        self.db.refresh(db_event)
        
        return db_event
    
    def get_calendar_events(self, user_id: int, start_date: date, end_date: date) -> List[CalendarEvent]:
        """Get calendar events for date range, excluding inactive plans"""
        import logging
        logger = logging.getLogger(__name__)
        
        # Get all matching calendar events
        query = (
            select(CalendarEvent)
            .where(
                and_(
                    CalendarEvent.user_id == user_id,
                    CalendarEvent.scheduled_date >= start_date,
                    CalendarEvent.scheduled_date <= end_date
                )
            )
        )
        all_events = self.db.execute(query).scalars().all()
        logger.info(f"Found {len(all_events)} total calendar events")
        
        # Get all workout IDs that belong to inactive plans (for this user)
        inactive_plan_workout_ids = self.db.execute(
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
        logger.info(f"Found {len(inactive_plan_workout_ids)} workouts from inactive plans: {inactive_plan_workout_ids}")
        
        # Filter events: exclude those with workout_id in inactive plans
        filtered_events = [
            event for event in all_events 
            if event.workout_id is None or event.workout_id not in inactive_plan_workout_ids
        ]
        logger.info(f"Returning {len(filtered_events)} filtered calendar events")
        
        return filtered_events
    
    def get_upcoming_workouts(self, user_id: int, days: int = 7) -> List[Workout]:
        """Get upcoming workouts for the next N days"""
        from datetime import timedelta
        end_date = date.today() + timedelta(days=days)
        
        return self.db.execute(
            select(Workout)
            .where(
                and_(
                    Workout.user_id == user_id,
                    Workout.scheduled_date >= date.today(),
                    Workout.scheduled_date <= end_date,
                    Workout.status == "scheduled"
                )
            )
        ).scalars().all()
    
    def get_workout_plan_with_details(self, plan_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Get workout plan with all workouts, sessions, and Strava details"""
        # Get the plan
        plan = self.get_workout_plan(plan_id, user_id)
        if not plan:
            return None
        
        # Get all workouts for this plan
        workouts = self.db.execute(
            select(Workout)
            .where(and_(Workout.plan_id == plan_id, Workout.user_id == user_id))
            .order_by(Workout.scheduled_date.asc(), Workout.day_number.asc())
        ).scalars().all()
        
        # Get all sessions for these workouts
        workout_ids = [w.id for w in workouts]
        sessions = []
        if workout_ids:
            sessions = self.db.execute(
                select(WorkoutSession)
                .where(WorkoutSession.workout_id.in_(workout_ids))
                .order_by(WorkoutSession.actual_date.desc())
            ).scalars().all()
        
        # Get all Strava activities for these workouts
        strava_activities = []
        if workout_ids:
            strava_activities = self.db.execute(
                select(StravaActivity)
                .where(StravaActivity.workout_id.in_(workout_ids))
            ).scalars().all()
        
        # Organize sessions by workout_id
        sessions_by_workout = {}
        for session in sessions:
            if session.workout_id not in sessions_by_workout:
                sessions_by_workout[session.workout_id] = []
            sessions_by_workout[session.workout_id].append(session)
        
        # Organize Strava activities by workout_id
        strava_by_workout = {}
        for activity in strava_activities:
            if activity.workout_id:
                strava_by_workout[activity.workout_id] = activity
        
        # Build detailed workouts
        detailed_workouts = []
        for workout in workouts:
            workout_detail = {
                "id": workout.id,
                "plan_id": workout.plan_id,
                "user_id": workout.user_id,
                "title": workout.title,
                "type": workout.type,
                "day_number": workout.day_number,
                "scheduled_date": workout.scheduled_date.isoformat() if workout.scheduled_date else None,
                "duration_minutes": workout.duration_minutes,
                "intensity": workout.intensity,
                "zone": workout.zone,
                "structure_json": workout.structure_json,
                "status": workout.status.value if workout.status else None,
                "notes": workout.notes,
                "created_at": workout.created_at.isoformat() if workout.created_at else None,
                "updated_at": workout.updated_at.isoformat() if workout.updated_at else None,
                "sessions": [],
                "strava_activity": None
            }
            
            # Add sessions
            if workout.id in sessions_by_workout:
                for session in sessions_by_workout[workout.id]:
                    workout_detail["sessions"].append({
                        "id": session.id,
                        "workout_id": session.workout_id,
                        "user_id": session.user_id,
                        "actual_date": session.actual_date.isoformat() if session.actual_date else None,
                        "duration_minutes": session.duration_minutes,
                        "avg_hr": session.avg_hr,
                        "max_hr": session.max_hr,
                        "avg_pace": session.avg_pace,
                        "avg_power": session.avg_power,
                        "perceived_exertion": session.perceived_exertion,
                        "notes": session.notes,
                        "created_at": session.created_at.isoformat() if session.created_at else None
                    })
            
            # Add Strava activity
            if workout.id in strava_by_workout:
                activity = strava_by_workout[workout.id]
                workout_detail["strava_activity"] = {
                    "id": activity.id,
                    "strava_activity_id": activity.strava_activity_id,
                    "name": activity.name,
                    "type": activity.type,
                    "sport_type": activity.sport_type,
                    "start_date": activity.start_date.isoformat() if activity.start_date else None,
                    "start_date_local": activity.start_date_local.isoformat() if activity.start_date_local else None,
                    "timezone": activity.timezone,
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
                    "feels_like": activity.feels_like,
                    "calories": activity.calories,
                    "kilojoules": activity.kilojoules,
                    "is_synced": activity.is_synced,
                    "sync_status": activity.sync_status,
                    "splits_metric": activity.splits_metric,
                    "splits_standard": activity.splits_standard,
                    "best_efforts": activity.best_efforts,
                    "segment_efforts": activity.segment_efforts,
                    "raw_data": activity.raw_data,
                    "created_at": activity.created_at.isoformat() if activity.created_at else None
                }
            
            detailed_workouts.append(workout_detail)
        
        # Calculate statistics
        total_workouts = len(workouts)
        completed_workouts = len([w for w in workouts if w.status == WorkoutStatus.COMPLETED])
        skipped_workouts = len([w for w in workouts if w.status == WorkoutStatus.SKIPPED])
        scheduled_workouts = len([w for w in workouts if w.status == WorkoutStatus.SCHEDULED])
        workouts_with_strava = len([w for w in workouts if w.id in strava_by_workout])
        
        # Build plan details
        plan_details = {
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
            "updated_at": plan.updated_at.isoformat() if plan.updated_at else None,
            "workouts": detailed_workouts,
            "total_workouts": total_workouts,
            "completed_workouts": completed_workouts,
            "skipped_workouts": skipped_workouts,
            "scheduled_workouts": scheduled_workouts,
            "workouts_with_strava": workouts_with_strava
        }
        
        return plan_details
