"""
Audit and observability layer: pipeline_runs and data_quality_issues tables.

pipeline_runs: one row per pipeline execution. Never left in 'running' status —
the runner uses try/finally to always close the record. A 'running' row after
startup indicates a crashed process.

data_quality_issues: field-level validation failures quarantined by the transform.
The pipeline continues processing — failures don't crash the run.
"""
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.engine import Base


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # UUID string — used in API responses and cross-table references.
    # A human-readable, stable identifier that doesn't leak internal IDs.
    run_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)

    # Which pipeline ran? Allows multiple pipelines to share this table.
    pipeline_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # What triggered this run?
    triggered_by: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'scheduler', 'manual', 'backfill', 'startup', 'api'

    # Which location did this run cover? Nullable for backward compat with existing rows.
    location_key: Mapped[str | None] = mapped_column(String(50), nullable=True)

    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Status lifecycle: running → success | failed | partial
    # 'partial' = some rows succeeded, some failed (data quality issues)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")

    # Row counts — these become the KPIs you monitor over time
    rows_fetched: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_transformed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # NULL on success; populated on failure with the exception message
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # How long did this run take? Useful for detecting performance regressions.
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    __table_args__ = (
        Index("idx_runs_pipeline_name", "pipeline_name", "started_at"),
        Index("idx_runs_status", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<PipelineRun run_id={self.run_id} status={self.status} "
            f"fetched={self.rows_fetched} transformed={self.rows_transformed}>"
        )


class DataQualityIssue(Base):
    __tablename__ = "data_quality_issues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Which raw row had the issue?
    raw_ingest_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("raw_weather_ingest.id"), nullable=False
    )

    # Which pipeline run caught this issue?
    pipeline_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("pipeline_runs.run_id"), nullable=False
    )

    # Which field failed validation?
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # What kind of failure?
    # 'missing' = required field absent in the API response
    # 'out_of_range' = value outside plausible bounds (e.g., temp > 60°C)
    # 'type_error' = value is not the expected type
    issue_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # What did we expect / what did we get?
    expected_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    actual_value: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    __table_args__ = (
        Index("idx_dqi_raw_ingest", "raw_ingest_id"),
        Index("idx_dqi_pipeline_run", "pipeline_run_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<DataQualityIssue raw_id={self.raw_ingest_id} "
            f"field={self.field_name} type={self.issue_type}>"
        )
