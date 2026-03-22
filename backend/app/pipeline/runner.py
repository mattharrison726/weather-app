"""
Pipeline runner — orchestrates the full ETL cycle.

This is the top-level coordinator. It:
  1. Creates a pipeline_runs audit record at the start (status='running')
  2. Calls Extract (client.fetch_weather)
  3. Calls Load (loader.write_raw)
  4. Calls Transform (transform.process_unprocessed) — stub in Phase 2
  5. Closes the audit record with final status, row counts, and duration

Data engineering principle: the try/finally block guarantees the audit record
is ALWAYS closed, even if the pipeline crashes. A pipeline_run row stuck in
status='running' after restart is a detectable, alertable anomaly.

Usage:
    From the command line (manual trigger):
        cd backend/
        python -m app.pipeline.runner

    Programmatically:
        from app.pipeline.runner import run_pipeline
        run_pipeline(triggered_by="manual")
"""
import uuid
from datetime import datetime, timezone

from loguru import logger

from app.db.engine import get_db_session
from app.db.models.pipeline import PipelineRun
from app.ingestion.client import fetch_weather
from app.ingestion.loader import write_raw


def run_pipeline(triggered_by: str = "manual") -> PipelineRun:
    """Execute one full ETL pipeline run.

    Args:
        triggered_by: Label for what triggered this run.
                      One of: 'manual', 'scheduler', 'startup', 'backfill'

    Returns:
        The completed PipelineRun ORM object with final status and row counts.

    Raises:
        Any exception from the ETL steps — the audit record is always closed
        via the finally block before the exception propagates.
    """
    run_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc).replace(tzinfo=None)

    logger.info(f"Pipeline starting | run_id={run_id} triggered_by={triggered_by}")

    # --- Create the audit record BEFORE doing any work ---
    # This ensures we always have a record of the attempt, even if we crash.
    with get_db_session() as session:
        pipeline_run = PipelineRun(
            run_id=run_id,
            pipeline_name="hourly_weather_ingest",
            triggered_by=triggered_by,
            started_at=started_at,
            status="running",
            rows_fetched=0,
            rows_transformed=0,
            rows_failed=0,
            created_at=started_at,
        )
        session.add(pipeline_run)

    rows_fetched = 0
    rows_transformed = 0
    rows_failed = 0
    final_status = "success"
    error_message = None

    try:
        # ----------------------------------------------------------------
        # EXTRACT: call the Open-Meteo API
        # ----------------------------------------------------------------
        logger.info(f"[{run_id}] Step 1/3: Extract — calling Open-Meteo API")
        fetch_result = fetch_weather()

        # ----------------------------------------------------------------
        # LOAD: write raw JSON to the bronze table (idempotent)
        # ----------------------------------------------------------------
        logger.info(f"[{run_id}] Step 2/3: Load — writing to raw_weather_ingest")
        load_result = write_raw(fetch_result)

        if load_result.was_new:
            rows_fetched = 1
            logger.info(f"[{run_id}] New raw row inserted (id={load_result.raw_ingest_id})")
        else:
            logger.info(
                f"[{run_id}] Duplicate row skipped — data already ingested for this timestamp"
            )

        # ----------------------------------------------------------------
        # TRANSFORM: raw → clean (implemented in Phase 3)
        # ----------------------------------------------------------------
        logger.info(f"[{run_id}] Step 3/3: Transform — (stub, implemented in Phase 3)")
        # Phase 3 will call:
        #   from app.pipeline.transform import process_unprocessed
        #   transform_result = process_unprocessed(pipeline_run_id=run_id)
        #   rows_transformed = transform_result.rows_transformed
        #   rows_failed = transform_result.rows_failed
        rows_transformed = 0

        # Determine final status
        if rows_failed > 0 and rows_transformed > 0:
            final_status = "partial"  # some succeeded, some failed
        elif rows_failed > 0 and rows_transformed == 0:
            final_status = "failed"
        else:
            final_status = "success"

    except Exception as exc:
        final_status = "failed"
        error_message = str(exc)
        logger.exception(f"[{run_id}] Pipeline failed: {exc}")
        raise

    finally:
        # --- Always close the audit record, even on exception ---
        completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        duration_seconds = (completed_at - started_at).total_seconds()

        with get_db_session() as session:
            run = session.query(PipelineRun).filter_by(run_id=run_id).one()
            run.completed_at = completed_at
            run.status = final_status
            run.rows_fetched = rows_fetched
            run.rows_transformed = rows_transformed
            run.rows_failed = rows_failed
            run.error_message = error_message
            run.duration_seconds = duration_seconds

        logger.info(
            f"Pipeline complete | run_id={run_id} status={final_status} "
            f"fetched={rows_fetched} transformed={rows_transformed} "
            f"failed={rows_failed} duration={duration_seconds:.2f}s"
        )

    # Return the final state of the pipeline run record
    with get_db_session() as session:
        return session.query(PipelineRun).filter_by(run_id=run_id).one()


if __name__ == "__main__":
    """Allow running the pipeline directly: python -m app.pipeline.runner"""
    import sys
    from loguru import logger
    from app.config import settings

    # Configure loguru for human-readable console output when running manually
    logger.remove()
    logger.add(sys.stdout, level=settings.log_level, colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}")

    logger.info(f"Manual pipeline trigger | location={settings.weather_location_name}")
    result = run_pipeline(triggered_by="manual")

    print()
    print("=" * 60)
    print(f"  Pipeline Run Summary")
    print("=" * 60)
    print(f"  run_id:      {result.run_id}")
    print(f"  status:      {result.status}")
    print(f"  fetched:     {result.rows_fetched} row(s)")
    print(f"  transformed: {result.rows_transformed} row(s)  (Phase 3)")
    print(f"  failed:      {result.rows_failed} row(s)")
    print(f"  duration:    {result.duration_seconds:.2f}s")
    print("=" * 60)
    if result.error_message:
        print(f"  ERROR: {result.error_message}")
        sys.exit(1)
