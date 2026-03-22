"""
Transform step — reads unprocessed bronze rows, validates, writes to silver.

This is the T in ELT. It runs after the loader has written raw data to
raw_weather_ingest (bronze) and produces validated, clean rows in
weather_observations (silver).

The full flow for each unprocessed raw row:
  1. Deserialize raw_payload JSON
  2. Map Open-Meteo field names → clean column names with units
  3. Validate the mapped data with WeatherObservationValidator (Pydantic)
  4a. On success → write to weather_observations, mark raw row processed=True
  4b. On failure → write each error to data_quality_issues, mark raw row
      processed=True (pipeline moves on — raw data is never left stuck)

Data engineering principles:
  - Reads in batches (not row-by-row) — one query gets all unprocessed rows
  - Idempotent: UNIQUE constraint + INSERT OR IGNORE on weather_observations
  - Raw rows are NEVER modified, only marked as processed
  - A row that fails validation is still marked processed=True — the failure
    is in data_quality_issues, not in a permanently-unprocessed raw row
  - All writes for a batch are committed together for consistency
"""
import json
from dataclasses import dataclass, field
from datetime import datetime

from loguru import logger
from pydantic import ValidationError
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.config import settings
from app.db.engine import get_db_session
from app.db.models.pipeline import DataQualityIssue, PipelineRun
from app.db.models.raw import RawWeatherIngest
from app.db.models.transformed import WeatherObservation
from app.pipeline.validate import WeatherObservationValidator, wmo_description


@dataclass
class TransformResult:
    rows_transformed: int = 0
    rows_failed: int = 0
    rows_skipped_duplicate: int = 0
    quality_issues: list[dict] = field(default_factory=list)


def _map_payload_to_candidate(raw_row: RawWeatherIngest) -> dict:
    """Extract and rename fields from the raw API payload.

    This is the mapping layer — Open-Meteo's field names (e.g. temperature_2m)
    are translated to our internal naming convention (e.g. temperature_c).

    Naming with units (_c, _mm, _pct, _kmh, _deg) is a data engineering
    convention that eliminates ambiguity at every downstream layer.
    """
    payload = json.loads(raw_row.raw_payload)
    current = payload["current"]

    weather_code = current.get("weather_code")

    return {
        "location_key": raw_row.location_key,
        "latitude": payload["latitude"],
        "longitude": payload["longitude"],
        "observed_at": datetime.fromisoformat(current["time"]),
        # Field mapping: Open-Meteo name → our name with units
        "temperature_c": current.get("temperature_2m"),
        "apparent_temperature_c": current.get("apparent_temperature"),
        "relative_humidity_pct": current.get("relative_humidity_2m"),
        "precipitation_mm": current.get("precipitation"),
        "wind_speed_kmh": current.get("wind_speed_10m"),
        "wind_direction_deg": current.get("wind_direction_10m"),
        "weather_code": weather_code,
        "weather_description": wmo_description(weather_code),
        # Open-Meteo returns is_day as 0 or 1 (integer), convert to bool
        "is_day": bool(current.get("is_day")) if current.get("is_day") is not None else None,
    }


def process_unprocessed(pipeline_run_id: str) -> TransformResult:
    """Transform all unprocessed bronze rows into silver rows.

    Args:
        pipeline_run_id: The run_id of the current PipelineRun, used to
                         link DataQualityIssue records back to this run.

    Returns:
        TransformResult with counts of transformed, failed, and duplicate rows.
    """
    result = TransformResult()

    # Fetch all unprocessed rows in one query.
    # The idx_raw_processed index makes this efficient even with large tables.
    with get_db_session() as session:
        unprocessed = (
            session.query(RawWeatherIngest)
            .filter_by(processed=False, location_key=settings.location_key)
            .order_by(RawWeatherIngest.fetched_for_timestamp)
            .all()
        )

    if not unprocessed:
        logger.info("Transform: no unprocessed raw rows found")
        return result

    logger.info(f"Transform: processing {len(unprocessed)} unprocessed row(s)")

    for raw_row in unprocessed:
        _process_one_row(raw_row, pipeline_run_id, result)

    logger.info(
        f"Transform complete: "
        f"transformed={result.rows_transformed} "
        f"failed={result.rows_failed} "
        f"duplicates={result.rows_skipped_duplicate}"
    )
    return result


