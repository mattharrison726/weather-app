"""
Pipeline API routes.

POST /api/pipeline/trigger  — run the ETL pipeline immediately, return the result
GET  /api/pipeline/runs     — return recent pipeline run history

Design note: POST /trigger is synchronous — it runs the pipeline in the request
thread and returns the completed result. For a personal project this is the right
call: simple, no background task complexity, and the pipeline completes in ~1 second.

In a production system with long-running pipelines (minutes or hours), you'd
return a 202 Accepted with a run_id immediately and provide a separate
GET /pipeline/runs/{run_id} polling endpoint. That's the async job pattern.
"""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from app.db.engine import get_db_session
from app.db.models.pipeline import PipelineRun
from app.pipeline.runner import run_pipeline
from app.schemas.pipeline import PipelineRunResponse, TriggerResponse

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


@router.post("/trigger", response_model=TriggerResponse, status_code=200)
def trigger_pipeline():
    """Run the weather ingestion pipeline immediately.

    Fetches current weather from Open-Meteo, writes to the raw table,
    validates and transforms to the clean table, and returns the run summary.

    This is a synchronous endpoint — it blocks until the pipeline completes
    (~0.5–2s depending on network). That's fine for a personal project.
    """
    logger.info("Pipeline trigger received via API")
    try:
        result = run_pipeline(triggered_by="api")
    except Exception as exc:
        # run_pipeline closes its audit record in finally before re-raising,
        # so the pipeline_runs table is always consistent.
        logger.error(f"Pipeline triggered via API failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))

    return TriggerResponse(
        message="Pipeline run complete",
        run_id=result.run_id,
        status=result.status,
        rows_fetched=result.rows_fetched,
        rows_transformed=result.rows_transformed,
        rows_failed=result.rows_failed,
        duration_seconds=result.duration_seconds,
        error_message=result.error_message,
    )


@router.get("/runs", response_model=list[PipelineRunResponse])
def get_pipeline_runs(
    limit: int = Query(default=20, ge=1, le=100),
    status: Optional[str] = Query(default=None),
):
    """Return recent pipeline run history, newest first.

    Query params:
      limit  — number of runs to return (1–100, default 20)
      status — filter by status: 'success', 'failed', 'partial', 'running'
    """
    with get_db_session() as session:
        query = session.query(PipelineRun).order_by(PipelineRun.started_at.desc())
        if status:
            query = query.filter(PipelineRun.status == status)
        runs = query.limit(limit).all()

    return [PipelineRunResponse.model_validate(r) for r in runs]
