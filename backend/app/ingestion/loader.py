"""
Raw data loader — writes to the bronze (landing zone) table.

Responsibilities:
  - Accept a FetchResult from the client
  - Serialize the full payload to JSON
  - Write one row to raw_weather_ingest
  - Enforce idempotency via INSERT OR IGNORE against the UNIQUE constraint
  - Return whether the row was new or a duplicate

Data engineering principles demonstrated here:
  1. Raw data is NEVER modified or filtered — the full JSON blob is stored
  2. Idempotency: running the loader twice with the same data is a safe no-op
  3. The loader knows nothing about transformation — that's a separate concern

The UNIQUE constraint on (location_key, fetched_for_timestamp) is the
source of truth for idempotency. The INSERT OR IGNORE is how we leverage it.
"""
import json
from dataclasses import dataclass

from loguru import logger
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.db.engine import get_db_session
from app.db.models.raw import RawWeatherIngest
from app.ingestion.client import FetchResult

# Schema version string — bump this if Open-Meteo changes their response format.
# Rows with old schema versions can be identified and reprocessed with new logic.
SCHEMA_VERSION = "1.0"


@dataclass
class LoadResult:
    """Result of a single load operation."""
    was_new: bool          # True if row was inserted, False if it was a duplicate
    raw_ingest_id: int     # ID of the row (new or existing)


def write_raw(fetch_result: FetchResult) -> LoadResult:
    """Write a raw API response to the bronze table.

    Uses INSERT OR IGNORE (via SQLAlchemy's on_conflict_do_nothing) to
    enforce idempotency. If a row for this location + data_timestamp already
    exists, the insert is silently skipped.

    The location_key is taken directly from fetch_result (set by the client),
    so the loader doesn't need to read from global settings.

    Returns a LoadResult indicating whether this was a new row or a duplicate.
    """
    location_key = fetch_result.location_key

    row_data = {
        "location_key": location_key,
        "fetched_at": fetch_result.fetched_at,
        "fetched_for_timestamp": fetch_result.data_timestamp,
        "api_url": fetch_result.url,
        "response_status_code": fetch_result.status_code,
        # Store the full JSON payload as a string — no fields are dropped
        "raw_payload": json.dumps(fetch_result.payload),
        "schema_version": SCHEMA_VERSION,
        "processed": False,
        "created_at": fetch_result.fetched_at,
    }

    with get_db_session() as session:
        stmt = sqlite_insert(RawWeatherIngest).values(**row_data)
        # on_conflict_do_nothing: if the UNIQUE constraint fires, skip silently
        stmt = stmt.on_conflict_do_nothing()
        result = session.execute(stmt)

        was_new = result.rowcount > 0

        if was_new:
            # Fetch the ID of the row we just inserted
            raw_row = session.query(RawWeatherIngest).filter_by(
                location_key=location_key,
                fetched_for_timestamp=fetch_result.data_timestamp,
            ).one()
            raw_ingest_id = raw_row.id
            logger.info(
                f"Loaded new raw row id={raw_ingest_id} "
                f"location={location_key} "
                f"data_ts={fetch_result.data_timestamp.isoformat()}"
            )
        else:
            # Row already exists — find its ID for the return value
            existing = session.query(RawWeatherIngest).filter_by(
                location_key=location_key,
                fetched_for_timestamp=fetch_result.data_timestamp,
            ).one()
            raw_ingest_id = existing.id
            logger.info(
                f"Duplicate raw row skipped (idempotent) id={raw_ingest_id} "
                f"data_ts={fetch_result.data_timestamp.isoformat()}"
            )

    return LoadResult(was_new=was_new, raw_ingest_id=raw_ingest_id)
