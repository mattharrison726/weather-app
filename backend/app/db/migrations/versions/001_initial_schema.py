"""Initial schema: all four tables

Revision ID: 001
Revises:
Create Date: 2026-03-22

This migration creates the full initial schema:
  - raw_weather_ingest   (Bronze / landing zone)
  - weather_observations (Silver / serving layer)
  - pipeline_runs        (Audit / observability)
  - data_quality_issues  (Quarantine)

Data engineering note: every schema change going forward should be a NEW migration
file — never edit this file after it has been applied. Alembic tracks which
migrations have run via the alembic_version table and applies only new ones.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # Bronze layer: raw API responses, exactly as received
    # -------------------------------------------------------------------------
    op.create_table(
        "raw_weather_ingest",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("location_key", sa.String(length=50), nullable=False),
        sa.Column("fetched_at", sa.DateTime(), nullable=False),
        sa.Column("fetched_for_timestamp", sa.DateTime(), nullable=False),
        sa.Column("api_url", sa.Text(), nullable=False),
        sa.Column("response_status_code", sa.Integer(), nullable=False),
        sa.Column("raw_payload", sa.Text(), nullable=False),
        sa.Column("schema_version", sa.String(length=20), nullable=False),
        sa.Column("processed", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "location_key", "fetched_for_timestamp", name="uq_raw_location_timestamp"
        ),
    )
    op.create_index("idx_raw_processed", "raw_weather_ingest", ["processed", "location_key"])
    op.create_index("idx_raw_fetched_for", "raw_weather_ingest", ["fetched_for_timestamp"])

    # -------------------------------------------------------------------------
    # Audit layer: one row per pipeline execution
    # -------------------------------------------------------------------------
    op.create_table(
        "pipeline_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("pipeline_name", sa.String(length=100), nullable=False),
        sa.Column("triggered_by", sa.String(length=50), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("rows_fetched", sa.Integer(), nullable=False),
        sa.Column("rows_transformed", sa.Integer(), nullable=False),
        sa.Column("rows_failed", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id"),
    )
    op.create_index("idx_runs_pipeline_name", "pipeline_runs", ["pipeline_name", "started_at"])
    op.create_index("idx_runs_status", "pipeline_runs", ["status"])

    # -------------------------------------------------------------------------
    # Silver layer: validated, typed, clean observations
    # -------------------------------------------------------------------------
    op.create_table(
        "weather_observations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("raw_ingest_id", sa.Integer(), nullable=False),
        sa.Column("location_key", sa.String(length=50), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("observed_at", sa.DateTime(), nullable=False),
        sa.Column("temperature_c", sa.Float(), nullable=True),
        sa.Column("apparent_temperature_c", sa.Float(), nullable=True),
        sa.Column("relative_humidity_pct", sa.Integer(), nullable=True),
        sa.Column("precipitation_mm", sa.Float(), nullable=True),
        sa.Column("wind_speed_kmh", sa.Float(), nullable=True),
        sa.Column("wind_direction_deg", sa.Integer(), nullable=True),
        sa.Column("weather_code", sa.Integer(), nullable=True),
        sa.Column("weather_description", sa.String(length=100), nullable=True),
        sa.Column("is_day", sa.Boolean(), nullable=True),
        sa.Column("data_quality_flag", sa.String(length=20), nullable=False),
        sa.Column("transformed_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["raw_ingest_id"], ["raw_weather_ingest.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "location_key", "observed_at", name="uq_obs_location_timestamp"
        ),
    )
    op.create_index("idx_obs_location_time", "weather_observations", ["location_key", "observed_at"])
    op.create_index("idx_obs_observed_at", "weather_observations", ["observed_at"])

    # -------------------------------------------------------------------------
    # Quarantine layer: field-level validation failures
    # -------------------------------------------------------------------------
    op.create_table(
        "data_quality_issues",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("raw_ingest_id", sa.Integer(), nullable=False),
        sa.Column("pipeline_run_id", sa.String(length=36), nullable=False),
        sa.Column("field_name", sa.String(length=100), nullable=False),
        sa.Column("issue_type", sa.String(length=50), nullable=False),
        sa.Column("expected_value", sa.Text(), nullable=True),
        sa.Column("actual_value", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["raw_ingest_id"], ["raw_weather_ingest.id"]),
        sa.ForeignKeyConstraint(["pipeline_run_id"], ["pipeline_runs.run_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_dqi_raw_ingest", "data_quality_issues", ["raw_ingest_id"])
    op.create_index("idx_dqi_pipeline_run", "data_quality_issues", ["pipeline_run_id"])


def downgrade() -> None:
    # Drop in reverse order of creation to respect foreign key dependencies
    op.drop_table("data_quality_issues")
    op.drop_table("weather_observations")
    op.drop_table("pipeline_runs")
    op.drop_table("raw_weather_ingest")
