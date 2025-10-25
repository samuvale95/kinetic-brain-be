from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_
from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
from app.models.workout import WorkoutPlan, Workout, WorkoutSession, WorkoutStatus
from app.models.calendar import CalendarEvent
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
        """Create a new workout plan"""
        # First, deactivate all existing active plans for this user
        self.db.execute(
            select(WorkoutPlan)
            .where(and_(WorkoutPlan.user_id == user_id, WorkoutPlan.status == "active"))
        ).scalars().all()
        
        # Update existing active plans to paused
        existing_plans = self.db.execute(
            select(WorkoutPlan)
            .where(and_(WorkoutPlan.user_id == user_id, WorkoutPlan.status == "active"))
        ).scalars().all()
        
        for plan in existing_plans:
            plan.status = "paused"
        
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
        """Get calendar events for date range"""
        return self.db.execute(
            select(CalendarEvent)
            .where(
                and_(
                    CalendarEvent.user_id == user_id,
                    CalendarEvent.scheduled_date >= start_date,
                    CalendarEvent.scheduled_date <= end_date
                )
            )
        ).scalars().all()
    
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
