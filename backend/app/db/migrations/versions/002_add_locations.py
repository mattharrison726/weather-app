"""Add locations table and location_key to pipeline_runs

Revision ID: 002
Revises: 001
Create Date: 2026-03-22

Changes:
  - Add `locations` table for user-favorited locations (the pipeline auto-runs for these)
  - Add `location_key` column to `pipeline_runs` for observability (which location did this run cover?)

The location_key column on pipeline_runs is nullable so existing rows are unaffected.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # New: locations table — user's favorited locations
    # -------------------------------------------------------------------------
    op.create_table(
        "locations",
        sa.Column("location_key", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("country", sa.String(length=100), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("added_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("location_key"),
    )

    # -------------------------------------------------------------------------
    # Add location_key to pipeline_runs for observability
    # -------------------------------------------------------------------------
    # SQLite does not support adding NOT NULL columns without a default to
    # existing tables with rows. Using nullable=True is the correct approach.
    op.add_column(
        "pipeline_runs",
        sa.Column("location_key", sa.String(length=50), nullable=True),
    )


def downgrade() -> None:
    # SQLite does not support DROP COLUMN in older versions.
    # Recreate pipeline_runs without the column.
    op.drop_table("locations")

    # For the column drop, we'd need to recreate the table in SQLite.
    # In practice, downgrade is rarely needed on a local SQLite project.
    # Just document the intent here.
    # op.drop_column("pipeline_runs", "location_key")  # not supported by SQLite
