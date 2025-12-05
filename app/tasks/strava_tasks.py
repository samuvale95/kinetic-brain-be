from datetime import datetime, timezone

from loguru import logger

from app.database import SessionLocal
from app.models.strava import StravaSyncJobStatus
from app.services.strava_service import StravaService
from app.services.metrics_orchestrator import process_metrics_jobs


def run_strava_sync_job(job_id: int, days_back: int = 30) -> None:
    """
    Background task to execute a Strava sync job without blocking the request thread.
    """
    db = SessionLocal()
    service = StravaService(db)
    job = None

    try:
        job = service.get_sync_job(job_id)
        if not job:
            logger.error(f"[SYNC][JOB] Job {job_id} not found, aborting")
            return

        logger.info(
            f"[SYNC][JOB] Starting background sync job {job_id} "
            f"(user={job.user_id}, days_back={days_back})"
        )

        service.sync_user_activities(
            user_id=job.user_id,
            days_back=days_back,
            job=job,
        )
    except Exception as exc:
        logger.exception(f"[SYNC][JOB] Job {job_id} failed: {exc}")
        if job:
            try:
                service._update_sync_job(
                    job,
                    status=StravaSyncJobStatus.FAILED,
                    status_message="Sync failed",
                    error=str(exc),
                    finished_at=datetime.now(timezone.utc),
                )
            except Exception as update_exc:
                logger.error(
                    f"[SYNC][JOB] Failed to update status for job {job_id}: {update_exc}"
                )
        db.rollback()
    finally:
        db.close()


def run_recalculate_metrics_job(job_id: int, months_back: int = 12) -> None:
    """
    Background task to execute a metrics recalculation job without blocking the request thread.
    
    Args:
        job_id: Job ID to execute
        months_back: Number of months to look back for activities (default: 12)
    """
    db = SessionLocal()
    service = StravaService(db)
    job = None

    try:
        job = service.get_sync_job(job_id)
        if not job:
            logger.error(f"[RECALC][JOB] Job {job_id} not found, aborting")
            return

        logger.info(
            f"[RECALC][JOB] Starting background recalculation job {job_id} "
            f"(user={job.user_id}, months_back={months_back})"
        )

        service.recalculate_all_metrics(
            user_id=job.user_id,
            job=job,
            months_back=months_back,
        )
    except Exception as exc:
        logger.exception(f"[RECALC][JOB] Job {job_id} failed: {exc}")
        if job:
            try:
                service._update_sync_job(
                    job,
                    status=StravaSyncJobStatus.FAILED,
                    status_message="Recalculation failed",
                    error=str(exc),
                    finished_at=datetime.now(timezone.utc),
                )
            except Exception as update_exc:
                logger.error(
                    f"[RECALC][JOB] Failed to update status for job {job_id}: {update_exc}"
                )
        db.rollback()
    finally:
        db.close()


def run_metrics_jobs_once(limit: int = 3) -> None:
    """
    Esegue una singola scansione/processing della coda metrics senza bloccare la request.
    Da usare con FastAPI BackgroundTasks dopo un enqueue per garantire latenza bassa.
    """
    db = SessionLocal()
    try:
        process_metrics_jobs(db, limit=limit)
    except Exception as exc:
        logger.exception(f"[ADV_METRICS][JOB] Processing failed: {exc}")
        db.rollback()
    finally:
        db.close()


def run_disconnect_cleanup_job(user_id: int, activity_dates: list) -> None:
    """
    Background task to clean up after Strava account disconnection.
    Recalculates daily metrics for affected dates without blocking the request.
    
    This is optimized for scalability: instead of blocking the HTTP response for
    minutes while recalculating metrics for potentially hundreds of dates, we
    do it asynchronously in the background.
    
    Args:
        user_id: User ID
        activity_dates: List of dates (date objects) that had activities and need
                       daily metrics recalculation
    """
    db = SessionLocal()
    try:
        logger.info(
            f"[DISCONNECT][CLEANUP] Starting cleanup for user {user_id} "
            f"({len(activity_dates)} dates to update)"
        )
        
        from app.services.daily_metrics_service import DailyMetricsService
        daily_metrics_service = DailyMetricsService(db)
        
        updated_count = 0
        errors_count = 0
        
        for activity_date in activity_dates:
            try:
                daily_metrics_service.update_daily_metrics(user_id, activity_date)
                updated_count += 1
            except Exception as e:
                logger.warning(
                    f"[DISCONNECT][CLEANUP] Failed to update daily metrics "
                    f"for {activity_date} after disconnect: {e}"
                )
                errors_count += 1
        
        db.commit()
        logger.info(
            f"[DISCONNECT][CLEANUP] Completed cleanup for user {user_id}: "
            f"{updated_count}/{len(activity_dates)} dates updated successfully "
            f"({errors_count} errors)"
        )
    except Exception as exc:
        logger.exception(f"[DISCONNECT][CLEANUP] Cleanup failed for user {user_id}: {exc}")
        db.rollback()
    finally:
        db.close()

