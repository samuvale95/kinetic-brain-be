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


def run_strava_token_exchange_and_sync(user_id: int, code: str, state: str) -> None:
    """
    Background task to exchange Strava authorization code for token and start sync.
    This is completely async - the callback responds immediately.
    
    Args:
        user_id: User ID
        code: Strava authorization code
        state: Encoded state parameter (contains user_id and mobile_redirect_uri)
    """
    db = SessionLocal()
    service = StravaService(db)
    
    try:
        logger.info(
            f"[TOKEN_EXCHANGE][JOB] Starting token exchange and sync for user {user_id}"
        )
        
        # Exchange code for token (this creates/updates the Strava account)
        result = service.exchange_code_for_token(
            code=code,
            user_id=user_id
        )
        
        logger.info(
            f"[TOKEN_EXCHANGE][JOB] Token exchange successful for user {user_id} "
            f"(account={result.get('strava_account_id')}, first_connection={result.get('is_first_connection')})"
        )
        
        # If first connection, start sync
        if result.get("initial_sync_required"):
            sync_job = service.create_sync_job(
                user_id=user_id,
                strava_account_id=result["strava_account_id"],
                job_type="initial_sync",
                status_message="Initial Strava synchronization queued",
                requested_days_back=30,  # Optimized: only sync last 30 days
            )
            
            logger.info(
                f"[TOKEN_EXCHANGE][JOB] Created sync job {sync_job.id} for user {user_id}, starting sync..."
            )
            
            # Start sync in background
            service.sync_user_activities(
                user_id=user_id,
                days_back=30,  # Optimized: only sync last 30 days
                job=sync_job,
            )
            
            logger.info(
                f"[TOKEN_EXCHANGE][JOB] Sync completed for user {user_id}, job {sync_job.id}"
            )
        else:
            logger.info(
                f"[TOKEN_EXCHANGE][JOB] Reconnection for user {user_id}, no sync needed"
            )
            
    except Exception as exc:
        logger.exception(f"[TOKEN_EXCHANGE][JOB] Token exchange failed for user {user_id}: {exc}")
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

