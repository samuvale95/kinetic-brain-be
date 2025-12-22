"""
Service for managing scheduled tasks.
Supports both APScheduler (in-process) and Render Cron Jobs (external HTTP calls).
"""
from typing import Optional
from loguru import logger
from app.config import settings


class SchedulerService:
    """Service for managing scheduled tasks"""
    
    _scheduler: Optional[object] = None  # APScheduler instance if enabled
    
    @classmethod
    def initialize(cls):
        """
        Initialize the scheduler based on configuration.
        
        If scheduled_tasks_provider == "apscheduler", starts APScheduler.
        If scheduled_tasks_provider == "render_cron", does nothing (jobs are external).
        """
        if settings.scheduled_tasks_provider == "apscheduler":
            try:
                from apscheduler.schedulers.asyncio import AsyncIOScheduler
                from apscheduler.triggers.cron import CronTrigger
                
                logger.info("Initializing APScheduler for scheduled tasks...")
                
                scheduler = AsyncIOScheduler(
                    timezone="UTC",
                    job_defaults={
                        "coalesce": True,  # Merge multiple pending executions into one
                        "max_instances": 1,  # Only one instance of a job at a time
                        "misfire_grace_time": 60,  # Grace time for missed executions (seconds)
                    }
                )
                
                # Add workout reminder jobs
                cls._add_workout_reminder_jobs(scheduler)
                
                scheduler.start()
                cls._scheduler = scheduler
                
                logger.info("APScheduler started successfully")
                logger.info(f"Workout reminder jobs scheduled: morning={settings.workout_reminder_morning_cron}, evening={settings.workout_reminder_evening_cron}")
                
            except ImportError as e:
                logger.error(f"Failed to import APScheduler: {e}. Install it with: pip install apscheduler")
                raise
            except Exception as e:
                logger.error(f"Failed to initialize APScheduler: {e}")
                raise
                
        elif settings.scheduled_tasks_provider == "render_cron":
            logger.info("Using Render Cron Jobs for scheduled tasks (external HTTP calls)")
            logger.info("Configure cron jobs in Render dashboard to call /notifications/cron/send-workout-reminders")
        else:
            logger.warning(
                f"Unknown scheduled_tasks_provider: {settings.scheduled_tasks_provider}. "
                f"Valid options: 'render_cron', 'apscheduler'"
            )
    
    @classmethod
    def _add_workout_reminder_jobs(cls, scheduler):
        """Add workout reminder jobs to the scheduler"""
        from apscheduler.triggers.cron import CronTrigger
        from app.tasks.notification_tasks import send_workout_reminders_task
        
        # Morning reminder
        if settings.workout_reminder_morning_cron:
            try:
                # Parse cron expression (format: minute hour day month day_of_week)
                cron_parts = settings.workout_reminder_morning_cron.split()
                if len(cron_parts) == 5:
                    minute, hour, day, month, day_of_week = cron_parts
                    trigger = CronTrigger(
                        minute=minute,
                        hour=hour,
                        day=day,
                        month=month,
                        day_of_week=day_of_week,
                        timezone="UTC"
                    )
                    scheduler.add_job(
                        send_workout_reminders_task,
                        trigger=trigger,
                        id="workout_reminder_morning",
                        name="Send workout reminders (morning)",
                        replace_existing=True
                    )
                    logger.info(f"Added morning workout reminder job: {settings.workout_reminder_morning_cron}")
                else:
                    logger.error(f"Invalid cron format for workout_reminder_morning_cron: {settings.workout_reminder_morning_cron}")
            except Exception as e:
                logger.error(f"Failed to add morning workout reminder job: {e}")
        
        # Evening reminder (optional)
        if settings.workout_reminder_evening_cron:
            try:
                cron_parts = settings.workout_reminder_evening_cron.split()
                if len(cron_parts) == 5:
                    minute, hour, day, month, day_of_week = cron_parts
                    trigger = CronTrigger(
                        minute=minute,
                        hour=hour,
                        day=day,
                        month=month,
                        day_of_week=day_of_week,
                        timezone="UTC"
                    )
                    scheduler.add_job(
                        send_workout_reminders_task,
                        trigger=trigger,
                        id="workout_reminder_evening",
                        name="Send workout reminders (evening)",
                        replace_existing=True
                    )
                    logger.info(f"Added evening workout reminder job: {settings.workout_reminder_evening_cron}")
                else:
                    logger.error(f"Invalid cron format for workout_reminder_evening_cron: {settings.workout_reminder_evening_cron}")
            except Exception as e:
                logger.error(f"Failed to add evening workout reminder job: {e}")
    
    @classmethod
    def shutdown(cls):
        """Shutdown the scheduler"""
        if cls._scheduler:
            try:
                cls._scheduler.shutdown(wait=True)
                logger.info("APScheduler shut down successfully")
            except Exception as e:
                logger.error(f"Error shutting down APScheduler: {e}")
            finally:
                cls._scheduler = None
    
    @classmethod
    def get_scheduler(cls):
        """Get the scheduler instance (if using APScheduler)"""
        return cls._scheduler
    
    @classmethod
    def is_apscheduler_enabled(cls) -> bool:
        """Check if APScheduler is enabled"""
        return settings.scheduled_tasks_provider == "apscheduler" and cls._scheduler is not None

