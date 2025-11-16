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

