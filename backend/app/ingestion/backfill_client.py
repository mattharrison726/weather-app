"""
Open-Meteo Historical Archive client for backfilling past weather data.

Open-Meteo provides a free historical archive API with hourly resolution.
This client fetches a date range and returns each hour as a synthetic
FetchResult — the same shape the regular forecast client returns — so the
existing transform pipeline can process backfill data without any changes.

Data engineering concept: backfill is the process of loading historical data
that predates your pipeline's start date. Good backfill support means you can
bootstrap a new location with years of history, not just data from "when you
added it."

Archive API docs: https://open-meteo.com/en/docs/historical-weather-api
"""
import httpx
from datetime import datetime, timezone
from dataclasses import dataclass
from loguru import logger
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)
import logging

from app.ingestion.client import FetchResult, LocationInfo, _is_retryable

_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

# Same fields as the forecast API, but requested as hourly (not current)
_HOURLY_FIELDS = ",".join([
    "temperature_2m",
    "relative_humidity_2m",
    "apparent_temperature",
    "precipitation",
    "weather_code",
    "wind_speed_10m",
    "wind_direction_10m",
    "is_day",
])


@dataclass
class ArchiveFetchResult:
    """Raw result of a single archive API call covering a date range."""
    url: str
    status_code: int
    payload: dict
    fetched_at: datetime
    location: LocationInfo


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception(_is_retryable),
    before_sleep=before_sleep_log(logging.getLogger("tenacity"), logging.WARNING),
    reraise=True,
)
def fetch_archive(location: LocationInfo, start_date: str, end_date: str) -> ArchiveFetchResult:
    """Fetch hourly archive data for a location over a date range.

    Args:
        location: The location to fetch archive data for.
        start_date: Start date in YYYY-MM-DD format.
        end_date: End date in YYYY-MM-DD format (inclusive).

    Returns an ArchiveFetchResult with the full hourly API response.
    """
    params = {
        "latitude": location.latitude,
        "longitude": location.longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": _HOURLY_FIELDS,
        "timezone": "UTC",
    }

    fetched_at = datetime.now(timezone.utc).replace(tzinfo=None)

    logger.info(
        f"Fetching archive data for {location.name} "
        f"from {start_date} to {end_date}"
    )

    with httpx.Client(timeout=httpx.Timeout(10.0, read=60.0)) as client:
        response = client.get(_ARCHIVE_URL, params=params)
        url = str(response.url)
        logger.debug(f"Archive API response: HTTP {response.status_code} from {url}")
        response.raise_for_status()

    payload = response.json()
    n_hours = len(payload.get("hourly", {}).get("time", []))
    logger.info(f"Archive fetch complete: {n_hours} hourly entries for {location.name}")

    return ArchiveFetchResult(
        url=url,
        status_code=response.status_code,
        payload=payload,
        fetched_at=fetched_at,
        location=location,
    )


def archive_to_fetch_results(archive: ArchiveFetchResult) -> list[FetchResult]:
    """Convert an archive response into a list of per-hour FetchResults.

    Each hourly entry is wrapped into the same "current" payload shape that
    the regular forecast API returns. This lets the existing transform pipeline
    process backfill data without modification.

    Data engineering concept: normalising different source shapes to a common
    internal format at the ingestion boundary keeps downstream logic simple.
    """
    payload = archive.payload
    hourly = payload.get("hourly", {})
    times = hourly.get("time", [])

    if not times:
        logger.warning("Archive payload contains no hourly data")
        return []

    lat = payload.get("latitude", archive.location.latitude)
    lon = payload.get("longitude", archive.location.longitude)

    results: list[FetchResult] = []

    for idx, time_str in enumerate(times):
        # Wrap each hourly entry as a synthetic "current" payload.
        # The transform's _map_payload_to_candidate reads payload["current"],
        # so this synthetic shape is transparent to downstream code.
        synthetic_payload = {
            "latitude": lat,
            "longitude": lon,
            "current": {
                "time": time_str,
                "temperature_2m": _get(hourly, "temperature_2m", idx),
                "relative_humidity_2m": _get(hourly, "relative_humidity_2m", idx),
                "apparent_temperature": _get(hourly, "apparent_temperature", idx),
                "precipitation": _get(hourly, "precipitation", idx),
                "weather_code": _get(hourly, "weather_code", idx),
                "wind_speed_10m": _get(hourly, "wind_speed_10m", idx),
                "wind_direction_10m": _get(hourly, "wind_direction_10m", idx),
                "is_day": _get(hourly, "is_day", idx),
            },
        }

        data_timestamp = datetime.fromisoformat(time_str).replace(tzinfo=None)

        results.append(FetchResult(
            url=archive.url,
            status_code=archive.status_code,
            payload=synthetic_payload,
            fetched_at=archive.fetched_at,
            data_timestamp=data_timestamp,
            location_key=archive.location.location_key,
            location_name=archive.location.name,
        ))

    logger.debug(f"Converted archive response to {len(results)} FetchResult entries")
    return results


def _get(hourly: dict, field: str, idx: int):
    """Safely retrieve hourly[field][idx], returning None if missing."""
    values = hourly.get(field)
    if values is None or idx >= len(values):
        return None
    return values[idx]