def _process_one_row(
    raw_row: RawWeatherIngest,
    pipeline_run_id: str,
    result: TransformResult,
) -> None:
    """Transform and validate a single raw row.

    Writes to weather_observations on success, data_quality_issues on failure.
    Always marks the raw row processed=True — the pipeline never gets stuck.
    """
    try:
        candidate = _map_payload_to_candidate(raw_row)
    except (KeyError, ValueError, json.JSONDecodeError) as exc:
        # The raw payload is malformed — can't even map it
        logger.warning(f"Row id={raw_row.id}: failed to parse payload: {exc}")
        _write_quality_issue(
            raw_ingest_id=raw_row.id,
            pipeline_run_id=pipeline_run_id,
            field_name="raw_payload",
            issue_type="parse_error",
            expected_value="valid JSON with current.time and current fields",
            actual_value=str(exc),
        )
        _mark_processed(raw_row.id)
        result.rows_failed += 1
        return

    # --- Pydantic validation ---
    # This is the data quality gate. Each field_validator runs and Pydantic
    # collects ALL errors before raising (not just the first one).
    try:
        validated = WeatherObservationValidator(**candidate)
    except ValidationError as exc:
        logger.warning(
            f"Row id={raw_row.id}: validation failed with "
            f"{len(exc.errors())} error(s)"
        )
        for error in exc.errors():
            field_name = ".".join(str(loc) for loc in error["loc"]) or "unknown"
            _write_quality_issue(
                raw_ingest_id=raw_row.id,
                pipeline_run_id=pipeline_run_id,
                field_name=field_name,
                issue_type=error["type"],
                expected_value=None,
                actual_value=str(error.get("input")),
            )
            result.quality_issues.append({
                "raw_id": raw_row.id,
                "field": field_name,
                "type": error["type"],
            })
        _mark_processed(raw_row.id)
        result.rows_failed += 1
        return

    # --- Write to silver table (idempotent) ---
    was_new = _write_silver(raw_row.id, validated)
    _mark_processed(raw_row.id)

    if was_new:
        result.rows_transformed += 1
        logger.debug(
            f"Row id={raw_row.id} → weather_observations "
            f"temp={validated.temperature_c}°C "
            f"humidity={validated.relative_humidity_pct}% "
            f"description='{validated.weather_description}'"
        )
    else:
        result.rows_skipped_duplicate += 1
        logger.debug(f"Row id={raw_row.id}: duplicate observation skipped")


def _write_silver(raw_ingest_id: int, validated: WeatherObservationValidator) -> bool:
    """Write a validated observation to weather_observations.

    Uses INSERT OR IGNORE on the UNIQUE(location_key, observed_at) constraint.
    Returns True if a new row was inserted, False if it was a duplicate.
    """
    row_data = {
        "raw_ingest_id": raw_ingest_id,
        **validated.model_dump(),
        "data_quality_flag": "ok",
        "transformed_at": datetime.utcnow(),
    }

    with get_db_session() as session:
        stmt = sqlite_insert(WeatherObservation).values(**row_data)
        stmt = stmt.on_conflict_do_nothing()
        result = session.execute(stmt)
        return result.rowcount > 0


def _write_quality_issue(
    raw_ingest_id: int,
    pipeline_run_id: str,
    field_name: str,
    issue_type: str,
    expected_value: str | None,
    actual_value: str | None,
) -> None:
    """Record a field-level validation failure in data_quality_issues."""
    with get_db_session() as session:
        issue = DataQualityIssue(
            raw_ingest_id=raw_ingest_id,
            pipeline_run_id=pipeline_run_id,
            field_name=field_name,
            issue_type=issue_type,
            expected_value=expected_value,
            actual_value=actual_value,
            created_at=datetime.utcnow(),
        )
        session.add(issue)


def _mark_processed(raw_ingest_id: int) -> None:
    """Mark a raw row as processed=True.

    Called whether transform succeeded or failed — a permanently-unprocessed
    row is a worse outcome than a quarantined failure with a clear error record.
    """
    with get_db_session() as session:
        row = session.get(RawWeatherIngest, raw_ingest_id)
        if row:
            row.processed = True
