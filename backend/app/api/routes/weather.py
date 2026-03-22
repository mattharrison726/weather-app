"""
Weather data API routes.

GET /api/weather/current  — most recent clean observation for a location
GET /api/weather/history  — paginated observation history with date filters
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.db.engine import get_db_session
from app.db.models.locations import Location
from app.db.models.transformed import WeatherObservation
from app.schemas.weather import CurrentWeatherResponse, WeatherObservationResponse

router = APIRouter(prefix="/api/weather", tags=["weather"])


def _resolve_location_key(location_key: Optional[str]) -> tuple[str, str, float, float]:
    """Resolve a location_key to (key, name, lat, lon).

    If location_key is provided, look it up in favorites.
    If not provided, use the first favorite alphabetically.
    Raises HTTPException 404 if no location can be resolved.
    """
    with get_db_session() as session:
        if location_key:
            loc = session.get(Location, location_key)
            if loc is None:
                # Try to find any observation for this key (location might not be in favorites
                # but could have data from a one-off trigger)
                from app.locations.catalog import CATALOG_BY_KEY
                city = CATALOG_BY_KEY.get(location_key)
                if city:
                    return city.location_key, city.name, city.latitude, city.longitude
                raise HTTPException(
                    status_code=404,
                    detail=f"Location '{location_key}' not found."
                )
            return loc.location_key, loc.name, loc.latitude, loc.longitude
        else:
            # Default: first favorite alphabetically
            loc = session.query(Location).order_by(Location.name).first()
            if loc is None:
                # Fall back to settings if no favorites exist yet
                from app.config import settings
                return (
                    settings.location_key,
                    settings.weather_location_name,
                    settings.weather_latitude,
                    settings.weather_longitude,
                )
            return loc.location_key, loc.name, loc.latitude, loc.longitude


@router.get("/current", response_model=CurrentWeatherResponse)
def get_current_weather(
    location_key: Optional[str] = Query(default=None),
):
    """Return the most recent weather observation for a location.

    Query params:
      location_key — optional; defaults to first favorite alphabetically.

    Returns 404 if no data has been ingested yet — trigger the pipeline
    first with POST /api/pipeline/trigger.
    """
    key, name, lat, lon = _resolve_location_key(location_key)

    with get_db_session() as session:
        row = (
            session.query(WeatherObservation)
            .filter_by(location_key=key)
            .order_by(WeatherObservation.observed_at.desc())
            .first()
        )

    if row is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No weather data found for {name}. "
                "Trigger the pipeline first: POST /api/pipeline/trigger"
            ),
        )

    return CurrentWeatherResponse(
        location_name=name,
        latitude=lat,
        longitude=lon,
        observation=WeatherObservationResponse.model_validate(row),
    )


@router.get("/history", response_model=list[WeatherObservationResponse])
def get_weather_history(
    location_key: Optional[str] = Query(default=None),
    limit: int = Query(default=48, ge=1, le=500),
    start_date: Optional[datetime] = Query(default=None),
    end_date: Optional[datetime] = Query(default=None),
):
    """Return weather observation history, newest first.

    Query params:
      location_key — optional; defaults to first favorite alphabetically.
      limit       — max rows to return (1–500, default 48 = last 48 observations)
      start_date  — ISO 8601 datetime, filter rows on or after this time
      end_date    — ISO 8601 datetime, filter rows on or before this time
    """
    key, _, _, _ = _resolve_location_key(location_key)

    with get_db_session() as session:
        query = (
            session.query(WeatherObservation)
            .filter_by(location_key=key)
            .order_by(WeatherObservation.observed_at.desc())
        )

        if start_date:
            query = query.filter(WeatherObservation.observed_at >= start_date)
        if end_date:
            query = query.filter(WeatherObservation.observed_at <= end_date)

        rows = query.limit(limit).all()

    return [WeatherObservationResponse.model_validate(r) for r in rows]
