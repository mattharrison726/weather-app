"""
APScheduler configuration — background ingestion scheduler.

Data engineering concept: scheduled pipelines vs on-demand triggers.

In production, pipelines typically run both ways:
  - Scheduled: runs automatically at a fixed cadence (hourly, daily, etc.)
  - On-demand: triggered manually, by an API call, or by an upstream event

This project defaults to on-demand only (SCHEDULER_ENABLED=false). The
scheduler is implemented here as a learning reference and can be enabled via
the SCHEDULER_ENABLED env var when you want automatic background ingestion.

Key APScheduler concepts implemented:
  - IntervalTrigger: fire every N hours (simpler than CronTrigger for this use case)
  - SQLAlchemyJobStore: persists job state in the database across restarts
    (without this, a restarted app doesn't know when the job last ran)
  - ThreadPoolExecutor: runs jobs in a background thread (not the FastAPI thread)
  - max_instances=1: prevents overlapping runs if a job takes longer than expected
  - misfire_grace_time: if the app was down at the scheduled time, run the job
    if it starts within this window — otherwise skip until next interval

See .claude/adr/002-scheduler-apscheduler.md for the technology choice rationale.
"""
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from loguru import logger

from app.config import settings


def _run_scheduled_pipeline() -> None:
    """Wrapper called by APScheduler — runs in a background thread.

    Runs the pipeline for all favorited locations. Each location gets
    its own pipeline_runs audit record.
    """
    from app.pipeline.runner import run_pipeline_for_favorites
    logger.info("Scheduler firing pipeline run for all favorites")
    run_pipeline_for_favorites(triggered_by="scheduler")


def create_scheduler() -> BackgroundScheduler:
    """Build and configure an APScheduler BackgroundScheduler.

    The scheduler is not started here — call scheduler.start() in the
    FastAPI lifespan to control when it begins.
    """
    jobstores = {
        # Store job definitions in SQLite alongside the app data.
        # This means if the app restarts, APScheduler knows when each job
        # last ran and whether any misfires need to be handled.
        "default": SQLAlchemyJobStore(url=settings.database_url),
    }
    executors = {
        # Run jobs in a thread pool (not the main FastAPI event loop thread).
        # max_workers=2 is plenty for a single infrequent job.
        "default": ThreadPoolExecutor(max_workers=2),
    }
    job_defaults = {
        # If a job fires and the previous run is still going, skip rather
        # than stack up multiple concurrent runs.
        "max_instances": 1,
        # If the app was down during a scheduled fire time, run the job
        # if it restarts within this window (in seconds). Otherwise skip.
        "misfire_grace_time": 300,  # 5 minutes
        # Don't try to catch up on misfires beyond the grace time.
        "coalesce": True,
    }

    scheduler = BackgroundScheduler(
        jobstores=jobstores,
        executors=executors,
        job_defaults=job_defaults,
    )

    return scheduler


def start_scheduler(scheduler: BackgroundScheduler) -> None:
    """Start the scheduler and register the ingestion job.

    Only called when SCHEDULER_ENABLED=true. Safe to call on every startup —
    APScheduler's SQLAlchemy job store uses replace_existing=True to avoid
    creating duplicate job definitions across restarts.
    """
    scheduler.start()
    logger.info(
        f"Scheduler started | interval={settings.scheduler_interval_hours}h "
        f"| next run on startup + every {settings.scheduler_interval_hours}h"
    )

    scheduler.add_job(
        func=_run_scheduled_pipeline,
        trigger="interval",
        hours=settings.scheduler_interval_hours,
        id="hourly_weather_ingest",
        name="Weather ingestion",
        replace_existing=True,  # Safe to re-add on restart — updates, doesn't duplicate
    )

    # Trigger one immediate run on startup so the database is populated
    # without waiting for the first interval to elapse.
    logger.info("Scheduler: firing startup run immediately")
    scheduler.add_job(
        func=_run_scheduled_pipeline,
        trigger="date",  # 'date' trigger fires once at a specific time (now = immediately)
        id="startup_run",
        name="Startup weather ingest",
        replace_existing=True,
    )
