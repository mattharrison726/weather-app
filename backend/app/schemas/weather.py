"""
Pydantic response schemas for weather API endpoints.

These are the outward-facing contract for weather data. The field names
here match the database column names deliberately — units are in the name
(_c, _mm, _pct, _kmh, _deg) so API consumers never have to guess.

The Optional fields reflect real data: some weather measurements may be
absent from the API response (e.g. precipitation when skies are clear).
Returning null is honest — it's different from returning 0.0.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class WeatherObservationResponse(BaseModel):
    id: int
    location_key: str
    observed_at: datetime
    temperature_c: Optional[float]
    apparent_temperature_c: Optional[float]
    relative_humidity_pct: Optional[int]
    precipitation_mm: Optional[float]
    wind_speed_kmh: Optional[float]
    wind_direction_deg: Optional[int]
    weather_code: Optional[int]
    weather_description: Optional[str]
    is_day: Optional[bool]
    data_quality_flag: str

    model_config = {"from_attributes": True}


class CurrentWeatherResponse(BaseModel):
    """Extended response for /current — includes location metadata."""
    location_name: str
    latitude: float
    longitude: float
    observation: WeatherObservationResponse
