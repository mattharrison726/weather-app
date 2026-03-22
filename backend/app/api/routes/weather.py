"""
Weather data API routes.

GET /api/weather/current  — most recent clean observation
GET /api/weather/history  — paginated observation history with date filters
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.config import settings
from app.db.engine import get_db_session
from app.db.models.transformed import WeatherObservation
from app.schemas.weather import CurrentWeatherResponse, WeatherObservationResponse

router = APIRouter(prefix="/api/weather", tags=["weather"])


@router.get("/current", response_model=CurrentWeatherResponse)
def get_current_weather():
    """Return the most recent weather observation from the silver table.

    Returns 404 if no data has been ingested yet — trigger the pipeline
    first with POST /api/pipeline/trigger.
    """
    with get_db_session() as session:
        row = (
            session.query(WeatherObservation)
            .filter_by(location_key=settings.location_key)
            .order_by(WeatherObservation.observed_at.desc())
            .first()
        )

    if row is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "No weather data found. "
                "Trigger the pipeline first: POST /api/pipeline/trigger"
            ),
        )

    return CurrentWeatherResponse(
        location_name=settings.weather_location_name,
        latitude=settings.weather_latitude,
        longitude=settings.weather_longitude,
        observation=WeatherObservationResponse.model_validate(row),
    )


@router.get("/history", response_model=list[WeatherObservationResponse])
def get_weather_history(
    limit: int = Query(default=48, ge=1, le=500),
    start_date: Optional[datetime] = Query(default=None),
    end_date: Optional[datetime] = Query(default=None),
):
    """Return weather observation history, newest first.

    Query params:
      limit       — max rows to return (1–500, default 48 = last 48 observations)
      start_date  — ISO 8601 datetime, filter rows on or after this time
      end_date    — ISO 8601 datetime, filter rows on or before this time

    Example: /api/weather/history?limit=24&start_date=2024-01-15T00:00:00
    """
    with get_db_session() as session:
        query = (
            session.query(WeatherObservation)
            .filter_by(location_key=settings.location_key)
            .order_by(WeatherObservation.observed_at.desc())
        )

        if start_date:
            query = query.filter(WeatherObservation.observed_at >= start_date)
        if end_date:
            query = query.filter(WeatherObservation.observed_at <= end_date)

        rows = query.limit(limit).all()

    return [WeatherObservationResponse.model_validate(r) for r in rows]
