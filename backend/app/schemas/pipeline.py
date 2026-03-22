"""
Pydantic response schemas for pipeline-related API endpoints.

These models define the shape of JSON that the API returns. They are the
outward-facing contract — consumers (the React frontend, curl, Swagger UI)
depend on this schema being stable.

Data engineering concept: API contracts are as important as database schemas.
If you rename a field in the database, the API schema insulates consumers from
that change. The schema is the boundary you version and maintain deliberately.

model_config = {"from_attributes": True} allows these models to be constructed
directly from SQLAlchemy ORM instances via model_validate(orm_obj).
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class PipelineRunResponse(BaseModel):
    """One pipeline run, as returned by GET /api/pipeline/runs."""
    run_id: str
    pipeline_name: str
    triggered_by: str
    location_key: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]
    status: str
    rows_fetched: int
    rows_transformed: int
    rows_failed: int
    error_message: Optional[str]
    duration_seconds: Optional[float]

    model_config = {"from_attributes": True}


class TriggerResponse(BaseModel):
    """Response returned immediately when POST /api/pipeline/trigger is called."""
    message: str
    run_id: str
    status: str
    rows_fetched: int
    rows_transformed: int
    rows_failed: int
    duration_seconds: Optional[float]
    error_message: Optional[str]
