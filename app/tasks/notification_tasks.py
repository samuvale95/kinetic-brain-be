"""
Background tasks for notifications.
Can be called by APScheduler or Render Cron Jobs.
"""
from datetime import date, timedelta
from loguru import logger
from app.database import SessionLocal
from app.services.workout_reminder_service import WorkoutReminderService


async def send_workout_reminders_task():
    """
    Background task to send workout reminders for tomorrow's workouts.
    
    This function can be called by:
    - APScheduler (if scheduled_tasks_provider == "apscheduler")
    - Render Cron Jobs via HTTP endpoint (if scheduled_tasks_provider == "render_cron")
    
    It sends reminders for workouts scheduled for tomorrow (today + 1 day).
    """
    db = SessionLocal()
    
    try:
        logger.info("[NOTIFICATION_TASK] Starting workout reminder task...")
        
        # Get tomorrow's date
        tomorrow = date.today() + timedelta(days=1)
        
        reminder_service = WorkoutReminderService(db)
        stats = await reminder_service.send_reminders_for_date(
            reminder_date=tomorrow,
            only_scheduled=True
        )
        
        logger.info(
            f"[NOTIFICATION_TASK] Workout reminder task completed for {tomorrow}: "
            f"{stats['notifications_sent']} sent, {stats['notifications_skipped']} skipped, "
            f"{stats['errors']} errors"
        )
        
        return stats
        
    except Exception as e:
        logger.exception(f"[NOTIFICATION_TASK] Error in workout reminder task: {e}")
        raise
    finally:
        db.close()

