"""
Pipeline API routes.

POST /api/pipeline/trigger             — run the ETL pipeline (all favorites or one location)
POST /api/pipeline/backfill            — backfill historical data for a location
GET  /api/pipeline/runs                — return recent pipeline run history
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from app.db.engine import get_db_session
from app.db.models.pipeline import PipelineRun
from app.ingestion.client import LocationInfo
from app.locations.catalog import CATALOG_BY_KEY
from app.pipeline.runner import run_pipeline, run_pipeline_for_favorites
from app.schemas.locations import BackfillRequest, BackfillResponse
from app.schemas.pipeline import PipelineRunResponse, TriggerResponse

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


def _resolve_location_for_pipeline(location_key: str) -> LocationInfo:
    """Look up a location for pipeline use (catalog or favorites)."""
    # Check catalog first
    city = CATALOG_BY_KEY.get(location_key)
    if city:
        return LocationInfo(
            location_key=city.location_key,
            name=city.name,
            latitude=city.latitude,
            longitude=city.longitude,
        )

    # Fall back to favorites table
    from app.db.models.locations import Location
    with get_db_session() as session:
        loc = session.get(Location, location_key)
        if loc:
            return LocationInfo(
                location_key=loc.location_key,
                name=loc.name,
                latitude=loc.latitude,
                longitude=loc.longitude,
            )

    raise HTTPException(
        status_code=404,
        detail=f"Location '{location_key}' not found in catalog or favorites.",
    )


@router.post("/trigger", response_model=list[TriggerResponse], status_code=200)
def trigger_pipeline(
    location_key: Optional[str] = Query(default=None),
):
    """Run the weather ingestion pipeline immediately.

    If location_key is provided: runs for that one location only.
    If not: runs for all favorited locations.

    Returns a list of run summaries (one per location triggered).
    This is synchronous — it blocks until all runs complete (~1s per location).
    """
    logger.info(
        "Pipeline trigger received via API"
        + (f" for location_key={location_key}" if location_key else " for all favorites")
    )

    try:
        if location_key:
            location = _resolve_location_for_pipeline(location_key)
            results = [run_pipeline(location, triggered_by="api")]
        else:
            results = run_pipeline_for_favorites(triggered_by="api")

        if not results:
            raise HTTPException(
                status_code=422,
                detail=(
                    "No favorites configured. Add at least one location via "
                    "POST /api/locations/favorites/{location_key} first."
                ),
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Pipeline trigger failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))

    return [
        TriggerResponse(
            message="Pipeline run complete",
            run_id=r.run_id,
            status=r.status,
            rows_fetched=r.rows_fetched,
            rows_transformed=r.rows_transformed,
            rows_failed=r.rows_failed,
            duration_seconds=r.duration_seconds,
            error_message=r.error_message,
        )
        for r in results
    ]


@router.post("/backfill", response_model=BackfillResponse, status_code=200)
def run_backfill(request: BackfillRequest):
    """Backfill historical weather data for a location.

    Fetches hourly data from the Open-Meteo archive API for the given date range
    and writes it through the full ETL pipeline (bronze → silver).

    Data is idempotent — re-running backfill for the same range is safe.

    Request body:
        location_key  — e.g. "51.5074,-0.1278"
        start_date    — YYYY-MM-DD
        end_date      — YYYY-MM-DD

    Note: large date ranges (e.g. a full year = 8760 hourly entries) may take
    several seconds. The endpoint is synchronous.
    """
    from app.ingestion.backfill_client import fetch_archive, archive_to_fetch_results
    from app.ingestion.loader import write_raw
    from app.pipeline.transform import process_unprocessed
    import uuid

    location = _resolve_location_for_pipeline(request.location_key)

    logger.info(
        f"Backfill starting | location={location.name} "
        f"range={request.start_date} to {request.end_date}"
    )

    started_at = datetime.now(timezone.utc)

    try:
        archive = fetch_archive(location, request.start_date, request.end_date)
        fetch_results = archive_to_fetch_results(archive)
    except Exception as exc:
        logger.error(f"Backfill fetch failed for {location.name}: {exc}")
        raise HTTPException(status_code=502, detail=f"Archive API error: {exc}")

    rows_written = 0
    rows_skipped = 0

    for fr in fetch_results:
        try:
            load_result = write_raw(fr)
            if load_result.was_new:
                rows_written += 1
            else:
                rows_skipped += 1
        except Exception as exc:
            logger.warning(f"Backfill load failed for timestamp {fr.data_timestamp}: {exc}")
            rows_skipped += 1

    # Run transform for all newly loaded rows
    run_id = str(uuid.uuid4())
    transform_result = process_unprocessed(
        pipeline_run_id=run_id,
        location_key=location.location_key,
    )

    duration = (datetime.now(timezone.utc) - started_at).total_seconds()

    logger.info(
        f"Backfill complete | location={location.name} "
        f"written={rows_written} skipped={rows_skipped} "
        f"transformed={transform_result.rows_transformed} "
        f"failed={transform_result.rows_failed} "
        f"duration={duration:.1f}s"
    )

    return BackfillResponse(
        location_key=location.location_key,
        location_name=location.name,
        start_date=request.start_date,
        end_date=request.end_date,
        rows_written=rows_written,
        rows_skipped=rows_skipped,
        rows_transformed=transform_result.rows_transformed,
        rows_failed=transform_result.rows_failed,
        duration_seconds=duration,
    )


@router.get("/runs", response_model=list[PipelineRunResponse])
def get_pipeline_runs(
    limit: int = Query(default=20, ge=1, le=100),
    status: Optional[str] = Query(default=None),
    location_key: Optional[str] = Query(default=None),
):
    """Return recent pipeline run history, newest first.

    Query params:
      limit        — number of runs to return (1–100, default 20)
      status       — filter by status: 'success', 'failed', 'partial', 'running'
      location_key — filter by location
    """
    with get_db_session() as session:
        query = session.query(PipelineRun).order_by(PipelineRun.started_at.desc())
        if status:
            query = query.filter(PipelineRun.status == status)
        if location_key:
            query = query.filter(PipelineRun.location_key == location_key)
        runs = query.limit(limit).all()

    return [PipelineRunResponse.model_validate(r) for r in runs]
