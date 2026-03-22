"""
Open-Meteo HTTP client.

Responsibilities:
  - Build the request URL from configured lat/lon
  - Make the HTTP GET request
  - Retry on transient failures (5xx, network errors) using tenacity
  - Return a typed result dict — NOT responsible for writing to the database

Data engineering concept: the client is stateless and knows nothing about the
database. It has one job — fetch data and return it. This makes it independently
testable and swappable (change the API provider without touching the loader).

Retry strategy: exponential backoff, 3 attempts max.
  - Transient errors (5xx, network) → retry
  - Permanent errors (4xx) → fail immediately; retrying won't help

See .claude/adr/004-retry-strategy.md for the full decision rationale.
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

from app.config import settings

# Open-Meteo base URL
_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# Current conditions fields we request from Open-Meteo
_CURRENT_FIELDS = ",".join([
    "temperature_2m",
    "relative_humidity_2m",
    "apparent_temperature",
    "precipitation",
    "weather_code",
    "wind_speed_10m",
    "wind_direction_10m",
    "is_day",
])


def _is_retryable(exc: BaseException) -> bool:
    """Determine whether an exception warrants a retry.

    Data engineering principle: distinguish transient from permanent errors.
    - Transient (worth retrying): server errors (5xx), network failures
    - Permanent (not worth retrying): client errors (4xx) — retrying won't fix them

    Retrying a 400 Bad Request is always wrong; it wastes time and can
    worsen rate-limiting situations.
    """
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500
    if isinstance(exc, httpx.RequestError):
        # Covers: ConnectTimeout, ReadTimeout, ConnectError, etc.
        return True
    return False


@dataclass
class FetchResult:
    """The raw result of a single Open-Meteo API call.

    Keeping this as a dataclass (rather than a raw dict) makes the contract
    between the client and loader explicit and type-checked.
    """
    url: str
    status_code: int
    payload: dict          # full parsed JSON response
    fetched_at: datetime   # UTC timestamp of when we called the API
    data_timestamp: datetime  # UTC timestamp the weather data represents


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception(_is_retryable),
    before_sleep=before_sleep_log(logging.getLogger("tenacity"), logging.WARNING),
    reraise=True,
)
def fetch_weather() -> FetchResult:
    """Fetch current weather conditions from Open-Meteo.

    Returns a FetchResult with the full API response payload.
    Raises httpx.HTTPStatusError on non-retryable HTTP errors.
    Raises httpx.RequestError (after 3 attempts) on network failures.

    The @retry decorator handles up to 3 attempts with exponential backoff
    (1s, 2s, 4s wait between attempts) for transient errors only.
    """
    params = {
        "latitude": settings.weather_latitude,
        "longitude": settings.weather_longitude,
        "current": _CURRENT_FIELDS,
        "timezone": "UTC",
        "forecast_days": 1,
    }

    fetched_at = datetime.now(timezone.utc).replace(tzinfo=None)  # store as naive UTC

    logger.debug(f"Fetching weather from Open-Meteo for {settings.weather_location_name}")

    with httpx.Client(timeout=httpx.Timeout(5.0, read=30.0)) as client:
        response = client.get(_FORECAST_URL, params=params)
        url = str(response.url)
        logger.debug(f"Open-Meteo response: HTTP {response.status_code} from {url}")

        # Raise for 4xx/5xx — tenacity will decide whether to retry based on status code
        response.raise_for_status()

    payload = response.json()

    # Parse the data timestamp from the response body.
    # Open-Meteo returns "current.time" as an ISO 8601 string in UTC.
    raw_time = payload["current"]["time"]  # e.g. "2024-01-15T14:00"
    data_timestamp = datetime.fromisoformat(raw_time).replace(tzinfo=None)

    logger.info(
        f"Fetched weather for {settings.weather_location_name} "
        f"at data_timestamp={data_timestamp.isoformat()}"
    )

    return FetchResult(
        url=url,
        status_code=response.status_code,
        payload=payload,
        fetched_at=fetched_at,
        data_timestamp=data_timestamp,
    )
