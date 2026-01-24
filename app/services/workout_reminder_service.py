from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from typing import List, Optional
from datetime import date, timedelta, datetime, timezone
from app.models.workout import Workout, WorkoutStatus, WorkoutPlan
from app.services.notification_service import NotificationService
from loguru import logger


class WorkoutReminderService:
    """Service for sending workout reminder notifications"""
    
    def __init__(self, db: Session):
        self.db = db
        self.notification_service = NotificationService(db)
    
    def get_workouts_for_reminder(
        self,
        reminder_date: date,
        only_scheduled: bool = True
    ) -> List[Workout]:
        """
        Get workouts scheduled for a specific date that need reminders.
        
        Args:
            reminder_date: Date to check for workouts (usually tomorrow)
            only_scheduled: If True, only return workouts with status "scheduled"
            
        Returns:
            List of Workout objects scheduled for the reminder_date
        """
        conditions = [
            Workout.scheduled_date == reminder_date,
        ]
        
        if only_scheduled:
            conditions.append(Workout.status == WorkoutStatus.SCHEDULED)
        
        # Get workouts from active plans
        workouts_from_plans = self.db.execute(
            select(Workout)
            .join(WorkoutPlan, Workout.plan_id == WorkoutPlan.id)
            .where(
                and_(
                    *conditions,
                    WorkoutPlan.status == "active"
                )
            )
        ).scalars().all()
        
        # Get standalone workouts (no plan_id)
        standalone_workouts = self.db.execute(
            select(Workout)
            .where(
                and_(
                    *conditions,
                    Workout.plan_id.is_(None)
                )
            )
        ).scalars().all()
        
        # Combine and return
        all_workouts = list(workouts_from_plans) + list(standalone_workouts)
        
        logger.info(
            f"Found {len(all_workouts)} workouts scheduled for {reminder_date} "
            f"(from plans: {len(workouts_from_plans)}, standalone: {len(standalone_workouts)})"
        )
        
        return all_workouts
    
    async def send_reminders_for_date(
        self,
        reminder_date: date,
        only_scheduled: bool = True
    ) -> dict:
        """
        Send reminder notifications for all workouts scheduled on a specific date.
        
        Args:
            reminder_date: Date to send reminders for (usually tomorrow)
            only_scheduled: If True, only send reminders for workouts with status "scheduled"
            
        Returns:
            Dict with statistics: {
                "total_workouts": int,
                "notifications_sent": int,
                "notifications_skipped": int,
                "errors": int
            }
        """
        workouts = self.get_workouts_for_reminder(reminder_date, only_scheduled)
        
        stats = {
            "total_workouts": len(workouts),
            "notifications_sent": 0,
            "notifications_skipped": 0,
            "errors": 0,
            "users_notified": set()
        }
        
        # Group workouts by user to send one notification per user with all their workouts
        workouts_by_user = {}
        for workout in workouts:
            if workout.user_id not in workouts_by_user:
                workouts_by_user[workout.user_id] = []
            workouts_by_user[workout.user_id].append(workout)
        
        # Send reminders for each user
        for user_id, user_workouts in workouts_by_user.items():
            try:
                # Check if user wants workout reminders
                can_send_push = self.notification_service.can_send_notification(
                    user_id=user_id,
                    notification_type="workout_reminder",
                    channel="push"
                )
                can_send_email = self.notification_service.can_send_notification(
                    user_id=user_id,
                    notification_type="workout_reminder",
                    channel="email"
                )
                
                if not can_send_push and not can_send_email:
                    logger.info(
                        f"User {user_id} has disabled workout reminders, skipping {len(user_workouts)} workouts"
                    )
                    stats["notifications_skipped"] += len(user_workouts)
                    continue
                
                # Prepare notification content
                if len(user_workouts) == 1:
                    workout = user_workouts[0]
                    title = "Promemoria Allenamento"
                    body = f"Ricorda: hai un allenamento programmato per domani: {workout.title}"
                    data = {
                        "workout_id": workout.id,
                        "workout_title": workout.title,
                        "scheduled_date": reminder_date.isoformat(),
                        "duration_minutes": workout.duration_minutes,
                        "type": workout.type
                    }
                else:
                    titles = [w.title for w in user_workouts]
                    title = "Promemoria Allenamenti"
                    body = f"Ricorda: hai {len(user_workouts)} allenamenti programmati per domani"
                    data = {
                        "workout_count": len(user_workouts),
                        "scheduled_date": reminder_date.isoformat(),
                        "workout_ids": [w.id for w in user_workouts],
                        "workout_titles": titles
                    }
                
                # Send notification
                result = await self.notification_service.send_notification(
                    user_id=user_id,
                    notification_type="workout_reminder",
                    title=title,
                    body=body,
                    data=data
                )
                
                # Check results
                sent = False
                if result.get("sent", {}).get("push", False) or result.get("sent", {}).get("email", False):
                    sent = True
                    stats["notifications_sent"] += 1
                    stats["users_notified"].add(user_id)
                else:
                    stats["notifications_skipped"] += 1
                
                logger.info(
                    f"Reminder for user {user_id}: sent={sent}, "
                    f"push={result.get('sent', {}).get('push', False)}, "
                    f"email={result.get('sent', {}).get('email', False)}"
                )
                
            except Exception as e:
                logger.error(f"Error sending reminder to user {user_id}: {e}")
                stats["errors"] += 1
        
        # Convert set to count
        stats["unique_users_notified"] = len(stats["users_notified"])
        stats.pop("users_notified")  # Remove set from response
        
        logger.info(
            f"Reminder job completed for {reminder_date}: "
            f"{stats['notifications_sent']} sent, "
            f"{stats['notifications_skipped']} skipped, "
            f"{stats['errors']} errors"
        )
        
        return stats
    
    async def send_daily_suggested_workout_notifications(
        self,
        target_date: Optional[date] = None
    ) -> dict:
        """
        Send daily suggested workout notifications to users.
        
        Args:
            target_date: Date to send suggestions for (defaults to today)
            
        Returns:
            Dict with statistics about notifications sent
        """
        from app.services.workout_service import WorkoutService
        
        if not target_date:
            target_date = date.today()
        
        workout_service = WorkoutService(self.db)
        
        # Get all active users (users with active plans or recent activity)
        from app.models.user import User
        from app.models.workout import WorkoutPlan
        
        active_users = self.db.execute(
            select(User.id)
            .join(WorkoutPlan, WorkoutPlan.user_id == User.id)
            .where(WorkoutPlan.status == "active")
            .distinct()
        ).scalars().all()
        
        stats = {
            "total_users": len(active_users),
            "notifications_sent": 0,
            "notifications_skipped": 0,
            "errors": 0,
            "no_suggestion": 0
        }
        
        for user_id in active_users:
            try:
                # Get suggested workout for user
                suggestion = workout_service.get_suggested_workout(user_id, target_date)
                
                if not suggestion:
                    stats["no_suggestion"] += 1
                    continue
                
                # Send notification
                workout_title = suggestion.get("workout", {}).get("title", "Allenamento")
                reasoning = suggestion.get("reasoning", "")
                
                result = await self.notification_service.send_notification(
                    user_id=user_id,
                    notification_type="daily_suggested_workout",
                    title=f"Workout Suggerito: {workout_title}",
                    body=reasoning[:200] if reasoning else "Hai un nuovo workout suggerito per oggi!",
                    data={
                        "workout_id": suggestion.get("workout", {}).get("id"),
                        "type": "daily_suggested_workout",
                        "date": target_date.isoformat()
                    },
                    channels=["push"]
                )
                
                if result.get("push_sent", 0) > 0:
                    stats["notifications_sent"] += 1
                else:
                    stats["notifications_skipped"] += 1
                    
            except Exception as e:
                logger.error(f"Error sending daily suggested workout notification to user {user_id}: {e}")
                stats["errors"] += 1
        
        logger.info(f"Daily suggested workout notifications sent: {stats}")
        return stats
    
    async def send_tomorrow_reminders(self) -> dict:
        """
        Convenience method to send reminders for tomorrow's workouts.
        
        Returns:
            Dict with statistics
        """
        tomorrow = date.today() + timedelta(days=1)
        return await self.send_reminders_for_date(tomorrow, only_scheduled=True)

